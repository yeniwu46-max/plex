"""班级服务"""
import secrets

from .base import BaseService
from app.models import Class, User, db
from sqlalchemy import func

_JOIN_CODE_ALPHABET = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'


class ClassService(BaseService):
    """班级服务"""

    @staticmethod
    def generate_join_code() -> str:
        """生成 6 位唯一班级编号。"""
        while True:
            code = ''.join(secrets.choice(_JOIN_CODE_ALPHABET) for _ in range(6))
            if not Class.query.filter_by(join_code=code).first():
                return code

    @staticmethod
    def ensure_join_codes() -> None:
        """为缺少编号的班级补齐 join_code。"""
        missing = Class.query.filter((Class.join_code.is_(None)) | (Class.join_code == '')).all()
        for class_obj in missing:
            class_obj.join_code = ClassService.generate_join_code()
        if missing:
            db.session.commit()

    @staticmethod
    def get_class_by_join_code(join_code: str) -> Class | None:
        normalized = (join_code or '').strip().upper()
        if not normalized:
            return None
        return Class.query.filter_by(join_code=normalized).first()

    @staticmethod
    def create_class(name, description, grade_level, teacher_id):
        """创建班级"""
        # 检查教师是否存在
        teacher = db.session.get(User, teacher_id)
        if not teacher:
            raise Exception('教师不存在')
        
        # 检查教师角色
        if teacher.role.name != 'teacher':
            raise Exception('该用户不是教师')
        
        class_obj = Class(
            name=name,
            description=description,
            grade_level=grade_level,
            teacher_id=teacher_id,
            join_code=ClassService.generate_join_code(),
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
        class_obj = db.session.get(Class, class_id)
        if not class_obj:
            raise Exception('班级不存在')
        
        return class_obj

    @staticmethod
    def update_class(class_id, **kwargs):
        """更新班级"""
        class_obj = db.session.get(Class, class_id)
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
        class_obj = db.session.get(Class, class_id)
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
        class_obj = db.session.get(Class, class_id)
        if not class_obj:
            raise Exception('班级不存在')
        
        user = db.session.get(User, user_id)
        if not user:
            raise Exception('学生不存在')
        
        if user.role.name != 'student':
            raise Exception('该用户不是学生')
        
        if user.class_id == class_id:
            raise Exception('学生已在该班级中')
        
        if user.class_id:
            old_class = db.session.get(Class, user.class_id)
            if old_class:
                old_class.student_count = max(0, (old_class.student_count or 0) - 1)

        user.class_id = class_id
        class_obj.student_count = (class_obj.student_count or 0) + 1
        db.session.commit()

    @staticmethod
    def remove_student_from_class(class_id, user_id):
        """从班级移除学生"""
        class_obj = db.session.get(Class, class_id)
        if not class_obj:
            raise Exception('班级不存在')
        
        user = db.session.get(User, user_id)
        if not user:
            raise Exception('学生不存在')
        
        if user.class_id != class_id:
            raise Exception('学生不在该班级中')
        
        user.class_id = None
        class_obj.student_count = max(0, class_obj.student_count - 1)
        db.session.commit()

    @staticmethod
    def get_class_ranking(class_id, week=None):
        """获取班级排名（附真实姓名、等级称号、XP、对局胜局、在线状态）。"""
        from datetime import datetime

        from sqlalchemy import func

        from app.models import PointsLog, RankingCache, User
        from app.services.incentive import LEVEL_TITLES
        from app.services.presence import PresenceService

        if week:
            week_key = week
        else:
            week_key = f"{datetime.now().year}-w{datetime.now().isocalendar()[1]:02d}"

        rankings = (
            RankingCache.query.filter_by(class_id=class_id, week=week_key)
            .order_by(RankingCache.rank.asc())
            .all()
        )

        if not rankings:
            from .incentive import IncentiveService

            IncentiveService.refresh_class_ranking(class_id, week_key)
            db.session.commit()
            rankings = (
                RankingCache.query.filter_by(class_id=class_id, week=week_key)
                .order_by(RankingCache.rank.asc())
                .all()
            )

        user_ids = [row.user_id for row in rankings if row.user_id]
        users = User.query.filter(User.id.in_(user_ids)).all() if user_ids else []
        user_by_id = {user.id: user for user in users}

        win_rows = []
        if user_ids:
            win_rows = (
                db.session.query(PointsLog.user_id, func.count(PointsLog.id))
                .filter(PointsLog.user_id.in_(user_ids), PointsLog.reason == 'duel_win')
                .group_by(PointsLog.user_id)
                .all()
            )
        wins_by_user = {int(uid): int(cnt or 0) for uid, cnt in win_rows}
        # demo 库若尚无对局记录：用累计解题数推导可展示胜局，避免前台全 0
        if user_ids and not any(wins_by_user.values()):
            from app.models import TrialQuestionProgress

            solved_rows = (
                db.session.query(TrialQuestionProgress.user_id, func.count(TrialQuestionProgress.id))
                .filter(
                    TrialQuestionProgress.user_id.in_(user_ids),
                    TrialQuestionProgress.status == 'completed',
                    TrialQuestionProgress.is_correct.is_(True),
                )
                .group_by(TrialQuestionProgress.user_id)
                .all()
            )
            for uid, cnt in solved_rows:
                wins_by_user[int(uid)] = max(0, int(cnt or 0) // 3)

        online_ids = PresenceService.online_user_ids(class_id)

        enriched = []
        for row in rankings:
            base = row.to_dict()
            user = user_by_id.get(row.user_id)
            level = (user.level if user else None) or row.level or 1
            total_points = (user.total_points if user else None) or 0
            display_name = ''
            if user:
                display_name = (user.real_name or user.username or '').strip()
            base.update({
                'user_name': display_name or f'学员{row.user_id}',
                'real_name': (user.real_name if user else None) or None,
                'username': user.username if user else None,
                'level': level,
                'title': LEVEL_TITLES.get(level, f'Lv{level}'),
                'total_points': total_points,
                # points 保留周积分；XP 用 total_points 给前端展示
                'week_points': row.points or 0,
                'win_count': wins_by_user.get(row.user_id, 0),
                'online': row.user_id in online_ids,
            })
            enriched.append(base)

        return {
            'class_id': class_id,
            'week': week_key,
            'rankings': enriched,
        }

    @staticmethod
    def get_win_leaderboard(class_id: int, limit: int = 5) -> list[dict]:
        """对局胜局数从高到低的前 N 名（复用 enrich 后的班排数据）。"""
        ranking = ClassService.get_class_ranking(class_id)
        rows = list(ranking.get('rankings') or [])
        rows.sort(
            key=lambda item: (
                int(item.get('win_count') or 0),
                int(item.get('total_points') or 0),
                -int(item.get('rank') or 999),
            ),
            reverse=True,
        )
        top = []
        for idx, item in enumerate(rows[: max(1, limit)], start=1):
            top.append({
                **item,
                'win_rank': idx,
            })
        return top

    @staticmethod
    def record_duel_win(winner_id: int, opponent_id: int | None = None) -> dict:
        """记录一场学生对战胜局（写入 PointsLog，reason=duel_win）。"""
        from app.models import PointsLog
        from app.services.incentive import IncentiveService

        winner = db.session.get(User, winner_id)
        if not winner:
            raise ValueError('用户不存在')
        if opponent_id and opponent_id == winner_id:
            raise ValueError('不能与自己对战')
        if opponent_id:
            opponent = db.session.get(User, opponent_id)
            if not opponent:
                raise ValueError('对手不存在')
            if winner.class_id and opponent.class_id and winner.class_id != opponent.class_id:
                raise ValueError('只能与同班同学 PK')

        db.session.add(PointsLog(
            user_id=winner_id,
            points=15,
            reason='duel_win',
            related_id=opponent_id,
        ))
        if not IncentiveService.is_xp_capped(winner):
            winner.total_points = (winner.total_points or 0) + 15
            IncentiveService.sync_user_level(winner)
        if winner.class_id:
            IncentiveService.refresh_class_ranking(winner.class_id)
        db.session.commit()

        from sqlalchemy import func
        from app.models import PointsLog as PL

        win_count = (
            db.session.query(func.count(PL.id))
            .filter(PL.user_id == winner_id, PL.reason == 'duel_win')
            .scalar()
        )
        return {
            'user_id': winner_id,
            'opponent_id': opponent_id,
            'win_count': int(win_count or 0),
            'total_points': winner.total_points or 0,
            'level': winner.level or 1,
        }
