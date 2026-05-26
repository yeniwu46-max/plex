"""班级服务"""
from .base import BaseService
from app.models import Class, User, db
from sqlalchemy import func


class ClassService(BaseService):
    """班级服务"""

    @staticmethod
    def create_class(name, description, grade_level, teacher_id):
        """创建班级"""
        # 检查教师是否存在
        teacher = User.query.get(teacher_id)
        if not teacher:
            raise Exception('教师不存在')
        
        # 检查教师角色
        if teacher.role.name != 'teacher':
            raise Exception('该用户不是教师')
        
        class_obj = Class(
            name=name,
            description=description,
            grade_level=grade_level,
            teacher_id=teacher_id
        )
        
        db.session.add(class_obj)
        db.session.commit()
        
        return class_obj

    @staticmethod
    def get_classes(teacher_id=None, page=1, limit=20):
        """获取班级列表"""
        query = Class.query
        
        if teacher_id:
            query = query.filter_by(teacher_id=teacher_id)
        
        total = query.count()
        classes = query.offset((page - 1) * limit).limit(limit).all()
        
        return {
            'total': total,
            'page': page,
            'limit': limit,
            'classes': [cls.to_dict() for cls in classes]
        }

    @staticmethod
    def get_class(class_id):
        """获取班级详情"""
        class_obj = Class.query.get(class_id)
        if not class_obj:
            raise Exception('班级不存在')
        
        return class_obj

    @staticmethod
    def update_class(class_id, **kwargs):
        """更新班级"""
        class_obj = Class.query.get(class_id)
        if not class_obj:
            raise Exception('班级不存在')
        
        allowed_fields = ['name', 'description', 'grade_level']
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(class_obj, field, value)
        
        db.session.commit()
        return class_obj

    @staticmethod
    def delete_class(class_id):
        """删除班级"""
        class_obj = Class.query.get(class_id)
        if not class_obj:
            raise Exception('班级不存在')
        
        # 检查是否有学生
        if class_obj.students:
            raise Exception('班级还有学生，无法删除')
        
        db.session.delete(class_obj)
        db.session.commit()

    @staticmethod
    def add_student_to_class(class_id, user_id):
        """将学生添加到班级"""
        class_obj = Class.query.get(class_id)
        if not class_obj:
            raise Exception('班级不存在')
        
        user = User.query.get(user_id)
        if not user:
            raise Exception('学生不存在')
        
        if user.role.name != 'student':
            raise Exception('该用户不是学生')
        
        if user.class_id == class_id:
            raise Exception('学生已在该班级中')
        
        if user.class_id:
            old_class = Class.query.get(user.class_id)
            if old_class:
                old_class.student_count = max(0, (old_class.student_count or 0) - 1)

        user.class_id = class_id
        class_obj.student_count = (class_obj.student_count or 0) + 1
        db.session.commit()

    @staticmethod
    def remove_student_from_class(class_id, user_id):
        """从班级移除学生"""
        class_obj = Class.query.get(class_id)
        if not class_obj:
            raise Exception('班级不存在')
        
        user = User.query.get(user_id)
        if not user:
            raise Exception('学生不存在')
        
        if user.class_id != class_id:
            raise Exception('学生不在该班级中')
        
        user.class_id = None
        class_obj.student_count = max(0, class_obj.student_count - 1)
        db.session.commit()

    @staticmethod
    def get_class_ranking(class_id, week=None):
        """获取班级排名"""
        from app.models import RankingCache
        
        query = RankingCache.query.filter_by(class_id=class_id)
        
        if week:
            query = query.filter_by(week=week)
        else:
            from datetime import datetime
            current_week = f"{datetime.now().year}-w{datetime.now().isocalendar()[1]:02d}"
            query = query.filter_by(week=current_week)
        
        rankings = query.order_by(RankingCache.rank.asc()).all()

        if not rankings:
            from .incentive import IncentiveService

            week_key = week or f"{datetime.now().year}-w{datetime.now().isocalendar()[1]:02d}"
            IncentiveService.refresh_class_ranking(class_id, week_key)
            db.session.commit()
            rankings = (
                RankingCache.query.filter_by(class_id=class_id, week=week_key)
                .order_by(RankingCache.rank.asc())
                .all()
            )

        return {
            'class_id': class_id,
            'week': week or f"{datetime.now().year}-w{datetime.now().isocalendar()[1]:02d}",
            'rankings': [r.to_dict() for r in rankings],
        }
