import os,tempfile,unittest,io,json,importlib.util
from email.message import Message
class Handlers(unittest.TestCase):
 def test_auth_and_moderation(self):
  with tempfile.TemporaryDirectory() as d:
   os.environ.update(DATA_DIR=d,BOARD_PASSWORD='test-board',ADMIN_PASSWORD='test-admin',SESSION_SECRET='test-secret',ORIGIN='https://hemlis.andreas.quest')
   spec=importlib.util.spec_from_file_location('hemlis','server.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
   def call(path,body=None,cookie='',origin='https://hemlis.andreas.quest'):
    h=m.Handler.__new__(m.Handler);h.path=path;h.headers=Message();h.headers['Cookie']=cookie;h.headers['Origin']=origin
    raw=json.dumps(body).encode();h.headers['Content-Length']=str(len(raw));h.rfile=io.BytesIO(raw)
    def reply(status,value,cookie=None,html=False): h.result=(status,value,cookie)
    h.reply=reply
    (h.do_GET if body is None else h.do_POST)();return h.result
   self.assertEqual(call('/api/secrets')[0],401)
   r=call('/api/login',{'password':'test-board'});self.assertEqual(r[0],200);reader=r[2].split(';')[0]
   self.assertEqual(call('/api/pending',cookie=reader)[0],403)
   self.assertEqual(call('/api/secrets',{'body':'secret'},reader,'https://evil.test')[0],403)
   self.assertEqual(call('/api/secrets',{'body':'secret','name':'alias'},reader)[0],201)
   self.assertEqual(call('/api/secrets',cookie=reader)[1],[])
   admin=call('/api/login',{'username':'andreas','password':'test-admin'})[2].split(';')[0]
   pending=call('/api/pending',cookie=admin)[1][0]
   self.assertEqual(call('/api/moderate',{'id':pending['id'],'action':'approve'},reader)[0],403)
   call('/api/moderate',{'id':pending['id'],'action':'approve'},admin)
   self.assertEqual(call('/api/secrets',cookie=reader)[1][0],pending)
   call('/api/secrets',{'body':'remove'},reader)
   rejected=call('/api/pending',cookie=admin)[1][0]
   call('/api/moderate',{'id':rejected['id'],'action':'reject'},admin)
   self.assertEqual(call('/api/pending',cookie=admin)[1],[])
   with m.db() as c:
    self.assertEqual(c.execute('SELECT count(*) FROM secrets').fetchone()[0],1)
    self.assertEqual([r[1] for r in c.execute('pragma table_info(secrets)')],['id','name','body','created_at','approved'])
if __name__=='__main__':unittest.main()
