"""Teacher dashboard aggregation service."""
from collections import defaultdict
from datetime import date, datetime, timedelta

from app.models import Class, PointsLog, RankingCache, Trial, TrialQuestion, TrialQuestionProgress, User, UserDailyQuest, db

from .base import BaseService
from .question_generator import QuestionGenerator


class TeacherService(BaseService):
    """Read-only aggregates for the teacher workspace."""

    @staticmethod
    def get_overview(current_user_id, class_id=None, period='week'):
        teacher = User.query.get(current_user_id)
        if not teacher or not teacher.role:
            raise PermissionError('用户信息获取失败或未设置角色')

        role_name = teacher.role.name
        if role_name not in ['teacher', 'admin']:
            raise PermissionError('只有教师或管理员可以访问教师工作台')

        normalized_period = period if period in ['week', 'month'] else 'week'
        classes_query = Class.query.order_by(Class.created_at.desc())
        if role_name == 'teacher':
            classes_query = classes_query.filter_by(teacher_id=teacher.id)

        classes = classes_query.all()
        selected_class = TeacherService._select_class(classes, class_id, role_name, teacher.id)
        if not selected_class:
            return TeacherService._empty_overview(teacher, classes, normalized_period)

        students = User.query.filter_by(class_id=selected_class.id).order_by(User.total_points.desc()).all()
        start_date, days = TeacherService._period_days(normalized_period)
        today = date.today()
        ranking = TeacherService._ranking(selected_class.id, students)
        heatmap = TeacherService._heatmap(students, start_date, days)
        students_payload = TeacherService._student_rows(students, ranking, today)
        attention_students = TeacherService._attention_students(students_payload)
        recent_activity = TeacherService._recent_activity(selected_class.id)

        metrics = TeacherService._metrics(students_payload)

        return {
            'teacher': TeacherService._teacher_payload(teacher),
            'classes': [cls.to_dict() for cls in classes],
            'selected_class': selected_class.to_dict(),
            'period': normalized_period,
            'metrics': metrics,
            'heatmap': heatmap,
            'ranking': ranking[:10],
            'attention_students': attention_students,
            'students': students_payload,
            'recent_activity': recent_activity,
        }

    @staticmethod
    def _select_class(classes, class_id, role_name, teacher_id):
        if class_id:
            selected = Class.query.get(class_id)
            if not selected:
                raise ValueError('班级不存在')
            if role_name == 'teacher' and selected.teacher_id != teacher_id:
                raise PermissionError('不能访问非本人负责的班级')
            return selected

        return classes[0] if classes else None

    @staticmethod
    def _period_days(period):
        day_count = 30 if period == 'month' else 7
        today = date.today()
        start = today - timedelta(days=day_count - 1)
        return start, [start + timedelta(days=idx) for idx in range(day_count)]

    @staticmethod
    def _ranking(class_id, students):
        current_week = f'{datetime.now().year}-w{datetime.now().isocalendar()[1]:02d}'
        cached = (
            RankingCache.query.filter_by(class_id=class_id, week=current_week)
            .order_by(RankingCache.rank.asc())
            .all()
        )
        student_map = {student.id: student for student in students}

        if cached:
            ranking = []
            for item in cached:
                student = student_map.get(item.user_id)
                if not student:
                    continue
                ranking.append(TeacherService._ranking_item(student, item.rank, item.points, item.level, current_week))
            return ranking

        sorted_students = sorted(students, key=lambda student: student.total_points or 0, reverse=True)
        return [
            TeacherService._ranking_item(student, idx + 1, student.total_points or 0, student.level or 1, current_week)
            for idx, student in enumerate(sorted_students)
        ]

    @staticmethod
    def _ranking_item(student, rank, points, level, week):
        return {
            'user_id': student.id,
            'student_name': student.real_name or student.username,
            'username': student.username,
            'rank': rank,
            'points': points or 0,
            'level': level or 1,
            'week': week,
            'achievements_count': len(student.achievements),
            'status': student.status,
        }

    @staticmethod
    def _heatmap(students, start_date, days):
        student_ids = [student.id for student in students]
        progress_map = {}
        if student_ids:
            records = UserDailyQuest.query.filter(
                UserDailyQuest.user_id.in_(student_ids),
                UserDailyQuest.quest_date >= start_date,
            ).all()
            for record in records:
                key = (record.user_id, record.quest_date)
                bucket = progress_map.setdefault(key, {'completed': 0, 'total': 0})
                bucket['total'] += 1
                if record.completed_at:
                    bucket['completed'] += 1

        day_payload = [{'date': day.isoformat(), 'label': day.strftime('%m-%d')} for day in days]
        rows = []
        for student in students:
            cells = []
            for day in days:
                bucket = progress_map.get((student.id, day), {'completed': 0, 'total': 0})
                total = bucket['total']
                completed = bucket['completed']
                rate = round((completed / total) * 100) if total else 0
                cells.append({
                    'date': day.isoformat(),
                    'completed': completed,
                    'total': total,
                    'rate': rate,
                })
            avg_rate = round(sum(cell['rate'] for cell in cells) / len(cells)) if cells else 0
            rows.append({
                'user_id': student.id,
                'student_name': student.real_name or student.username,
                'cells': cells,
                'avg_rate': avg_rate,
            })

        return {'days': day_payload, 'rows': rows}

    @staticmethod
    def _student_rows(students, ranking, today):
        rank_map = {item['user_id']: item['rank'] for item in ranking}
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        today_progress = TeacherService._today_progress([student.id for student in students], today)

        rows = []
        for student in students:
            last_log = (
                PointsLog.query.filter_by(user_id=student.id)
                .order_by(PointsLog.created_at.desc())
                .first()
            )
            today_bucket = today_progress.get(student.id, {'completed': 0, 'total': 0})
            today_rate = round((today_bucket['completed'] / today_bucket['total']) * 100) if today_bucket['total'] else 0
            inactive_days = None
            if last_log and last_log.created_at:
                inactive_days = max(0, (datetime.utcnow().date() - last_log.created_at.date()).days)

            rows.append({
                'id': student.id,
                'username': student.username,
                'real_name': student.real_name,
                'status': student.status,
                'level': student.level or 1,
                'total_points': student.total_points or 0,
                'consecutive_days': student.consecutive_days or 0,
                'achievements_count': len(student.achievements),
                'rank': rank_map.get(student.id),
                'today_completed': today_bucket['completed'],
                'today_total': today_bucket['total'],
                'today_completion_rate': today_rate,
                'last_activity_at': last_log.created_at.isoformat() if last_log and last_log.created_at else None,
                'inactive_days': inactive_days,
                'is_inactive_7d': not last_log or (last_log.created_at and last_log.created_at < seven_days_ago),
            })
        return rows

    @staticmethod
    def _today_progress(student_ids, today):
        if not student_ids:
            return {}
        records = UserDailyQuest.query.filter(
            UserDailyQuest.user_id.in_(student_ids),
            UserDailyQuest.quest_date == today,
        ).all()
        progress = {}
        for record in records:
            bucket = progress.setdefault(record.user_id, {'completed': 0, 'total': 0})
            bucket['total'] += 1
            if record.completed_at:
                bucket['completed'] += 1
        return progress

    @staticmethod
    def _attention_students(students_payload):
        total = len(students_payload)
        rank_threshold = max(1, int(total * 0.8)) if total else 0
        attention = []
        for student in students_payload:
            reasons = []
            if student['status'] == 'frozen':
                reasons.append('账号冻结')
            if student['is_inactive_7d']:
                reasons.append('7天无积分记录')
            if student['today_total'] > 0 and student['today_completion_rate'] < 50:
                reasons.append('今日委托低于50%')
            if student['rank'] and rank_threshold and student['rank'] > rank_threshold:
                reasons.append('班级排名后20%')
            if reasons:
                attention.append({**student, 'reasons': reasons})
        return attention[:8]

    @staticmethod
    def _metrics(students_payload):
        total = len(students_payload)
        active_students = [student for student in students_payload if student['status'] == 'active']
        avg_points = round(sum(student['total_points'] for student in students_payload) / total) if total else 0
        avg_today_completion = (
            round(sum(student['today_completion_rate'] for student in students_payload) / total) if total else 0
        )
        return {
            'student_count': total,
            'active_count': len(active_students),
            'frozen_count': len([student for student in students_payload if student['status'] == 'frozen']),
            'avg_points': avg_points,
            'avg_today_completion': avg_today_completion,
            'attention_count': len(TeacherService._attention_students(students_payload)),
        }

    @staticmethod
    def _recent_activity(class_id):
        logs = (
            db.session.query(PointsLog, User)
            .join(User, PointsLog.user_id == User.id)
            .filter(User.class_id == class_id)
            .order_by(PointsLog.created_at.desc())
            .limit(8)
            .all()
        )
        return [
            {
                'id': log.id,
                'user_id': user.id,
                'student_name': user.real_name or user.username,
                'points': log.points,
                'reason': log.reason,
                'created_at': log.created_at.isoformat() if log.created_at else None,
            }
            for log, user in logs
        ]

    @staticmethod
    def _empty_overview(teacher, classes, period):
        return {
            'teacher': TeacherService._teacher_payload(teacher),
            'classes': [cls.to_dict() for cls in classes],
            'selected_class': None,
            'period': period,
            'metrics': {
                'student_count': 0,
                'active_count': 0,
                'frozen_count': 0,
                'avg_points': 0,
                'avg_today_completion': 0,
                'attention_count': 0,
            },
            'heatmap': {'days': [], 'rows': []},
            'ranking': [],
            'attention_students': [],
            'students': [],
            'recent_activity': [],
        }

    @staticmethod
    def _teacher_payload(teacher):
        return {
            'id': teacher.id,
            'username': teacher.username,
            'real_name': teacher.real_name,
            'role': teacher.role.name if teacher.role else None,
        }

    @staticmethod
    def get_class_stats(current_user_id, class_id=None):
        teacher = User.query.get(current_user_id)
        if not teacher or not teacher.role:
            raise PermissionError('用户信息获取失败或未设置角色')
        role_name = teacher.role.name
        if role_name not in ['teacher', 'admin']:
            raise PermissionError('只有教师或管理员可以访问班级统计')

        classes_query = Class.query.order_by(Class.created_at.desc())
        if role_name == 'teacher':
            classes_query = classes_query.filter_by(teacher_id=teacher.id)
        classes = classes_query.all()
        selected_class = TeacherService._select_class(classes, class_id, role_name, teacher.id)
        if not selected_class:
            return {'domain_mastery': [], 'mistake_types': []}

        students = User.query.filter_by(class_id=selected_class.id).all()
        student_ids = [student.id for student in students]
        if not student_ids:
            return {'domain_mastery': [], 'mistake_types': []}

        trial_ids = [trial.id for trial in Trial.query.filter_by(class_id=selected_class.id).all()]
        if not trial_ids:
            return {'domain_mastery': [], 'mistake_types': []}

        questions = TrialQuestion.query.filter(TrialQuestion.trial_id.in_(trial_ids)).all()
        by_knowledge: dict[str, dict] = defaultdict(lambda: {'correct': 0, 'answered': 0, 'label': ''})
        mistake_by_label: dict[str, int] = defaultdict(int)

        for question in questions:
            rows = TrialQuestionProgress.query.filter(
                TrialQuestionProgress.question_id == question.id,
                TrialQuestionProgress.user_id.in_(student_ids),
                TrialQuestionProgress.status == 'completed',
            ).all()
            key = question.knowledge_key or 'algo'
            label = QuestionGenerator.label_for_key(key)
            bucket = by_knowledge[key]
            bucket['label'] = label
            for row in rows:
                bucket['answered'] += 1
                if row.is_correct:
                    bucket['correct'] += 1
                else:
                    mistake_by_label[label] += 1

        domain_mastery = []
        for stats in by_knowledge.values():
            answered = stats['answered']
            rate = round((stats['correct'] / answered) * 100) if answered else 0
            domain_mastery.append({'label': stats['label'], 'mastery_rate': rate})
        domain_mastery.sort(key=lambda item: item['mastery_rate'], reverse=True)

        colors = ['#f97316', '#fb923c', '#fdba74', '#fde68a', '#fed7aa', '#ffedd5']
        mistake_types = [
            {'name': name, 'value': count, 'color': colors[index % len(colors)]}
            for index, (name, count) in enumerate(sorted(mistake_by_label.items(), key=lambda item: -item[1]))
        ]

        return {'domain_mastery': domain_mastery, 'mistake_types': mistake_types}
