"""Documents and concept maps use the same reviewed, owned tutoring contract."""
from copy import deepcopy
import hashlib
import json
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from test_learner_state import app, append
from test_tutoring_modes import Provider, APPROVED
from test_knowledge_access import materials, headers
from test_resource_learning_context import set_profile
from app.models import db, KnowledgeChunk, KnowledgeDocument, TrialQuestion, Trial, User
from app.models.learner_state import LearningEvent, TutorDisplayReceipt
from app.models.tutor_session import TutorTurn
from app.services.learner_state import LearnerStateService as State
from app.services.knowledge.knowledge_service import KnowledgeService
from app.services.messenger_artifacts import MessengerArtifactService as Artifacts, plain
from app.services.tutor_context import TutorContextError


def generated(kind='document'):
    result = {'title':'循环学习笔记','summary':'理解循环停止值和边界。','next_step':'','follow_up':'',
              'citations':[{'chunk_id':'own','supports':'停止值不包含在序列中'}]}
    if kind == 'document':
        result['sections'] = [{'heading':title,'text':'循环的停止值不包含在结果中，需要核对边界。'} for title in ['学习目标','分步讲解','易错提醒']]
    else:
        result.update(nodes=[{'id':f'n{i}','label':label} for i,label in enumerate(['循环','起点','停止条件'])],
                      edges=[{'from':'n0','to':'n1'},{'from':'n0','to':'n2'}])
    return result


@pytest.fixture
def evidence(app):
    app.config.update(TUTOR_MODELS_ENABLED=True, LEARNER_STATE_READ_MODE='evidence')
    with app.app_context():
        materials(app)
        row = KnowledgeChunk.query.filter_by(chunk_id='own').one()
        source = {'chunk_id':'own','document_id':'own','version':2,'title':'循环材料','chapter':'循环','source_page':1,
                  'content':row.content,'content_hash':hashlib.sha256(row.content.encode()).hexdigest()}
    with patch.object(KnowledgeService,'tutor_evidence',return_value={'status':'grounded','sources':[source],'prerequisite_gaps':[]}) as get:
        yield get


def post(app, body, provider, kind='document'):
    path = 'learning-document' if kind == 'document' else 'knowledge-graph'
    with app.app_context(): auth = headers(app.config['TEST_STUDENT'])
    with patch('app.services.tutoring.get_llm_provider', return_value=provider):
        return app.test_client().post('/api/v1/student/messenger/tools/'+path, headers=auth, json=body)


def body(**extra):
    return {'topic':'Python 循环边界','request_id':str(uuid.uuid4()), **extra}


@pytest.mark.parametrize('kind',['document','graph'])
def test_tools_review_before_publish_reuse_request_and_do_not_create_learning_evidence(app, evidence, kind):
    provider = Provider(generated(kind)); payload = body()
    with app.app_context():
        before = (TutorDisplayReceipt.query.count(), LearningEvent.query.count())
    response = post(app, payload, provider, kind)
    assert response.status_code == 200
    result = response.json['data']
    assert result['status']=='ok' and result['kind']==kind and result['artifact_id']==payload['request_id']
    assert '版本 2' in result['markdown'] and result['knowledge']['sources'][0]['chunk_id']=='own'
    assert 'content_hash' not in str(result) and 'http' not in result['markdown']
    assert result['illustration'] is None
    assert (bool(result['mermaid'])) == (kind=='graph')
    again = post(app, payload, provider, kind)
    assert again.json['data']==result and len(provider.calls)==2
    assert post(app,{**payload,'topic':'Python 函数'}, provider,kind).status_code==409
    with app.app_context():
        assert (TutorDisplayReceipt.query.count(),LearningEvent.query.count())==before
        stored=TutorTurn.query.filter_by(id=payload['request_id']).one()
        assert stored.evidence_refs[0]['content_hash']
        assert Artifacts.read(app.config['TEST_STUDENT'],payload['request_id'])==result


def test_artifact_retrieval_uses_frozen_profile_and_evidence_without_age(app, evidence):
    with app.app_context():
        set_profile(app); append(app); db.session.commit(); State.drain()
    def change_profile():
        set_profile(app,'有工作经验',4)
        app.config['LEARNER_STATE_READ_MODE']='shadow'
    result=post(app,body(),Provider(generated(),callback=change_profile)).json['data']
    learner=evidence.call_args.kwargs['learner_context']
    assert learner.knowledge_foundation=='完全零基础' and learner.state_version==1
    assert result['learning_context']=={'state_source':'evidence','state_version':1,'profile_version':3}
    assert 'private-age' not in str(learner.profile_dimensions)


@pytest.mark.parametrize('change',['revoke','version','content'])
def test_artifact_restore_and_retry_recheck_sources(app,evidence,change):
    provider=Provider(generated()); payload=body()
    assert post(app,payload,provider).json['data']['status']=='ok'
    with app.app_context():
        if change=='revoke': db.session.get(KnowledgeDocument,'own').published=False
        elif change=='version': db.session.get(KnowledgeDocument,'own').version=3
        else: KnowledgeChunk.query.filter_by(chunk_id='own').one().content='replacement with unchanged version'
        db.session.commit()
        auth=headers(app.config['TEST_STUDENT'])
    assert app.test_client().get('/api/v1/student/messenger/tools/artifacts/'+payload['request_id'],headers=auth).status_code==409
    assert post(app,payload,provider).status_code==409 and len(provider.calls)==2


