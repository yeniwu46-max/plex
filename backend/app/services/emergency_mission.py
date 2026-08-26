"""边界条件补给站 · 紧急任务"""
import logging
import random
from collections import defaultdict
from datetime import date, datetime

from app.models import EmergencyMissionQuestion, EmergencyMissionSession, User, db
from app.services.question_generator import KNOWLEDGE_LABELS, QuestionGenerator
from app.services.student_progress import StudentProgressService
from app.utils.time import utc_now

logger = logging.getLogger(__name__)

EMERGENCY_REWARD_XP = 55
EMERGENCY_QUESTION_COUNT = 3


class EmergencyMissionService:
    @staticmethod
    def _pick_focus_knowledge(user_id: int) -> tuple[str, str]:
        """优先错题本薄弱点，再回退试炼均分。"""
        from app.services.mistake import MistakeService

        weak = MistakeService.list_weak_knowledge(user_id, limit=1)
        if weak:
            key = weak[0]['knowledge_key']
            return key, QuestionGenerator.label_for_key(key)

        completed = StudentProgressService._completed_trials(user_id)
        skill_map: dict[str, list[int]] = defaultdict(list)
        for part in completed:
            key = QuestionGenerator._normalize_key(part.trial.knowledge_key if part.trial else None)
            skill_map[key].append(part.score or 60)

        if skill_map:
            weakest = min(skill_map.items(), key=lambda item: sum(item[1]) / len(item[1]))
            key = weakest[0]
        else:
            key = random.choice(['intro', 'var', 'cond', 'loop', 'list', 'algo'])

        label = QuestionGenerator.label_for_key(key)
        return key, label

    @staticmethod
    def _profile_snapshot(user_id: int) -> dict:
        """轻量画像摘要，供星火出题提示词使用。"""
        try:
            from app.services.student_profile import StudentProfileService

            row = StudentProfileService.get_or_create(user_id, persist=False)
            dimensions = row.to_dict().get('dimensions') or {}
            snapshot = {}
            for key, payload in dimensions.items():
                if not isinstance(payload, dict):
                    continue
                value = payload.get('value')
                if value:
                    snapshot[key] = str(value)[:80]
            return snapshot
        except Exception:
            return {}

    @staticmethod
    def _recent_practice_summary(user_id: int, limit: int = 8) -> list[str]:
        """最近练习/错题摘要，帮助星火避开已掌握题并针对薄弱点出题。"""
        from app.services.mistake import MistakeService

        lines: list[str] = []
        weak = MistakeService.list_weak_knowledge(user_id, limit=5)
        for item in weak:
            lines.append(
                f"薄弱点 {item.get('knowledge_label') or item.get('knowledge_key')} "
                f"(失败 {item.get('fail_count', 0)} 次)"
            )

        try:
            from app.models import StudentMistake

            rows = (
                StudentMistake.query.filter_by(user_id=user_id)
                .order_by(StudentMistake.last_failed_at.desc())
                .limit(limit)
                .all()
            )
            for row in rows:
                title = (row.question_title or row.question_ref or '')[:60]
                status = '已掌握' if MistakeService.is_accepted(row) else '未过关'
                label = QuestionGenerator.label_for_key(row.knowledge_key)
                if title:
                    lines.append(f'{status} · {label} · {title}')
        except Exception:
            pass

        completed = StudentProgressService._completed_trials(user_id)[:5]
        for part in completed:
            trial = part.trial
            title = getattr(trial, 'title', None) or getattr(trial, 'knowledge_key', 'trial')
            lines.append(f"试炼均分 {part.score or 0} · {title}")

        return lines[:limit]

    @staticmethod
    def _normalize_spark_questions(payload: dict, focus_key: str) -> list[dict] | None:
        raw_questions = payload.get('questions') if isinstance(payload, dict) else None
        if not isinstance(raw_questions, list):
            return None

        normalized: list[dict] = []
        for item in raw_questions:
            if not isinstance(item, dict):
                continue
            stem = str(item.get('stem') or item.get('question') or '').strip()
            options = item.get('options')
            if not stem or not isinstance(options, list):
                continue
            cleaned_options = [str(opt).strip() for opt in options if str(opt).strip()]
            if len(cleaned_options) < 4:
                continue
            cleaned_options = cleaned_options[:4]
            correct_index = item.get('correct_index', item.get('answer_index', 0))
            try:
                correct_index = int(correct_index)
            except (TypeError, ValueError):
                correct_index = 0
            if correct_index < 0 or correct_index >= len(cleaned_options):
                letter = str(item.get('answer') or item.get('correct') or '').strip().upper()
                if letter in {'A', 'B', 'C', 'D'}:
                    correct_index = ord(letter) - 65
                else:
                    correct_index = 0
            knowledge_key = QuestionGenerator._normalize_key(
                item.get('knowledge_key') or focus_key
            )
            normalized.append(
                {
                    'stem': stem[:240],
                    'options': cleaned_options,
                    'correct_index': correct_index,
                    'knowledge_key': knowledge_key,
                }
            )
            if len(normalized) >= EMERGENCY_QUESTION_COUNT:
                break

        if len(normalized) < EMERGENCY_QUESTION_COUNT:
            return None
        return normalized[:EMERGENCY_QUESTION_COUNT]

    @staticmethod
    def _build_spark_question_set(user_id: int, focus_key: str, focus_label: str) -> list[dict] | None:
        """调用补给站专用星火凭证智能出题；失败返回 None 由调用方本地回退。"""
        from flask import current_app, has_app_context

        from app.services.iflytek_spark import IflytekSparkService, SparkServiceError

        if has_app_context() and current_app.config.get('TESTING') and not current_app.config.get('SPARK_ALLOW_IN_TESTS'):
            return None
        if not IflytekSparkService._resolve_api_password('supply_station'):
            return None

        profile = EmergencyMissionService._profile_snapshot(user_id)
        recent = EmergencyMissionService._recent_practice_summary(user_id)
        system_prompt = (
            '你是 Python 编程教学出题助手，为「边界条件补给站」紧急任务生成选择题。'
            '必须输出 JSON 对象，格式：'
            '{"questions":[{"stem":"...","options":["A选项","B选项","C选项","D选项"],'
            '"correct_index":0,"knowledge_key":"intro"}]}。'
            f'正好 {EMERGENCY_QUESTION_COUNT} 道题；每题 4 个选项；correct_index 为 0-3。'
            '题目应围绕边界条件、易错点与薄弱知识点，难度适中，题干简洁中文，不要 Markdown。'
            'options 里不要再带 A/B/C/D 前缀。'
        )
        user_prompt = (
            f'聚焦知识点：{focus_label}（key={focus_key}）\n'
            f'学习者画像：{profile or "暂无"}\n'
            f'最近练习与薄弱记录：\n' + ('\n'.join(f'- {line}' for line in recent) or '- 暂无记录') + '\n'
            '请生成 3 道不重复的选择题，其中至少 2 道紧扣聚焦知识点，1 道可综合相关边界条件。'
        )
        try:
            result = IflytekSparkService.chat_json(
                system_prompt,
                user_prompt,
                timeout=18,
                purpose='supply_station',
            )
            questions = EmergencyMissionService._normalize_spark_questions(result, focus_key)
            if questions:
                logger.info('emergency_mission spark questions ready focus=%s count=%s', focus_key, len(questions))
                return questions
            logger.warning('emergency_mission spark payload invalid, fallback local bank')
            return None
        except SparkServiceError as exc:
            logger.warning('emergency_mission spark failed code=%s, fallback local bank', exc.code)
            return None
        except Exception:
            logger.exception('emergency_mission spark unexpected error, fallback local bank')
            return None

    @staticmethod
    def _build_question_set(focus_key: str) -> list[dict]:
        """本地题库回退：3 道题，2 道聚焦薄弱点，1 道综合/随机。"""
        focus_bank = list(QuestionGenerator.bank_for_key(focus_key))
        algo_bank = list(QuestionGenerator.bank_for_key('algo'))
        random.shuffle(focus_bank)
        random.shuffle(algo_bank)

        picked: list[dict] = []
        for item in focus_bank:
            if len(picked) >= 2:
                break
            picked.append({**item, 'knowledge_key': focus_key})

        for item in algo_bank:
            if len(picked) >= EMERGENCY_QUESTION_COUNT:
                break
            if item['stem'] not in {p['stem'] for p in picked}:
                picked.append({**item, 'knowledge_key': QuestionGenerator._normalize_key(focus_key)})

        while len(picked) < EMERGENCY_QUESTION_COUNT:
            extra_bank = QuestionGenerator.bank_for_key(random.choice(['intro', 'var', 'loop', 'list', 'algo']))
            item = random.choice(extra_bank)
            if item['stem'] not in {p['stem'] for p in picked}:
                picked.append({**item, 'knowledge_key': focus_key})

        return picked[:EMERGENCY_QUESTION_COUNT]

    @staticmethod
    def _build_deepseek_question_set(user_id: int, focus_key: str, focus_label: str) -> list[dict] | None:
        """补给站出题优先 DeepSeek；失败返回 None 由调用方回退。"""
        from agents.llm_client import chat_json, emergency_provider

        provider = emergency_provider()
        if not provider:
            return None
        profile = EmergencyMissionService._profile_snapshot(user_id)
        recent = EmergencyMissionService._recent_practice_summary(user_id)
        system_prompt = (
            '你是 Python 编程教学出题助手，为「边界条件补给站」紧急任务生成选择题。'
            '必须输出 JSON 对象，格式：'
            '{"questions":[{"stem":"...","options":["A选项","B选项","C选项","D选项"],'
            '"correct_index":0,"knowledge_key":"intro"}]}。'
            f'正好 {EMERGENCY_QUESTION_COUNT} 道题；每题 4 个选项；correct_index 为 0-3。'
            '题目应围绕边界条件、易错点与薄弱知识点，难度适中，题干简洁中文，不要 Markdown。'
            'options 里不要再带 A/B/C/D 前缀。'
        )
        user_prompt = (
            f'聚焦知识点：{focus_label}（key={focus_key}）\n'
            f'学习者画像：{profile or "暂无"}\n'
            f'最近练习与薄弱记录：\n' + ('\n'.join(f'- {line}' for line in recent) or '- 暂无记录') + '\n'
            '请生成 3 道不重复的选择题，其中至少 2 道紧扣聚焦知识点，1 道可综合相关边界条件。'
        )
        try:
            result = chat_json(
                system=system_prompt,
                user=user_prompt,
                timeout=18.0,
                max_tokens=900,
                provider=provider,
            )
            questions = EmergencyMissionService._normalize_spark_questions(result, focus_key)
            if questions:
                logger.info('emergency_mission deepseek questions ready focus=%s count=%s', focus_key, len(questions))
                return questions
            return None
        except Exception:
            logger.exception('emergency_mission deepseek unexpected error, fallback next provider')
            return None

    @staticmethod
    def _resolve_question_set(user_id: int, focus_key: str, focus_label: str) -> list[dict]:
        deepseek_questions = EmergencyMissionService._build_deepseek_question_set(
            user_id, focus_key, focus_label,
        )
        if deepseek_questions:
            return deepseek_questions
        spark_questions = EmergencyMissionService._build_spark_question_set(user_id, focus_key, focus_label)
        if spark_questions:
            return spark_questions
        return EmergencyMissionService._build_question_set(focus_key)

    @staticmethod
    def today_status(user_id: int) -> dict:
        """查询今日紧急任务完成状态。"""
        today_start = datetime.combine(date.today(), datetime.min.time())
        completed_today = (
            EmergencyMissionSession.query.filter(
                EmergencyMissionSession.user_id == user_id,
                EmergencyMissionSession.status == 'completed',
                EmergencyMissionSession.submitted_at >= today_start,
            )
            .order_by(EmergencyMissionSession.id.desc())
            .first()
        )
        if completed_today:
            return {'done': True, 'session_id': completed_today.id}
        return {'done': False, 'session_id': None}

    @staticmethod
    def start_session(user_id: int):
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError('用户不存在')

        today_start = datetime.combine(date.today(), datetime.min.time())
        completed_today = (
            EmergencyMissionSession.query.filter(
                EmergencyMissionSession.user_id == user_id,
                EmergencyMissionSession.status == 'completed',
                EmergencyMissionSession.submitted_at >= today_start,
            )
            .first()
        )
        if completed_today:
            raise ValueError('already_done_today')

        active = (
            EmergencyMissionSession.query.filter_by(user_id=user_id, status='in_progress')
            .order_by(EmergencyMissionSession.id.desc())
            .first()
        )
        if active and active.questions:
            return active.to_dict(include_questions=True, reveal_answers=False)

        focus_key, focus_label = EmergencyMissionService._pick_focus_knowledge(user_id)
        session = EmergencyMissionSession(
            user_id=user_id,
            focus_knowledge_key=focus_key,
            focus_label=focus_label,
            status='in_progress',
        )
        db.session.add(session)
        db.session.flush()

        for index, item in enumerate(
            EmergencyMissionService._resolve_question_set(user_id, focus_key, focus_label)
        ):
            db.session.add(
                EmergencyMissionQuestion(
                    session_id=session.id,
                    sort_order=index + 1,
                    stem=item['stem'],
                    options=item['options'],
                    correct_index=int(item['correct_index']),
                    knowledge_key=item.get('knowledge_key', focus_key),
                )
            )
        db.session.commit()
        return session.to_dict(include_questions=True, reveal_answers=False)

    @staticmethod
    def submit_session(user_id: int, session_id: int, answers: list[dict]):
        session = db.session.get(EmergencyMissionSession, session_id)
        if not session or session.user_id != user_id:
            raise ValueError('任务不存在')
        if session.status != 'in_progress':
            raise ValueError('该任务已提交')

        answer_map = {int(a['question_id']): int(a['selected_index']) for a in answers}
        if len(answer_map) != len(session.questions):
            raise ValueError('请完成全部 3 道题目后再提交')

        correct_count = 0
        for question in session.questions:
            selected = answer_map.get(question.id)
            if selected is None:
                raise ValueError('请完成全部 3 道题目后再提交')
            question.selected_index = selected
            question.is_correct = selected == int(question.correct_index)
            if question.is_correct:
                correct_count += 1

        session.correct_count = correct_count
        session.all_correct = correct_count == len(session.questions)
        session.status = 'submitted'
        session.submitted_at = utc_now()

        if not session.all_correct:
            from app.services.mistake import MistakeService

            wrong_stems = [q.stem for q in session.questions if not q.is_correct]
            MistakeService.record_emergency_wrong(user_id, session.focus_knowledge_key, wrong_stems)

        incentive = None
        if session.all_correct:
            session.reward_points = EMERGENCY_REWARD_XP
            from app.services.incentive import IncentiveService

            incentive = IncentiveService.record_points(
                user_id,
                EMERGENCY_REWARD_XP,
                'emergency_mission:supply_station',
                related_id=session.id,
            )
            session.reward_granted = True

        db.session.commit()

        return {
            'session': session.to_dict(include_questions=True, reveal_answers=True),
            'incentive': incentive,
        }

    @staticmethod
    def _format_answer_letter(index: int | None) -> str:
        if index is None or index < 0:
            return '未作答'
        return chr(65 + int(index))

    @staticmethod
    def generate_ai_explanation(user_id: int, session_id: int) -> dict:
        """按需生成补给站任务的 AI 解析（DeepSeek），并缓存到 session。"""
        from agents.llm_client import chat_text, emergency_provider, strip_asterisks

        session = db.session.get(EmergencyMissionSession, session_id)
        if not session or session.user_id != user_id:
            raise ValueError('任务不存在')
        if session.status != 'submitted':
            raise ValueError('任务尚未提交')

        if isinstance(session.ai_explanation, dict) and session.ai_explanation.get('summary'):
            return session.ai_explanation

        lines: list[str] = []
        for question in session.questions:
            selected = question.selected_index
            correct = question.correct_index
            lines.append(
                f'第{question.sort_order}题：{question.stem}\n'
                f'学生选择：{EmergencyMissionService._format_answer_letter(selected)} · '
                f'{'正确' if question.is_correct else '错误'} · '
                f'正确答案：{EmergencyMissionService._format_answer_letter(correct)}'
            )

        system_prompt = (
            '你叫小E，是 A3 学习系统的学习伙伴，正在为学生讲解边界条件补给站的紧急任务。'
            '用温和、聪明、具体的中文逐题解析，说明为什么正确选项成立、学生错选可能忽略了什么，'
            '像伙伴复盘一样，不要官腔。'
            '不要使用星号或 Markdown 加粗，不要提及 AI、模型或 API，不要用“小E：”开头自我署名。'
            '控制在 280 字以内，分段清晰。'
        )
        user_prompt = (
            f'薄弱知识点：{session.focus_label or session.focus_knowledge_key}\n'
            f'作答情况：{session.correct_count}/{len(session.questions)} 题正确\n\n'
            + '\n\n'.join(lines)
        )

        summary = chat_text(
            system=system_prompt,
            user=user_prompt,
            timeout=12,
            max_tokens=520,
            provider=emergency_provider(),
        )
        if not summary:
            summary = (
                '本次补给站任务已完成。建议回顾每道题涉及的边界条件：'
                '注意循环范围、比较符号与特殊输入（如 0、空值、边界值）。'
                '可在星轨学习中针对「'
                f'{session.focus_label or '相关知识点'}'
                '」再做一次巩固练习。'
            )

        payload = {
            'summary': strip_asterisks(summary),
            'focus_label': session.focus_label,
            'generated_at': utc_now().isoformat(),
        }
        session.ai_explanation = payload
        db.session.commit()
        return payload

    @staticmethod
    def list_archive_records(user_id: int, limit: int = 12):
        sessions = (
            EmergencyMissionSession.query.filter_by(user_id=user_id, status='submitted')
            .order_by(EmergencyMissionSession.submitted_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                'id': s.id,
                'title': '边界条件补给站 · 紧急任务',
                'focus_label': s.focus_label or KNOWLEDGE_LABELS.get(s.focus_knowledge_key, '综合'),
                'date': s.submitted_at.isoformat() if s.submitted_at else None,
                'all_correct': s.all_correct,
                'correct_count': s.correct_count,
                'total_count': len(s.questions),
                'reward_points': s.reward_points if s.reward_granted else 0,
                'has_ai_explanation': bool(isinstance(s.ai_explanation, dict) and s.ai_explanation.get('summary')),
                'questions': [q.to_dict(reveal_answer=True) for q in s.questions],
            }
            for s in sessions
        ]
