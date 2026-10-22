"""Offline teacher-declared annotation integrity; never auto-completes human labels."""
from collections import Counter
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re

from scripts.prepare_teacher_baseline import digest, INTENTS

ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$')
SHA = re.compile(r'^[a-f0-9]{64}$')
ACTIONS = {'explain', 'locate_error', 'check_reasoning', 'next_step', 'pseudocode', 'trace', 'ask_context', 'limited_evidence'}
ANSWERABILITY = {'supported', 'needs_context', 'no_course_evidence', 'out_of_scope'}
MAX_FILE_BYTES = 8 * 1024 * 1024


class ContractError(ValueError):
    pass


def _require(condition, message):
    if not condition:
        raise ContractError(message)


def _text(value, max_length=1000):
    return isinstance(value, str) and 0 < len(value.strip()) <= max_length


def _id(value):
    return isinstance(value, str) and ID.fullmatch(value) is not None


def _sha(value):
    return isinstance(value, str) and SHA.fullmatch(value) is not None


def _unique(rows, field, name):
    _require(isinstance(rows, list), name+' must be an array')
    result = {}
    for row in rows:
        _require(isinstance(row, dict) and _id(row.get(field)), name+' has invalid '+field)
        _require(row[field] not in result, name+' has duplicate '+field)
        result[row[field]] = row
    return result


def read_json(path, *, max_bytes=MAX_FILE_BYTES):
    # Teacher input stays capped at 8 MiB; comparison packs repeat approved
    # passages across arms and may explicitly request a larger bounded read.
    _require(type(max_bytes) is int and 0 < max_bytes <= 64 * 1024 * 1024, 'Invalid JSON size limit')
    path = Path(path)
    _require(path.stat().st_size <= max_bytes, f'JSON file exceeds {max_bytes // (1024 * 1024)} MiB')
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, 'Duplicate JSON object key')
            result[key] = value
        return result
    value = json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=pairs,
                       parse_constant=lambda value: (_ for _ in ()).throw(ContractError('Non-finite JSON number')))
    _require(isinstance(value, dict), 'JSON root must be an object')
    return value


