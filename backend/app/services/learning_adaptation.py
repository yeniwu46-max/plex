"""Deterministic learning interventions; LLM output never controls this policy."""
from __future__ import annotations

from app.models import LearningAdaptation, StudentProfile, TrialQuestion, TrialQuestionProgress, db
from app.utils.time import utc_now


class LearningAdaptationService:
    REMEDIAL_TARGET = 3

    @staticmethod
    def _plan(key: str) -> dict:
        return {
            'action': 'visual_micro_practice', 'difficulty': 'lower', 'knowledge_key': key,
            'resources': ['visual_execution', 'micro_practice'], 'micro_practice_count': 3,
            'recovery_rule': '完成 3 道补救练习且至少答对 2 道后恢复常规难度',
        }

    @classmethod
    def record_answer(cls, user_id: int, question: TrialQuestion, correct: bool) -> dict | None:
        key = question.knowledge_key or 'python'
        active = LearningAdaptation.query.filter_by(user_id=user_id, knowledge_key=key, status='active').first()
        if active:
            active.remedial_completed += 1
            active.remedial_correct += int(bool(correct))
            if active.remedial_completed >= cls.REMEDIAL_TARGET and active.remedial_correct >= 2:
                active.status = 'recovered'
                active.resolved_at = utc_now()
            db.session.commit()
            return active.to_dict()
        if correct:
            return None
        rows = (
            TrialQuestionProgress.query.join(TrialQuestion)
            .filter(TrialQuestionProgress.user_id == user_id, TrialQuestion.knowledge_key == key,
                    TrialQuestionProgress.status == 'completed')
            .order_by(TrialQuestionProgress.answered_at.desc()).limit(3).all()
        )
        if len(rows) != 3 or any(row.is_correct for row in rows):
            return None
        profile = StudentProfile.query.filter_by(user_id=user_id).first()
        action = LearningAdaptation(
            user_id=user_id, knowledge_key=key,
            trigger_evidence={'rule': 'three_consecutive_errors', 'question_ids': [row.question_id for row in rows]},
            action_plan=cls._plan(key), profile_version=profile.version if profile else 0,
        )
        db.session.add(action)
        db.session.commit()
        return action.to_dict()

    @staticmethod
    def active_for_student(user_id: int) -> list[dict]:
        return [row.to_dict() for row in LearningAdaptation.query.filter_by(user_id=user_id, status='active').order_by(LearningAdaptation.created_at.desc()).all()]

    @staticmethod
    def active_for_key(user_id: int, knowledge_key: str | None) -> dict | None:
        row = LearningAdaptation.query.filter_by(
            user_id=user_id, knowledge_key=knowledge_key or 'python', status='active'
        ).order_by(LearningAdaptation.created_at.desc()).first()
        return row.to_dict() if row else None

    @staticmethod
    def teacher_summary(user_id: int) -> dict:
        active = LearningAdaptationService.active_for_student(user_id)
        return {'active_interventions': active, 'risk_level': 'needs_support' if active else 'stable'}
