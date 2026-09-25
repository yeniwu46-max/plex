# -*- coding: utf-8 -*-
"""知识图谱数据层：节点/关系 CRUD、种子导入、k-hop 受控扩展。

图谱主存储为 MySQL（knowledge_concepts / knowledge_relations）；节点 id 与 knowledge_node_registry 的 kg_id 对齐，
因此试炼、错题、学习路径中的 knowledge_key 可经 ``resolve_node_id`` 直接映射到图谱概念。
"""
from __future__ import annotations

import re
import threading
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Iterable

from app.data.course_knowledge import KNOWLEDGE_ROOT, DOMAIN_SOURCE_FILES, knowledge_section
from app.data.kg_topology import KG_EDGES
from app.data.knowledge_node_registry import (
    KNOWLEDGE_DOMAINS,
    KNOWLEDGE_NODE_REGISTRY,
    get_entry,
    nodes_for_domain,
    resolve_node_id,
)
from app.models import KnowledgeConcept, KnowledgeRelation, Problem, db
from app.models.knowledge_graph import NODE_TYPES, RELATION_TYPES

from .schemas import GraphContext, GraphNode, LearnerContext
from .settings import retrieval_config

_EDGE_TYPE_MAP = {
    'prerequisite': 'PREREQUISITE_OF',
    'related': 'RELATED_TO',
    'path': 'NEXT_RECOMMENDED',
    'belongs_to': 'PART_OF',
    'remediation': 'REMEDIATES',
}

_DOMAIN_NODE_PREFIX = 'domain:'
_MISCONCEPTION_PREFIX = 'mis:'
_EXAMPLE_PREFIX = 'ex:'
_EXERCISE_PREFIX = 'exr:'
_PROBLEM_PREFIX = 'problem:'

_ID_IN_BACKTICKS = re.compile(r'`([a-z][a-z0-9-]+)`')


class GraphValidationError(ValueError):
    pass


@dataclass(frozen=True)
class _NodeSnapshot:
    """缓存中只保存纯数据快照，避免跨请求持有 ORM 实例（DetachedInstanceError）。"""

    concept_id: str
    name: str
    node_type: str
    chapter: str
    difficulty: int
    description: str
    mastery_threshold: float

    @classmethod
    def from_row(cls, row: KnowledgeConcept) -> '_NodeSnapshot':
        return cls(
            concept_id=row.concept_id,
            name=row.name or '',
            node_type=row.node_type or 'concept',
            chapter=row.chapter or '',
            difficulty=int(row.difficulty or 2),
            description=row.description or '',
            mastery_threshold=float(row.mastery_threshold or 0.7),
        )


