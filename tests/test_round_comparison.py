import json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Comparison(unittest.TestCase):
 def test_incompatible_and_execution_errors_remain_visible(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);rounds=root/'sprints/s1/rounds'
   def record(case,score,version='v1',error=False):return {'case_id':case,'record_id':case,'task_input':{'instruction':'task'},'trajectory':[],'annotation':{'status':'completed','score':score,'rubric_version':version,'criteria':[]},'reflection':'Evidence reviewed','execution':{'status':'error' if error else 'completed'}}
   for n,values in [('000',[record('a',0),record('b',20),record('c',30)]),('001',[record('a',100),record('b',100,'v2'),record('c',100,error=True)])]:
    for v in values:
     p=rounds/n/'cases'/v['case_id']/'record.json';p.parent.mkdir(parents=True);p.write_text(json.dumps(v))
   subprocess.run([sys.executable,str(ROOT/'evolution/scripts/manage_evolution_round.py'),'compare','--project-root',td,'--sprint','s1','--round','1'],check=True,capture_output=True)
   v=json.loads((rounds/'001/comparison.json').read_text());self.assertEqual(v['total'],3);self.assertEqual(v['comparable'],1);self.assertEqual(v['groups']['incomparable'],['b','c']);self.assertEqual(v['round_mean'],100)
 def test_replay_requires_plan_before_execution(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);p=root/'sprints/s1/rounds/000/cases/c1/record.json';p.parent.mkdir(parents=True);p.write_text('{}');adapter=root/'adapter.json';adapter.write_text('{"fresh_session":true,"command":["must-not-execute"]}')
   run=subprocess.run([sys.executable,str(ROOT/'evolution/scripts/manage_evolution_round.py'),'replay','--project-root',td,'--sprint','s1','--round','1','--adapter',str(adapter)],capture_output=True,text=True);self.assertNotEqual(run.returncode,0);self.assertIn('plan.md',run.stderr)
if __name__=='__main__':unittest.main()
