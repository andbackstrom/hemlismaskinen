import importlib.util
import io
import json
import os
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import patch


class Music(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.catalog = Path(self.temp.name) / 'likes.json'
        self.environment = patch.dict(os.environ, {
            'DATA_DIR': self.temp.name, 'BOARD_PASSWORD': 'synthetic-board',
            'ADMIN_PASSWORD': 'synthetic-admin', 'SESSION_SECRET': 'synthetic-signing-key',
            'MUSIC_CATALOG_PATH': str(self.catalog),
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        spec = importlib.util.spec_from_file_location('music_test_server', 'server.py')
        self.server = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.server)

    def write(self, tracks):
        self.catalog.write_text(json.dumps({'tracks': tracks}))

    def test_only_liked_youtube_videos_are_returned_without_extra_source_data(self):
        self.write([
            {'links': [{'href': 'watch?v=TESTVID0001&list=LM', 'name': 'Synthetic song'},
                       {'href': 'channel/example', 'name': 'Synthetic channel'}],
             'private_note': 'Must stay in the source file'},
            {'links': [{'href': 'watch?v=TESTVID0002&list=OTHER', 'name': 'Not a like'}]},
            {'links': [{'href': 'https://evil.example/watch?v=TESTVID0003&list=LM', 'name': 'Wrong origin'}]},
            {'links': [{'href': 'watch?v=../bad&list=LM', 'name': 'Invalid ID'}]},
            None,
        ])
        track = self.server.random_music()
        self.assertEqual(track, {'video_id': 'TESTVID0001', 'title': 'Synthetic song',
                                'artist': 'Synthetic channel', 'source': 'Musikhjärnans YouTube-favoriter'})

    def test_missing_empty_malformed_and_oversized_sources_fail_closed(self):
        with self.assertRaises(self.server.MusicUnavailable):
            self.server.random_music()
        for raw in ('{"tracks": []}', '{broken', '{"tracks": {}}', ' ' * (2 * 1024 * 1024 + 1)):
            self.catalog.write_text(raw)
            with self.subTest(size=len(raw)), self.assertRaises(self.server.MusicUnavailable):
                self.server.random_music()

    def request(self, role):
        handler = self.server.Handler.__new__(self.server.Handler)
        handler.path = '/api/music'
        handler.headers = Message()
        handler.role = lambda: role
        handler.reply = lambda status, value: (status, value)
        return handler.do_GET()

    def test_music_endpoint_requires_login_and_returns_a_sanitized_error(self):
        self.assertEqual(self.request(None)[0], 401)
        status, response = self.request('reader')
        self.assertEqual(status, 503)
        self.assertNotIn(self.temp.name, json.dumps(response))
        self.write([{'links': [{'href': 'watch?v=TESTVID0001&list=LM', 'name': 'Synthetic song'}]}])
        for role in ('reader', 'admin'):
            with self.subTest(role=role):
                status, response = self.request(role)
                self.assertEqual(status, 200)
                self.assertEqual(response['video_id'], 'TESTVID0001')


if __name__ == '__main__':
    unittest.main()
