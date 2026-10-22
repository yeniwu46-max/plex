"""Durable candidate tasks. External calls never hold a database transaction."""
from copy import deepcopy
from datetime import timedelta
import uuid
from flask import current_app
from sqlalchemy import update, or_, and_
from app.models import db, User
from app.models.counterexample import (CounterexampleGenerationTask as Task,
    CounterexampleGenerationCall as Call, CounterexampleChallenge as Challenge,
    CounterexampleVersion as Version, CounterexampleValidation as Validation)
from app.services.counterexample import (CounterexampleService, actor, owns_class, owned_spec,
    identifier, manifest, save, check_manifest)
from app.services.counterexample_contract import CounterexampleError as Error, object_fields, integer, BUG_KINDS
from app.services import counterexample_generation_model as model
from app.services.execution_errors import ExecutionUnavailable
from app.utils.time import utc_now

ACTIVE = {'queued', 'running'}
MAX_ATTEMPTS = 3
LEASE_SECONDS = 180


def view(row, *, detail=False):
    result = {key: getattr(row, key) for key in ('id','class_id','spec_id','spec_hash','bug_kind',
        'challenge_id','version_id','validation_id','status','stage','attempts','error_code')}
    result.update(created_at=row.created_at.isoformat()+'Z',
        completed_at=row.completed_at.isoformat()+'Z' if row.completed_at else None,
        retryable=row.status == 'failed' and row.attempts < MAX_ATTEMPTS
            and row.error_code not in {'context_changed','permission_changed'})
    if detail:
        result.update(generation_audit=row.generation_audit, pedagogy_review=row.pedagogy_review,
            calls=[{'id': call.id, 'attempt': call.attempt, 'stage': call.stage, 'audit': call.audit,
                'created_at': call.created_at.isoformat()+'Z',
                'completed_at': call.completed_at.isoformat()+'Z' if call.completed_at else None}
                for call in Call.query.filter_by(task_id=row.id).order_by(Call.created_at, Call.id).all()])
    return result


def owned(user_id, task_id):
    row = db.session.get(Task, identifier(task_id), populate_existing=True)
    if not row:
        raise Error('候选生成任务不存在', 404)
    owns_class(user_id, row.class_id)
    if row.teacher_id != user_id and actor(user_id, {'teacher','admin'}).role.name != 'admin':
        raise Error('候选生成任务不存在', 404)
    return row


def teacher_lock(user_id, *, reset=True):
    # Drop any JWT decorator's read snapshot before the serialization point.
    if reset:db.session.rollback()
    db.session.execute(update(User).where(User.id == user_id).values(id=User.id, updated_at=User.updated_at)
        .execution_options(synchronize_session=False))
    actor(user_id, {'teacher','admin'})


def check_capacity(user_id, class_id=None):
    limit = current_app.config.get('COUNTEREXAMPLE_GENERATION_ACTIVE_LIMIT', 2)
    if Task.query.filter(Task.teacher_id == user_id, Task.status.in_(ACTIVE)).count() >= limit:
        raise Error('当前候选任务已达并行上限，请等待完成或取消后再试', 429)
    if Task.query.filter(Task.status.in_(ACTIVE)).count() >= current_app.config.get('COUNTEREXAMPLE_GLOBAL_ACTIVE_LIMIT',8):
        raise Error('候选任务队列暂时已满，请稍后再试',429)
    if class_id is not None and Task.query.filter(Task.class_id==class_id,Task.status.in_(ACTIVE)).count() >= current_app.config.get('COUNTEREXAMPLE_CLASS_ACTIVE_LIMIT',4):
        raise Error('本班候选任务已达并行上限，请稍后再试',429)



from app.services.ai_admission import admission_lock


