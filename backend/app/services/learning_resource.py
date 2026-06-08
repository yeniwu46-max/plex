"""学习资源库 MVP"""
import json

from app.models import LearningResource, db

from app.services.question_generator import QuestionGenerator

DEFAULT_RESOURCES = [
    {
        'knowledge_key': 'intro',
        'resource_type': 'article',
        'title': '第一段 Python 程序',
        'content_ref': '从 print 输出开始，理解代码如何运行与注释的作用。',
        'difficulty': 20,
    },
    {
        'knowledge_key': 'loop',
        'resource_type': 'article',
        'title': '循环与 range 入门',
        'content_ref': '用 for/while 解决重复计算与简单统计问题。',
        'difficulty': 35,
    },
    {
        'knowledge_key': 'list',
        'resource_type': 'video',
        'title': '列表与字典实战',
        'content_ref': 'https://example.com/resources/python-containers',
        'difficulty': 40,
    },
    {
        'knowledge_key': 'algo',
        'resource_type': 'mcq',
        'title': 'Python 算法小练习',
        'content_ref': '完成求和、查找与去重相关的小题。',
        'difficulty': 45,
    },
]


class LearningResourceService:
    @staticmethod
    def ensure_seed():
        if LearningResource.query.first():
            return
        for item in DEFAULT_RESOURCES:
            db.session.add(LearningResource(**item))
        db.session.commit()

    @staticmethod
    def list_all(active_only: bool = True):
        LearningResourceService.ensure_seed()
        query = LearningResource.query.order_by(LearningResource.knowledge_key, LearningResource.id)
        if active_only:
            query = query.filter_by(is_active=True)
        items = query.all()
        return {
            'items': [row.to_dict() for row in items],
            'total': len(items),
        }

    @staticmethod
    def list_for_knowledge(knowledge_key: str | None):
        LearningResourceService.ensure_seed()
        query = LearningResource.query.filter_by(is_active=True)
        if knowledge_key:
            query = query.filter_by(knowledge_key=knowledge_key)
        items = query.order_by(LearningResource.difficulty).all()
        label = QuestionGenerator.label_for_key(knowledge_key) if knowledge_key else '综合'
        return {
            'knowledge_key': knowledge_key,
            'knowledge_label': label,
            'items': [row.to_dict() for row in items],
        }

    @staticmethod
    def import_json(payload: dict):
        raw = payload.get('resources') or payload.get('items') or []
        if isinstance(raw, str):
            raw = json.loads(raw)
        if not isinstance(raw, list):
            raise ValueError('resources 须为数组')
        created = 0
        for entry in raw:
            key = (entry.get('knowledge_key') or 'algo').strip()
            db.session.add(
                LearningResource(
                    knowledge_key=key,
                    resource_type=entry.get('type') or entry.get('resource_type') or 'article',
                    title=(entry.get('title') or '未命名资源')[:200],
                    content_ref=entry.get('content_ref') or entry.get('content') or '',
                    difficulty=int(entry.get('difficulty') or 50),
                    is_active=bool(entry.get('is_active', True)),
                )
            )
            created += 1
        db.session.commit()
        return {'imported': created}
