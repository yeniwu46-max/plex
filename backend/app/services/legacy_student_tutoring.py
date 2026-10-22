"""Student adapters for legacy agent/RAG APIs; no caller-supplied evidence."""
import time
import uuid

from app.models import db
from app.models.tutor_session import TutorTurn
from app.services.tutor_compat import _alias, response_text
from app.services.tutor_context import TutorContextService, TutorContextError, _text
from app.services.tutor_intents import infer_mode
from app.services.tutoring import TutorService


def prepare(user_id, body, entry, *, default_question='', mode=None):
    if not isinstance(body, dict):
        raise TutorContextError('请求体必须是 JSON 对象')
    question = _alias(body, 'question', 'userQuestion')
    for key in ('query', 'message'):
        if key in body:
            if question is not None and question != body[key]:
                raise TutorContextError('问题字段不一致')
            question = body[key]
    question = _text(question, '问题', 8000).strip() or default_question
    code = _text(body.get('code'), '代码', 65536)
    payload = {'question': question, 'code': code, 'mode': mode or infer_mode(question, code),
               'hint_level': _alias(body, 'hint_level', 'hintLevel', 2)}
    raw_context = body.get('context')
    if raw_context is not None and not isinstance(raw_context, dict):
        raise TutorContextError('context 必须是 JSON 对象')
    nested = raw_context or {}
    for snake, camel in [('question_ref', 'exerciseId'), ('formal_question_id', 'formalQuestionId'),
                         ('question_version', 'questionVersion'), ('run_id', 'runId'),
                         ('session_id', 'sessionId'), ('request_id', 'requestId')]:
        value = _alias(body, snake, camel)
        if snake in nested:
            if value is not None and value != nested[snake]:
                raise TutorContextError(f'{snake} 与 context 不一致')
            value = nested[snake]
        if value is not None:
            payload[snake] = value
    # A numeric problem_id identifies the server question bank, not a formal
    # trial question. An unspecified trial/task ID cannot silently become an
    # unrestricted autonomous question.
    problem = body.get('problem_id', nested.get('problem_id'))
    if 'problem_id' in body and 'problem_id' in nested and body['problem_id'] != nested['problem_id']:
        raise TutorContextError('problem_id 与 context 不一致')
    if problem is not None:
        if isinstance(problem, bool) or not str(problem).isdigit():
            raise TutorContextError('problem_id 无效')
        reference = f'bank-{int(problem)}'
        if payload.get('question_ref', reference) != reference:
            raise TutorContextError('problem_id 与题目引用不一致')
        payload['question_ref'] = reference
    if not (payload.get('question_ref') or payload.get('formal_question_id')) and any(
        body.get(key) is not None or nested.get(key) is not None for key in ('trial_id', 'task_id')
    ):
        raise TutorContextError('请提供明确的 question_ref 或 formal_question_id')
    context = TutorContextService.resolve(user_id, payload)
    if 'request_id' not in payload:
        payload['question_version'] = (context.task or {}).get('version')
        payload['request_id'] = str(uuid.uuid4())
    return payload


def common(tutor):
    row = db.session.get(TutorTurn, tutor['request_id'])
    return {'tutor': tutor, 'request_id': tutor['request_id'], 'session_id': tutor['session_id'],
        'display_receipt_id': tutor['display_receipt_id'], 'state_version': tutor['state_version'],
        'backend': tutor['generation_mode'],
        'completed_at': row.completed_at.isoformat() + 'Z' if row and row.completed_at else None}


def feedback_view(tutor):
    return {**common(tutor), 'diagnosis': {'weakPoints': [], 'errorType': 'unverified',
            'diagnosis': tutor['summary'], 'confidence': None},
        'codeAnalysis': {'codeIssueSummary': tutor['summary'], 'possibleCause': '', 'fixDirection': tutor['next_step'], 'relatedConcepts': []},
        'graphInsight': {'relatedNodes': [], 'prerequisiteNodes': [], 'recommendedReviewNodes': [], 'graphReason': ''},
        'recommendation': {'nextKnowledgePoint': '', 'recommendedExercises': [], 'reviewPlan': [], 'estimatedDifficulty': ''},
        'feedback': {'shortFeedback': response_text(tutor), 'stepHints': [tutor['next_step']], 'encouragement': '', 'nextAction': tutor['next_step']},
        'pipelineTrace': []}


