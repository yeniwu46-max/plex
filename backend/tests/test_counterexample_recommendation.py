"""Published, scoped, versioned challenge suggestions from the same learning evidence."""
from unittest.mock import patch
import pytest
import uuid
from test_learner_state import app
from test_learner_misconceptions import event
from test_counterexample_attempts import publish, submit, body_for, fake_run
from test_counterexample_gates import make_challenge, review
from test_tutoring_modes import dependencies, ask, body, candidate, Provider
from test_tutor_context import headers
from app.models import db, User, Class, TrialQuestion
from app.models.counterexample import CounterexampleVersion as Version, CounterexampleValidation as Validation, CounterexampleChallenge as Challenge
from app.services.learner_state import LearnerStateService as State
from app.services.learner_decision import LearnerDecisionService
from app.services.counterexample_recommendation import recommend
from app.services.tutor_intents import learning_overview


def decision(app, count=2):
    for q in range(count): event(app, 101+q)
    db.session.commit(); State.drain()
    snapshot = State.snapshot(app.config['TEST_STUDENT'])
    return snapshot, LearnerDecisionService.from_snapshot(snapshot)


def test_repeat_evidence_selects_reviewed_matching_task_without_hidden_content(app):
    row=publish(app)
    with app.app_context():
        snapshot, choice=decision(app)
        assert choice['misconception_kind']=='loop_end_excluded'
        pick=recommend(app.config['TEST_STUDENT'], choice)
        assert pick['id']==row['id'] and pick['version']==row['manifest_hash']
        assert pick['state_version']==snapshot['state_version']==2
        assert pick['evidence_ids']==choice['hint']['evidence_ids'] and len(pick['evidence_ids'])==2
        assert set(pick)=={'id','title','revision','version','concept_id','state_version','evidence_ids','reason','practice_path'}
        assert '理解偏差' in pick['reason'] and '已确认' not in pick['reason']
        assert State.snapshot(app.config['TEST_STUDENT'])==snapshot


@pytest.mark.parametrize('change',['draft','withdrawn','other_class','blocked','invalid_report','wrong_kind','wrong_concept','one_failure','no_samples'])
def test_ineligible_challenges_are_not_recommended(app,change):
    row=make_challenge(app) if change=='draft' else publish(app)
    with app.app_context():
        _,choice=decision(app, 0 if change=='no_samples' else 1 if change=='one_failure' else 2)
        challenge=db.session.get(Challenge,row['id']); v=db.session.get(Version,row['version_id'])
        if change=='withdrawn': challenge.published_revision=None
        if change=='other_class':
            other=Class(name='other',teacher_id=app.config['TEST_TEACHER'],grade_level=1); db.session.add(other);db.session.flush();challenge.class_id=other.id
        if change=='blocked': v.blocked_reason='material_issue'
        if change=='invalid_report': db.session.get(Validation,v.reviewed_report_id).report={'passed':False}
        # Use a valid immutable publication but ask for a different teaching target.
        if change=='wrong_kind': choice['misconception_kind']='recursion_missing_guard'
        if change=='wrong_concept': choice['concept_id']='recursion'
        db.session.commit()
        assert recommend(app.config['TEST_STUDENT'],choice) is None


def test_completed_challenge_is_skipped_and_ordinary_practice_remains(app):
    row=publish(app)
    with patch('app.services.counterexample_validation.CodeExecutionService.run',side_effect=fake_run):
        assert submit(app,row,body_for(row)).status_code==200
    with app.app_context():
        snapshot,choice=decision(app)
        assert recommend(app.config['TEST_STUDENT'],choice) is None
        ordinary={'id':'bank-1','title':'独立循环练习','knowledge_key':'loop-for'}
        with patch('app.services.practice_question.PracticeQuestionService.recommend_for_student',return_value=ordinary):
            answer=learning_overview(app.config['TEST_STUDENT'],snapshot,'推荐一道练习')
        assert answer['question_pick']['id']=='bank-1' and answer['counterexample_pick'] is None


def test_response_links_share_frozen_state_and_cache_rechecks_withdrawal(app,dependencies):
    row=publish(app)
    with app.app_context():
        snapshot,choice=decision(app)
    payload=body(app,question='只提示下一步')
    provider=Provider(candidate())
    first=ask(app,payload,provider).json['data']
    assert first['counterexample_pick']['state_version']==first['teaching_plan']['state_version']==2
    assert first['counterexample_pick']['id']==row['id']
    assert ask(app,payload,provider).json['data']==first and len(provider.calls)==2
    assert review(app,row,{'action':'withdraw','manifest_hash':row['manifest_hash']}).status_code==200
    retried=ask(app,payload,provider).json['data']
    restored=app.test_client().get('/api/v1/student/tutor/turns/'+payload['request_id'],headers=headers(app)).json['data']
    assert retried['counterexample_pick'] is None and restored['counterexample_pick'] is None
    assert restored['summary']==first['summary'] and '暂不可访问' in restored['recommendation_notice']
    assert len(provider.calls)==2


def test_next_practice_uses_evidence_link_without_calling_model(app):
    row=publish(app)
    with app.app_context(): snapshot,_=decision(app)
    with patch('app.services.tutoring.get_llm_provider',side_effect=AssertionError('no model for practice routing')):
        result=app.test_client().post('/api/v1/student/messenger/chat',headers=headers(app),json={
            'request_id':str(uuid.uuid4()), 'message':'下一道题该练什么？'}).json['data']['tutor']
    assert result['generation_mode']=='learning_records' and result['question_pick'] is None
    assert result['counterexample_pick']['id']==row['id']


def test_concept_only_and_rejected_hint_do_not_add_targeted_challenge(app,dependencies):
    publish(app)
    with app.app_context():
        decision(app)
        q=db.session.get(TrialQuestion,app.config['TEST_QUESTION']); q.trial.tutoring_policy='concept_only';db.session.commit()
    assert not ask(app,body(app),Provider(candidate())).json['data'].get('counterexample_pick')
    with app.app_context():
        q=db.session.get(TrialQuestion,app.config['TEST_QUESTION']);q.trial.tutoring_policy='guided';db.session.commit()
    app.config['TUTOR_MODELS_ENABLED']=False
    assert not ask(app,body(app),Provider(candidate())).json['data'].get('counterexample_pick')
