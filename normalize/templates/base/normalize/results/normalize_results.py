#!/usr/bin/env python3
"""Convert a project driver's raw Codex event envelope into canonical replay output."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'shared'))
from io_helpers import read_request, emit, project_path

request = read_request()
raw = request['raw_result']
if raw.get('protocol_version') != 1:
    raise ValueError('unsupported raw replay protocol')
if raw.get('status') == 'error':
    emit({'protocol_version':1, 'trajectory':[], 'execution':{'status':'error','error':raw.get('error','driver failed')}})
    sys.exit(0)
if raw.get('format') != 'codex-events-jsonl':
    raise ValueError('implement parsing for this project raw format; never assume another harness emits Codex events')
events = [json.loads(line) for line in project_path(request, raw['events_path']).read_text(encoding='utf-8').splitlines() if line.strip()]
session = next((event.get('thread_id') for event in events if event.get('type') == 'thread.started'), None)
turn_done = any(event.get('type') == 'turn.completed' for event in events)
execution = {'status':'completed' if turn_done else 'error', 'session_id':session,
             'loaded_skill_digest':raw.get('skill_digest'), 'isolation_evidence':raw.get('isolation_evidence'),
             'skill_load_evidence':{'verified':False,'scope':'source snapshot only; inspect trajectory to verify actual Skill loading'}}
if not turn_done:
    execution['error'] = 'Codex events do not include turn.completed'
emit({'protocol_version':1, 'trajectory':events, 'execution':execution})
