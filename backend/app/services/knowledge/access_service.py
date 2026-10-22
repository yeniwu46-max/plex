"""Authoritative document access, shared by retrieval and source reads.

Role/class/scope never come from a prompt, vector metadata or caller-provided role.
Indexing status alone does not grant student access.
"""
from __future__ import annotations

from app.models import Class, KnowledgeChunk, KnowledgeDocument, User, db
from .settings import retrieval_config


class KnowledgeAccessService:
    STUDENT_EXCLUDED_TYPES = frozenset({'teacher_note', 'solution'})

    @staticmethod
    def actor(user_id, session=None):
        return (session or db.session).get(User, user_id) if user_id is not None else None

    @staticmethod
    def role(user):
        return user.role.name if user and user.role else 'student'

    @classmethod
    def documents(cls, user_id, *, retrieval=False, course_id=None, session=None):
        session = session or db.session
        user = cls.actor(user_id, session)
        role = cls.role(user)
        query = session.query(KnowledgeDocument)
        if user_id is not None and (not user or user.status != 'active'):
            return query.filter(db.false())
        if role != 'admin':
            public = KnowledgeDocument.visibility == 'public'
            if role == 'teacher':
                classes = db.select(Class.id).where(Class.teacher_id == user.id)
                scope = db.or_(public, KnowledgeDocument.uploaded_by == user.id,
                    db.and_(KnowledgeDocument.visibility == 'class', KnowledgeDocument.class_id.in_(classes)))
            else:
                scope = public
                if user and user.class_id:
                    scope = db.or_(scope, db.and_(KnowledgeDocument.visibility == 'class', KnowledgeDocument.class_id == user.class_id))
                query = query.filter(KnowledgeDocument.published.is_(True))
                # There is currently one enrolled course. Adding a course requires a server-side enrollment model.
                query = query.filter(KnowledgeDocument.course_id == retrieval_config().get('course_id', 'python-basics'))
            query = query.filter(scope)
        if retrieval:
            query = query.filter(KnowledgeDocument.status == 'READY')
        if course_id:
            query = query.filter(KnowledgeDocument.course_id == course_id)
        return query

    @classmethod
    def document(cls, user_id, document_id, *, edit=False):
        if edit:
            user = cls.actor(user_id)
            if not user or user.status != 'active' or cls.role(user) not in {'admin', 'teacher'}:
                return None
            query = KnowledgeDocument.query.filter_by(id=document_id)
            if cls.role(user) != 'admin':
                query = query.filter(KnowledgeDocument.uploaded_by == user_id)
            return query.first()
        return cls.documents(user_id).filter(KnowledgeDocument.id == document_id).first()

    @classmethod
    def update(cls, user_id, document_id, body):
        doc = cls.document(user_id, document_id, edit=True)
        if not doc:
            return None
        visibility = body.get('visibility')
        published = body.get('published')
        class_id = body.get('class_id')
        if visibility not in {'private', 'class', 'public'} or type(published) is not bool:
            raise ValueError('请选择有效的可见范围与发布状态')
        role = cls.role(cls.actor(user_id))
        if visibility == 'public' and role != 'admin':
            raise ValueError('全课程公开需由管理员设置；可发布给本人任教班级')
        if visibility == 'private' and published:
            raise ValueError('私有文档不能向学生发布')
        if visibility == 'class':
            if type(class_id) is not int:
                raise ValueError('请选择发布班级')
            classroom = db.session.get(Class, class_id)
            if not classroom or (role != 'admin' and classroom.teacher_id != user_id):
                raise ValueError('不能发布到未任教的班级')
        elif class_id is not None:
            raise ValueError('仅班级范围可以指定班级')
        doc.visibility, doc.class_id, doc.published = visibility, class_id, published
        db.session.commit()
        return doc

    @classmethod
    def chunks(cls, user_id, *, course_id=None, session=None):
        session = session or db.session
        ids = cls.documents(user_id, retrieval=True, course_id=course_id, session=session).with_entities(KnowledgeDocument.id)
        query = session.query(KnowledgeChunk).join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id).filter(
            KnowledgeDocument.id.in_(ids), KnowledgeChunk.status == 'active',
            KnowledgeChunk.version == KnowledgeDocument.version,
            KnowledgeChunk.course_id == KnowledgeDocument.course_id,
        )
        if cls.role(cls.actor(user_id, session)) not in {'admin', 'teacher'}:
            query = query.filter(KnowledgeChunk.knowledge_type.notin_(cls.STUDENT_EXCLUDED_TYPES))
        return query

    @classmethod
    def citation(cls, user_id, chunk_id, version):
        row = cls.chunks(user_id).filter(KnowledgeChunk.chunk_id == chunk_id, KnowledgeChunk.version == version).first()
        if not row:
            return None
        doc = row.document
        return {
            'chunk_id': row.chunk_id, 'document_id': row.document_id, 'version': row.version,
            'title': row.title or doc.title, 'document_title': doc.title,
            'chapter': row.chapter or doc.chapter, 'source_page': row.source_page,
            'content': row.content, 'teacher_verified': bool(row.teacher_verified),
        }

    @classmethod
    def plan_is_current(cls, plan):
        """Recheck authorization/version before releasing buffered generated content."""
        if not plan.chunks:
            return True
        # A short independent transaction sees revocations made while generation was running.
        from sqlalchemy.orm import Session
        with Session(db.engine) as session:
            rows = cls.chunks(plan.user_id, session=session).filter(
                KnowledgeChunk.chunk_id.in_([c.chunk_id for c in plan.chunks])).all()
            current = {(r.chunk_id, r.version) for r in rows}
        return all((c.chunk_id, c.version) in current for c in plan.chunks)
