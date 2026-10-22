"""Student-owned attempts, exam deadlines and trash boundaries on real SQLite."""
import uuid
from datetime import timedelta
from unittest.mock import patch
import pytest
from test_learner_state import app
from test_tutor_context import headers
from app.models import db, Problem, User
from app.models.student_practice import MockExam, PracticeAttempt
from app.models.personalized_resource import ResourceGenerationTask, PersonalizedLearningResource
from app.services.student_practice import StudentPractice, MockExams
from app.services.resource_trash import ResourceTrash
from app.services.tutor_context import TutorContextService, TutorContextError
from app.utils.time import utc_now


def seed_questions():
    for i in range(8):
        db.session.add(Problem(id=88000+i, problem_no=f'QX{i:04}', title_cn=f'测试题 {i}',
            kg_node_id='loop-for' if i<4 else 'loop-while', description_cn='输出 1',
            test_cases_json=[{'id':'one','expected':'1','hidden':True}], source_kind='manual',
            is_active=True, needs_review=False, question_type='coding', run_mode='stdout'))
    db.session.commit()


def test_favorites_submission_history_and_owned_access(app):
    with app.app_context():
        seed_questions()
        uid=app.config['TEST_STUDENT']
        ref='bank-88000'
        StudentPractice.favorite(uid,ref,True)
        assert StudentPractice.catalog(uid,{'favorite':'true'})['total']==1
        rid=str(uuid.uuid4())
        with patch('app.services.student_practice.CodeExecutionService.submit', return_value={'all_passed':False,'results':[]}) as run:
            result=StudentPractice.submit(uid,ref,{'request_id':rid,'code':'print(2)'})
            assert StudentPractice.submit(uid,ref,{'request_id':rid,'code':'print(2)'})['id']==result['id']
            assert run.call_count==1
        assert StudentPractice.catalog(uid,{'favorite':'true','done':'yes'})['total']==1
        assert StudentPractice.catalog(uid,{'favorite':'true','done':'no'})['total']==0
        assert StudentPractice.history(uid,{})['items'][0]['code']=='print(2)'
        from app.services.learner_state import LearnerStateService
        assert LearnerStateService.drain() == 1
        snapshot = LearnerStateService.snapshot(uid)
        concept = next(c for c in snapshot['concepts'] if c['concept_id'] == 'loop-for')
        assert concept['independent_count'] == 1
        assert concept['independent_success'] == 0
        with pytest.raises(TutorContextError):
            TutorContextService.resolve(app.config['TEST_TEACHER'],{'submission_id':rid})
        with pytest.raises(TutorContextError):
            StudentPractice.submit(uid,ref,{'request_id':rid,'code':'print(3)'})


def test_six_unique_questions_scoped_resume_lock_grade(app):
    with app.app_context():
        seed_questions(); uid=app.config['TEST_STUDENT']
        exam=MockExams.create(uid,{'knowledge_keys':['loop-for','loop-while']})
        assert len({q['id'] for q in exam['questions']})==6
        assert {q['knowledge_key'] for q in exam['questions']}=={'loop-for','loop-while'}
        assert all('test_cases' not in q and 'hint' not in q for q in exam['questions'])
        assert MockExams.create(uid,{})['id']==exam['id']
        context=TutorContextService.resolve(uid,{'question_ref':exam['questions'][0]['id']})
        assert context.task['tutoring_policy']=='disabled'
        answers={q['id']:'print(1)' for q in exam['questions']}
        saved=MockExams.save(uid,exam['id'],{'answers':answers,'revision':0})
        assert saved['revision']==1 and saved['answers']==answers
        with pytest.raises(TutorContextError):
            MockExams.save(uid,exam['id'],{'answers':{},'revision':0})
        MockExams.lock(uid,exam['id']);MockExams.lock(uid,exam['id'])
        with pytest.raises(TutorContextError):
            MockExams.save(uid,exam['id'],{'answers':{},'revision':1})
        with patch('app.services.student_practice.CodeExecutionService.submit',return_value={'all_passed':True,'results':[]}) as run:
            MockExams.grade(exam['id']);MockExams.grade(exam['id'])
            assert run.call_count==6
        assert MockExams.view(uid,exam['id'])['score']==100
        assert PracticeAttempt.query.filter_by(source='mock_exam').count()==6
        assert TutorContextService.resolve(uid,{'question_ref':exam['questions'][0]['id']}).task['tutoring_policy']=='guided'


