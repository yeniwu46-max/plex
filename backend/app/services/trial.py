"""试炼业务服务"""
from datetime import datetime, timedelta

from app.models import Class, PointsLog, Trial, TrialParticipation, User, db

from .base import BaseService


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
        now = datetime.utcnow()
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
            if trial.starts_at and trial.starts_at > datetime.utcnow():
                return 'scheduled'
            return 'running'
        return trial.status

    @staticmethod
    def _get_teacher_class(class_id, teacher_id, role_name):
        cls = Class.query.get(class_id)
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
            starts_at = datetime.utcnow() + timedelta(minutes=int(start_delay))

        if publish_mode == 'draft':
            status = 'draft'
            if not starts_at:
                starts_at = None
        elif publish_mode == 'scheduled':
            status = 'scheduled'
            if not starts_at:
                starts_at = datetime.utcnow() + timedelta(minutes=30)
        else:
            status = 'running'
            starts_at = starts_at or datetime.utcnow()

        ends_at = TrialService._parse_datetime(payload.get('ends_at'))
        if not ends_at and starts_at:
            ends_at = starts_at + timedelta(minutes=duration)

        if status == 'scheduled' and starts_at and starts_at <= datetime.utcnow():
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
        db.session.add(trial)
        db.session.commit()
        return trial.to_dict(
            include_stats=True,
            effective_status=TrialService.effective_status(trial),
        )

    @staticmethod
    def publish_trial(current_user_id, trial_id, role_name):
        trial = Trial.query.get(trial_id)
        if not trial:
            raise ValueError('试炼不存在')
        TrialService._get_teacher_class(trial.class_id, current_user_id, role_name)
        if role_name == 'teacher' and trial.teacher_id != current_user_id:
            raise PermissionError('不能发布他人创建的试炼')
        if trial.status not in ('draft', 'scheduled'):
            raise ValueError('仅草稿或定时试炼可发布')

        now = datetime.utcnow()
        if not trial.starts_at:
            trial.starts_at = now
        if trial.starts_at > now:
            trial.status = 'scheduled'
        else:
            trial.status = 'running'
            if not trial.ends_at:
                trial.ends_at = trial.starts_at + timedelta(minutes=trial.duration_minutes or 60)
        db.session.commit()
        return trial.to_dict(
            include_stats=True,
            effective_status=TrialService.effective_status(trial),
        )

    @staticmethod
    def update_trial(current_user_id, trial_id, role_name, payload):
        trial = Trial.query.get(trial_id)
        if not trial:
            raise ValueError('试炼不存在')
        TrialService._get_teacher_class(trial.class_id, current_user_id, role_name)
        if role_name == 'teacher' and trial.teacher_id != current_user_id:
            raise PermissionError('不能修改他人创建的试炼')

        if 'status' in payload and payload['status']:
            new_status = payload['status']
            trial.status = new_status
            if new_status == 'ended':
                trial.ends_at = trial.ends_at or datetime.utcnow()
            if new_status == 'running' and not trial.starts_at:
                trial.starts_at = datetime.utcnow()
        if 'title' in payload and payload['title']:
            trial.title = str(payload['title']).strip()[:120]
        if 'starts_at' in payload:
            trial.starts_at = TrialService._parse_datetime(payload.get('starts_at'))
        if 'ends_at' in payload:
            trial.ends_at = TrialService._parse_datetime(payload.get('ends_at'))
        if 'start_delay_minutes' in payload and payload['start_delay_minutes'] is not None:
            trial.starts_at = datetime.utcnow() + timedelta(minutes=int(payload['start_delay_minutes']))
        db.session.commit()
        TrialService._sync_trial_status(trial, commit=True)
        return trial.to_dict(
            include_stats=True,
            effective_status=TrialService.effective_status(trial),
        )

    @staticmethod
    def list_student_trials(user_id, include_scheduled=False):
        user = User.query.get(user_id)
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
        user = User.query.get(user_id)
        trial = Trial.query.get(trial_id)
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
        user = User.query.get(user_id)
        trial = Trial.query.get(trial_id)
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

        part.status = 'completed'
        part.score = int(score if score is not None else max(60, trial.difficulty))
        part.completed_at = datetime.utcnow()

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

        db.session.commit()
        return {
            'participation': part.to_dict(),
            'trial': trial.to_dict(effective_status=TrialService.effective_status(trial)),
            'total_points': user.total_points,
            'incentive': incentive_feedback,
        }

    @staticmethod
    def list_student_trials_for_teacher(teacher_id, student_user_id, role_name):
        student = User.query.get(student_user_id)
        if not student:
            raise ValueError('学生不存在')
        if not student.class_id:
            return {'participations': [], 'summary': {'completed': 0, 'joined': 0, 'avg_score': 0}}

        cls = Class.query.get(student.class_id)
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
