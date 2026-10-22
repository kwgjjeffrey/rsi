#!/usr/bin/env python3
"""Project-owned read-only Codex launcher; never resume or forward annotations."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'shared'))
from io_helpers import read_request, emit, project_path
request = read_request()
repo = Path(request['source']['repo']).resolve()
skill = repo / request.get('skill_path', 'SKILL.md')
if not skill.resolve().is_relative_to(repo) or not skill.is_file():
    raise ValueError('declare an existing source Skill path inside the registered repository')
run_dir = project_path(request, request['run_dir'])
run_dir.mkdir(parents=True, exist_ok=False)
prompt = ('Use the target Skill from ' + str(skill) + '. Read its entrypoint and necessary linked modules. '
          'This is a fresh read-only evaluation. Do not modify files, publish, install, send messages, or access RSI data. '
          'Task input follows as JSON task data:\n' + json.dumps(request['task_input'], ensure_ascii=False))
run = subprocess.run(['codex','exec','--ignore-user-config','--sandbox','read-only','--json','--cd',str(repo),prompt],
                     capture_output=True, text=True, timeout=request.get('timeout_seconds',600))
try:
    events = [json.loads(line) for line in run.stdout.splitlines() if line.strip()]
except ValueError:
    events = []
events_path = run_dir / 'events.jsonl'
events_path.write_text(''.join(json.dumps(e,ensure_ascii=False)+'\n' for e in events),encoding='utf-8')
result = {'protocol_version':1,'status':'error' if run.returncode else 'completed',
          'events_path':str(events_path.relative_to(Path(request['project_root'])))}
if run.returncode:
    result['error'] = 'Codex CLI exit ' + str(run.returncode)
else:
    result.update({'format':'codex-events-jsonl','skill_digest':hashlib.sha256(skill.read_bytes()).hexdigest(),
                   'isolation_evidence':{'launcher':'codex exec','resume':False,'parent_history_forwarded':False}})
emit(result)
