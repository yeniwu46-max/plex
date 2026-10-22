"""Durable budgets, race-safe cancellation and non-fabricated model usage."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from unittest.mock import patch
import importlib.util
from pathlib import Path
import uuid
import pytest
from sqlalchemy import inspect,select,update
from sqlalchemy.orm import Session
from alembic.migration import MigrationContext
from alembic.operations import Operations
from test_learner_state import app
from test_tutoring_modes import dependencies,Provider,candidate,ask,body
from test_tutor_context import headers
from app.models import db,User
from app.models.ai_runtime import AiRuntimeLock,TutorRequestAttempt as Attempt,TutorRequestCancellation as Cancellation,AiModelCall as Call
from app.models.tutor_session import TutorTurn
from app.models.learner_state import TutorDisplayReceipt,LearningEvent
from app.services import tutor_runtime as runtime
from app.services.tutor_sessions import TutorSessions
from app.services.tutor_context import TutorContextService,TutorContextError
from app.services.model_observation import report_model
from app.utils.time import utc_now

class Metered(Provider):
    def generate_json(self,**kwargs):
        report_model(status='succeeded',provider='synthetic',model='test-model',token_usage={'prompt_tokens':50,'completion_tokens':5,'total_tokens':55})
        return super().generate_json(**kwargs)

def cancel(app,rid):
    return app.test_client().post('/api/v1/student/tutor/turns/'+rid+'/cancel',headers=headers(app))

def test_retry_cached_response_does_not_consume_quota_or_tokens(app,dependencies):
    app.config['TUTOR_DAILY_REQUEST_LIMIT']=2
    provider=Metered(candidate());payload=body(app,'next_step')
    assert ask(app,payload,provider).status_code==200
    assert ask(app,payload,provider).status_code==200
    assert ask(app,body(app,'next_step'),provider).status_code==200
    assert ask(app,body(app,'next_step'),provider).status_code==429
    with app.app_context():
        use=runtime.usage(app.config['TEST_STUDENT'])
        assert use['requests_used']==2 and use['requests_remaining']==0 and use['reported_total_tokens']==220
        assert use['model_calls']==4 and use['unknown_usage_calls']==0 and use['cost'] is None
        assert Attempt.query.count()==2 and Call.query.count()==4
        rows=Call.query.all()
        assert {r.stage for r in rows}=={'generation','review'} and all(r.model=='test-model' and len(r.retrieval_config_hash)==64 for r in rows)
        assert not {'question','prompt','reply','code','api_key'}.intersection(Call.__table__.columns.keys())


def test_cancel_before_claim_is_owned_durable_and_idempotent(app,dependencies):
    payload=body(app,'next_step');rid=payload['request_id'];provider=Metered(candidate())
    assert cancel(app,rid).json['data']['cancelled']
    assert cancel(app,rid).json['data']['cancelled']
    assert ask(app,payload,provider).status_code==409 and not provider.calls
    with app.app_context():
        assert Cancellation.query.count()==1 and TutorTurn.query.count()==Attempt.query.count()==0
        db.session.remove()
        assert runtime.cancel(app.config['TEST_STUDENT'],rid)['cancelled']


def test_cancel_during_model_keeps_usage_but_prevents_review_publication_and_receipt(app,dependencies):
    payload=body(app,'next_step')
    provider=Metered(candidate(),callback=lambda:cancel(app,payload['request_id']))
    result=ask(app,payload,provider)
    assert result.status_code==409 and len(provider.calls)==1
    assert ask(app,payload,provider).status_code==409
    with app.app_context():
        assert TutorTurn.query.one().status=='cancelled' and Attempt.query.one().status=='cancelled'
        assert TutorDisplayReceipt.query.count()==LearningEvent.query.count()==0
        assert Call.query.one().total_tokens==55
        use=runtime.usage(app.config['TEST_STUDENT']);assert use['cancelled_requests']==1 and use['active_requests']==0
    assert app.test_client().get('/api/v1/student/tutor/turns/'+payload['request_id'],headers=headers(app)).status_code==404


def test_cancel_does_not_release_inflight_provider_capacity_until_return(app,dependencies):
    entered=Event();release=Event();app.config['TUTOR_USER_CONCURRENCY']=1
    payload=body(app,'next_step')
    provider=Metered(candidate(),callback=lambda:(entered.set(),release.wait(12)))
    with patch('app.services.tutoring.get_llm_provider',return_value=provider),ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(lambda:app.test_client().post('/api/v1/student/tutor/ask',headers=headers(app),json=payload))
        try:
            assert entered.wait(10)
            assert cancel(app,payload['request_id']).json['data']['cancelled']
            with app.app_context():assert runtime.usage(app.config['TEST_STUDENT'])['active_requests']==1
            denied=app.test_client().post('/api/v1/student/tutor/ask',headers=headers(app),json=body(app,'next_step'))
            assert denied.status_code==429
        finally:release.set()
        assert future.result(timeout=10).status_code==409
    with app.app_context():assert runtime.usage(app.config['TEST_STUDENT'])['active_requests']==0


def test_completed_result_wins_cancellation_and_other_account_cannot_cancel(app,dependencies):
    payload=body(app,'next_step');assert ask(app,payload,Metered(candidate())).status_code==200
    assert cancel(app,payload['request_id']).json['data']=={'request_id':payload['request_id'],'cancelled':False,'status':'complete'}
    with app.app_context():
        student=db.session.get(User,app.config['TEST_STUDENT'])
        other=User(username='cancel-other',email='cancel-other@example.invalid',password_hash='unused',role_id=student.role_id)
        db.session.add(other);db.session.commit()
        with pytest.raises(TutorContextError) as exc:runtime.cancel(other.id,payload['request_id'])
        assert exc.value.status==404
        assert TutorTurn.query.one().status=='complete' and Cancellation.query.count()==0
        assert runtime.usage(other.id)['requests_used']==0


def claim(app,request_id=None,uid=None):
    with app.app_context():
        user=uid or app.config['TEST_STUDENT'];ctx=TutorContextService.resolve(user,{})
        return TutorSessions.claim(user,request_id or str(uuid.uuid4()),None,'fixed',ctx,'Python loop','next_step')


def test_concurrent_claims_obey_database_account_limit(app):
    app.config['TUTOR_USER_CONCURRENCY']=2
    def worker(_):
        try:return claim(app)
        except TutorContextError as exc:return exc.status
    with ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(worker,range(5)))
    assert sum(isinstance(r,dict) for r in results)==2 and results.count(429)==3
    with app.app_context():assert Attempt.query.count()==TutorTurn.query.count()==2


def test_global_capacity_and_expired_attempts(app):
    app.config['TUTOR_GLOBAL_CONCURRENCY']=1
    first=claim(app)
    with app.app_context():
        student=db.session.get(User,app.config['TEST_STUDENT'])
        other=User(username='limit-other',email='limit-other@example.invalid',password_hash='unused',role_id=student.role_id)
        db.session.add(other);db.session.commit();other_id=other.id
    with pytest.raises(TutorContextError) as exc:claim(app,uid=other_id)
    assert exc.value.status==429
    with app.app_context():
        db.session.get(Attempt,first['token']).lease_until=utc_now()-timedelta(seconds=1);db.session.commit()
    assert claim(app,uid=other_id)


def test_failed_same_request_retries_are_bounded_and_old_lease_cannot_publish(app):
    rid=str(uuid.uuid4());app.config['TUTOR_REQUEST_ATTEMPT_LIMIT']=2
    first=claim(app,rid)
    with app.app_context():TutorSessions.fail(first);runtime.settle(first)
    second=claim(app,rid)
    with app.app_context():
        with pytest.raises(TutorContextError):runtime.checkpoint(first)
        TutorSessions.fail(second);runtime.settle(second)
    with pytest.raises(TutorContextError) as exc:claim(app,rid)
    assert exc.value.status==429
    with app.app_context():assert Attempt.query.count()==2


def test_unknown_usage_is_not_zero_and_daily_window_is_utc(app,dependencies):
    assert ask(app,body(app,'next_step'),Provider(candidate())).status_code==200
    with app.app_context():
        data=runtime.usage(app.config['TEST_STUDENT'])
        assert data['model_calls']==2 and data['unknown_usage_calls']==2 and data['reported_total_tokens']==0
        assert all(row.total_tokens is None for row in Call.query.all())
        for row in Attempt.query.all():row.started_at=utc_now()-timedelta(days=1)
        db.session.commit();assert runtime.usage(app.config['TEST_STUDENT'])['requests_used']==0


def test_usage_requires_student_identity_and_exposes_no_call_bodies(app):
    client=app.test_client()
    assert client.get('/api/v1/student/tutor/usage').status_code==401
    assert client.get('/api/v1/student/tutor/usage',headers=headers(app,teacher=True)).status_code==403
    response=client.get('/api/v1/student/tutor/usage',headers=headers(app))
    assert response.status_code==200 and response.json['data']['scope']=='tutor'
    assert 'prompt' not in response.text and 'api_key' not in response.text


def test_runtime_migration_is_repeatable_and_preserves_existing_users(app):
    file=Path(__file__).parents[1]/'migrations/versions/20261017_0029_tutor_runtime.py'
    spec=importlib.util.spec_from_file_location('runtime_migration',file);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with app.app_context():
        before=User.query.count();db.session.rollback()
        with db.engine.begin() as connection:
            for table in [Call.__table__,Attempt.__table__,Cancellation.__table__,AiRuntimeLock.__table__]:table.drop(connection)
            with Operations.context(MigrationContext.configure(connection)):
                module.upgrade();module.upgrade()
            assert {'ai_model_calls','tutor_request_attempts','tutor_request_cancellations','ai_runtime_locks'}<=set(inspect(connection).get_table_names())
        assert User.query.count()==before
