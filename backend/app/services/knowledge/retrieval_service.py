# -*- coding: utf-8 -*-
"""Hybrid Retrieval：Query Understanding → Graph Retrieval → Vector + Lexical Retrieval → Metadata Filtering。

产出候选 RetrievedChunk 列表（含 vector/lexical/hybrid 分值），交由 RerankService 重排。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.models import KnowledgeChunk, KnowledgeDocument, db

from .graph_service import GraphService
from .lexical_index import LexicalIndex
from .providers.embedding import cosine
from .providers.llm import get_llm_provider
from .schemas import GraphContext, LearnerContext, QueryUnderstanding, RetrievedChunk
from .settings import prompts_config, retrieval_config, strategy_config
from .text_utils import normalize_text, tokenize
from .vector_service import VectorService

_GENERIC_SUFFIX = re.compile(r'(基础|入门|进阶|详解|操作|方法|概念|应用|实践|技巧|专题|详述|初步)$')

_INTENT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ('debug_error', ('报错', '错误', 'error', 'exception', 'traceback', '为什么不对', '哪里错', '不通过', '失败', 'bug', '异常', '输出不对', '死循环')),
    ('practice_request', ('练习', '题目', '出题', '练一练', '来几道', '习题', '刷题', '再做', '测试我')),
    ('compare', ('区别', '不同', '对比', '比较', '和', '与', 'vs', '哪个好', '还是')),
    ('code_review', ('看看我的代码', '帮我看', '优化', '改进', '重构', '代码质量', '这样写', '规范')),
    ('extension', ('进阶', '深入', '拓展', '更多', '原理', '底层', '还有什么', '延伸')),
    ('concept_explain', ('什么是', '是什么', '怎么用', '如何', '怎么', '解释', '含义', '意思', '用法', '为什么', '讲讲', '介绍')),
)

_ERROR_TYPES = ('SyntaxError', 'IndentationError', 'NameError', 'TypeError', 'ValueError', 'IndexError', 'KeyError',
                'ZeroDivisionError', 'AttributeError', 'RecursionError', 'TabError', 'UnboundLocalError')

_PRACTICE_INTENT_HINT = {'trial', 'practice', 'exercise', 'emergency', 'problem'}


@dataclass
class RetrievalResult:
    understanding: QueryUnderstanding
    graph: GraphContext
    candidates: list[RetrievedChunk] = field(default_factory=list)
    filters: dict[str, Any] = field(default_factory=dict)
    channel_stats: dict[str, int] = field(default_factory=dict)


class RetrievalService:
    def __init__(self, vector: VectorService | None = None):
        self._vector = vector

    @property
    def vector(self) -> VectorService:
        if self._vector is None:
            self._vector = VectorService()
        return self._vector

    # ------------------------------------------------------------------ query understanding
    @staticmethod
    def understand(query: str, learner: LearnerContext | None = None, *, allow_llm: bool | None = None) -> QueryUnderstanding:
        cfg = retrieval_config().get('query_understanding', {})
        normalized = normalize_text(query)
        qu = QueryUnderstanding(query=query, normalized_query=normalized)
        lowered = normalized.lower()

        # intent
        compare_hit = False
        for intent, keywords in _INTENT_RULES:
            if any(k in lowered for k in keywords):
                if intent == 'compare' and not re.search(r'(区别|不同|对比|比较|vs|还是|哪个)', lowered):
                    continue
                qu.intent = intent
                compare_hit = intent == 'compare'
                break
        if qu.intent == 'general' and re.search(r'[?？]$', normalized):
            qu.intent = 'concept_explain'
        del compare_hit

        # error type
        for err in _ERROR_TYPES:
            if err.lower() in lowered:
                qu.error_type = err
                qu.intent = 'debug_error' if qu.intent in {'general', 'concept_explain'} else qu.intent
                break

        # concept detection by lexicon（别名按“出现在多少个概念里”做特异性加权，通用词如“循环”权重低）
        lexicon = GraphService.concept_lexicon()
        alias_freq: dict[str, int] = {}
        head_freq: dict[str, int] = {}
        for item in lexicon:
            for alias in {a.lower() for a in item['aliases']}:
                alias_freq[alias] = alias_freq.get(alias, 0) + 1
                head = _GENERIC_SUFFIX.sub('', alias)
                if head != alias and len(head) >= 2:
                    head_freq[head] = head_freq.get(head, 0) + 1
        scores: dict[str, float] = {}
        query_tokens = set(tokenize(normalized))
        for item in lexicon:
            score = 0.0
            for alias in item['aliases']:
                alias_l = alias.lower()
                if len(alias_l) < 2:
                    continue
                if alias_l in lowered:
                    specificity = 1.0 / (alias_freq.get(alias_l, 1) ** 0.5)
                    score += (1.0 if len(alias_l) >= 4 else 0.7) * specificity
                    continue
                # “字典基础”→“字典”：去掉通用后缀后的核心词命中也计分（权重低于完整别名）
                head = _GENERIC_SUFFIX.sub('', alias_l)
                if head != alias_l and len(head) >= 2 and head in lowered:
                    score += 0.5 / (head_freq.get(head, 1) ** 0.5)
            if item['name'].lower() in lowered:
                score += 0.6
            if score == 0.0 and query_tokens:
                # 兜底：仅当英文标识符（如 range/for/len）或至少两个中文片段重合时才计分，避免单个二元组误命中
                alias_tokens = {t for t in tokenize(' '.join(item['aliases'])) if len(t) >= 2}
                overlap_tokens = {t for t in (query_tokens & alias_tokens) if len(t) >= 2}
                ascii_hits = [t for t in overlap_tokens if t.isascii() and len(t) >= 3]
                cjk_hits = [t for t in overlap_tokens if not t.isascii()]
                if ascii_hits or len(cjk_hits) >= 2:
                    score = 0.3 * len(overlap_tokens) / max(1, len(alias_tokens) ** 0.5) + (0.25 if ascii_hits else 0.0)
            if score > 0:
                scores[item['concept_id']] = min(score, 2.0)

        # 当前任务的概念提示（试炼题绑定的知识点）优先级最高
        task = (learner.current_task if learner else {}) or {}
        hints = task.get('concept_hint') or task.get('concept_ids') or []
        if isinstance(hints, str):
            hints = [hints]
        for cid in GraphService.resolve_concept_ids(hints):
            scores[cid] = scores.get(cid, 0) + 1.5
            qu.method = 'hint'

        # 报错类问题若没识别到概念，用近期错题/薄弱点兜底
        if not scores and learner and qu.intent == 'debug_error':
            for err in learner.recent_errors[:2]:
                if err.get('concept_id'):
                    scores[err['concept_id']] = 0.5

        ranked = sorted(scores.items(), key=lambda kv: -kv[1])
        min_score = float(cfg.get('min_lexical_score', 0.18))
        max_concepts = int(cfg.get('max_concepts', 4))
        qu.concept_ids = [cid for cid, score in ranked if score >= min_score][:max_concepts]
        qu.concept_scores = {cid: round(score, 3) for cid, score in ranked[:8]}
        qu.keywords = sorted(query_tokens)[:12]
        if re.search(r'(简单|入门|基础)', lowered):
            qu.difficulty_hint = 1
        elif re.search(r'(进阶|深入|高级|难)', lowered):
            qu.difficulty_hint = 4

        # 可选 LLM 精炼（默认关闭；开启且有 provider 时才调用）
        use_llm = cfg.get('use_llm', False) if allow_llm is None else allow_llm
        if use_llm:
            RetrievalService._refine_with_llm(qu, lexicon, float(cfg.get('llm_timeout_seconds', 6)))
        return qu

    @staticmethod
    def _refine_with_llm(qu: QueryUnderstanding, lexicon: list[dict], timeout: float) -> None:
        provider = get_llm_provider()
        if not provider.available():
            return
        candidates = [item for item in lexicon if item['concept_id'] in qu.concept_scores] or lexicon[:40]
        listing = '\n'.join(f'- {item["concept_id"]}：{item["name"]}' for item in candidates[:40])
        result = provider.generate_json(
            system=prompts_config().get('query_understanding_system', ''),
            user=f'问题：{qu.query}\n候选知识点：\n{listing}',
            timeout=timeout,
        )
        if not result:
            return
        valid = {item['concept_id'] for item in lexicon}
        ids = [cid for cid in (result.get('concept_ids') or []) if cid in valid]
        if ids:
            qu.concept_ids = ids[:4]
            qu.method = 'llm'
        intent = str(result.get('intent') or '')
        if intent in {'concept_explain', 'debug_error', 'practice_request', 'compare', 'code_review', 'extension', 'general'}:
            qu.intent = intent

    # ------------------------------------------------------------------ retrieval
    def retrieve(
        self,
        query: str,
        learner: LearnerContext | None = None,
        *,
        understanding: QueryUnderstanding | None = None,
        course_id: str | None = None,
        top_k: int | None = None,
        practice_mode: bool | None = None,
        knowledge_types: list[str] | None = None,
        document_ids: list[str] | None = None,
        require_verified: bool = False,
    ) -> RetrievalResult:
        cfg = retrieval_config()
        vector_cfg = cfg.get('vector', {})
        filter_cfg = cfg.get('metadata_filter', {})
        course_id = course_id or cfg.get('course_id', 'python-basics')
        qu = understanding or self.understand(query, learner)

        task_type = str(((learner.current_task if learner else {}) or {}).get('task_type') or '').lower()
        if practice_mode is None:
            practice_mode = task_type in set(strategy_config().get('hint_policy', {}).get('practice_scenes', _PRACTICE_INTENT_HINT))

        graph = GraphService.expand(qu.concept_ids, learner)
        graph_ids = graph.node_ids()

        where: dict[str, Any] = {'course_id': course_id}
        if document_ids:
            where['document_id'] = {'$in': list(document_ids)}
        if require_verified:
            where['teacher_verified'] = True
        excluded_types: set[str] = set()
        if practice_mode:
            excluded_types.update(filter_cfg.get('exclude_knowledge_types_in_practice', ['solution']))

        k = int(top_k or vector_cfg.get('top_k', 20))
        lexical_k = int(vector_cfg.get('lexical_top_k', 20))
        alpha = float(vector_cfg.get('hybrid_alpha', 0.6))

        # 查询扩展：把识别到的概念名拼进查询，提升概念级召回
        concept_names = {item['concept_id']: item['name'] for item in GraphService.concepts_brief(graph_ids)}
        expanded_query = qu.normalized_query
        if qu.concept_ids:
            expanded_query += ' ' + ' '.join(concept_names.get(c, '') for c in qu.concept_ids[:2])

        candidates: dict[str, RetrievedChunk] = {}
        stats = {'vector': 0, 'lexical': 0, 'graph': 0}

        # 通道 1：向量检索（扩展查询用于召回；原始查询向量用于绝对证据）
        query_vector = self.vector.embedding.embed_query(qu.normalized_query)
        if expanded_query != qu.normalized_query:
            expanded_vector = self.vector.embedding.embed_query(expanded_query)
        else:
            expanded_vector = query_vector
        vector_hits = self.vector.search_vector(expanded_vector, k, where)
        max_vec = max((h.score for h in vector_hits), default=0.0) or 1.0
        for hit in vector_hits:
            rc = candidates.setdefault(hit.id, RetrievedChunk(chunk_id=hit.id, document_id=str(hit.metadata.get('document_id', '')), content=''))
            rc.vector_score = round(hit.score, 4)
            rc.score_breakdown['vector_norm'] = round(hit.score / max_vec, 4)
            rc.retrieval_channels.append('vector')
            stats['vector'] += 1

        # 通道 2：BM25 词法检索
        lexical_hits = LexicalIndex.search(expanded_query, lexical_k, {'course_id': course_id} if course_id else None)
        for chunk_id, score, meta in lexical_hits:
            if document_ids and meta.get('document_id') not in document_ids:
                continue
            if require_verified and not meta.get('teacher_verified'):
                continue
            rc = candidates.setdefault(chunk_id, RetrievedChunk(chunk_id=chunk_id, document_id=str(meta.get('document_id', '')), content=''))
            rc.lexical_score = round(score, 4)
            rc.retrieval_channels.append('lexical')
            stats['lexical'] += 1

        # 通道 3：图谱驱动召回（焦点/前置/迷思概念的代表性 chunk）
        if graph_ids:
            priority_ids = graph.focus_ids + graph.unmet_prerequisites + graph.misconceptions
            rows = (
                KnowledgeChunk.query.filter(
                    KnowledgeChunk.status == 'active',
                    KnowledgeChunk.course_id == course_id,
                    KnowledgeChunk.primary_concept_id.in_(priority_ids[:8] or graph_ids[:8]),
                )
                .order_by(KnowledgeChunk.teacher_verified.desc(), KnowledgeChunk.sequence.asc())
                .limit(24)
                .all()
            )
            per_concept: dict[str, int] = {}
            for row in rows:
                if document_ids and row.document_id not in document_ids:
                    continue
                if require_verified and not row.teacher_verified:
                    continue
                count = per_concept.get(row.primary_concept_id, 0)
                if count >= 3:
                    continue
                per_concept[row.primary_concept_id] = count + 1
                rc = candidates.setdefault(row.chunk_id, RetrievedChunk(chunk_id=row.chunk_id, document_id=row.document_id, content=''))
                if 'graph' not in rc.retrieval_channels:
                    rc.retrieval_channels.append('graph')
                    stats['graph'] += 1

        # 装载正文与 metadata（MySQL 为权威）
        if candidates:
            rows = KnowledgeChunk.query.filter(KnowledgeChunk.chunk_id.in_(list(candidates.keys())), KnowledgeChunk.status == 'active').all()
            docs = {
                d.id: d
                for d in KnowledgeDocument.query.filter(KnowledgeDocument.id.in_({r.document_id for r in rows})).all()
            }
            loaded: dict[str, RetrievedChunk] = {}
            for row in rows:
                rc = candidates[row.chunk_id]
                doc = docs.get(row.document_id)
                rc.content = row.content
                rc.title = row.title or ''
                rc.knowledge_type = row.knowledge_type
                rc.concept_ids = list(row.concept_ids or [])
                rc.primary_concept_id = row.primary_concept_id
                rc.difficulty = int(row.difficulty or 2)
                rc.resource_type = row.resource_type
                rc.source = row.source or ''
                rc.source_page = row.source_page
                rc.teacher_verified = bool(row.teacher_verified)
                rc.audience_level = row.audience_level or 'beginner'
                rc.quality_score = float(doc.quality_score) if doc else 0.6
                rc.document_title = doc.title if doc else ''
                loaded[row.chunk_id] = rc
            candidates = loaded

        # 统一按**原始**查询计算绝对证据（词法覆盖率 + 与原始查询向量的余弦）；扩展查询只用于召回
        if candidates:
            ids = list(candidates.keys())
            for cid, cov in LexicalIndex.coverage(qu.normalized_query, ids).items():
                candidates[cid].score_breakdown['lexical_abs'] = cov
            for cid, record in self.vector.store.get(ids).items():
                candidates[cid].score_breakdown['vector_abs'] = round(max(0.0, cosine(query_vector, record.vector)), 4)

        # Metadata filtering
        band = int(filter_cfg.get('difficulty_band', 1))
        target_difficulty = self._target_difficulty(qu, learner, graph)
        filtered: list[RetrievedChunk] = []
        for rc in candidates.values():
            if not rc.content:
                continue
            if rc.knowledge_type in excluded_types:
                continue
            if knowledge_types and rc.knowledge_type not in knowledge_types:
                continue
            if target_difficulty is not None and abs(rc.difficulty - target_difficulty) > band + 1:
                continue
            vec_norm = rc.score_breakdown.get('vector_norm', 0.0)
            rc.hybrid_score = round(alpha * vec_norm + (1 - alpha) * rc.lexical_score, 4)
            if 'graph' in rc.retrieval_channels and rc.hybrid_score < 0.15:
                rc.hybrid_score = 0.15  # 图谱召回保底，保证概念相关材料进入重排
            filtered.append(rc)

        filtered.sort(key=lambda c: -c.hybrid_score)
        return RetrievalResult(
            understanding=qu,
            graph=graph,
            candidates=filtered,
            filters={
                'course_id': course_id,
                'practice_mode': practice_mode,
                'excluded_knowledge_types': sorted(excluded_types),
                'target_difficulty': target_difficulty,
                'difficulty_band': band,
                'document_ids': document_ids or [],
                'require_verified': require_verified,
            },
            channel_stats=stats,
        )

    @staticmethod
    def _target_difficulty(qu: QueryUnderstanding, learner: LearnerContext | None, graph: GraphContext) -> int | None:
        if qu.difficulty_hint:
            return qu.difficulty_hint
        if not graph.focus_ids:
            return None
        rows = GraphService.concepts_brief(graph.focus_ids)
        base = round(sum(int(r.get('difficulty') or 2) for r in rows) / len(rows)) if rows else 2
        if learner and learner.available:
            mastery = learner.mastery_of(graph.focus_ids[0], 0.3)
            if mastery >= 0.75:
                base += 1
            elif mastery < 0.4:
                base -= 1
        return max(1, min(5, base))
