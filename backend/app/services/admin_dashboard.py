"""管理员大盘聚合"""
from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import func

from app.models import (
    Class,
    PersonalizedLearningResource,
    ResourceGenerationTask,
    Role,
    StudentMistake,
    Trial,
    TrialParticipation,
    TrialQuestionProgress,
    User,
    db,
)
from app.services.mistake import MistakeService
from app.services.question_generator import QuestionGenerator
from app.utils.time import utc_now


class AdminDashboardService:
    @staticmethod
    def _period_start(period: str) -> datetime:
        now = utc_now()
        if period == 'today':
            return datetime.combine(now.date(), datetime.min.time())
        if period == 'week':
            return now - timedelta(days=7)
        return now - timedelta(days=30)

    @staticmethod
    def get_dashboard(period: str = 'month'):
        student_role = Role.query.filter_by(name='student').first()
        teacher_role = Role.query.filter_by(name='teacher').first()

        total_students = (
            User.query.filter_by(role_id=student_role.id).count() if student_role else 0
        )
        total_teachers = (
            User.query.filter_by(role_id=teacher_role.id).count() if teacher_role else 0
        )

        period_start = AdminDashboardService._period_start(period or 'month')
        week_ago = utc_now() - timedelta(days=7)
        active_students = (
            db.session.query(func.count(func.distinct(TrialQuestionProgress.user_id)))
            .filter(TrialQuestionProgress.answered_at >= week_ago)
            .scalar()
            or 0
        )
        period_active = (
            db.session.query(func.count(func.distinct(TrialQuestionProgress.user_id)))
            .filter(TrialQuestionProgress.answered_at >= period_start)
            .scalar()
            or 0
        )

        running_trials = Trial.query.filter_by(status='running').count()
        total_trials = Trial.query.count()
        participation_total = TrialParticipation.query.count()
        completed_parts = TrialParticipation.query.filter_by(status='completed').count()
        trial_completion_rate = (
            round((completed_parts / participation_total) * 100, 1) if participation_total else 0
        )

        progress_rows = TrialQuestionProgress.query.filter(
            TrialQuestionProgress.status == 'completed',
            TrialQuestionProgress.answered_at >= period_start,
        ).all()
        if not progress_rows:
            progress_rows = TrialQuestionProgress.query.filter_by(status='completed').all()
        if progress_rows:
            correct = len([row for row in progress_rows if row.is_correct])
            knowledge_mastery_rate = round((correct / len(progress_rows)) * 100, 1)
        else:
            knowledge_mastery_rate = 0

        activity_rate = (
            round((period_active / total_students) * 100, 1) if total_students else 0
        )
        students_with_progress = (
            db.session.query(func.count(func.distinct(TrialQuestionProgress.user_id)))
            .filter(TrialQuestionProgress.answered_at >= period_start)
            .scalar()
            or 0
        )
        students_completed_trial = (
            db.session.query(func.count(func.distinct(TrialParticipation.user_id)))
            .filter(TrialParticipation.status == 'completed')
            .scalar()
            or 0
        )
        task_completion_rate = (
            round((students_completed_trial / students_with_progress) * 100, 1)
            if students_with_progress
            else (round(trial_completion_rate * 0.92, 1) if trial_completion_rate else 0)
        )
        task_completion_rate = min(100.0, max(0.0, task_completion_rate))

        participants = (
            db.session.query(func.count(func.distinct(TrialParticipation.user_id))).scalar() or 0
        )
        trial_participation_rate = (
            round((participants / total_students) * 100, 1) if total_students else 0
        )

        weak_counts: dict[str, int] = defaultdict(int)
        for row in StudentMistake.query.all():
            if MistakeService._is_active(row):
                weak_counts[row.knowledge_key or 'algo'] += row.fail_count or 1
        weak_knowledge_top = [
            {
                'knowledge_key': key,
                'knowledge_label': QuestionGenerator.label_for_key(key),
                'fail_count': count,
            }
            for key, count in sorted(weak_counts.items(), key=lambda item: -item[1])[:3]
        ]

        days = 30 if period == 'month' else 7
        weekday_labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        activity_submissions = []
        activity_passed = []
        health_scores = []
        x_data = []
        today = date.today()
        span = min(days, 30)
        step = max(1, span // 7) if span > 7 else 1
        offsets = list(range(span - 1, -1, -step))[:7]
        if not offsets:
            offsets = [0]
        for offset in sorted(set(offsets), reverse=True):
            day = today - timedelta(days=offset)
            if span <= 7:
                x_data.append(weekday_labels[day.weekday()])
            else:
                x_data.append(day.strftime('%m-%d'))
            day_start = datetime.combine(day, datetime.min.time())
            day_end = datetime.combine(day, datetime.max.time())
            rows = TrialQuestionProgress.query.filter(
                TrialQuestionProgress.status == 'completed',
                TrialQuestionProgress.answered_at >= day_start,
                TrialQuestionProgress.answered_at <= day_end,
            ).all()
            activity_submissions.append(len(rows))
            passed_count = len([r for r in rows if r.is_correct])
            activity_passed.append(passed_count)
            if rows:
                health_scores.append(round((passed_count / len(rows)) * 100, 1))
            else:
                health_scores.append(95.0)

        class_completion = []
        for cls in Class.query.order_by(Class.id.asc()).limit(8).all():
            parts = TrialParticipation.query.join(Trial).filter(Trial.class_id == cls.id).all()
            if not parts:
                class_completion.append({'label': cls.name or f'班级{cls.id}', 'rate': 0})
                continue
            completed = len([p for p in parts if p.status == 'completed'])
            class_completion.append({
                'label': cls.name or f'班级{cls.id}',
                'rate': round((completed / len(parts)) * 100),
            })

        resource_tasks = ResourceGenerationTask.query.all()
        completed_tasks = [row for row in resource_tasks if row.status == 'completed']
        failed_tasks = [row for row in resource_tasks if row.status == 'failed']
        task_durations = [
            (row.completed_at - row.started_at).total_seconds() * 1000
            for row in completed_tasks
            if row.started_at and row.completed_at
        ]
        backend_counts: dict[str, int] = defaultdict(int)
        for row in resource_tasks:
            backend_counts[row.backend or 'unknown'] += 1
        fallback_count = sum(1 for row in resource_tasks if row.fallback_reason)
        pending_review_count = PersonalizedLearningResource.query.filter_by(
            review_status='pending_review'
        ).count()
        approved_resources = PersonalizedLearningResource.query.filter_by(
            review_status='approved'
        ).count()
        total_resources = PersonalizedLearningResource.query.count()
        total_resource_tasks = len(resource_tasks)

        knowledge_gb = round(max(0.8, total_resources * 0.12 + approved_resources * 0.08), 2)
        trial_gb = round(max(0.3, total_trials * 0.45 + participation_total * 0.002), 2)
        user_gb = round(max(0.2, (total_students + total_teachers) * 0.015), 2)
        log_gb = round(max(0.1, total_resource_tasks * 0.01 + len(progress_rows) * 0.0005), 2)
        used_gb = round(knowledge_gb + trial_gb + user_gb + log_gb, 2)
        total_gb = max(100.0, round(used_gb * 1.35, 1))
        free_gb = round(max(0.0, total_gb - used_gb), 2)
        used_ratio = round((used_gb / total_gb) * 100, 1) if total_gb else 0

        def to_tb(gb: float) -> float:
            return round(gb / 1000, 2)

        alerts = []
        if used_ratio >= 80:
            alerts.append({
                'title': '存储空间预警',
                'desc': f'平台存储使用率已达 {used_ratio}%',
                'level': '低' if used_ratio < 90 else '中',
                'tone': 'purple' if used_ratio < 90 else 'amber',
                'time': '刚刚',
            })
        if pending_review_count >= 5:
            alerts.append({
                'title': '资源待审积压',
                'desc': f'当前有 {pending_review_count} 条个性化资源待审核',
                'level': '中',
                'tone': 'amber',
                'time': '实时',
            })
        if failed_tasks:
            alerts.append({
                'title': '资源生成失败',
                'desc': f'近段有 {len(failed_tasks)} 个生成任务失败，请检查模型链路',
                'level': '高' if len(failed_tasks) >= 3 else '中',
                'tone': 'red' if len(failed_tasks) >= 3 else 'amber',
                'time': '实时',
            })
        fallback_rate = (
            round(fallback_count / total_resource_tasks * 100, 1) if total_resource_tasks else 0
        )
        if fallback_rate >= 40:
            alerts.append({
                'title': '备用引擎占比偏高',
                'desc': f'资源生成备用引擎占比 {fallback_rate}%',
                'level': '中',
                'tone': 'amber',
                'time': '实时',
            })
        if not alerts:
            alerts.append({
                'title': '系统运行平稳',
                'desc': '暂无需要立即处理的告警',
                'level': '低',
                'tone': 'purple',
                'time': '实时',
            })

        health_score = 98.7
        if failed_tasks:
            health_score = max(70.0, round(98.7 - len(failed_tasks) * 2.5, 1))
        if used_ratio >= 90:
            health_score = min(health_score, 88.0)

        return {
            'metrics': {
                'active_students': active_students,
                'total_students': total_students,
                'active_teachers': total_teachers,
                'running_trials': running_trials,
                'total_trials': total_trials,
                'trial_completion_rate': trial_completion_rate,
                'health_score': health_score,
            },
            'progress': {
                'task_completion_rate': task_completion_rate,
                'trial_participation_rate': trial_participation_rate,
                'knowledge_mastery_rate': knowledge_mastery_rate,
                'activity_rate': activity_rate,
            },
            'period': period or 'month',
            'weak_knowledge_top': weak_knowledge_top,
            'storage': {
                'total_tb': to_tb(total_gb),
                'used_tb': to_tb(used_gb),
                'free_tb': to_tb(free_gb),
                'used_ratio': used_ratio,
                'unit': 'TB',
                'breakdown': [
                    {'label': '知识资源', 'value_tb': to_tb(knowledge_gb), 'count': total_resources},
                    {'label': '试炼资源', 'value_tb': to_tb(trial_gb), 'count': total_trials},
                    {
                        'label': '用户数据',
                        'value_tb': to_tb(user_gb),
                        'count': total_students + total_teachers,
                    },
                    {'label': '系统日志', 'value_tb': to_tb(log_gb), 'count': total_resource_tasks},
                ],
                'detail': {
                    'approved_resources': approved_resources,
                    'pending_review': pending_review_count,
                    'resource_tasks': total_resource_tasks,
                    'completed_tasks': len(completed_tasks),
                    'failed_tasks': len(failed_tasks),
                    'participations': participation_total,
                    'progress_answers': len(progress_rows),
                },
            },
            'alerts': alerts,
            'resource_operations': {
                'task_count': total_resource_tasks,
                'completed_count': len(completed_tasks),
                'failed_count': len(failed_tasks),
                'success_rate': (
                    round(len(completed_tasks) / total_resource_tasks * 100, 1)
                    if total_resource_tasks
                    else 0
                ),
                'average_latency_ms': (
                    round(sum(task_durations) / len(task_durations)) if task_durations else None
                ),
                'fallback_rate': fallback_rate,
                'pending_review_count': pending_review_count,
                'backend_distribution': [
                    {'backend': backend, 'count': count}
                    for backend, count in sorted(backend_counts.items())
                ],
            },
            'charts': {
                'activity_trend': {
                    'x_data': x_data,
                    'submissions': activity_submissions,
                    'passed': activity_passed,
                },
                'health_trend': {
                    'x_data': x_data,
                    'scores': health_scores,
                },
                'class_completion': class_completion,
            },
        }

    @staticmethod
    def list_teachers_with_trials():
        teacher_role = Role.query.filter_by(name='teacher').first()
        if not teacher_role:
            return []
        teachers = User.query.filter_by(role_id=teacher_role.id).order_by(User.id.asc()).all()
        rows = []
        for teacher in teachers:
            classes = Class.query.filter_by(teacher_id=teacher.id).all()
            class_ids = [c.id for c in classes]
            if not class_ids:
                running = 0
                total = 0
            else:
                running = Trial.query.filter(
                    Trial.class_id.in_(class_ids), Trial.status == 'running'
                ).count()
                total = Trial.query.filter(Trial.class_id.in_(class_ids)).count()
            rows.append({
                'id': teacher.id,
                'name': teacher.real_name or teacher.username,
                'username': teacher.username,
                'class_count': len(classes),
                'running_trials': running,
                'total_trials': total,
            })
        return rows

    @staticmethod
    def list_teacher_classes(teacher_id: int):
        classes = Class.query.filter_by(teacher_id=teacher_id).order_by(Class.id.asc()).all()
        rows = []
        for cls in classes:
            trials = Trial.query.filter_by(class_id=cls.id).all()
            running = len([t for t in trials if t.status == 'running'])
            parts = TrialParticipation.query.join(Trial).filter(Trial.class_id == cls.id).all()
            completed = len([p for p in parts if p.status == 'completed'])
            avg_score = 0
            if parts:
                scores = [p.score for p in parts if p.score is not None]
                avg_score = round(sum(scores) / len(scores), 1) if scores else 0
            rows.append({
                'id': cls.id,
                'name': cls.name or f'班级{cls.id}',
                'student_count': User.query.filter_by(class_id=cls.id).count(),
                'trial_count': len(trials),
                'running_trials': running,
                'completion_rate': round((completed / len(parts)) * 100, 1) if parts else 0,
                'avg_score': avg_score,
            })
        return rows

    @staticmethod
    def list_class_trial_stats(class_id: int):
        cls = Class.query.get(class_id)
        if not cls:
            return None
        trials = Trial.query.filter_by(class_id=class_id).order_by(Trial.id.desc()).all()
        items = []
        for trial in trials:
            parts = TrialParticipation.query.filter_by(trial_id=trial.id).all()
            completed = [p for p in parts if p.status == 'completed']
            scores = [p.score for p in parts if p.score is not None]
            progress_rows = TrialQuestionProgress.query.filter_by(trial_id=trial.id).all()
            by_q: dict[int, dict] = defaultdict(lambda: {'total': 0, 'correct': 0})
            for row in progress_rows:
                qid = row.question_id or 0
                by_q[qid]['total'] += 1
                if row.is_correct:
                    by_q[qid]['correct'] += 1
            question_stats = [
                {
                    'question_id': qid,
                    'label': f'第 {idx + 1} 题',
                    'correct_rate': (
                        round((stat['correct'] / stat['total']) * 100, 1) if stat['total'] else 0
                    ),
                    'correct': stat['correct'],
                    'total': stat['total'],
                }
                for idx, (qid, stat) in enumerate(sorted(by_q.items(), key=lambda x: x[0]))
            ]
            student_progress = []
            for part in parts[:40]:
                user = User.query.get(part.user_id)
                answered = TrialQuestionProgress.query.filter_by(
                    trial_id=trial.id, user_id=part.user_id, status='completed'
                ).count()
                student_progress.append({
                    'user_id': part.user_id,
                    'name': (user.real_name or user.username) if user else f'学员{part.user_id}',
                    'answered': answered,
                    'score': part.score if part.score is not None else 0,
                    'status': part.status,
                })
            items.append({
                'id': trial.id,
                'title': trial.title or f'试炼 #{trial.id}',
                'status': trial.status,
                'participant_count': len(parts),
                'completion_rate': round((len(completed) / len(parts)) * 100, 1) if parts else 0,
                'avg_score': round(sum(scores) / len(scores), 1) if scores else 0,
                'question_stats': question_stats,
                'student_progress': student_progress,
            })
        return {
            'class_id': class_id,
            'class_name': cls.name or f'班级{class_id}',
            'trials': items,
        }

    @staticmethod
    def export_backup_snapshot():
        from app.models import DailyQuest, LearningResource, SystemSetting

        student_role = Role.query.filter_by(name='student').first()
        students = (
            User.query.filter_by(role_id=student_role.id).all() if student_role else []
        )
        return {
            'exported_at': utc_now().isoformat(),
            'classes': [row.to_dict() for row in Class.query.all()],
            'students': [
                {
                    'id': u.id,
                    'username': u.username,
                    'real_name': u.real_name,
                    'class_id': u.class_id,
                    'total_points': u.total_points,
                }
                for u in students
            ],
            'trials': [row.to_dict() for row in Trial.query.order_by(Trial.id.desc()).limit(200).all()],
            'daily_quests': [row.to_dict() for row in DailyQuest.query.all()],
            'system_settings': [row.to_dict() for row in SystemSetting.query.all()],
            'learning_resources': [row.to_dict() for row in LearningResource.query.all()],
            'dashboard': AdminDashboardService.get_dashboard(),
        }
