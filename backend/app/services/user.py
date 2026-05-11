"""用户服务"""
from .base import BaseService
from app.models import User, Role, Permission, db
from werkzeug.security import generate_password_hash


class UserService(BaseService):
    """用户服务"""

    @staticmethod
    def get_user(user_id):
        """获取用户信息"""
        user = User.query.get(user_id)
        if not user:
            raise Exception('用户不存在')
        return user

    @staticmethod
    def get_current_user_info(user_id):
        """获取当前用户完整信息"""
        user = User.query.get(user_id)
        if not user:
            raise Exception('用户不存在')
        
        # 计算班级排名
        class_rank = None
        achievements_count = len(user.achievements)
        
        if user.class_id:
            rank_result = db.session.query(
                db.func.count(User.id)
            ).filter(
                User.class_id == user.class_id,
                User.total_points > user.total_points
            ).scalar()
            class_rank = (rank_result or 0) + 1
        
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
            'title': f'Lv{user.level}',
            'total_points': user.total_points,
            'consecutive_days': user.consecutive_days,
            'achievements_count': achievements_count,
            'class_rank': class_rank,
            'class': {
                'id': user.class_rel.id,
                'name': user.class_rel.name
            } if user.class_rel else None,
        }

    @staticmethod
    def get_users_list(page=1, limit=20, role=None, class_id=None, status=None, search=None):
        """获取用户列表"""
        query = User.query
        
        if role:
            role_obj = Role.query.filter_by(name=role).first()
            if role_obj:
                query = query.filter_by(role_id=role_obj.id)
        
        if class_id:
            query = query.filter_by(class_id=class_id)
        
        if status:
            query = query.filter_by(status=status)
        
        if search:
            query = query.filter(
                db.or_(
                    User.username.contains(search),
                    User.email.contains(search),
                    User.real_name.contains(search)
                )
            )
        
        total = query.count()
        users = query.offset((page - 1) * limit).limit(limit).all()
        
        return {
            'total': total,
            'page': page,
            'limit': limit,
            'users': [
                {
                    'id': u.id,
                    'username': u.username,
                    'real_name': u.real_name,
                    'email': u.email,
                    'phone': u.phone,
                    'avatar_url': u.avatar_url,
                    'role': u.role.name if u.role else None,
                    'level': u.level,
                    'total_points': u.total_points,
                    'class_id': u.class_id,
                    'status': u.status,
                    'created_at': u.created_at.isoformat() if u.created_at else None,
                } for u in users
            ]
        }

    @staticmethod
    def update_user(user_id, **kwargs):
        """更新用户信息"""
        user = User.query.get(user_id)
        if not user:
            raise Exception('用户不存在')
        
        # 允许更新的字段
        allowed_fields = ['real_name', 'phone', 'avatar_url', 'bio', 'gender']
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(user, field, value)
        
        db.session.commit()
        return user

    @staticmethod
    def delete_user(user_id):
        """删除用户（软删除）"""
        user = User.query.get(user_id)
        if not user:
            raise Exception('用户不存在')
        
        user.status = 'deleted'
        from datetime import datetime
        user.deleted_at = datetime.utcnow()
        db.session.commit()

    @staticmethod
    def freeze_user(user_id):
        """冻结用户"""
        user = User.query.get(user_id)
        if not user:
            raise Exception('用户不存在')
        
        user.status = 'frozen'
        db.session.commit()

    @staticmethod
    def unfreeze_user(user_id):
        """解冻用户"""
        user = User.query.get(user_id)
        if not user:
            raise Exception('用户不存在')
        
        user.status = 'active'
        db.session.commit()

    @staticmethod
    def get_user_permissions(user_id):
        """获取用户权限"""
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
