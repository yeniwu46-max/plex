"""边界条件补给站 · 紧急任务"""
import random
from collections import defaultdict
from datetime import date, datetime

from app.models import EmergencyMissionQuestion, EmergencyMissionSession, User, db
from app.services.question_generator import KNOWLEDGE_LABELS, QuestionGenerator
from app.services.student_progress import StudentProgressService

EMERGENCY_REWARD_XP = 55
EMERGENCY_QUESTION_COUNT = 3


class EmergencyMissionService:
    @staticmethod
    def _pick_focus_knowledge(user_id: int) -> tuple[str, str]:
        """根据近期掌握情况选薄弱知识点；无数据则随机。"""
        completed = StudentProgressService._completed_trials(user_id)
        skill_map: dict[str, list[int]] = defaultdict(list)
        for part in completed:
            key = QuestionGenerator._normalize_key(part.trial.knowledge_key if part.trial else None)
            skill_map[key].append(part.score or 60)

        if skill_map:
            weakest = min(skill_map.items(), key=lambda item: sum(item[1]) / len(item[1]))
            key = weakest[0]
        else:
            key = random.choice(['dp', 'graph', 'ds', 'frontend', 'algo'])

        label = QuestionGenerator.label_for_key(key)
        return key, label

    @staticmethod
    def _build_question_set(focus_key: str) -> list[dict]:
        """3 道题：2 道聚焦薄弱点，1 道综合/随机。"""
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
            extra_bank = QuestionGenerator.bank_for_key(random.choice(['dp', 'graph', 'ds', 'frontend']))
            item = random.choice(extra_bank)
            if item['stem'] not in {p['stem'] for p in picked}:
                picked.append({**item, 'knowledge_key': focus_key})

        return picked[:EMERGENCY_QUESTION_COUNT]

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
        user = User.query.get(user_id)
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

        for index, item in enumerate(EmergencyMissionService._build_question_set(focus_key)):
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
        session = EmergencyMissionSession.query.get(session_id)
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
        session.submitted_at = datetime.utcnow()

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
                'questions': [q.to_dict(reveal_answer=True) for q in s.questions],
            }
            for s in sessions
        ]
