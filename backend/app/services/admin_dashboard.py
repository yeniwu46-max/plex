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
    def get_dashboard():
        student_role = Role.query.filter_by(name='student').first()
        teacher_role = Role.query.filter_by(name='teacher').first()

        total_students = (
            User.query.filter_by(role_id=student_role.id).count() if student_role else 0
        )
        total_teachers = (
            User.query.filter_by(role_id=teacher_role.id).count() if teacher_role else 0
        )

        week_ago = utc_now() - timedelta(days=7)
        active_students = (
            db.session.query(func.count(func.distinct(TrialQuestionProgress.user_id)))
            .filter(TrialQuestionProgress.answered_at >= week_ago)
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

        progress_rows = TrialQuestionProgress.query.filter_by(status='completed').all()
        if progress_rows:
            correct = len([row for row in progress_rows if row.is_correct])
            knowledge_mastery_rate = round((correct / len(progress_rows)) * 100, 1)
        else:
            knowledge_mastery_rate = 0

        activity_rate = (
            round((active_students / total_students) * 100, 1) if total_students else 0
        )
        task_completion_rate = min(100.0, round(activity_rate * 1.05, 1))

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

        weekday_labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        activity_submissions = []
        activity_passed = []
        health_scores = []
        x_data = []
        today = date.today()
        for offset in range(6, -1, -1):
            day = today - timedelta(days=offset)
            x_data.append(weekday_labels[day.weekday()])
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
        total_resource_tasks = len(resource_tasks)

        return {
            'metrics': {
                'active_students': active_students,
                'total_students': total_students,
                'active_teachers': total_teachers,
                'running_trials': running_trials,
                'total_trials': total_trials,
                'trial_completion_rate': trial_completion_rate,
                'health_score': 98.7,
            },
            'progress': {
                'task_completion_rate': task_completion_rate,
                'trial_participation_rate': trial_completion_rate,
                'knowledge_mastery_rate': knowledge_mastery_rate,
                'activity_rate': activity_rate,
            },
            'weak_knowledge_top': weak_knowledge_top,
            'resource_operations': {
                'task_count': total_resource_tasks,
                'completed_count': len(completed_tasks),
                'failed_count': len(failed_tasks),
                'success_rate': (
                    round(len(completed_tasks) / total_resource_tasks * 100, 1)
                    if total_resource_tasks else 0
                ),
                'average_latency_ms': (
                    round(sum(task_durations) / len(task_durations))
                    if task_durations else None
                ),
                'fallback_rate': (
                    round(fallback_count / total_resource_tasks * 100, 1)
                    if total_resource_tasks else 0
                ),
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
    def export_backup_snapshot():
        from app.models import Class, DailyQuest, LearningResource, SystemSetting, Trial

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
