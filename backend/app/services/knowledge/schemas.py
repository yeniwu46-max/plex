# -*- coding: utf-8 -*-
"""Knowledge Intelligence Layer 内部数据结构（dataclass，不依赖 ORM）。"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

INTENTS = (
    'concept_explain',
    'debug_error',
    'practice_request',
    'compare',
    'code_review',
    'extension',
    'general',
)


@dataclass
class QueryUnderstanding:
    query: str
    normalized_query: str
    intent: str = 'general'
    concept_ids: list[str] = field(default_factory=list)
    concept_scores: dict[str, float] = field(default_factory=dict)
    keywords: list[str] = field(default_factory=list)
    error_type: str | None = None
    difficulty_hint: int | None = None
    method: str = 'lexical'  # lexical | llm | hint

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LearnerContext:
    user_id: int | None
    role: str = 'student'
    profile_dimensions: dict[str, Any] = field(default_factory=dict)
    explanation_preference: str = 'default'
    learning_pace: str = ''
    knowledge_foundation: str = ''
    mistake_pattern: str = ''
    mastery: dict[str, float] = field(default_factory=dict)  # concept_id -> 0..1
    mastery_status: dict[str, str] = field(default_factory=dict)  # concept_id -> weak/learning/...
    weak_concepts: list[str] = field(default_factory=list)
    recent_errors: list[dict[str, Any]] = field(default_factory=list)
    current_path: list[str] = field(default_factory=list)
    current_task: dict[str, Any] = field(default_factory=dict)  # task_type / question_id / concept_hint / hint_level
    available: bool = True

    def mastery_of(self, concept_id: str | None, default: float = 0.0) -> float:
        if not concept_id:
            return default
        return float(self.mastery.get(concept_id, default))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphNode:
    concept_id: str
    name: str
    node_type: str
    role: str  # focus | prerequisite | related | misconception | next | example | exercise | resource
    hop: int
    weight: float
    mastery: float | None = None
    description: str = ''

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphContext:
    focus_ids: list[str] = field(default_factory=list)
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    unmet_prerequisites: list[str] = field(default_factory=list)
    misconceptions: list[str] = field(default_factory=list)
    next_recommended: list[str] = field(default_factory=list)

    def node_ids(self) -> list[str]:
        return [node.concept_id for node in self.nodes]

    def weight_of(self, concept_id: str) -> float:
        for node in self.nodes:
            if node.concept_id == concept_id:
                return node.weight
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            'focus_ids': list(self.focus_ids),
            'nodes': [node.to_dict() for node in self.nodes],
            'edges': list(self.edges),
            'unmet_prerequisites': list(self.unmet_prerequisites),
            'misconceptions': list(self.misconceptions),
            'next_recommended': list(self.next_recommended),
        }


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    content: str
    title: str = ''
    knowledge_type: str = 'concept_explanation'
    concept_ids: list[str] = field(default_factory=list)
    primary_concept_id: str | None = None
    difficulty: int = 2
    resource_type: str = 'markdown'
    source: str = ''
    source_page: int | None = None
    teacher_verified: bool = False
    audience_level: str = 'beginner'
    quality_score: float = 0.6
    document_title: str = ''
    vector_score: float = 0.0
    lexical_score: float = 0.0
    hybrid_score: float = 0.0
    score_breakdown: dict[str, float] = field(default_factory=dict)
    final_score: float = 0.0
    rank: int = 0
    retrieval_channels: list[str] = field(default_factory=list)

    def to_debug_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_source_dict(self, preview_chars: int = 160) -> dict[str, Any]:
        """学生端安全视图：不暴露 embedding / similarity / rerank 分值。"""
        text = self.content or ''
        return {
            'chunk_id': self.chunk_id,
            'document_id': self.document_id,
            'title': self.title or self.document_title,
            'document_title': self.document_title,
            'knowledge_type': self.knowledge_type,
            'concept_ids': list(self.concept_ids),
            'resource_type': self.resource_type,
            'source': self.source,
            'source_page': self.source_page,
            'teacher_verified': self.teacher_verified,
            'preview': text[:preview_chars] + ('…' if len(text) > preview_chars else ''),
        }


@dataclass
class TeachingStrategy:
    strategies: list[str] = field(default_factory=list)
    mastery_band: str = 'unknown'  # low | medium | high | unknown
    focus_mastery: float | None = None
    style: str = ''
    hint_level: int | None = None
    hint_max_level: int | None = None
    hint_policy: dict[str, Any] = field(default_factory=dict)
    practice_mode: bool = False
    rationale: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RagAnswer:
    answer: str
    concepts: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    confidence: float
    confidence_level: str  # HIGH | MEDIUM | LOW_CONFIDENCE
    knowledge_grounded: bool
    teaching_strategy: dict[str, Any]
    recommended_next: list[dict[str, Any]]
    hint_level: int | None = None
    intent: str = 'general'
    generation_mode: str = 'extractive'  # llm | extractive | refused
    model: str | None = None
    provider: str | None = None
    latency_ms: int = 0
    token_usage: dict[str, Any] = field(default_factory=dict)
    log_id: int | None = None
    debug: dict[str, Any] | None = None

    def to_dict(self, include_debug: bool = False) -> dict[str, Any]:
        payload = {
            'answer': self.answer,
            'concepts': self.concepts,
            'sources': self.sources,
            'confidence': round(self.confidence, 3),
            'confidence_level': self.confidence_level,
            'knowledge_grounded': self.knowledge_grounded,
            'teaching_strategy': self.teaching_strategy,
            'recommended_next': self.recommended_next,
            'hint_level': self.hint_level,
            'intent': self.intent,
            'generation_mode': self.generation_mode,
            'latency_ms': self.latency_ms,
            'log_id': self.log_id,
        }
        if include_debug:
            payload['model'] = self.model
            payload['provider'] = self.provider
            payload['token_usage'] = self.token_usage
            payload['debug'] = self.debug or {}
        return payload