def test_insufficient_questions_expiry_and_failure_not_wrong(app):
    with app.app_context():
        seed_questions();uid=app.config['TEST_STUDENT']
        with pytest.raises(TutorContextError):MockExams.create(uid,{'knowledge_keys':['loop-for']})
        exam=MockExams.create(uid,{})
        row=db.session.get(MockExam,exam['id']);row.answers={row.questions[0]['item']['id']:'print(1)'};row.deadline=utc_now()-timedelta(seconds=1);db.session.commit()
        assert MockExams.view(uid,row.id)['status']=='pending'
        with patch('app.services.student_practice.CodeExecutionService.submit',side_effect=RuntimeError('unavailable')):
            with pytest.raises(RuntimeError):MockExams.grade(row.id)
        db.session.refresh(row)
        assert row.status=='pending' and row.score is None and not row.results


def seed_resources(uid):
    task=ResourceGenerationTask(task_id=str(uuid.uuid4()),user_id=uid,knowledge_key='loop',requested_types=['learning_bundle','lesson_document'],status='completed')
    db.session.add(task);db.session.flush()
    rows=[]
    for kind in ['lesson_document','exercise_set','learning_bundle']:
        row=PersonalizedLearningResource(user_id=uid,generation_task_id=task.task_id,knowledge_key='loop',knowledge_label='循环',resource_type=kind,title=kind,recommendation_reason='测试',content={'explain':'private-text','exercises':[{'stem':'private-exercise'}],'markdown':'full copy'},citations=[])
        db.session.add(row);rows.append(row)
    db.session.commit();return task,rows


def test_trash_single_package_restore_and_expiry(app):
    with app.app_context():
        uid=app.config['TEST_STUDENT'];task,rows=seed_resources(uid)
        first=ResourceTrash.move(uid,resource_id=rows[0].id);db.session.refresh(rows[0]);expiry=rows[0].expires_at
        package=ResourceTrash.move(uid,task_id=task.task_id)
        assert package['count']==2
        db.session.refresh(rows[0]);assert rows[0].expires_at==expiry
        assert ResourceTrash.restore(uid,batch_id=package['batch_id'])['count']==2
        db.session.refresh(rows[0]);db.session.refresh(rows[2]);assert rows[0].deleted_at
        bundle=rows[2].to_dict();assert 'private-text' not in str(bundle['content'])
        with pytest.raises(TutorContextError):ResourceTrash.restore(app.config['TEST_TEACHER'],batch_id=first['batch_id'])
        rows[0].expires_at=utc_now()-timedelta(seconds=1);db.session.commit()
        with pytest.raises(TutorContextError):ResourceTrash.restore(uid,resource_id=rows[0].id)
        assert ResourceTrash.purge()==1
        db.session.refresh(rows[0]);assert rows[0].content=={} and rows[0].deleted_at


def test_new_routes_auth_and_ownership(app):
    client=app.test_client()
    with app.app_context():
        seed_questions()
    assert client.get('/api/v1/student/practice-questions/bank-88000', headers=headers(app)).status_code == 200
    assert client.get('/api/v1/student/practice-questions/bank-99999999', headers=headers(app)).status_code == 404
    staff = client.get('/api/v1/student/practice-questions', headers=headers(app, teacher=True))
    assert staff.status_code == 200 and staff.json['data']['items']
    assert client.get('/api/v1/student/practice-history').status_code==401
    assert client.get('/api/v1/student/practice-history',headers=headers(app,teacher=True)).status_code==403
    assert client.get('/api/v1/student/mock-exams/not-owned',headers=headers(app)).status_code==404
    assert client.post('/api/v1/student/mock-exams',headers=headers(app),json=[]).status_code==400


