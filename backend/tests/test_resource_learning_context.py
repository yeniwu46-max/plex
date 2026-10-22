"""Queued generation and retries use the same server-owned teaching evidence."""
from copy import deepcopy
import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect
from test_learner_state import app, append
from test_counterexample_gates import auth
from app.models import db, StudentProfile, ResourceGenerationTask, User
from app.models.learner_state import LearningEvent, LearnerState
from app.services.learner_state import LearnerStateService as State
from app.services.student_profile import StudentProfileService
from app.services.personalized_resource import PersonalizedResourceService as Resources
from app.services.resource_learning_context import ResourceLearningContext as Context


def set_profile(app, foundation='完全零基础', version=3):
    row=StudentProfileService.get_or_create(app.config['TEST_STUDENT'],persist=True)
    row.version=version
    row.dimensions={
        'knowledge_foundation':{'value':foundation,'source':'questionnaire','evidence':['private-profile-evidence']},
        'interest_direction':{'value':'游戏','source':'conversation'},
        'mistake_pattern':{'value':'legacy-behavior-inference','source':'behavior'},
        'age_range':{'value':'private-age','source':'questionnaire'}}
    db.session.commit()


def queued(app, **payload):
    with patch.object(Resources,'run_task'):
        return Resources.create_task(app.config['TEST_STUDENT'],{
            'knowledge_key':'loop-for','resource_types':['learning_bundle'],
            'target':'大学','learning_stage':'复习','learning_style':['案例'],**payload})


def test_capture_is_read_only_filters_profile_and_keeps_unknown_unknown(app):
    app.config['LEARNER_STATE_READ_MODE']='evidence'
    with app.app_context():
        set_profile(app)
        before=(StudentProfile.query.count(),LearningEvent.query.count(),LearnerState.query.count())
        context=Context.capture(app.config['TEST_STUDENT'],'loop-for')
        assert context['profile']=={'knowledge_foundation':'完全零基础','interest_direction':'游戏'}
        assert context['profile_version']==3 and context['learner_state']['state_version']==0
        assert context['learner_state']['concepts']==[] and context['learning_decision']['basis']=='baseline'
        assert 'private-' not in str(context)
        assert (StudentProfile.query.count(),LearningEvent.query.count(),LearnerState.query.count())==before


def test_queued_task_uses_frozen_state_profile_and_teaching_choices(app):
    app.config['LEARNER_STATE_READ_MODE']='evidence'
    with app.app_context():
        set_profile(app)
        append(app,'first',correct=False);append(app,'second',correct=False);db.session.commit();State.drain()
        task=queued(app)
        original=deepcopy(ResourceGenerationTask.query.filter_by(task_id=task['task_id']).one().context_snapshot)
        assert task['learning_context']['state_version']==2 and task['learning_context']['basis']=='formal_evidence'
        set_profile(app,'有工作经验',version=4)
        append(app,'third',correct=True);db.session.commit();State.drain()
        assert State.snapshot(app.config['TEST_STUDENT'])['state_version']==3
        with patch.object(Resources,'_profile_snapshot',side_effect=AssertionError('must not reread live profile')):
            Resources.run_task(app,task['task_id'])
        db.session.expire_all()
        result=Resources.get_task(app.config['TEST_STUDENT'],task['task_id'])
        assert result['status']=='completed',result['error']
        assert result['profile_version']==3 and result['learning_context']['state_version']==2
        assert all(step['input_summary']['state_version']==2 for step in result['steps'])
        assert {step['input_summary']['learning_context_hash'] for step in result['steps']}=={task['learning_context']['context_hash']}
        assert result['resources'][0]['profile_snapshot']['knowledge_foundation']=='完全零基础'
        analysis=result['resources'][0]['content']['analysis']
        assert analysis['learning_stage']=='复习' and analysis['learning_guidance']['state_version']==2
        assert ResourceGenerationTask.query.filter_by(task_id=task['task_id']).one().context_snapshot==original
        assert State.snapshot(app.config['TEST_STUDENT'])['state_version']==3
        assert 'private-' not in str(result) and 'learner_state' not in str(result)


def test_changed_evidence_creates_new_request_but_unchanged_inputs_reuse(app):
    app.config['RESOURCE_USER_ACTIVE_LIMIT']=4  # This test holds three tasks to exercise snapshot identity.
    app.config['LEARNER_STATE_READ_MODE']='evidence'
    with app.app_context():
        first=queued(app);same=queued(app)
        assert same['task_id']==first['task_id']
        append(app,'new-evidence');db.session.commit();State.drain()
        changed=queued(app)
        assert changed['task_id']!=first['task_id'] and changed['learning_context']['state_version']==1
        # An explicit retry key returns the original task even after state advances.
        keyed=queued(app,idempotency_key='stable-client-request')
        append(app,'later-evidence');db.session.commit();State.drain()
        assert queued(app,idempotency_key='stable-client-request')['task_id']==keyed['task_id']


