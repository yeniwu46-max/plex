"""成就路由"""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.achievement import AchievementService
from app.utils.response import success_response, error_response
from app.utils.decorators import permission_required

achievements_bp = Blueprint('achievements', __name__, url_prefix='/api/v1/achievements')


@achievements_bp.route('', methods=['POST'])
@jwt_required()
@permission_required('manage_achievements')
def create_achievement():
    """创建成就 - 需要 manage_achievements 权限"""
    try:
        data = request.get_json()

        required_fields = ['name', 'condition_type', 'condition_value']
        for field in required_fields:
            if not data.get(field):
                return error_response(f'缺少必需字段: {field}', 40001)

        achievement = AchievementService.create_achievement(
            name=data['name'],
            description=data.get('description'),
            icon_url=data.get('icon_url'),
            rarity=data.get('rarity', 'common'),
            condition_type=data['condition_type'],
            condition_value=data['condition_value']
        )

        return success_response(achievement.to_dict(), '成就创建成功', 0, 201)

    except Exception as e:
        return error_response(str(e), 40001)


@achievements_bp.route('', methods=['GET'])
@jwt_required()
def get_achievements():
    """获取成就列表 - 所有认证用户可访问"""
    try:
        rarity = request.args.get('rarity')
        achievements = AchievementService.get_achievements(rarity)
        return success_response(achievements)

    except Exception as e:
        return error_response(str(e), 50001)


@achievements_bp.route('/unlock', methods=['POST'])
@jwt_required()
def unlock_achievement():
    """解锁成就 - 用户可为自己解锁成就，或需要 manage_achievements 权限为他人解锁"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        achievement_id = data.get('achievement_id')
        user_id = data.get('user_id', current_user_id)

        if not achievement_id:
            return error_response('缺少achievement_id', 40001)

        # 如果为其他用户解锁，需要权限
        if user_id != current_user_id:
            from app.models import User
            current_user = User.query.get(current_user_id)
            if not current_user or not current_user.role:
                return error_response("权限检查失败", 40301, None, 403)

            user_permissions = set()
            if current_user.role.permissions:
                for perm in current_user.role.permissions:
                    user_permissions.add(perm.name)

            if 'manage_achievements' not in user_permissions:
                return error_response("您没有权限为其他用户解锁成就", 40301, None, 403)

        AchievementService.unlock_achievement(user_id, achievement_id)

        return success_response(None, '成就已解锁', 0, 201)

    except Exception as e:
        return error_response(str(e), 50001)


@achievements_bp.route('/user/<int:user_id>', methods=['GET'])
@jwt_required()
@permission_required('view_achievements')
def get_user_achievements(user_id):
    """获取用户成就 - 需要 view_achievements 权限"""
    try:
        result = AchievementService.get_user_achievements(user_id)
        return success_response(result)

    except Exception as e:
        return error_response(str(e), 40401)


@achievements_bp.route('/points', methods=['POST'])
@jwt_required()
@permission_required('manage_achievements')
def add_points():
    """添加积分 - 需要 manage_achievements 权限"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        points = data.get('points')
        reason = data.get('reason')

        if not all([user_id, points, reason]):
            return error_response('缺少必需字段', 40001)

        user = AchievementService.add_points(
            user_id=user_id,
            points=points,
            reason=reason,
            related_id=data.get('related_id')
        )

        return success_response(user.to_dict(), '积分已添加', 0, 201)

    except Exception as e:
        return error_response(str(e), 50001)


@achievements_bp.route('/points-log/<int:user_id>', methods=['GET'])
@jwt_required()
@permission_required('view_achievements')
def get_points_log(user_id):
    """获取积分日志 - 需要 view_achievements 权限"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)

        result = AchievementService.get_points_log(user_id, page, limit)
        return success_response(result)

    except Exception as e:
        return error_response(str(e), 50001)
