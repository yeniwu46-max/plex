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
from app.services.student_profile import (
    DIMENSION_LABELS,
    ProfileRecalibrationUnavailable,
    StudentProfileService,
)
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


def _profile_reply_stream(message: str, result: dict, history=None, profile: dict | None = None):
    """基于抽取结果流式生成自然语言确认回复；无 LLM 时伪流式输出既有文案。"""
    history_rows = []
    if isinstance(history, list):
        for item in history[-12:]:
            if not isinstance(item, dict):
                continue
            role = item.get('role')
            if role not in ('user', 'assistant'):
                continue
            content = str(item.get('content') or item.get('text') or '').strip()
            if content:
                history_rows.append({'role': role, 'content': content[:400]})

    proposed = result.get('proposed_changes') or []
    filled_dims = []
    if profile and isinstance(profile.get('dimensions'), dict):
        for key, dim in profile['dimensions'].items():
            if (dim or {}).get('value'):
                filled_dims.append(DIMENSION_LABELS.get(key, key))

    missing_hint = '、'.join(
        label for key, label in DIMENSION_LABELS.items()
        if key != 'cognitive_state' and label not in filled_dims
    ) or '学习偏好与节奏'

    system = (
        '你是 A3 个性化学习系统的画像助手小E。你的任务是通过引导式对话收集学生学习画像。'
        '每次回复：先用 1-2 句回应学生刚说的话；然后只问 1 个具体、好回答的追问，'
        f'优先补齐尚未明确的维度（如 {missing_hint}）。'
        '语气像学习伙伴，80-140 字，可用 Markdown 列表。'
        '不要一次性问多个问题，不要提及模型、接口或供应商。'
    )
    transcript = '\n'.join(
        f'{"学生" if row["role"] == "user" else "小E"}：{row["content"]}'
        for row in history_rows
    )
    user = f'对话记录：\n{transcript or "（首次对话）"}\n\n学生最新一句：{message[:300]}'
    if proposed:
        summary = '\n'.join(
            f"- {item.get('label')}：{item.get('new_value')}"
            for item in proposed[:5]
        )
        user += f'\n\n后台已抽取（可在回复中自然提及，勿逐条念置信度）：\n{summary}'

    for provider in stream_provider_chain('profile'):
        emitted = False
        collected: list[str] = []
        try:
            for delta in iter_openai_stream(provider, [
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user},
            ], max_tokens=360, timeout=(3, 20)):
                emitted = True
                collected.append(delta)
                yield {'type': 'delta', 'text': delta}
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning('profile stream provider failed: %s', exc)
            if not emitted:
                continue
        if emitted:
            result['assistant_reply'] = ''.join(collected).strip()
            return

    fallback = (result.get('assistant_reply') or '').strip()
    if not fallback:
        fallback = (
            '我先记下了你的话。可以再补充专业背景、学习目标或节奏偏好，'
            '我会继续完善画像。'
        )
        result['assistant_reply'] = fallback
    for piece in chunk_text(fallback):
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
    history = payload.get('history') or payload.get('messages') or []
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
            profile_snapshot = quick.get('profile')
            for event in _profile_reply_stream(message, quick, history, profile_snapshot):
                if event.get('type') == 'delta':
                    yield sse_event(event)

            # 2) 短超时 LLM enrichment；用线程硬超时，绝不让 SSE 挂死
            yield sse_event({'type': 'stage', 'stage': 'merging', 'label': '补充画像细节并刷新卡片'})
            result = quick
            try:
                from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

                def _enrich():
                    return StudentProfileService.chat(
                        user_id,
                        message,
                        confirm_changes,
                        skip_llm=False,
                        llm_timeout=4.0,
                    )

                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(_enrich)
                    try:
                        enriched = future.result(timeout=5.5)
                    except FuturesTimeout:
                        future.cancel()
                        raise TimeoutError('profile enrichment timed out')
                result = enriched
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


@student_profile_bp.route('/recalibrate', methods=['POST'])
@jwt_required()
@role_required('student')
def recalibrate_profile():
    """Use a real model response as the gate before updating the student profile."""
    try:
        user_id = int(get_jwt_identity())
        payload = request.get_json() or {}
        return success_response(StudentProfileService.recalibrate(
            user_id,
            payload.get('changes') or {},
        ))
    except SafetyViolation as exc:
        return error_response(str(exc), 40012, {'reason_code': exc.reason_code}, 400)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except ProfileRecalibrationUnavailable as exc:
        return error_response(str(exc), 50321, None, 503)


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