def test_failed_retry_keeps_snapshot_options_and_real_api_requirement(app):
    app.config['LEARNER_STATE_READ_MODE']='evidence'
    with app.app_context():
        set_profile(app);task=queued(app,require_real_api=True)
        row=ResourceGenerationTask.query.filter_by(task_id=task['task_id']).one()
        original=deepcopy(row.context_snapshot)
        row.status='failed';row.steps=[{'input_summary':{'require_real_api':False,'pedagogical_context':{'learning_stage':'考试'}}}]
        db.session.commit();set_profile(app,'有工作经验',4)
        app.config['LEARNER_STATE_READ_MODE']='shadow'
        with patch.object(Resources,'run_task'):
            result=Resources.retry(app.config['TEST_STUDENT'],row.task_id)
        retried=ResourceGenerationTask.query.filter_by(task_id=result['task_id']).one()
        assert retried.context_snapshot==original and result['retry_of']==task['task_id']
        assert Resources._requires_real_api(retried) is True
        assert Resources._extract_pedagogical_context(retried)['learning_stage']=='复习'
        assert retried.profile_version==3 and result['learning_context']['state_source']=='evidence'


def test_shadow_mode_does_not_mix_in_evidence_decisions(app):
    app.config['LEARNER_STATE_READ_MODE']='shadow'
    with app.app_context():
        set_profile(app)
        with patch.object(State,'snapshot',side_effect=AssertionError('shadow cannot read evidence')):
            task=queued(app)
        context=ResourceGenerationTask.query.filter_by(task_id=task['task_id']).one().context_snapshot
        assert context['profile']['mistake_pattern']=='legacy-behavior-inference'
        assert context['learner_state'] is None
        assert task['learning_context']['basis']=='profile_only' and task['learning_context']['state_version'] is None


def test_legacy_pending_is_bound_at_execution_but_completed_is_not_backfilled(app):
    with app.app_context():
        set_profile(app)
        row=ResourceGenerationTask(task_id='legacy-queued',user_id=app.config['TEST_STUDENT'],knowledge_key='loop-for',
            requested_types=['learning_bundle'],profile_version=1,steps=Resources._steps())
        completed=ResourceGenerationTask(task_id='legacy-completed',user_id=app.config['TEST_STUDENT'],knowledge_key='loop-for',
            requested_types=['learning_bundle'],status='completed')
        db.session.add_all([row,completed]);db.session.commit()
        assert Resources.get_task(app.config['TEST_STUDENT'],'legacy-completed')['learning_context'] is None
        Resources.run_task(app,'legacy-queued');db.session.rollback();db.session.expire_all()
        result=Resources.get_task(app.config['TEST_STUDENT'],'legacy-queued')
        assert result['status']=='completed',result['error']
        assert result['profile_version']==3 and result['learning_context']['origin']=='legacy_execution'
        assert ResourceGenerationTask.query.filter_by(task_id='legacy-completed').one().context_snapshot is None


def test_tampered_snapshot_fails_without_running_models(app):
    with app.app_context():
        task=queued(app);row=ResourceGenerationTask.query.filter_by(task_id=task['task_id']).one()
        changed=deepcopy(row.context_snapshot);changed['profile']['knowledge_foundation']='forged'
        row.context_snapshot=changed;db.session.commit()
        with patch.object(Resources,'_run_profile_interpreter',side_effect=AssertionError('cannot generate with altered context')) as agent:
            Resources.run_task(app,task['task_id'])
        db.session.expire_all()
        result=Resources.get_task(app.config['TEST_STUDENT'],task['task_id'])
        assert result['status']=='failed' and result['resources']==[] and result['learning_context'] is None
        agent.assert_not_called()


def test_client_cannot_supply_context_or_read_another_students_task(app):
    with app.app_context():task=queued(app,context_snapshot={'user_id':999,'profile_version':999},learning_context={'state_version':999})
    response=app.test_client().get('/api/v1/student/resource-generation/tasks/'+task['task_id'],headers=auth(app,'student'))
    assert response.status_code==200
    assert response.json['data']['profile_version']!=999 and 'context_snapshot' not in response.json['data']
    from flask_jwt_extended import create_access_token
    with app.app_context():
        student=db.session.get(User,app.config['TEST_STUDENT'])
        other=User(username='context-other',email='context-other@example.invalid',password_hash='unused-test-hash',role_id=student.role_id)
        db.session.add(other);db.session.commit()
        token=create_access_token(identity=str(other.id))
    assert app.test_client().get('/api/v1/student/resource-generation/tasks/'+task['task_id'],headers={'Authorization':'Bearer '+token}).status_code==404


