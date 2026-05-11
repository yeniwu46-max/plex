"""
角色模型 - 定义系统中的角色（学生、教师、管理员）
"""
from .base import BaseModel, db


class Role(BaseModel):
    """
    角色表
    """
    __tablename__ = 'roles'

    name = db.Column(db.String(50), unique=True, nullable=False)  # 角色名: student, teacher, admin
    description = db.Column(db.Text)  # 角色描述
    color = db.Column(db.String(10))  # 配色: green, orange, purple

    # 关系
    permissions = db.relationship('Permission', secondary='role_permissions', backref='roles', lazy=True)

    def __repr__(self):
        return f"<Role {self.name}>"
