"""Four tutoring modes: owned context -> evidence -> action -> validate -> publish."""
import json
import time
from flask import current_app

from app.models import db
from app.services.course_safety import CourseSafetyService, SafetyViolation
from app.services.knowledge import KnowledgeService
from app.services.knowledge.providers.llm import get_llm_provider
from app.services.learner_state import LearnerStateService, fingerprint
from app.services.tutor_context import TutorContextService, TutorContextError, _text
from app.services.tutor_policy import (TeachingPlan, validate_candidate, semantic_review_ok,
    generation_prompt, REVIEW_PROMPT, OutputRejected, ARTIFACT_MODES, semantic_review_failures)
from app.services.tutor_sessions import TutorSessions, uuid_value
from app.services import tutor_runtime as runtime
from app.services.tutor_intents import learning_overview

REQUEST_FIELDS = {'request_id', 'session_id', 'mode', 'hint_level', 'question',
    'question_ref', 'formal_question_id', 'question_version', 'code', 'run_id', 'submission_id'}
NOTICES = {
    'grounded': '已检索到课程材料；引用仅支持标注的说明。',
    'insufficient_evidence': '本次未找到足够课程依据，下面只提供通用帮助。',
    'retrieval_unavailable': '课程检索暂不可用，下面只提供通用帮助。',
    'learning_records': '以下依据你本人的近期学习记录，不将记录变化解释为能力提升的证明。',
    'not_requested': '请先补充当前模式所需的信息。',
}


def missing_context(teaching, context, question):
    if teaching.mode == 'explain_error':
        if not context.code.strip():
            return '请附上产生报错的当前代码，再选择“解释这个报错”。'
        run = context.run
        result = (run or {}).get('result') or {}
        if not run or not (result.get('stderr') or result.get('compile_output') or result.get('errors')):
            return '请先运行当前代码，并附上这次有报错的运行记录。'
    if teaching.mode == 'review_approach' and not (context.code.strip() or question.strip() not in {'', '检查我的思路'}):
        return '请写下你的解题思路，或附上已经尝试的代码。'
    if teaching.mode in {'next_step', 'pseudocode'} and not (context.task or question.strip() or context.code.strip()):
        return '请先说明正在解决的问题和卡住的位置，或打开一道练习题。'
    return None


SHORTCUT_QUESTIONS = frozenset({'解释这个报错', '检查我的思路', '只提示下一步', '用伪代码说明'})


def retrieval_query(question, task):
    """Separate a UI action label from evidence; never expand a real question."""
    if question.strip() and question.strip() not in SHORTCUT_QUESTIONS:
        return question[:3000]
    task = task or {}
    concept = KnowledgeService.concept_detail(task.get('concept_id')) if task.get('concept_id') else None
    return ((concept or {}).get('name') or task.get('title') or question or 'Python 编程概念')[:3000]


def safe_fallback(teaching, context, reason, history):
    """Reviewed fixed instructional templates, never a generated answer excerpt."""
    if teaching.task_policy == 'concept_only':
        return {'summary': '本题仅开放通用概念帮助。', 'next_step': '请说出一个你想核对的编程概念。', 'follow_up': '', 'citations': []}
    if reason == 'repeated_hint' or (teaching.mode == 'next_step' and history):
        return {'summary': '这次未能提供可靠的新提示。',
            'next_step': '请重试当前问题，或请教师帮你核对这次尝试。', 'follow_up': '', 'citations': []}
    actions = {
        'learning_document': '请缩小文档主题或请教师补充课程资料后重试。',
        'knowledge_graph': '请指定一个课程概念，补充课程资料后再生成概念图。',
        'concept_explain': '请指出你希望进一步了解的一个概念或例子。',
        'algorithm_validation': '选一个边界输入，核对你的推理所依赖的条件。',
        'algorithm_trace': '先写出示例输入和程序开始时各变量的值。',
        'explain_error': '从本次报错最后一行找到异常类型，再对照代码中的对应操作。',
        'review_approach': '选一个符合题目约束的小输入，写出你的思路每一步会产生的结果。',
        'next_step': '把当前最不确定的一个条件写出来，并说明你预计它何时成立。',
        'pseudocode': '选出你最不确定的一个局部步骤，用一句话描述它的输入和输出。',
    }
    return {'summary': '这次还没有得到通过全部检查的针对性解释，可以先做一次小范围核对。',
            'next_step': actions[teaching.mode], 'follow_up': '', 'citations': []}


