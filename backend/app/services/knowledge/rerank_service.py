# -*- coding: utf-8 -*-
"""Rerank：FinalScore = Σ w_i · f_i，权重来自 retrieval.json。

f_semantic  : Hybrid（向量 + 词法）归一化分
f_concept   : chunk 概念与焦点/图谱扩展概念的相关度（焦点 1.0，前置/迷思按图谱权重）
f_learner   : 难度与学习者掌握度匹配 + knowledge_type 与意图/策略匹配
f_verified  : 教师审核
f_quality   : 文档质量分
"""
from __future__ import annotations

from typing import Any

from .schemas import GraphContext, LearnerContext, QueryUnderstanding, RetrievedChunk
from .settings import retrieval_config

_TYPE_PREFERENCE_BY_INTENT = {
    'concept_explain': {'concept_explanation': 1.0, 'example': 0.8, 'summary': 0.7, 'misconception': 0.5, 'extension': 0.4, 'exercise': 0.3, 'solution': 0.3, 'teacher_note': 0.5},
    'debug_error': {'misconception': 1.0, 'concept_explanation': 0.7, 'example': 0.8, 'solution': 0.6, 'summary': 0.4, 'exercise': 0.3, 'extension': 0.3, 'teacher_note': 0.6},
    'practice_request': {'exercise': 1.0, 'example': 0.6, 'concept_explanation': 0.5, 'misconception': 0.5, 'solution': 0.2, 'summary': 0.4, 'extension': 0.3, 'teacher_note': 0.4},
    'compare': {'concept_explanation': 1.0, 'example': 0.8, 'summary': 0.8, 'misconception': 0.6, 'extension': 0.5, 'exercise': 0.3, 'solution': 0.3, 'teacher_note': 0.5},
    'code_review': {'misconception': 0.9, 'example': 1.0, 'concept_explanation': 0.7, 'solution': 0.6, 'summary': 0.4, 'exercise': 0.3, 'extension': 0.5, 'teacher_note': 0.6},
    'extension': {'extension': 1.0, 'concept_explanation': 0.7, 'example': 0.7, 'summary': 0.6, 'misconception': 0.4, 'exercise': 0.4, 'solution': 0.3, 'teacher_note': 0.5},
    'general': {'concept_explanation': 0.9, 'example': 0.8, 'summary': 0.7, 'misconception': 0.6, 'extension': 0.5, 'exercise': 0.4, 'solution': 0.3, 'teacher_note': 0.5},
}


