"""Resolve task authority independently of browser-provided descriptions/verdicts.

Only this service creates the context consumed by tutoring. Model-facing data is
allowlisted: no answer key, hidden tests, reference solution or arbitrary history.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import uuid
from dataclasses import dataclass

from flask import current_app
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.coding_question_bank import CODING_QUESTION_BANK
from app.models import db, User, Trial, TrialQuestion, TrialQuestionProgress, Problem
from app.models.tutor_context import TutorCodeRun
from app.services.code_execution import CodeExecutionService
from app.utils.time import utc_now


class TutorContextError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def code_hash(code):
    return hashlib.sha256(code.encode('utf-8')).hexdigest()


def _version(value):
    # An unkeyed digest containing a multiple-choice answer is guessable. Keep
    # versions opaque while invalidating when either public or grading data changes.
    key = str(current_app.config['SECRET_KEY']).encode('utf-8')
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode('utf-8')
    return hmac.new(key, raw, hashlib.sha256).hexdigest()


def _text(value, field, limit, *, default=''):
    if value is None:
        return default
    try:
        size = len(value.encode('utf-8')) if isinstance(value, str) else limit + 1
    except UnicodeError:
        raise TutorContextError(f'{field} 包含无效的 Unicode 字符') from None
    if not isinstance(value, str) or size > limit:
        raise TutorContextError(f'{field} 格式不正确或长度超限')
    return value


@dataclass
class TutorContext:
    task: dict | None
    code: str
    code_hash: str
    run: dict | None
    formal_result: dict | None
    local_ref: str | None = None

    @property
    def ref(self):
        return (self.task or {}).get('ref') or self.local_ref

    def public(self):
        return {'task': self.task, 'code_hash': self.code_hash,
                'code_lines': len(self.code.splitlines()), 'run': self.run,
                'formal_result': self.formal_result,
                'task_source': 'server' if self.task else ('browser_only' if self.local_ref else 'none'),
                'local_ref': self.local_ref,
                'execution_note': '运行记录仅证明本次执行；自测用例不代表正式判题或已掌握。'}


class TutorContextService:
    @staticmethod
    def student(user_id, session):
        user = session.get(User, user_id)
        if not user or user.status != 'active' or not user.role or user.role.name != 'student':
            raise TutorContextError('仅当前有效学生账号可使用辅导', 403)
        return user

    @staticmethod
    def formal(question_id, user, session):
        question = session.get(TrialQuestion, question_id)
        trial = session.get(Trial, question.trial_id) if question else None
        now = utc_now()
        visible = bool(trial and user.class_id and trial.class_id == user.class_id
                       and trial.status in {'running', 'ended', 'scheduled'})
        if visible and trial.status != 'ended':
            visible = bool(trial.starts_at is None or trial.starts_at <= now)
            if trial.status == 'scheduled' and trial.starts_at is None:
                visible = False
        if not visible:
            raise TutorContextError('题目不存在或尚未向你开放', 404)
        ended = trial.status == 'ended' or bool(trial.ends_at and trial.ends_at <= now)
        policy = trial.tutoring_policy
        if policy == 'auto':
            policy = ('disabled' if not ended and trial.trial_type not in {'solo', 'team'} else 'guided')
        if policy not in {'disabled', 'concept_only', 'guided'}:
            policy = 'disabled'  # Unknown task policies never grant extra help.
        task = {'ref': f'lc-{question.id}', 'title': question.stem[:120], 'prompt': question.stem,
                'question_type': question.question_type, 'options': question.options or [],
                'concept_id': question.knowledge_key, 'formal_question_id': question.id,
                'tutoring_policy': policy, 'max_hint_level': 0 if policy == 'disabled' else (1 if policy == 'concept_only' else 2)}
        task['version'] = _version([task, question.correct_index, question.coding_meta(), trial.id])
        return task

    @staticmethod
    def task(user_id, ref=None, formal_id=None, *, session=None):
        session = session if session is not None else db.session
        user = TutorContextService.student(user_id, session)
        if formal_id is not None:
            if type(formal_id) is not int or formal_id <= 0:
                raise TutorContextError('正式题目编号无效')
            task = TutorContextService.formal(formal_id, user, session)
            # A workspace may use a bank alias for a formal task; the formal
            # identifier is authoritative and the unrelated browser alias ignored.
            return task
        ref = _text(ref, '题目引用', 100).strip()
        if not ref:
            return None
        if ref.startswith('lc-') and ref[3:].isdigit():
            return TutorContextService.formal(int(ref[3:]), user, session)
        if ref.startswith('bank-') and ref[5:].isdigit():
            problem = session.get(Problem, int(ref[5:]))
            if not problem or not problem.is_active or problem.needs_review:
                raise TutorContextError('题目不存在或尚未开放', 404)
            if problem.source_kind == 'trial_question':
                source = (problem.source_ref or '').removeprefix('trial_questions:')
                if not source.isdigit():
                    raise TutorContextError('题目来源尚待核对', 404)
                return TutorContextService.formal(int(source), user, session)
            task = {'ref': f'bank-{problem.id}', 'title': problem.title_cn,
                    'prompt': '\n'.join(filter(None, [problem.description_cn, problem.input_format_cn, problem.output_format_cn])),
                    'question_type': problem.question_type, 'options': problem.options_json or [],
                    'concept_id': problem.kg_node_id, 'formal_question_id': None,
                    'tutoring_policy': 'guided', 'max_hint_level': 2}
            task['version'] = _version([task, problem.test_cases_json, problem.correct_index, problem.reference_answer, problem.updated_at])
            return task
        alias = session.scalar(select(Problem.id).where(
            (Problem.problem_no == ref.upper()) |
            ((Problem.source_kind == 'frontend_static') & (Problem.source_ref == f'pythonTrialQuestions:{ref}'))
        ).order_by(Problem.id).limit(1))
        if alias is not None:
            return TutorContextService.task(user_id, f'bank-{alias}', session=session)
        from app.services.practice_question import PracticeQuestionService
        for item in CODING_QUESTION_BANK:
            if ref in {item.get('id'), PracticeQuestionService._code_for_builtin(item)}:
                task = {'ref': item['id'], 'title': item.get('title') or item['stem'][:120],
                        'prompt': item['stem'], 'question_type': 'coding', 'options': [],
                        'concept_id': item.get('knowledge_key'), 'formal_question_id': None,
                        'tutoring_policy': 'guided', 'max_hint_level': 2}
                task['version'] = _version([task, item])
                return task
        # Existing front-end-only template exercises are not authoritative tasks.
        # Keep their self-test runner usable, but never import their description,
        # hidden tests or verdict as server-owned context. Bind runs to the local
        # reference solely to prevent accidental reuse across UI exercises.
        if re.fullmatch(r'(?:gen-|class-hard-|mock-)[a-zA-Z0-9_-]{1,80}', ref):
            return None
        raise TutorContextError('题目不存在或尚未开放', 404)

    @staticmethod
    def resolve(user_id, body, *, session=None):
        if not isinstance(body, dict):
            raise TutorContextError('请求体必须是 JSON 对象')
        session = session if session is not None else db.session
        attempt = None
        if body.get('submission_id'):
            from app.models.student_practice import PracticeAttempt
            attempt = session.get(PracticeAttempt, str(body['submission_id']))
            if not attempt or attempt.user_id != user_id:
                raise TutorContextError('作答记录不存在', 404)
            body = {**body, 'question_ref': attempt.question_ref, 'question_version': attempt.question_version}
            body.pop('formal_question_id', None)
            body.setdefault('code', attempt.code)
        task = TutorContextService.task(user_id, body.get('question_ref'), body.get('formal_question_id'), session=session)
        if task:
            from app.models.student_practice import MockExam
            active = session.scalar(select(MockExam).where(MockExam.user_id == user_id, MockExam.status == 'active'))
            if active and any(p['task']['ref'] == task['ref'] for p in active.questions):
                task = {**task, 'tutoring_policy': 'disabled', 'max_hint_level': 0}

        local_ref = ((body.get('question_ref') or '').strip() or None) if not task else None
        if body.get('question_version') and (not task or body['question_version'] != task['version']):
            raise TutorContextError('题目已更新，请重新载入题目后再提问', 409)
        code = _text(body.get('code'), '代码', 65536)
        digest = code_hash(code)
        run = None
        if body.get('run_id') is not None:
            rid = _text(body['run_id'], '运行引用', 36)
            row = session.get(TutorCodeRun, rid)
            if not row or row.user_id != user_id:
                raise TutorContextError('运行记录不存在', 404)
            if row.code_hash != digest or row.question_ref != ((task or {}).get('ref') or local_ref) or row.question_version != (task or {}).get('version'):
                raise TutorContextError('运行记录对应旧代码或其他题目，请重新运行或移除该记录', 409)
            run = {'id': row.id, 'kind': row.execution_kind, 'evidence_scope': 'self_test',
                   'backend': row.backend, 'created_at': row.created_at.isoformat(),
                   'code_normalized': row.code_hash != row.normalized_code_hash,
                   'result': row.result}
        formal = None
        if task and task['formal_question_id']:
            progress = session.scalar(select(TrialQuestionProgress).where(
                TrialQuestionProgress.user_id == user_id,
                TrialQuestionProgress.question_id == task['formal_question_id']))
            from app.models.learner_state import LearningEvent
            from app.services.learner_state import fingerprint
            question = session.get(TrialQuestion, task['formal_question_id'])
            event = session.scalar(select(LearningEvent).where(
                LearningEvent.user_id == user_id, LearningEvent.kind == 'submission_graded',
                LearningEvent.source_type == 'trial_question_progress',
                LearningEvent.source_id == str(progress.id if progress else ''),
            ).limit(1))
            evidence = event.payload if event else {}
            current_version = fingerprint([question.stem, question.correct_index, question.coding_meta(), question.knowledge_key])
            if (progress and progress.status == 'completed' and progress.submitted_code
                    and code_hash(progress.submitted_code) == digest
                    and evidence.get('question_version') == current_version
                    and evidence.get('code_hash') == fingerprint(code)):
                # No hidden expected values, test inputs or exception traces from
                # formal tests enter tutoring. A verdict is not a causal diagnosis.
                formal = {'evidence_scope': 'server_graded', 'passed': bool(progress.code_passed),
                          'at': progress.answered_at.isoformat() if progress.answered_at else None}
        if attempt:
            formal = {'evidence_scope': 'server_graded', 'passed': bool(attempt.result.get('all_passed', attempt.result.get('code_passed', attempt.result.get('correct', False)))), 'at': attempt.created_at.isoformat()} if code == attempt.code else None
        return TutorContext(task, code, digest, run, formal, local_ref)

    @staticmethod
    def legacy_payload(context, body):
        """Temporary adapter until all coach consumers use TutorResponse.

        Browser history/verdicts are deliberately not merged back in. Free text
        remains student input; it never sets authoritative context fields.
        """
        task = context.task or {}
        if task.get('tutoring_policy') == 'disabled':
            raise TutorContextError('本次任务暂未开放小 E 辅导，请按教师要求独立完成', 403)
        if task.get('tutoring_policy') == 'concept_only':
            # The old coach cannot enforce concept-only output structurally.
            # Fail closed until the new teaching-plan service is connected.
            raise TutorContextError('本题仅开放概念帮助，请在小 E 中询问通用概念', 403)
        requested = body.get('hintLevel', 2)
        if type(requested) is not int or requested not in {1, 2, 3, 4}:
            raise TutorContextError('提示层级无效')
        run = context.run
        result = (run or {}).get('result') or {}
        errors = result.get('errors') or [result.get('stderr') or result.get('compile_output') or '']
        verified_error = '\n'.join(str(e) for e in errors if e)[:2000]
        return {'intent': body.get('intent'), 'exerciseId': task.get('ref') or 'free-code',
                'questionTitle': task.get('title') or '自主代码讨论（未绑定题目）',
                'questionPrompt': task.get('prompt') or '', 'topic': task.get('concept_id') or '',
                'code': context.code, 'userQuestion': _text(body.get('userQuestion'), '问题', 8000),
                'hintLevel': min(requested, task.get('max_hint_level', 2)),
                'stderr': verified_error, 'stdout': result.get('stdout') or '',
                'answerStatus': ('correct' if context.formal_result['passed'] else 'wrong') if context.formal_result else 'not_run',
                'caseResults': [], 'allPassed': False,
                'executionStatusLabel': ('正式判题已通过' if context.formal_result['passed'] else '正式判题未通过') if context.formal_result else (
                    '已执行自测（非正式判题）' if run else '未绑定服务器运行记录'),
                'executionNote': ('服务器执行的自测记录；用例由学生提供，不是正式测验。' if run else '没有绑定的服务器执行记录。'),
                'conversationHistory': []}

    @staticmethod
    def current(user_id, context):
        # Fresh transaction observes withdrawals, edits, account changes and
        # teacher policy changes that happened during a model request.
        try:
            with Session(db.engine) as session:
                task = TutorContextService.task(user_id, (context.task or {}).get('ref'), session=session)
                return task == context.task
        except TutorContextError:
            return False

    @staticmethod
    def record_run(user_id, context, result, *, kind):
        if kind not in {'run', 'test_cases', 'trace'}:
            raise ValueError('invalid_execution_kind')
        if kind == 'trace':
            safe = {key: result.get(key) for key in ('status', 'stdout', 'stderr', 'compile_output', 'trace', 'trace_status')}
        elif kind == 'run':
            safe = {key: result.get(key) for key in ('status', 'stdout', 'stderr', 'compile_output')}
            for key in ('stdout', 'stderr', 'compile_output'):
                safe[key] = str(safe.get(key) or '')[:4096]
        else:
            # Expected values and executable setup/invoke fragments are not
            # retained. Caller-supplied tests remain explicitly self-tests.
            safe = {'all_passed': result['all_passed'], 'passed_count': result['passed_count'],
                    'total': result['total'], 'errors': [str(row.get('error'))[:1000]
                        for row in result['results'] if row.get('error')][:5]}
        row = TutorCodeRun(id=str(uuid.uuid4()), user_id=user_id,
            question_ref=context.ref, question_version=(context.task or {}).get('version'),
            code_hash=context.code_hash, normalized_code_hash=code_hash(CodeExecutionService.normalize_python_source(context.code)),
            execution_kind=kind, backend=result.get('backend') or CodeExecutionService.backend_name(), result=safe)
        db.session.add(row)
        db.session.commit()
        return {'run_id': row.id, 'code_hash': row.code_hash, 'question_version': row.question_version,
                'evidence_scope': 'self_test'}