class TutorService:
    @staticmethod
    def ask(user_id, body, *, automatic=False, state_snapshot=None, require_evidence=False, self_test=None):
        if not isinstance(body, dict) or set(body) - REQUEST_FIELDS:
            raise TutorContextError('请求字段不符合辅导接口约定')
        request_id = uuid_value(body.get('request_id'), '请求编号')
        session_id = uuid_value(body['session_id'], '会话编号') if body.get('session_id') is not None else None
        question = _text(body.get('question'), '问题', 8000)
        context = TutorContextService.resolve(user_id, body)
        try:
            if question.strip():
                CourseSafetyService.ensure_safe(question)
        except SafetyViolation:
            raise TutorContextError('请围绕当前编程学习问题提问', 400) from None
        frozen = learner = None
        if isinstance(body.get('mode'), str) and body['mode'] in ARTIFACT_MODES:
            from app.services.resource_learning_context import ResourceLearningContext
            from app.services.knowledge.learner_context_service import LearnerContextService
            frozen = ResourceLearningContext.capture(user_id, (context.task or {}).get('concept_id') or 'general')
            learner = LearnerContextService.from_resource_snapshot(frozen)
            snapshot = frozen['learner_state'] if frozen['state_source'] == 'evidence' else {'state_version': 0, 'concepts': [], 'changes': [], 'misconceptions': []}
        else:
            snapshot = state_snapshot if state_snapshot is not None else LearnerStateService.snapshot(user_id)
        teaching = TeachingPlan.build(context, body.get('mode'), body.get('hint_level', 2), snapshot, automatic=automatic)
        # Unknown fields have been rejected; hash exact input so a retry cannot
        # silently switch code, session, mode or permission-sensitive references.
        digest = fingerprint({'automatic': True, 'request': body}) if automatic else fingerprint(body)
        if require_evidence:
            digest = fingerprint({'digest': digest, 'require_evidence': True})
        if self_test is not None:
            # Internal compatibility hook only: HTTP /tutor/ask rejects this
            # field. Reserve before execution so retries cannot fork live work.
            digest = fingerprint({'digest': digest, 'self_test': self_test})
        claim = TutorSessions.claim(user_id, request_id, session_id, digest, context, question, teaching.mode,
            lease_seconds=180 if self_test is not None else 120)
        if 'cached' in claim:
            return claim['cached']
        claim['retrieval_config_hash'] = fingerprint(runtime.retrieval_config())
        try:
            runtime.checkpoint(claim)
            execution = None
            if self_test is not None:
                from app.services.learning_cycle import execute_self_test
                started = time.perf_counter()
                execution = execute_self_test(user_id, context, self_test)
                execution['latency_ms'] = round((time.perf_counter() - started) * 1000)
                if not TutorContextService.current(user_id, context):
                    raise TutorContextError('执行期间题目或权限已变化，请重新加载', 409)
                refreshed = TutorContextService.resolve(user_id, {**body, 'run_id': execution['run_id'],
                    'question_version': (context.task or {}).get('version')})
                if refreshed.task != context.task:
                    raise TutorContextError('执行期间题目或权限已变化，请重新加载', 409)
                context = refreshed
            tutoring_started = time.perf_counter()
            history = TutorSessions.history(user_id, claim['session_id'])
            missing = missing_context(teaching, context, question)
            evidence = {'status': 'not_requested', 'sources': [], 'prerequisite_gaps': []}
            if teaching.mode == 'learning_overview':
                candidate = learning_overview(user_id, snapshot, question, **(
                    {'decision': teaching.decision, 'allow_counterexample': teaching.task_policy != 'concept_only'} if context.task else {}))
                evidence['status'] = 'learning_records'
                status, reason, generation, count_help = 'ok', None, 'learning_records', False
            elif teaching.mode == 'clarify':
                candidate = {'summary': '你好，我是小 E。可以一起学 Python、核对思路或查看学习记录。',
                    'next_step': '告诉我一个想了解的概念，或附上你卡住的代码。', 'follow_up': '', 'citations': []}
                status, reason, generation, count_help = 'needs_context', 'missing_context', 'none', False
            elif missing:
                candidate = {'summary': '还需要一点上下文，才能按这个方式帮助你。',
                    'next_step': missing, 'follow_up': '', 'citations': []}
                status, reason, generation, count_help = 'needs_context', 'missing_context', 'none', False
            else:
                try:
                    query = retrieval_query(question, context.task)
                    # Free-chat pronouns may refer to an acknowledged example.
                    # Do not pull old topics into a bound task or every short query.
                    if automatic and not context.task and history and any(
                        word in question for word in ('这个例子', '这个示例', '上面的例子', '刚才的示例')):
                        query = (question + '\n' + history[-1]['question'])[:3000]
                    evidence = KnowledgeService.tutor_evidence(query, user_id=user_id, task=context.task, state_snapshot=snapshot,
                        **({'learner_context': learner} if learner is not None else {}))
                except Exception:
                    db.session.rollback()
                    current_app.logger.warning('tutor retrieval unavailable')
                    evidence = {'status': 'retrieval_unavailable', 'sources': [], 'prerequisite_gaps': []}
                if evidence.get('blocked_reason'):
                    raise TutorContextError('请调整为具体的编程学习问题', 400)
                db.session.rollback()  # No database transaction around either model call.
                if require_evidence and evidence['status'] != 'grounded':
                    candidate = {'summary': '本次没有足够课程材料支持回答。',
                        'next_step': '请指出课程知识点，或请教师补充并发布相关材料后重试。', 'follow_up': '', 'citations': []}
                    reason = evidence['status']
                else:
                    runtime.checkpoint(claim)
                    candidate, reason = TutorService.generate(teaching, context, question, evidence, history, user_id=user_id, claim=claim)
                    if require_evidence and reason is None and not candidate.get('citations'):
                        reason = 'missing_course_citation'
                        candidate = safe_fallback(teaching, context, reason, history)
                status, generation = ('ok', 'llm_reviewed') if reason is None else ('safe_fallback', 'rules')
                count_help = reason is None
            runtime.checkpoint(claim)
            used = evidence['sources'] + [s for h in history for s in h.get('evidence_refs', [])]
            dependencies = list({(s['chunk_id'], s['version']): s for s in used}.values())
            if not TutorContextService.current(user_id, context) or not KnowledgeService.tutor_sources_current(user_id, dependencies):
                raise TutorContextError('题目、权限或课程材料已变化，请重新加载后再提问', 409)
            response = {'mode': teaching.mode, **candidate, 'status': status,
                'evidence_status': evidence['status'], 'evidence_notice': NOTICES[evidence['status']],
                'state_version': teaching.state_version, 'teaching_plan': teaching.public(),
                'context': context.public(), 'generation_mode': generation,
                'policy_result': {'version': teaching.policy_version, 'status': status,
                    'reason': reason, 'checks': (['owned_learning_records'] if generation == 'learning_records' else ['schema', 'line_bounds', 'citation_allowlist', 'semantic_review']) if reason is None else []}}
            if status == 'ok' and teaching.mode == 'next_step' and teaching.task_policy != 'concept_only':
                from app.services.counterexample_recommendation import recommend
                response['counterexample_pick'] = recommend(user_id, teaching.decision)
            if reason == 'semantic_review_failed':
                response['policy_result']['review_failures'] = claim.get('review_failures', ['invalid_review'])
            if teaching.mode == 'algorithm_trace' and (context.run or {}).get('kind') == 'trace':
                recorded = (context.run.get('result') or {}).get('trace')
                if recorded:
                    response['execution_trace'] = recorded
                    response['trace_notice'] = '模型说明不等同于执行记录；请对照服务器保存的逐行轨迹，变量值为该行执行前的快照。'
            if frozen is not None:
                response['timing'] = {'tutoring_ms': round((time.perf_counter() - tutoring_started) * 1000)}
                response['learning_context'] = {'state_source': frozen['state_source'],
                    'profile_version': frozen['profile_version'], 'state_version': teaching.state_version}
            if execution is not None:
                response['self_test_execution'] = execution
                response['timing'] = {'execution_ms': execution['latency_ms'],
                    'tutoring_ms': round((time.perf_counter() - tutoring_started) * 1000)}
            return TutorSessions.finish(user_id, claim, response, context, count_help=count_help and teaching.mode not in ARTIFACT_MODES, dependencies=dependencies,
                track_display=automatic and teaching.mode not in ARTIFACT_MODES)
        except Exception:
            TutorSessions.fail(claim)
            raise
        finally:
            db.session.rollback()
            runtime.settle(claim)

    @staticmethod
    def generate(teaching, context, question, evidence, history, *, user_id, claim):
        reason = 'model_unavailable'
        if current_app.config.get('TUTOR_MODELS_ENABLED', not current_app.testing):
            provider = get_llm_provider()
            if provider.available():
                # The model never receives answer keys, hidden tests, age or raw profile.
                task = context.task
                from app.services.python_trace import for_tutor
                code, run = context.code, for_tutor(context.run)
                if teaching.task_policy == 'concept_only':
                    task = {'concept_id': (task or {}).get('concept_id')}
                    code, run = '', None
                payload = {'teaching_plan': teaching.public(), 'task': task,
                    'student_question': question, 'student_code': code, 'execution': run,
                    'formal_result': context.formal_result if teaching.task_policy != 'concept_only' else None,
                    'evidence_status': evidence['status'], 'materials': [{k:v for k,v in s.items() if k != 'content_hash'} for s in evidence['sources']],
                    'learning_preferences': evidence.get('learning_preferences', {}),
                    'prerequisite_gaps': evidence.get('prerequisite_gaps', []),
                    'displayed_history': [{k:v for k,v in h.items() if k != 'evidence_refs'} for h in history]}
                try:
                    raw = runtime.model_call(user_id, claim, teaching, 'generation', lambda: provider.generate_json(system=generation_prompt(teaching),
                        user=json.dumps(payload, ensure_ascii=False), max_tokens=2400 if teaching.mode in ARTIFACT_MODES else 1300, timeout=30 if teaching.mode in ARTIFACT_MODES else 22))
                    candidate = validate_candidate(raw, teaching, context, evidence['sources'], history)
                    review = runtime.model_call(user_id, claim, teaching, 'review', lambda: provider.generate_json(system=REVIEW_PROMPT,
                        user=json.dumps({'context': payload, 'candidate': candidate}, ensure_ascii=False), max_tokens=220, timeout=12))
                    if not semantic_review_ok(review):
                        # Persist only fixed diagnostic categories, never rejected text.
                        claim['review_failures'] = semantic_review_failures(review)
                        raise OutputRejected('semantic_review_failed')
                    # No material citation means the generated explanation is general,
                    # even when retrieval itself had relevant evidence.
                    return candidate, None
                except TutorContextError:
                    raise
                except OutputRejected as exc:
                    reason = str(exc)
                except Exception:
                    reason = 'model_unavailable'
        return safe_fallback(teaching, context, reason, history), reason