class CounterexampleGenerationService:
    @staticmethod
    @admission_lock('counterexample')
    def create(user_id, body):
        object_fields(body, {'request_id','spec_id','bug_kind'}, {'request_id','spec_id','bug_kind'})
        task_id, spec_id = identifier(body['request_id']), identifier(body['spec_id'])
        if not isinstance(body['bug_kind'], str) or body['bug_kind'] not in BUG_KINDS:
            raise Error('请选择已支持的错误类型')
        teacher_lock(user_id,reset=False)
        spec = owned_spec(user_id, spec_id)
        existing = db.session.get(Task, task_id)
        if existing:
            if (existing.teacher_id != user_id or existing.spec_id != spec.id
                    or existing.spec_hash != spec.content_hash or existing.bug_kind != body['bug_kind']):
                raise Error('请求编号已被不同内容使用', 409)
            result = view(existing, detail=True); save(); return result
        check_capacity(user_id,spec.class_id)
        if Task.query.filter(Task.class_id==spec.class_id,Task.created_at>=utc_now()-timedelta(hours=24)).count() >= current_app.config.get('COUNTEREXAMPLE_CLASS_DAILY_LIMIT',20):
            raise Error('本班最近 24 小时的候选任务额度已用完，请稍后再试',429)
        if Task.query.filter(Task.teacher_id == user_id, Task.created_at >= utc_now()-timedelta(hours=24)).count() >= current_app.config.get('COUNTEREXAMPLE_GENERATION_DAILY_LIMIT', 10):
            raise Error('最近 24 小时的候选任务额度已用完，请稍后再试', 429)
        row = Task(id=task_id, teacher_id=user_id, class_id=spec.class_id, spec_id=spec.id,
            spec_hash=spec.content_hash, bug_kind=body['bug_kind'], challenge_id=str(uuid.uuid4()),
            validation_id=str(uuid.uuid4()), status='queued', stage='generation', attempts=0)
        db.session.add(row); save()
        return view(row, detail=True)

    @staticmethod
    def read(user_id, task_id):
        return view(owned(user_id, task_id), detail=True)

    @staticmethod
    def list(user_id, class_id, page=1):
        owns_class(user_id, class_id); integer(page, 'page', 1, 100000)
        query = Task.query.filter_by(class_id=class_id)
        if actor(user_id, {'teacher','admin'}).role.name != 'admin':
            query = query.filter_by(teacher_id=user_id)
        return {'items': [view(row) for row in query.order_by(Task.created_at.desc(), Task.id).offset((page-1)*20).limit(20)],
            'page': page, 'page_size': 20, 'total': query.count()}

    @staticmethod
    def cancel(user_id, task_id):
        row = owned(user_id, task_id)
        db.session.execute(update(Task).where(Task.id == row.id, Task.status.in_(ACTIVE))
            .values(status='cancelled', lease_token=None, lease_until=None, completed_at=utc_now())
            .execution_options(synchronize_session=False))
        save(); db.session.expire_all()
        return view(db.session.get(Task, row.id), detail=True)

    @staticmethod
    @admission_lock('counterexample')
    def retry(user_id, task_id, body):
        object_fields(body, {'expected_attempts'}, {'expected_attempts'})
        expected = integer(body['expected_attempts'], 'expected_attempts', 0, MAX_ATTEMPTS-1)
        owner_id = owned(user_id, task_id).teacher_id
        teacher_lock(owner_id,reset=False)
        row = owned(user_id, task_id)
        # expected_attempts makes a retry request itself idempotent, including a lost response.
        if row.attempts > expected or row.status in ACTIVE:
            result = view(row, detail=True); save(); return result
        if not view(row)['retryable'] or row.attempts != expected:
            raise Error('此任务不能重试，请检查记录或修订基准后创建新任务', 409)
        check_capacity(row.teacher_id,row.class_id)
        row.status, row.error_code, row.completed_at = 'queued', None, None
        save(); return view(row, detail=True)


def claim():
    db.session.rollback()
    now = utc_now()
    eligible = or_(Task.status == 'queued', and_(Task.status == 'running', Task.lease_until <= now))
    # Recovery is bounded: an interrupted call might already have been billed.
    db.session.execute(update(Task).where(eligible, Task.attempts >= MAX_ATTEMPTS).values(
        status='failed', error_code='retry_limit', lease_token=None, lease_until=None, completed_at=now))
    save()
    for row in Task.query.filter(eligible, Task.attempts < MAX_ATTEMPTS).order_by(Task.created_at, Task.id).limit(20).all():
        token, task_id = str(uuid.uuid4()), row.id
        changed = db.session.execute(update(Task).where(Task.id == task_id, eligible, Task.attempts < MAX_ATTEMPTS)
            .values(status='running', lease_token=token, lease_until=now+timedelta(seconds=LEASE_SECONDS),
                attempts=Task.attempts+1, error_code=None, completed_at=None).execution_options(synchronize_session=False)).rowcount
        save()
        if changed:
            return task_id, token
    return None


class LostClaim(Exception):
    pass


def checkpoint(task_id, token):
    db.session.rollback()
    if not db.session.execute(update(Task).where(Task.id == task_id, Task.status == 'running',
            Task.lease_token == token, Task.lease_until > utc_now()).values(
                lease_until=utc_now()+timedelta(seconds=LEASE_SECONDS)).execution_options(synchronize_session=False)).rowcount:
        db.session.rollback(); raise LostClaim()
    row = db.session.get(Task, task_id, populate_existing=True)
    spec = owned_spec(row.teacher_id, row.spec_id)
    if spec.content_hash != row.spec_hash or spec.class_id != row.class_id:
        raise Error('生成依据已变化', 409)
    if row.version_id:
        version = db.session.get(Version, row.version_id, populate_existing=True)
        challenge = db.session.get(Challenge, row.challenge_id, populate_existing=True)
        check_manifest(version)
        if challenge.current_revision != version.revision or version.blocked_reason:
            raise Error('生成期间题目版本已变化', 409)
    return row, spec


