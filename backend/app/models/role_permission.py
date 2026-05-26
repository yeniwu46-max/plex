"""
角色权限关联表 - 定义角色和权限的多对多关系
"""
from .base import db


role_permissions = db.Table(
    'role_permissions',
    db.Column('id', db.Integer, primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False),
    db.Column('created_at', db.DateTime, default=db.func.now()),
    db.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
)
