"""学生端：教师发布试炼题目的拉取与作答"""
from datetime import datetime

from app.models import Trial, TrialQuestion, TrialQuestionProgress, User, db
from app.services.daily_quest import DailyQuestService
from app.services.question_generator import QuestionGenerator
from app.services.trial import TrialService


class AssignmentService:
    @staticmethod
    def _active_trials_for_student(user: User):
        if not user.class_id:
            return []
        trials = (
            Trial.query.filter_by(class_id=user.class_id)
            .filter(Trial.status.in_(('running', 'scheduled')))
            .order_by(Trial.created_at.desc())
            .all()
        )
        dirty = False
        active = []
        for trial in trials:
            if TrialService._sync_trial_status(trial):
                dirty = True
            if TrialService.effective_status(trial) in ('running', 'scheduled'):
                active.append(trial)
        if dirty:
            db.session.commit()
        return active

    @staticmethod
    def _get_or_create_progress(user_id: int, question_id: int) -> TrialQuestionProgress:
        row = TrialQuestionProgress.query.filter_by(user_id=user_id, question_id=question_id).first()
        if row:
            return row
        row = TrialQuestionProgress(user_id=user_id, question_id=question_id, status='pending')
        db.session.add(row)
        db.session.flush()
        return row

    @staticmethod
    def list_for_student(user_id: int, include_completed: bool = False):
        user = User.query.get(user_id)
        if not user:
            raise ValueError('用户不存在')

        trials = AssignmentService._active_trials_for_student(user)
        for trial in trials:
            QuestionGenerator.ensure_for_trial(trial)

        items = []
        pending_count = 0
        for trial in trials:
            teacher_name = trial.teacher.real_name if trial.teacher else '老师'
            questions = (
                TrialQuestion.query.filter_by(trial_id=trial.id)
                .order_by(TrialQuestion.sort_order.asc(), TrialQuestion.id.asc())
                .all()
            )
            for question in questions:
                progress = AssignmentService._get_or_create_progress(user_id, question.id)
                if progress.status == 'completed' and not include_completed:
                    continue
                if progress.status == 'pending':
                    pending_count += 1
                items.append(
                    {
                        'id': question.id,
                        'trial_id': trial.id,
                        'trial_title': trial.title,
                        'teacher_name': teacher_name,
                        'knowledge_key': question.knowledge_key,
                        'knowledge_label': QuestionGenerator.label_for_key(question.knowledge_key),
                        'stem': question.stem,
                        'options': question.to_dict()['options'],
                        'status': progress.status,
                        'is_correct': progress.is_correct,
                        'selected_index': progress.selected_index,
                        'sort_order': question.sort_order,
                        'published_at': trial.starts_at.isoformat() if trial.starts_at else None,
                    }
                )
        db.session.commit()

        return {
            'pending_count': pending_count,
            'total_count': len(items) if include_completed else pending_count,
            'items': items,
        }

    @staticmethod
    def submit_answer(user_id: int, question_id: int, selected_index: int):
        user = User.query.get(user_id)
        if not user:
            raise ValueError('用户不存在')
        question = TrialQuestion.query.get(question_id)
        if not question:
            raise ValueError('题目不存在')

        trial = Trial.query.get(question.trial_id)
        if not trial or trial.class_id != user.class_id:
            raise PermissionError('无权作答该题目')
        if TrialService.effective_status(trial) not in ('running', 'scheduled'):
            raise ValueError('试炼已结束，无法作答')

        progress = AssignmentService._get_or_create_progress(user_id, question_id)
        if progress.status == 'completed':
            raise ValueError('该题已完成')

        selected = int(selected_index)
        is_correct = selected == int(question.correct_index)
        progress.status = 'completed'
        progress.selected_index = selected
        progress.is_correct = is_correct
        progress.answered_at = datetime.utcnow()
        db.session.commit()

        daily_payload = None
        incentive = None
        if is_correct:
            try:
                daily_payload = DailyQuestService.advance_progress(user_id, 'fragment-repair')
                incentive = daily_payload.get('incentive')
            except Exception:
                daily_payload = DailyQuestService.get_today(user_id)

        assignments = AssignmentService.list_for_student(user_id)
        return {
            'correct': is_correct,
            'correct_index': question.correct_index,
            'assignments': assignments,
            'daily': daily_payload,
            'incentive': incentive,
        }
