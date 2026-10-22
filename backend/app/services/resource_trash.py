"""Seven-day owner trash. Audits survive expiry; shared assets are never removed."""
from copy import deepcopy
from datetime import timedelta
import uuid
from app.models import db
from app.models.personalized_resource import PersonalizedLearningResource as Resource, ResourceGenerationTask as Task
from app.services.tutor_context import TutorContextError
from app.utils.time import utc_now


class ResourceTrash:
    @staticmethod
    def move(uid, *, resource_id=None, task_id=None):
        query = Resource.query.filter_by(user_id=uid)
        if task_id:
            task = Task.query.filter_by(task_id=task_id, user_id=uid).first()
            if not task:
                raise TutorContextError('资源包不存在', 404)
            if task.status in ('pending', 'running'):
                raise TutorContextError('生成完成后才可删除资源包', 409)
            query = query.filter_by(generation_task_id=task_id)
        else:
            query = query.filter_by(id=resource_id)
        if not query.first():
            raise TutorContextError('资源不存在', 404)
        batch = str(uuid.uuid4())
        now = utc_now()
        count = query.filter(Resource.deleted_at.is_(None)).update(
            {'deleted_at': now, 'expires_at': now + timedelta(days=7), 'deletion_batch': batch}, synchronize_session=False)
        db.session.commit()
        return {'batch_id': batch, 'count': count}

    @staticmethod
    def list(uid, args):
        q = Resource.query.filter(Resource.user_id == uid, Resource.deleted_at.isnot(None), Resource.expires_at > utc_now())
        page = max(1, int(args.get('page') or 1))
        return {'items': [{'id': r.id, 'title': r.title, 'resource_type': r.resource_type, 'batch_id': r.deletion_batch,
                'deleted_at': r.deleted_at.isoformat()+'Z', 'expires_at': r.expires_at.isoformat()+'Z'}
                for r in q.order_by(Resource.deleted_at.desc(), Resource.id.desc()).offset((page-1)*20).limit(20)], 'total': q.count()}

    @staticmethod
    def restore(uid, *, resource_id=None, batch_id=None):
        q = Resource.query.filter(Resource.user_id == uid, Resource.deleted_at.isnot(None), Resource.expires_at > utc_now())
        q = q.filter_by(deletion_batch=batch_id) if batch_id else q.filter_by(id=resource_id)
        count = q.update({'deleted_at': None, 'expires_at': None, 'deletion_batch': None}, synchronize_session=False)
        db.session.commit()
        if not count:
            raise TutorContextError('资源已到期或不在你的回收站中', 404)
        return {'count': count}

    @staticmethod
    def sanitize(row, payload):
        if row.deleted_at:
            return {**payload, 'content': {}, 'content_url': None, 'citations': [], 'deleted': True}
        deleted = Resource.query.filter(Resource.generation_task_id == row.generation_task_id, Resource.deleted_at.isnot(None)).all()
        if not deleted:
            return payload
        content = deepcopy(payload['content'])
        # Bundle copies otherwise resurrect individually deleted content/downloads.
        fields = {'lesson_document': ['explain'], 'exercise_set': ['exercises'],
                  'coding_lab': ['code'], 'mind_map': ['summary'], 'extended_reading': ['cases'], 'visual_diagram': ['diagrams']}
        if row.resource_type == 'learning_bundle':
            for item in deleted:
                for key in fields.get(item.resource_type, []):
                    content.pop(key, None)
            content.pop('markdown', None)
            from app.services.pedagogical_resource import render_markdown
            content['markdown'] = render_markdown(content)
        payload['content'] = content
        return payload

    @staticmethod
    def purge():
        # Keep the tombstone and review metadata. Exclusive generated content is
        # cleared; external/shared media files are deliberately not unlinked.
        rows = Resource.query.filter(Resource.expires_at <= utc_now(), Resource.purged_at.is_(None)).limit(100).all()
        for row in rows:
            row.content, row.purged_at = {}, utc_now()
        db.session.commit()
        return len(rows)
