"""Conversation-driven seven-dimension student profiles."""
from __future__ import annotations

import re

from app.models import StudentProfile, StudentProfileHistory, db
from app.services.iflytek_spark import IflytekSparkService
from app.services.mistake import MistakeService


PROFILE_DIMENSIONS = (
    'major_background',
    'knowledge_foundation',
    'learning_goal',
    'explanation_preference',
    'mistake_pattern',
    'learning_pace',
    'interest_direction',
)

DIMENSION_LABELS = {
    'major_background': '专业背景',
    'knowledge_foundation': '知识基础',
    'learning_goal': '学习目标',
    'explanation_preference': '讲解偏好',
    'mistake_pattern': '易错模式',
    'learning_pace': '学习节奏',
    'interest_direction': '兴趣方向',
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
        if re.search(r'(基础|学过|会写|不会|掌握|刚开始|零基础)', text):
            changes['knowledge_foundation'] = StudentProfileService._dimension(text[:100], text, 0.82)
        if re.search(r'(目标|希望|想要|考试|两周|比赛|完成)', text):
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
        weak = MistakeService.list_weak_knowledge(user_id, limit=3)
        if not weak:
            return {}
        labels = [item['knowledge_label'] for item in weak]
        return {
            'mistake_pattern': StudentProfileService._dimension(
                '近期薄弱点：' + '、'.join(labels),
                [f"{item['knowledge_label']}失败权重 {item['weight']}" for item in weak],
                0.9,
                'behavior',
            )
        }

    @staticmethod
    def _completion(dimensions: dict) -> int:
        filled = sum(1 for key in PROFILE_DIMENSIONS if (dimensions.get(key) or {}).get('value'))
        return round(filled / len(PROFILE_DIMENSIONS) * 100)

    @staticmethod
    def chat(user_id: int, message: str, confirm_changes: bool = False) -> dict:
        if not message or len(message.strip()) < 2:
            raise ValueError('message不能为空')
        backend = 'local_rules'
        try:
            extracted = StudentProfileService._spark_extract(message)
            backend = 'iflytek_spark'
        except Exception:
            extracted = StudentProfileService._rule_extract(message)
        extracted.update(StudentProfileService._behavior_changes(user_id))

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
