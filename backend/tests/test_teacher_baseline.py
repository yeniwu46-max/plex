"""Offline contract tests only; synthetic reviewers are never shipped as real labels."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import pytest

from scripts.prepare_teacher_baseline import build, prepare, digest, INTENTS
from scripts.teacher_baseline_contract import ContractError, read_json, validate, freeze, verify_frozen


def draft(tmp_path):
    prepare(tmp_path/'draft')
    return [read_json(tmp_path/'draft'/name) for name in ('cases.json','corpus.json','reviews.json')]


def filled_fixture(tmp_path):
    """Intentional synthetic declarations, confined to a test temporary directory."""
    cases, corpus, reviews = draft(tmp_path)
    content = 'Synthetic fixture, not a teacher-verified lesson.'
    sha = hashlib.sha256(content.encode()).hexdigest()
    corpus['documents'] = [{'id':'fixture-source','title':'Test-only source','version':1,'content':content,
        'content_sha256':sha,'source_reference':'synthetic test fixture','approved_for_evaluation':True}]
    reviews['reviewers'] = [{'id':'synthetic-test-reviewer','declares_python_teaching_experience':True,
                            'declares_personal_review':True}]
    for case, review in zip(cases['cases'],reviews['reviews']):
        supported = case['boundary']=='normal'
        review.update(reviewer_id='synthetic-test-reviewer',reviewed_at=datetime.now(timezone.utc).isoformat(),
            accepted=True,rationale='Synthetic contract fixture, not an actual human review.',
            gold_intent=case['proposed_intent'] or 'needs_context',
            answerability='supported' if supported else 'needs_context',
            expected_action='explain' if supported else 'ask_context', expected_response_points=['Synthetic assertion.'],
            evidence=[{'document_id':'fixture-source','version':1,'content_sha256':sha,'relevance':3}] if supported else [])
    return cases, corpus, reviews


def test_teacher_pack_has_120_unique_unreviewed_cases_and_family_disjoint_splits(tmp_path):
    cases, corpus, reviews = draft(tmp_path)
    assert len(cases['cases']) == 120 and corpus['documents']==[]
    assert sum(c['split']=='test' for c in cases['cases']) == 24
    assert {c['proposed_intent'] for c in cases['cases']} == {*INTENTS,None}
    assert all(c['execution_verified'] is False for c in cases['cases'])
    from app.data.knowledge_node_registry import resolve_node_id
    assert all(resolve_node_id(c['proposed_concept_id']) == c['proposed_concept_id'] for c in cases['cases'])
    report=validate(cases,corpus,reviews)
    assert report['schema_valid'] and not report['ready_to_freeze']
    assert report['reviewed']==0 and report['pending']==120 and report['declared_reviewers']==0
    assert all(r['accepted'] is None and not r['expected_response_points'] for r in reviews['reviews'])
    with pytest.raises(FileExistsError):prepare(tmp_path/'draft')


def test_teacher_pending_review_cannot_write_frozen_file(tmp_path):
    data=draft(tmp_path)
    destination=tmp_path/'frozen.json'
    with pytest.raises(ContractError,match='incomplete'):freeze(*data,destination)
    assert not destination.exists()


def test_teacher_freeze_roundtrip_immutable_and_provenance_remains_synthetic(tmp_path):
    data=filled_fixture(tmp_path)
    path=tmp_path/'frozen.json'
    result=freeze(*data,path)
    artifact=read_json(path)
    assert result['accepted']==120 and result['identity_verified'] is False
    assert artifact['prompt_origin']=='agent-authored synthetic cases, not real student records'
    assert verify_frozen(artifact)['ready_to_freeze']
    with pytest.raises(ContractError,match='already exists'):freeze(*data,path)
    artifact['case_pack']['cases'][0]['query']='tampered'
    with pytest.raises(ContractError,match='has changed'):verify_frozen(artifact)


@pytest.mark.parametrize('mutation', ['case','case_hash','duplicate_case','missing_review','duplicate_query','cross_family','cross_concept'])
def test_teacher_case_manifest_and_split_tampering_rejected(tmp_path,mutation):
    cases,corpus,reviews=filled_fixture(tmp_path)
    if mutation=='case':cases['cases'][0]['query']+=' changed'
    if mutation=='case_hash':reviews['reviews'][0]['case_sha256']='0'*64
    if mutation=='duplicate_case':cases['cases'][1]['id']=cases['cases'][0]['id']
    if mutation=='missing_review':reviews['reviews'].pop()
    if mutation=='duplicate_query':cases['cases'][1]['query']=cases['cases'][0]['query']
    if mutation=='cross_family':
        c=next(c for c in cases['cases'] if c['split']=='test');c['family_id']=cases['cases'][0]['family_id']
    if mutation=='cross_concept':
        c=next(c for c in cases['cases'] if c['split']=='test');c['proposed_concept_id']=cases['cases'][0]['proposed_concept_id']
    with pytest.raises(ContractError):validate(cases,corpus,reviews)


@pytest.mark.parametrize('mutation',['source_text','source_version','unknown_source','duplicate_source','bool_grade','empty_source','missing_approval'])
def test_teacher_evidence_must_match_frozen_course_material(tmp_path,mutation):
    cases,corpus,reviews=filled_fixture(tmp_path)
    source=reviews['reviews'][0]['evidence'][0]
    if mutation=='source_text':corpus['documents'][0]['content']+='changed'
    if mutation=='source_version':source['version']=2
    if mutation=='unknown_source':source['document_id']='not-found'
    if mutation=='duplicate_source':reviews['reviews'][0]['evidence'].append(deepcopy(source))
    if mutation=='bool_grade':source['relevance']=True
    if mutation=='empty_source':reviews['reviews'][0]['evidence']=[]
    if mutation=='missing_approval':corpus['documents'][0]['approved_for_evaluation']=False
    with pytest.raises(ContractError):validate(cases,corpus,reviews)


@pytest.mark.parametrize('mutation',['reviewer','timestamp','future','rationale','response','action','bool_accepted'])
def test_teacher_required_annotation_fields_cannot_be_skipped(tmp_path,mutation):
    cases,corpus,reviews=filled_fixture(tmp_path)
    review=reviews['reviews'][0]
    if mutation=='reviewer':reviews['reviewers']=[]
    if mutation=='timestamp':review['reviewed_at']='2026-01-01T00:00:00'
    if mutation=='future':review['reviewed_at']='2099-01-01T00:00:00Z'
    if mutation=='rationale':review['rationale']=' '
    if mutation=='response':review['expected_response_points']=[]
    if mutation=='action':review['answerability']='needs_context';review['expected_action']='trace'
    if mutation=='bool_accepted':review['accepted']=1
    with pytest.raises(ContractError):validate(cases,corpus,reviews)


def test_teacher_rejected_cases_are_recorded_and_missing_test_stratum_blocks_freeze(tmp_path):
    cases,corpus,reviews=filled_fixture(tmp_path)
    for case,review in zip(cases['cases'],reviews['reviews']):
        if case['split']=='test' and case['proposed_intent']=='debugging':review['accepted']=False
    report=validate(cases,corpus,reviews)
    assert report['reviewed']==120 and report['pending']==0 and report['rejected']==4
    assert 'debugging' in report['coverage_gaps']['test']['intents']
    assert not report['ready_to_freeze']


def test_teacher_json_duplicate_keys_and_nonfinite_values_rejected(tmp_path):
    path=tmp_path/'bad.json'
    for raw in ('{"a":1,"a":2}','{"a":NaN}'):
        path.write_text(raw,encoding='utf-8')
        with pytest.raises(ContractError):read_json(path)


@pytest.mark.parametrize('field',['reviewer_id','answerability','expected_action'])
def test_teacher_invalid_field_containers_fail_as_contract_errors(tmp_path,field):
    cases,corpus,reviews=filled_fixture(tmp_path)
    reviews['reviews'][0][field]=[]
    with pytest.raises(ContractError):validate(cases,corpus,reviews)


def test_teacher_cli_report_cannot_overwrite_review_inputs_or_frozen_artifact(tmp_path,monkeypatch,capsys):
    from scripts.check_teacher_baseline import main
    cases,corpus,reviews=filled_fixture(tmp_path)
    folder=tmp_path/'draft'
    for name,value in [('cases.json',cases),('corpus.json',corpus),('reviews.json',reviews)]:
        (folder/name).write_text(json.dumps(value),encoding='utf-8')
    before=(folder/'reviews.json').read_bytes()
    monkeypatch.setattr('sys.argv',['check','--pack',str(folder),'--report',str(folder/'reviews.json')])
    assert main()==1 and (folder/'reviews.json').read_bytes()==before
    path=tmp_path/'frozen.json'
    monkeypatch.setattr('sys.argv',['check','--pack',str(folder),'--freeze',str(path),'--report',str(path)])
    assert main()==1 and not path.exists()
    assert 'cannot overwrite' in capsys.readouterr().out


def test_teacher_cli_pending_exit_is_not_success(tmp_path,monkeypatch,capsys):
    from scripts.check_teacher_baseline import main
    draft(tmp_path)
    monkeypatch.setattr('sys.argv',['check','--pack',str(tmp_path/'draft')])
    assert main()==2
    assert json.loads(capsys.readouterr().out)['pending']==120
