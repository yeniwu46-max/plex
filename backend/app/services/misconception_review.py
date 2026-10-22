"""Teacher decisions use the same event/proposal writer, not a parallel state store."""
import uuid
from sqlalchemy import select, update
from app.models import db, User, LearnerState, LearnerMisconception
from app.services.learner_state import LearnerStateService as State
from app.utils.access import teacher_owns_class


class ReviewConflict(ValueError):
    pass


class MisconceptionReviewService:
    @staticmethod
    def review(actor_id, student_id, misconception_id, data):
        if not isinstance(data, dict):
            raise ValueError('审核内容无效')
        try:
            request_id = str(uuid.UUID(data.get('request_id', '')))
        except (ValueError, TypeError, AttributeError):
            raise ValueError('请提供有效的审核请求编号') from None
        action, revision, note = data.get('action'), data.get('expected_revision'), data.get('note')
        if action not in ('confirm', 'dismiss', 'reopen') or type(revision) is not int or revision < 1:
            raise ValueError('审核动作或版本无效')
        if not isinstance(note, str) or not 1 <= len(note.strip()) <= 300:
            raise ValueError('请填写 1–300 字的核对说明')
        actor, student = db.session.get(User, actor_id), db.session.get(User, student_id)
        if (not actor or not actor.role or actor.role.name != 'teacher' or not student or not student.role
            or student.role.name != 'student' or not teacher_owns_class(actor, student.class_id)):
            raise PermissionError('无权审核该学生的学习状态')
        # SQLite has no SELECT FOR UPDATE; acquire its write reservation before
        # reading the revision. MySQL takes the same per-state row lock here.
        db.session.execute(update(LearnerState).where(LearnerState.user_id == student_id,
            LearnerState.course == 'python').values(version=LearnerState.version)
            .execution_options(synchronize_session=False))
        state = db.session.scalar(select(LearnerState).where(LearnerState.user_id == student_id,
            LearnerState.course == 'python').execution_options(populate_existing=True).with_for_update())
        row = db.session.scalar(select(LearnerMisconception).where(LearnerMisconception.id == misconception_id,
            LearnerMisconception.state_id == state.id if state else False)
            .execution_options(populate_existing=True).with_for_update())
        if not row:
            raise LookupError('误概念候选不存在')
        payload = {'misconception_id': row.id, 'concept_id': row.concept_id, 'expected_revision': revision,
                   'reviewer_id': actor_id, 'action': action, 'note': note.strip(), 'evidence_scope': 'teacher_review'}
        event = State.append(user_id=student_id, kind='misconception_reviewed', source_type='teacher_review',
            source_id=row.id, source_version=request_id, payload=payload)
        if event.payload != payload:
            raise ReviewConflict('请求编号已用于不同的审核内容，请刷新后重试')
        if event.status != 'done':
            if row.revision != revision:
                raise ReviewConflict('这条证据已更新，请刷新后重新核对')
            State._commit_proposal(db.session, state, event, State.propose(event, state.version))
        db.session.commit()
        return State.snapshot(student_id)
