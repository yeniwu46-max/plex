# -*- coding: utf-8 -*-
"""Knowledge Intelligence Layer：知识图谱节点与关系。

- KnowledgeConcept：多类型知识节点（concept/skill/example/exercise/misconception/resource/objective），
  concept 节点的 concept_id 与 knowledge_node_registry 的 kg_id 保持一致，保证全站 ID 统一。
- KnowledgeRelation：有向关系，允许多前置（一个节点多条 PREREQUISITE_OF 入边）。
"""
from __future__ import annotations

from app.utils.time import utc_now

from .base import db

NODE_TYPES = (
    'concept',
    'skill',
    'example',
    'exercise',
    'misconception',
    'resource',
    'objective',
)

RELATION_TYPES = (
    'PREREQUISITE_OF',
    'RELATED_TO',
    'PART_OF',
    'EXAMPLE_OF',
    'EXERCISE_FOR',
    'MISCONCEPTION_OF',
    'REMEDIATES',
    'NEXT_RECOMMENDED',
)


class KnowledgeConcept(db.Model):
    __tablename__ = 'knowledge_concepts'

    concept_id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(160), nullable=False, index=True)
    description = db.Column(db.Text, default='')
    course_id = db.Column(db.String(64), nullable=False, default='python-basics', index=True)
    chapter = db.Column(db.String(120), default='', index=True)
    node_type = db.Column(db.String(24), nullable=False, default='concept', index=True)
    difficulty = db.Column(db.Integer, nullable=False, default=2)  # 1-5
    importance = db.Column(db.Float, nullable=False, default=0.5)  # 0-1
    learning_objectives = db.Column(db.JSON)
    common_misconceptions = db.Column(db.JSON)
    tags = db.Column(db.JSON)
    mastery_threshold = db.Column(db.Float, nullable=False, default=0.7)
    embedding_text = db.Column(db.Text, default='')
    source = db.Column(db.String(32), nullable=False, default='registry')  # registry|document|manual|ai
    status = db.Column(db.String(16), nullable=False, default='active')  # active|archived
    kg_node_id = db.Column(db.String(48), index=True)  # 对应 knowledge_nodes.id（concept 类型）
    ref_type = db.Column(db.String(32))  # problem|learning_resource|document_chunk|...
    ref_id = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    def to_dict(self, expand: bool = False) -> dict:
        payload = {
            'concept_id': self.concept_id,
            'name': self.name,
            'description': self.description or '',
            'course': self.course_id,
            'course_id': self.course_id,
            'chapter': self.chapter or '',
            'node_type': self.node_type,
            'difficulty': self.difficulty,
            'importance': self.importance,
            'learning_objectives': list(self.learning_objectives or []),
            'common_misconceptions': list(self.common_misconceptions or []),
            'tags': list(self.tags or []),
            'mastery_threshold': self.mastery_threshold,
            'embedding_text': self.embedding_text or '',
            'source': self.source,
            'status': self.status,
            'kg_node_id': self.kg_node_id,
            'ref_type': self.ref_type,
            'ref_id': self.ref_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if expand:
            payload.update(self.relation_summary())
        return payload

    def relation_summary(self) -> dict:
        """从关系表派生 prerequisites / related_concepts / example_ids 等字段。"""
        incoming = KnowledgeRelation.query.filter_by(target_id=self.concept_id).all()
        outgoing = KnowledgeRelation.query.filter_by(source_id=self.concept_id).all()
        summary = {
            'prerequisites': [],
            'related_concepts': [],
            'example_ids': [],
            'exercise_ids': [],
            'misconception_ids': [],
            'resource_ids': [],
            'part_of': [],
            'next_recommended': [],
            'remediates': [],
        }
        for rel in incoming:
            if rel.relation_type == 'PREREQUISITE_OF':
                summary['prerequisites'].append(rel.source_id)
            elif rel.relation_type == 'EXAMPLE_OF':
                summary['example_ids'].append(rel.source_id)
            elif rel.relation_type == 'EXERCISE_FOR':
                summary['exercise_ids'].append(rel.source_id)
            elif rel.relation_type == 'MISCONCEPTION_OF':
                summary['misconception_ids'].append(rel.source_id)
            elif rel.relation_type == 'RELATED_TO':
                summary['related_concepts'].append(rel.source_id)
            elif rel.relation_type == 'REMEDIATES':
                summary['resource_ids'].append(rel.source_id)
        for rel in outgoing:
            if rel.relation_type == 'RELATED_TO':
                summary['related_concepts'].append(rel.target_id)
            elif rel.relation_type == 'PART_OF':
                summary['part_of'].append(rel.target_id)
            elif rel.relation_type == 'NEXT_RECOMMENDED':
                summary['next_recommended'].append(rel.target_id)
            elif rel.relation_type == 'REMEDIATES':
                summary['remediates'].append(rel.target_id)
        for key, values in summary.items():
            summary[key] = sorted(set(values))
        return summary


class KnowledgeRelation(db.Model):
    __tablename__ = 'knowledge_relations'

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(
        db.String(64), db.ForeignKey('knowledge_concepts.concept_id', ondelete='CASCADE'), nullable=False, index=True
    )
    target_id = db.Column(
        db.String(64), db.ForeignKey('knowledge_concepts.concept_id', ondelete='CASCADE'), nullable=False, index=True
    )
    relation_type = db.Column(db.String(24), nullable=False, index=True)
    weight = db.Column(db.Float, nullable=False, default=1.0)
    source = db.Column(db.String(32), nullable=False, default='registry')  # registry|document|manual|ai
    teacher_verified = db.Column(db.Boolean, nullable=False, default=False)
    verified_by = db.Column(db.Integer)
    note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('source_id', 'target_id', 'relation_type', name='uq_knowledge_relation'),
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'source': self.source_id,
            'target': self.target_id,
            'relation_type': self.relation_type,
            'weight': self.weight,
            'origin': self.source,
            'teacher_verified': bool(self.teacher_verified),
            'verified_by': self.verified_by,
            'note': self.note,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
