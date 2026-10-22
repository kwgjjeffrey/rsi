import json,os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Contract(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.repo=self.root/'repo';self.repo.mkdir();subprocess.run(['git','init','-q',str(self.repo)],check=True)
 def tearDown(self):self.tmp.cleanup()
 def call(self,v,ok=True):
  req=self.root/'request.json';req.write_text(json.dumps(v));p=subprocess.run([str(ROOT/'local-runtime/bin/rsi-runtime'),'dispatch',str(req)],env=dict(os.environ,RSI_DATA_DIR=str(self.root/'data')),capture_output=True,text=True)
  self.assertEqual(p.returncode==0,ok,p.stderr)
  return json.loads(p.stdout) if ok else p.stderr
 def register(self):self.call({'op':'register','project':'target','repo':str(self.repo)})
 def record(self):return {'case_id':'c1','record_id':'i1','task_input':{'instruction':'task'},'trajectory':[],'annotation':{'status':'unknown'},'reflection':'insufficient evidence'}
 def test_import_snapshot_and_immutability(self):
  self.register();v={'op':'import','project':'target','dataset':'seed','version':'v1','records':[self.record()]};self.call(v);self.call(v,False)
  self.call({'op':'create-sprint','project':'target','sprint':'s1','dataset':'seed','version':'v1'})
  base=self.root/'data/projects/target';original=base/'datasets/seed/v1/cases/c1/record.json';snap=base/'sprints/s1/rounds/000/cases/c1/record.json';self.assertEqual(original.read_bytes(),snap.read_bytes());original.write_text('{}');self.assertIn('task_input',snap.read_text())
 def test_boundaries(self):
  self.register();self.call({'op':'register','project':'../escape','repo':str(self.repo)},False);self.call({'op':'read','project':'target','path':'../../rsi.sqlite'},False)
  rec=self.record();del rec['annotation'];self.call({'op':'import','project':'target','dataset':'bad','version':'v1','records':[rec]},False)
 def test_workspace_preserves_preview_boundaries(self):
  self.register();base=self.root/'data/projects/target';(base/'blueprint/analysis.md').write_text('# Analysis')
  (base/'private.txt').write_text('not a workbench artifact')
  outside=self.root/'outside.md';outside.write_text('private outside');(base/'blueprint/escape.md').symlink_to(outside)
  result=self.call({'op':'workspace','project':'target'})
  self.assertEqual(result['contents']['blueprint/analysis.md'],'# Analysis');self.assertNotIn('private.txt',result['contents']);self.assertNotIn('blueprint/escape.md',result['contents'])
 def test_duplicate_cases_rejected(self):
  self.register();self.call({'op':'import','project':'target','dataset':'bad','version':'v1','records':[self.record(),self.record()]},False)
if __name__=='__main__':unittest.main()
