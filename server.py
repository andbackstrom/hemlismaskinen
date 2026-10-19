import os, json, sqlite3, secrets, hashlib, hmac, time, re
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

ROOT = Path(__file__).parent
DATA = Path(os.environ.get('DATA_DIR', str(ROOT / 'data')))
DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
BOARD = os.environ['BOARD_PASSWORD']
ADMIN = os.environ['ADMIN_PASSWORD']
KEY = os.environ['SESSION_SECRET'].encode()
ORIGIN = os.environ.get('ORIGIN', 'https://hemlis.andreas.quest')
SECURE = os.environ.get('COOKIE_SECURE', '1') == '1'

class MusicUnavailable(Exception):
    pass

def random_music():
    """Read only the imported YouTube Likes source; never contact YouTube here."""
    try:
        path = Path(os.environ.get('MUSIC_CATALOG_PATH', '/music/youtube-likes.json'))
        with path.open('rb') as source:
            raw = source.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            raise ValueError('Source too large')
        source = json.loads(raw)
        tracks = source.get('tracks') if isinstance(source, dict) else None
        if not isinstance(tracks, list) or len(tracks) > 5000:
            raise ValueError('Invalid source')
        candidates = {}
        for track in tracks:
            if not isinstance(track, dict) or not isinstance(track.get('links'), list):
                continue
            links = [link for link in track['links'] if isinstance(link, dict)]
            artists = []
            for link in links:
                href, name = link.get('href'), link.get('name')
                if isinstance(href, str) and isinstance(name, str) and href.startswith('channel/'):
                    artists.append(name.strip()[:160])
            for link in links:
                href, title = link.get('href'), link.get('name')
                if not isinstance(href, str) or not isinstance(title, str) or not title.strip():
                    continue
                parsed = urlsplit(href)
                if parsed.netloc and parsed.netloc not in ('www.youtube.com', 'youtube.com', 'music.youtube.com'):
                    continue
                if parsed.scheme not in ('', 'https') or parsed.path.lstrip('/') != 'watch':
                    continue
                query = parse_qs(parsed.query)
                video_id = query.get('v', [''])[0]
                if query.get('list') != ['LM'] or not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
                    continue
                candidates[video_id] = {'video_id': video_id, 'title': title.strip()[:240],
                    'artist': ', '.join(dict.fromkeys(artists))[:240], 'source': 'Musikhjärnans YouTube-favoriter'}
        if not candidates:
            raise ValueError('No liked videos')
        return secrets.choice(list(candidates.values()))
    except (OSError, ValueError, TypeError, RecursionError):
        raise MusicUnavailable() from None
def db():
    c = sqlite3.connect(DATA / 'secrets.sqlite3')
    c.row_factory = sqlite3.Row
    return c
with db() as c:
    c.execute('CREATE TABLE IF NOT EXISTS secrets (id TEXT PRIMARY KEY, name TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL, approved INTEGER NOT NULL DEFAULT 0)')
