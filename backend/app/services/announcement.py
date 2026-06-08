"""系统公告"""
from app.models import SystemAnnouncement, db


class AnnouncementService:
    @staticmethod
    def list_for_role(role_name: str, limit: int = 30):
        query = SystemAnnouncement.query.filter_by(is_active=True)
        if role_name == 'teacher':
            query = query.filter(SystemAnnouncement.target_role.in_(['teacher', 'all']))
        elif role_name == 'student':
            query = query.filter(SystemAnnouncement.target_role.in_(['student', 'all']))
        rows = query.order_by(SystemAnnouncement.created_at.desc()).limit(limit).all()
        return [row.to_dict() for row in rows]

    @staticmethod
    def list_all(limit: int = 50):
        rows = (
            SystemAnnouncement.query.filter_by(is_active=True)
            .order_by(SystemAnnouncement.created_at.desc())
            .limit(limit)
            .all()
        )
        return [row.to_dict() for row in rows]

    @staticmethod
    def create(admin_id: int, payload: dict):
        title = (payload.get('title') or '').strip()
        body = (payload.get('body') or '').strip()
        if not title or not body:
            raise ValueError('标题与内容不能为空')
        target = (payload.get('target_role') or 'teacher').strip().lower()
        if target not in ('teacher', 'student', 'all'):
            target = 'teacher'
        row = SystemAnnouncement(
            title=title[:120],
            body=body[:4000],
            target_role=target,
            created_by=admin_id,
            is_active=True,
        )
        db.session.add(row)
        db.session.commit()
        return row.to_dict()

    @staticmethod
    def update(announcement_id: int, payload: dict):
        row = SystemAnnouncement.query.get(announcement_id)
        if not row:
            raise ValueError('公告不存在')
        if 'title' in payload and payload['title']:
            row.title = str(payload['title']).strip()[:120]
        if 'body' in payload and payload['body']:
            row.body = str(payload['body']).strip()[:4000]
        if 'target_role' in payload and payload['target_role']:
            target = str(payload['target_role']).strip().lower()
            if target in ('teacher', 'student', 'all'):
                row.target_role = target
        db.session.commit()
        return row.to_dict()

    @staticmethod
    def delete(announcement_id: int):
        row = SystemAnnouncement.query.get(announcement_id)
        if not row:
            raise ValueError('公告不存在')
        row.is_active = False
        db.session.commit()
        return {'deleted': True, 'id': announcement_id}
