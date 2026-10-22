# -*- coding: utf-8 -*-
"""KnowledgeService：Knowledge Intelligence Layer 的公共门面。

小E、学习诊断、路径规划、资源生成等 Agent 统一经此取材；禁止直接操作 VectorStore。
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from flask import current_app

from app.models import KnowledgeConcept, KnowledgeDocument, db

from .graph_service import GraphService
from .index_service import IndexService
from .learner_context_service import LearnerContextService
from .rag_service import KnowledgeRagService, RagPlan
from .rerank_service import RerankService
from .retrieval_service import RetrievalService
from .schemas import RagAnswer
from .settings import knowledge_env, retrieval_config
from .strategy_service import StrategyService

_BOOTSTRAP_LOCK = threading.Lock()


class KnowledgeService:
    # ------------------------------------------------------------------ bootstrap
    @staticmethod
    def ensure_ready(*, seed_graph: bool | None = None, index_builtin: bool | None = None) -> dict[str, Any]:
        """幂等初始化：图谱种子 + 内建课程知识库注册/索引。"""
        env = knowledge_env()
        seed_graph = env['auto_seed'] if seed_graph is None else seed_graph
        index_builtin = env['auto_index_builtin'] if index_builtin is None else index_builtin
        report: dict[str, Any] = {}
        with _BOOTSTRAP_LOCK:
            if seed_graph:
                try:
                    report['graph'] = GraphService.seed_from_registry()
                except Exception as exc:  # noqa: BLE001
                    db.session.rollback()
                    current_app.logger.warning('knowledge graph seed failed: %s', exc)
                    report['graph'] = {'error': str(exc)}
            if index_builtin:
                try:
                    report['builtin_docs'] = IndexService.register_builtin_docs(index=True)
                except Exception as exc:  # noqa: BLE001
                    db.session.rollback()
                    current_app.logger.warning('builtin knowledge docs registration failed: %s', exc)
                    report['builtin_docs'] = {'error': str(exc)}
                try:
                    report['vector_repair'] = IndexService.repair_missing_vectors()
                except Exception as exc:  # noqa: BLE001
                    db.session.rollback()
                    current_app.logger.warning('knowledge vector consistency repair failed: %s', exc)
                    report['vector_repair'] = {'error': str(exc)}
        return report

    @staticmethod
    def bootstrap_async(app) -> threading.Thread | None:
        """应用启动钩子（非 TESTING）：恢复中断的索引任务，并在后台线程完成图谱种子/内建文档索引，不阻塞启动。"""
        if app.config.get('TESTING') or not knowledge_env()['auto_bootstrap']:
            return None

        def _run() -> None:
            with app.app_context():
                try:
                    IndexService.recover_stale_jobs(app)
                except Exception as exc:  # noqa: BLE001
                    db.session.rollback()
                    app.logger.warning('knowledge index job recovery skipped: %s', exc)
                try:
                    report = KnowledgeService.ensure_ready()
                    app.logger.info('knowledge layer ready: %s', report)
                except Exception as exc:  # noqa: BLE001
                    db.session.rollback()
                    app.logger.warning('knowledge layer bootstrap failed: %s', exc)
                finally:
                    db.session.remove()

        thread = threading.Thread(target=_run, name='plex-knowledge-bootstrap', daemon=True)
        thread.start()
        return thread

    @staticmethod
    def is_ready() -> bool:
        return (
            KnowledgeConcept.query.filter_by(node_type='concept').count() > 0
            and KnowledgeDocument.query.filter_by(status='READY').count() > 0
        )

    @staticmethod
    def status() -> dict[str, Any]:
        info = IndexService.index_status()
        info['ready'] = KnowledgeService.is_ready()
        info['course_id'] = retrieval_config().get('course_id')
        return info

    # ------------------------------------------------------------------ RAG
    @staticmethod
    def answer(
        query: str,
        *,
        user_id: int | None,
        role: str = 'student',
        scene: str = 'chat',
        context: dict[str, Any] | None = None,
        history: list[dict[str, str]] | None = None,
        debug: bool = False,
        use_llm: bool | None = None,
        request_id: str | None = None,
    ) -> RagAnswer:
        if user_id is not None and role in {'teacher', 'admin'}:
            from app.services.rag_runtime import ask
            return ask(query, user_id=user_id, role=role, request_id=request_id, scene=scene,
                       context=context, history=history, debug=debug, use_llm=use_llm)
        import uuid
        from contextlib import nullcontext
        from app.services.model_accounting import scope
        request_id=str(uuid.uuid4())
        trace=scope(workflow='rag',user_id=user_id,request_id=request_id,attempt_id=request_id,
                    policy_version='rag-answer-v1') if user_id is not None else nullcontext()
        with trace:
            answer=KnowledgeRagService().query(
                query,user_id=user_id,role=role,scene=scene,context=context,history=history,debug=debug,use_llm=use_llm)
        answer.request_id=request_id
        return answer

    @staticmethod
    def prepare(query: str, *, user_id: int | None, role: str = 'student', scene: str = 'chat', context: dict[str, Any] | None = None, state_snapshot: dict | None = None, learner_context=None) -> RagPlan:
        """两段式（流式）第一步：完成检索/策略/上下文，返回 RagPlan。"""
        return KnowledgeRagService().prepare(query, user_id=user_id, role=role, scene=scene, context=context, state_snapshot=state_snapshot, learner_context=learner_context)

    @staticmethod
    def finalize(plan: RagPlan, **kwargs: Any) -> RagAnswer:
        return KnowledgeRagService().finalize(plan, **kwargs)

    @staticmethod
    def answer_prepared(plan: RagPlan, *, use_llm: bool = False) -> RagAnswer:
        service = KnowledgeRagService()
        text, mode, meta = service.generate(plan, use_llm=use_llm)
        return service.finalize(plan, answer_text=text, generation_mode=mode, model=meta.get('model'),
            provider=meta.get('provider'), token_usage=meta.get('token_usage') or {})

    @staticmethod
    def apply_answer_policy(plan: RagPlan, text: str) -> str:
        """对外部 LLM 生成的文本套用 Answer Policy（Hint Level / 代码策略 / 练习禁泄题）。"""
        return KnowledgeRagService().enforce_answer_policy(plan, text)

    @staticmethod
    def tutor_evidence(query, *, user_id, task, state_snapshot, learner_context=None):
        """Evidence only; the tutor's explicit mode owns the teaching action."""
        plan = KnowledgeService.prepare(query, user_id=user_id, scene='trial',
            context={'task_type': 'practice', 'concept_hint': (task or {}).get('concept_id')},
            state_snapshot=state_snapshot, learner_context=learner_context)
        ids = {row['chunk_id'] for row in plan.context.source_index}
        sources, remaining = [], 9000
        if plan.knowledge_grounded and not plan.blocked_reason:
            for chunk in plan.chunks:
                if chunk.chunk_id not in ids or remaining <= 0:
                    continue
                content = chunk.content[:min(2200, remaining)]
                from hashlib import sha256
                sources.append({**chunk.to_source_dict(preview_chars=0), 'content': content,
                    'content_hash': sha256(chunk.content.encode()).hexdigest()})
                remaining -= len(content)
        return {'status': 'grounded' if sources else 'insufficient_evidence',
                'sources': sources, 'blocked_reason': plan.blocked_reason,
                'prerequisite_gaps': list(plan.retrieval.graph.unmet_prerequisites),
                'query_intent': plan.retrieval.understanding.intent,
                'learning_preferences': dict(learner_context.profile_dimensions) if learner_context else {}}

    @staticmethod
    def tutor_sources_current(user_id, sources):
        from sqlalchemy.orm import Session
        from app.models import KnowledgeChunk
        from .access_service import KnowledgeAccessService
        if not sources:
            return True
        with Session(db.engine) as session:
            rows = KnowledgeAccessService.chunks(user_id, session=session).filter(
                KnowledgeChunk.chunk_id.in_([s['chunk_id'] for s in sources])).all()
            from hashlib import sha256
            current = {(r.chunk_id, r.version): sha256(r.content.encode()).hexdigest() for r in rows}
        return all((s['chunk_id'], s['version']) in current and (not s.get('content_hash')
            or current[(s['chunk_id'], s['version'])] == s['content_hash']) for s in sources)

    @staticmethod
    def plan_context_text(plan: RagPlan | None, *, limit: int = 1400) -> str:
        """把 RagPlan 压成可拼进外部 Prompt 的课程参考 + 教学策略指令；证据不足时返回空串。"""
        if plan is None or plan.blocked_reason or not plan.knowledge_grounded:
            return ''
        parts: list[str] = []
        if plan.context.knowledge_context:
            parts.append(f'知识图谱上下文：\n{plan.context.knowledge_context}')
        if plan.context.retrieved_context:
            parts.append(f'课程材料（只依据这些材料回答，材料没有的内容要明确说不确定）：\n{plan.context.retrieved_context}')
        instructions = StrategyService.instructions(plan.strategy)
        if instructions:
            parts.append(f'教学策略：\n{instructions}')
        if plan.context.hint_instruction:
            parts.append(plan.context.hint_instruction)
        return '\n\n'.join(parts)[:limit]

    @staticmethod
    def student_view(plan: RagPlan | None, *, answer_text: str, generation_mode: str, model: str | None = None, provider: str | None = None) -> dict[str, Any] | None:
        """记录 RAG 日志并返回学生端安全视图（不含 answer 与任何分值）；失败不阻断调用方。"""
        if plan is None:
            return None
        try:
            answer = KnowledgeRagService().finalize(plan, answer_text=answer_text, generation_mode=generation_mode, model=model, provider=provider)
            payload = answer.to_dict()
            payload.pop('answer', None)
            return payload
        except Exception as exc:  # noqa: BLE001
            logging.getLogger(__name__).warning('knowledge finalize failed: %s', exc)
            return None

    @staticmethod
    def retrieve(
        query: str,
        *,
        user_id: int | None = None,
        role: str = 'student',
        context: dict[str, Any] | None = None,
        top_k: int | None = None,
        knowledge_types: list[str] | None = None,
        document_ids: list[str] | None = None,
        require_verified: bool = False,
        log: bool = True,
    ) -> dict[str, Any]:
        return KnowledgeRagService().retrieve_only(
            query, user_id=user_id, role=role, context=context, top_k=top_k,
            knowledge_types=knowledge_types, document_ids=document_ids, require_verified=require_verified, log=log,
        )

    # ------------------------------------------------------------------ agent-facing helpers
    @staticmethod
    def concept_knowledge(
        keys: list[str],
        *,
        user_id: int | None = None,
        knowledge_types: list[str] | None = None,
        top_k: int = 4,
    ) -> dict[str, Any]:
        """按知识点（knowledge_key 或 concept_id）取 grounded 材料与图谱上下文，供 Agent 使用。"""
        concept_ids = GraphService.resolve_concept_ids(keys)
        if not concept_ids:
            return {'concept_ids': [], 'graph': {}, 'chunks': [], 'grounded': False}
        learner = LearnerContextService.build(user_id, role='student') if user_id else None
        retrieval = RetrievalService()
        names = {item['concept_id']: item['name'] for item in GraphService.concepts_brief(concept_ids)}
        query = ' '.join(names.get(c, c) for c in concept_ids)
        qu = retrieval.understand(query, learner)
        qu.concept_ids = concept_ids[:4]
        result = retrieval.retrieve(query, learner, understanding=qu, knowledge_types=knowledge_types, top_k=max(top_k * 3, 12))
        strategy = StrategyService.select(qu, learner, result.graph)
        ranked = RerankService.rerank(result.candidates, understanding=qu, graph=result.graph, learner=learner, strategies=strategy.strategies, top_k=top_k)
        from .access_service import KnowledgeAccessService
        manageable = {c.document_id for c in ranked if KnowledgeAccessService.document(user_id, c.document_id, edit=True)}
        return {
            'concept_ids': concept_ids,
            'concepts': GraphService.concepts_brief(concept_ids),
            'graph': result.graph.to_dict(),
            'strategy': StrategyService.public_view(strategy),
            'chunks': [
                {
                    **c.to_source_dict(preview_chars=0),
                    'content': c.content,
                    'difficulty': c.difficulty,
                    'can_manage': c.document_id in manageable,
                }
                for c in ranked
            ],
            'grounded': bool(ranked),
        }

    @staticmethod
    def resolve_concepts(keys: list[str]) -> list[str]:
        """把 knowledge_key / 中文名 / concept_id 解析为权威 concept_id 列表（去重）。"""
        return GraphService.resolve_concept_ids(keys)

    @staticmethod
    def prerequisites(concept_or_key: str) -> list[dict[str, Any]]:
        ids = GraphService.resolve_concept_ids([concept_or_key])
        if not ids:
            return []
        return GraphService.concepts_brief(GraphService.prerequisites_of(ids[0]))

    @staticmethod
    def concept_detail(concept_id: str) -> dict[str, Any] | None:
        return GraphService.concept_detail(concept_id)
