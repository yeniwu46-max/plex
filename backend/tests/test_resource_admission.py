"""Admission is transactional across processes and safe for ambiguous retries."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import importlib.util
from pathlib import Path
from unittest.mock import patch
import uuid
import pytest
from sqlalchemy import text,update
from sqlalchemy.orm import Session
from alembic.migration import MigrationContext
from alembic.operations import Operations
from test_learner_state import app
from test_tutor_context import headers
from app.models import db,User,ResourceGenerationTask as Task,PersonalizedLearningResource as Resource
from app.services.personalized_resource import PersonalizedResourceService as Resources
from app.services import resource_runtime
from app.services.tutor_context import TutorContextError
from app.utils.time import utc_now


def payload(**kwargs):
    return {'knowledge_key':'loop-for','resource_types':['learning_bundle'],'force_regenerate':True,**kwargs}


def create(app,uid=None,**extra):
    with app.app_context():return Resources.create_task(uid or app.config['TEST_STUDENT'],payload(**extra))


def fail(app,task_id):
    with app.app_context():
        Task.query.filter_by(task_id=task_id).update({'status':'failed'});db.session.commit()


def test_resource_admission_explicit_identity_always_replays_before_limits(app):
    app.config['RESOURCE_USER_DAILY_LIMIT']=1
    with patch.object(Resources,'run_task') as worker:
        first=create(app,idempotency_key='same')
        with app.app_context():
            Task.query.filter_by(task_id=first['task_id']).update({'created_at':utc_now()-timedelta(days=1),'status':'failed'});db.session.commit()
        again=create(app,idempotency_key='same')
        assert again['task_id']==first['task_id'] and again['status']=='failed' and worker.call_count==1
        with pytest.raises(TutorContextError) as exc:create(app,idempotency_key='same',learning_stage='复习')
        assert exc.value.status==409
        assert create(app,idempotency_key='new')['task_id']!=first['task_id']
        with pytest.raises(TutorContextError) as exc:create(app,idempotency_key='third')
        assert exc.value.status==429


def test_resource_admission_concurrent_identity_and_user_limit(app):
    app.config.update(RESOURCE_USER_ACTIVE_LIMIT=1)
    with patch.object(Resources,'run_task') as worker,ThreadPoolExecutor(5) as pool:
        same=[pool.submit(create,app,idempotency_key='same') for _ in range(5)]
        ids={f.result(timeout=30)['task_id'] for f in same}
        assert len(ids)==1 and worker.call_count==1
        def attempt():
            try:return create(app,idempotency_key=str(uuid.uuid4()))['status']
            except TutorContextError as exc:return exc.status
        assert list(pool.map(lambda _:attempt(),range(4)))==[429]*4
    with app.app_context():assert Task.query.count()==1


def test_resource_admission_different_requests_race_for_last_slots(app):
    app.config.update(RESOURCE_USER_ACTIVE_LIMIT=2,RESOURCE_USER_DAILY_LIMIT=2)
    def submit(index):
        try:return create(app,idempotency_key='parallel-'+str(index))['status']
        except TutorContextError as exc:return exc.status
    with patch.object(Resources,'run_task'),ThreadPoolExecutor(5) as pool:
        results=list(pool.map(submit,range(5)))
    assert results.count('pending')==2 and results.count(429)==3
    with app.app_context():assert Task.query.count()==2


def test_resource_admission_shared_class_cap_and_owner_usage(app):
    app.config.update(RESOURCE_CLASS_ACTIVE_LIMIT=1,RESOURCE_USER_ACTIVE_LIMIT=4)
    with app.app_context():
        student=db.session.get(User,app.config['TEST_STUDENT']);cid=student.class_id
        second=User(username='quota-student',email='quota@example.test',password_hash='not-login',role_id=student.role_id,class_id=cid)
        db.session.add(second);db.session.commit();other_id=second.id
    with patch.object(Resources,'run_task'):
        first=create(app)
        with pytest.raises(TutorContextError) as exc:create(app,other_id)
        assert exc.value.status==429
        fail(app,first['task_id'])
        app.config['RESOURCE_CLASS_DAILY_LIMIT']=1
        with pytest.raises(TutorContextError) as exc:create(app,other_id)
        assert exc.value.status==429
    client=app.test_client()
    own=client.get('/api/v1/student/resource-generation/usage',headers=headers(app)).json['data']
    assert own['requests_used']==1 and own['active_tasks']==0
    url=f'/api/v1/teacher/classes/{cid}/resource-generation/usage'
    assert client.get(url,headers=headers(app,True)).json['data']['requests_remaining']==0
    assert client.get(url,headers=headers(app)).status_code==403
    assert client.get('/api/v1/student/resource-generation/usage').status_code==401


def test_resource_admission_retries_form_one_bounded_chain(app):
    with patch.object(Resources,'run_task'):
        first=create(app);fail(app,first['task_id'])
        with app.app_context():
            child=Resources.retry(app.config['TEST_STUDENT'],first['task_id'])
            same=Resources.retry(app.config['TEST_STUDENT'],first['task_id'])
            assert child['task_id']==same['task_id'] and child['retry_remaining']==1
        fail(app,child['task_id'])
        with app.app_context():last=Resources.retry(app.config['TEST_STUDENT'],child['task_id'])
        fail(app,last['task_id'])
        with app.app_context():
            with pytest.raises(TutorContextError) as exc:Resources.retry(app.config['TEST_STUDENT'],last['task_id'])
            assert exc.value.status==429 and Task.query.count()==3
            assert len({r.retry_root_id for r in Task.query.all()})==1
            assert Resources.get_task(app.config['TEST_STUDENT'],last['task_id'])['recoverable'] is False
    with pytest.raises(TutorContextError):create(app,retry_of=first['task_id'])


def test_resource_admission_queue_failure_returns_existing_failed_task(app,monkeypatch):
    # Select the production dispatch branch only; no provider/executor is called.
    app.config['TESTING']=False;monkeypatch.delenv('RESOURCE_TASK_SYNC',raising=False)
    with patch('app.services.personalized_resource.submit_resource_task',side_effect=RuntimeError('private transport')):
        result=create(app,idempotency_key='queue-failure')
        assert result['status']=='failed' and 'private' not in result['error']
        assert create(app,idempotency_key='queue-failure')['task_id']==result['task_id']
    with app.app_context():assert Task.query.count()==1


def test_resource_admission_expired_worker_cannot_publish_after_recovery(app):
    with patch.object(Resources,'run_task'):task=create(app)
    original=Resources._run_profile_interpreter
    def slow(*a,**kw):
        with Session(db.engine) as other:
            other.execute(update(Task).where(Task.task_id==task['task_id']).values(status='failed',error='recovered elsewhere'));other.commit()
        return original(*a,**kw)
    with patch.object(Resources,'_run_profile_interpreter',side_effect=slow):Resources.run_task(app,task['task_id'])
    with app.app_context():
        row=Task.query.filter_by(task_id=task['task_id']).one()
        assert row.status=='failed' and row.error=='recovered elsewhere' and Resource.query.count()==0


def test_resource_admission_recovery_releases_only_stale_running_capacity(app):
    with patch.object(Resources,'run_task'):
        first=create(app)
        with app.app_context():
            Task.query.filter_by(task_id=first['task_id']).update({'status':'running','updated_at':utc_now()-timedelta(hours=1)});db.session.commit()
        app.config['RESOURCE_USER_ACTIVE_LIMIT']=1
        assert create(app)['task_id']!=first['task_id']
    with app.app_context():assert Task.query.filter_by(task_id=first['task_id']).one().status=='failed'


def test_resource_admission_recovery_persists_even_when_new_quota_is_rejected(app):
    app.config['RESOURCE_USER_DAILY_LIMIT']=1
    with patch.object(Resources,'run_task'):
        task=create(app)
        with app.app_context():
            Task.query.filter_by(task_id=task['task_id']).update({'status':'running','updated_at':utc_now()-timedelta(hours=1)});db.session.commit()
        with pytest.raises(TutorContextError):create(app)
    with app.app_context():assert Task.query.filter_by(task_id=task['task_id']).one().status=='failed'


def test_resource_admission_api_rejects_without_creating_and_preserves_429(app):
    app.config['RESOURCE_USER_DAILY_LIMIT']=1
    client=app.test_client();url='/api/v1/student/resource-generation/tasks'
    with patch.object(Resources,'run_task'):
        assert client.post(url,headers=headers(app),json=payload()).status_code==201
        assert client.post(url,headers=headers(app),json=payload()).status_code==429
    for body in ([],None,payload(resource_types={'bad':'input'}),payload(idempotency_key='x'*101)):
        assert client.post(url,headers=headers(app),json=body).status_code==400
    with app.app_context():assert Task.query.count()==1


def test_resource_admission_migration_keeps_old_unknown_class_and_repeats(app):
    with patch.object(Resources,'run_task'):create(app)
    with app.app_context():
        db.session.remove()
        with db.engine.begin() as conn:
            for name in ['ix_resource_class_time','ix_resource_retry_root']:
                conn.execute(text('DROP INDEX '+name+(' ON resource_generation_tasks' if conn.dialect.name=='mysql' else '')))
            for name in ['class_id','retry_root_id','request_body_hash']:conn.execute(text('ALTER TABLE resource_generation_tasks DROP COLUMN '+name))
            path=Path(__file__).parents[1]/'migrations/versions/20261018_0031_resource_admission.py'
            spec=importlib.util.spec_from_file_location('resource_admission_migration',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            with Operations.context(MigrationContext.configure(conn)):module.upgrade();module.upgrade()
        row=Task.query.one();assert row.class_id is None and row.retry_root_id is None and row.request_body_hash is None


def test_counterexample_class_admission_replay_and_retry_respect_shared_cap(app):
    from test_counterexample_generation import make_task,call,ROOT
    from app.models.counterexample import CounterexampleGenerationTask as Candidate
    app.config.update(COUNTEREXAMPLE_GENERATION_ACTIVE_LIMIT=10,COUNTEREXAMPLE_CLASS_ACTIVE_LIMIT=1)
    first=make_task(app)
    body={'request_id':str(uuid.uuid4()),'spec_id':first['spec_id'],'bug_kind':'loop_boundary'}
    assert call(app,ROOT,body).status_code==429
    assert call(app,ROOT,{**body,'request_id':first['id']}).json['data']['id']==first['id']
    with app.app_context():
        row=db.session.get(Candidate,first['id']);row.status='failed';row.error_code='model_unavailable';row.attempts=1;db.session.commit()
    second=call(app,ROOT,body);assert second.status_code==200
    assert call(app,ROOT+'/'+first['id']+'/retry',{'expected_attempts':1}).status_code==429
    assert call(app,ROOT+'/'+second.json['data']['id']+'/cancel',{}).status_code==200
    app.config['COUNTEREXAMPLE_CLASS_DAILY_LIMIT']=2
    assert call(app,ROOT,{**body,'request_id':str(uuid.uuid4())}).status_code==429


def test_browser_acceptance_can_dispatch_async_without_disabling_testing(app, monkeypatch):
    app.config['RESOURCE_TASK_SYNC'] = False
    monkeypatch.delenv('RESOURCE_TASK_SYNC', raising=False)
    with patch('app.services.personalized_resource.submit_resource_task') as submit, patch.object(Resources, 'run_task') as worker:
        first = create(app, idempotency_key='browser-background')
        assert first['status'] == 'pending'
        submit.assert_called_once_with(worker, app, first['task_id'])
        worker.assert_not_called()
        assert app.config['TESTING'] is True
        assert create(app, idempotency_key='browser-background')['task_id'] == first['task_id']
        assert submit.call_count == 1
