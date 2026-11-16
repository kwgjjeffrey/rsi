#!/usr/bin/env python3
"""Initialize project-owned adapters, inspect readiness, or run a versioned stage."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

from validate_normalization_records import validate_cases, validate_result

SKILL = Path(__file__).resolve().parents[2]
STAGES = ('cases', 'replay', 'results')
PROFILES = ('instruction-tools', 'code-artifact', 'business-workflow')
HARNESSES = ('codex', 'app-server', 'cdp', 'custom')

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        temp = stream.name
    os.replace(temp, path)

def inside(root, relative):
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError('adapter entrypoint must be a project-relative path')
    path = (root / relative).resolve()
    boundary = root / 'normalize'
    if boundary.is_symlink() or not boundary.resolve().is_relative_to(root) or not path.is_relative_to(boundary):
        raise ValueError('adapter entrypoint must stay inside project normalize/')
    return path

def initialize(root, profile, harness):
    if not (root / 'project.json').is_file():
        raise ValueError('register the target project before initialization')
    manifest_path = root / 'normalize/manifest.json'
    if manifest_path.exists():
        existing = load(manifest_path)
        profile, harness = existing.get('profile', profile), existing.get('harness', harness)
        if profile not in PROFILES or harness not in HARNESSES:
            raise ValueError('existing manifest has an unsupported profile or harness')
    created, preserved = [], []
    def copy_tree(source, destination):
        for file in sorted(source.rglob('*')):
            if not file.is_file():
                continue
            target = destination / file.relative_to(source)
            relative = target.relative_to(root).as_posix()
            if not target.resolve().is_relative_to(root) or target.is_symlink():
                raise ValueError('refusing a template destination symlink or escaped path')
            if target.exists():
                preserved.append(relative)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(file.read_bytes())
            created.append(relative)
    copy_tree(SKILL / 'onboarding/templates/base/blueprint', root / 'blueprint')
    copy_tree(SKILL / 'normalize/templates/base/normalize', root / 'normalize')
    copy_tree(SKILL / 'normalize/templates/replay' / harness, root / 'normalize')
    profile_path = root / 'blueprint/scenario.md'
    if profile_path.exists():
        preserved.append('blueprint/scenario.md')
    else:
        profile_path.write_bytes((SKILL / 'onboarding/templates/profiles' / (profile + '.md')).read_bytes())
        created.append('blueprint/scenario.md')
    manifest = root / 'normalize/manifest.json'
    if manifest.is_symlink() or not manifest.resolve().is_relative_to(root): raise ValueError('manifest must remain inside project')
    if manifest.exists():
        preserved.append('normalize/manifest.json')
    else:
        save(manifest, {'protocol_version': 1, 'template_version': '1.0.0', 'profile': profile,
                        'harness': harness, 'stages': {
                            stage: {'runtime': 'node' if stage == 'replay' and harness == 'cdp' else 'python3',
                                    'entrypoint': 'normalize/' + stage + '/' + ('run_replay.mjs' if stage == 'replay' and harness == 'cdp' else {'cases':'normalize_cases.py','replay':'run_replay.py','results':'normalize_results.py'}[stage]),
                                    'status': 'needs_analysis'} for stage in STAGES}})
        created.append('normalize/manifest.json')
    return {'created': created, 'preserved': preserved, 'note': 'templates are not verified project capabilities; complete assessment.md and verify each stage'}

def fingerprint(root, config):
    import hashlib
    digest = hashlib.sha256(json.dumps(config, sort_keys=True).encode())
    files = [inside(root, config.get('entrypoint'))]
    files.extend(sorted((root / 'normalize/shared').rglob('*.py')))
    files.extend(inside(root, p) for p in config.get('dependencies', []))
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(root / 'normalize'):
            raise ValueError('adapter dependencies must remain inside normalize/')
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()

def inspect(root):
    manifest = load(root / 'normalize/manifest.json')
    if manifest.get('protocol_version') != 1:
        raise ValueError('unsupported normalization protocol')
    stages = {}
    for stage in STAGES:
        config = manifest.get('stages', {}).get(stage, {})
        try:
            path = inside(root, config.get('entrypoint'))
            entry_exists = path.is_file()
        except ValueError:
            entry_exists = False
        receipt = root / 'normalize/receipts' / (stage + '.json')
        evidence = load(receipt) if receipt.is_file() else {}
        try: current = fingerprint(root, config)
        except (ValueError, OSError): current = None
        stages[stage] = {'configured': config.get('status') == 'configured', 'entry_exists': entry_exists,
                         'contract_verified': evidence.get('status') == 'passed' and bool(current) and evidence.get('sha256') == current,
                         'last_verification': evidence.get('at'),
                         'note': 'a contract receipt does not prove task quality, actual isolation, or integration reachability'}
    return {'protocol_version': 1, 'profile': manifest.get('profile'), 'harness': manifest.get('harness'), 'stages': stages}

def invoke_stage(root, stage, request, timeout=600):
    manifest = load(root / 'normalize/manifest.json')
    if manifest.get('protocol_version') != 1:
        raise ValueError('unsupported normalization protocol')
    config = manifest['stages'][stage]
    if config.get('status') != 'configured':
        raise ValueError(stage + ': analyze the project and set this stage to configured before execution')
    runtime = config.get('runtime')
    if runtime not in ('python3', 'node'):
        raise ValueError('supported stage runtimes are python3 and node')
    entry = inside(root, config.get('entrypoint'))
    if not entry.is_file():
        raise ValueError('adapter entrypoint does not exist')
    request = dict(request, protocol_version=1, project_root=str(root))
    if stage == 'replay':
        forbidden = ('annotation', 'reflection', 'reference', 'gold_answer')
        if any(k in request for k in forbidden):
            raise ValueError('replay requests cannot contain evaluation or reflection context')
        repo = Path(load(root / 'project.json')['repo']).resolve()
        if Path(request.get('source', {}).get('repo', '')).resolve() != repo:
            raise ValueError('replay source must match the registered repository')
    proc = subprocess.Popen([runtime, str(entry)], cwd=root, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        out, err = proc.communicate(json.dumps(request), timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
        raise ValueError(stage + ': adapter timed out')
    if proc.returncode:
        # Adapter stderr may include private source data; never echo it into tool output.
        raise ValueError(stage + ': adapter failed (exit ' + str(proc.returncode) + '); inspect the project adapter locally')
    if len(out.encode('utf-8')) > 32_000_000:
        raise ValueError('adapter JSON output exceeds 32MB; return local artifact references')
    value = json.loads(out)
    if stage == 'cases':
        validate_cases(value)
    elif stage == 'results':
        validate_result(value)
    elif not isinstance(value, dict) or value.get('protocol_version') != 1 or value.get('status') not in ('completed', 'error'):
        raise ValueError('replay driver must return a raw result envelope with protocol_version=1 and status')
    # Protocol evidence is bound to entrypoint, shared helpers and manifest config.
    save(root / 'normalize/receipts' / (stage + '.json'), {'status':'passed', 'at':time.time(),
         'entrypoint': config['entrypoint'], 'sha256': fingerprint(root, config),
         'scope':'adapter protocol only; not evaluation quality or real-world correctness'})
    return value

def run_replay_pipeline(root, request, timeout=600):
    raw = invoke_stage(root, 'replay', request, timeout)
    run_dir = Path(request['run_dir']).resolve()
    if not run_dir.is_relative_to(root): raise ValueError('run_dir must stay inside RSI project')
    save(run_dir / 'raw-result.json', raw)
    result = invoke_stage(root, 'results', {'raw_result':raw, 'replay_request':request}, timeout)
    result['execution']['normalization_receipts'] = {stage: load(root / 'normalize/receipts' / (stage + '.json')) for stage in ('replay','results')}
    save(run_dir / 'normalized-result.json', result)
    return validate_result(result)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('initialize','inspect','run','validate'))
    parser.add_argument('--project-root', type=Path, required=True)
    parser.add_argument('--profile', choices=PROFILES, default='instruction-tools')
    parser.add_argument('--harness', choices=HARNESSES, default='custom')
    parser.add_argument('--stage', choices=STAGES)
    parser.add_argument('--request', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    root = args.project_root.resolve()
    try:
        if args.action == 'initialize':
            value = initialize(root, args.profile, args.harness)
        elif args.action == 'inspect':
            value = inspect(root)
        else:
            if not args.stage or not args.request:
                parser.error('--stage and --request are required')
            if args.timeout <= 0:
                parser.error('--timeout must be positive')
            request = load(args.request)
            if args.action == 'validate':
                if args.stage == 'cases': validate_cases(request)
                elif args.stage == 'results': validate_result(request)
                else: raise ValueError('validate supports cases or results; replay envelopes are checked during run')
                value = {'valid':True, 'stage':args.stage}
            else:
                if not args.output:
                    parser.error('--output is required for run; normalized private records are not printed')
                if not args.output.resolve().is_relative_to(root): raise ValueError('output must stay inside the project data directory')
                if args.output.exists():
                    raise ValueError('output exists; use a new path to preserve evidence')
                value = invoke_stage(root, args.stage, request, args.timeout)
                save(args.output, value)
                value = {'stage':args.stage,'output':str(args.output.resolve()),'contract_valid':True}
        print(json.dumps(value, ensure_ascii=False))
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as error:
        parser.exit(1, 'normalization: ' + str(error) + '\n')

if __name__ == '__main__':
    main()
