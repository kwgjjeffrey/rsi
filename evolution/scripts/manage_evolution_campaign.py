"""Bound independent replay to Fibonacci windows; no automatic grading or edits."""
import argparse,copy,fcntl,hashlib,json,os,subprocess,sys
from pathlib import Path

SKILL=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(SKILL/'normalize/scripts'))
from validate_normalization_records import identifier,judgment_results,validate_record

def size_at(index):
    a,b=1,2
    for _ in range(index):a,b=b,a+b
    return a

def qualify(record,evaluation):
    annotation=record.get('annotation',{})
    try:validate_record(record)
    except ValueError:return 'incomplete'
    if record.get('execution',{}).get('status')!='completed' or annotation.get('status')!='completed' or not record.get('reflection','').strip():return 'incomplete'
    mode=evaluation.get('qualification',{}).get('mode','all_criteria')
    if mode=='numeric':
        score=annotation.get('score');threshold=evaluation.get('pass_threshold')
        if any(isinstance(x,bool)or not isinstance(x,(int,float))or not 0<=x<=100 for x in [score,threshold]):return 'incomplete'
        return 'qualified'if score>=threshold else'unqualified'
    if mode!='all_criteria':return 'incomplete'
    try:values=judgment_results(record)
    except ValueError:return 'incomplete'
    if any(not(j.get('reason')or j.get('explanation'))or not j.get('evidence')for j in annotation['judgments']):return 'incomplete'
    result='qualified'if all(v=='passed'for v in values.values())else'unqualified'
    if annotation.get('outcome')not in [None,'passed'if result=='qualified'else'failed']:return 'incomplete'
    return result

def assess(records,evaluation,repair=False):
    if not records:raise ValueError('No measured records')
    outcomes={r['case_id']:qualify(r,evaluation)for r in records}
    if len(outcomes)!=len(records):raise ValueError('Duplicate case IDs')
    incomplete=[k for k,v in outcomes.items()if v=='incomplete'];bad=[k for k,v in outcomes.items()if v=='unqualified']
    decision='hold_execution'if incomplete else'repair'if(repair and bad)or len(bad)*2>len(records)else'expand'
    return {'decision':decision,'total':len(records),'outcomes':outcomes,'unqualified':bad,'incomplete':incomplete,'unqualified_rate':len(bad)/len(records)if not incomplete else None,'threshold':'strictly >50%; unresolved executions/evaluation hold separately'}

def outstanding(previous,outcomes):
    values=set(previous)
    for key,result in outcomes.items():
        if result=='qualified':values.discard(key)
        else:values.add(key)
    return sorted(values)

