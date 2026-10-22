"""Owned JSON counterexamples: executable facts and explanation advice stay separate."""
from copy import deepcopy
from datetime import timedelta
import time
import uuid

from sqlalchemy import update

from app.models import db, User
from app.models.counterexample import (CounterexampleAttempt as Attempt, CounterexampleVersion as Version,
    CounterexampleChallenge as Challenge, CounterexampleValidation as Validation,
    CounterexampleExplanationReview as ExplanationReview)
from app.services.counterexample import (CounterexampleService, actor, identifier, version_for,
    check_manifest, owned_challenge, save)
from app.services.counterexample_contract import CounterexampleError as Error, object_fields, integer, text, digest, check_value
from app.services.counterexample_validation import run_function, ValidationFailure
from app.services.counterexample_explanation import evaluate_explanation
from app.services.execution_errors import ExecutionUnavailable
from app.services.learner_state import LearnerStateService
from app.utils.time import utc_now

INFRA_FAILURES = {'invalid_execution_contract','unverified_execution_backend','missing_runtime_identity','runtime_changed'}


def context(user_id, challenge_id, revision=None, manifest_hash=None):
    public = CounterexampleService.get_student(user_id, challenge_id)
    if (revision is not None and public['revision'] != revision) or (manifest_hash is not None and public['version'] != manifest_hash):
        raise Error('题目版本已变化，请重新加载', 409)
    row = db.session.get(Challenge, public['id'])
    version = version_for(row, public['revision'])
    spec = check_manifest(version)
    validation = db.session.get(Validation, version.reviewed_report_id)
    runtimes = (validation.report or {}).get('runtimes') or []
    if not runtimes:
        raise ExecutionUnavailable('challenge_baseline_unavailable')
    runtime = {k:v for k,v in runtimes[0].items() if k != 'program'}
    return {'public': public, 'version_id': version.id, 'validation_id': validation.id,
        'class_id': row.class_id, 'spec': deepcopy(spec.content), 'candidate': deepcopy(version.candidate),
        'runtime': deepcopy(runtime)}


def probe(task, input_value, expected_output):
    """Repeat each independent program on this one legal input; no hidden suite."""
    started = time.perf_counter()
    spec, proposed = task['spec'], task['candidate']
    report = {'results': {}, 'runtimes': [], 'scope': 'submitted_input_only'}
    try:
        for name, source in [('reference', spec['reference_code']), ('fixed', proposed['fixed_code']), ('buggy', proposed['buggy_code'])]:
            observed, runtime = run_function(source, [input_value])
            repeated, again = run_function(source, [input_value])
            if runtime != again or runtime != task['runtime']:
                raise ExecutionUnavailable('challenge_runtime_changed')
            report['runtimes'].append({'program': name, **runtime})
            report['results'][name] = observed[0]
            if digest(observed) != digest(repeated):
                raise ValidationFailure('non_deterministic')
            outcome = observed[0]
            if outcome['kind'] == 'value' and not check_value(outcome['value'], spec['output_contract']):
                raise ValidationFailure(name+'_output_contract')
            if outcome['kind'] == 'exception' and (name != 'buggy' or outcome['exception'] not in spec['allowed_bug_exceptions']):
                raise ValidationFailure(name+'_exception')
        correct, fixed, buggy = (report['results'][name] for name in ('reference','fixed','buggy'))
        if digest(correct) != digest(fixed):
            raise ValidationFailure('reference_fixed_disagreement')
        facts = {'counterexample_found': digest(correct) != digest(buggy),
            'expected_output_correct': digest(expected_output) == digest(correct['value']),
            'correct_result': correct, 'buggy_result': buggy}
        return facts, {**report, 'elapsed_ms': round((time.perf_counter()-started)*1000)}
    except ValidationFailure as exc:
        if exc.reason in INFRA_FAILURES:
            raise ExecutionUnavailable(exc.reason) from None
        return None, {**report, 'material_issue': exc.reason, 'elapsed_ms': round((time.perf_counter()-started)*1000)}


