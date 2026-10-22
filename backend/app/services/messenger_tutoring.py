"""Free questions use the same owned sessions, evidence and reviewed publication."""
import time
import uuid

from app.services.course_safety import CourseSafetyService
from app.services.tutor_context import TutorContextService, TutorContextError, _text
from app.services.tutor_intents import infer_mode
from app.services.tutor_sessions import uuid_value
from app.services.tutor_compat import response_text
from app.services.tutoring import TutorService
from app.services.llm_stream import chunk_text

FIELDS = {'message', 'content', 'history', 'messages', 'request_id', 'session_id',
          'code', 'run_id', 'submission_id', 'question_ref', 'formal_question_id', 'question_version'}


class MessengerTutoring:
    @staticmethod
    def prepare(user_id, body):
        if not isinstance(body, dict) or set(body) - FIELDS:
            raise TutorContextError('对话请求字段不正确')
        if 'message' in body and 'content' in body and body['message'] != body['content']:
            raise TutorContextError('message 与 content 不一致')
        question = _text(body.get('message', body.get('content')), '消息', 8000).strip()
        if not question:
            raise TutorContextError('消息不能为空')
        CourseSafetyService.ensure_safe(question, enforce_course_scope=True)
        payload = {k: body[k] for k in FIELDS - {'message', 'content', 'history', 'messages'} if k in body}
        context = TutorContextService.resolve(user_id, payload)
        # 'history/messages' are accepted for older clients but are never read.
        payload.update(question=question, mode=infer_mode(question, context.code), hint_level=2)
        if 'request_id' not in payload:
            payload['question_version'] = (context.task or {}).get('version')
            payload['request_id'] = str(uuid.uuid4())
        uuid_value(payload['request_id'], '请求编号')
        if payload.get('session_id') is not None:
            uuid_value(payload['session_id'], '会话编号')
        # Match the ordinary tutor's policy before opening SSE. Authoritative
        # context is resolved again by ask, including after transport setup.
        if (context.task or {}).get('tutoring_policy') == 'disabled':
            raise TutorContextError('本次任务暂未开放小 E 辅导，请按教师要求独立完成', 403)
        return payload

    @staticmethod
    def answer(user_id, payload, *, state_snapshot=None):
        tutor = TutorService.ask(user_id, payload, automatic=True, state_snapshot=state_snapshot)
        return {'reply': response_text(tutor), 'tutor': tutor, 'request_id': tutor['request_id'],
                'session_id': tutor['session_id'], 'display_receipt_id': tutor['display_receipt_id'],
                'source': tutor['generation_mode'], 'state_version': tutor['state_version'],
                'learning_decision': tutor['teaching_plan']['decision'],
                'recommendations': [], 'rag_used': tutor['evidence_status'] == 'grounded',
                'question_pick': tutor.get('question_pick')}

    @staticmethod
    def stream(user_id, payload):
        started = time.monotonic()
        yield {'type': 'stage', 'stage': 'context', 'label': '核对上下文与学习记录'}
        yield {'type': 'stage', 'stage': 'review', 'label': '组织回答并检查依据'}
        result = MessengerTutoring.answer(user_id, payload)
        elapsed = round((time.monotonic() - started) * 1000)
        # Only reviewed/safe fixed content is segmented. No model draft delta.
        for piece in chunk_text(result['reply']):
            yield {'type': 'delta', 'text': piece}
        yield {'type': 'done', **result, 'thinking': [],
               'latency': {'generation_ms': elapsed, 'first_token_ms': elapsed}}