def model_call(task_id, token, stage, function):
    row, _ = checkpoint(task_id, token)
    call_id = str(uuid.uuid4())
    db.session.add(Call(id=call_id, task_id=row.id, attempt=row.attempts, stage=stage))
    save()
    from app.services.model_accounting import scope
    policy=model.GENERATION_POLICY if stage=='generation' else model.REVIEW_POLICY
    with scope(workflow='counterexample',user_id=row.teacher_id,request_id=row.id,attempt_id=token,
               class_id=row.class_id,stage=stage,policy_version=policy):
        result = function()
    audit = result[1] if stage == 'generation' else result
    # Persist usage even if the user cancelled during the external request.
    db.session.rollback()
    db.session.execute(update(Call).where(Call.id == call_id).values(audit=audit, completed_at=utc_now()))
    save()
    return result


def finish(row, status, reason=None):
    row.status, row.error_code, row.completed_at = status, reason, utc_now()
    row.lease_token = row.lease_until = None
    save()


def execute(task_id, token):
    try:
        row, spec = checkpoint(task_id, token)
        content, bug_kind = deepcopy(spec.content), row.bug_kind
        stage = row.stage; save()
        if stage == 'generation':
            proposed, audit = model_call(task_id, token, 'generation', lambda: model.generate(content, bug_kind))
            row, spec = checkpoint(task_id, token)
            row.generation_audit = audit
            if proposed is None:
                finish(row, 'failed' if audit['error_code'] == 'model_unavailable' else 'rejected', audit['error_code']); return
            challenge = Challenge(id=row.challenge_id, teacher_id=row.teacher_id, class_id=row.class_id)
            db.session.add(challenge); db.session.flush()
            version = Version(id=str(uuid.uuid4()), challenge_id=challenge.id, revision=1, spec_id=spec.id,
                candidate=proposed, manifest_hash=manifest(spec, proposed), origin='model_generated')
            db.session.add(version); db.session.flush()
            row.version_id, row.stage = version.id, 'validation'; save()
        row, spec = checkpoint(task_id, token)
        version = db.session.get(Version, row.version_id)
        challenge_id, teacher_id, validation_id = row.challenge_id, row.teacher_id, row.validation_id
        expected_hash, proposed = version.manifest_hash, deepcopy(version.candidate)
        stage = row.stage; save()
        if stage == 'validation':
            result = CounterexampleService.validate(teacher_id, challenge_id,
                {'request_id': validation_id, 'manifest_hash': expected_hash}, generation_token=token)
            row, _ = checkpoint(task_id, token)
            if result['status'] != 'passed':
                finish(row, 'rejected', 'execution_rejected'); return
            row.stage = 'pedagogy'; save()
        row, _ = checkpoint(task_id, token)
        validation = db.session.get(Validation, validation_id, populate_existing=True)
        version = db.session.get(Version, row.version_id, populate_existing=True)
        if not validation or validation.status != 'passed' or version.latest_report_id != validation.id:
            raise Error('执行报告已变化', 409)
        report = deepcopy(validation.report); save()
        audit = model_call(task_id, token, 'pedagogy', lambda: model.review(content, proposed, report, expected_hash, validation_id))
        row, _ = checkpoint(task_id, token)
        version = db.session.get(Version, row.version_id, populate_existing=True)
        if version.latest_report_id != validation_id:
            raise Error('教学审核期间执行报告已变化', 409)
        row.pedagogy_review = audit
        if audit['error_code'] == 'model_unavailable':
            finish(row, 'failed', 'model_unavailable')
        elif audit['error_code'] or audit['verdict'] != 'pass':
            finish(row, 'rejected', audit['error_code'] or 'pedagogy_rejected')
        else:
            finish(row, 'ready')
    except LostClaim:
        db.session.rollback()  # Cancelled/expired workers cannot advance or publish.
    except Exception as exc:
        db.session.rollback()
        reason = ('execution_unavailable' if isinstance(exc, ExecutionUnavailable) else
                  'permission_changed' if isinstance(exc, Error) and exc.status in {403,404} else
                  'context_changed' if isinstance(exc, Error) else 'worker_error')
        if reason == 'worker_error':
            current_app.logger.warning('counterexample worker failed: %s', type(exc).__name__)
        db.session.execute(update(Task).where(Task.id == task_id, Task.status == 'running',
            Task.lease_token == token, Task.lease_until > utc_now()).values(status='failed', error_code=reason,
            lease_token=None, lease_until=None, completed_at=utc_now()).execution_options(synchronize_session=False))
        save()


def run_once(app):
    with app.app_context():
        try:
            work = claim()
            if work:
                execute(*work)
            return bool(work)
        finally:
            db.session.remove()
