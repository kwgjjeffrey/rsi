#!/usr/bin/env python3
"""Create immutable replay records and compare annotated rounds; never simulate agent evaluation."""
import argparse,json,os,subprocess,time,hashlib,sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'normalize/scripts'))
from manage_project_normalization import run_replay_pipeline
from validate_normalization_records import materialize_replay, validate_result, identifier, judgment_results

def load(p): return json.loads(p.read_text())
def save(p,v): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['replay','compare']);p.add_argument('--project-root',type=Path,required=True);p.add_argument('--sprint',required=True);p.add_argument('--round',type=int,required=True);p.add_argument('--baseline-round',help='Earlier round number, or previous for each case’s last measured round');p.add_argument('--adapter',type=Path);p.add_argument('--timeout',type=int,default=600);a=p.parse_args()
 if not a.sprint or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in a.sprint):p.error('invalid sprint')
 if a.round<1:p.error('round must be >=1')
 root=a.project_root.resolve();s=root/'sprints'/a.sprint;dst=s/'rounds'/f'{a.round:03d}'
 selection=load(dst/'selection.json')if(dst/'selection.json').exists()else None
 choice=a.baseline_round or ('previous'if selection else'0')
 if choice!='previous' and(not choice.isdigit()or not 0<=int(choice)<a.round):p.error('baseline must be an earlier round or previous')
 baseline_number=int(choice)if choice!='previous'and a.action=='compare'else 0
 baseline=s/'rounds'/f'{baseline_number:03d}'
 cases=sorted(((dst if a.action=='compare'and choice=='previous'else baseline)/'cases').glob('*/record.json'))
 if selection:
  selected=selection.get('cases',[])
  if not selected or len(set(selected))!=len(selected):p.error('Invalid round selection')
  cases=[f for f in cases if f.parent.name in selected]
  if len(cases)!=len(selected):p.error('Selected cases are missing from the frozen baseline or measured round')
 if not cases:p.error('baseline contains no cases')
 if a.action=='replay':
  if not a.adapter:p.error('--adapter required')
  config=load(a.adapter);cmd=config.get('command');
  if config.get('enabled')is False:p.error('Replay is on hold in blueprint/replay.json')
  pipeline=config.get('normalization_protocol')==1
  if not pipeline and (not isinstance(cmd,list) or not cmd or not all(isinstance(x,str) for x in cmd)):p.error('adapter.command must be argv array')
  if config.get('fresh_session') is not True:p.error('adapter must declare fresh_session=true; verify harness behavior separately')
  if not (dst/'plan.md').is_file():p.error('write round plan.md before replay')
  repo=Path(load(root/'project.json')['repo']);revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip();patch=subprocess.check_output(['git','diff','HEAD','--binary'],cwd=repo);status=subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True)
  if '?? ' in status:p.error('untracked source files: record/commit them before replay')
  if (dst/'round.json').exists():p.error('round already executed; use a new round')
  (dst/'changes.patch').write_bytes(patch);save(dst/'round.json',{'status':'running','revision':revision,'patch_sha256':hashlib.sha256(patch).hexdigest(),'adapter':config,'started_at':time.time()})
  for file in cases:
   original=load(file);case=identifier(original['case_id'],'case_id');request={'schema_version':1,'case_id':case,'task_input':original['task_input'],'source':{'repo':str(repo),'revision':revision,'patch_sha256':hashlib.sha256(patch).hexdigest()},'fresh_session':True}
   start=time.monotonic();error=None;result={};normalized=None
   try:
    if pipeline:
     request['run_dir']=str(dst/'cases'/case/'raw')
     request['timeout_seconds']=a.timeout
     normalized=run_replay_pipeline(root,request,a.timeout)
    else:
     run=subprocess.run(cmd,input=json.dumps(request),capture_output=True,text=True,timeout=a.timeout,cwd=repo)
     if run.returncode:error=f'adapter exit {run.returncode}'
     else:
      result=json.loads(run.stdout)
      if not isinstance(result.get('trajectory'),list) or not result.get('session_id') or not result.get('loaded_skill_digest'):error='adapter missing trajectory/session_id/loaded_skill_digest'
     normalized={'protocol_version':1,'trajectory':result.get('trajectory',[]),'execution':{'status':'error' if error else 'completed','error':error,'session_id':result.get('session_id'),'loaded_skill_digest':result.get('loaded_skill_digest')}}
    validate_result(normalized)
   except (subprocess.TimeoutExpired,OSError,ValueError,KeyError) as e:
    normalized={'protocol_version':1,'trajectory':[],'execution':{'status':'error','error':str(e)}}
   normalized['execution']['seconds']=time.monotonic()-start
   record=materialize_replay(original,normalized,f'{a.sprint}_r{a.round}_{case}')
   save(dst/'cases'/case/'record.json',record)
  meta=load(dst/'round.json');meta['status']='awaiting_annotation';save(dst/'round.json',meta);print(json.dumps(meta));return
 def score(r):
  annotation=r['annotation']
  if annotation.get('status')!='completed':return None
  n=annotation.get('score')
  if n is None:return None
  if isinstance(n,bool) or not isinstance(n,(int,float)) or not 0<=n<=100:raise ValueError('completed annotation requires score 0..100')
  if not annotation.get('rubric_version'):raise ValueError('rubric_version required')
  if not r.get('reflection'):raise ValueError('case reflection required')
  if r.get('execution',{}).get('status')=='error':return None
  return n
 groups={'improved':[],'regressed':[],'mixed':[],'unchanged':[],'incomparable':[],'new':[]};pairs=[];vectors={};baseline_rounds={}
 for file in cases:
  if choice=='previous':
   case=file.parent.name;prior=[]
   for previous in sorted((s/'rounds').iterdir(),key=lambda p:int(p.name)if p.name.isdigit()else-1):
    candidate=previous/'cases'/case/'record.json'
    if previous.name.isdigit()and int(previous.name)<a.round and candidate.exists():
     value=load(candidate)
     if value.get('annotation',{}).get('status')=='completed'and value.get('execution',{}).get('status')not in ['error','failed','timeout','cancelled']:prior.append((int(previous.name),value))
   if not prior:groups['new'].append(case);baseline_rounds[case]=None;continue
   number,old=prior[-1];baseline_rounds[case]=number
  else:old=load(file);baseline_rounds[old['case_id']]=int(choice)
  newpath=dst/'cases'/old['case_id']/'record.json'
  if not newpath.exists():groups['incomparable'].append(old['case_id']);continue
  new=load(newpath);x,y=score(old),score(new)
  compatible=old['task_input']==new['task_input'] and old['annotation'].get('rubric_version')==new['annotation'].get('rubric_version') and old['annotation'].get('criteria')==new['annotation'].get('criteria')
  if not compatible:groups['incomparable'].append(old['case_id']);continue
  if x is None or y is None:
   if any(r.get('execution',{}).get('status')=='error' or r['annotation'].get('status')!='completed' or not r['annotation'].get('rubric_version') or not r.get('reflection')for r in [old,new]):groups['incomparable'].append(old['case_id']);continue
   try:before,after=judgment_results(old),judgment_results(new)
   except ValueError:groups['incomparable'].append(old['case_id']);continue
   if set(before)!=set(after):groups['incomparable'].append(old['case_id']);continue
   rank={'failed':0,'needs_improvement':1,'passed':2};better=any(rank[after[k]]>rank[before[k]]for k in before);worse=any(rank[after[k]]<rank[before[k]]for k in before)
   groups['mixed'if better and worse else'improved'if better else'regressed'if worse else'unchanged'].append(old['case_id']);vectors[old['case_id']]={'before':before,'after':after};continue
  pairs.append((x,y));groups['improved' if y>x else 'regressed' if y<x else 'unchanged'].append(old['case_id'])
 out={'groups':groups,'total':len(cases),'comparable':len(pairs)+len(vectors),'baseline_round':None if choice=='previous'else int(choice),'baseline_strategy':'previous_measurement'if choice=='previous'else'explicit_round','baseline_rounds':baseline_rounds,'dimensions':vectors,'numeric_comparable':len(pairs),'categorical_comparable':len(vectors),'baseline_mean':sum(x for x,y in pairs)/len(pairs) if pairs else None,'round_mean':sum(y for x,y in pairs)/len(pairs) if pairs else None,'comparison_scope':'paired identical task/criteria; categorical judgments remain separate, no manufactured aggregate'};save(dst/'comparison.json',out);print(json.dumps(out))
if __name__=='__main__':main()
