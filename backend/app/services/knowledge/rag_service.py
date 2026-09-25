# -*- coding: utf-8 -*-
"""KnowledgeRagService：完整的个性化 Graph-enhanced RAG 流水线。

Safety → Learner Context → Query Understanding → Graph + Hybrid Retrieval → Rerank → Strategy → Context →
Generation（LLM / 抽取式）→ 置信度评估（LOW_CONFIDENCE 时 knowledge_grounded=false，不编造）→ 日志。

支持两段式调用：``prepare()`` 产出 RagPlan（用于流式），``finalize()`` 落日志并组装 RagAnswer。
"""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Any

from flask import current_app

from app.models import RagQueryLog, db
from app.services.course_safety import CourseSafetyService, SafetyViolation

from .context_builder import BuiltContext, ContextBuilder
from .graph_service import GraphService
from .learner_context_service import LearnerContextService
from .providers.llm import LLMProvider, get_llm_provider
from .rerank_service import RerankService
from .retrieval_service import RetrievalResult, RetrievalService
from .schemas import LearnerContext, RagAnswer, RetrievedChunk, TeachingStrategy
from .settings import knowledge_env, prompts_config, retrieval_config
from .strategy_service import STRATEGY_LABELS, StrategyService
from .text_utils import redact_preview, truncate

_CODE_FENCE = re.compile(r'```[\s\S]*?```')
_CODE_PLACEHOLDER = '（此处省略代码——先按上面的思路自己写一版，再来对照）'


@dataclass
class RagPlan:
    query: str
    user_id: int | None
    role: str
    scene: str
    learner: LearnerContext
    retrieval: RetrievalResult
    strategy: TeachingStrategy
    chunks: list[RetrievedChunk]
    context: BuiltContext
    confidence: float
    confidence_level: str
    knowledge_grounded: bool
    started_at: float
    blocked_reason: str | None = None
    debug: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def practice_mode(self) -> bool:
        return self.strategy.practice_mode

    def allow_code(self) -> bool:
        if not self.practice_mode:
            return True
        return bool(self.strategy.hint_policy.get('allow_code', False))

    def allow_solution(self) -> bool:
        if not self.practice_mode:
            return True
        return bool(self.strategy.hint_policy.get('allow_solution', False))

    def apply_code_policy(self, text: str) -> str:
        """练习场景 Answer Policy：不允许代码→移除代码块；允许片段但不允许完整解→截断为前 N 行骨架。"""
        if not text or not self.practice_mode or self.allow_solution():
            return text
        if not self.allow_code():
            return _CODE_FENCE.sub(_CODE_PLACEHOLDER, text)
        max_lines = int(self.strategy.hint_policy.get('max_code_lines', 3) or 3)

        def _trim(match: re.Match) -> str:
            block = match.group(0)
            lines = block.split('\n')
            if len(lines) <= max_lines + 2:  # 含首尾围栏
                return block
            head = lines[0]
            body = [ln for ln in lines[1:-1] if ln.strip()][:max_lines]
            return '\n'.join([head, *body, '    # ……核心逻辑留给你补全', '```'])

        return _CODE_FENCE.sub(_trim, text)


