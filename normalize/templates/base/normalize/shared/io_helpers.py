"""Project-local protocol I/O and artifact path boundaries; Python standard library only."""
import json
from pathlib import Path
import sys

def read_request():
    request = json.load(sys.stdin)
    if request.get('protocol_version') != 1:
        raise ValueError('expected normalization protocol_version=1')
    return request

def emit(value):
    print(json.dumps(value, ensure_ascii=False))

def project_path(request, relative):
    root = Path(request['project_root']).resolve()
    path = Path(relative)
    path = (root / path).resolve() if not path.is_absolute() else path.resolve()
    if not path.is_relative_to(root):
        raise ValueError('artifact path must stay inside this RSI project directory')
    return path
