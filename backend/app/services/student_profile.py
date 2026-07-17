"""Conversation-driven seven-dimension student profiles."""
from __future__ import annotations

import re
from datetime import datetime

from app.models import (
    StudentProfile,
    StudentProfileHistory,
    StudentProfileSuggestion,
    TrialQuestion,
    TrialQuestionProgress,
    db,
)
from app.services.course_safety import CourseSafetyService
from app.services.iflytek_spark import IflytekSparkService
from app.services.mistake import MistakeService
from app.utils.time import utc_now


PROFILE_DIMENSIONS = (
    'major_background',
    'knowledge_foundation',
    'learning_goal',
    'explanation_preference',
    'mistake_pattern',
    'learning_pace',
    'interest_direction',
    'cognitive_state',
)

DIMENSION_LABELS = {
    'major_background': '专业背景',
    'knowledge_foundation': '知识基础',
    'learning_goal': '学习目标',
    'explanation_preference': '讲解偏好',
    'mistake_pattern': '易错模式',
    'learning_pace': '学习节奏',
    'interest_direction': '兴趣方向',
    'cognitive_state': '当前学习状态',
}


class StudentProfileService:
    @staticmethod
    def _empty_dimension():
        return {'value': None, 'confidence': 0.0, 'evidence': [], 'source': 'conversation'}

    @staticmethod
    def get_or_create(user_id: int, persist: bool = False) -> StudentProfile:
        row = StudentProfile.query.filter_by(user_id=user_id).first()
        if row:
            return row
        row = StudentProfile(
            user_id=user_id,
            dimensions={key: StudentProfileService._empty_dimension() for key in PROFILE_DIMENSIONS},
            completion_rate=0,
            version=1,
        )
        if persist:
            db.session.add(row)
            db.session.commit()
        return row

    @staticmethod
    def _dimension(value, evidence, confidence=0.86, source='conversation'):
        return {
            'value': value,
            'confidence': round(float(confidence), 2),
            'evidence': [evidence] if isinstance(evidence, str) else list(evidence),
            'source': source,
        }

    @staticmethod
    def _rule_extract(message: str) -> dict:
        text = message.strip()
        changes = {}
        if re.search(r'(计算机|软件|人工智能|电子信息|大[一二三四]|研究生|专业)', text):
            changes['major_background'] = StudentProfileService._dimension(text[:80], text)
        if re.search(
            r'(零基础|基础.{0,4}(不牢|薄弱|较差|一般|还行|扎实)|'
            r'学过|会写|不会|掌握|刚开始)',
            text,
        ):
            changes['knowledge_foundation'] = StudentProfileService._dimension(text[:100], text, 0.82)
        if re.search(
            r'(目标|想要|考试|两周|比赛|完成|'
            r'画像|学习情况|最近练习|'
            r'希望.{0,20}(掌握|提升|通过|完成|参加|学会))',
            text,
        ):
            changes['learning_goal'] = StudentProfileService._dimension(text[:100], text)
        if re.search(r'(例子|案例|图|视频|分步|详细|简洁|代码)', text):
            preference = '案例优先、分步骤讲解' if re.search(r'(例子|案例|代码|分步)', text) else text[:80]
            changes['explanation_preference'] = StudentProfileService._dimension(preference, text)
        if re.search(r'(容易错|总是错|边界|下标|循环|缩进|异常)', text):
            changes['mistake_pattern'] = StudentProfileService._dimension(text[:100], text, 0.8)
        pace = re.search(r'(每天|每日|每周).{0,12}?(\d+).{0,4}?(分钟|小时|次)', text)
        if pace:
            changes['learning_pace'] = StudentProfileService._dimension(pace.group(0), pace.group(0), 0.92)
        elif re.search(r'(节奏|慢一点|快一点|碎片时间)', text):
            changes['learning_pace'] = StudentProfileService._dimension(text[:80], text, 0.78)
        if re.search(r'(喜欢|兴趣|游戏|数据|爬虫|网站|算法|项目)', text):
            changes['interest_direction'] = StudentProfileService._dimension(text[:100], text)
        return changes

    @staticmethod
    def _spark_extract(message: str) -> dict:
        prompt = (
            '只输出 JSON 对象。键仅允许为：' + ','.join(PROFILE_DIMENSIONS) +
            '。每个值包含 value、confidence(0-1)、evidence(字符串数组)、source="conversation"。'
            '未识别的维度不要输出。不得推断敏感个人信息。'
        )
        result = IflytekSparkService.chat_json(prompt, message)
        return {key: value for key, value in result.items() if key in PROFILE_DIMENSIONS and isinstance(value, dict)}

    @staticmethod
    def _behavior_changes(user_id: int) -> dict:
        changes = {}
        weak = MistakeService.list_weak_knowledge(user_id, limit=3)
        if weak:
            labels = [item['knowledge_label'] for item in weak]
            changes['mistake_pattern'] = StudentProfileService._dimension(
                '近期薄弱点：' + '、'.join(labels),
                [f"{item['knowledge_label']}失败权重 {item['weight']}" for item in weak],
                0.9,
                'behavior',
            )

        recent_rows = (
            TrialQuestionProgress.query.filter_by(user_id=user_id, status='completed')
            .order_by(TrialQuestionProgress.answered_at.desc(), TrialQuestionProgress.id.desc())
            .limit(20)
            .all()
        )
        if recent_rows:
            correct = sum(1 for row in recent_rows if row.is_correct)
            accuracy = round(correct / len(recent_rows) * 100)
            question_ids = [row.question_id for row in recent_rows if row.question_id]
            questions = TrialQuestion.query.filter(TrialQuestion.id.in_(question_ids)).all() if question_ids else []
            knowledge_labels = []
            for question in questions:
                label = getattr(question, 'knowledge_label', None) or getattr(question, 'knowledge_key', None)
                if label and label not in knowledge_labels:
                    knowledge_labels.append(label)
            if accuracy >= 80:
                foundation = f'近期练习正确率 {accuracy}%，基础表现较稳定'
                confidence = 0.82
            elif accuracy >= 60:
                foundation = f'近期练习正确率 {accuracy}%，基础处于巩固阶段'
                confidence = 0.78
            else:
                foundation = f'近期练习正确率 {accuracy}%，基础仍需补强'
                confidence = 0.86
            changes['knowledge_foundation'] = StudentProfileService._dimension(
                foundation,
                [f'最近完成 {len(recent_rows)} 次练习，正确 {correct} 次'],
                confidence,
                'behavior',
            )
            changes['learning_pace'] = StudentProfileService._dimension(
                f'近阶段已完成 {len(recent_rows)} 次练习，建议按每日短练节奏推进',
                '由最近练习记录自动生成',
                0.76,
                'behavior',
            )
            state = '学习状态稳定' if accuracy >= 60 else '需要支持：近期连续错误可能带来挫败感'
            changes['cognitive_state'] = StudentProfileService._dimension(
                state, [f'最近练习正确率 {accuracy}%'], .8 if accuracy >= 60 else .86, 'behavior'
            )
            if knowledge_labels:
                changes['interest_direction'] = StudentProfileService._dimension(
                    '近期关注：' + '、'.join(knowledge_labels[:3]),
                    '由最近练习知识点自动生成',
                    0.72,
                    'behavior',
                )
        return changes

    @staticmethod
    def diagnostic_questions() -> list[dict]:
        # (knowledge_key, question_type, stem, options, correct_index, code_preview)
        specs = [
            ('syntax', 'single_choice', '在 Python 中，用于把文本输出到屏幕的内置函数是？',
             ['print()', 'echo()', 'write()', 'console.log()'], 0, None),
            ('var', 'code_reading', '运行下面这段代码，输出结果是什么？',
             ['True', 'False', '报错', '3'], 1, 'x = 3\ny = "3"\nprint(x == y)'),
            ('cond', 'scenario', '你要根据分数判断是否及格（≥60 及格，否则不及格），最合适的结构是？',
             ['if / else 条件判断', 'for 循环遍历', '直接 def 定义函数', 'import 导入模块'], 0, None),
            ('cond', 'code_reading', '阅读代码，程序会打印出什么？',
             ['及格', '不及格', '报错', '没有任何输出'], 1, 'score = 45\nif score >= 60:\n    print("及格")\nelse:\n    print("不及格")'),
            ('loop', 'code_reading', '下面的循环会依次输出哪些内容？',
             ['a 和 b（各占一行）', 'ab', '0 和 1', '报错'], 0, 'for ch in "ab":\n    print(ch)'),
            ('range', 'code_reading', 'range(3) 配合循环，会打印出哪些数字？',
             ['0 1 2', '1 2 3', '0 1 2 3', '只打印 3'], 0, 'for i in range(3):\n    print(i)'),
            ('func', 'fill_blank', '补全空格：定义函数后，用于把结果交还给调用者的关键字是 ____',
             ['return', 'yield', 'print', 'out'], 0, 'def add(a, b):\n    ____ a + b'),
            ('func', 'code_reading', '调用函数后，最终会打印什么？',
             ['16', '8', '4', 'nn'], 0, 'def square(n):\n    return n * n\n\nprint(square(4))'),
            ('list', 'code_reading', '列表索引从 0 开始，下面代码会输出？',
             ['a', 'b', 'c', '1'], 1, 'items = ["a", "b", "c"]\nprint(items[1])'),
            ('list', 'true_false', '判断对错：列表（list）创建后，其中的元素仍然可以被修改。',
             ['正确', '错误'], 0, None),
            ('except', 'scenario', '程序可能因用户输入而崩溃，为了优雅地处理错误，应该怎么做？',
             ['把可能出错的代码放进 try 块，并用 except 捕获', '把代码全部写在最外层', '把出错的代码注释掉', '用 print 把代码包起来'], 0, None),
            ('except', 'true_false', '判断对错：try 后面必须紧跟 finally，程序才能正常运行。',
             ['正确', '错误'], 1, None),
        ]
        return [
            {'id': f'q{i+1}', 'knowledge_key': key, 'question_type': qtype, 'stem': stem,
             'options': options, 'correct_index': answer, 'code_preview': preview}
            for i, (key, qtype, stem, options, answer, preview) in enumerate(specs)
        ]

    @staticmethod
    def diagnostic_status(user_id: int) -> dict:
        from app.models import StudentProfileDiagnostic
        row = StudentProfileDiagnostic.query.filter_by(user_id=user_id).first()
        return row.to_dict() if row else {'status': 'pending', 'answers': {}, 'mastery': {}}

    @staticmethod
    def submit_diagnostic(user_id: int, answers: dict | None, skip: bool) -> dict:
        from app.models import StudentProfileDiagnostic
        row = StudentProfileDiagnostic.query.filter_by(user_id=user_id).first() or StudentProfileDiagnostic(user_id=user_id)
        if skip:
            row.status, row.answers, row.mastery, row.skipped_at = 'skipped', {}, {}, utc_now()
            change = StudentProfileService._dimension('入门测验已跳过，Python 基础待学习行为补全', '学生跳过入门测验', .2, 'confirmed')
        else:
            questions = {q['id']: q for q in StudentProfileService.diagnostic_questions()}
            if set((answers or {}).keys()) != set(questions):
                raise ValueError('请完成全部 12 道入门测验题目')
            mastery = {}
            for q in questions.values():
                item = mastery.setdefault(q['knowledge_key'], {'correct': 0, 'total': 0})
                item['total'] += 1; item['correct'] += int(answers[q['id']] == q['correct_index'])
            row.status, row.answers, row.mastery, row.completed_at = 'completed', answers, mastery, utc_now()
            correct = sum(v['correct'] for v in mastery.values())
            change = StudentProfileService._dimension(f'Python 入门测验正确率 {round(correct / 12 * 100)}%', [f'{k}: {v["correct"]}/{v["total"]}' for k, v in mastery.items()], .95, 'behavior')
        db.session.add(row); db.session.commit()
        return {'diagnostic': row.to_dict(), 'profile': StudentProfileService.apply_changes(user_id, {'knowledge_foundation': change}, 'onboarding_diagnostic', 'local_rules'), 'backend': 'local_rules'}

    @staticmethod
    def create_behavior_suggestion(user_id: int) -> dict | None:
        candidate = StudentProfileService._behavior_changes(user_id).get('mistake_pattern')
        if not candidate or not candidate.get('value'):
            return None
        value = str(candidate['value'])[:500]
        profile = StudentProfileService.get_or_create(user_id)
        existing = StudentProfileSuggestion.query.filter_by(
            user_id=user_id,
            dimension='mistake_pattern',
            proposed_value=value,
            status='pending',
        ).first()
        if existing:
            return existing.to_dict()
        row = StudentProfileSuggestion(
            user_id=user_id,
            dimension='mistake_pattern',
            proposed_value=value,
            evidence=candidate.get('evidence') or [],
            source='behavior',
            status='pending',
            profile_version=profile.version if profile.id else 0,
        )
        db.session.add(row)
        db.session.commit()
        return row.to_dict()

    @staticmethod
    def _completion(dimensions: dict) -> int:
        # cognitive_state is inferred from behavior and cannot reasonably be
        # required from a student-entered profile form.  The seven explicit
        # learner dimensions are therefore the completion contract.
        required = tuple(key for key in PROFILE_DIMENSIONS if key != 'cognitive_state')
        filled = sum(1 for key in required if (dimensions.get(key) or {}).get('value'))
        return round(filled / len(required) * 100)

    @staticmethod
    def chat(user_id: int, message: str, confirm_changes: bool = False) -> dict:
        if not message or len(message.strip()) < 2:
            raise ValueError('message不能为空')
        CourseSafetyService.ensure_safe(message)
        backend = 'local_rules'
        try:
            from agents.learning_profile_agent import LearningProfileAgent
            recent = TrialQuestionProgress.query.filter_by(user_id=user_id, status='completed').count()
            extracted, backend = LearningProfileAgent.analyze({'message': message[:600], 'practice_count': recent, 'weak_knowledge': MistakeService.list_weak_knowledge(user_id, 3)})
            if not extracted:
                extracted = StudentProfileService._rule_extract(message)
        except Exception:
            extracted = StudentProfileService._rule_extract(message)
        extracted.update(StudentProfileService._behavior_changes(user_id))
        extracted.setdefault('cognitive_state', StudentProfileService._dimension(
            '当前状态待后续练习补全', '尚无足够连续作答行为', 0.75, 'mixed'
        ))

        row = StudentProfileService.get_or_create(user_id)
        existing = row.dimensions or {}
        proposed = []
        accepted = {}
        for key, value in extracted.items():
            confidence = float(value.get('confidence') or 0)
            item = {
                'dimension': key,
                'label': DIMENSION_LABELS[key],
                'old_value': (existing.get(key) or {}).get('value'),
                'new_value': value.get('value'),
                'confidence': confidence,
                'evidence': value.get('evidence') or [],
                'requires_confirmation': confidence < 0.75,
            }
            proposed.append(item)
            if confirm_changes or confidence >= 0.75:
                accepted[key] = value

        if accepted:
            StudentProfileService.apply_changes(user_id, accepted, 'conversation', backend)
            row = StudentProfile.query.filter_by(user_id=user_id).first()

        return {
            'conversation_id': f'profile-{user_id}',
            'assistant_reply': '已识别画像信息，请确认低置信度字段。' if proposed else '暂未识别到画像字段，请补充专业、目标、偏好、节奏或兴趣。',
            'proposed_changes': proposed,
            'profile': row.to_dict() if row and row.id else StudentProfileService.get_or_create(user_id).to_dict(),
            'backend': backend,
            'safety': {'passed': True, 'flags': []},
        }

    @staticmethod
    def apply_changes(user_id: int, changes: dict, reason: str, backend: str = 'manual') -> dict:
        row = StudentProfileService.get_or_create(user_id, persist=True)
        dimensions = dict(row.dimensions or {})
        normalized = {}
        for key, raw in changes.items():
            if key not in PROFILE_DIMENSIONS:
                continue
            value = raw if isinstance(raw, dict) else StudentProfileService._dimension(
                str(raw), '学生人工修正', 1.0, 'confirmed'
            )
            if reason == 'student_correction':
                value = {**value, 'source': 'confirmed', 'confidence': 1.0}
            dimensions[key] = value
            normalized[key] = value
        if not normalized:
            raise ValueError('没有有效画像字段')
        if reason == 'student_correction':
            # Keep an explicitly completed profile internally consistent: an
            # optional, still-empty cognitive-state slot is not conversation
            # evidence, but it belongs to the student's confirmed profile
            # version with zero confidence until behavior supplies a value.
            cognitive = dict(dimensions.get('cognitive_state') or {})
            if not cognitive.get('value'):
                cognitive['source'] = 'confirmed'
                dimensions['cognitive_state'] = cognitive
        row.dimensions = dimensions
        row.version = (row.version or 0) + 1
        row.completion_rate = StudentProfileService._completion(dimensions)
        db.session.add(StudentProfileHistory(
            user_id=user_id,
            version=row.version,
            dimensions=dimensions,
            changes=normalized,
            reason=reason,
            backend=backend,
        ))
        db.session.commit()
        return row.to_dict()

    @staticmethod
    def history(user_id: int, page: int = 1, page_size: int = 20) -> dict:
        query = StudentProfileHistory.query.filter_by(user_id=user_id).order_by(
            StudentProfileHistory.version.desc()
        )
        pagination = query.paginate(page=max(1, page), per_page=min(max(page_size, 1), 100), error_out=False)
        return {
            'items': [item.to_dict() for item in pagination.items],
            'total': pagination.total,
            'page': pagination.page,
            'page_size': pagination.per_page,
        }

    @staticmethod
    def suggestions(user_id: int, status: str = 'pending') -> dict:
        query = StudentProfileSuggestion.query.filter_by(user_id=user_id)
        if status:
            query = query.filter_by(status=status)
        rows = query.order_by(StudentProfileSuggestion.created_at.desc()).all()
        return {'items': [row.to_dict() for row in rows], 'total': len(rows)}

    @staticmethod
    def resolve_suggestion(user_id: int, suggestion_id: int, action: str) -> dict:
        if action not in ('accepted', 'rejected'):
            raise ValueError('action必须为accepted或rejected')
        row = StudentProfileSuggestion.query.filter_by(
            id=suggestion_id,
            user_id=user_id,
        ).first()
        if not row:
            raise LookupError('画像建议不存在')
        if row.status != 'pending':
            raise ValueError('画像建议已经处理')
        profile = None
        if action == 'accepted':
            profile = StudentProfileService.apply_changes(
                user_id,
                {
                    row.dimension: StudentProfileService._dimension(
                        row.proposed_value,
                        row.evidence,
                        1.0,
                        'confirmed',
                    )
                },
                'behavior_confirmed',
                'behavior',
            )
        row.status = action
        row.resolved_at = utc_now()
        db.session.commit()
        return {'suggestion': row.to_dict(), 'profile': profile}
