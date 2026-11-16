import hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from test_evolution_campaign import record
ROOT=Path(__file__).resolve().parents[1]

class CampaignMigration(unittest.TestCase):
 def test_existing_measurements_become_rounds_without_regrading_or_breaking_evidence(self):
  with tempfile.TemporaryDirectory()as temporary:
   base=Path(temporary);repo=base/'repo';subprocess.run(['git','init','-q',str(repo)],check=True);subprocess.run(['git','-C',str(repo),'-c','user.name=Fixture','-c','user.email=f@example.invalid','commit','--allow-empty','-qm','fixture'],check=True)
   data=base/'data';binary=ROOT/'local-runtime/bin/rsi-runtime'
   def dispatch(value):
    p=base/'request.json';p.write_text(json.dumps(value));return json.loads(subprocess.check_output([str(binary),'dispatch',str(p)],env={**os.environ,'RSI_DATA_DIR':str(data)},text=True))
   dispatch({'op':'register','project':'target','repo':str(repo)});project=data/'projects/target'
   records=[record(x)for x in ['a','b','c']]
   for r in records:r['annotation']['status']='pending';r['annotation'].pop('judgments');r['execution']={}
   dispatch({'op':'import','project':'target','dataset':'daily','version':'v1','records':records})
   (project/'blueprint/evaluation.json').write_text('{}');(project/'blueprint/analysis.md').write_text('Analysis');(project/'blueprint/improvement-plan.md').write_text('Plan')
   history=[];unchanged={}
   for n,result in [(1,'failed'),(2,'passed')]:
    sprint=f'old_{n}';dispatch({'op':'create-sprint','project':'target','sprint':sprint,'dataset':'daily','version':'v1'})
    directory=project/f'sprints/{sprint}/rounds/001/cases/a';directory.mkdir(parents=True);r=record('a',result);(directory/'record.json').write_text(json.dumps(r));(directory/'raw.json').write_text(json.dumps({'original_path':f'sprints/{sprint}/rounds/001','session_id':f'session{n}'}))
    for p in directory.iterdir():unchanged[p]=p.read_bytes()
    history.append({'sprint':sprint,'cases':['a'],'repair':n==2,'source':'fixture','batch_size':1,'decision':'repair'if n==1 else'expand'})
   state={'campaign':'daily','dataset':'daily/v1','case_order':['a','b','c'],'dataset_hashes':{r['case_id']:hashlib.sha256((project/f'datasets/daily/v1/cases/{r["case_id"]}/record.json').read_bytes()).hexdigest()for r in records},'cursor':1,'fibonacci_index':1,'repair_cases':[],'outstanding_cases':[],'active':None,'history':history}
   state_file=project/'blueprint/campaigns/daily.json';state_file.parent.mkdir();state_file.write_text(json.dumps(state))
   def cli(action):return json.loads(subprocess.check_output([sys.executable,str(ROOT/'evolution/scripts/manage_evolution_campaign.py'),action,'--project-root',str(project),'--campaign','daily'],text=True))
   result=cli('migrate');self.assertEqual(result['rounds'],2)
   for p,content in unchanged.items():self.assertEqual(p.read_bytes(),content)
   for n in [1,2]:
    for p in (project/f'sprints/old_{n}/rounds/001/cases/a').iterdir():self.assertEqual(p.read_bytes(),(project/f'sprints/daily/rounds/{n:03}/cases/a'/p.name).read_bytes())
    self.assertEqual(json.loads((project/f'sprints/old_{n}/sprint.json').read_text())['archived_into'],'daily')
   comparison=json.loads((project/'sprints/daily/rounds/002/comparison.json').read_text());self.assertEqual(comparison['groups']['improved'],['a']);self.assertEqual(comparison['baseline_rounds'],{'a':1})
   migrated=json.loads(state_file.read_text());self.assertEqual([h['round']for h in migrated['history']],[1,2]);self.assertEqual({h['sprint']for h in migrated['history']},{'daily'})
   self.assertEqual(cli('migrate')['status'],'already_consolidated')
   next_round=cli('prepare');self.assertEqual(next_round['round'],3);self.assertEqual(next_round['sprint'],'daily');self.assertEqual(next_round['cases'],['b','c'])
if __name__=='__main__':unittest.main()
