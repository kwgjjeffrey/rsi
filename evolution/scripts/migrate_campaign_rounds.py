"""Consolidate legacy per-window Sprints without changing any measured case bytes."""
import copy,datetime,hashlib,json,shutil,subprocess,sys
from pathlib import Path
from manage_evolution_campaign import dispatch,load,save,identifier,digest

def migrate(root,project,state,state_path,sprint,title=None):
    sprint=identifier(sprint,'sprint')
    if state.get('schema_version')==2:return {'status':'already_consolidated','sprint':state['sprint']}
    if state.get('active'):raise ValueError('Finish or explicitly recover the active legacy window before migration')
    history=state.get('history',[])
    if not history:raise ValueError('No legacy history to consolidate')
    destination=root/'sprints'/sprint
    if destination.exists():raise ValueError('Destination Sprint exists; inspect a prior migration')
    sources=[root/'sprints'/identifier(item['sprint'],'sprint')for item in history]
    if len(set(sources))!=len(sources):raise ValueError('History already shares Sprints; inspect the record structure')
    for case in state['case_order']:
        if digest(root/f'datasets/{state["dataset"]}/cases/{case}/record.json')!=state['dataset_hashes'][case]:raise ValueError('Frozen question changed')
    originals={str(path/'sprint.json'):(path/'sprint.json').read_bytes()for path in sources}
    case_hashes={}
    for index,(item,source)in enumerate(zip(history,sources),1):
        source_round=source/f'rounds/{item.get("round",1):03d}'
        actual={p.parent.name for p in(source_round/'cases').glob('*/record.json')}
        if actual!=set(item['cases']):raise ValueError('Legacy case selection differs from measured records')
        for file in(source_round/'cases').rglob('*'):
            if file.is_symlink():raise ValueError('Do not follow symlinks in measured evidence')
            if file.is_file():case_hashes[str(file)]=digest(file)
    backup=root/'runs/campaign-migrations'/f'{state["campaign"]}-{datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")}'
    backup.mkdir(parents=True)
    save(backup/'state-before.json',state);save(backup/'sprint-metadata-before.json',{key:json.loads(value)for key,value in originals.items()})
    created=False
    try:
        dataset,version=state['dataset'].split('/')
        dispatch(root,{'op':'create-sprint','project':project['id'],'sprint':sprint,'dataset':dataset,'version':version,'source':{'kind':'consolidated_existing_rounds'},'budget':{}});created=True
        meta=load(destination/'sprint.json');meta['title']=title or state.get('title')or project.get('name')or sprint.replace('_',' ');meta['campaign']=state['campaign'];save(destination/'sprint.json',meta)
        entries=[]
        for index,(item,source)in enumerate(zip(history,sources),1):
            old_number=item.get('round',1);old=source/f'rounds/{old_number:03d}';new=destination/f'rounds/{index:03d}'
            shutil.copytree(old,new)
            shutil.copytree(source/'snapshots/blueprint',new/'snapshots/blueprint')
            if(new/'comparison.json').exists():(new/'comparison.json').rename(new/'comparison-legacy.json')
            entry={**item,'legacy_sprint':item['sprint'],'legacy_round':old_number,'sprint':sprint,'round':index}
            selection={key:entry[key]for key in ['sprint','round','cases','repair','source','batch_size']};save(new/'selection.json',selection);save(new/'provenance.json',{'original_round':str(old.relative_to(root)),'cases_copied_without_changes':True})
            for file in(old/'cases').rglob('*'):
                if file.is_file()and digest(file)!=digest(new/'cases'/file.relative_to(old/'cases')):raise ValueError('Copied evidence differs')
            if not(new/'reflection.md').exists():(new/'reflection.md').write_text('Historical execution prerequisite failure; no business request was dispatched. Original evidence is retained.\n')
            subprocess.run([sys.executable,str(Path(__file__).with_name('manage_evolution_round.py')),'compare','--project-root',str(root),'--sprint',sprint,'--round',str(index),'--baseline-round','previous'],check=True,capture_output=True)
            entries.append(entry)
        migrated={**copy.deepcopy(state),'schema_version':2,'sprint':sprint,'history':entries}
        save(destination/'migration.json',{'kind':'legacy_sprints_to_rounds','backup':str(backup),'rounds':[{'round':e['round'],'from_sprint':e['legacy_sprint'],'cases':e['cases']}for e in entries],'original_case_file_sha256':case_hashes,'case_grades_and_trajectories_unchanged':True})
        for source in sources:
            value=load(source/'sprint.json');value['archived_into']=sprint;value['archive_reason']='Consolidated into successive Rounds of the same task; original evidence remains readable.';save(source/'sprint.json',value)
        save(state_path,migrated)
        return {'status':'consolidated','sprint':sprint,'rounds':len(entries),'measured_case_records':sum(len(e['cases'])for e in entries),'backup':str(backup)}
    except BaseException:
        for path,content in originals.items():Path(path).write_bytes(content)
        if created:shutil.rmtree(destination)
        raise