def load(path):return json.loads(path.read_text())
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');os.replace(temp,path)
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def dispatch(root,request):
    if root.parent.name!='projects':raise ValueError('Expected registered RSI data/projects/<project> root')
    file=root/'normalize/requests/campaign-dispatch.json';save(file,request)
    result=subprocess.check_output([str(SKILL/'local-runtime/bin/rsi-runtime'),'dispatch',str(file)],env={**os.environ,'RSI_DATA_DIR':str(root.parents[1])},text=True)
    return json.loads(result)

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['init','status','prepare','run','assess']);p.add_argument('--project-root',type=Path,required=True);p.add_argument('--campaign',required=True);p.add_argument('--dataset');p.add_argument('--version');p.add_argument('--timeout',type=int,default=600);a=p.parse_args()
    root=a.project_root.resolve();project=load(root/'project.json');campaign=identifier(a.campaign,'campaign');state_path=root/f'blueprint/campaigns/{campaign}.json';state_path.parent.mkdir(parents=True,exist_ok=True)
    with state_path.with_suffix('.lock').open('a')as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if a.action=='init':
            if state_path.exists():raise ValueError('Campaign already exists')
            dataset=identifier(a.dataset,'dataset');version=identifier(a.version,'version');files=sorted((root/f'datasets/{dataset}/{version}/cases').glob('*/record.json'))
            if not files:raise ValueError('Freeze a nonempty annotated question library first')
            records=[validate_record(load(f))for f in files]
            state={'campaign':campaign,'dataset':dataset+'/'+version,'case_order':[r['case_id']for r in records],'dataset_hashes':{r['case_id']:digest(f)for r,f in zip(records,files)},'cursor':0,'fibonacci_index':0,'active':None,'repair_cases':[],'outstanding_cases':[],'history':[]};save(state_path,state)
        state=load(state_path)
        if a.action in ['init','status']:
            print(json.dumps({'campaign':campaign,'questions':len(state['case_order']),'next_window_size':size_at(state['fibonacci_index']),'active':state['active'],'repair_cases':state['repair_cases'],'state':str(state_path)},ensure_ascii=False));return
        if a.action=='prepare':
            if state['active']:raise ValueError('Assess the active window before preparing another')
            for name in ['analysis.md','improvement-plan.md']:
                if not(root/f'blueprint/{name}').is_file()or not(root/f'blueprint/{name}').read_text().strip():raise ValueError('Write actual problem analysis and improvement plan before preparing a window')
            final_repairs=state['outstanding_cases'] if state['cursor']>=len(state['case_order']) else []
            repair=bool(state['repair_cases']or final_repairs);cases=state['repair_cases']or final_repairs or state['case_order'][state['cursor']:state['cursor']+size_at(state['fibonacci_index'])]
            if not cases:print(json.dumps({'decision':'finished','questions':state['cursor']}));return
            records=[]
            for case in cases:
                file=root/f'datasets/{state["dataset"]}/cases/{case}/record.json'
                if digest(file)!=state['dataset_hashes'][case]:raise ValueError('Frozen question changed; create a new dataset version')
                original=load(file);record=copy.deepcopy(original)
                if repair:
                    previous=next(x for x in reversed(state['history'])if case in x['cases']);last=load(root/f'sprints/{previous["sprint"]}/rounds/001/cases/{case}/record.json')
                    if last['task_input']!=original['task_input']or last['annotation'].get('criteria')!=original['annotation'].get('criteria'):raise ValueError('Repair cannot change question or criteria')
                    record.update(last);record['annotation']={**original['annotation'],**last['annotation']}
                records.append(record)
            index=len(state['history'])+1;version=f'{campaign}_{index:03}';sprint=f'{campaign}_{index:03}';repo=Path(project['repo']);revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
            dispatch(root,{'op':'import','project':project['id'],'dataset':'campaign_windows','version':version,'records':records})
            result=dispatch(root,{'op':'create-sprint','project':project['id'],'sprint':sprint,'dataset':'campaign_windows','version':version,'source':{'revision':revision,'kind':'repair_existing_cases'if repair else'fibonacci_sample'},'budget':{'max_rounds':1,'case_timeout_seconds':a.timeout}})
            directory=Path(result['path']);(directory/'rounds/000/reflection.md').write_text('Actual previous records retained as repair baseline.'if repair else'Pre-execution references, not observed outcomes.')
            round_dir=directory/'rounds/001';round_dir.mkdir();plan=(root/'blueprint/improvement-plan.md').read_text();(round_dir/'plan.md').write_text('# Window '+str(index)+'\n\nCases: '+', '.join(cases)+'\n\nFrozen analysis: [analysis](sprints/'+sprint+'/snapshots/blueprint/analysis.md)\n\n'+plan)
            state['active']={'sprint':sprint,'cases':cases,'repair':repair,'source':revision,'batch_size':len(cases)};save(state_path,state);print(json.dumps(state['active'],ensure_ascii=False));return
        active=state['active']
        if not active:raise ValueError('No active window')
        if a.action=='run':
            subprocess.run([sys.executable,str(SKILL/'evolution/scripts/manage_evolution_round.py'),'replay','--project-root',str(root),'--sprint',active['sprint'],'--round','1','--adapter',str(root/'blueprint/replay.json'),'--timeout',str(a.timeout)],check=True);return
        round_dir=root/f'sprints/{active["sprint"]}/rounds/001'
        if not(round_dir/'reflection.md').is_file()or not(round_dir/'reflection.md').read_text().strip():raise ValueError('Write the observed common causes and next changes in round reflection.md before expansion')
        records=[load(round_dir/f'cases/{case}/record.json')for case in active['cases']];decision=assess(records,load(round_dir.parent.parent/'snapshots/blueprint/evaluation.json'),repair=active['repair']);save(round_dir/'expansion-decision.json',decision)
        state['outstanding_cases']=outstanding(state['outstanding_cases'],decision['outcomes']);state['repair_cases']=state['outstanding_cases']if decision['decision']!='expand'else[]
        if not active['repair']:state['cursor']+=len(active['cases']);state['fibonacci_index']+=1
        state['history'].append({**active,**decision});state['active']=None;save(state_path,state);print(json.dumps(decision,ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError)as error:print(str(error),file=sys.stderr);sys.exit(1)
