# -*- coding: utf-8 -*-
"""RAG 日志统计：高频问题、薄弱知识点、置信度分布（教师端 / 管理端）。"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta
from typing import Any

from app.models import Class, RagQueryLog, User
from app.utils.time import utc_now

from .graph_service import GraphService


class KnowledgeAnalyticsService:
    @staticmethod
    def overview(*, days: int = 14, class_id: int | None = None, teacher_id: int | None = None, limit: int = 10) -> dict[str, Any]:
        """teacher_id 给定时只统计该教师名下班级的学生；class_id 进一步限定单个班级。"""
        since = utc_now() - timedelta(days=days)
        query = RagQueryLog.query.filter(RagQueryLog.created_at >= since, RagQueryLog.scene != 'retrieve')
        class_ids: list[int] | None = None
        if teacher_id is not None:
            owned = [row.id for row in Class.query.filter_by(teacher_id=teacher_id).with_entities(Class.id).all()]
            if class_id is not None and class_id not in owned:
                return KnowledgeAnalyticsService._empty(days)
            class_ids = [class_id] if class_id is not None else owned
        elif class_id is not None:
            class_ids = [class_id]
        if class_ids is not None:
            if not class_ids:
                return KnowledgeAnalyticsService._empty(days)
            student_ids = [row.id for row in User.query.filter(User.class_id.in_(class_ids)).with_entities(User.id).all()]
            if not student_ids:
                return KnowledgeAnalyticsService._empty(days)
            query = query.filter(RagQueryLog.user_id.in_(student_ids))
        rows = query.order_by(RagQueryLog.created_at.desc()).limit(5000).all()
        if not rows:
            return KnowledgeAnalyticsService._empty(days)

        by_hash: dict[str, dict[str, Any]] = {}
        concept_counter: Counter = Counter()
        concept_low_conf: Counter = Counter()
        concept_users: dict[str, set] = defaultdict(set)
        intent_counter: Counter = Counter()
        strategy_counter: Counter = Counter()
        level_counter: Counter = Counter()
        latency_total = 0
        for row in rows:
            bucket = by_hash.setdefault(row.query_hash or str(row.id), {'preview': row.query_preview, 'count': 0, 'users': set(), 'concepts': list(row.detected_concepts or [])})
            bucket['count'] += 1
            if row.user_id:
                bucket['users'].add(row.user_id)
            for cid in row.detected_concepts or []:
                concept_counter[cid] += 1
                if row.user_id:
                    concept_users[cid].add(row.user_id)
                if not row.knowledge_grounded:
                    concept_low_conf[cid] += 1
            intent_counter[row.intent or 'general'] += 1
            for s in row.teaching_strategy or []:
                strategy_counter[s] += 1
            level_counter[row.confidence_level or 'UNKNOWN'] += 1
            latency_total += int(row.latency_ms or 0)

        hot = sorted(by_hash.values(), key=lambda b: -b['count'])[:limit]
        names = {item['concept_id']: item['name'] for item in GraphService.concepts_brief(list(concept_counter.keys()))}
        weak = [
            {
                'concept_id': cid,
                'name': names.get(cid, cid),
                'queries': count,
                'students': len(concept_users[cid]),
                'low_confidence': concept_low_conf[cid],
            }
            for cid, count in concept_counter.most_common(limit)
        ]
        return {
            'days': days,
            'total_queries': len(rows),
            'unique_students': len({r.user_id for r in rows if r.user_id}),
            'avg_latency_ms': int(latency_total / len(rows)) if rows else 0,
            'grounded_rate': round(sum(1 for r in rows if r.knowledge_grounded) / len(rows), 3),
            'hot_queries': [
                {'preview': h['preview'], 'count': h['count'], 'students': len(h['users']), 'concepts': [names.get(c, c) for c in h['concepts'][:3]]}
                for h in hot
            ],
            'weak_concepts': weak,
            'intents': dict(intent_counter),
            'strategies': dict(strategy_counter),
            'confidence_levels': dict(level_counter),
        }

    @staticmethod
    def _empty(days: int) -> dict[str, Any]:
        return {
            'days': days,
            'total_queries': 0,
            'unique_students': 0,
            'avg_latency_ms': 0,
            'grounded_rate': 0.0,
            'hot_queries': [],
            'weak_concepts': [],
            'intents': {},
            'strategies': {},
            'confidence_levels': {},
        }

    @staticmethod
    def recent_logs(*, page: int = 1, per_page: int = 20, user_id: int | None = None, scene: str | None = None, status: str | None = None):
        query = RagQueryLog.query
        if user_id:
            query = query.filter(RagQueryLog.user_id == user_id)
        if scene:
            query = query.filter(RagQueryLog.scene == scene)
        if status:
            query = query.filter(RagQueryLog.status == status)
        return query.order_by(RagQueryLog.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def concept_usage(concept_id: str, *, days: int = 30) -> dict[str, Any]:
        since = utc_now() - timedelta(days=days)
        rows = RagQueryLog.query.filter(RagQueryLog.created_at >= since).all()
        hits = [r for r in rows if concept_id in (r.detected_concepts or [])]
        return {
            'concept_id': concept_id,
            'queries': len(hits),
            'students': len({r.user_id for r in hits if r.user_id}),
            'low_confidence': sum(1 for r in hits if not r.knowledge_grounded),
            'strategies': dict(Counter(s for r in hits for s in (r.teaching_strategy or []))),
        }
