"""
权限模型 - 定义系统中的权限
"""
from .base import BaseModel, db


class Permission(BaseModel):
    """
    权限表
    """
    __tablename__ = 'permissions'

    name = db.Column(db.String(100), unique=True, nullable=False)  # 权限名: users:read, users:create
    description = db.Column(db.Text)  # 权限描述
    resource = db.Column(db.String(50), nullable=False)  # 资源: users, classes, courses
    action = db.Column(db.String(50), nullable=False)  # 操作: create, read, update, delete

    def __repr__(self):
        return f"<Permission {self.name}>"