class _AdjacencyCache:
    """关系表的内存邻接缓存；任何写操作后失效。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._data: dict[str, Any] | None = None

    def invalidate(self) -> None:
        with self._lock:
            self._data = None

    def get(self) -> dict[str, Any]:
        with self._lock:
            if self._data is None:
                self._data = self._build()
            return self._data

    @staticmethod
    def _build() -> dict[str, Any]:
        outgoing: dict[str, list[dict]] = defaultdict(list)
        incoming: dict[str, list[dict]] = defaultdict(list)
        for rel in KnowledgeRelation.query.all():
            edge = {
                'source': rel.source_id,
                'target': rel.target_id,
                'type': rel.relation_type,
                'weight': float(rel.weight or 1.0),
                'teacher_verified': bool(rel.teacher_verified),
            }
            outgoing[rel.source_id].append(edge)
            incoming[rel.target_id].append(edge)
        nodes = {
            row.concept_id: _NodeSnapshot.from_row(row)
            for row in KnowledgeConcept.query.filter(KnowledgeConcept.status == 'active').all()
        }
        return {'out': outgoing, 'in': incoming, 'nodes': nodes}


_CACHE = _AdjacencyCache()


class GraphService:
    # ------------------------------------------------------------------ read
    @staticmethod
    def get_concept(concept_id: str) -> KnowledgeConcept | None:
        return db.session.get(KnowledgeConcept, concept_id)

    @staticmethod
    def concept_exists(concept_id: str) -> bool:
        return GraphService.get_concept(concept_id) is not None

    @staticmethod
    def list_concepts(
        *,
        course_id: str | None = None,
        node_types: Iterable[str] | None = None,
        chapter: str | None = None,
        keyword: str | None = None,
        status: str = 'active',
    ) -> list[KnowledgeConcept]:
        query = KnowledgeConcept.query
        if status:
            query = query.filter(KnowledgeConcept.status == status)
        if course_id:
            query = query.filter(KnowledgeConcept.course_id == course_id)
        if node_types:
            query = query.filter(KnowledgeConcept.node_type.in_(list(node_types)))
        if chapter:
            query = query.filter(KnowledgeConcept.chapter == chapter)
        if keyword:
            like = f'%{keyword.strip()}%'
            query = query.filter(db.or_(KnowledgeConcept.name.ilike(like), KnowledgeConcept.description.ilike(like)))
        return query.order_by(KnowledgeConcept.chapter, KnowledgeConcept.concept_id).all()

    @staticmethod
    def concept_lexicon() -> list[dict[str, Any]]:
        """供 Query Understanding 使用的概念词典（仅 concept/skill 类型）。"""
        rows = GraphService.list_concepts(node_types=('concept', 'skill'))
        lexicon = []
        for row in rows:
            entry = get_entry(row.concept_id)
            aliases = set(row.tags or [])
            aliases.add(row.name)
            if entry:
                aliases.update(entry.scope_names)
                aliases.update(k for k in entry.knowledge_keys if len(k) > 2)
            lexicon.append(
                {
                    'concept_id': row.concept_id,
                    'name': row.name,
                    'aliases': sorted(a for a in aliases if a),
                    'description': row.description or '',
                    'difficulty': row.difficulty,
                    'chapter': row.chapter,
                }
            )
        return lexicon

    @staticmethod
    def get_graph(
        *,
        course_id: str | None = None,
        node_types: Iterable[str] | None = None,
        relation_types: Iterable[str] | None = None,
        include_problem_nodes: bool = False,
    ) -> dict[str, Any]:
        types = list(node_types) if node_types else ['concept', 'skill', 'misconception', 'example', 'exercise', 'objective', 'resource']
        rows = GraphService.list_concepts(course_id=course_id, node_types=types)
        if not include_problem_nodes:
            rows = [r for r in rows if not r.concept_id.startswith(_PROBLEM_PREFIX)]
        node_ids = {r.concept_id for r in rows}
        rel_query = KnowledgeRelation.query
        if relation_types:
            rel_query = rel_query.filter(KnowledgeRelation.relation_type.in_(list(relation_types)))
        edges = [
            rel.to_dict()
            for rel in rel_query.all()
            if rel.source_id in node_ids and rel.target_id in node_ids
        ]
        counts = defaultdict(int)
        for r in rows:
            counts[r.node_type] += 1
        return {
            'nodes': [r.to_dict() for r in rows],
            'edges': edges,
            'stats': {
                'node_count': len(rows),
                'edge_count': len(edges),
                'by_type': dict(counts),
            },
            'chapters': [
                {'key': d.key, 'title': d.title, 'order': d.order, 'description': d.description}
                for d in KNOWLEDGE_DOMAINS
            ],
        }

    @staticmethod
    def relations_of(concept_id: str) -> dict[str, list[dict]]:
        adjacency = _CACHE.get()
        return {
            'outgoing': list(adjacency['out'].get(concept_id, [])),
            'incoming': list(adjacency['in'].get(concept_id, [])),
        }

    @staticmethod
    def prerequisites_of(concept_id: str) -> list[str]:
        adjacency = _CACHE.get()
        return sorted({e['source'] for e in adjacency['in'].get(concept_id, []) if e['type'] == 'PREREQUISITE_OF'})

    @staticmethod
    def concept_detail(concept_id: str) -> dict[str, Any] | None:
        row = GraphService.get_concept(concept_id)
        if not row:
            return None
        payload = row.to_dict(expand=True)
        adjacency = _CACHE.get()
        nodes = adjacency['nodes']

        def describe(ids: list[str]) -> list[dict]:
            out = []
            for cid in ids:
                node = nodes.get(cid)
                if node:
                    out.append({'concept_id': cid, 'name': node.name, 'node_type': node.node_type, 'difficulty': node.difficulty})
            return out

        payload['prerequisite_nodes'] = describe(payload['prerequisites'])
        payload['related_nodes'] = describe(payload['related_concepts'])
        payload['misconception_nodes'] = [
            {**item, 'description': nodes[item['concept_id']].description}
            for item in describe(payload['misconception_ids'])
        ]
        payload['example_nodes'] = describe(payload['example_ids'])
        payload['exercise_nodes'] = describe(payload['exercise_ids'])
        payload['next_nodes'] = describe(payload['next_recommended'])
        return payload

    # ------------------------------------------------------------------ write
    @staticmethod
    def upsert_concept(concept_id: str, **fields: Any) -> KnowledgeConcept:
        if not concept_id or len(concept_id) > 64:
            raise GraphValidationError('concept_id 非法')
        node_type = fields.get('node_type', 'concept')
        if node_type not in NODE_TYPES:
            raise GraphValidationError(f'未知节点类型 {node_type}')
        difficulty = int(fields.get('difficulty') or 2)
        if not 1 <= difficulty <= 5:
            raise GraphValidationError('difficulty 必须在 1-5')
        row = db.session.get(KnowledgeConcept, concept_id)
        created = row is None
        if created:
            row = KnowledgeConcept(concept_id=concept_id)
            db.session.add(row)
        for key, value in fields.items():
            if hasattr(row, key) and key not in {'concept_id', 'created_at'}:
                setattr(row, key, value)
        row.difficulty = difficulty
        if not row.embedding_text:
            row.embedding_text = GraphService._default_embedding_text(row)
        _CACHE.invalidate()
        return row

    @staticmethod
    def add_relation(
        source_id: str,
        target_id: str,
        relation_type: str,
        *,
        weight: float = 1.0,
        source: str = 'manual',
        teacher_verified: bool = False,
        verified_by: int | None = None,
        note: str | None = None,
        commit: bool = False,
    ) -> KnowledgeRelation:
        if relation_type not in RELATION_TYPES:
            raise GraphValidationError(f'未知关系类型 {relation_type}')
        if source_id == target_id:
            raise GraphValidationError('不允许自环关系')
        if not GraphService.concept_exists(source_id) or not GraphService.concept_exists(target_id):
            raise GraphValidationError('关系两端节点必须已存在')
        if relation_type == 'PREREQUISITE_OF' and GraphService._would_create_cycle(source_id, target_id):
            raise GraphValidationError('该前置关系会形成环')
        row = KnowledgeRelation.query.filter_by(
            source_id=source_id, target_id=target_id, relation_type=relation_type
        ).first()
        if row is None:
            row = KnowledgeRelation(source_id=source_id, target_id=target_id, relation_type=relation_type)
            db.session.add(row)
        row.weight = float(weight)
        row.source = source
        if teacher_verified:
            row.teacher_verified = True
            row.verified_by = verified_by
        if note is not None:
            row.note = note[:255]
        _CACHE.invalidate()
        if commit:
            db.session.commit()
        return row

    @staticmethod
    def remove_relation(relation_id: int, *, commit: bool = True) -> bool:
        row = db.session.get(KnowledgeRelation, relation_id)
        if not row:
            return False
        db.session.delete(row)
        _CACHE.invalidate()
        if commit:
            db.session.commit()
        return True

    @staticmethod
    def verify_relation(relation_id: int, user_id: int, verified: bool = True, *, commit: bool = True) -> KnowledgeRelation | None:
        row = db.session.get(KnowledgeRelation, relation_id)
        if not row:
            return None
        row.teacher_verified = bool(verified)
        row.verified_by = user_id if verified else None
        _CACHE.invalidate()
        if commit:
            db.session.commit()
        return row

    @staticmethod
    def update_concept(concept_id: str, **fields: Any) -> KnowledgeConcept | None:
        """教师/管理员修正节点的可编辑字段（不允许改 concept_id / node_type）。"""
        row = GraphService.get_concept(concept_id)
        if not row:
            return None
        allowed = {'name', 'description', 'chapter', 'difficulty', 'importance', 'learning_objectives',
                   'common_misconceptions', 'tags', 'mastery_threshold', 'embedding_text', 'status'}
        clean = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if 'difficulty' not in clean:
            clean['difficulty'] = row.difficulty
        GraphService.upsert_concept(concept_id, node_type=row.node_type, **clean)
        db.session.commit()
        return row

    @staticmethod
    def invalidate_cache() -> None:
        _CACHE.invalidate()

    @staticmethod
    def _would_create_cycle(source_id: str, target_id: str) -> bool:
        """新增 source→target 前置边后，若从 target 能沿前置边到达 source，则成环。"""
        adjacency = _CACHE.get()
        seen = {target_id}
        queue = deque([target_id])
        while queue:
            current = queue.popleft()
            for edge in adjacency['out'].get(current, []):
                if edge['type'] != 'PREREQUISITE_OF':
                    continue
                nxt = edge['target']
                if nxt == source_id:
                    return True
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return False

    @staticmethod
    def _default_embedding_text(row: KnowledgeConcept) -> str:
        parts = [row.name or '', row.description or '']
        parts.extend(row.tags or [])
        parts.extend(row.learning_objectives or [])
        return '\n'.join(p for p in parts if p)

    # ------------------------------------------------------------------ seed
    @staticmethod
    def seed_from_registry(*, include_problems: bool = True, force: bool = False) -> dict[str, int]:
        """从知识节点注册表 + 课程知识库 md + 题库生成初始图谱（幂等）。"""
        stats = defaultdict(int)
        existing = {row.concept_id for row in KnowledgeConcept.query.all()}
        if existing and not force and len(existing) >= len(KNOWLEDGE_NODE_REGISTRY):
            already = KnowledgeConcept.query.filter(KnowledgeConcept.node_type == 'concept').count()
            if already >= len(KNOWLEDGE_NODE_REGISTRY):
                return {'skipped': already}

        # 1) 学域 → LearningObjective 节点
        for domain in KNOWLEDGE_DOMAINS:
            GraphService.upsert_concept(
                f'{_DOMAIN_NODE_PREFIX}{domain.key}',
                name=domain.title,
                description=domain.description,
                chapter=domain.title,
                node_type='objective',
                difficulty=1,
                importance=0.9,
                learning_objectives=[domain.description, domain.focus],
                tags=[domain.key, domain.focus],
                source='registry',
                embedding_text=f'{domain.title}\n{domain.description}\n{domain.focus}',
            )
            stats['objectives'] += 1

        # 2) 注册表 → Concept 节点
        for entry in KNOWLEDGE_NODE_REGISTRY:
            domain = next((d for d in KNOWLEDGE_DOMAINS if d.key == entry.domain_key), None)
            section = knowledge_section(entry.kg_id)
            difficulty = max(1, min(5, int(entry.default_difficulty or 1) + (1 if entry.level == 'advanced' else 0)))
            misconceptions = _split_items(section.get('common_mistakes') or '')
            GraphService.upsert_concept(
                entry.kg_id,
                name=entry.label,
                description=(section.get('concept') or entry.summary or '')[:2000],
                chapter=domain.title if domain else entry.domain_key,
                node_type='concept',
                difficulty=difficulty,
                importance=0.8 if entry.level == 'basic' else 0.6,
                learning_objectives=[entry.summary] if entry.summary else [],
                common_misconceptions=misconceptions,
                tags=sorted(set(entry.scope_names) | {entry.domain_key}),
                source='registry',
                kg_node_id=entry.kg_id,
                embedding_text='\n'.join(
                    p for p in [entry.label, ' '.join(entry.scope_names), entry.summary, section.get('concept') or ''] if p
                ),
            )
            stats['concepts'] += 1
            GraphService.add_relation(entry.kg_id, f'{_DOMAIN_NODE_PREFIX}{entry.domain_key}', 'PART_OF', source='registry')
            stats['relations'] += 1

            # 2a) 课程知识库派生：迷思 / 正例 / 练习节点
            if misconceptions:
                GraphService.upsert_concept(
                    f'{_MISCONCEPTION_PREFIX}{entry.kg_id}',
                    name=f'{entry.label} · 常见误区',
                    description='；'.join(misconceptions)[:2000],
                    chapter=domain.title if domain else entry.domain_key,
                    node_type='misconception',
                    difficulty=difficulty,
                    importance=0.6,
                    tags=[entry.kg_id, 'misconception'],
                    source='document',
                    ref_type='course_knowledge',
                    ref_id=section.get('document_id'),
                    embedding_text=f'{entry.label} 常见错误：' + '；'.join(misconceptions),
                )
                GraphService.add_relation(f'{_MISCONCEPTION_PREFIX}{entry.kg_id}', entry.kg_id, 'MISCONCEPTION_OF', source='document')
                stats['misconceptions'] += 1
            if section.get('good_example'):
                GraphService.upsert_concept(
                    f'{_EXAMPLE_PREFIX}{entry.kg_id}',
                    name=f'{entry.label} · 正例',
                    description=section['good_example'][:2000],
                    chapter=domain.title if domain else entry.domain_key,
                    node_type='example',
                    difficulty=difficulty,
                    importance=0.5,
                    tags=[entry.kg_id, 'example'],
                    source='document',
                    ref_type='course_knowledge',
                    ref_id=section.get('document_id'),
                    embedding_text=f'{entry.label} 正例：{section["good_example"]}',
                )
                GraphService.add_relation(f'{_EXAMPLE_PREFIX}{entry.kg_id}', entry.kg_id, 'EXAMPLE_OF', source='document')
                stats['examples'] += 1
            for suffix, key, label, extra_difficulty in (
                ('base', 'base_question', '基础题', 0),
                ('adv', 'advanced_question', '进阶题', 1),
            ):
                text = section.get(key)
                if not text:
                    continue
                GraphService.upsert_concept(
                    f'{_EXERCISE_PREFIX}{entry.kg_id}:{suffix}',
                    name=f'{entry.label} · {label}',
                    description=text[:2000],
                    chapter=domain.title if domain else entry.domain_key,
                    node_type='exercise',
                    difficulty=max(1, min(5, difficulty + extra_difficulty)),
                    importance=0.5,
                    tags=[entry.kg_id, 'exercise', suffix],
                    source='document',
                    ref_type='course_knowledge',
                    ref_id=section.get('document_id'),
                    embedding_text=f'{entry.label} {label}：{text}',
                )
                GraphService.add_relation(f'{_EXERCISE_PREFIX}{entry.kg_id}:{suffix}', entry.kg_id, 'EXERCISE_FOR', source='document')
                stats['exercises'] += 1

        db.session.flush()

        # 3) 静态拓扑边 → 关系
        for edge in KG_EDGES:
            rel_type = _EDGE_TYPE_MAP.get(edge['type'])
            if not rel_type or rel_type == 'PART_OF':
                continue
            try:
                GraphService.add_relation(edge['source'], edge['target'], rel_type, source='registry')
                stats['relations'] += 1
            except GraphValidationError:
                stats['skipped_edges'] += 1

        # 4) 课程知识库 md 中显式声明的前置/后续（允许多前置）
        for domain_key, filename in DOMAIN_SOURCE_FILES.items():
            path = KNOWLEDGE_ROOT / filename
            if not path.is_file():
                continue
            for concept_id, prereqs, nexts in _parse_relation_lines(path.read_text(encoding='utf-8')):
                for pre in prereqs:
                    if pre != concept_id and GraphService.concept_exists(pre):
                        try:
                            GraphService.add_relation(pre, concept_id, 'PREREQUISITE_OF', source='document')
                            stats['relations'] += 1
                        except GraphValidationError:
                            stats['skipped_edges'] += 1
                for nxt in nexts:
                    if nxt != concept_id and GraphService.concept_exists(nxt):
                        try:
                            GraphService.add_relation(concept_id, nxt, 'NEXT_RECOMMENDED', source='document')
                            stats['relations'] += 1
                        except GraphValidationError:
                            stats['skipped_edges'] += 1

        # 5) 题库 → Exercise 节点
        if include_problems:
            problems = Problem.query.filter(Problem.is_active.is_(True), Problem.kg_node_id.isnot(None)).all()
            for problem in problems:
                if not GraphService.concept_exists(problem.kg_node_id):
                    continue
                if problem.star_difficulty:
                    difficulty = max(1, min(5, int(problem.star_difficulty)))
                else:
                    difficulty = max(1, min(5, int((problem.difficulty or 40) / 25) + 1))
                GraphService.upsert_concept(
                    f'{_PROBLEM_PREFIX}{problem.id}',
                    name=(problem.title_cn or f'题目 {problem.problem_no}')[:160],
                    description=(problem.description_cn or '')[:2000],
                    chapter=next((d.title for d in KNOWLEDGE_DOMAINS if d.key == problem.domain_key), problem.domain_key or ''),
                    node_type='exercise',
                    difficulty=difficulty,
                    importance=0.4,
                    tags=[problem.kg_node_id, problem.question_type or 'coding', 'problem_bank'],
                    source='registry',
                    ref_type='problem',
                    ref_id=str(problem.id),
                    embedding_text=f'{problem.title_cn}\n{(problem.description_cn or "")[:600]}',
                )
                GraphService.add_relation(f'{_PROBLEM_PREFIX}{problem.id}', problem.kg_node_id, 'EXERCISE_FOR', source='registry')
                stats['problem_exercises'] += 1

        db.session.commit()
        _CACHE.invalidate()
        return dict(stats)

    # ------------------------------------------------------------------ expansion
    @staticmethod
    def resolve_concept_ids(keys: Iterable[str | None]) -> list[str]:
        """knowledge_key / kg_id 混合输入 → 图谱 concept_id 列表（去重、保序）。"""
        adjacency = _CACHE.get()
        out: list[str] = []
        for key in keys:
            if not key:
                continue
            cid = key if key in adjacency['nodes'] else resolve_node_id(key)
            if not cid:
                cid = GraphService._resolve_by_name(str(key), adjacency['nodes'])
            if cid and cid in adjacency['nodes'] and cid not in out:
                out.append(cid)
        return out

    @staticmethod
    def _resolve_by_name(key: str, nodes: dict[str, '_NodeSnapshot']) -> str | None:
        """按节点名 / 注册表 scope_names 精确匹配（忽略大小写与空格），只匹配 concept/skill。"""
        needle = key.strip().lower().replace(' ', '')
        if len(needle) < 2:
            return None
        for cid, node in nodes.items():
            if node.node_type not in ('concept', 'skill'):
                continue
            if node.name.lower().replace(' ', '') == needle:
                return cid
            entry = get_entry(cid)
            if entry and any(s.lower().replace(' ', '') == needle for s in entry.scope_names):
                return cid
        return None

    @staticmethod
    def expand(
        focus_ids: list[str],
        learner: LearnerContext | None = None,
        *,
        include_examples: bool = True,
    ) -> GraphContext:
        """围绕焦点概念做受控扩展：前置(1-hop，薄弱时 2-hop) / 相关 / 迷思 / 后续 / 正例 / 练习。"""
        cfg = retrieval_config().get('graph', {})
        role_weights = cfg.get('role_weights', {})
        max_nodes = int(cfg.get('max_expanded_nodes', 12))
        adjacency = _CACHE.get()
        nodes_by_id: dict[str, _NodeSnapshot] = adjacency['nodes']
        focus_ids = [cid for cid in focus_ids if cid in nodes_by_id]
        ctx = GraphContext(focus_ids=list(focus_ids))
        if not focus_ids:
            return ctx

        mastery = learner.mastery if learner else {}
        threshold_low = 0.4

        def add_node(cid: str, role: str, hop: int, weight: float) -> None:
            if any(n.concept_id == cid for n in ctx.nodes):
                return
            row = nodes_by_id.get(cid)
            if not row:
                return
            ctx.nodes.append(
                GraphNode(
                    concept_id=cid,
                    name=row.name,
                    node_type=row.node_type,
                    role=role,
                    hop=hop,
                    weight=round(weight, 3),
                    mastery=mastery.get(cid),
                    description=(row.description or '')[:200],
                )
            )

        def add_edge(edge: dict) -> None:
            if edge not in ctx.edges:
                ctx.edges.append(edge)

        for cid in focus_ids:
            add_node(cid, 'focus', 0, role_weights.get('focus', 1.0))

        # 前置：BFS，薄弱时多走一跳
        for cid in focus_ids:
            focus_mastery = mastery.get(cid, 0.0)
            hops = int(cfg.get('prerequisite_hops_when_weak', 2)) if focus_mastery < threshold_low else int(cfg.get('prerequisite_hops', 1))
            queue = deque([(cid, 0)])
            seen = {cid}
            while queue:
                current, depth = queue.popleft()
                if depth >= hops:
                    continue
                for edge in adjacency['in'].get(current, []):
                    if edge['type'] != 'PREREQUISITE_OF':
                        continue
                    pre = edge['source']
                    if pre in seen:
                        continue
                    seen.add(pre)
                    decay = role_weights.get('prerequisite', 0.8) * (0.7 ** depth)
                    add_node(pre, 'prerequisite', depth + 1, decay)
                    add_edge(edge)
                    pre_row = nodes_by_id.get(pre)
                    if (
                        learner is not None
                        and learner.available
                        and pre_row
                        and mastery.get(pre, 0.0) < (pre_row.mastery_threshold or 0.7)
                        and pre not in ctx.unmet_prerequisites
                    ):
                        ctx.unmet_prerequisites.append(pre)
                    queue.append((pre, depth + 1))

        # 迷思 / 正例 / 练习 / 相关 / 后续（1-hop）
        for cid in focus_ids:
            for edge in adjacency['in'].get(cid, []):
                if edge['type'] == 'MISCONCEPTION_OF':
                    add_node(edge['source'], 'misconception', 1, role_weights.get('misconception', 0.75))
                    add_edge(edge)
                    if edge['source'] not in ctx.misconceptions:
                        ctx.misconceptions.append(edge['source'])
                elif edge['type'] == 'EXAMPLE_OF' and include_examples:
                    add_node(edge['source'], 'example', 1, role_weights.get('example', 0.6))
                    add_edge(edge)
                elif edge['type'] == 'EXERCISE_FOR' and include_examples and not edge['source'].startswith(_PROBLEM_PREFIX):
                    add_node(edge['source'], 'exercise', 1, role_weights.get('exercise', 0.5))
                    add_edge(edge)
                elif edge['type'] == 'RELATED_TO':
                    add_node(edge['source'], 'related', 1, role_weights.get('related', 0.55))
                    add_edge(edge)
                elif edge['type'] == 'REMEDIATES':
                    add_node(edge['source'], 'resource', 1, role_weights.get('resource', 0.5))
                    add_edge(edge)
            for edge in adjacency['out'].get(cid, []):
                if edge['type'] == 'RELATED_TO':
                    add_node(edge['target'], 'related', 1, role_weights.get('related', 0.55))
                    add_edge(edge)
                elif edge['type'] == 'NEXT_RECOMMENDED':
                    add_node(edge['target'], 'next', 1, role_weights.get('next', 0.45))
                    add_edge(edge)
                    if edge['target'] not in ctx.next_recommended:
                        ctx.next_recommended.append(edge['target'])

        # 限制规模：焦点与前置优先，其余按权重截断
        if len(ctx.nodes) > max_nodes:
            priority = {'focus': 0, 'prerequisite': 1, 'misconception': 2, 'example': 3, 'related': 4, 'exercise': 5, 'next': 6, 'resource': 7}
            ctx.nodes.sort(key=lambda n: (priority.get(n.role, 9), -n.weight))
            keep = ctx.nodes[:max_nodes]
            keep_ids = {n.concept_id for n in keep}
            ctx.nodes = keep
            ctx.edges = [e for e in ctx.edges if e['source'] in keep_ids and e['target'] in keep_ids]
            ctx.misconceptions = [m for m in ctx.misconceptions if m in keep_ids]
            ctx.next_recommended = [n for n in ctx.next_recommended if n in keep_ids]
        return ctx

    @staticmethod
    def concepts_brief(concept_ids: Iterable[str]) -> list[dict[str, Any]]:
        adjacency = _CACHE.get()
        out = []
        for cid in concept_ids:
            row = adjacency['nodes'].get(cid)
            if row:
                out.append(
                    {
                        'concept_id': cid,
                        'name': row.name,
                        'node_type': row.node_type,
                        'chapter': row.chapter,
                        'difficulty': row.difficulty,
                    }
                )
        return out


# ---------------------------------------------------------------------- helpers

def _split_items(text: str) -> list[str]:
    text = (text or '').strip()
    if not text:
        return []
    parts = [p.strip().rstrip('。') for p in re.split(r'[；;]\s*', text) if p and p.strip()]
    if len(parts) == 1 and '、' in parts[0] and '`' not in parts[0]:
        candidates = [p.strip().rstrip('。') for p in parts[0].split('、') if p.strip()]
        # 保守：若拆得过碎（平均 < 6 字），退回整句
        if candidates and sum(len(i) for i in candidates) / len(candidates) >= 6:
            parts = candidates
    return parts[:8]


def _parse_relation_lines(markdown: str) -> list[tuple[str, list[str], list[str]]]:
    """解析每个 ``## N.`` 小节中 ``- 前置知识点：`` / ``- 后续知识点：`` 声明的节点 id。"""
    results: list[tuple[str, list[str], list[str]]] = []
    headings = list(re.finditer(r'^##\s+\d+\.\s+.+$', markdown, flags=re.MULTILINE))
    for index, heading in enumerate(headings):
        start = heading.start()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(markdown)
        body = markdown[start:end]
        doc_match = re.search(r'`document_id:\s*([^`\s]+)\s*`', body)
        if not doc_match:
            continue
        document_id = doc_match.group(1)
        entry = next((e for e in KNOWLEDGE_NODE_REGISTRY if e.document_id == document_id), None)
        if not entry:
            continue
        pre_match = re.search(r'^-\s*前置知识点：(.+)$', body, flags=re.MULTILINE)
        next_match = re.search(r'^-\s*后续知识点：(.+)$', body, flags=re.MULTILINE)
        prereqs = _ID_IN_BACKTICKS.findall(pre_match.group(1)) if pre_match else []
        nexts = _ID_IN_BACKTICKS.findall(next_match.group(1)) if next_match else []
        results.append((entry.kg_id, prereqs, nexts))
    return results
