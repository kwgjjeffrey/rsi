import copy,importlib.util,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('campaign',ROOT/'evolution/scripts/manage_evolution_campaign.py');campaign=importlib.util.module_from_spec(spec);spec.loader.exec_module(campaign)

def record(case,result='passed'):
 return {'case_id':case,'record_id':case,'task_input':{'instruction':'A normal business request'},'trajectory':[],'annotation':{'status':'completed','rubric_version':'project-v1','criteria':[{'id':'correctness'},{'id':'discovery'}],'judgments':[{'criterion':key,'result':result if key=='discovery'else'passed','reason':'Observed fixture comparison','evidence':[{'source':'fixture/trajectory.json'}]}for key in ['correctness','discovery']]},'reflection':'Unit fixture evidence reviewed','execution':{'status':'completed'}}

class Campaign(unittest.TestCase):
 def test_fibonacci_and_strict_half_gate(self):
  self.assertEqual([campaign.size_at(i)for i in range(7)],[1,2,3,5,8,13,21])
  self.assertEqual(campaign.assess([record('a','failed'),record('b')],{})['decision'],'expand')
  self.assertEqual(campaign.assess([record('a','failed'),record('b','needs_improvement'),record('c')],{})['decision'],'repair')
 def test_incomplete_or_evidenceless_assessment_blocks_expansion(self):
  for kind in ['execution','criterion','reason','reflection']:
   r=record('a')
   if kind=='execution':r['execution']['status']='error'
   elif kind=='criterion':r['annotation']['judgments'].pop()
   elif kind=='reason':r['annotation']['judgments'][0]['reason']=''
   else:r['reflection']=''
   result=campaign.assess([r],{});self.assertEqual(result['decision'],'hold_execution');self.assertIsNone(result['unqualified_rate'])
 def test_repair_holds_until_existing_issues_clear(self):
  self.assertEqual(campaign.assess([record('a','failed'),record('b')],{},repair=True)['decision'],'repair')
  self.assertEqual(campaign.outstanding(['old'],{'new':'unqualified'}),['new','old'])
  self.assertEqual(campaign.outstanding(['old','new'],{'old':'qualified'}),['new'])
 def test_numeric_requires_project_choice_and_threshold(self):
  r=record('a');r['annotation']={'status':'completed','score':80,'rubric_version':'project-v1'}
  self.assertEqual(campaign.qualify(r,{}),'incomplete')
  self.assertEqual(campaign.qualify(r,{'qualification':{'mode':'numeric'}}),'incomplete')
  self.assertEqual(campaign.qualify(r,{'qualification':{'mode':'numeric'},'pass_threshold':75}),'qualified')

 def test_cli_windows_hold_and_repair_without_expanding(self):
  with tempfile.TemporaryDirectory()as temporary:
   base=Path(temporary);repo=base/'repo';repo.mkdir();subprocess.run(['git','init','-q',str(repo)],check=True);subprocess.run(['git','-C',str(repo),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','--allow-empty','-qm','fixture'],check=True)
   data=base/'data';binary=ROOT/'local-runtime/bin/rsi-runtime'
   def dispatch(value):
    request=base/'request.json';request.write_text(json.dumps(value));return json.loads(subprocess.check_output([str(binary),'dispatch',str(request)],env={**os.environ,'RSI_DATA_DIR':str(data)},text=True))
   dispatch({'op':'register','project':'target','repo':str(repo)});records=[record(x)for x in ['a','b','c','d','e','f']]
   for r in records:r['annotation']['status']='pending';r['annotation'].pop('judgments');r['execution']={}
   dispatch({'op':'import','project':'target','dataset':'daily','version':'v1','records':records});project=data/'projects/target'
   def cli(action,*args,ok=True):
    result=subprocess.run([sys.executable,str(ROOT/'evolution/scripts/manage_evolution_campaign.py'),action,'--project-root',str(project),'--campaign','daily',*args],capture_output=True,text=True);self.assertEqual(result.returncode==0,ok,result.stderr);return json.loads(result.stdout)if ok else result.stderr
   cli('init','--dataset','daily','--version','v1');self.assertIn('analysis',cli('prepare',ok=False))
   (project/'blueprint/analysis.md').write_text('Unit fixture: actual failure and supporting evidence.');(project/'blueprint/improvement-plan.md').write_text('Unit fixture: change one source path, replay existing failure, reject unchanged behavior.');(project/'blueprint/evaluation.json').write_text('{}')
   first=cli('prepare');self.assertEqual(first['cases'],['a']);self.assertIn('active window',cli('prepare',ok=False))
   round_dir=project/f'sprints/{first["sprint"]}/rounds/001';file=round_dir/'cases/a/record.json';file.parent.mkdir(parents=True);file.write_text(json.dumps(record('a','failed')))
   self.assertIn('reflection.md',cli('assess',ok=False));(round_dir/'reflection.md').write_text('Fixture failure proves the planned change is still needed.');self.assertEqual(cli('assess')['decision'],'repair')
   repair=cli('prepare');self.assertTrue(repair['repair']);self.assertEqual(repair['cases'],['a']);self.assertEqual(repair['sprint'],first['sprint']);self.assertEqual(repair['round'],2);round_dir=project/f'sprints/{repair["sprint"]}/rounds/002';file=round_dir/'cases/a/record.json';file.parent.mkdir(parents=True);file.write_text(json.dumps(record('a')));(round_dir/'reflection.md').write_text('Fixture corrected behavior; existing failure cleared.')
   # Changing live grading policy cannot alter a frozen window's decision.
   (project/'blueprint/evaluation.json').write_text(json.dumps({'qualification':{'mode':'numeric'},'pass_threshold':100}));self.assertEqual(cli('assess')['decision'],'expand');(project/'blueprint/evaluation.json').write_text('{}')
   expanded=cli('prepare');self.assertEqual(expanded['cases'],['b','c']);self.assertEqual(expanded['round'],3)
   self.assertEqual(list((project/'sprints').iterdir()),[project/'sprints/daily'])
   self.assertEqual(len(list((project/'sprints/daily/rounds/000/cases').iterdir())),6)
   self.assertEqual(json.loads((project/'sprints/daily/rounds/003/selection.json').read_text())['cases'],['b','c'])
   self.assertFalse((project/'datasets/campaign_windows').exists())
   # Only selected cases reach the independent replay adapter.
   adapter=base/'adapter.py';adapter.write_text('import sys,json; q=json.load(sys.stdin); print(json.dumps({"trajectory":[],"session_id":q["case_id"],"loaded_skill_digest":"fixture"}))')
   (project/'blueprint/replay.json').write_text(json.dumps({'fresh_session':True,'command':[sys.executable,str(adapter)]}))
   cli('run');self.assertEqual(sorted(p.name for p in(project/'sprints/daily/rounds/003/cases').iterdir()),['b','c'])
   self.assertTrue((project/'sprints/daily/rounds/001/cases/a/record.json').exists())

if __name__=='__main__':unittest.main()