class KnowledgeRagService:
    def __init__(self, retrieval: RetrievalService | None = None, llm: LLMProvider | None = None):
        self._retrieval = retrieval or RetrievalService()
        self._llm = llm or get_llm_provider()

    # ------------------------------------------------------------------ public
    def query(
        self,
        query: str,
        *,
        user_id: int | None,
        role: str = 'student',
        scene: str = 'chat',
        context: dict[str, Any] | None = None,
        history: list[dict[str, str]] | None = None,
        debug: bool = False,
        use_llm: bool | None = None,
        course_id: str | None = None,
    ) -> RagAnswer:
        plan = self.prepare(query, user_id=user_id, role=role, scene=scene, context=context, debug=debug, course_id=course_id)
        if plan.blocked_reason:
            return self.finalize(plan, answer_text=None, generation_mode='refused', status='blocked', error=plan.blocked_reason)
        text, mode, meta = self.generate(plan, history=history, use_llm=use_llm)
        return self.finalize(plan, answer_text=text, generation_mode=mode, model=meta.get('model'), provider=meta.get('provider'), token_usage=meta.get('token_usage') or {})

    def retrieve_only(
        self,
        query: str,
        *,
        user_id: int | None,
        role: str = 'student',
        context: dict[str, Any] | None = None,
        course_id: str | None = None,
        top_k: int | None = None,
        knowledge_types: list[str] | None = None,
        document_ids: list[str] | None = None,
        require_verified: bool = False,
        log: bool = True,
    ) -> dict[str, Any]:
        """仅检索（管理员调试 / Agent 取材），不生成回答。"""
        started = time.perf_counter()
        learner = LearnerContextService.build(user_id, role=role, current_task=context)
        qu = self._retrieval.understand(query, learner)
        result = self._retrieval.retrieve(
            query, learner, understanding=qu, course_id=course_id, top_k=top_k,
            knowledge_types=knowledge_types, document_ids=document_ids, require_verified=require_verified,
        )
        strategy = StrategyService.select(qu, learner, result.graph)
        ranked = RerankService.rerank(result.candidates, understanding=qu, graph=result.graph, learner=learner, strategies=strategy.strategies, top_k=top_k)
        confidence, level, grounded = self._confidence(ranked, qu.concept_ids)
        latency = int((time.perf_counter() - started) * 1000)
        payload = {
            'query': query,
            'understanding': qu.to_dict(),
            'graph': result.graph.to_dict(),
            'candidates': [c.to_debug_dict() for c in result.candidates],
            'reranked': [c.to_debug_dict() for c in ranked],
            'rerank_explain': [RerankService.explain(c) for c in ranked],
            'strategy': strategy.to_dict(),
            'filters': result.filters,
            'channel_stats': result.channel_stats,
            'confidence': round(confidence, 3),
            'confidence_level': level,
            'knowledge_grounded': grounded,
            'learner_context': learner.to_dict(),
            'latency_ms': latency,
        }
        if log:
            row = self._log(
                user_id=user_id, role=role, scene='retrieve', query=query, qu=qu, graph=result.graph, chunks=ranked,
                strategy=strategy, generation_mode='none', model=None, provider=None, latency_ms=latency, token_usage={},
                confidence=confidence, level=level, grounded=grounded, status='ok', error=None,
            )
            payload['log_id'] = row.id if row else None
        return payload

    # ------------------------------------------------------------------ pipeline stages
    def prepare(
        self,
        query: str,
        *,
        user_id: int | None,
        role: str = 'student',
        scene: str = 'chat',
        context: dict[str, Any] | None = None,
        debug: bool = False,
        course_id: str | None = None,
    ) -> RagPlan:
        started = time.perf_counter()
        query = (query or '').strip()
        context = dict(context or {})
        learner = LearnerContextService.build(user_id, role=role, current_task=context)
        blocked: str | None = None
        if not query:
            blocked = 'empty_query'
        else:
            try:
                CourseSafetyService.ensure_safe(query)
            except SafetyViolation as exc:
                blocked = exc.reason_code

        if blocked:
            qu = self._retrieval.understand(query or ' ', learner) if query else self._retrieval.understand(' ', learner)
            from .schemas import GraphContext
            empty = RetrievalResult(understanding=qu, graph=GraphContext())
            strategy = TeachingStrategy(strategies=['DIRECT_EXPLANATION'])
            ctx = BuiltContext('', '', '', '')
            return RagPlan(query, user_id, role, scene, learner, empty, strategy, [], ctx, 0.0, 'LOW_CONFIDENCE', False, started, blocked_reason=blocked, debug=debug)

        qu = self._retrieval.understand(query, learner)
        retrieval = self._retrieval.retrieve(query, learner, understanding=qu, course_id=course_id)
        strategy = StrategyService.select(qu, learner, retrieval.graph, requested_hint_level=context.get('hint_level'))
        ranked = RerankService.rerank(retrieval.candidates, understanding=qu, graph=retrieval.graph, learner=learner, strategies=strategy.strategies)
        confidence, level, grounded = self._confidence(ranked, qu.concept_ids)
        ctx = ContextBuilder.build(query=query, learner=learner, graph=retrieval.graph, chunks=ranked, strategy=strategy, low_confidence=not grounded)
        return RagPlan(query, user_id, role, scene, learner, retrieval, strategy, ranked, ctx, confidence, level, grounded, started, debug=debug)

    def generate(
        self,
        plan: RagPlan,
        *,
        history: list[dict[str, str]] | None = None,
        use_llm: bool | None = None,
    ) -> tuple[str, str, dict[str, Any]]:
        """返回 (answer_text, generation_mode, meta)。"""
        env = knowledge_env()
        llm_enabled = env['rag_llm_enabled'] if use_llm is None else use_llm
        meta: dict[str, Any] = {}
        if llm_enabled and self._llm.available():
            result = self._llm.generate(
                system=plan.context.system_prompt,
                user=plan.context.user_prompt,
                history=history,
                max_tokens=env['rag_llm_max_tokens'],
                timeout=env['rag_llm_timeout'],
            )
            if result and result.text:
                meta = {'model': result.model, 'provider': result.provider, 'token_usage': result.token_usage}
                text = self.enforce_answer_policy(plan, result.text)
                return text, ('llm' if plan.knowledge_grounded else 'refused'), meta
        if not plan.knowledge_grounded:
            return self._no_evidence_answer(plan), 'refused', meta
        return self.enforce_answer_policy(plan, self._extractive_answer(plan)), 'extractive', meta

    def finalize(
        self,
        plan: RagPlan,
        *,
        answer_text: str | None,
        generation_mode: str,
        model: str | None = None,
        provider: str | None = None,
        token_usage: dict[str, Any] | None = None,
        status: str | None = None,
        error: str | None = None,
    ) -> RagAnswer:
        latency = int((time.perf_counter() - plan.started_at) * 1000)
        if plan.blocked_reason:
            answer_text = answer_text or self._blocked_answer(plan.blocked_reason)
        status = status or ('low_confidence' if not plan.knowledge_grounded else 'ok')
        row = self._log(
            user_id=plan.user_id, role=plan.role, scene=plan.scene, query=plan.query, qu=plan.retrieval.understanding,
            graph=plan.retrieval.graph, chunks=plan.chunks, strategy=plan.strategy, generation_mode=generation_mode,
            model=model, provider=provider, latency_ms=latency, token_usage=token_usage or {}, confidence=plan.confidence,
            level=plan.confidence_level, grounded=plan.knowledge_grounded, status=status, error=error,
        )
        used_ids = {item['chunk_id'] for item in plan.context.source_index}
        sources = [
            {**c.to_source_dict(), 'label': next((i['label'] for i in plan.context.source_index if i['chunk_id'] == c.chunk_id), None)}
            for c in plan.chunks if c.chunk_id in used_ids
        ]
        answer = RagAnswer(
            answer=answer_text or '',
            concepts=self._concepts_view(plan),
            sources=sources,
            confidence=plan.confidence,
            confidence_level=plan.confidence_level,
            knowledge_grounded=plan.knowledge_grounded,
            teaching_strategy=StrategyService.public_view(plan.strategy),
            recommended_next=self._recommended_next(plan),
            hint_level=plan.strategy.hint_level,
            intent=plan.retrieval.understanding.intent,
            generation_mode=generation_mode,
            model=model,
            provider=provider,
            latency_ms=latency,
            token_usage=token_usage or {},
            log_id=row.id if row else None,
        )
        if plan.debug:
            answer.debug = {
                'understanding': plan.retrieval.understanding.to_dict(),
                'graph': plan.retrieval.graph.to_dict(),
                'candidates': [c.to_debug_dict() for c in plan.retrieval.candidates],
                'reranked': [c.to_debug_dict() for c in plan.chunks],
                'rerank_explain': [RerankService.explain(c) for c in plan.chunks],
                'strategy': plan.strategy.to_dict(),
                'context': plan.context.to_debug_dict(),
                'filters': plan.retrieval.filters,
                'channel_stats': plan.retrieval.channel_stats,
                'learner_context': plan.learner.to_dict(),
                'blocked_reason': plan.blocked_reason,
            }
        return answer

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _confidence(chunks: list[RetrievedChunk], concept_ids: list[str]) -> tuple[float, str, bool]:
        """置信度基于**绝对**证据强度，而非组内归一化分：

        evidence = max(向量余弦, 词法绝对分) / saturation；concept_factor 取决于是否识别到知识点且材料与之相关；
        support 只统计证据强度超过 min_evidence 的材料。避免“无关问题也因归一化拿到高分”。
        """
        cfg = retrieval_config().get('confidence', {})
        if not chunks:
            return 0.0, 'LOW_CONFIDENCE', False
        from .providers.embedding import get_embedding_provider

        vector_reliable = bool(get_embedding_provider().absolute_similarity_reliable)
        lex_floor = float(cfg.get('lexical_evidence_floor', 0.22))
        lex_sat = float(cfg.get('lexical_evidence_saturation', 0.5)) or 0.5
        vec_floor = float(cfg.get('vector_evidence_floor', 0.42))
        vec_sat = float(cfg.get('vector_evidence_saturation', 0.7)) or 0.7

        def evidence(c: RetrievedChunk) -> tuple[float, bool]:
            """返回 (归一化证据强度 0..1, 是否达到支持门槛)。两条通道各自有 floor/saturation。"""
            lexical = float(c.score_breakdown.get('lexical_abs', 0.0))
            lex_norm = max(0.0, min(1.0, (lexical - lex_floor) / max(1e-6, lex_sat - lex_floor)))
            strength, supported = lex_norm, lexical >= lex_floor
            if vector_reliable:
                vec = float(c.score_breakdown.get('vector_abs', 0.0))
                vec_norm = max(0.0, min(1.0, (vec - vec_floor) / max(1e-6, vec_sat - vec_floor)))
                strength = max(strength, vec_norm)
                supported = supported or vec >= vec_floor
            return strength, supported

        scored = [evidence(c) for c in chunks]
        top_evidence = max(s for s, _ in scored)
        support = sum(1 for _, ok in scored if ok)
        concept_set = set(concept_ids)
        if concept_set and any(concept_set & set(c.concept_ids) for c in chunks):
            concept_factor = 1.0
        elif concept_set:
            concept_factor = 0.55
        else:
            concept_factor = 0.25
        confidence = 0.5 * top_evidence + 0.3 * concept_factor + 0.2 * min(support, 3) / 3
        confidence = max(0.0, min(1.0, confidence))
        grounded = (
            confidence >= float(cfg.get('grounded_threshold', 0.42))
            and support >= int(cfg.get('min_supporting_chunks', 1))
        )
        if not grounded:
            return confidence, 'LOW_CONFIDENCE', False
        level = 'HIGH' if confidence >= float(cfg.get('high_threshold', 0.68)) else 'MEDIUM'
        return confidence, level, True

    def enforce_answer_policy(self, plan: RagPlan, text: str) -> str:
        """练习场景 Answer Policy 的后置保障：提示等级不允许代码时移除代码块。"""
        if not text:
            return text
        return plan.apply_code_policy(text).strip()

    @staticmethod
    def _no_evidence_answer(plan: RagPlan) -> str:
        base = retrieval_config().get('confidence', {}).get('no_evidence_answer', '知识库中暂无足够依据。')
        related = GraphService.concepts_brief(plan.retrieval.understanding.concept_ids[:3] or plan.retrieval.graph.node_ids()[:3])
        if related:
            base += '\n相关知识点：' + '、'.join(item['name'] for item in related)
        return base

    @staticmethod
    def _blocked_answer(reason: str) -> str:
        mapping = {
            'empty_query': '请告诉我你想了解的 Python 问题。',
            'prompt_injection': '这个请求超出了我能协助的范围。我们回到 Python 学习内容吧。',
            'sensitive_content': '这个话题不在课程学习范围内，我们继续聊 Python 好吗？',
            'out_of_course_scope': '这个问题超出了本课程范围，我更擅长 Python 入门相关内容。',
        }
        return mapping.get(reason, '当前无法处理这个请求。')

    def _extractive_answer(self, plan: RagPlan) -> str:
        """无 LLM 时的 grounded 抽取式回答：直接引用重排后的材料，不做任何推断。"""
        prompts = prompts_config()
        lines = [prompts.get('extractive_answer_intro', '根据课程知识库：')]
        allow_solution = plan.allow_solution()
        used = 0
        for item in plan.context.source_index:
            chunk = next((c for c in plan.chunks if c.chunk_id == item['chunk_id']), None)
            if not chunk or (chunk.knowledge_type == 'solution' and not allow_solution):
                continue
            body = plan.apply_code_policy(chunk.content.strip())
            body = re.sub(r'^-\s*(概念|正例|反例|常见错误)：', r'\1：', body, flags=re.MULTILINE)
            body = truncate(body, 420)
            if body.count('```') % 2 == 1:  # 截断落在代码块内部，补全围栏
                body += '\n```'
            lines.append(f'{body} [{item["label"]}]')
            used += 1
            if used >= 3:
                break
        misconceptions = [n for n in plan.retrieval.graph.nodes if n.role == 'misconception' and n.description]
        if misconceptions and 'MISCONCEPTION_CORRECTION' in plan.strategy.strategies:
            lines.append('常见误区提醒：' + truncate(misconceptions[0].description, 160))
        nxt = self._recommended_next(plan)
        if nxt:
            lines.append(prompts.get('extractive_next_step', '下一步建议：{suggestion}').format(suggestion=nxt[0]['reason']))
        return '\n\n'.join(lines)

    @staticmethod
    def _concepts_view(plan: RagPlan) -> list[dict[str, Any]]:
        qu = plan.retrieval.understanding
        out = []
        for item in GraphService.concepts_brief(qu.concept_ids[:4]):
            cid = item['concept_id']
            out.append(
                {
                    **item,
                    'role': 'focus',
                    'mastery_status': plan.learner.mastery_status.get(cid) if plan.learner.available else None,
                }
            )
        for node in plan.retrieval.graph.nodes:
            if node.role in {'prerequisite', 'related'} and node.node_type == 'concept' and len(out) < 8:
                out.append(
                    {
                        'concept_id': node.concept_id,
                        'name': node.name,
                        'node_type': node.node_type,
                        'role': node.role,
                        'mastery_status': plan.learner.mastery_status.get(node.concept_id) if plan.learner.available else None,
                    }
                )
        return out

    @staticmethod
    def _recommended_next(plan: RagPlan) -> list[dict[str, Any]]:
        graph = plan.retrieval.graph
        names = {n.concept_id: n for n in graph.nodes}
        out: list[dict[str, Any]] = []
        if 'PREREQUISITE_REMEDIATION' in plan.strategy.strategies:
            for cid in graph.unmet_prerequisites[:2]:
                node = names.get(cid)
                if node:
                    out.append({'type': 'prerequisite', 'concept_id': cid, 'name': node.name, 'reason': f'先补齐前置知识「{node.name}」再回到当前问题'})
        if 'PRACTICE_RECOMMENDATION' in plan.strategy.strategies or plan.retrieval.understanding.intent == 'practice_request':
            for node in graph.nodes:
                if node.role == 'exercise' and len(out) < 4:
                    out.append({'type': 'exercise', 'concept_id': node.concept_id, 'name': node.name, 'reason': f'用「{node.name}」巩固当前知识点'})
                    break
        if 'MISCONCEPTION_CORRECTION' in plan.strategy.strategies:
            for cid in graph.misconceptions[:1]:
                node = names.get(cid)
                if node:
                    out.append({'type': 'misconception', 'concept_id': cid, 'name': node.name, 'reason': f'对照「{node.name}」检查自己的理解'})
        for cid in graph.next_recommended[:2]:
            node = names.get(cid)
            if node and len(out) < 5:
                out.append({'type': 'next', 'concept_id': cid, 'name': node.name, 'reason': f'掌握后可以继续学习「{node.name}」'})
        if not out and graph.focus_ids:
            focus = GraphService.concepts_brief(graph.focus_ids[:1])
            if focus:
                out.append({'type': 'review', 'concept_id': focus[0]['concept_id'], 'name': focus[0]['name'], 'reason': f'围绕「{focus[0]["name"]}」再做一道基础题巩固'})
        return out

    @staticmethod
    def _log(
        *,
        user_id: int | None,
        role: str,
        scene: str,
        query: str,
        qu,
        graph,
        chunks: list[RetrievedChunk],
        strategy: TeachingStrategy,
        generation_mode: str,
        model: str | None,
        provider: str | None,
        latency_ms: int,
        token_usage: dict[str, Any],
        confidence: float,
        level: str,
        grounded: bool,
        status: str,
        error: str | None,
    ) -> RagQueryLog | None:
        cfg = retrieval_config().get('logging', {})
        preview_chars = int(cfg.get('query_preview_chars', 120))
        store_scores = bool(cfg.get('store_chunk_scores', True))
        try:
            row = RagQueryLog(
                user_id=user_id,
                role=role,
                scene=scene,
                query_hash=hashlib.sha256((query or '').encode('utf-8')).hexdigest(),
                query_preview=redact_preview(query, preview_chars),
                intent=qu.intent if qu else None,
                detected_concepts=list(qu.concept_ids) if qu else [],
                graph_nodes=[{'id': n.concept_id, 'role': n.role, 'hop': n.hop} for n in graph.nodes] if graph else [],
                retrieved_chunks=[c.chunk_id for c in chunks],
                retrieval_scores={c.chunk_id: {'vector': c.vector_score, 'lexical': c.lexical_score, 'hybrid': c.hybrid_score} for c in chunks} if store_scores else {},
                rerank_scores={c.chunk_id: c.final_score for c in chunks} if store_scores else {},
                teaching_strategy=list(strategy.strategies),
                hint_level=strategy.hint_level,
                model=model,
                provider=provider,
                generation_mode=generation_mode,
                latency_ms=latency_ms,
                token_usage=token_usage or {},
                confidence=round(confidence, 4),
                confidence_level=level,
                knowledge_grounded=grounded,
                status=status,
                error_message=(error or '')[:255] or None,
            )
            db.session.add(row)
            db.session.commit()
            return row
        except Exception as exc:  # noqa: BLE001 - 日志失败不影响回答
            db.session.rollback()
            current_app.logger.warning('rag log failed: %s', exc)
            return None


def strategy_label(code: str) -> str:
    return STRATEGY_LABELS.get(code, code)
