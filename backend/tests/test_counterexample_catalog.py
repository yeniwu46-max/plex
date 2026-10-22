"""Frozen drafts are teacher-only inputs, never publication authority."""
from collections import Counter
from copy import deepcopy
import json
from unittest.mock import patch

import pytest
from test_learner_state import app
from test_counterexample_gates import auth, call, uid, public, review, review_body, validate_body, validation_path, PASSED
from test_counterexample_workbench import get
from app.models import db, User, Class
from app.models.counterexample import CounterexampleSpec, CounterexampleChallenge, CounterexampleVersion, CounterexampleValidation
from app.services import counterexample_catalog as catalog
from app.services.counterexample_contract import CounterexampleError


def cohort(app):
    with app.app_context(): return db.session.get(User,app.config['TEST_STUDENT']).class_id


def template_body(app, template_id='L01'):
    item=deepcopy(catalog.lookup(template_id))
    content={k:v for k,v in item['specification'].items() if k!='contract_version'}
    spec=call(app,'teacher/counterexample-specifications',{'request_id':uid(),'class_id':cohort(app),'specification':content})
    assert spec.status_code==200,spec.json
    return {'request_id':uid(),'spec_id':spec.json['data']['id'],'candidate':item['candidate'],
            'source_template':{k:item[k] for k in ('id','content_hash')}}


def counts(app):
    with app.app_context():
        return tuple(model.query.count() for model in (CounterexampleSpec,CounterexampleChallenge,CounterexampleVersion,CounterexampleValidation))


def test_fixed_catalog_contracts_and_development_evidence():
    data=catalog.load_catalog()
    assert len(data['items'])==30
    assert Counter(item['candidate']['bug_kind'] for item in data['items'])==dict(loop_boundary=10,empty_input=10,duplicate_elements=10)
    assert len({item['specification']['title'] for item in data['items']})==30
    assert all(item['human_review_status']=='pending' for item in data['items'])
    records=catalog.development_records(data['catalog_hash'])
    assert len(records)==30
    for item in data['items']:
        record=catalog.summary(item,records)['development_validation']
        assert record and record['passed'] is True and record['scope']=='declared_and_bounded_checks'
        assert record['witness_count']>0 and record['coverage']['total_inputs']>=len(item['specification']['tests'])


def test_list_and_load_are_owned_read_only_and_return_copies(app):
    class_id=cohort(app);path=f'teacher/counterexample-templates?class_id={class_id}'
    before=counts(app)
    with patch('app.services.counterexample_validation.CodeExecutionService.run',side_effect=AssertionError('no execution on read')):
        result=get(app,path)
        assert result.status_code==200,result.json
        item=result.json['data']['items'][0]
        assert 'candidate' not in item and 'specification' not in item
        detail=f"teacher/counterexample-templates/{item['id']}?class_id={class_id}&content_hash={item['content_hash']}"
        loaded=get(app,detail).json['data']
        assert loaded['candidate']==catalog.lookup(item['id'])['candidate']
        loaded['specification']['tests'][0]['expected']=999
        assert get(app,detail).json['data']['specification']['tests'][0]['expected']!=999
    assert counts(app)==before
    for target in (path,detail):
        assert get(app,target,'student').status_code==403
        assert app.test_client().get('/api/v1/'+target).status_code==401
    assert get(app,detail.replace(item['content_hash'],'0'*64)).status_code==409
    assert get(app,detail.replace(item['id'],'L00')).status_code==400
    with app.app_context():
        db.session.get(Class,class_id).teacher_id=User.query.filter(User.role.has(name='admin')).first().id
        db.session.commit()
    for target in (path,detail):
        assert get(app,target).status_code==404
        assert get(app,target,'admin').status_code==200


def test_template_provenance_does_not_bypass_validation_or_manual_review(app):
    body=template_body(app)
    created=call(app,'teacher/counterexample-challenges',body)
    assert created.status_code==200,created.json
    row=created.json['data']
    assert row['origin']=='catalog_draft' and row['source_template']=={**body['source_template'],'revision':1}
    assert row['validation'] is None and row['published_revision'] is None
    assert public(app,row).status_code==404
    assert review(app,row,review_body(row,uid())).status_code==409
    # Mock only the execution fact for gate testing; the 30 real Docker reports are separate evidence.
    with patch('app.services.counterexample.validate',return_value=deepcopy(PASSED)):
        report=call(app,validation_path(row),validate_body(row)).json['data']
    assert public(app,row).status_code==404
    assert review(app,row,review_body(row,report['id'])).status_code==200
    visible=public(app,row).json['data']
    assert all(key not in visible for key in ('source_template','origin','specification','candidate','development_validation'))
    assert call(app,'teacher/counterexample-challenges',body).json['data']['id']==row['id']
    assert call(app,'teacher/counterexample-challenges',{k:v for k,v in body.items() if k!='source_template'}).status_code==409