def validate(cases, corpus, annotations):
    for item in (cases, corpus, annotations):
        _require(isinstance(item, dict), 'Case pack, corpus and annotations must be objects')
        _require(type(item.get('schema_version')) is int and item['schema_version'] == 1, 'Unsupported schema version')
    _require(_id(cases.get('dataset_id')), 'Invalid dataset id')
    _require(cases.get('status') == 'unreviewed_draft' and cases.get('label_source') == 'none', 'Input must remain an unreviewed draft')
    case_map = _unique(cases.get('cases'), 'id', 'cases')
    _require(len(case_map) == 120, 'This baseline requires 120 reviewed candidate cases; rejected cases remain documented')
    families, concepts, queries = {}, {}, set()
    for c in case_map.values():
        _require(_id(c.get('family_id')) and _id(c.get('proposed_concept_id')), 'Invalid case family or concept')
        _require(c.get('split') in ('development', 'test'), 'Invalid case split')
        _require(c.get('origin') == 'agent_authored_synthetic_draft', 'Do not relabel synthetic prompts as real student records')
        _require(c.get('execution_verified') is False, 'Draft pack cannot declare execution verification')
        _require(c.get('proposed_intent') in (*INTENTS, None), 'Invalid proposed intent')
        _require(c.get('boundary') in ('normal', 'missing_course_evidence', 'context_mismatch'), 'Invalid boundary')
        _require(_text(c.get('query'), 12000), 'Invalid query')
        _require(c.get('code') is None or _text(c['code'], 12000), 'Invalid code')
        _require(c.get('task_context') is None or isinstance(c['task_context'], dict), 'Invalid context')
        key = ' '.join(c['query'].split())
        _require(key not in queries, 'Duplicate query text; cases cannot be padded with exact copies')
        queries.add(key)
        for grouping, value in ((families,c['family_id']), (concepts,c['proposed_concept_id'])):
            _require(value not in grouping or grouping[value] == c['split'], 'Family/concept crosses development and test splits')
            grouping[value] = c['split']
    _require(set(families.values()) == {'development','test'}, 'Both splits are required')
    _require(annotations.get('dataset_sha256') == digest(cases), 'Cases changed after review template was prepared')
    reviews = _unique(annotations.get('reviews'), 'case_id', 'reviews')
    _require(set(reviews) == set(case_map), 'Every case needs exactly one review record, with no unknown case')
    reviewers = _unique(annotations.get('reviewers'), 'id', 'reviewers')
    for reviewer in reviewers.values():
        _require(reviewer.get('declares_python_teaching_experience') is True
                 and reviewer.get('declares_personal_review') is True,
                 'Reviewer must explicitly declare teaching experience and personal review')
    documents = _unique(corpus.get('documents'), 'id', 'documents')
    _require(len(documents) <= 1000, 'Too many corpus documents')
    for d in documents.values():
        _require(type(d.get('version')) is int and d['version'] > 0, 'Invalid document version')
        _require(_text(d.get('title'), 300) and _text(d.get('content'), 200000), 'Invalid course document text')
        _require(_text(d.get('source_reference'), 1000), 'Course document requires its source reference')
        _require(d.get('approved_for_evaluation') is True, 'Only materials approved for evaluation may be included')
        d_hash = hashlib.sha256(d['content'].encode('utf-8')).hexdigest()
        _require(d.get('content_sha256') == d_hash, 'Course document content hash mismatch')
    pending, rejected, accepted = [], [], []
    coverage = {split:Counter() for split in ('development','test')}
    boundaries = {split:Counter() for split in ('development','test')}
    now = datetime.now(timezone.utc)
    for cid, review in reviews.items():
        _require(review.get('case_sha256') == digest(case_map[cid]), 'Case hash mismatch: '+cid)
        if review.get('accepted') is None:
            pending.append(cid)
            continue
        _require(type(review.get('accepted')) is bool, 'accepted must be a boolean or null: '+cid)
        _require(_id(review.get('reviewer_id')) and review['reviewer_id'] in reviewers, 'Missing declared reviewer: '+cid)
        _require(_text(review.get('rationale'), 3000), 'Missing review rationale: '+cid)
        try:
            reviewed_at = datetime.fromisoformat(review.get('reviewed_at', '').replace('Z','+00:00'))
        except (ValueError, AttributeError, TypeError):
            raise ContractError('Invalid review timestamp: '+cid) from None
        _require(reviewed_at.tzinfo is not None and reviewed_at <= now + timedelta(minutes=5), 'Review timestamp must be timezone-aware and not in the future: '+cid)
        if not review['accepted']:
            rejected.append(cid)
            continue
        _require(review.get('gold_intent') in (*INTENTS, 'needs_context', 'out_of_scope'), 'Invalid gold intent: '+cid)
        _require(isinstance(review.get('answerability'),str) and review['answerability'] in ANSWERABILITY, 'Invalid answerability: '+cid)
        _require(isinstance(review.get('expected_action'),str) and review['expected_action'] in ACTIONS, 'Invalid expected teaching action: '+cid)
        points = review.get('expected_response_points')
        _require(isinstance(points,list) and 1 <= len(points) <= 12 and all(_text(p,1500) for p in points), 'Teacher response points required: '+cid)
        evidence = review.get('evidence')
        _require(isinstance(evidence,list) and len(evidence) <= 20, 'Evidence must be an array of at most 20 items: '+cid)
        seen = set()
        for source in evidence:
            _require(isinstance(source,dict) and _id(source.get('document_id')) and source['document_id'] in documents, 'Unknown evidence source: '+cid)
            d = documents[source['document_id']]
            _require(d['id'] not in seen, 'Duplicate evidence source: '+cid)
            seen.add(d['id'])
            _require(type(source.get('version')) is int and source['version'] == d['version']
                and _sha(source.get('content_sha256')) and source['content_sha256'] == d['content_sha256'], 'Stale evidence version or hash: '+cid)
            _require(type(source.get('relevance')) is int and source['relevance'] in (1,2,3), 'Relevance must be integer 1, 2 or 3: '+cid)
        if review['answerability'] == 'supported':
            _require(evidence, 'Supported answers require reviewed course evidence: '+cid)
        if review['answerability'] == 'needs_context':
            _require(review['expected_action'] == 'ask_context', 'Missing context requires a clarification action: '+cid)
        if review['answerability'] in ('no_course_evidence', 'out_of_scope'):
            _require(review['expected_action'] in ('limited_evidence','ask_context'), 'Unsupported claims need a limited-evidence/clarification response: '+cid)
        accepted.append(cid)
        split = case_map[cid]['split']
        coverage[split][review['gold_intent']] += 1
        boundaries[split][case_map[cid]['boundary']] += 1
    gaps = {split:{'intents':[i for i in INTENTS if not coverage[split][i]],
                   'boundaries':[b for b in ('missing_course_evidence','context_mismatch') if not boundaries[split][b]]}
            for split in coverage}
    ready = not pending and all(not g['intents'] and not g['boundaries'] for g in gaps.values())
    return {'schema_valid':True, 'ready_to_freeze':ready, 'cases':len(case_map),
        'reviewed':len(accepted)+len(rejected), 'accepted':len(accepted), 'rejected':len(rejected),
        'pending':len(pending), 'pending_case_ids':pending, 'accepted_case_ids':accepted,
        'coverage':{k:dict(v) for k,v in coverage.items()}, 'coverage_gaps':gaps,
        'declared_reviewers':len(reviewers), 'reviewer_identity_verified_by_tool':False,
        'dataset_sha256':digest(cases), 'corpus_sha256':digest(corpus), 'annotations_sha256':digest(annotations)}


def freeze(cases, corpus, annotations, destination):
    report = validate(cases, corpus, annotations)
    _require(report['ready_to_freeze'], 'Human review is incomplete or coverage is insufficient; no frozen artifact written')
    artifact = {'schema_version':1, 'dataset_id':cases['dataset_id'], 'status':'frozen_teacher_declared_review',
        'label_source':'human review declared by supplied reviewers; identity not authenticated by this offline tool',
        'prompt_origin':'agent-authored synthetic cases, not real student records',
        'frozen_at':datetime.now(timezone.utc).isoformat(), 'case_pack':cases, 'corpus':corpus,
        'annotations':annotations, 'validation':report}
    checksum = digest(artifact)
    artifact['artifact_sha256'] = checksum
    destination = Path(destination)
    _require(not destination.exists(), 'Frozen destination already exists; choose a new version instead of overwriting')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(artifact, ensure_ascii=False, indent=2)+'\n')
    return {'path':str(destination), 'artifact_sha256':checksum, 'accepted':report['accepted'],
            'rejected':report['rejected'], 'identity_verified':False}


def verify_frozen(artifact):
    _require(artifact.get('status') == 'frozen_teacher_declared_review', 'Not a frozen teacher-declared dataset')
    signed = {k:v for k,v in artifact.items() if k != 'artifact_sha256'}
    _require(_sha(artifact.get('artifact_sha256')) and digest(signed) == artifact['artifact_sha256'], 'Frozen artifact has changed')
    report = validate(artifact['case_pack'], artifact['corpus'], artifact['annotations'])
    _require(report['ready_to_freeze'] and report == artifact.get('validation'), 'Frozen review contract no longer validates')
    return report
