"""Version-pinned evidence pages never mix identities, new events or raw payloads."""
from datetime import timedelta
from unittest.mock import patch
import time
import pytest
from sqlalchemy import select

from test_learner_state import app, append
from test_tutor_context import headers
from app.models import db, User, Class
from app.models.learner_state import LearningEvent, LearnerState, LearnerStateChange
from app.services.learner_state import LearnerStateService as State
from app.services.learning_evidence import page, _serializer
from app.services.tutor_context import TutorContextError
from app.utils.time import utc_now


def seed(app, count=3, offset=0):
    for i in range(count):
        # Arrival order deliberately differs from occurrence time.
        append(app,str(offset+i),when=utc_now()-timedelta(days=i))
    db.session.commit()
    assert State.drain(count+1)==count
    db.session.remove()


def own(app, **kwargs):
    return page(app.config['TEST_STUDENT'],app.config['TEST_STUDENT'],**kwargs)


def test_evidence_pages_are_complete_and_stable_while_new_events_arrive(app):
    with app.app_context():
        seed(app,45)
        first=own(app)
        assert first['snapshot_version']==45 and first['latest_version']==45 and first['has_more']
        assert [r['version'] for r in first['items']]==list(range(45,25,-1))
        seed(app,2,100)
        second=own(app,cursor=first['next_cursor'])
        replay=own(app,cursor=first['next_cursor'])
        assert replay['items']==second['items'] and replay['snapshot_version']==second['snapshot_version']
        assert _serializer().loads(replay['next_cursor'])==_serializer().loads(second['next_cursor'])
        assert second['snapshot_version']==45 and second['latest_version']==47
        last=own(app,cursor=second['next_cursor'])
        assert not last['has_more'] and last['next_cursor'] is None
        combined=first['items']+second['items']+last['items']
        assert [r['version'] for r in combined]==list(range(45,0,-1))
        assert len({r['event_id'] for r in combined})==45
        assert own(app)['items'][0]['version']==47


def test_evidence_page_can_start_from_visible_snapshot_and_change_page_size(app):
    with app.app_context():
        seed(app,7)
        first=own(app,limit=2,snapshot_version=5)
        assert [r['version'] for r in first['items']]==[5,4]
        second=own(app,limit=50,cursor=first['next_cursor'])
        assert [r['version'] for r in second['items']]==[3,2,1]
        assert not second['has_more']


def test_evidence_empty_and_unprocessed_are_not_fabricated_history(app):
    with app.app_context():
        append(app,'pending');bad=append(app,'bad');bad.payload={**bad.payload,'evidence_scope':'client_tests'}
        db.session.commit()
        empty=own(app)
        assert empty['snapshot_version']==0 and empty['items']==[] and empty['next_cursor'] is None
        assert State.drain()==1
        assert len(own(app)['items'])==1
        assert own(app,snapshot_version=0)['items']==[]


def test_evidence_duplicate_event_100_times_is_one_history_change(app):
    with app.app_context():
        for _ in range(100):append(app,'same-formal-evidence')
        db.session.commit()
        assert State.drain()==1
        assert LearningEvent.query.count()==LearnerStateChange.query.count()==1
        result=own(app)
        assert result['snapshot_version']==1 and len(result['items'])==1


def test_evidence_payload_allowlist_matches_compact_snapshot(app):
    with app.app_context():
        event=append(app)
        event.payload={**event.payload,'question_title':'Q'*150,'question_id':True,
            'answer_key':'DO_NOT_EXPOSE','test_cases':['HIDDEN_TEST'], 'submitted_code':'PRIVATE_CODE',
            'note':'PRIVATE_NOTE','raw_response':'RAW_MODEL_RESPONSE','code_hash':'PRIVATE_HASH'}
        db.session.commit();State.drain();db.session.remove()
        item=own(app)['items'][0]
        assert item==State.snapshot(app.config['TEST_STUDENT'])['changes'][0]
        assert item['question_title']=='Q'*120 and item['question_id'] is None
        assert item['policy_version']=='evidence-heuristic-v2'
        for secret in ('DO_NOT_EXPOSE','HIDDEN_TEST','PRIVATE_CODE','PRIVATE_NOTE','RAW_MODEL_RESPONSE','PRIVATE_HASH'):
            assert secret not in str(item)


