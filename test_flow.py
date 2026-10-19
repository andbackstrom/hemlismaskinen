import os,tempfile,subprocess,time,urllib.request,urllib.error,json,http.cookiejar,sqlite3,unittest
class Flow(unittest.TestCase):
 def test_flow(self):
  with tempfile.TemporaryDirectory() as data:
   env={**os.environ,'DATA_DIR':data,'BOARD_PASSWORD':'board-test','ADMIN_PASSWORD':'admin-test','SESSION_SECRET':'test-key','ORIGIN':'http://127.0.0.1:18947','PORT':'18947','COOKIE_SECURE':'0'}
   p=subprocess.Popen(['python3','server.py'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
   try:
    time.sleep(.4)
    reader=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    admin=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def call(client,path,body=None,origin='http://127.0.0.1:18947'):
     req=urllib.request.Request('http://127.0.0.1:18947/api/'+path,data=json.dumps(body).encode() if body is not None else None,headers={'Origin':origin,'Content-Type':'application/json'})
     with client.open(req) as r: return json.load(r)
    def denied(client,path,body=None,code=401,origin='http://127.0.0.1:18947'):
     with self.assertRaises(urllib.error.HTTPError) as e: call(client,path,body,origin)
     self.assertEqual(e.exception.code,code)
    denied(reader,'secrets')
    denied(reader,'login',{'password':'wrong'})
    call(reader,'login',{'password':'board-test'})
    denied(reader,'pending',code=403)
    denied(reader,'secrets',{'body':'x'},403,'https://evil.example')
    call(reader,'secrets',{'name':'<script>','body':'a real secret'})
    self.assertEqual(call(reader,'secrets'),[])
    call(admin,'login',{'username':'andreas','password':'admin-test'})
    row=call(admin,'pending')[0]
    denied(reader,'moderate',{'id':row['id'],'action':'approve'},403)
    call(admin,'moderate',{'id':row['id'],'action':'approve'})
    self.assertEqual(call(reader,'secrets')[0],row)
    call(reader,'secrets',{'body':'reject me'})
    row2=call(admin,'pending')[0]
    call(admin,'moderate',{'id':row2['id'],'action':'reject'})
    self.assertEqual(call(admin,'pending'),[])
    with sqlite3.connect(data+'/secrets.sqlite3') as db:
     self.assertEqual(db.execute('select count(*) from secrets').fetchone()[0],1)
     self.assertEqual([r[1] for r in db.execute('pragma table_info(secrets)')],['id','name','body','created_at','approved','published_at'])
    call(reader,'logout',{})
    denied(reader,'secrets')
   finally:
    p.terminate();out,err=p.communicate(timeout=3)
    self.assertEqual(out,b'');self.assertEqual(err,b'')
if __name__=='__main__': unittest.main()
