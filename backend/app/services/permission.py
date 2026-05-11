"""权限服务"""
from .base import BaseService
from app.models import Role, Permission, role_permissions, db


class PermissionService(BaseService):
    """权限服务"""

    @staticmethod
    def get_roles():
        """获取所有角色"""
        roles = Role.query.all()
        return [role.to_dict() for role in roles]

    @staticmethod
    def get_permissions(resource=None):
        """获取权限列表"""
        query = Permission.query

        if resource:
            query = query.filter_by(resource=resource)

        permissions = query.all()
        return [perm.to_dict() for perm in permissions]

    @staticmethod
    def assign_permissions_to_role(role_id, permission_ids):
        """为角色分配权限"""
        role = Role.query.get(role_id)
        if not role:
            raise Exception('角色不存在')

        db.session.execute(role_permissions.delete().where(role_permissions.c.role_id == role_id))

        for perm_id in permission_ids:
            perm = Permission.query.get(perm_id)
            if not perm:
                raise Exception(f'权限ID {perm_id} 不存在')

            db.session.execute(role_permissions.insert().values(
                role_id=role_id,
                permission_id=perm_id
            ))

        db.session.commit()

    @staticmethod
    def check_user_permission(user_id, permission_name):
        """检查用户是否有某个权限"""
        from app.models import User

        user = User.query.get(user_id)
        if not user:
            raise Exception('用户不存在')

        if not user.role:
            return False

        permission = Permission.query.filter_by(name=permission_name).first()
        if not permission:
            return False

        has_permission = db.session.execute(
            role_permissions.select().where(
                (role_permissions.c.role_id == user.role.id) &
                (role_permissions.c.permission_id == permission.id)
            )
        ).first()

        return has_permission is not None
