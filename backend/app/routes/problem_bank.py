"""题库浏览与提交记录查询路由（清洗自旧版 Mulberry/HydroOJ dump，见任务1报告）。

当前仅开放给教师/管理员使用（预览页面 `/teacher/problem-bank`）；这些题目与
提交记录来自旧系统导入，`legacy_user_id` 不对应当前 PLEX 学生账号，暂不对
学生端开放个人提交历史查询。
"""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.services.problem_bank import ProblemBankService
from app.utils.decorators import role_required
from app.utils.response import error_response, success_response

problem_bank_bp = Blueprint('problem_bank', __name__, url_prefix='/api/v1/problem-bank')


@problem_bank_bp.route('/problems', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def list_problems():
    try:
        return success_response(ProblemBankService.list_problems(
            concept_group=request.args.get('concept_group'),
            keyword=request.args.get('keyword'),
            tag=request.args.get('tag'),
            domain_key=request.args.get('domain_key'),
            kg_node_id=request.args.get('kg_node_id'),
        ))
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@problem_bank_bp.route('/tags', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def list_tags():
    try:
        return success_response(ProblemBankService.list_tags())
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@problem_bank_bp.route('/problems/<int:problem_id>/stats', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def get_problem_stats(problem_id):
    try:
        legacy_group_id = request.args.get('legacy_group_id', type=int)
        return success_response(ProblemBankService.get_problem_stats(problem_id, legacy_group_id))
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@problem_bank_bp.route('/problems/<int:problem_id>', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def get_problem(problem_id):
    try:
        include_answer = request.args.get('include_answer') == '1'
        return success_response(ProblemBankService.get_problem_detail(problem_id, include_answer))
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@problem_bank_bp.route('/problems/<int:problem_id>/submissions', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def list_problem_submissions(problem_id):
    try:
        legacy_user_id = request.args.get('legacy_user_id', type=int)
        limit = request.args.get('limit', default=100, type=int)
        return success_response(ProblemBankService.list_submissions(problem_id, legacy_user_id, limit))
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@problem_bank_bp.route('/submissions/<int:submission_id>', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def get_submission(submission_id):
    try:
        return success_response(ProblemBankService.get_submission_detail(submission_id))
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)
