import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'normalize/scripts'))
from validate_normalization_records import validate_record,materialize_replay

def record(values):
 return {'case_id':'a','record_id':'a','task_input':{'instruction':'ordinary request'},'trajectory':[],'annotation':{'status':'completed','rubric_version':'v1','criteria':[{'id':k}for k in values],'judgments':[{'criterion':k,'result':v,'reason':'Observed evidence'}for k,v in values.items()],'reference':{'ideal_path':['known contract','action']},'asset_contract':{'target':'test capability'}},'reflection':'Actual case evidence reviewed','execution':{'status':'completed'}}

class Categorical(unittest.TestCase):
 def test_completed_judgments_need_no_aggregate(self):
  r=record({'purpose':'passed','usage':'failed'});self.assertIs(validate_record(r),r);self.assertNotIn('score',r['annotation'])
 def test_missing_criterion_cannot_be_completed(self):
  r=record({'purpose':'passed','usage':'failed'});r['annotation']['judgments'].pop()
  with self.assertRaises(ValueError):validate_record(r)
 def test_replay_preserves_references_but_clears_labels(self):
  old=record({'purpose':'passed'});old['annotation']['score']=100;old['annotation']['reason']='old observation'
  new=materialize_replay(old,{'protocol_version':1,'trajectory':[],'execution':{'status':'completed','session_id':'fresh','loaded_skill_digest':'actual'}},'new')
  self.assertEqual(new['annotation']['reference'],old['annotation']['reference']);self.assertEqual(new['annotation']['asset_contract'],old['annotation']['asset_contract']);self.assertNotIn('judgments',new['annotation']);self.assertNotIn('score',new['annotation']);self.assertNotIn('reason',new['annotation'])
 def test_compare_keeps_dimensions_and_exposes_mixed_changes(self):
  with tempfile.TemporaryDirectory()as temporary:
   root=Path(temporary);rounds=root/'sprints/s/rounds'
   for name,values in [('000',{'purpose':'passed','usage':'failed'}),('001',{'purpose':'failed','usage':'passed'})]:
    file=rounds/name/'cases/a/record.json';file.parent.mkdir(parents=True);file.write_text(json.dumps(record(values)))
   subprocess.run([sys.executable,str(ROOT/'evolution/scripts/manage_evolution_round.py'),'compare','--project-root',str(root),'--sprint','s','--round','1'],capture_output=True,text=True,check=True)
   result=json.loads((rounds/'001/comparison.json').read_text());self.assertEqual(result['groups']['mixed'],['a']);self.assertIsNone(result['round_mean']);self.assertEqual(result['categorical_comparable'],1);self.assertEqual(result['dimensions']['a']['after']['usage'],'passed')

if __name__=='__main__':unittest.main()