def _view(row, version, *, teacher=False):
    result = {'request_id': row.id, 'challenge_id': version.challenge_id, 'revision': version.revision,
        'version': version.manifest_hash, 'status': row.status, 'input': row.input_value,
        'expected_output': row.expected_output, 'explanation': row.explanation,
        'created_at': row.created_at.isoformat()+'Z',
        'completed_at': row.completed_at.isoformat()+'Z' if row.completed_at else None,
        'retryable': row.status == 'unavailable' or (row.status == 'processing' and row.lease_until <= utc_now())}
    if row.status == 'complete':
        feedback = deepcopy(row.explanation_review)
        if not teacher and feedback:
            for key in ('provider','model','token_usage','elapsed_ms'):
                feedback.pop(key,None)
        result.update(**deepcopy(row.result), explanation_review=feedback)
    elif row.status == 'material_issue':
        result.update(graded=False, message='本次输入暴露出题目材料需要核对，题目已暂停；本次不计作答错误。')
    elif row.status == 'unavailable':
        result.update(graded=False, message='执行环境暂不可用，请稍后重试；本次不计作答结果。')
    else:
        result.update(graded=False, message='正在核对本次输入。' if row.status=='processing' else '题目已变化，请重新加载后提交。')
    if teacher:
        result['execution_report'] = row.execution_report
        result['student_id'] = row.user_id
    return result


def _mark_failed(request_id, token, status):
    db.session.rollback()
    db.session.execute(update(Attempt).where(Attempt.id == request_id, Attempt.lease_token == token,
        Attempt.status == 'processing').values(status=status, completed_at=utc_now()))
    db.session.commit()


