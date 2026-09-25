# -*- coding: utf-8 -*-
"""构造四类上下文：learner_context / knowledge_context / retrieved_context / teaching_strategy，并拼装 Prompt。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .graph_service import GraphService
from .learner_context_service import LearnerContextService
from .schemas import GraphContext, LearnerContext, RetrievedChunk, TeachingStrategy
from .settings import prompts_config, retrieval_config
from .strategy_service import StrategyService
from .text_utils import truncate

_ROLE_LABEL = {
    'focus': '当前知识点',
    'prerequisite': '前置知识点',
    'related': '相关知识点',
    'misconception': '常见误区',
    'next': '后续推荐',
    'example': '正例',
    'exercise': '练习',
    'resource': '补救资源',
}


@dataclass
class BuiltContext:
    learner_context: str
    knowledge_context: str
    retrieved_context: str
    teaching_strategy: str
    hint_instruction: str = ''
    system_prompt: str = ''
    user_prompt: str = ''
    source_index: list[dict[str, Any]] = field(default_factory=list)

    def to_debug_dict(self) -> dict[str, Any]:
        return {
            'learner_context': self.learner_context,
            'knowledge_context': self.knowledge_context,
            'retrieved_context': self.retrieved_context,
            'teaching_strategy': self.teaching_strategy,
            'hint_instruction': self.hint_instruction,
            'system_prompt': self.system_prompt,
            'user_prompt': self.user_prompt,
        }


class ContextBuilder:
    @staticmethod
    def build(
        *,
        query: str,
        learner: LearnerContext | None,
        graph: GraphContext,
        chunks: list[RetrievedChunk],
        strategy: TeachingStrategy,
        low_confidence: bool = False,
    ) -> BuiltContext:
        prompts = prompts_config()
        max_chars = int(retrieval_config().get('rerank', {}).get('max_context_chars', 3200))
        names = {n.concept_id: n.name for n in graph.nodes}
        names.update({item['concept_id']: item['name'] for item in GraphService.concepts_brief(graph.focus_ids)})

        learner_text = LearnerContextService.summarize(learner, graph.focus_ids, names) if learner else '无学习者画像。'
        knowledge_text = ContextBuilder._knowledge_context(graph, learner)
        retrieved_text, index = ContextBuilder._retrieved_context(chunks, max_chars, strategy)
        strategy_text = StrategyService.instructions(strategy)

        hint_instruction = ''
        if strategy.practice_mode and strategy.hint_policy:
            hint_instruction = prompts.get('hint_instruction_template', '').format(
                level=strategy.hint_policy.get('level'),
                max_level=strategy.hint_policy.get('max_level'),
                level_name=strategy.hint_policy.get('name', ''),
                level_instruction=strategy.hint_policy.get('instruction', ''),
            )

        if low_confidence:
            system_prompt = prompts.get('low_confidence_system', '').format(knowledge_context=knowledge_text or '（无）')
            user_prompt = query
        else:
            system_prompt = prompts.get('system', '').format(
                teaching_strategy=strategy_text or '（默认）',
                learner_context=learner_text,
                knowledge_context=knowledge_text or '（未识别到明确知识点）',
                hint_instruction=hint_instruction,
            )
            user_prompt = prompts.get('user', '').format(query=query, retrieved_context=retrieved_text or '（无检索材料）')
        return BuiltContext(
            learner_context=learner_text,
            knowledge_context=knowledge_text,
            retrieved_context=retrieved_text,
            teaching_strategy=strategy_text,
            hint_instruction=hint_instruction,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            source_index=index,
        )

    @staticmethod
    def _knowledge_context(graph: GraphContext, learner: LearnerContext | None) -> str:
        if not graph.nodes:
            return ''
        grouped: dict[str, list[str]] = {}
        for node in graph.nodes:
            label = node.name
            if node.role == 'misconception' and node.description:
                label = f'{node.name}——{truncate(node.description, 120)}'
            if learner and learner.available and node.concept_id in learner.mastery_status and node.node_type == 'concept':
                label += f'（{learner.mastery_status[node.concept_id]}）'
            grouped.setdefault(node.role, []).append(label)
        lines = []
        for role in ('focus', 'prerequisite', 'misconception', 'related', 'example', 'exercise', 'resource', 'next'):
            if role in grouped:
                lines.append(f'{_ROLE_LABEL[role]}：' + '；'.join(grouped[role][:5]))
        if graph.unmet_prerequisites:
            names = {n.concept_id: n.name for n in graph.nodes}
            lines.append('未掌握的前置：' + '、'.join(names.get(c, c) for c in graph.unmet_prerequisites[:4]))
        return '\n'.join(lines)

    @staticmethod
    def _retrieved_context(chunks: list[RetrievedChunk], max_chars: int, strategy: TeachingStrategy) -> tuple[str, list[dict[str, Any]]]:
        blocks: list[str] = []
        index: list[dict[str, Any]] = []
        used = 0
        allow_solution = not strategy.practice_mode or bool(strategy.hint_policy.get('allow_solution'))
        for chunk in chunks:
            if chunk.knowledge_type == 'solution' and not allow_solution:
                continue
            label = f'S{len(index) + 1}'
            header = f'[{label}] {chunk.title or chunk.document_title}（{chunk.knowledge_type}' + ('，教师审核' if chunk.teacher_verified else '') + '）'
            body = chunk.content.strip()
            budget = max_chars - used - len(header) - 4
            if budget <= 80:
                break
            if len(body) > budget:
                body = truncate(body, budget)
            block = f'{header}\n{body}'
            blocks.append(block)
            used += len(block) + 2
            index.append({'label': label, 'chunk_id': chunk.chunk_id, 'document_id': chunk.document_id})
        return '\n\n'.join(blocks), index
