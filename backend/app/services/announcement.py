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