def test_evidence_cursor_binds_actor_student_and_current_class_access(app):
    with app.app_context():
        seed(app)
        uid=app.config['TEST_STUDENT'];teacher=app.config['TEST_TEACHER']
        student_cursor=own(app,limit=1)['next_cursor']
        with pytest.raises(TutorContextError) as caught:page(teacher,uid,cursor=student_cursor)
        assert caught.value.status==403
        teacher_cursor=page(teacher,uid,limit=1)['next_cursor']
        classroom=Class(name='Other class',teacher_id=uid,grade_level=1)
        db.session.add(classroom);db.session.flush();db.session.get(User,uid).class_id=classroom.id
        db.session.commit()
        with pytest.raises(TutorContextError) as caught:page(teacher,uid,cursor=teacher_cursor)
        assert caught.value.status==403
        assert own(app,cursor=student_cursor)['items']


def test_evidence_other_account_and_changed_role_cannot_reuse_cursor(app):
    with app.app_context():
        seed(app)
        uid=app.config['TEST_STUDENT'];original=db.session.get(User,uid)
        other=User(username='history-other',email='history-other@example.invalid',password_hash='unused',role_id=original.role_id)
        db.session.add(other);db.session.commit();other_id=other.id
        cursor=own(app,limit=1)['next_cursor']
        for actor,target in ((other_id,uid),(other_id,other_id)):
            with pytest.raises(TutorContextError) as caught:page(actor,target,cursor=cursor)
            assert caught.value.status==403
        original.role_id=db.session.get(User,app.config['TEST_TEACHER']).role_id;db.session.commit()
        with pytest.raises(TutorContextError) as caught:own(app,cursor=cursor)
        assert caught.value.status==403


def test_evidence_cursor_signature_expiry_and_state_reset_require_refresh(app):
    with app.app_context():
        seed(app)
        token=own(app,limit=1)['next_cursor']
        with pytest.raises(TutorContextError) as caught:own(app,cursor=token+'x')
        assert caught.value.status==400
        payload=_serializer().loads(token)
        earlier=time.time()-3602
        with patch('itsdangerous.timed.time.time',return_value=earlier):expired=_serializer().dumps(payload)
        with pytest.raises(TutorContextError) as caught:own(app,cursor=expired)
        assert caught.value.status==410
        state=db.session.scalar(select(LearnerState).where(LearnerState.user_id==app.config['TEST_STUDENT']))
        state.version=1;db.session.commit()
        with pytest.raises(TutorContextError) as caught:own(app,cursor=token)
        assert caught.value.status==409


@pytest.mark.parametrize('query',['limit=0','limit=51','limit=-1','limit=2.5','limit=999999999999',
                                'limit=1&limit=2','cursor=','snapshot_version=-1','snapshot_version=2.0',
                                'snapshot_version=2147483648'])
def test_evidence_api_rejects_invalid_pagination(app,query):
    response=app.test_client().get('/api/v1/student/learning-evidence?'+query,headers=headers(app))
    assert response.status_code==400


def test_evidence_api_permissions_and_version_conflict(app):
    client=app.test_client();path='/api/v1/student/learning-evidence'
    assert client.get(path).status_code==401
    assert client.get(path,headers=headers(app,True)).status_code==403
    response=client.get(path,headers=headers(app))
    assert response.status_code==200 and response.headers['Cache-Control']=='no-store'
    assert client.get(path+'?snapshot_version=1',headers=headers(app)).status_code==409
    teacher_path=f"/api/v1/teacher/students/{app.config['TEST_STUDENT']}/learning-evidence"
    assert client.get(teacher_path,headers=headers(app)).status_code==403
    assert client.get(teacher_path,headers=headers(app,True)).status_code==200
    assert client.get('/api/v1/teacher/students/2147483647/learning-evidence',headers=headers(app,True)).status_code==403


def test_evidence_conflicting_cursor_and_version_rejected_and_get_is_read_only(app):
    with app.app_context():
        seed(app)
        token=own(app,limit=1)['next_cursor']
        before=(LearningEvent.query.count(),LearnerStateChange.query.count())
        for _ in range(3):own(app,cursor=token)
        assert before==(LearningEvent.query.count(),LearnerStateChange.query.count())
        with pytest.raises(TutorContextError):own(app,cursor=token,snapshot_version=3)


def test_evidence_cursor_payload_bounds_and_inactive_actor_are_rechecked(app):
    with app.app_context():
        seed(app)
        payload=_serializer().loads(own(app,limit=1)['next_cursor'])
        for mutation in ({'before':999},{'format':True},{'student':True},{'version':-1},{'unexpected':'field'}):
            token=_serializer().dumps({**payload,**mutation})
            with pytest.raises(TutorContextError) as caught:own(app,cursor=token)
            assert caught.value.status==400
        db.session.get(User,app.config['TEST_STUDENT']).status='frozen';db.session.commit()
        with pytest.raises(TutorContextError) as caught:own(app)
        assert caught.value.status==403
