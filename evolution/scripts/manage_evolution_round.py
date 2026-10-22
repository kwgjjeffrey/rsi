#!/usr/bin/env python3
"""Create immutable replay records and compare annotated rounds; never simulate agent evaluation."""
import argparse,json,os,subprocess,time,hashlib
from pathlib import Path

def load(p): return json.loads(p.read_text())
def save(p,v): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['replay','compare']);p.add_argument('--project-root',type=Path,required=True);p.add_argument('--sprint',required=True);p.add_argument('--round',type=int,required=True);p.add_argument('--adapter',type=Path);p.add_argument('--timeout',type=int,default=600);a=p.parse_args()
 if not a.sprint or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in a.sprint):p.error('invalid sprint')
 if a.round<1:p.error('round must be >=1')
 root=a.project_root.resolve();s=root/'sprints'/a.sprint;baseline=s/'rounds/000';dst=s/'rounds'/f'{a.round:03d}'
 cases=sorted((baseline/'cases').glob('*/record.json'))
 if not cases:p.error('baseline contains no cases')
 if a.action=='replay':
  if not a.adapter:p.error('--adapter required')
  config=load(a.adapter);cmd=config.get('command');
  if not isinstance(cmd,list) or not cmd or not all(isinstance(x,str) for x in cmd):p.error('adapter.command must be argv array')
  if config.get('fresh_session') is not True:p.error('adapter must declare fresh_session=true; verify harness behavior separately')
  if not (dst/'plan.md').is_file():p.error('write round plan.md before replay')
  repo=Path(load(root/'project.json')['repo']);revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip();patch=subprocess.check_output(['git','diff','HEAD','--binary'],cwd=repo);status=subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True)
  if '?? ' in status:p.error('untracked source files: record/commit them before replay')
  if (dst/'round.json').exists():p.error('round already executed; use a new round')
  (dst/'changes.patch').write_bytes(patch);save(dst/'round.json',{'status':'running','revision':revision,'patch_sha256':hashlib.sha256(patch).hexdigest(),'adapter':config,'started_at':time.time()})
  for file in cases:
   original=load(file);case=original['case_id'];request={'schema_version':1,'case_id':case,'task_input':original['task_input'],'source':{'repo':str(repo),'revision':revision,'patch_sha256':hashlib.sha256(patch).hexdigest()},'fresh_session':True}
   start=time.monotonic();error=None;result={}
   try:
    run=subprocess.run(cmd,input=json.dumps(request),capture_output=True,text=True,timeout=a.timeout,cwd=repo)
    if run.returncode:error=f'adapter exit {run.returncode}'
    else:
     result=json.loads(run.stdout)
     if not isinstance(result.get('trajectory'),list) or not result.get('session_id') or not result.get('loaded_skill_digest'):error='adapter missing trajectory/session_id/loaded_skill_digest'
   except (subprocess.TimeoutExpired,OSError,ValueError) as e:error=str(e)
   record={'schema_version':1,'case_id':case,'record_id':f'{a.sprint}_r{a.round}_{case}','initial_record_id':original['record_id'],'task_input':original['task_input'],'trajectory':result.get('trajectory',[]),'annotation':{'status':'pending','criteria':original['annotation'].get('criteria',[])},'reflection':'','execution':{'status':'error' if error else 'completed','error':error,'seconds':time.monotonic()-start,'session_id':result.get('session_id'),'loaded_skill_digest':result.get('loaded_skill_digest')}}
   save(dst/'cases'/case/'record.json',record)
  meta=load(dst/'round.json');meta['status']='awaiting_annotation';save(dst/'round.json',meta);print(json.dumps(meta));return
 def score(r):
  annotation=r['annotation']
  if annotation.get('status')!='completed':return None
  n=annotation.get('score')
  if isinstance(n,bool) or not isinstance(n,(int,float)) or not 0<=n<=100:raise ValueError('completed annotation requires score 0..100')
  if not annotation.get('rubric_version'):raise ValueError('rubric_version required')
  if not r.get('reflection'):raise ValueError('case reflection required')
  if r.get('execution',{}).get('status')=='error':return None
  return n
 groups={'improved':[],'regressed':[],'unchanged':[],'incomparable':[]};pairs=[]
 for file in cases:
  old=load(file);newpath=dst/'cases'/old['case_id']/'record.json'
  if not newpath.exists():groups['incomparable'].append(old['case_id']);continue
  new=load(newpath);x,y=score(old),score(new)
  compatible=old['task_input']==new['task_input'] and old['annotation'].get('rubric_version')==new['annotation'].get('rubric_version') and old['annotation'].get('criteria')==new['annotation'].get('criteria')
  if x is None or y is None or not compatible:groups['incomparable'].append(old['case_id']);continue
  pairs.append((x,y));groups['improved' if y>x else 'regressed' if y<x else 'unchanged'].append(old['case_id'])
 out={'groups':groups,'total':len(cases),'comparable':len(pairs),'baseline_mean':sum(x for x,y in pairs)/len(pairs) if pairs else None,'round_mean':sum(y for x,y in pairs)/len(pairs) if pairs else None,'comparison_scope':'paired comparable cases only'};save(dst/'comparison.json',out);print(json.dumps(out))
if __name__=='__main__':main()
