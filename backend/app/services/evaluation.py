"""学习效果评估：报告、班级学情、推荐动作"""
from collections import defaultdict
from datetime import date, datetime, timedelta

from app.models import TrialQuestion, TrialQuestionProgress, User, UserDailyQuest, db
from app.services.mistake import MistakeService
from app.services.question_generator import QuestionGenerator
from app.services.student_progress import DOMAIN_CATALOG, StudentProgressService
from app.services.teacher import TeacherService


class EvaluationService:
    PERIOD_DAYS = {'7d': 7, '30d': 30}

    @staticmethod
    def _parse_period(period: str) -> int:
        return EvaluationService.PERIOD_DAYS.get(period, 7)

    @staticmethod
    def _period_range(days: int):
        today = date.today()
        start = datetime.combine(today - timedelta(days=days - 1), datetime.min.time())
        end = datetime.combine(today, datetime.max.time())
        return start, end

    @staticmethod
    def _domain_mastery_for_user(user_id: int, start: datetime, end: datetime):
        rows = TrialQuestionProgress.query.filter(
            TrialQuestionProgress.user_id == user_id,
            TrialQuestionProgress.status == 'completed',
            TrialQuestionProgress.answered_at >= start,
            TrialQuestionProgress.answered_at <= end,
        ).all()
        by_key: dict[str, dict] = defaultdict(lambda: {'correct': 0, 'answered': 0})
        for row in rows:
            question = TrialQuestion.query.get(row.question_id)
            key = (question.knowledge_key if question else None) or 'algo'
            bucket = by_key[key]
            bucket['answered'] += 1
            if row.is_correct:
                bucket['correct'] += 1

        result = []
        for domain in DOMAIN_CATALOG:
            keys = domain['knowledge_keys']
            correct = sum(by_key[k]['correct'] for k in keys if k in by_key)
            answered = sum(by_key[k]['answered'] for k in keys if k in by_key)
            rate = round((correct / answered) * 100) if answered else 0
            result.append(
                {
                    'key': domain['key'],
                    'label': domain['title'],
                    'mastery_rate': rate,
                    'answered': answered,
                }
            )
        return result

    @staticmethod
    def _learning_index(user_id: int, start: datetime, end: datetime) -> dict:
        rows = TrialQuestionProgress.query.filter(
            TrialQuestionProgress.user_id == user_id,
            TrialQuestionProgress.status == 'completed',
            TrialQuestionProgress.answered_at >= start,
            TrialQuestionProgress.answered_at <= end,
        ).all()
        correct_rate = 0
        if rows:
            correct = len([r for r in rows if r.is_correct])
            correct_rate = round((correct / len(rows)) * 100)

        quests = UserDailyQuest.query.filter_by(user_id=user_id).all()
        quest_done = sum(1 for q in quests if q.completed_at)
        quest_total = max(len(quests), 1)
        quest_rate = round((quest_done / quest_total) * 100)

        trials = StudentProgressService._completed_trials(user_id)
        trial_score = min(100, len(trials) * 15)

        index = round(correct_rate * 0.5 + quest_rate * 0.25 + trial_score * 0.25)
        if index >= 80:
            level_label = '探索先锋'
        elif index >= 60:
            level_label = '稳步进阶'
        elif index >= 40:
            level_label = '蓄力成长'
        else:
            level_label = '起步探索'

        return {
            'index': index,
            'level_label': level_label,
            'correct_rate': correct_rate,
            'quest_completion_rate': quest_rate,
            'completed_trials': len(trials),
        }

    @staticmethod
    def _risk_tags(user_id: int, domain_mastery: list, start: datetime, end: datetime) -> list[str]:
        tags = []
        rows = TrialQuestionProgress.query.filter(
            TrialQuestionProgress.user_id == user_id,
            TrialQuestionProgress.status == 'completed',
            TrialQuestionProgress.answered_at >= start,
            TrialQuestionProgress.answered_at <= end,
        ).all()
        if not rows:
            tags.append('近期无练习')
        weak = [d for d in domain_mastery if d['answered'] >= 2 and d['mastery_rate'] < 40]
        if weak:
            tags.append(f'薄弱：{weak[0]["label"]}')
        mistakes = MistakeService.list_weak_knowledge(user_id, limit=1)
        if mistakes and mistakes[0]['fail_count'] >= 3:
            tags.append('错题集中')
        return tags

    @staticmethod
    def _recommendations(user_id: int, weak_knowledge: list) -> list[dict]:
        recs = []
        if weak_knowledge:
            w = weak_knowledge[0]
            recs.append(
                {
                    'action': 'emergency_mission',
                    'title': '边界条件补给站',
                    'detail': f'建议巩固「{w["knowledge_label"]}」，完成今日紧急任务。',
                    'knowledge_key': w['knowledge_key'],
                }
            )
            recs.append(
                {
                    'action': 'star_path',
                    'title': '星轨复习',
                    'detail': f'在星轨路径中回顾「{w["knowledge_label"]}」相关知识点。',
                    'knowledge_key': w['knowledge_key'],
                }
            )
        else:
            recs.append(
                {
                    'action': 'daily_quest',
                    'title': '今日委托',
                    'detail': '保持每日委托节奏，积累探索指数。',
                    'knowledge_key': None,
                }
            )
        return recs

    @staticmethod
    def _trend_extended(user_id: int, days: int):
        weekday_labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        x_data = []
        correct_rates = []
        practice_counts = []
        today = date.today()
        span = min(days, 30)

        for offset in range(span - 1, -1, -1):
            day = today - timedelta(days=offset)
            x_data.append(weekday_labels[day.weekday()] if span <= 7 else day.strftime('%m-%d'))
            day_start = datetime.combine(day, datetime.min.time())
            day_end = datetime.combine(day, datetime.max.time())
            rows = TrialQuestionProgress.query.filter(
                TrialQuestionProgress.user_id == user_id,
                TrialQuestionProgress.status == 'completed',
                TrialQuestionProgress.answered_at >= day_start,
                TrialQuestionProgress.answered_at <= day_end,
            ).all()
            practice_counts.append(len(rows))
            if rows:
                correct = len([r for r in rows if r.is_correct])
                correct_rates.append(round((correct / len(rows)) * 100))
            else:
                correct_rates.append(0)

        return {'x_data': x_data, 'correct_rate': correct_rates, 'practice_count': practice_counts}

    @staticmethod
    def get_student_learning_report(user_id: int, period: str = '7d'):
        user = User.query.get(user_id)
        if not user:
            raise ValueError('用户不存在')

        days = EvaluationService._parse_period(period)
        start, end = EvaluationService._period_range(days)
        prev_start = start - timedelta(days=days)
        prev_end = start - timedelta(seconds=1)

        domain_mastery = EvaluationService._domain_mastery_for_user(user_id, start, end)
        prev_mastery = EvaluationService._domain_mastery_for_user(user_id, prev_start, prev_end)
        prev_map = {d['key']: d['mastery_rate'] for d in prev_mastery}

        for item in domain_mastery:
            prev_rate = prev_map.get(item['key'], 0)
            item['delta'] = item['mastery_rate'] - prev_rate if item['answered'] else 0

        summary = EvaluationService._learning_index(user_id, start, end)
        weak = MistakeService.list_weak_knowledge(user_id)
        mistakes = MistakeService.list_for_student(user_id, active_only=True)[:8]
        ability = StudentProgressService.get_ability_stats(user_id)

        return {
            'period': period,
            'summary': summary,
            'domain_mastery': domain_mastery,
            'mistake_highlights': mistakes,
            'weak_knowledge': weak,
            'trend': EvaluationService._trend_extended(user_id, days),
            'radar': ability.get('radar'),
            'risk_tags': EvaluationService._risk_tags(user_id, domain_mastery, start, end),
            'recommendations': EvaluationService._recommendations(user_id, weak),
        }

    @staticmethod
    def get_teacher_student_report(current_user_id: int, student_id: int, role_name: str, period: str = '7d'):
        from app.services.trial import TrialService

        student = User.query.get(student_id)
        if not student or not student.class_id:
            raise ValueError('学生不存在或未分班')
        TrialService._get_teacher_class(student.class_id, current_user_id, role_name)
        report = EvaluationService.get_student_learning_report(student_id, period)
        report['student'] = {
            'id': student.id,
            'username': student.username,
            'real_name': student.real_name or student.username,
        }
        return report

    @staticmethod
    def get_class_evaluation(current_user_id: int, class_id: int | None, period: str = '7d'):
        teacher = User.query.get(current_user_id)
        if not teacher or not teacher.role:
            raise PermissionError('用户信息获取失败')

        from app.models import Class

        role_name = teacher.role.name
        classes_query = Class.query.order_by(Class.created_at.desc())
        if role_name == 'teacher':
            classes_query = classes_query.filter_by(teacher_id=teacher.id)
        classes = classes_query.all()
        selected = TeacherService._select_class(classes, class_id, role_name, teacher.id)
        if not selected:
            return {'class_id': None, 'students': [], 'domain_mastery': [], 'mistake_types': []}

        days = EvaluationService._parse_period(period)
        start, end = EvaluationService._period_range(days)
        students = User.query.filter_by(class_id=selected.id).all()
        student_reports = []
        attention = []

        for student in students:
            if not student.role or student.role.name != 'student':
                continue
            report = EvaluationService.get_student_learning_report(student.id, period)
            entry = {
                'student_id': student.id,
                'username': student.username,
                'real_name': student.real_name or student.username,
                'learning_index': report['summary']['index'],
                'level_label': report['summary']['level_label'],
                'risk_tags': report['risk_tags'],
                'weak_knowledge': report['weak_knowledge'],
            }
            student_reports.append(entry)
            if report['risk_tags']:
                attention.append(entry)

        class_stats = TeacherService.get_class_stats(current_user_id, selected.id)
        return {
            'class_id': selected.id,
            'class_name': selected.name,
            'period': period,
            'domain_mastery': class_stats.get('domain_mastery', []),
            'mistake_types': class_stats.get('mistake_types', []),
            'students': sorted(student_reports, key=lambda s: s['learning_index']),
            'attention_students': attention[:10],
            'avg_learning_index': round(
                sum(s['learning_index'] for s in student_reports) / len(student_reports)
            )
            if student_reports
            else 0,
        }

    @staticmethod
    def export_class_csv(current_user_id: int, class_id: int, role_name: str) -> str:
        from app.services.trial import TrialService
        import csv
        import io

        cls = TrialService._get_teacher_class(class_id, current_user_id, role_name)
        students = User.query.filter_by(class_id=cls.id).all()
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                'student_id',
                'username',
                'real_name',
                'learning_index',
                'level_label',
                'correct_rate',
                'completed_trials',
                'active_mistakes',
                'weak_knowledge',
                'risk_tags',
            ]
        )
        for student in students:
            if not student.role or student.role.name != 'student':
                continue
            report = EvaluationService.get_student_learning_report(student.id, '7d')
            weak = ', '.join(w['knowledge_label'] for w in report['weak_knowledge'][:3])
            writer.writerow(
                [
                    student.id,
                    student.username,
                    student.real_name or '',
                    report['summary']['index'],
                    report['summary']['level_label'],
                    report['summary']['correct_rate'],
                    report['summary']['completed_trials'],
                    len(report['mistake_highlights']),
                    weak,
                    '; '.join(report['risk_tags']),
                ]
            )
        return buf.getvalue()