def test_concurrent_exam_creation_is_single_per_user(app):
    from concurrent.futures import ThreadPoolExecutor
    with app.app_context():
        seed_questions();uid=app.config['TEST_STUDENT']
    def create():
        with app.app_context():
            return MockExams.create(uid,{})['id']
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids=list(pool.map(lambda _:create(),range(2)))
    assert len(set(ids))==1


def test_mcq_submission_is_server_graded_and_idempotent(app):
    with app.app_context():
        uid = app.config['TEST_STUDENT']
        db.session.add(Problem(id=89000, problem_no='CHOICE01', title_cn='选择题', kg_node_id='loop-for',
            description_cn='range(2) 的最后一个值？', question_type='mcq', options_json=['1', '2'],
            correct_index=0, is_active=True, needs_review=False, source_kind='manual'))
        db.session.commit()
        request = {'request_id': str(uuid.uuid4()), 'selected_index': 1, 'code': '', 'all_passed': True}
        result = StudentPractice.submit(uid, 'bank-89000', request)
        assert result['result']['all_passed'] is False
        assert StudentPractice.submit(uid, 'bank-89000', request)['id'] == result['id']
        with pytest.raises(TutorContextError):
            StudentPractice.submit(uid, 'bank-89000', {**request, 'selected_index': 0})


def test_teacher_trial_ignores_client_score(app):
    from app.models import TrialQuestion, TrialParticipation
    from app.services.assignment import AssignmentService
    from app.services.trial import TrialService
    with app.app_context():
        uid, qid = app.config['TEST_STUDENT'], app.config['TEST_QUESTION']
        question = db.session.get(TrialQuestion, qid)
        AssignmentService.submit_answer(uid, qid, 1)
        part = TrialParticipation.query.filter_by(user_id=uid, trial_id=question.trial_id).one()
        part.status = 'joined'
        db.session.commit()
        result = TrialService.complete_trial(uid, question.trial_id, score=100)
        assert result['participation']['score'] == 0


def test_waiting_without_opponent_then_shared_server_questions(app):
    from app.services.duel_match import DuelMatchService as Duel
    from app.services.presence import PresenceService as Presence
    with app.app_context():
        seed_questions();uid=app.config['TEST_STUDENT'];student=db.session.get(User,uid)
        other=User(username='duel-peer',email='duel-peer@example.test',password_hash='unused',role_id=student.role_id,class_id=student.class_id,status='active')
        db.session.add(other);db.session.commit()
        Duel._queue.clear();Duel._matches.clear();Duel._user_match.clear();Presence._heartbeats.clear()
        assert Duel.join(uid)['status']=='waiting'
        match=Duel.join(other.id)
        assert match['status']=='matched'
        first=Duel.status(uid)
        assert first['question_ids']==match['question_ids']
        assert first['questions']==match['questions'] and len(first['questions'])==3
        assert all(q['id'].startswith('bank-') for q in first['questions'])
        Duel.cancel(uid)
        assert Duel.status(other.id)['status']=='idle'
        Duel._queue.clear();Duel._matches.clear();Duel._user_match.clear();Presence._heartbeats.clear()


def test_sqlite_migration_round_trip(tmp_path):
    import importlib.util
    from pathlib import Path
    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    path=Path(__file__).parents[1]/'migrations/versions/20261022_0035_student_practice.py'
    spec=importlib.util.spec_from_file_location('experience_migration',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    engine=sa.create_engine('sqlite:///'+str(tmp_path/'migration.db'))
    with engine.begin() as connection:
        connection.exec_driver_sql('CREATE TABLE users (id INTEGER PRIMARY KEY)')
        connection.exec_driver_sql('CREATE TABLE personalized_learning_resources (id INTEGER PRIMARY KEY)')
        connection.exec_driver_sql('INSERT INTO personalized_learning_resources VALUES (1)')
        with Operations.context(MigrationContext.configure(connection)):
            module.upgrade();module.upgrade()
            assert 'student_mock_exams' in sa.inspect(connection).get_table_names()
            assert connection.exec_driver_sql('SELECT count(*) FROM personalized_learning_resources').scalar()==1
            module.downgrade()
        assert [c['name'] for c in sa.inspect(connection).get_columns('personalized_learning_resources')]==['id']
    engine.dispose()