class CounterexampleAttemptService:
    @staticmethod
    def list_teacher(user_id, challenge_id, page=1):
        challenge = owned_challenge(user_id, challenge_id)
        page = integer(page, 'page', 1, 100000)
        query = db.session.query(Attempt, Version, User).join(Version, Version.id == Attempt.version_id).join(User, User.id == Attempt.user_id).filter(
            Version.challenge_id == challenge.id, User.class_id == challenge.class_id, User.status != 'deleted')
        rows = query.order_by(Attempt.created_at.desc(), Attempt.id).offset((page-1)*20).limit(20).all()
        return {'items': [{'request_id': row.id, 'student_id': student.id,
            'student_name': student.real_name or student.username, 'revision': version.revision,
            'status': row.status, 'explanation_status': (row.explanation_review or {}).get('status'),
            'explanation_source': (row.explanation_review or {}).get('source'),
            'created_at': row.created_at.isoformat()+'Z'} for row, version, student in rows],
            'page': page, 'page_size': 20, 'total': query.count()}

    @staticmethod
    def list_owned(user_id, challenge_id):
        task = context(user_id, challenge_id)
        rows = Attempt.query.filter_by(user_id=user_id, version_id=task['version_id'],
            validation_id=task['validation_id']).order_by(Attempt.created_at.desc()).limit(20).all()
        return {'items': [{'request_id': row.id, 'status': row.status,
            'created_at': row.created_at.isoformat()+'Z'} for row in rows]}

    @staticmethod
    def submit(user_id, challenge_id, body):
        fields = {'request_id','revision','version','input','expected_output','explanation'}
        object_fields(body, fields, fields)
        request_id = identifier(body['request_id'])
        revision = integer(body['revision'], 'revision', 1, 2**31-1)
        explanation = text(body['explanation'], '原因说明', 2000)
        task = context(user_id, challenge_id, revision, body['version'])
        if not check_value(body['input'], task['spec']['input_contract']):
            raise Error('输入不在题目允许的范围内；这不算作答失败')
        if not check_value(body['expected_output'], task['spec']['output_contract']):
            raise Error('预期输出不符合题目声明的输出格式')
        request_hash = digest({**body, 'challenge_id': task['public']['id']})
        row = db.session.get(Attempt, request_id)
        now, token = utc_now(), str(uuid.uuid4())
        if row:
            if row.user_id != user_id or row.request_hash != request_hash or row.version_id != task['version_id']:
                raise Error('请求编号已用于不同提交，请重新发起', 409)
            if row.validation_id != task['validation_id']:
                raise Error('题目已重新验证，请重新加载并发起新提交', 409)
            if row.status == 'complete':
                return _view(row, db.session.get(Version, row.version_id))
            if row.status == 'processing' and row.lease_until > now:
                raise Error('这次提交仍在处理，请稍后使用原请求编号重试', 409)
            if not db.session.execute(update(Attempt).where(Attempt.id == request_id,
                    Attempt.lease_token == row.lease_token, Attempt.status == row.status)
                    .values(status='processing', lease_token=token, lease_until=now+timedelta(seconds=120),
                            completed_at=None).execution_options(synchronize_session=False)).rowcount:
                raise Error('提交状态已变化，请重试', 409)
        else:
            db.session.add(Attempt(id=request_id, user_id=user_id, version_id=task['version_id'],
                validation_id=task['validation_id'], request_hash=request_hash,
                input_value=deepcopy(body['input']), expected_output=deepcopy(body['expected_output']),
                explanation=explanation, status='processing', lease_token=token, lease_until=now+timedelta(seconds=120)))
        save()
        try:
            facts, report = probe(task, body['input'], body['expected_output'])
            feedback = evaluate_explanation(task['spec']['statement'], task['candidate']['buggy_code'],
                body['input'], explanation, facts) if facts else None
            report['initial_explanation_review'] = deepcopy(feedback)
        except ExecutionUnavailable:
            _mark_failed(request_id, token, 'unavailable')
            raise
        except Exception:
            _mark_failed(request_id, token, 'unavailable')
            raise
        db.session.rollback()
        try:
            # Lock in the same version -> challenge order as validation/publication.
            actor_now = actor(user_id, {'student'})
            if actor_now.class_id != task['class_id']:
                raise Error('班级归属已变化，请重新加载', 409)
            version = db.session.get(Version, task['version_id'], populate_existing=True)
            check_manifest(version)
            gate = db.session.execute(update(Version).where(Version.id == task['version_id'],
                Version.manifest_hash == task['public']['version'], Version.blocked_reason.is_(None),
                Version.reviewed_report_id == task['validation_id'], Version.latest_report_id == task['validation_id'])
                .values(blocked_reason=report.get('material_issue')).execution_options(synchronize_session=False)).rowcount
            published = db.session.execute(update(Challenge).where(Challenge.id == task['public']['id'],
                Challenge.current_revision == revision, Challenge.published_revision == revision,
                Challenge.class_id == task['class_id']).values(published_revision=None if facts is None else revision)
                .execution_options(synchronize_session=False)).rowcount if gate else 0
            if not gate or not published:
                raise Error('题目或发布状态已变化，请重新加载；本次未计成绩', 409)
            status = 'complete' if facts else 'material_issue'
            changed = db.session.execute(update(Attempt).where(Attempt.id == request_id,
                Attempt.lease_token == token, Attempt.status == 'processing', Attempt.lease_until > utc_now())
                .values(status=status, execution_report=report, explanation_review=feedback, completed_at=utc_now())
                .execution_options(synchronize_session=False)).rowcount
            if not changed:
                raise Error('本次请求已过期，请使用原请求编号重试', 409)
            row = db.session.get(Attempt, request_id, populate_existing=True)
            if facts:
                event = LearnerStateService.append(user_id=user_id, kind='counterexample_checked',
                    source_type='counterexample_attempt', source_id=row.id, source_version=task['public']['version'],
                    payload={'concept_id':task['spec']['concept_id'], 'question_title':task['spec']['title'],
                        'challenge_id': task['public']['id'], 'challenge_revision': revision,
                        'counterexample_found':facts['counterexample_found'], 'expected_output_correct':facts['expected_output_correct'],
                        'success':facts['counterexample_found'] and facts['expected_output_correct'],
                        'evidence_scope':'isolated_counterexample'})
                row.result = {**facts, 'graded': True, 'evidence_scope':'submitted_input_only',
                    'evidence_event_id':event.id, 'execution_ms':report['elapsed_ms'],
                    'notice':'记录的是这次反例实践，不能据此认定整个算法已掌握。'}
            save(); db.session.expire_all()
            return _view(db.session.get(Attempt,request_id), db.session.get(Version,task['version_id']))
        except Exception:
            _mark_failed(request_id, token, 'stale')
            raise

    @staticmethod
    def read(user_id, request_id):
        user = actor(user_id, {'student'})
        row = db.session.get(Attempt, identifier(request_id), populate_existing=True)
        if not row or row.user_id != user_id:
            raise Error('作答记录不存在', 404)
        version = db.session.get(Version,row.version_id)
        challenge = db.session.get(Challenge,version.challenge_id)
        if challenge.class_id != user.class_id:
            raise Error('作答记录不可访问', 404)
        if row.status == 'complete':
            task = context(user_id,challenge.id,version.revision,version.manifest_hash)
            if task['validation_id'] != row.validation_id:
                raise Error('题目已重新验证，这条旧结果暂不可展示',409)
        return _view(row,version)

    @staticmethod
    def teacher_read(user_id, request_id):
        row = db.session.get(Attempt, identifier(request_id), populate_existing=True)
        if not row:
            raise Error('作答记录不存在',404)
        version = db.session.get(Version,row.version_id)
        challenge = owned_challenge(user_id,version.challenge_id)
        student = db.session.get(User,row.user_id)
        if not student or student.class_id != challenge.class_id or student.status == 'deleted':
            raise Error('该学生已不在当前班级',404)
        spec = check_manifest(version)
        history = ExplanationReview.query.filter_by(attempt_id=row.id).order_by(ExplanationReview.revision.desc()).limit(20).all()
        return {**_view(row,version,teacher=True), 'student_name': student.real_name or student.username,
            'task_snapshot': {'title': spec.content['title'], 'statement': spec.content['statement'],
                'buggy_code': version.candidate['buggy_code'], 'input_contract': spec.content['input_contract'],
                'output_contract': spec.content['output_contract']},
            'review_history': [{'revision': item.revision, 'verdict': item.verdict, 'note': item.note,
                'reviewer_id': item.reviewer_id, 'created_at': item.created_at.isoformat()+'Z'} for item in history]}

    @staticmethod
    def review(user_id, request_id, body):
        object_fields(body, {'request_id','expected_revision','verdict','note'}, {'request_id','expected_revision','verdict','note'})
        review_id = identifier(body['request_id'])
        current = CounterexampleAttemptService.teacher_read(user_id,request_id)
        if current['status'] != 'complete':
            raise Error('执行判定尚未完成，不能通过解释审核改写结果',409)
        expected = integer(body['expected_revision'],'expected_revision',0,2**31-2)
        if body['verdict'] not in ('supported','needs_revision'):
            raise Error('请明确支持这段解释或要求修改')
        note = text(body['note'],'核对说明',500)
        prior = db.session.get(ExplanationReview,review_id)
        if prior:
            if (prior.attempt_id != request_id or prior.reviewer_id != user_id or prior.revision != expected+1
                    or prior.verdict != body['verdict'] or prior.note != note):
                raise Error('审核请求编号已用于不同内容',409)
            return CounterexampleAttemptService.teacher_read(user_id,request_id)
        feedback = {'policy_version':'counterexample-teacher-review-v1','source':'teacher','status':body['verdict'],
            'feedback':note,'revision':expected+1,'review_id':review_id,
            'notice':'教师核对解释；程序执行结果与学习证据保持原记录。'}
        if not db.session.execute(update(Attempt).where(Attempt.id == request_id, Attempt.review_revision == expected,
                Attempt.status == 'complete').values(review_revision=expected+1, explanation_review=feedback)
                .execution_options(synchronize_session=False)).rowcount:
            raise Error('解释已被审核，请重新加载',409)
        db.session.add(ExplanationReview(id=review_id, attempt_id=request_id, reviewer_id=user_id,
            revision=expected+1, verdict=body['verdict'],note=note))
        save();db.session.expire_all()
        return CounterexampleAttemptService.teacher_read(user_id,request_id)
