"""Old student endpoints are projections of the reviewed tutor contract.

Browser verdicts, task descriptions, identities and conversation histories are
deliberately not forwarded. New callers should use /student/tutor/ask directly.
"""
import uuid

from app.services.tutor_context import TutorContextService, TutorContextError, _text, _version
from app.services.tutoring import TutorService


def _alias(body, snake, camel, default=None):
    if snake in body and camel in body and body[snake] != body[camel]:
        raise TutorContextError(f'{snake} 与 {camel} 不一致')
    return body.get(snake, body.get(camel, default))


def _intent(body):
    intent = body.get('intent')
    if intent is None or intent == '':
        question = _text(_alias(body, 'question', 'userQuestion'), '问题', 8000)
        if any(term in question for term in ('优化', '复杂度', '效率')):
            return 'optimization'
        if any(term in question for term in ('报错', '异常')):
            return 'error_diagnosis'
        return 'custom'
    if not isinstance(intent, str) or intent not in {'error_diagnosis', 'code_quality', 'optimization', 'custom'}:
        raise TutorContextError('不支持的辅导类型')
    return intent


def response_text(tutor):
    lines = [tutor['summary']]
    if tutor.get('records_at'):
        lines.append('记录截至：' + tutor['records_at'])
    lines += [f"第 {a['line']} 行：{a['message']}" for a in tutor.get('annotations', [])]
    if tutor.get('example'):
        lines += ['示例（未执行）：', tutor['example']['code'], tutor['example']['explanation']]
    if tutor.get('trace_steps'):
        lines += [tutor['trace_notice'], '示例输入：' + tutor['trace_input'], *tutor['trace_steps']]
    if tutor.get('pseudocode_lines'):
        lines += [f"{row['step']} — {row['explanation']}" for row in tutor['pseudocode_lines']]
    if tutor['next_step']:
        lines += [f"下一步：{tutor['next_step']}"]
    if tutor.get('follow_up'):
        lines.append(tutor['follow_up'])
    lines.append(tutor['evidence_notice'])
    lines += [f"来源：{s.get('title') or s.get('document_title') or '课程材料'} · v{s['version']}（{s['supports']}）"
              for s in tutor['citations']]
    return '\n\n'.join(lines)


class TutorCompatibility:
    @staticmethod
    def ask(user_id, body, endpoint):
        if not isinstance(body, dict):
            raise TutorContextError('请求体必须是 JSON 对象')
        code = _text(body.get('code'), '代码', 65536)
        if endpoint != 'trial-coach' and not code.strip():
            raise TutorContextError('code required')
        intent = _intent(body) if endpoint == 'trial-coach' else None
        mode = ({'error_diagnosis': 'explain_error', 'code_quality': 'review_approach',
                 'optimization': 'review_approach', 'custom': 'next_step'}[intent]
                if intent else ('next_step' if endpoint == 'code-hint' else 'review_approach'))
        question = _text(_alias(body, 'question', 'userQuestion'), '问题', 8000)
        if not question and intent == 'optimization':
            question = '请检查我已经写出的思路中需要核对的复杂度问题。'
        payload = {
            'code': code, 'mode': mode, 'question': question,
            'hint_level': _alias(body, 'hint_level', 'hintLevel', 2),
        }
        for snake, camel in [('question_ref', 'exerciseId'), ('formal_question_id', 'formalQuestionId'),
                             ('question_version', 'questionVersion'), ('run_id', 'runId'),
                             ('session_id', 'sessionId'), ('request_id', 'requestId')]:
            value = _alias(body, snake, camel)
            if value is not None:
                payload[snake] = value
        # Legacy clients have no UUID. Stable, owner-scoped identities prevent
        # network retries from producing multiple replies/receipts. Bind to the
        # resolved task version; a changed task cannot reuse an old answer.
        if 'request_id' not in payload:
            context = TutorContextService.resolve(user_id, payload)
            payload['question_version'] = (context.task or {}).get('version')
            payload['request_id'] = str(uuid.UUID(hex=_version(['tutor-compat-v1', user_id, endpoint, payload])[:32]))
        tutor = TutorService.ask(user_id, payload)
        common = {'tutor': tutor, 'context': tutor['context'], 'request_id': tutor['request_id'],
                  'session_id': tutor['session_id'], 'display_receipt_id': tutor['display_receipt_id'],
                  'state_version': tutor['state_version'], 'backend': tutor['generation_mode']}
        if endpoint == 'trial-coach':
            return {**common, 'agentId': 'trial_custom_coach' if intent == 'custom' else f'trial_{intent}',
                    'agentName': '小E', 'intent': intent, 'contextSummary': tutor['summary'],
                    'response': response_text(tutor), 'guidingQuestions': [tutor['follow_up']] if tutor['follow_up'] else [],
                    'strengths': [], 'improvements': [tutor['next_step']], 'policy': 'no_direct_answer',
                    'hintLevel': tutor['teaching_plan']['hint_level']}
        if endpoint == 'code-hint':
            # Never insert model text into executable source (including comments
            # containing line breaks); old callers can display comments separately.
            return {**common, 'annotated_code': code,
                    'comments': [tutor['summary'], tutor['next_step'], tutor['evidence_notice']],
                    'policy': 'hint_only_no_direct_answer'}
        # Keep legacy panel keys, without fabricating diagnosis confidence,
        # proficiency, mastered concepts, or a verdict from client test results.
        return {**common, 'diagnosis': {'weakPoints': [], 'errorType': 'unverified',
                    'diagnosis': tutor['summary'], 'confidence': None},
                'codeAnalysis': {'codeIssueSummary': tutor['summary'], 'possibleCause': '',
                    'fixDirection': tutor['next_step'], 'relatedConcepts': []},
                'graphInsight': {'relatedNodes': [], 'prerequisiteNodes': [], 'recommendedReviewNodes': [], 'graphReason': ''},
                'recommendation': {'nextKnowledgePoint': '', 'recommendedExercises': [], 'reviewPlan': [], 'estimatedDifficulty': ''},
                'feedback': {'shortFeedback': response_text(tutor), 'stepHints': [tutor['next_step']],
                    'encouragement': '', 'nextAction': tutor['next_step']}, 'pipelineTrace': []}