def test_adapted_revision_inherits_source_and_is_unvalidated(app):
    body=template_body(app);body['candidate']['explanation']+=' 教师待核对。'
    created=call(app,'teacher/counterexample-challenges',body).json['data']
    assert created['origin']=='catalog_adapted'
    revised={'request_id':uid(),'expected_revision':1,'spec_id':body['spec_id'],
             'candidate':{**body['candidate'],'explanation':'教师修改解释，仍需审核。'}}
    path=f"teacher/counterexample-challenges/{created['id']}/versions"
    result=call(app,path,revised)
    assert result.status_code==200,result.json
    row=result.json['data']
    assert row['source_template']==created['source_template'] and row['origin']=='catalog_adapted'
    assert row['revision']==2 and row['validation'] is None and row['published_revision'] is None
    assert call(app,path,revised).json['data']['revision']==2
    wrong=deepcopy(revised);wrong['source_template']={k:catalog.lookup('L02')[k] for k in ('id','content_hash')}
    assert call(app,path,wrong).status_code==409
    old=get(app,f"teacher/counterexample-challenges/{row['id']}/versions/1").json['data']
    assert old['candidate']==body['candidate'] and old['source_template']==row['source_template']


@pytest.mark.parametrize('source,status',[
    ({'id':'L01','content_hash':'0'*64},409),
    ({'id':'../secret','content_hash':'0'*64},400),
    ({'id':[],'content_hash':'0'*64},400),
    ({'id':'L01','content_hash':{}},400),
    ({'id':'L01','content_hash':'0'*64,'human_review_status':'passed'},400),
])
def test_invalid_source_does_not_create_versions(app,source,status):
    body=template_body(app);before=counts(app);body['source_template']=source
    assert call(app,'teacher/counterexample-challenges',body).status_code==status
    assert counts(app)==before


def test_stale_development_evidence_is_not_attached(tmp_path,monkeypatch):
    data=catalog.load_catalog();item=data['items'][0];path=tmp_path/'report.json'
    monkeypatch.setattr(catalog,'VALIDATION_PATH',path)
    def write(value):path.write_text(json.dumps(value),encoding='utf-8')
    write({'catalog_hash':'old','human_review_status':'pending','items':[]})
    assert catalog.development_records(data['catalog_hash'])=={}
    record={'id':item['id'],'validator_version':'old','content_hash':item['content_hash']}
    write({'catalog_hash':data['catalog_hash'],'human_review_status':'pending','items':[record]})
    assert catalog.development_records(data['catalog_hash'])=={}
    record.update(validator_version=catalog.VALIDATOR_VERSION,content_hash='0'*64)
    write({'catalog_hash':data['catalog_hash'],'human_review_status':'pending','items':[record]})
    assert catalog.summary(item,catalog.development_records(data['catalog_hash']))['development_validation'] is None


def test_corrupt_catalog_fails_closed_without_mutation(tmp_path,monkeypatch):
    data=deepcopy(catalog.load_catalog());data['items'][0]['candidate']['explanation']='changed'
    path=tmp_path/'catalog.json';path.write_text(json.dumps(data),encoding='utf-8')
    monkeypatch.setattr(catalog,'CATALOG_PATH',path);catalog.load_catalog.cache_clear()
    try:
        with pytest.raises(CounterexampleError) as caught:catalog.load_catalog()
        assert caught.value.status==503
    finally:catalog.load_catalog.cache_clear()


def test_revision_rejects_malformed_falsey_source_instead_of_silently_inheriting(app):
    body=template_body(app)
    created=call(app,'teacher/counterexample-challenges',body).json['data']
    path=f"teacher/counterexample-challenges/{created['id']}/versions"
    for source in ({},[],False,0,''):
        revised={'request_id':uid(),'expected_revision':1,'spec_id':body['spec_id'],
                 'candidate':body['candidate'],'source_template':source}
        assert call(app,path,revised).status_code==400
    assert get(app,f"teacher/counterexample-challenges/{created['id']}").json['data']['revision']==1
