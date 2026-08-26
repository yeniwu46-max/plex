"""学习效果评估：报告、班级学情、推荐动作"""
from collections import defaultdict
from datetime import date, datetime, timedelta

from app.models import (
    PersonalizedLearningResource,
    ResourceGenerationTask,
    StudentProfile,
    TrialQuestion,
    TrialQuestionProgress,
    User,
    UserDailyQuest,
    db,
)
from app.services.mistake import MistakeService
from app.services.question_generator import QuestionGenerator
from app.services.student_progress import DOMAIN_CATALOG, StudentProgressService
from app.services.teacher import TeacherService
from app.utils.time import utc_now


class EvaluationService:
    PERIOD_DAYS = {'7d': 7, '30d': 30}
    MIN_EFFECT_SAMPLES = 3
    PHASE_REPORT_COOLDOWN_HOURS = 12

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
            question = db.session.get(TrialQuestion, row.question_id)
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
        user = db.session.get(User, user_id)
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
    def _build_phase_report(user_id: int, period: str, report: dict, profile: StudentProfile | None = None) -> dict:
        """结构化薄弱点报告：证据 + 画像维度 + 下一步（借鉴学习诊断/反馈报告思路）。"""
        summary = report.get('summary') or {}
        trend = report.get('trend') or {}
        weak = report.get('weak_knowledge') or []
        mistakes = report.get('mistake_highlights') or []
        domain_mastery = report.get('domain_mastery') or []
        recommendations = report.get('recommendations') or []

        practice_counts = trend.get('practice_count') or []
        correct_rates = trend.get('correct_rate') or []
        total_practice = sum(practice_counts)
        active_days = len([value for value in practice_counts if value > 0])
        avg_recent_accuracy = (
            round(sum(correct_rates) / len([value for value in correct_rates if value or value == 0]))
            if correct_rates
            else 0
        )
        weakest_domains = sorted(
            [item for item in domain_mastery if item.get('answered', 0) > 0],
            key=lambda item: (item.get('mastery_rate', 0), -item.get('answered', 0)),
        )[:3]
        top_weak = weak[:3]

        profile_dims = dict((profile.dimensions if profile else None) or {})
        identity = profile_dims.get('learning_identity') or profile_dims.get('identity') or {}
        stage_hint = (
            identity.get('stage')
            or profile_dims.get('current_stage')
            or profile_dims.get('stage')
            or summary.get('level_label')
            or '起步探索'
        )
        style_hint = (
            identity.get('mode')
            or profile_dims.get('learning_style')
            or profile_dims.get('preferred_style')
        )
        if isinstance(style_hint, list):
            style_hint = '、'.join(str(x) for x in style_hint[:3])

        highlights = [
            f"阶段指数 {summary.get('index', 0)}，状态为「{summary.get('level_label', '起步探索')}」。",
            f"近 {EvaluationService._parse_period(period)} 天完成 {total_practice} 次练习，活跃 {active_days} 天。",
            f"最近正确率约 {summary.get('correct_rate', avg_recent_accuracy)}%，累计完成试炼 {summary.get('completed_trials', 0)} 个。",
        ]
        if style_hint:
            highlights.append(f"结合当前画像，你更适合「{style_hint}」节奏下的短时巩固。")
        if top_weak:
            highlights.append(
                '主要薄弱点集中在：'
                + '、'.join(item['knowledge_label'] for item in top_weak)
                + '（有错题证据支撑）。'
            )
        elif mistakes:
            highlights.append('已有错题记录，但知识点集中度不高，建议先修复最近失败题。')
        else:
            highlights.append('近期错题证据不足，建议先完成 2-3 道代码试炼以生成更准确诊断。')

        focus_items = []
        for item in top_weak:
            evidence = item.get('fail_count', item.get('mistake_count', 1))
            focus_items.append({
                'label': item['knowledge_label'],
                'reason': f"证据：累计失败 {evidence} 次；建议优先修复关联错题后再做进阶题。",
                'knowledge_key': item.get('knowledge_key'),
            })
        for item in weakest_domains:
            if len(focus_items) >= 4:
                break
            focus_items.append({
                'label': item['label'],
                'reason': (
                    f"证据：本阶段答题 {item.get('answered', 0)} 次，"
                    f"掌握率 {item.get('mastery_rate', 0)}%，属于优先补强域。"
                ),
                'knowledge_key': item.get('key'),
            })
        if not focus_items:
            focus_items.append({
                'label': str(stage_hint),
                'reason': '证据不足：暂以画像阶段为锚点，先完成基础试炼收集信号。',
                'knowledge_key': None,
            })

        next_actions = [
            rec.get('detail') or rec.get('title')
            for rec in recommendations[:4]
            if rec.get('detail') or rec.get('title')
        ]
        if top_weak:
            next_actions.insert(
                0,
                f"打开「{top_weak[0]['knowledge_label']}」相关资源或分层题库，完成 2 道针对性练习。",
            )
        if not next_actions:
            next_actions = [
                '先完成一次星轨代码试炼，收集新的运行结果。',
                '把未通过用例对应的输入输出差异记录到错题本。',
                '完成今日委托后再点「更新报告」刷新薄弱点诊断。',
            ]
        # 去重保序
        seen = set()
        deduped = []
        for action in next_actions:
            text = str(action).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            deduped.append(text)

        return {
            'user_id': user_id,
            'period': period,
            'generated_at': utc_now().isoformat() + 'Z',
            'cooldown_hours': EvaluationService.PHASE_REPORT_COOLDOWN_HOURS,
            'headline': '阶段性薄弱点报告',
            'summary': highlights,
            'focus_items': focus_items[:4],
            'recent_evidence': {
                'practice_count': total_practice,
                'active_days': active_days,
                'correct_rate': summary.get('correct_rate', avg_recent_accuracy),
                'mistake_count': len(mistakes),
                'risk_tags': report.get('risk_tags') or [],
                'profile_stage': str(stage_hint),
            },
            'next_actions': deduped[:4],
        }

    @staticmethod
    def generate_phase_report(user_id: int, period: str = '7d', force: bool = False) -> dict:
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError('用户不存在')

        now = utc_now()
        profile = StudentProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = StudentProfile(user_id=user_id, dimensions={}, completion_rate=0, version=1)
            db.session.add(profile)
            db.session.flush()

        dimensions = dict(profile.dimensions or {})
        previous = dimensions.get('phase_report') or {}
        generated_raw = previous.get('generated_at')
        if generated_raw and not force:
            try:
                last_generated = datetime.fromisoformat(str(generated_raw).replace('Z', ''))
                elapsed = now - last_generated
                cooldown = timedelta(hours=EvaluationService.PHASE_REPORT_COOLDOWN_HOURS)
                if elapsed < cooldown and previous.get('report'):
                    remaining = cooldown - elapsed
                    return {
                        'status': 'cooldown',
                        'report': previous['report'],
                        'next_available_at': (last_generated + cooldown).isoformat() + 'Z',
                        'remaining_seconds': max(1, int(remaining.total_seconds())),
                    }
            except ValueError:
                pass

        base_report = EvaluationService.get_student_learning_report(user_id, period)
        phase_report = EvaluationService._build_phase_report(
            user_id, period, base_report, profile=profile
        )
        dimensions['phase_report'] = {
            'generated_at': phase_report['generated_at'],
            'period': period,
            'report': phase_report,
        }
        profile.dimensions = dimensions
        profile.version = (profile.version or 1) + 1
        db.session.commit()
        return {
            'status': 'generated',
            'report': phase_report,
            'next_available_at': (now + timedelta(hours=EvaluationService.PHASE_REPORT_COOLDOWN_HOURS)).isoformat() + 'Z',
            'remaining_seconds': EvaluationService.PHASE_REPORT_COOLDOWN_HOURS * 3600,
        }

    @staticmethod
    def get_teacher_student_report(current_user_id: int, student_id: int, role_name: str, period: str = '7d'):
        from app.services.trial import TrialService

        student = db.session.get(User, student_id)
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
    def _effect_snapshot(rows: list[TrialQuestionProgress]) -> dict:
        answered = len(rows)
        correct = sum(1 for row in rows if row.is_correct)
        incorrect = answered - correct
        rate = round((correct / answered) * 100, 1) if answered else 0.0
        risk_tags = []
        if answered < EvaluationService.MIN_EFFECT_SAMPLES:
            risk_tags.append('insufficient_sample')
        if answered >= EvaluationService.MIN_EFFECT_SAMPLES and rate < 60:
            risk_tags.append('low_accuracy')
        if incorrect >= 3:
            risk_tags.append('mistakes_concentrated')
        return {
            'correct_rate': rate,
            'answered_count': answered,
            'correct_count': correct,
            'mastery_rate': rate,
            'mistake_count': incorrect,
            'risk_tags': risk_tags,
            'evidence_ids': [row.id for row in rows],
        }

    @staticmethod
    def get_learning_effect(user_id: int, task_id: str | None = None) -> dict:
        query = ResourceGenerationTask.query.filter_by(user_id=user_id)
        if task_id:
            task = query.filter_by(task_id=task_id).first()
        else:
            task = query.filter(
                ResourceGenerationTask.status == 'completed',
            ).order_by(ResourceGenerationTask.completed_at.desc(), ResourceGenerationTask.created_at.desc()).first()
        if not task:
            raise ValueError('个性化资源任务不存在')

        intervention_at = task.created_at
        rows = (
            TrialQuestionProgress.query.join(
                TrialQuestion,
                TrialQuestionProgress.question_id == TrialQuestion.id,
            )
            .filter(
                TrialQuestionProgress.user_id == user_id,
                TrialQuestionProgress.status == 'completed',
                TrialQuestionProgress.answered_at.isnot(None),
                TrialQuestion.knowledge_key == task.knowledge_key,
            )
            .order_by(TrialQuestionProgress.answered_at.asc(), TrialQuestionProgress.id.asc())
            .all()
        )
        before_rows = [row for row in rows if row.answered_at < intervention_at]
        after_rows = [row for row in rows if row.answered_at >= intervention_at]
        before = EvaluationService._effect_snapshot(before_rows)
        after = EvaluationService._effect_snapshot(after_rows)
        sufficient = (
            before['answered_count'] >= EvaluationService.MIN_EFFECT_SAMPLES
            and after['answered_count'] >= EvaluationService.MIN_EFFECT_SAMPLES
        )
        resources = PersonalizedLearningResource.query.filter_by(
            user_id=user_id,
            generation_task_id=task.task_id,
        ).order_by(PersonalizedLearningResource.id.asc()).all()

        def delta(field: str):
            return round(after[field] - before[field], 1) if sufficient else None

        return {
            'status': 'sufficient' if sufficient else 'insufficient_evidence',
            'minimum_samples_per_period': EvaluationService.MIN_EFFECT_SAMPLES,
            'task': {
                'task_id': task.task_id,
                'knowledge_key': task.knowledge_key,
                'profile_version': task.profile_version,
                'resource_types': [resource.resource_type for resource in resources]
                or list(task.requested_types or []),
                'backend': task.backend,
                'intervention_at': intervention_at.isoformat() if intervention_at else None,
            },
            'before': before,
            'after': after,
            'delta': {
                'correct_rate': delta('correct_rate'),
                'answered_count': delta('answered_count'),
                'mastery_rate': delta('mastery_rate'),
                'mistake_count': delta('mistake_count'),
            },
            'evidence_count': len(rows),
        }

    @staticmethod
    def get_teacher_learning_effect(
        current_user_id: int,
        student_id: int,
        role_name: str,
        task_id: str | None = None,
    ) -> dict:
        from app.services.trial import TrialService

        student = db.session.get(User, student_id)
        if not student or not student.class_id:
            raise ValueError('学生不存在或未分班')
        TrialService._get_teacher_class(student.class_id, current_user_id, role_name)
        result = EvaluationService.get_learning_effect(student_id, task_id)
        result['student'] = {
            'id': student.id,
            'username': student.username,
            'real_name': student.real_name or student.username,
        }
        return result

    @staticmethod
    def get_class_evaluation(current_user_id: int, class_id: int | None, period: str = '7d'):
        teacher = db.session.get(User, current_user_id)
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