def test_migration_preserves_existing_task_and_is_repeatable(app):
    path=Path(__file__).parents[1]/'migrations/versions/20261017_0027_resource_learning_context.py'
    spec=importlib.util.spec_from_file_location('resource_context_migration',path)
    migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
    with app.app_context():
        row=ResourceGenerationTask(task_id='pre-migration',user_id=app.config['TEST_STUDENT'],knowledge_key='loop-for',
            requested_types=['learning_bundle'],status='completed',profile_version=5)
        db.session.add(row);db.session.commit();db.session.remove()
        with db.engine.begin() as conn:
            operations=Operations(MigrationContext.configure(conn))
            with patch.object(migration,'op',operations):
                migration.downgrade();migration.upgrade();migration.upgrade()
            assert {'context_snapshot','context_hash'} <= {column['name'] for column in inspect(conn).get_columns('resource_generation_tasks')}
        old=ResourceGenerationTask.query.filter_by(task_id='pre-migration').one()
        assert old.profile_version==5 and old.status=='completed' and old.context_snapshot is None


@pytest.mark.parametrize('change',['frozen','class'])
def test_queue_rechecks_account_and_class_before_sending_profile(app,change):
    with app.app_context():
        task=queued(app)
        student=db.session.get(User,app.config['TEST_STUDENT'])
        if change=='frozen':student.status='frozen'
        else:student.class_id=None
        db.session.commit()
        with patch.object(Resources,'_run_profile_interpreter') as model:
            Resources.run_task(app,task['task_id'])
        db.session.expire_all()
        result=Resources.get_task(app.config['TEST_STUDENT'],task['task_id'])
        assert result['status']=='failed' and result['resources']==[]
        model.assert_not_called()


def test_model_cannot_replace_server_guidance_and_prompt_excludes_raw_history(app):
    import json
    from agents import resource_pipeline_agents as agents
    app.config['LEARNER_STATE_READ_MODE']='evidence'
    with app.app_context():
        set_profile(app)
        context=Context.capture(app.config['TEST_STUDENT'],'loop-for')
        guidance=Context.guidance(context)
        payloads=[]
        def fake_json(**kwargs):
            payloads.append(json.loads(kwargs['user']))
            return {'learning_guidance':{'state_version':999},'difficulty_target':45}
        with patch.object(agents,'_llm_json',side_effect=fake_json):
            strategy,_,_=Resources._run_profile_interpreter(context['profile'],'loop-for',guidance)
            knowledge,_,_=Resources._run_knowledge_retriever('loop-for',strategy)
            design,_,_=Resources._run_instructional_designer(['learning_bundle'],strategy,knowledge,{},context['profile'])
        assert strategy['learning_guidance']==design['learning_guidance']==guidance
        assert payloads[0]['baseline_strategy']['learning_guidance']==guidance
        assert payloads[1]['profile_strategy']['learning_guidance']==guidance
        assert payloads[2]['learning_guidance']==guidance
        assert all('private-' not in str(payload) and 'learner_state' not in str(payload) for payload in payloads)


def test_generated_bundle_cannot_claim_a_different_state_version(app):
    from app.services.pedagogical_resource import build_local_bundle
    app.config['LEARNER_STATE_READ_MODE']='evidence'
    with app.app_context():
        context=Context.capture(app.config['TEST_STUDENT'],'loop-for')
        guidance=Context.guidance(context)
        analysis={'learning_guidance':guidance,'learning_stage':'复习'}
        forged=build_local_bundle('loop-for',analysis=analysis,profile=context['profile'])
        forged['analysis']={'learning_guidance':{'state_version':999}}
        with patch('agents.llm_client.llm_provider',return_value=('test-only','https://example.invalid','test-model')),patch('app.services.personalized_resource.llm_bundle',return_value=forged):
            generated,_,bundle=Resources._generate_from_bundle('loop-for',['learning_bundle'],context['profile'],analysis,require_real_api=True)
        assert bundle['analysis']['learning_guidance']==guidance
        assert generated[0]['content']['analysis']['learning_guidance']==guidance


def test_synchronous_response_reads_the_committed_worker_result(app):
    with app.app_context():
        task=Resources.create_task(app.config['TEST_STUDENT'],{'knowledge_key':'loop-for','resource_types':['learning_bundle']})
        assert task['status']=='completed',task['error']
        assert len(task['resources'])==1 and task['learning_context']
