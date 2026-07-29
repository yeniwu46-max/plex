"""Student profile API."""
from flask import Blueprint, Response, request, stream_with_context
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.course_safety import CourseSafetyService, SafetyViolation
from app.services.llm_stream import (
    chunk_text,
    iter_openai_stream,
    sse_event,
    sse_headers,
    stream_provider_chain,
)
from app.services.student_profile import StudentProfileService
from app.utils.decorators import role_required
from app.utils.response import error_response, success_response

student_profile_bp = Blueprint('student_profile', __name__, url_prefix='/api/v1/student/profile')


@student_profile_bp.route('', methods=['GET'])
@jwt_required()
@role_required('student')
def get_profile():
    user_id = int(get_jwt_identity())
    return success_response(StudentProfileService.get_or_create(user_id).to_dict())


@student_profile_bp.route('/diagnostic', methods=['GET', 'POST'])
@jwt_required()
@role_required('student')
def diagnostic():
    user_id = int(get_jwt_identity())
    if request.method == 'GET':
        return success_response({'questions': StudentProfileService.diagnostic_questions(), 'diagnostic': StudentProfileService.diagnostic_status(user_id)})
    try:
        payload = request.get_json() or {}
        return success_response(StudentProfileService.submit_diagnostic(user_id, payload.get('answers'), bool(payload.get('skip'))))
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)


@student_profile_bp.route('/adaptations', methods=['GET'])
@jwt_required()
@role_required('student')
def adaptations():
    from app.services.learning_adaptation import LearningAdaptationService
    return success_response({'items': LearningAdaptationService.active_for_student(int(get_jwt_identity()))})


@student_profile_bp.route('/chat', methods=['POST'])
@jwt_required()
@role_required('student')
def chat_profile():
    try:
        user_id = int(get_jwt_identity())
        payload = request.get_json() or {}
        return success_response(StudentProfileService.chat(
            user_id,
            payload.get('message', ''),
            bool(payload.get('confirm_changes')),
        ))
    except SafetyViolation as exc:
        return error_response(str(exc), 40012, {'reason_code': exc.reason_code}, 400)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)


def _profile_reply_stream(message: str, result: dict):
    """基于抽取结果流式生成自然语言确认回复；无 LLM 时伪流式输出既有文案。"""
    proposed = result.get('proposed_changes') or []
    if proposed:
        lines = []
        for item in proposed:
            flag = '（低置信度，需要学生确认）' if item.get('requires_confirmation') else ''
            lines.append(f"- {item.get('label')}：{item.get('new_value')}{flag}")
        summary = '\n'.join(lines)
        system = (
            '你是 A3 个性化学习系统的画像助手小E。刚才你从学生的一句话中抽取了画像信息。'
            '请用 80-150 字向学生自然地复述你了解到了什么，并请学生确认低置信度条目。'
            '可以使用 Markdown 列表。不要提到"置信度"这类术语，说"我不太确定"即可。'
            '不要提及模型、接口或供应商。'
        )
        user = f'学生原话：{message[:300]}\n\n抽取结果：\n{summary}'
        for provider in stream_provider_chain('profile'):
            emitted = False
            collected: list[str] = []
            try:
                for delta in iter_openai_stream(provider, [
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': user},
                ], max_tokens=320, timeout=(3, 5)):
                    emitted = True
                    collected.append(delta)
                    yield {'type': 'delta', 'text': delta}
            except Exception:
                if not emitted:
                    continue
            if emitted:
                result['assistant_reply'] = ''.join(collected).strip()
                return
    for piece in chunk_text(result.get('assistant_reply') or ''):
        yield {'type': 'delta', 'text': piece}


@student_profile_bp.route('/chat/stream', methods=['POST'])
@jwt_required()
@role_required('student')
def chat_profile_stream():
    """SSE 流式画像对话：阶段进度 + 流式确认回复 + 完整画像结果。"""
    user_id = int(get_jwt_identity())
    payload = request.get_json() or {}
    message = (payload.get('message') or '').strip()
    confirm_changes = bool(payload.get('confirm_changes'))
    if len(message) < 2:
        return error_response('message不能为空', 40001, None, 400)
    try:
        CourseSafetyService.ensure_safe(message)
    except SafetyViolation as exc:
        return error_response(str(exc), 40012, {'reason_code': exc.reason_code}, 400)

    def generate():
        try:
            # 1) 规则快抽：立刻吐字，避免空等 LLM
            yield sse_event({'type': 'stage', 'stage': 'extracting', 'label': '先快速理解你的描述'})
            quick = StudentProfileService.chat(
                user_id, message, confirm_changes, skip_llm=True,
            )
            for piece in chunk_text(quick.get('assistant_reply') or ''):
                yield sse_event({'type': 'delta', 'text': piece})

            # 2) 短超时 LLM  enrichment；失败保留规则结果
            yield sse_event({'type': 'stage', 'stage': 'merging', 'label': '补充画像细节并刷新卡片'})
            result = quick
            try:
                enriched = StudentProfileService.chat(
                    user_id,
                    message,
                    confirm_changes,
                    skip_llm=False,
                    llm_timeout=7.0,
                )
                result = enriched
                # 若 LLM 文案与规则稿明显不同，再补一段精炼说明（不覆盖已流式内容）
                extra = (enriched.get('assistant_reply') or '').strip()
                quick_reply = (quick.get('assistant_reply') or '').strip()
                if extra and extra != quick_reply and enriched.get('backend') not in (
                    None, 'local_rules',
                ):
                    yield sse_event({
                        'type': 'delta',
                        'text': '\n\n——\n' + extra,
                    })
            except Exception:
                yield sse_event({
                    'type': 'stage',
                    'stage': 'fallback',
                    'label': '已用规则结果完成更新',
                })

            yield sse_event({'type': 'done', 'result': result})
        except ValueError as exc:
            yield sse_event({'type': 'error', 'message': str(exc)})
        except Exception as exc:
            yield sse_event({'type': 'error', 'message': str(exc)})

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers=sse_headers(),
    )


@student_profile_bp.route('', methods=['PUT'])
@jwt_required()
@role_required('student')
def update_profile():
    try:
        user_id = int(get_jwt_identity())
        payload = request.get_json() or {}
        return success_response(StudentProfileService.apply_changes(
            user_id,
            payload.get('changes') or {},
            payload.get('reason') or 'student_correction',
        ))
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)


@student_profile_bp.route('/history', methods=['GET'])
@jwt_required()
@role_required('student')
def profile_history():
    user_id = int(get_jwt_identity())
    return success_response(StudentProfileService.history(
        user_id,
        request.args.get('page', 1, type=int),
        request.args.get('page_size', 20, type=int),
    ))


@student_profile_bp.route('/suggestions', methods=['GET'])
@jwt_required()
@role_required('student')
def profile_suggestions():
    return success_response(StudentProfileService.suggestions(
        int(get_jwt_identity()),
        request.args.get('status', 'pending'),
    ))


@student_profile_bp.route('/suggestions/<int:suggestion_id>', methods=['PUT'])
@jwt_required()
@role_required('student')
def resolve_profile_suggestion(suggestion_id):
    try:
        payload = request.get_json() or {}
        return success_response(StudentProfileService.resolve_suggestion(
            int(get_jwt_identity()),
            suggestion_id,
            payload.get('action') or '',
        ))
    except LookupError as exc:
        return error_response(str(exc), 40401, None, 404)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
