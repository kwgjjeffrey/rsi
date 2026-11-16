"""Versioned normalization contract; no knowledge of a target project's layout."""
import copy
import json
import re

IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]+$")

def identifier(value, label):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError(label + ' must contain only letters, digits, _ or -')
    return value

def validate_record(record):
    if not isinstance(record, dict):
        raise ValueError('case record must be an object')
    if record.get('schema_version', 1) != 1:
        raise ValueError('unsupported case schema_version')
    for key in ('case_id', 'record_id'):
        identifier(record.get(key), key)
    if record.get('task_input') is None:
        raise ValueError('task_input is required')
    if not isinstance(record.get('trajectory'), list):
        raise ValueError('trajectory must be an array')
    if not all(isinstance(event, dict) for event in record['trajectory']):
        raise ValueError('trajectory events must be objects; wrap raw source fragments')
    annotation = record.get('annotation')
    if not isinstance(annotation, dict) or annotation.get('status') not in ('pending', 'unknown', 'completed'):
        raise ValueError('annotation.status must be pending, unknown or completed')
    if not isinstance(record.get('reflection'), str):
        raise ValueError('reflection must be a string')
    if annotation['status'] == 'completed':
        number = annotation.get('score')
        if isinstance(number, bool) or not isinstance(number, (int, float)) or not 0 <= number <= 100:
            raise ValueError('completed annotation requires score 0..100')
        if not annotation.get('rubric_version') or not record['reflection'].strip():
            raise ValueError('completed annotation requires rubric_version and reflection')
    if annotation.get('outcome') is not None and annotation['outcome'] not in ('passed', 'failed'):
        raise ValueError('annotation.outcome must be passed or failed')
    return record

def validate_cases(value):
    if not isinstance(value, dict) or not isinstance(value.get('records'), list) or not value['records']:
        raise ValueError('cases adapter must return a nonempty records array')
    seen = set()
    for record in value['records']:
        validate_record(record)
        if record['case_id'] in seen:
            raise ValueError('duplicate case_id')
        seen.add(record['case_id'])
    return value

def validate_result(value):
    if not isinstance(value, dict) or value.get('protocol_version') != 1:
        raise ValueError('results adapter must return protocol_version=1')
    if not isinstance(value.get('trajectory'), list) or not all(isinstance(e, dict) for e in value['trajectory']):
        raise ValueError('normalized result requires trajectory objects')
    execution = value.get('execution')
    if not isinstance(execution, dict) or execution.get('status') not in ('completed', 'error'):
        raise ValueError('normalized result requires execution.status completed or error')
    if execution['status'] == 'completed' and not all(execution.get(k) for k in ('session_id', 'loaded_skill_digest')):
        raise ValueError('completed replay requires actual session_id and skill digest')
    if execution['status'] == 'error' and not execution.get('error'):
        raise ValueError('failed replay requires an error explanation')
    if any(k in value for k in ('annotation', 'reflection', 'task_input')):
        raise ValueError('results adapters must not supply labels, reflection or task input')
    return value

def materialize_replay(original, normalized, record_id):
    validate_result(normalized)
    identifier(record_id, 'record_id')
    criteria = original.get('annotation', {})
    annotation = {'status': 'pending', 'criteria': copy.deepcopy(criteria.get('criteria', []))}
    if criteria.get('rubric_version'):
        annotation['rubric_version'] = criteria['rubric_version']
    result = {'schema_version': 1, 'case_id': original['case_id'], 'record_id': record_id,
              'initial_record_id': original['record_id'], 'task_input': copy.deepcopy(original['task_input']),
              'trajectory': normalized['trajectory'], 'annotation': annotation, 'reflection': '',
              'execution': normalized['execution']}
    return validate_record(result)