class LegacyStudentTutoring:
    @staticmethod
    def agent(user_id, body, entry):
        if not isinstance(body, dict):
            raise TutorContextError('请求体必须是 JSON 对象')
        if entry == 'analyze-code' and not _text(body.get('code'), '代码', 65536).strip():
            raise TutorContextError('code required')
        overview = entry in {'recommend-path', 'diagnose-learning'} or (entry == 'diagnose' and not body.get('code'))
        mode = 'learning_overview' if overview else ('review_approach' if body.get('code') else 'clarify')
        default = '请根据我的学习记录建议复习路径' if entry == 'recommend-path' else '请查看我最近的学习记录与薄弱点' if overview else ''
        payload = prepare(user_id, body, entry, default_question=default, mode=mode)
        tutor = TutorService.ask(user_id, payload, automatic=True)
        shared = common(tutor)
        text = response_text(tutor)
        if entry == 'diagnose-learning':
            return feedback_view(tutor)
        if entry == 'diagnose':
            return {**shared, 'agent': 'LearningDiagnosisAgent', 'status': 'completed', 'weak_points': [],
                'error_types': [], 'overall_assessment': text, 'confidence': None, 'diagnosed_at': shared['completed_at']}
        if entry == 'recommend-path':
            decision = tutor['teaching_plan']['decision']
            steps = [{'step': 1, 'node': decision['concept_id'], 'action': tutor['next_step']}]
            return {**shared, 'agent': 'LearningPathAgent', 'status': 'completed',
                'path': {'title': '基于本人学习记录的下一步', 'steps': steps, 'total_nodes': len(steps)},
                'ordered_nodes': [], 'next_best_action': {'node_id': decision['concept_id'], 'action': tutor['next_step'], 'reason': decision['reason']},
                'remediation_paths': [], 'confidence': None, 'recommended_at': shared['completed_at']}
        if entry == 'analyze-code':
            analysis = {'codeIssueSummary': tutor['summary'], 'possibleCause': '', 'fixDirection': tutor['next_step'], 'relatedConcepts': []}
            return {**shared, 'agent': 'CodeAnalysisAgent', 'status': 'completed', 'error_type': 'unverified',
                'explanation': text, 'suggestions': [tutor['next_step']], 'code_analysis': analysis,
                'analyzed_at': shared['completed_at']}
        return {**shared, 'agent': 'FeedbackAgent', 'status': 'completed',
            'feedback': {'summary': text, 'encouragement': '', 'next_action': tutor['next_step'], 'step_hints': [tutor['next_step']]},
            'generated_at': shared['completed_at']}

    @staticmethod
    def rag(user_id, body):
        started = time.perf_counter()
        payload = prepare(user_id, body, 'rag-query')
        if payload['mode'] in {'clarify', 'learning_overview'}:
            payload['mode'] = 'concept_explain'
        tutor = TutorService.ask(user_id, payload, automatic=True, require_evidence=True)
        grounded = tutor['status'] == 'ok' and tutor['evidence_status'] == 'grounded' and bool(tutor['citations'])
        concepts = list(dict.fromkeys(cid for s in tutor['citations'] for cid in s.get('concept_ids', [])))
        return {**common(tutor), 'answer': response_text(tutor),
            'concepts': [{'concept_id': cid, 'name': cid, 'node_type': 'concept', 'role': 'focus', 'mastery_status': None} for cid in concepts],
            'sources': tutor['citations'], 'confidence': None,
            'confidence_level': 'UNASSESSED' if grounded else 'LOW_CONFIDENCE', 'knowledge_grounded': grounded,
            'teaching_strategy': {'strategies': [], 'mastery_band': 'unknown', 'style': '',
                'practice_mode': tutor['teaching_plan']['task_policy'] != 'autonomous',
                'hint_level': tutor['teaching_plan']['hint_level'], 'hint_max_level': tutor['teaching_plan']['hint_level'], 'hint_name': None},
            'recommended_next': [], 'hint_level': tutor['teaching_plan']['hint_level'], 'intent': tutor['mode'],
            'generation_mode': 'llm_reviewed' if grounded else 'refused',
            'latency_ms': round((time.perf_counter() - started) * 1000), 'log_id': None}
