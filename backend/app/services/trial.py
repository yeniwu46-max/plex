"""试炼业务服务"""
from datetime import datetime, timedelta

from app.models import Class, PointsLog, Trial, TrialParticipation, User, db
from app.utils.time import utc_now

from .base import BaseService
from .question_generator import QuestionGenerator


class TrialService(BaseService):
    """教师发布与学生参与试炼"""

    @staticmethod
    def _parse_datetime(value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        text = str(value).strip()
        if text.endswith('Z'):
            text = text[:-1]
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None

    @staticmethod
    def _sync_trial_status(trial, commit=False):
        """按时间推进 scheduled→running、running→ended。"""
        now = utc_now()
        changed = False
        if trial.status == 'scheduled' and trial.starts_at and trial.starts_at <= now:
            trial.status = 'running'
            changed = True
        if trial.status == 'running' and trial.ends_at and trial.ends_at <= now:
            trial.status = 'ended'
            changed = True
        if changed and commit:
            db.session.commit()
        return changed

    @staticmethod
    def effective_status(trial):
        TrialService._sync_trial_status(trial, commit=False)
        if trial.status == 'ended':
            return 'ended'
        if trial.status == 'draft':
            return 'draft'
        if trial.status == 'scheduled':
            return 'scheduled'
        if trial.status == 'running':
            if trial.starts_at and trial.starts_at > utc_now():
                return 'scheduled'
            return 'running'
        return trial.status

    @staticmethod
    def _get_teacher_class(class_id, teacher_id, role_name):
        cls = db.session.get(Class, class_id)
        if not cls:
            raise ValueError('班级不存在')
        if role_name == 'teacher' and cls.teacher_id != teacher_id:
            raise PermissionError('不能操作非本人负责的班级')
        return cls

    @staticmethod
    def list_teacher_trials(current_user_id, class_id, role_name):
        TrialService._get_teacher_class(class_id, current_user_id, role_name)
        trials = (
            Trial.query.filter_by(class_id=class_id)
            .order_by(Trial.created_at.desc())
            .all()
        )
        dirty = False
        for trial in trials:
            if TrialService._sync_trial_status(trial):
                dirty = True
        if dirty:
            db.session.commit()

        summary = TrialService._build_summary(trials, class_id)
        return {
            'trials': [
                trial.to_dict(
                    include_stats=True,
                    effective_status=TrialService.effective_status(trial),
                )
                for trial in trials
            ],
            'summary': summary,
        }

    @staticmethod
    def create_trial(current_user_id, role_name, payload):
        class_id = payload.get('class_id')
        if not class_id:
            raise ValueError('class_id 不能为空')
        TrialService._get_teacher_class(class_id, current_user_id, role_name)

        duration = int(payload.get('duration_minutes') or 60)
        publish_mode = (payload.get('publish_mode') or payload.get('status') or 'running').lower()
        if publish_mode in ('running', 'now', 'immediate'):
            publish_mode = 'now'
        elif publish_mode in ('draft', 'schedule', 'scheduled'):
            publish_mode = 'scheduled' if publish_mode in ('schedule', 'scheduled') else 'draft'

        starts_at = TrialService._parse_datetime(payload.get('starts_at'))
        start_delay = payload.get('start_delay_minutes')
        if start_delay is not None and starts_at is None:
            starts_at = utc_now() + timedelta(minutes=int(start_delay))

        if publish_mode == 'draft':
            status = 'draft'
            if not starts_at:
                starts_at = None
        elif publish_mode == 'scheduled':
            status = 'scheduled'
            if not starts_at:
                starts_at = utc_now() + timedelta(minutes=30)
        else:
            status = 'running'
            starts_at = starts_at or utc_now()

        ends_at = TrialService._parse_datetime(payload.get('ends_at'))
        if not ends_at and starts_at:
            ends_at = starts_at + timedelta(minutes=duration)

        if status == 'scheduled' and starts_at and starts_at <= utc_now():
            status = 'running'

        trial = Trial(
            class_id=class_id,
            teacher_id=current_user_id,
            title=(payload.get('title') or '未命名试炼').strip()[:120],
            trial_type=payload.get('trial_type') or 'solo',
            knowledge_key=payload.get('knowledge_key'),
            difficulty=int(payload.get('difficulty') or 50),
            duration_minutes=duration,
            status=status,
            reward_points=int(payload.get('reward_points') or 35),
            starts_at=starts_at,
            ends_at=ends_at,
        )
        keys = payload.get('knowledge_keys') or []
        if keys:
            trial.set_knowledge_keys(keys)
        elif payload.get('knowledge_key'):
            trial.knowledge_key = payload.get('knowledge_key')
        db.session.add(trial)
        db.session.flush()
        custom_questions = payload.get('custom_questions') or payload.get('draft_questions') or []
        if custom_questions:
            trial.set_draft_questions(custom_questions)
        db.session.commit()
        if trial.status in ('running', 'scheduled'):
            if custom_questions:
                QuestionGenerator.ensure_from_payload(trial, custom_questions)
            else:
                QuestionGenerator.ensure_for_trial(trial)
        result = trial.to_dict(
            include_stats=True,
            effective_status=TrialService.effective_status(trial),
        )
        if trial.status == 'running':
            notify = bool(payload.get('notify_students', True))
            result['notify_students'] = notify
            result['student_count'] = TrialService._class_student_count(class_id) if notify else 0
            if notify:
                result['notifications_sent'] = TrialService._notify_students_if_requested(trial, True)
        return result

    @staticmethod
    def _class_student_count(class_id: int) -> int:
        from app.models import Role, User

        student_role = Role.query.filter_by(name='student').first()
        if not student_role:
            return 0
        return User.query.filter_by(class_id=class_id, role_id=student_role.id).count()

    @staticmethod
    def _notify_students_if_requested(trial: Trial, notify_students: bool) -> int:
        if not notify_students or trial.status != 'running':
            return 0
        from app.services.student_notification import StudentNotificationService

        teacher = trial.teacher
        teacher_name = (teacher.real_name or teacher.username) if teacher else '老师'
        return StudentNotificationService.notify_class_teacher_task(
            trial.class_id,
            trial.id,
            trial.title,
            teacher_name,
        )

    @staticmethod
    def publish_trial(current_user_id, trial_id, role_name, notify_students: bool = True):
        trial = db.session.get(Trial, trial_id)
        if not trial:
            raise ValueError('试炼不存在')
        TrialService._get_teacher_class(trial.class_id, current_user_id, role_name)
        if role_name == 'teacher' and trial.teacher_id != current_user_id:
            raise PermissionError('不能发布他人创建的试炼')
        if trial.status not in ('draft', 'scheduled'):
            raise ValueError('仅草稿或定时试炼可发布')

        now = utc_now()
        if not trial.starts_at:
            trial.starts_at = now
        if trial.starts_at > now:
            trial.status = 'scheduled'
        else:
            trial.status = 'running'
            if not trial.ends_at:
                trial.ends_at = trial.starts_at + timedelta(minutes=trial.duration_minutes or 60)
        db.session.commit()
        draft = trial.draft_questions()
        if trial.status in ('running', 'scheduled'):
            if draft:
                QuestionGenerator.ensure_from_payload(trial, draft)
            else:
                QuestionGenerator.ensure_for_trial(trial)
        student_count = TrialService._class_student_count(trial.class_id) if notify_students else 0
        notifications_sent = 0
        if notify_students and trial.status == 'running':
            notifications_sent = TrialService._notify_students_if_requested(trial, True)
        return {
            'trial': trial.to_dict(
                include_stats=True,
                effective_status=TrialService.effective_status(trial),
            ),
            'notify_students': bool(notify_students),
            'student_count': student_count,
            'notifications_sent': notifications_sent,
        }

    @staticmethod
    def update_trial(current_user_id, trial_id, role_name, payload):
        trial = db.session.get(Trial, trial_id)
        if not trial:
            raise ValueError('试炼不存在')
        TrialService._get_teacher_class(trial.class_id, current_user_id, role_name)
        if role_name == 'teacher' and trial.teacher_id != current_user_id:
            raise PermissionError('不能修改他人创建的试炼')

        if 'status' in payload and payload['status']:
            new_status = payload['status']
            trial.status = new_status
            if new_status == 'ended':
                trial.ends_at = trial.ends_at or utc_now()
            if new_status == 'running' and not trial.starts_at:
                trial.starts_at = utc_now()
        if 'title' in payload and payload['title']:
            trial.title = str(payload['title']).strip()[:120]
        draft_questions = payload.get('draft_questions')
        if draft_questions is None and payload.get('custom_questions') is not None:
            draft_questions = payload.get('custom_questions')
        if draft_questions is not None:
            if trial.status != 'draft':
                raise ValueError('仅草稿试炼可编辑试卷题目')
            trial.set_draft_questions(draft_questions if isinstance(draft_questions, list) else [])
        if 'starts_at' in payload:
            trial.starts_at = TrialService._parse_datetime(payload.get('starts_at'))
        if 'ends_at' in payload:
            trial.ends_at = TrialService._parse_datetime(payload.get('ends_at'))
        if 'start_delay_minutes' in payload and payload['start_delay_minutes'] is not None:
            trial.starts_at = utc_now() + timedelta(minutes=int(payload['start_delay_minutes']))
        db.session.commit()
        TrialService._sync_trial_status(trial, commit=True)
        return trial.to_dict(
            include_stats=True,
            effective_status=TrialService.effective_status(trial),
        )

    @staticmethod
    def delete_trial(current_user_id, trial_id, role_name):
        trial = db.session.get(Trial, trial_id)
        if not trial:
            raise ValueError('试炼不存在')
        TrialService._get_teacher_class(trial.class_id, current_user_id, role_name)
        if role_name == 'teacher' and trial.teacher_id != current_user_id:
            raise PermissionError('不能删除他人创建的试炼')
        if trial.status not in ('draft', 'ended'):
            raise ValueError('仅草稿或已结束试炼可删除')
        db.session.delete(trial)
        db.session.commit()
        return {'deleted': True, 'trial_id': trial_id}

    @staticmethod
    def list_student_trials(user_id, include_scheduled=False):
        user = db.session.get(User, user_id)
        if not user or not user.class_id:
            return {'trials': [], 'participations': []}

        trials = Trial.query.filter_by(class_id=user.class_id).order_by(Trial.created_at.desc()).all()
        dirty = False
        for trial in trials:
            if TrialService._sync_trial_status(trial):
                dirty = True
        if dirty:
            db.session.commit()

        allowed = {'running'}
        if include_scheduled:
            allowed.add('scheduled')

        participations = {
            p.trial_id: p
            for p in TrialParticipation.query.filter_by(user_id=user_id).all()
        }
        items = []
        for trial in trials:
            effective = TrialService.effective_status(trial)
            if trial.status == 'draft' or effective not in allowed:
                continue
            row = trial.to_dict(include_stats=True, effective_status=effective)
            part = participations.get(trial.id)
            row['my_status'] = part.status if part else None
            row['my_score'] = part.score if part else 0
            items.append(row)
        return {'trials': items}

    @staticmethod
    def list_student_arena_trials(user_id):
        """探索舱地图：进行中 + 即将开始。"""
        return TrialService.list_student_trials(user_id, include_scheduled=True)

    @staticmethod
    def join_trial(user_id, trial_id):
        user = db.session.get(User, user_id)
        trial = db.session.get(Trial, trial_id)
        if not user or not trial:
            raise ValueError('试炼或用户不存在')
        if not user.class_id or user.class_id != trial.class_id:
            raise PermissionError('只能参与本班试炼')
        TrialService._sync_trial_status(trial, commit=True)
        if TrialService.effective_status(trial) != 'running':
            raise ValueError('试炼未在进行中')

        existing = TrialParticipation.query.filter_by(trial_id=trial_id, user_id=user_id).first()
        if existing:
            if existing.status == 'completed':
                raise ValueError('已完成该试炼')
            return existing.to_dict()

        part = TrialParticipation(trial_id=trial_id, user_id=user_id, status='joined')
        db.session.add(part)
        db.session.commit()
        return part.to_dict()

    @staticmethod
    def complete_trial(user_id, trial_id, score=None):
        user = db.session.get(User, user_id)
        trial = db.session.get(Trial, trial_id)
        if not user or not trial:
            raise ValueError('试炼或用户不存在')
        if not user.class_id or user.class_id != trial.class_id:
            raise PermissionError('只能完成本班试炼')

        part = TrialParticipation.query.filter_by(trial_id=trial_id, user_id=user_id).first()
        if not part:
            part = TrialParticipation(trial_id=trial_id, user_id=user_id, status='joined')
            db.session.add(part)
            db.session.flush()
        if part.status == 'completed':
            raise ValueError('已完成该试炼')

        from .assignment import AssignmentService

        questions = AssignmentService._questions_for_trial(trial_id)
        if questions:
            computed_score, answered_count, _ = AssignmentService.compute_trial_score(user_id, trial_id)
            if answered_count < len(questions):
                raise ValueError('请先完成全部题目再提交试炼')
            final_score = int(score if score is not None else computed_score)
        else:
            final_score = int(score if score is not None else max(60, trial.difficulty))

        part.status = 'completed'
        part.score = final_score
        part.completed_at = utc_now()

        incentive_feedback = None
        if trial.reward_points:
            from .incentive import IncentiveService

            db.session.flush()
            incentive_feedback = IncentiveService.record_points(
                user_id,
                trial.reward_points,
                f'trial_complete:{trial.id}',
                related_id=trial.id,
                refresh_ranking=True,
            )
        else:
            from .incentive import IncentiveService

            incentive_feedback = IncentiveService.process_user_incentive(user_id)

        try:
            from .daily_quest import DailyQuestService
            DailyQuestService.advance_progress(user_id, 'trial-challenge')
        except Exception:
            pass

        db.session.commit()
        return {
            'participation': part.to_dict(),
            'trial': trial.to_dict(effective_status=TrialService.effective_status(trial)),
            'total_points': user.total_points,
            'incentive': incentive_feedback,
        }

    @staticmethod
    def list_student_trials_for_teacher(teacher_id, student_user_id, role_name):
        student = db.session.get(User, student_user_id)
        if not student:
            raise ValueError('学生不存在')
        if not student.class_id:
            return {'participations': [], 'summary': {'completed': 0, 'joined': 0, 'avg_score': 0}}

        cls = db.session.get(Class, student.class_id)
        if not cls:
            raise ValueError('班级不存在')
        if role_name == 'teacher' and cls.teacher_id != teacher_id:
            raise PermissionError('只能查看本人班级学生')
        if role_name not in ('teacher', 'admin'):
            raise PermissionError('无权查看学生试炼记录')

        parts = (
            TrialParticipation.query.join(Trial)
            .filter(TrialParticipation.user_id == student_user_id)
            .order_by(TrialParticipation.joined_at.desc())
            .all()
        )
        rows = []
        for part in parts:
            trial = part.trial
            row = part.to_dict()
            row['trial'] = trial.to_dict(effective_status=TrialService.effective_status(trial))
            rows.append(row)

        completed = [p for p in parts if p.status == 'completed']
        joined = [p for p in parts if p.status == 'joined']
        avg_score = round(sum(p.score or 0 for p in completed) / len(completed)) if completed else 0
        return {
            'student_id': student_user_id,
            'participations': rows,
            'summary': {
                'total': len(parts),
                'completed': len(completed),
                'joined': len(joined),
                'avg_score': avg_score,
            },
        }

    @staticmethod
    def get_student_trial_stats(user_id: int):
        from datetime import date, datetime, timedelta

        user = db.session.get(User, user_id)
        if not user:
            raise ValueError('用户不存在')

        parts = (
            TrialParticipation.query.filter_by(user_id=user_id)
            .order_by(TrialParticipation.joined_at.desc())
            .all()
        )
        completed = [p for p in parts if p.status == 'completed']
        joined = [p for p in parts if p.status == 'joined']
        avg_score = round(sum(p.score or 0 for p in completed) / len(completed)) if completed else 0

        weekday_labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        x_data = []
        completed_counts = []
        avg_scores = []
        today = date.today()
        for offset in range(6, -1, -1):
            day = today - timedelta(days=offset)
            x_data.append(weekday_labels[day.weekday()] if offset < 6 else weekday_labels[day.weekday()])
            day_start = datetime.combine(day, datetime.min.time())
            day_end = datetime.combine(day, datetime.max.time())
            day_parts = [
                p
                for p in completed
                if p.completed_at and day_start <= p.completed_at <= day_end
            ]
            completed_counts.append(len(day_parts))
            if day_parts:
                avg_scores.append(round(sum(p.score or 0 for p in day_parts) / len(day_parts)))
            else:
                avg_scores.append(0)

        recent = []
        for part in completed[:8]:
            trial = part.trial
            recent.append(
                {
                    'trial_id': part.trial_id,
                    'title': trial.title if trial else '',
                    'score': part.score,
                    'knowledge_key': trial.knowledge_key if trial else None,
                    'completed_at': part.completed_at.isoformat() if part.completed_at else None,
                }
            )

        return {
            'summary': {
                'total_participations': len(parts),
                'completed_count': len(completed),
                'active_count': len(joined),
                'avg_score': avg_score,
            },
            'trend': {
                'x_data': x_data,
                'completed_count': completed_counts,
                'avg_score': avg_scores,
            },
            'recent_completions': recent,
        }

    @staticmethod
    def _build_summary(trials, class_id):
        student_count = User.query.filter_by(class_id=class_id).count()
        running = [t for t in trials if TrialService.effective_status(t) == 'running']
        scheduled = [t for t in trials if TrialService.effective_status(t) == 'scheduled']
        drafts = [t for t in trials if t.status == 'draft']
        all_parts = TrialParticipation.query.join(Trial).filter(Trial.class_id == class_id).all()
        completed = [p for p in all_parts if p.status == 'completed']
        participants = len({p.user_id for p in all_parts})
        completion_rate = round((len(completed) / participants) * 100) if participants else 0
        return {
            'running_count': len(running),
            'scheduled_count': len(scheduled),
            'draft_count': len(drafts),
            'participant_count': participants,
            'class_student_count': student_count,
            'avg_completion_rate': completion_rate,
            'template_count': 5,
        }
