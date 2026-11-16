#!/usr/bin/env python3
"""Import already canonical JSON/JSONL; extend here for project data sources, not in RSI core."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'shared'))
from io_helpers import read_request, emit

request = read_request()
source = request.get('source', {})
if source.get('kind') != 'file':
    raise ValueError('this template only handles files; implement the project API/database/export adapter after assessment')
path = Path(source['path']).expanduser().resolve()
format_name = source.get('format', 'canonical-json')
if format_name == 'canonical-jsonl':
    records = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
elif format_name == 'canonical-json':
    value = json.loads(path.read_text(encoding='utf-8'))
    records = value if isinstance(value, list) else value.get('records', [value] if 'case_id' in value else [])
else:
    raise ValueError('unsupported source.format; map source fields in this project-owned adapter')
emit({'protocol_version': 1, 'records': records, 'source': {'kind': 'file', 'path': str(path)}})
