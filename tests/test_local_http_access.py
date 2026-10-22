import json,os,subprocess,tempfile,time,unittest,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class LocalAccess(unittest.TestCase):
 def test_plain_local_url_and_cross_site_boundary(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);proc=subprocess.Popen([str(ROOT/'local-runtime/bin/rsi-runtime'),'serve'],env=dict(os.environ,RSI_DATA_DIR=td,RSI_PORT='0'),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
   try:
    for _ in range(100):
     if (root/'runtime.json').exists():break
     if proc.poll() is not None:self.fail(proc.stderr.read().decode())
     time.sleep(.02)
    d=json.loads((root/'runtime.json').read_text());self.assertNotIn('token',d)
    html=urllib.request.urlopen(d['url']+'/').read().decode();self.assertNotIn('Bearer',html);self.assertNotIn('rsi-token',html)
    repo=root/'repo';subprocess.run(['git','init','-q',str(repo)],check=True)
    def call(v,headers=None):
     return urllib.request.urlopen(urllib.request.Request(d['url']+'/api',data=json.dumps(v).encode(),headers=dict({'Content-Type':'application/json'},**(headers or {}))))
    json.load(call({'op':'register','project':'target','repo':str(repo)}))
    self.assertEqual(json.load(call({'op':'list'}))[0]['id'],'target')
    self.assertEqual(json.load(call({'op':'list'},{'Origin':d['url']}))[0]['id'],'target')
    for headers in [{'Origin':'https://unrelated.example'},{'Host':'unrelated.example'}]:
     with self.assertRaises(urllib.error.HTTPError) as failure:call({'op':'list'},headers)
     self.assertEqual(failure.exception.code,403)
   finally:
    proc.terminate();proc.wait(timeout=5);proc.stderr.close()
if __name__=='__main__':unittest.main()
