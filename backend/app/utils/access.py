"""路由层权限与班级归属校验。"""
from app.models import Class, User


def current_user_from_id(user_id: int) -> User | None:
    return User.query.get(user_id)


def permission_names(user: User | None) -> set[str]:
    if not user or not user.role or not user.role.permissions:
        return set()
    return {perm.name for perm in user.role.permissions}


def is_admin(user: User | None) -> bool:
    return bool(user and user.role and user.role.name == 'admin')


def can_manage_classes(user: User | None) -> bool:
    return 'manage_classes' in permission_names(user)


def teacher_owns_class(user: User | None, class_id: int | None) -> bool:
    if not user or not class_id:
        return False
    if user.role and user.role.name != 'teacher':
        return False
    class_obj = Class.query.get(class_id)
    return bool(class_obj and class_obj.teacher_id == user.id)


def can_edit_class(user: User | None, class_id: int) -> bool:
    if can_manage_classes(user):
        return True
    return teacher_owns_class(user, class_id)


def can_manage_class_students(user: User | None, class_id: int) -> bool:
    if can_manage_classes(user):
        return True
    return teacher_owns_class(user, class_id)


def can_manage_student_user(actor: User | None, target: User | None) -> bool:
    if not actor or not target:
        return False
    if is_admin(actor) or 'manage_classes' in permission_names(actor):
        return True
    if target.role and target.role.name != 'student':
        return False
    if not teacher_owns_class(actor, target.class_id):
        return False
    perms = permission_names(actor)
    return bool(perms & {'create_user', 'edit_user', 'delete_user'})
