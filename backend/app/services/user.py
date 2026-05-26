"""User service."""
from datetime import datetime

from werkzeug.security import generate_password_hash

from .base import BaseService
from app.models import RankingCache, User, Role, db


class UserService(BaseService):
    """User domain operations."""

    @staticmethod
    def get_user(user_id):
        user = User.query.get(user_id)
        if not user:
            raise Exception('用户不存在')
        return user

    @staticmethod
    def create_student(username, email, password, real_name, **kwargs):
        """Create a student account from the management console."""
        if User.query.filter_by(username=username).first():
            raise Exception('用户名已存在')
        if User.query.filter_by(email=email).first():
            raise Exception('邮箱已存在')

        student_role = Role.query.filter_by(name='student').first()
        if not student_role:
            raise Exception('学生角色不存在')

        class_id = UserService._normalize_class_id(kwargs.get('class_id'))
        class_obj = UserService._get_class_or_none(class_id)

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            real_name=real_name,
            phone=kwargs.get('phone'),
            gender=kwargs.get('gender') or 'other',
            bio=kwargs.get('bio'),
            class_id=class_id,
            role_id=student_role.id,
            status='active',
        )

        db.session.add(user)
        if class_obj:
            class_obj.student_count = (class_obj.student_count or 0) + 1
        db.session.commit()
        return user

    @staticmethod
    def get_current_user_info(user_id):
        user = User.query.get(user_id)
        if not user:
            raise Exception('用户不存在')

        from .incentive import IncentiveService

        IncentiveService.sync_user_level(user)
        if user.class_id:
            if not RankingCache.query.filter_by(
                class_id=user.class_id, week=IncentiveService.current_week_key()
            ).count():
                IncentiveService.refresh_class_ranking(user.class_id)
            db.session.commit()

        class_rank = IncentiveService.class_rank_for_user(user)
        achievements_count = len(user.achievements)
        level_profile = IncentiveService.level_profile(user)
        incentive_summary = IncentiveService.incentive_summary(user.id)

        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'real_name': user.real_name,
            'avatar_url': user.avatar_url,
            'phone': user.phone,
            'gender': user.gender,
            'bio': user.bio,
            'role': user.role.name if user.role else None,
            'status': user.status,
            'level': user.level,
            'title': level_profile['title'],
            'total_points': user.total_points,
            'level_profile': level_profile,
            'incentive': incentive_summary,
            'consecutive_days': user.consecutive_days,
            'achievements_count': achievements_count,
            'class_rank': class_rank,
            'class': {
                'id': user.class_rel.id,
                'name': user.class_rel.name,
            } if user.class_rel else None,
        }

    @staticmethod
    def get_users_list(page=1, limit=20, role=None, class_id=None, status=None, search=None):
        query = User.query

        if role:
            role_obj = Role.query.filter_by(name=role).first()
            if role_obj:
                query = query.filter_by(role_id=role_obj.id)

        if class_id:
            query = query.filter_by(class_id=class_id)

        if status:
            statuses = [item.strip() for item in str(status).split(',') if item.strip()]
            if len(statuses) == 1:
                query = query.filter_by(status=statuses[0])
            elif statuses:
                query = query.filter(User.status.in_(statuses))

        if search:
            query = query.filter(
                db.or_(
                    User.username.contains(search),
                    User.email.contains(search),
                    User.real_name.contains(search),
                )
            )

        total = query.count()
        users = query.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

        return {
            'total': total,
            'page': page,
            'limit': limit,
            'users': [UserService._list_item(u) for u in users],
        }

    @staticmethod
    def update_user(user_id, admin_edit=False, **kwargs):
        user = User.query.get(user_id)
        if not user:
            raise Exception('用户不存在')

        allowed_fields = ['real_name', 'phone', 'avatar_url', 'bio', 'gender']
        if admin_edit:
            allowed_fields = [
                'username',
                'email',
                'real_name',
                'phone',
                'avatar_url',
                'bio',
                'gender',
                'class_id',
                'status',
            ]

        if admin_edit and 'username' in kwargs and kwargs['username'] != user.username:
            if User.query.filter(User.username == kwargs['username'], User.id != user.id).first():
                raise Exception('用户名已存在')

        if admin_edit and 'email' in kwargs and kwargs['email'] != user.email:
            if User.query.filter(User.email == kwargs['email'], User.id != user.id).first():
                raise Exception('邮箱已存在')

        old_class_id = user.class_id

        for field, value in kwargs.items():
            if field not in allowed_fields:
                continue
            if field == 'class_id':
                value = UserService._normalize_class_id(value)
            if field == 'status' and value not in ['active', 'frozen', 'deleted']:
                raise Exception('无效的用户状态')
            setattr(user, field, value)

        if admin_edit and old_class_id != user.class_id:
            new_class = UserService._get_class_or_none(user.class_id)
            if old_class_id is not None:
                old_class = UserService._get_class_or_none(old_class_id, required=False)
                if old_class:
                    old_class.student_count = max(0, (old_class.student_count or 0) - 1)
            if new_class:
                new_class.student_count = (new_class.student_count or 0) + 1

        db.session.commit()
        return user

    @staticmethod
    def delete_user(user_id):
        user = User.query.get(user_id)
        if not user:
            raise Exception('用户不存在')

        if user.class_id is not None:
            class_obj = UserService._get_class_or_none(user.class_id, required=False)
            if class_obj:
                class_obj.student_count = max(0, (class_obj.student_count or 0) - 1)
            user.class_id = None

        user.status = 'deleted'
        user.deleted_at = datetime.utcnow()
        db.session.commit()

    @staticmethod
    def freeze_user(user_id):
        user = User.query.get(user_id)
        if not user:
            raise Exception('用户不存在')

        user.status = 'frozen'
        db.session.commit()

    @staticmethod
    def unfreeze_user(user_id):
        user = User.query.get(user_id)
        if not user:
            raise Exception('用户不存在')

        user.status = 'active'
        db.session.commit()

    @staticmethod
    def get_user_permissions(user_id):
        user = User.query.get(user_id)
        if not user:
            raise Exception('用户不存在')

        permissions = [p.name for p in user.role.permissions] if user.role else []

        return {
            'user_id': user_id,
            'role': user.role.name if user.role else None,
            'permissions': permissions,
            'can_manage_classes': 'manage_classes' in permissions,
            'can_manage_permissions': 'manage_permissions' in permissions,
        }

    @staticmethod
    def _list_item(user):
        return {
            'id': user.id,
            'username': user.username,
            'real_name': user.real_name,
            'email': user.email,
            'phone': user.phone,
            'avatar_url': user.avatar_url,
            'role': user.role.name if user.role else None,
            'level': user.level,
            'total_points': user.total_points,
            'class_id': user.class_id,
            'class_name': user.class_rel.name if user.class_rel else None,
            'status': user.status,
            'created_at': user.created_at.isoformat() if user.created_at else None,
        }

    @staticmethod
    def _normalize_class_id(value):
        if value in (None, '', 0, '0'):
            return None
        return int(value)

    @staticmethod
    def _get_class_or_none(class_id, required=True):
        if class_id is None:
            return None

        from app.models import Class

        class_obj = Class.query.get(class_id)
        if required and not class_obj:
            raise Exception('班级不存在')
        return class_obj