os.chmod(DATA / 'secrets.sqlite3', 0o600)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def log_error(self, *args): pass
    def reply(self, status, value, cookie=None, html=False):
        payload = value.encode() if html else json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8' if html else 'application/json; charset=utf-8')
        for k,v in {'Cache-Control':'no-store', 'Referrer-Policy':'no-referrer', 'X-Content-Type-Options':'nosniff', 'X-Frame-Options':'DENY', 'Permissions-Policy':'camera=(), microphone=(), geolocation=()', 'Content-Security-Policy':"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-src https://www.youtube-nocookie.com; frame-ancestors 'none'; base-uri 'none'; form-action 'self'", 'Content-Length':str(len(payload))}.items(): self.send_header(k,v)
        if cookie: self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(payload)
    def role(self):
        try:
            cookies = SimpleCookie(self.headers.get('Cookie',''))
            token = cookies['hemlis'].value
            role, expiry, sig = token.split('.')
            expected = hmac.new(KEY, f'{role}.{expiry}'.encode(), hashlib.sha256).hexdigest()
            return role if int(expiry)>time.time() and hmac.compare_digest(sig, expected) and role in ('reader','admin') else None
        except Exception: return None
    def cookie(self, role):
        base = f'{role}.{int(time.time())+28800}'
        token = base+'.'+hmac.new(KEY,base.encode(),hashlib.sha256).hexdigest()
        return f'hemlis={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'+ ('; Secure' if SECURE else '')
    def do_GET(self):
        path = self.path.split('?')[0]
        if path in ('/', '/anonymitet', '/admin'):
            return self.reply(200,(ROOT/'index.html').read_text(),html=True)
        if path == '/api/session': return self.reply(200,{'role':self.role()})
        if path not in ('/api/secrets','/api/pending','/api/music'): return self.reply(404,{'error':'Finns inte.'})
        role = self.role()
        if not role: return self.reply(401,{'error':'Lås upp först.'})
        if path == '/api/music':
            try: return self.reply(200, random_music())
            except MusicUnavailable: return self.reply(503, {'error':'Musikkällan är inte tillgänglig just nu.'})
        if path == '/api/pending' and role != 'admin': return self.reply(403,{'error':'Endast andreas.'})
        with db() as c:
            rows = c.execute('SELECT id,name,body,created_at FROM secrets WHERE approved=? ORDER BY created_at DESC LIMIT 500',(0 if path=='/api/pending' else 1,)).fetchall()
        return self.reply(200,[dict(r) for r in rows])
    def do_POST(self):
        if self.headers.get('Origin') != ORIGIN: return self.reply(403,{'error':'Ogiltigt ursprung.'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size>12000 or size<2: return self.reply(413,{'error':'För stor förfrågan.'})
            data=json.loads(self.rfile.read(size))
            if not isinstance(data,dict): raise ValueError()
        except Exception: return self.reply(400,{'error':'Ogiltig förfrågan.'})
        if self.path=='/api/login':
            admin=data.get('username')=='andreas'
            password=data.get('password','')
            if not isinstance(password,str): password=''
            valid = hmac.compare_digest(hashlib.sha256(password.encode()).digest(),hashlib.sha256((ADMIN if admin else BOARD).encode()).digest())
            if not valid:
                time.sleep(0.5)
                return self.reply(401,{'error':'Fel lösenord.'})
            return self.reply(200,{'role':'admin' if admin else 'reader'},self.cookie('admin' if admin else 'reader'))
        if self.path=='/api/logout': return self.reply(200,{},'hemlis=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'+ ('; Secure' if SECURE else ''))
        role=self.role()
        if not role: return self.reply(401,{'error':'Lås upp först.'})
        if self.path=='/api/secrets':
            name=data.get('name','').strip() if isinstance(data.get('name',''),str) else ''
            body=data.get('body','').strip() if isinstance(data.get('body',''),str) else ''
            if not 1<=len(body)<=2000 or len(name)>40: return self.reply(400,{'error':'Skriv 1–2000 tecken och ett alias på högst 40 tecken.'})
            from datetime import datetime, timezone
            with db() as c: c.execute('INSERT INTO secrets(id,name,body,created_at) VALUES(?,?,?,?)',(secrets.token_hex(16),name or 'Anonym',body,datetime.now(timezone.utc).isoformat()))
            return self.reply(201,{'ok':True})
        if self.path=='/api/moderate' and role=='admin':
            if data.get('action') not in ('approve','reject'): return self.reply(400,{'error':'Ogiltigt val.'})
            with db() as c:
                if data['action']=='approve': c.execute('UPDATE secrets SET approved=1 WHERE id=? AND approved=0',(str(data.get('id','')),))
                else: c.execute('DELETE FROM secrets WHERE id=? AND approved=0',(str(data.get('id','')),))
            return self.reply(200,{'ok':True})
        return self.reply(403,{'error':'Åtkomst nekad.'})

if __name__=='__main__':
    ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT','8080'))),Handler).serve_forever()