class RerankService:
    @staticmethod
    def rerank(
        candidates: list[RetrievedChunk],
        *,
        understanding: QueryUnderstanding,
        graph: GraphContext,
        learner: LearnerContext | None,
        strategies: list[str] | None = None,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        cfg = retrieval_config().get('rerank', {})
        weights: dict[str, float] = cfg.get('weights', {})
        final_k = int(top_k or cfg.get('final_top_k', 6))
        per_doc = int(cfg.get('diversity_per_document', 3))
        if not candidates:
            return []

        max_hybrid = max((c.hybrid_score for c in candidates), default=0.0) or 1.0
        graph_weights = {node.concept_id: node.weight for node in graph.nodes}
        focus = set(graph.focus_ids)
        type_pref = _TYPE_PREFERENCE_BY_INTENT.get(understanding.intent, _TYPE_PREFERENCE_BY_INTENT['general'])
        strategies = strategies or []

        for chunk in candidates:
            f_semantic = chunk.hybrid_score / max_hybrid
            f_concept = RerankService._concept_relevance(chunk, focus, graph_weights)
            f_learner = RerankService._learner_fit(chunk, learner, graph, type_pref, strategies)
            f_verified = 1.0 if chunk.teacher_verified else 0.0
            f_quality = max(0.0, min(1.0, chunk.quality_score))
            final = (
                weights.get('semantic_similarity', 0.4) * f_semantic
                + weights.get('concept_relevance', 0.25) * f_concept
                + weights.get('learner_fit', 0.2) * f_learner
                + weights.get('teacher_verified', 0.1) * f_verified
                + weights.get('resource_quality', 0.05) * f_quality
            )
            chunk.score_breakdown.update(
                {
                    'semantic_similarity': round(f_semantic, 4),
                    'concept_relevance': round(f_concept, 4),
                    'learner_fit': round(f_learner, 4),
                    'teacher_verified': f_verified,
                    'resource_quality': round(f_quality, 4),
                }
            )
            chunk.final_score = round(final, 4)

        ranked = sorted(candidates, key=lambda c: -c.final_score)
        selected: list[RetrievedChunk] = []
        doc_counts: dict[str, int] = {}
        for chunk in ranked:
            count = doc_counts.get(chunk.document_id, 0)
            if count >= per_doc:
                continue
            doc_counts[chunk.document_id] = count + 1
            selected.append(chunk)
            if len(selected) >= final_k:
                break
        for index, chunk in enumerate(selected, 1):
            chunk.rank = index
        return selected

    @staticmethod
    def _concept_relevance(chunk: RetrievedChunk, focus: set[str], graph_weights: dict[str, float]) -> float:
        if not chunk.concept_ids and not chunk.primary_concept_id:
            return 0.0 if focus else 0.5
        if not focus:
            return 0.5
        best = 0.0
        if chunk.primary_concept_id in focus:
            best = 1.0
        for cid in chunk.concept_ids:
            if cid in focus:
                best = max(best, 0.9)
            elif cid in graph_weights:
                best = max(best, graph_weights[cid] * 0.8)
        return best

    @staticmethod
    def _learner_fit(
        chunk: RetrievedChunk,
        learner: LearnerContext | None,
        graph: GraphContext,
        type_pref: dict[str, float],
        strategies: list[str],
    ) -> float:
        type_score = type_pref.get(chunk.knowledge_type, 0.5)
        # 策略对 knowledge_type 的偏好叠加
        if 'MISCONCEPTION_CORRECTION' in strategies and chunk.knowledge_type == 'misconception':
            type_score = max(type_score, 1.0)
        if 'EXAMPLE_BASED' in strategies and chunk.knowledge_type == 'example':
            type_score = max(type_score, 1.0)
        if 'PRACTICE_RECOMMENDATION' in strategies and chunk.knowledge_type == 'exercise':
            type_score = max(type_score, 0.9)
        if 'PREREQUISITE_REMEDIATION' in strategies and chunk.primary_concept_id in graph.unmet_prerequisites:
            type_score = max(type_score, 1.0)
        if 'EXTENSION' in strategies and chunk.knowledge_type == 'extension':
            type_score = max(type_score, 1.0)

        if not learner or not learner.available:
            return 0.5 * type_score + 0.5 * 0.6
        concept = chunk.primary_concept_id or (chunk.concept_ids[0] if chunk.concept_ids else None)
        mastery = learner.mastery_of(concept, 0.3)
        # 目标难度：掌握度低 → 1-2；中 → 2-3；高 → 3-4
        target = 1.5 if mastery < 0.4 else (2.5 if mastery < 0.75 else 3.5)
        diff_fit = max(0.0, 1.0 - abs(chunk.difficulty - target) / 3.0)
        pref_bonus = 0.0
        if learner.explanation_preference == 'example_first' and chunk.knowledge_type == 'example':
            pref_bonus = 0.15
        elif learner.explanation_preference == 'concise' and chunk.knowledge_type == 'summary':
            pref_bonus = 0.15
        elif learner.explanation_preference == 'detailed' and chunk.knowledge_type == 'concept_explanation':
            pref_bonus = 0.1
        return max(0.0, min(1.0, 0.5 * type_score + 0.4 * diff_fit + pref_bonus))

    @staticmethod
    def explain(chunk: RetrievedChunk) -> dict[str, Any]:
        return {
            'chunk_id': chunk.chunk_id,
            'rank': chunk.rank,
            'final_score': chunk.final_score,
            'hybrid_score': chunk.hybrid_score,
            'vector_score': chunk.vector_score,
            'lexical_score': chunk.lexical_score,
            'breakdown': chunk.score_breakdown,
            'channels': chunk.retrieval_channels,
        }
