"""Real ledger transactions around controlled transport, not estimated billing."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import uuid

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
import requests
from sqlalchemy import text
from test_learner_state import app
from test_tutor_context import headers
from test_tutoring_modes import dependencies, Provider, candidate, body, ask
from app.models import db, User, Class
from app.models.ai_runtime import AiModelCall as Call
from app.services import model_accounting as accounting
from app.utils.time import utc_now
from agents import http_client


BODY={'model':'requested-model','messages':[{'role':'system','content':'private policy'}, {'role':'user','content':'private code'}]}
USAGE={'prompt_tokens':12,'completion_tokens':8,'total_tokens':20}


class Response:
    def __init__(self,status=200,data=None,lines=()):
        self.status_code=status
        self.data=data if data is not None else {'model':'actual-model','choices':[{'message':{'content':'private reply'}}],'usage':USAGE}
        self.lines=lines
        self.closed=False
    def json(self):return self.data
    def iter_lines(self,*args,**kwargs):yield from self.lines
    def close(self):self.closed=True


def metadata(app,**extra):
    return {'workflow':'resource','user_id':app.config['TEST_STUDENT'],'request_id':str(uuid.uuid4()),
        'attempt_id':str(uuid.uuid4()),'policy_version':'test-policy','state_version':7,**extra}


def post(**extra):
    return http_client.direct_post('https://api.deepseek.com/chat/completions',json=BODY,**extra)


def test_accounting_physical_fallbacks_no_double_count_or_private_contents(app,monkeypatch):
    monkeypatch.setattr(http_client._DIRECT,'post',lambda url,**kw:Response(401,{}) if 'deepseek' in url else Response())
    with app.app_context():
        def generate():
            assert post().status_code==401
            return http_client.direct_post('https://api.openai.com/v1/chat/completions?private=credential',json=BODY)
        response=accounting.operation(metadata(app),generate)
        assert response.json()['model']=='actual-model'
        rows=Call.query.order_by(Call.started_at).all()
        assert len(rows)==2
        assert [(r.provider,r.status,r.error_code) for r in rows]==[('deepseek','failed','http_401'),('openai','succeeded',None)]
        assert rows[0].total_tokens is None and rows[1].total_tokens==20
        assert rows[1].model=='actual-model' and rows[1].state_version==7
        assert rows[1].prompt_hash==accounting.digest(['private policy'])
        assert 'private' not in repr([{c.name:getattr(r,c.name) for c in Call.__table__.columns} for r in rows])
        # Context is restored, so unrelated HTTP does not inherit the student's identity.
        post(); assert Call.query.count()==2
        usage=accounting.summary(app.config['TEST_STUDENT'])
        assert usage['totals']==dict(calls=2,reported_total_tokens=20,unknown_usage_calls=1,failed_calls=1,unfinished_calls=0)
        assert usage['cost'] is None


@pytest.mark.parametrize('failure',[requests.ReadTimeout,requests.Timeout,requests.ConnectionError])
def test_accounting_paid_post_uncertain_failure_is_not_retried(app,monkeypatch,failure):
    monkeypatch.setenv('LLM_HTTP_RETRIES','2')
    with patch.object(http_client._DIRECT,'post',side_effect=failure('private endpoint')) as transport,app.app_context():
        with pytest.raises(failure),accounting.scope(**metadata(app)):
            post()
        assert transport.call_count==1
        row=Call.query.one();assert row.status=='failed' and row.total_tokens is None
        assert 'private' not in (row.error_code or '')
        assert accounting._SCOPE.get() is None


def test_accounting_connect_timeout_retry_is_two_real_attempts(app,monkeypatch):
    monkeypatch.setenv('LLM_HTTP_RETRIES','1')
    with patch.object(http_client._DIRECT,'post',side_effect=[requests.ConnectTimeout(),Response()]) as transport,app.app_context():
        with accounting.scope(**metadata(app)):post()
        assert transport.call_count==2 and Call.query.count()==2
        assert sorted(r.status for r in Call.query.all())==['failed','succeeded']


def test_accounting_stream_usage_and_early_close(app,monkeypatch):
    lines=[b'data: {"model":"stream-model","choices":[{"delta":{"content":"private"}}]}',
           b'data: {"choices":[],"usage":{"prompt_tokens":12,"completion_tokens":8,"total_tokens":20}}',b'data: [DONE]']
    underlying=[]
    def transport(*args,**kw):
        response=Response(lines=lines);underlying.append(response);return response
    monkeypatch.setattr(http_client._DIRECT,'post',transport)
    with app.app_context():
        with accounting.scope(**metadata(app)):
            response=post(stream=True);assert list(response.iter_lines())==lines;response.close()
            interrupted=post(stream=True);iterator=interrupted.iter_lines();next(iterator);iterator.close()
        db.session.expire_all()
        rows=Call.query.order_by(Call.started_at).all()
        assert len(rows)==2 and all(r.closed for r in underlying)
        assert (rows[0].status,rows[0].model,rows[0].total_tokens)==('succeeded','stream-model',20)
        assert rows[1].status=='interrupted' and rows[1].total_tokens is None
        assert accounting.summary(app.config['TEST_STUDENT'])['totals']['unfinished_calls']==1


def test_accounting_stream_error_and_http_error_are_recorded(app,monkeypatch):
    with app.app_context(),patch.object(http_client._DIRECT,'post',side_effect=[Response(lines=[b'data: {"error":{"message":"secret"}}',b'data: [DONE]']),Response(503,{})]):
        with accounting.scope(**metadata(app)):
            list(post(stream=True).iter_lines());post(stream=True)
        assert {r.error_code for r in Call.query.all()}=={'stream_provider_error','http_503'}
        assert all(r.status=='failed' for r in Call.query.all())


def test_accounting_parallel_scopes_do_not_mix_owner_stage_or_class(app,monkeypatch):
    monkeypatch.setattr(http_client._DIRECT,'post',lambda *a,**kw:Response())
    def execute(uid,stage):
        with app.app_context(),accounting.scope(**metadata(app,user_id=uid,class_id=uid,workflow='counterexample')):
            accounting.update_scope(stage=stage);post()
    with ThreadPoolExecutor(2) as pool:
        futures=[pool.submit(execute,app.config[key],stage) for key,stage in [('TEST_STUDENT','generation'),('TEST_TEACHER','review')]]
        for future in futures:future.result(timeout=30)
    with app.app_context():
        rows=Call.query.all();assert len(rows)==2
        assert {(r.user_id,r.stage,r.class_id) for r in rows}=={
            (app.config['TEST_STUDENT'],'generation',app.config['TEST_STUDENT']),
            (app.config['TEST_TEACHER'],'review',app.config['TEST_TEACHER'])}


def test_accounting_usage_owned_and_class_access_current(app,monkeypatch):
    monkeypatch.setattr(http_client._DIRECT,'post',lambda *a,**kw:Response())
    with app.app_context():
        class_id=db.session.get(User,app.config['TEST_STUDENT']).class_id
        other_teacher=User(username='usage-teacher',email='usage-teacher@example.test',password_hash='not-login',
                           role_id=db.session.get(User,app.config['TEST_TEACHER']).role_id)
        db.session.add(other_teacher);db.session.flush();other_teacher_id=other_teacher.id
        other=Class(name='Other',teacher_id=other_teacher_id,grade_level=1)
        db.session.add(other);db.session.commit();other_id=other.id
        for uid,cid in [(app.config['TEST_STUDENT'],class_id),(app.config['TEST_TEACHER'],other_id)]:
            with accounting.scope(**metadata(app,user_id=uid,class_id=cid)):post()
        db.session.rollback()  # Ledger writes use separate short transactions.
        row=Call.query.filter_by(user_id=app.config['TEST_TEACHER']).one()
        row.started_at=utc_now()-timedelta(days=1);db.session.commit()
    client=app.test_client()
    assert client.get('/api/v1/ai/usage').status_code==401
    own=client.get('/api/v1/ai/usage?user_id='+str(app.config['TEST_TEACHER']),headers=headers(app)).json['data']
    assert own['audience']=='self' and own['totals']['calls']==1
    assert client.get('/api/v1/ai/usage',headers=headers(app,True)).json['data']['totals']['calls']==0
    url=f'/api/v1/teacher/classes/{class_id}/ai-usage'
    assert client.get(url,headers=headers(app)).status_code==403
    cohort=client.get(url,headers=headers(app,True)).json['data']
    assert cohort['audience']=='class' and cohort['class_id']==class_id and cohort['totals']['calls']==1
    assert client.get(f'/api/v1/teacher/classes/{other_id}/ai-usage',headers=headers(app,True)).status_code==404
    with app.app_context():
        db.session.get(Class,class_id).teacher_id=other_teacher_id;db.session.commit()
    assert client.get(url,headers=headers(app,True)).status_code==404


def test_accounting_migration_preserves_historical_unknowns_and_repeats(app):
    with app.app_context():
        with accounting.scope(**metadata(app)) as scope:
            accounting.Record(scope).finish(status='unreported')
        db.session.remove()
        with db.engine.begin() as conn:
            conn.execute(text('DROP INDEX ix_ai_call_class_time'+(' ON ai_model_calls' if conn.dialect.name=='mysql' else '')))
            conn.execute(text('ALTER TABLE ai_model_calls DROP COLUMN class_id'))
            conn.execute(text('ALTER TABLE ai_model_calls DROP COLUMN prompt_hash'))
            path=Path(__file__).parents[1]/'migrations/versions/20261017_0030_model_accounting.py'
            spec=importlib.util.spec_from_file_location('accounting_migration',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            with Operations.context(MigrationContext.configure(conn)):
                module.upgrade();module.upgrade()
        row=Call.query.one()
        assert row.class_id is None and row.prompt_hash is None and row.total_tokens is None


@pytest.mark.parametrize('version',[9,None])
def test_accounting_rag_scope_returns_server_request_and_cleans_context(app,monkeypatch,version):
    from app.services.knowledge.knowledge_service import KnowledgeService
    monkeypatch.setattr(http_client._DIRECT,'post',lambda *a,**kw:Response())
    from test_rag_runtime import pipeline, fake_plan
    plan = fake_plan(); plan.learner.state_version = version
    def generate(*a, **kw):
        post(); return '课程回答', 'llm', {}
    with app.app_context(), pipeline(plan=lambda *a, **k: plan, generate=generate):
        answer=KnowledgeService.answer('private question',user_id=app.config['TEST_TEACHER'],role='teacher')
        row=Call.query.one()
        assert row.workflow=='rag' and row.request_id==answer.request_id and row.state_version==(version or 0)
        assert str(uuid.UUID(answer.request_id))==answer.request_id and accounting._SCOPE.get() is None


def test_accounting_tutor_transport_not_counted_again_as_logical_generation(app,dependencies,monkeypatch):
    monkeypatch.setattr(http_client._DIRECT,'post',lambda *a,**kw:Response())
    class TransportProvider(Provider):
        def generate_json(self,**kwargs):
            post();return super().generate_json(**kwargs)
    payload=body(app)
    assert ask(app,payload,TransportProvider(candidate())).status_code==200
    with app.app_context():
        rows=Call.query.all()
        assert len(rows)==2 and {r.stage for r in rows}=={'generation','review'}
        assert all(r.workflow=='tutor' and r.request_id==payload['request_id'] and r.total_tokens==20 for r in rows)


def test_accounting_resource_uses_frozen_state_class_and_current_step(app,monkeypatch):
    from test_learner_state import append
    from test_resource_learning_context import queued
    from app.services.learner_state import LearnerStateService as State
    from app.services.personalized_resource import PersonalizedResourceService as Resources
    app.config['LEARNER_STATE_READ_MODE']='evidence'
    monkeypatch.setattr(http_client._DIRECT,'post',lambda *a,**kw:Response())
    original=Resources._profile_strategy
    def profile(*args):post();return original(*args)
    with app.app_context():
        class_id=db.session.get(User,app.config['TEST_STUDENT']).class_id
        append(app);db.session.commit();State.drain()
        task=queued(app)
        append(app,'later');db.session.commit();State.drain()
        with patch.object(Resources,'_profile_strategy',side_effect=profile):Resources.run_task(app,task['task_id'])
        db.session.expire_all()
        row=Call.query.one()
        assert row.workflow=='resource' and row.request_id==task['task_id']
        assert row.stage=='profile_interpreter' and row.class_id==class_id and row.state_version==1
        assert accounting._SCOPE.get() is None


def test_accounting_counterexample_scope_keeps_task_and_lease(app,monkeypatch):
    from test_counterexample_generation import make_task
    from app.services.counterexample_generation import claim,model_call
    monkeypatch.setattr(http_client._DIRECT,'post',lambda *a,**kw:Response())
    task=make_task(app)
    def generate():post();return None,{'error_code':'synthetic-contract-rejection'}
    with app.app_context():
        task_id,token=claim()
        model_call(task_id,token,'generation',generate)
        row=Call.query.one()
        assert row.workflow=='counterexample' and row.request_id==task['id'] and row.attempt_id==token
        assert row.class_id==task['class_id'] and row.user_id==app.config['TEST_TEACHER']
        assert row.policy_version=='counterexample-generation-v2' and accounting._SCOPE.get() is None