def test_source_revoked_during_generation_never_publishes_artifact(app,evidence):
    def revoke():
        with Session(db.engine) as session:
            session.get(KnowledgeDocument,'own').published=False;session.commit()
    result=post(app,body(),Provider(generated(),callback=revoke))
    assert result.status_code==409 and '循环学习笔记' not in result.text
    with app.app_context(): assert not TutorTurn.query.filter_by(status='complete').count()


@pytest.mark.parametrize('invalid',['citation','html','edge','semantic'])
def test_unreviewed_or_malformed_document_and_graph_are_not_presented_as_success(app,evidence,invalid):
    graph = invalid=='edge'; raw=generated('graph' if graph else 'document'); review=dict(APPROVED)
    if invalid=='citation': raw['citations'][0]['chunk_id']='forged'
    if invalid=='html': raw['sections'][0]['text']='<script>DO_NOT_SHOW</script>'
    if invalid=='edge': raw['edges'][0]['to']='click n0 callback'
    if invalid=='semantic': raw['summary']='DO_NOT_SHOW';review['answer_leakage']=True
    result=post(app,body(),Provider(raw,review),'graph' if graph else 'document').json['data']
    assert result['status']=='safe_fallback' and not result['mermaid']
    assert 'DO_NOT_SHOW' not in str(result) and 'forged' not in str(result)
    assert result['title']=='学习材料暂未生成'


@pytest.mark.parametrize('status',['insufficient_evidence','retrieval_unavailable'])
def test_missing_evidence_does_not_fabricate_a_document(app,evidence,status):
    evidence.return_value={'status':status,'sources':[],'prerequisite_gaps':[]}
    provider=Provider(generated())
    result=post(app,body(),provider).json['data']
    assert result['status']=='safe_fallback' and result['evidence_status']==status and not provider.calls


def test_task_restrictions_cross_account_and_unknown_inputs(app,evidence):
    with app.app_context():
        question=db.session.get(TrialQuestion,app.config['TEST_QUESTION'])
        trial=db.session.get(Trial,question.trial_id);trial.tutoring_policy='disabled';db.session.commit()
    provider=Provider(generated())
    assert post(app,body(formal_question_id=app.config['TEST_QUESTION']),provider).status_code==403
    assert not provider.calls
    assert post(app,body(sources=[{'chunk_id':'forged'}]),provider).status_code==400
    assert post(app,body(topic=['not text']),provider).status_code==400
    result=post(app,body(),provider).json['data']
    with app.app_context():
        other=User(username='artifact-other',email='artifact-other@example.invalid',role_id=db.session.get(User,app.config['TEST_STUDENT']).role_id,status='active',password_hash='unused-test-only')
        db.session.add(other);db.session.commit()
        auth=headers(other.id)
    response=app.test_client().get('/api/v1/student/messenger/tools/artifacts/'+result['artifact_id'],headers=auth)
    assert response.status_code==404


def test_document_renderer_does_not_turn_model_text_into_links():
    assert plain('[click](//example.invalid)')==r'\[click\](//example\.invalid)'


def test_artifact_real_retrieval_uses_frozen_preferences_and_checks_all_evidence(app):
    from test_resource_course_evidence import materials as course_materials, indexed
    from app.services.resource_learning_context import ResourceLearningContext
    from app.services.knowledge.learner_context_service import LearnerContextService
    with app.app_context():
        course_materials(app);set_profile(app)
        frozen=ResourceLearningContext.capture(app.config['TEST_STUDENT'],'loop-for')
        learner=LearnerContextService.from_resource_snapshot(frozen)
        with indexed(), patch.object(LearnerContextService,'build',side_effect=AssertionError('live profile read')):
            result=KnowledgeService.tutor_evidence('for 循环边界',user_id=learner.user_id,task=None,state_snapshot={},learner_context=learner)
        assert result['status']=='grounded'
        assert {s['chunk_id'] for s in result['sources']}=={'own','public'}
        assert all(s['content_hash']==hashlib.sha256(db.session.get(KnowledgeChunk,s['chunk_id']).content.encode()).hexdigest() for s in result['sources'])
        assert result['learning_preferences']==frozen['profile']
        assert 'private-age' not in str(result)
        assert KnowledgeService.tutor_sources_current(learner.user_id,result['sources'])


def test_json_model_values_preserve_operators_before_artifact_review():
    from unittest.mock import Mock
    from app.services.knowledge.providers.llm import OpenAICompatibleLLMProvider
    raw={'summary':'2 * 3 等于 6，平方写作 2 ** 2','nodes':[{'id':'n0','label':'* 运算'}]}
    response=Mock();response.json.return_value={'choices':[{'message':{'content':json.dumps(raw)}}]}
    with patch.object(OpenAICompatibleLLMProvider,'_resolve',return_value=('fixture','https://example.invalid','fixture')),patch('app.services.knowledge.providers.llm.direct_post',return_value=response):
        assert OpenAICompatibleLLMProvider().generate_json(system='JSON',user='synthetic')==raw


def test_artifact_renderer_prevents_automatic_bare_links():
    assert plain('www.example.com')==r'www\.example\.com'
    assert plain('mail@example.com')==r'mail\@example\.com'
