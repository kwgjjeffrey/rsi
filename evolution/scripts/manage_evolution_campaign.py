"""One frozen Sprint per campaign; Fibonacci selects cases in successive Rounds."""
import argparse,copy,fcntl,hashlib,json,os,shutil,subprocess,sys
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

def round_directory(root,item):return root/f'sprints/{item["sprint"]}/rounds/{item["round"]:03d}'

def prepare(root,project,state,timeout):
    if state['active']:raise ValueError('Assess the active window before preparing another')
    for name in ['analysis.md','improvement-plan.md']:
        if not(root/f'blueprint/{name}').is_file()or not(root/f'blueprint/{name}').read_text().strip():raise ValueError('Write actual problem analysis and improvement plan before preparing a window')
    for case in state['case_order']:
        file=root/f'datasets/{state["dataset"]}/cases/{case}/record.json'
        if digest(file)!=state['dataset_hashes'][case]:raise ValueError('Frozen question changed; create a new dataset version and Sprint')
    final_repairs=state['outstanding_cases']if state['cursor']>=len(state['case_order'])else[]
    repair=bool(state['repair_cases']or final_repairs)
    cases=state['repair_cases']or final_repairs or state['case_order'][state['cursor']:state['cursor']+size_at(state['fibonacci_index'])]
    if not cases:return None
    sprint=state['sprint'];directory=root/'sprints'/sprint
    repo=Path(project['repo']);revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    if not directory.exists():
        dataset,version=state['dataset'].split('/')
        dispatch(root,{'op':'create-sprint','project':project['id'],'sprint':sprint,'dataset':dataset,'version':version,'source':{'revision':revision,'kind':'fibonacci_campaign'},'budget':{'case_timeout_seconds':timeout}})
        (directory/'rounds/000/reflection.md').write_text('Frozen question library. Pending references are not measured results.\n')
    number=len(state['history'])+1;round_dir=directory/f'rounds/{number:03d}'
    if round_dir.exists():raise ValueError('Round already exists; inspect an interrupted prepare before retrying')
    round_dir.mkdir()
    try:
        # Round-local analysis is frozen before execution; grading remains Sprint-frozen.
        shutil.copytree(root/'blueprint',round_dir/'snapshots/blueprint')
        selection={'sprint':sprint,'round':number,'cases':cases,'repair':repair,'source':revision,'batch_size':len(cases),'fibonacci_index':state['fibonacci_index']}
        save(round_dir/'selection.json',selection)
        (round_dir/'plan.md').write_text('# Round '+str(number)+'\n\n'+('Repair existing cases'if repair else'Fibonacci sample')+': '+', '.join(cases)+'\n\n'+(root/'blueprint/improvement-plan.md').read_text())
    except BaseException:
        shutil.rmtree(round_dir);raise
    return selection

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['init','status','prepare','run','assess','migrate']);p.add_argument('--project-root',type=Path,required=True);p.add_argument('--campaign',required=True);p.add_argument('--sprint');p.add_argument('--title');p.add_argument('--dataset');p.add_argument('--version');p.add_argument('--timeout',type=int,default=600);a=p.parse_args()
    root=a.project_root.resolve();project=load(root/'project.json');campaign=identifier(a.campaign,'campaign');state_path=root/f'blueprint/campaigns/{campaign}.json';state_path.parent.mkdir(parents=True,exist_ok=True)
    with state_path.with_suffix('.lock').open('a')as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if a.action=='init':
            if state_path.exists():raise ValueError('Campaign already exists')
            dataset=identifier(a.dataset,'dataset');version=identifier(a.version,'version');files=sorted((root/f'datasets/{dataset}/{version}/cases').glob('*/record.json'))
            if not files:raise ValueError('Freeze a nonempty annotated question library first')
            records=[validate_record(load(f))for f in files]
            state={'schema_version':2,'campaign':campaign,'sprint':identifier(a.sprint or campaign,'sprint'),'title':a.title or campaign.replace('_',' '),'dataset':dataset+'/'+version,'case_order':[r['case_id']for r in records],'dataset_hashes':{r['case_id']:digest(f)for r,f in zip(records,files)},'cursor':0,'fibonacci_index':0,'active':None,'repair_cases':[],'outstanding_cases':[],'history':[]};save(state_path,state)
        state=load(state_path)
        if a.action=='migrate':
            from migrate_campaign_rounds import migrate
            print(json.dumps(migrate(root,project,state,state_path,a.sprint or campaign,a.title),ensure_ascii=False));return
        if a.action in ['init','status']:
            print(json.dumps({'campaign':campaign,'sprint':state.get('sprint'),'questions':len(state['case_order']),'next_round':len(state['history'])+1,'next_window_size':size_at(state['fibonacci_index']),'active':state['active'],'repair_cases':state['repair_cases'],'state':str(state_path)},ensure_ascii=False));return
        if state.get('schema_version')!=2:raise ValueError('Legacy per-window Sprints: run migrate before continuing')
        if a.action=='prepare':
            selection=prepare(root,project,state,a.timeout)
            if selection:state['active']=selection;save(state_path,state)
            print(json.dumps(selection or {'decision':'finished','questions':state['cursor']},ensure_ascii=False));return
        active=state['active']
        if not active:raise ValueError('No active window')
        round_dir=round_directory(root,active)
        if a.action=='run':
            subprocess.run([sys.executable,str(SKILL/'evolution/scripts/manage_evolution_round.py'),'replay','--project-root',str(root),'--sprint',active['sprint'],'--round',str(active['round']),'--adapter',str(root/'blueprint/replay.json'),'--timeout',str(a.timeout)],check=True);return
        if not(round_dir/'reflection.md').is_file()or not(round_dir/'reflection.md').read_text().strip():raise ValueError('Write the observed common causes and next changes in round reflection.md before expansion')
        records=[load(round_dir/f'cases/{case}/record.json')for case in active['cases']]
        decision=assess(records,load(round_dir.parent.parent/'snapshots/blueprint/evaluation.json'),repair=active['repair']);save(round_dir/'expansion-decision.json',decision)
        state['outstanding_cases']=outstanding(state['outstanding_cases'],decision['outcomes']);state['repair_cases']=state['outstanding_cases']if decision['decision']!='expand'else[]
        if not active['repair']:state['cursor']+=len(active['cases']);state['fibonacci_index']+=1
        state['history'].append({**active,**decision});state['active']=None;save(state_path,state);print(json.dumps(decision,ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError)as error:print(str(error),file=sys.stderr);sys.exit(1)
