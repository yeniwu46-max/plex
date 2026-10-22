"""Authenticated, self-only arrival and appearance endpoints."""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db
from app.services.onboarding import OnboardingService
from app.utils.decorators import role_required
from app.utils.response import success_response, error_response

onboarding_bp = Blueprint('onboarding', __name__, url_prefix='/api/v1')


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or (request.content_length or 0) > 4096:
        raise ValueError('请提交有效的问卷数据')
    return data


def run(operation):
    try:
        return success_response(operation(int(get_jwt_identity())))
    except ValueError as exc:
        db.session.rollback()
        return error_response(str(exc), 40001, None, 400)
    except Exception:
        db.session.rollback()
        from flask import current_app
        current_app.logger.exception('Onboarding operation failed')
        return error_response('暂时无法保存，请重试，你的编号不会重复领取', 50001, None, 500)


@onboarding_bp.route('/student/onboarding', methods=['GET', 'PATCH'])
@jwt_required()
@role_required('student')
def onboarding():
    return run(lambda uid: OnboardingService.get(uid) if request.method == 'GET' else OnboardingService.patch(uid, body()))


@onboarding_bp.post('/student/onboarding/complete')
@jwt_required()
@role_required('student')
def complete():
    return run(lambda uid: OnboardingService.complete(uid, body()))


@onboarding_bp.post('/student/onboarding/acknowledge')
@jwt_required()
@role_required('student')
def acknowledge():
    return run(OnboardingService.acknowledge)


@onboarding_bp.route('/users/me/preferences', methods=['GET', 'PATCH'])
@jwt_required()
def preferences():
    def operation(uid):
        if request.method == 'PATCH':
            row = OnboardingService.set_appearance(uid, body())
            db.session.commit()
            return row.to_dict()
        return OnboardingService.account_fields(uid)['preferences']
    return run(operation)
