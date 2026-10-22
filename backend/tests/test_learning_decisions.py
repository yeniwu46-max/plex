"""Actual consumers share evidence and never silently turn missing knowledge into failure."""
from unittest.mock import patch
from app.models import db, Trial, TrialQuestion, User, Class
from app.services.learner_state import LearnerStateService as State
from app.services.learning_path import LearningPathService
from app.services.practice_question import PracticeQuestionService
from app.services.messenger_chat import MessengerChatService, active_turn, learning_turn
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.knowledge.learner_context_service import LearnerContextService
from app.services.knowledge import KnowledgeService
from test_learner_state import app, snapshot
from test_learner_misconceptions import event


def test_path_and_rag_use_same_focus_version_and_unknowns(app):
    with app.app_context():
        app.config['LEARNER_STATE_READ_MODE'] = 'evidence'
        event(app, 101); event(app, 102); db.session.commit(); State.drain()
        frozen = snapshot(app)
        with patch('app.services.knowledge_graph.KnowledgeGraphService.get_student_graph', side_effect=AssertionError('mixed source')), \
             patch('app.services.mistake.MistakeService.list_weak_knowledge', side_effect=AssertionError('mixed source')):
            path = LearningPathService.plan(app.config['TEST_STUDENT'], state_snapshot=frozen)
            learner = LearnerContextService.build(app.config['TEST_STUDENT'], state_snapshot=frozen)
        assert path['state_version'] == learner.state_version == 2
        assert path['active_node_id'] == learner.learning_decision['concept_id'] == 'loop-for'
        assert path['learning_decision'] == learner.learning_decision
        assert path['remediation_paths'][0]['evidence_ids'] == learner.learning_decision['evidence_ids']
        unknown = [n for n in path['ordered_nodes'] if n['id'] != 'loop-for']
        assert unknown and all(n['mastery_score'] is None and n['status'] == 'unknown' for n in unknown)
        assert '前置已满足' not in path['next_best_action']['reason']


def test_quick_action_keeps_old_snapshot_when_new_grade_arrives(app):
    with app.app_context():
        app.config['LEARNER_STATE_READ_MODE'] = 'evidence'
        event(app, 101); event(app, 102); db.session.commit(); State.drain()
        frozen = snapshot(app)
        uid = app.config['TEST_STUDENT']
        from app.services.tutor_intents import learning_overview
        def overview(user_id, state, question):
            assert state['state_version'] == 2
            result = learning_overview(user_id, state, question)
            event(app, 103, correct=True, signal=False); db.session.commit(); State.drain()
            return result
        pick = {'id': 'bank-900', 'code': 'PY900', 'title': '循环末项', 'knowledge_key': 'loop-for', 'topic': '循环'}
        with patch.object(State, 'snapshot', return_value=frozen) as read, \
             patch.object(KnowledgeService, 'prepare', return_value=None), \
             patch('app.services.tutoring.learning_overview', side_effect=overview), \
             patch.object(PracticeQuestionService, '_list_from_bank', return_value=[pick]):
            result = AgentOrchestrator.messenger_quick_action(uid, 'next_trial')
        assert read.call_count == 1
        assert result['state_version'] == result['question_pick']['state_version'] == 2
        assert result['learning_decision']['review']['state_version'] == 2
        assert snapshot(app)['state_version'] == 3
        assert active_turn(uid) is None


def test_request_local_state_does_not_leak_to_other_user_or_next_turn(app):
    with app.app_context():
        app.config['LEARNER_STATE_READ_MODE'] = 'evidence'
        uid = app.config['TEST_STUDENT']
        with learning_turn(uid) as turn:
            assert active_turn(uid) is turn and active_turn(app.config['TEST_TEACHER']) is None
        assert active_turn(uid) is None


def test_recommendations_exclude_other_classes_and_drafts(app):
    with app.app_context():
        app.config['LEARNER_STATE_READ_MODE'] = 'evidence'
        uid = app.config['TEST_STUDENT']; user = db.session.get(User, uid)
        other = Class(name='另一个班', teacher_id=app.config['TEST_TEACHER'], grade_level=1)
        db.session.add(other); db.session.flush()
        questions = []
        for class_id, status in ((user.class_id, 'running'), (other.id, 'running'), (user.class_id, 'draft')):
            trial = Trial(class_id=class_id, teacher_id=app.config['TEST_TEACHER'], title='scope', status=status)
            db.session.add(trial); db.session.flush()
            q = TrialQuestion(trial_id=trial.id, stem=f'题目 {status} {class_id}', question_type='coding',
                              knowledge_key='loop-for', options=[], correct_index=0)
            q.set_coding_meta({'test_cases': [{'id': '1', 'expected': '1'}]})
            db.session.add(q); db.session.flush(); questions.append(q.id)
        db.session.commit()
        allowed = PracticeQuestionService._list_legacy('loop-for', 100, user_id=uid)
        ids = [q.get('db_question_id') for q in allowed]
        assert questions[0] in ids and questions[1] not in ids and questions[2] not in ids
        bound = LearningPathService._bind_trials('loop-for', uid)
        ids = [int(q['question_id']) for q in bound]
        assert questions[0] in ids and questions[1] not in ids and questions[2] not in ids


def test_aliases_accumulate_in_one_concept(app):
    with app.app_context():
        event(app, 101, correct=True, signal=False)
        row = event(app, 102, correct=True, signal=False)
        row.payload = {**row.payload, 'concept_id': 'loop-for'}
        db.session.commit(); State.drain()
        state = snapshot(app)
        assert len(state['concepts']) == 1 and state['concepts'][0]['independent_count'] == 2


def test_legacy_behavior_profile_is_not_new_measurement(app):
    from app.models import StudentProfile
    with app.app_context():
        app.config['LEARNER_STATE_READ_MODE'] = 'evidence'
        uid = app.config['TEST_STUDENT']
        profile = StudentProfile.query.filter_by(user_id=uid).first()
        if profile is None:
            profile = StudentProfile(user_id=uid); db.session.add(profile)
        profile.dimensions = {
            'knowledge_foundation': {'value': '历史复习已掌握', 'source': 'behavior'},
            'explanation_preference': {'value': '举例讲解', 'source': 'confirmed'},
        }
        db.session.commit()
        learner = LearnerContextService.build(uid)
        assert learner.mastery == {} and not learner.knowledge_foundation
        assert learner.explanation_preference == 'example_first'
        assert StudentProfile.query.filter_by(user_id=uid).one().dimensions['knowledge_foundation']['value'] == '历史复习已掌握'
