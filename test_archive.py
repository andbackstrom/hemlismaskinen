import importlib.util
import io
import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from email.message import Message
from pathlib import Path
from unittest.mock import patch


class Archive(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.environment = patch.dict(os.environ, {
            'DATA_DIR': self.temp.name, 'BOARD_PASSWORD': 'synthetic-board',
            'ADMIN_PASSWORD': 'synthetic-admin', 'SESSION_SECRET': 'synthetic-signing-key',
            'ORIGIN': 'https://hemlis.test',
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.now = datetime(2026, 10, 19, 6, tzinfo=timezone.utc)

    def load(self):
        spec = importlib.util.spec_from_file_location('archive_test_server', 'server.py')
        self.server = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.server)
        self.server.utc_now = lambda: self.now.isoformat()

    def call(self, path, role='admin', body=None, origin='https://hemlis.test'):
        handler = self.server.Handler.__new__(self.server.Handler)
        handler.path = path
        handler.role = lambda: role
        handler.headers = Message()
        handler.headers['Origin'] = origin
        handler.reply = lambda status, value: (status, value)
        if body is None:
            return handler.do_GET()
        raw = json.dumps(body).encode()
        handler.headers['Content-Length'] = str(len(raw))
        handler.rfile = io.BytesIO(raw)
        return handler.do_POST()

    def seed(self, identifier, approved, published=None):
        with self.server.db() as db:
            db.execute('INSERT INTO secrets VALUES(?,?,?,?,?,?)',
                       (identifier, 'Original alias', 'Original text', '2020-01-02T03:04:05+00:00', approved, published))

    def test_exact_thirty_day_boundary_and_archive_access(self):
        self.load()
        boundary = self.now - timedelta(days=30)
        self.seed('expired', 1, boundary.isoformat())
        self.seed('active', 1, (boundary + timedelta(seconds=1)).isoformat())
        self.seed('pending', 0)
        self.seed('invalid-date', 1, 'not-a-date')
        self.seed('missing-date', 1)
        self.assertEqual([x['id'] for x in self.call('/api/secrets', role='reader')[1]], ['active'])
        for role, expected in ((None, 401), ('reader', 403)):
            self.assertEqual(self.call('/api/archive', role=role)[0], expected)
        archived = self.call('/api/archive')[1]
        self.assertEqual({x['id'] for x in archived}, {'expired', 'invalid-date', 'missing-date'})
        self.assertEqual([x['id'] for x in self.call('/api/pending')[1]], ['pending'])

    def test_only_explicit_admin_republish_starts_a_new_window(self):
        self.load()
        old_publication = (self.now - timedelta(days=31)).isoformat()
        self.seed('secret', 1, old_publication)
        original = self.call('/api/archive')[1][0]
        self.call('/api/archive')
        with self.server.db() as db:
            self.assertEqual(db.execute('SELECT published_at FROM secrets').fetchone()[0], old_publication)
        action = {'id': 'secret', 'action': 'republish'}
        self.assertEqual(self.call('/api/moderate', role='reader', body=action)[0], 403)
        self.assertEqual(self.call('/api/moderate', body=action, origin='https://foreign.test')[0], 403)
        self.assertEqual(self.call('/api/moderate', body=action)[0], 200)
        self.assertEqual(self.call('/api/secrets', role='reader')[1], [original])
        self.assertEqual(self.call('/api/archive')[1], [])
        self.assertEqual(self.call('/api/moderate', body=action)[0], 409)
        self.now += timedelta(days=30)
        self.assertEqual(self.call('/api/secrets', role='reader')[1], [])
        self.assertEqual(self.call('/api/archive')[1], [original])

    def test_approval_uses_publication_time_not_the_old_submission_time(self):
        self.load()
        self.seed('pending', 0)
        self.assertEqual(self.call('/api/moderate', body={'id':'pending', 'action':'republish'})[0], 409)
        self.assertEqual(self.call('/api/moderate', body={'id':'pending', 'action':'approve'})[0], 200)
        self.assertEqual(self.call('/api/secrets', role='reader')[1][0]['created_at'], '2020-01-02T03:04:05+00:00')
        with self.server.db() as db:
            self.assertEqual(db.execute('SELECT published_at FROM secrets').fetchone()[0], self.now.isoformat())

    def test_old_schema_migrates_once_preserving_rows(self):
        database = Path(self.temp.name) / 'secrets.sqlite3'
        with sqlite3.connect(database) as db:
            db.execute('CREATE TABLE secrets (id TEXT PRIMARY KEY, name TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL, approved INTEGER NOT NULL DEFAULT 0)')
            db.executemany('INSERT INTO secrets VALUES(?,?,?,?,?)', [
                ('old', 'Old alias', 'Old text', (self.now-timedelta(days=31)).isoformat(), 1),
                ('recent', 'Recent alias', 'Recent text', (self.now-timedelta(days=2)).isoformat(), 1),
                ('pending', 'Pending alias', 'Pending text', '2020-01-01T00:00:00+00:00', 0),
            ])
        self.load()
        self.assertEqual([x['id'] for x in self.call('/api/archive')[1]], ['old'])
        self.assertEqual([x['id'] for x in self.call('/api/secrets', role='reader')[1]], ['recent'])
        with self.server.db() as db:
            db.execute('UPDATE secrets SET published_at=NULL WHERE id=?', ('recent',))
        self.load()
        self.assertEqual({x['id'] for x in self.call('/api/archive')[1]}, {'old', 'recent'})
        with self.server.db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM secrets').fetchone()[0], 3)
            self.assertIsNone(db.execute('SELECT published_at FROM secrets WHERE id=?', ('pending',)).fetchone()[0])

    def test_archive_pages_do_not_hide_older_rows_and_offsets_are_validated(self):
        self.load()
        date = (self.now-timedelta(days=31)).isoformat()
        with self.server.db() as db:
            db.executemany('INSERT INTO secrets VALUES(?,?,?,?,?,?)',
                          [(str(i).zfill(4), 'Synthetic', 'Synthetic', date, 1, date) for i in range(501)])
        first = self.call('/api/archive')[1]
        second = self.call('/api/archive?offset=500')[1]
        self.assertEqual((len(first),len(second)), (500,1))
        self.assertEqual(len({x['id'] for x in first+second}), 501)
        for offset in ('-1','nope','1000000000'):
            self.assertEqual(self.call('/api/archive?offset='+offset)[0], 400)


if __name__ == '__main__':
    unittest.main()
