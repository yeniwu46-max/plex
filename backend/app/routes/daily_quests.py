"""每日委托路由"""
from flask_jwt_extended import get_jwt_identity, jwt_required

from flask import Blueprint

from app.services.daily_quest import DailyQuestService
from app.utils.response import error_response, success_response

daily_quests_bp = Blueprint('daily_quests', __name__, url_prefix='/api/v1/daily-quests')


@daily_quests_bp.route('/today', methods=['GET'])
@jwt_required()
def get_today_quests():
    try:
        user_id = int(get_jwt_identity())
        return success_response(DailyQuestService.get_today(user_id))
    except Exception as e:
        return error_response(str(e), 50001)


@daily_quests_bp.route('/<string:quest_key>/progress', methods=['POST'])
@jwt_required()
def progress_quest(quest_key):
    try:
        user_id = int(get_jwt_identity())
        return success_response(DailyQuestService.advance_progress(user_id, quest_key), '委托进度已更新')
    except Exception as e:
        return error_response(str(e), 40001)


@daily_quests_bp.route('/claim-bonus', methods=['POST'])
@jwt_required()
def claim_bonus():
    try:
        user_id = int(get_jwt_identity())
        return success_response(DailyQuestService.claim_bonus(user_id), '今日委托奖励已结算')
    except Exception as e:
        return error_response(str(e), 40001)
