"""Versioned authoring and publication; no generic resource approval can bypass it."""
from copy import deepcopy
from datetime import timedelta
import uuid

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from app.models import db, User, Class
from app.models.counterexample import (CounterexampleSpec as Spec, CounterexampleChallenge as Challenge,
    CounterexampleVersion as Version, CounterexampleValidation as Validation, CounterexampleAttempt as Attempt,
    CounterexampleGenerationTask as GenerationTask)
from app.data.knowledge_node_registry import get_entry
from app.services.counterexample_contract import (CounterexampleError as Error, candidate,
    digest, integer, object_fields, specification, text, check_value)
from app.services.counterexample_validation import validate
from app.services.execution_errors import ExecutionUnavailable
from app.utils.time import utc_now


def identifier(value):
    try:
        if not isinstance(value, str) or str(uuid.UUID(value)) != value.lower():
            raise ValueError()
        return value.lower()
    except (ValueError, AttributeError):
        raise Error('请求与记录编号必须是 UUID') from None


def actor(user_id, role):
    user = db.session.get(User, user_id, populate_existing=True)
    if not user or user.status != 'active' or not user.role or user.role.name not in role:
        raise Error('当前账号无权访问反例挑战', 403)
    return user


def owns_class(user_id, class_id):
    user = actor(user_id, {'teacher', 'admin'})
    cohort = db.session.get(Class, class_id, populate_existing=True)
    if not cohort or (user.role.name != 'admin' and cohort.teacher_id != user.id):
        raise Error('班级不存在或不可管理', 404)


def owned_challenge(user_id, challenge_id):
    row = db.session.get(Challenge, identifier(challenge_id), populate_existing=True)
    if not row:
        raise Error('反例挑战不存在', 404)
    owns_class(user_id, row.class_id)
    if row.teacher_id != user_id and actor(user_id, {'teacher', 'admin'}).role.name != 'admin':
        raise Error('反例挑战不存在', 404)
    return row


def owned_spec(user_id, spec_id):
    row = db.session.get(Spec, identifier(spec_id), populate_existing=True)
    if not row:
        raise Error('题意与测试基准不存在', 404)
    owns_class(user_id, row.class_id)
    if row.teacher_id != user_id and actor(user_id, {'teacher', 'admin'}).role.name != 'admin':
        raise Error('题意与测试基准不存在', 404)
    if digest(row.content) != row.content_hash:
        raise Error('基准内容已变化，请创建新基准重新验证', 409)
    return row


def manifest(spec, proposed):
    return digest({'spec_hash': spec.content_hash, 'candidate': proposed})


def version_for(row, revision=None):
    return Version.query.filter_by(challenge_id=row.id, revision=revision or row.current_revision).one()


def check_manifest(version):
    spec = db.session.get(Spec, version.spec_id, populate_existing=True)
    if digest(spec.content) != spec.content_hash or manifest(spec, version.candidate) != version.manifest_hash:
        raise Error('版本内容与验证依据不一致，请重新创建版本', 409)
    return spec


def report_view(row):
    return {'id': row.id, 'version_id': row.version_id, 'manifest_hash': row.manifest_hash,
        'status': row.status, 'report': row.report,
        'completed_at': row.completed_at.isoformat() + 'Z' if row.completed_at else None}


def teacher_view(row, revision=None):
    version = version_for(row, revision)
    spec = check_manifest(version)
    report = db.session.get(Validation, version.latest_report_id) if version.latest_report_id else None
    generation = GenerationTask.query.filter_by(version_id=version.id).first() if version.origin == 'model_generated' else None
    return {'id': row.id, 'class_id': row.class_id, 'current_revision': row.current_revision,
        'published_revision': row.published_revision, 'version_id': version.id, 'revision': version.revision,
        'manifest_hash': version.manifest_hash, 'spec_id': spec.id, 'specification': spec.content,
        'blocked_reason': version.blocked_reason,
        'material_issues': [{'attempt_id': item.id, 'input': item.input_value,
            'reason': (item.execution_report or {}).get('material_issue')} for item in Attempt.query.filter_by(
                version_id=version.id, status='material_issue').order_by(Attempt.created_at.desc()).limit(10).all()],
        'candidate': version.candidate, 'origin': version.origin, 'source_template': version.source_template,
        'generation': {'id': generation.id, 'status': generation.status, 'stage': generation.stage,
            'error_code': generation.error_code, 'pedagogy_review': generation.pedagogy_review} if generation else None,
        'validation': report_view(report) if report else None,
        'reviewed_report_id': version.reviewed_report_id, 'review_note': version.review_note}


def save():
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise Error('相同请求正在处理，请使用原请求编号重试', 409) from None


class CounterexampleService:
    @staticmethod
    def list_teacher(user_id, class_id, page=1):
        owns_class(user_id, class_id)
        page = integer(page, 'page', 1, 100000)
        user = actor(user_id, {'teacher', 'admin'})
        query = db.session.query(Challenge, Version, Spec).join(Version,
            (Version.challenge_id == Challenge.id) & (Version.revision == Challenge.current_revision)).join(Spec, Spec.id == Version.spec_id)
        query = query.filter(Challenge.class_id == class_id)
        if user.role.name != 'admin':
            query = query.filter(Challenge.teacher_id == user_id)
        total = query.count()
        rows = query.order_by(Challenge.created_at.desc(), Challenge.id).offset((page-1)*20).limit(20).all()
        items = []
        for row, version, spec in rows:
            report = db.session.get(Validation, version.latest_report_id) if version.latest_report_id else None
            items.append({'id': row.id, 'class_id': row.class_id, 'title': spec.content.get('title'),
                'revision': version.revision, 'published_revision': row.published_revision,
                'blocked_reason': version.blocked_reason, 'validation_status': report.status if report else None,
                'created_at': row.created_at.isoformat()+'Z'})
        return {'items': items, 'page': page, 'page_size': 20, 'total': total}

    @staticmethod
    def get_spec(user_id, spec_id):
        row = owned_spec(user_id, spec_id)
        return {'id': row.id, 'class_id': row.class_id, 'content_hash': row.content_hash, 'specification': row.content}

    @staticmethod
    def version_history(user_id, challenge_id, page=1):
        row = owned_challenge(user_id, challenge_id)
        page = integer(page, 'page', 1, 100000)
        query = Version.query.filter_by(challenge_id=row.id)
        items = query.order_by(Version.revision.desc()).offset((page-1)*20).limit(20).all()
        return {'items': [{'revision': v.revision, 'created_at': v.created_at.isoformat()+'Z',
            'origin': v.origin, 'manifest_hash': v.manifest_hash, 'blocked_reason': v.blocked_reason,
            'reviewed_report_id': v.reviewed_report_id, 'review_note': v.review_note} for v in items],
            'page': page, 'page_size': 20, 'total': query.count()}

    @staticmethod
    def create_spec(user_id, body):
        object_fields(body, {'request_id', 'class_id', 'specification'}, {'request_id', 'class_id', 'specification'})
        request_id = identifier(body['request_id'])
        class_id = integer(body['class_id'], 'class_id', 1, 2**31-1)
        owns_class(user_id, class_id)
        content = specification(body['specification'])
        if not get_entry(content['concept_id']):
            raise Error('请使用课程中的有效知识点编号')
        existing = db.session.get(Spec, request_id)
        if existing:
            if existing.teacher_id != user_id or existing.class_id != class_id or existing.content_hash != digest(content):
                raise Error('请求编号已被不同内容使用', 409)
            return {'id': existing.id, 'content_hash': existing.content_hash}
        row = Spec(id=request_id, teacher_id=user_id, class_id=class_id, content=content, content_hash=digest(content))
        db.session.add(row); save()
        return {'id': row.id, 'content_hash': row.content_hash}

    @staticmethod
    def create(user_id, body):
        object_fields(body, {'request_id', 'spec_id', 'candidate', 'source_template'}, {'request_id', 'spec_id', 'candidate'})
        request_id = identifier(body['request_id'])
        spec = owned_spec(user_id, body['spec_id'])
        proposed = candidate(body['candidate'])
        from app.services.counterexample_catalog import source_reference
        source, origin = source_reference(body.get('source_template'), spec.content, proposed)
        row = db.session.get(Challenge, request_id)
        if row:
            row = owned_challenge(user_id, row.id)
            first = version_for(row, 1)
            if first.spec_id != spec.id or first.manifest_hash != manifest(spec, proposed) or first.source_template != source:
                raise Error('请求编号已被不同内容使用', 409)
            return teacher_view(row)
        row = Challenge(id=request_id, teacher_id=user_id, class_id=spec.class_id)
        db.session.add(row)
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            raise Error('相同请求正在处理，请使用原请求编号重试', 409) from None
        db.session.add(Version(id=str(uuid.uuid4()), challenge_id=row.id, revision=1,
            spec_id=spec.id, candidate=proposed, manifest_hash=manifest(spec, proposed), origin=origin, source_template=source))
        save()
        return teacher_view(row)

    @staticmethod
    def revise(user_id, challenge_id, body):
        object_fields(body, {'request_id', 'expected_revision', 'spec_id', 'candidate', 'source_template'},
            {'request_id', 'expected_revision', 'spec_id', 'candidate'})
        request_id = identifier(body['request_id'])
        row = owned_challenge(user_id, challenge_id)
        expected = integer(body['expected_revision'], 'expected_revision', 1, 2**31-2)
        spec = owned_spec(user_id, body['spec_id'])
        proposed = candidate(body['candidate'])
        from app.services.counterexample_catalog import source_reference
        base_version = Version.query.filter_by(challenge_id=row.id, revision=expected).first()
        base_source = base_version.source_template if base_version else None
        raw_source = body.get('source_template')
        if raw_source is None:
            raw_source = {key:base_source[key] for key in ('id','content_hash')} if base_source else None
        source, origin = source_reference(raw_source, spec.content, proposed)
        if spec.class_id != row.class_id:
            raise Error('新基准必须属于同一班级')
        regressions = db.session.query(Attempt.input_value).join(Version, Version.id == Attempt.version_id).filter(
            Version.challenge_id == row.id, Attempt.status == 'material_issue').all()
        covered = {digest(test['input']) for test in spec.content['tests']}
        if any(check_value(value, spec.content['input_contract']) and digest(value) not in covered for (value,) in regressions):
            raise Error('新基准必须纳入此前发现材料问题且仍合法的输入，填写独立预期结果后再修订')
        existing = db.session.get(Version, request_id)
        if existing:
            if (existing.challenge_id != row.id or existing.revision != expected+1
                    or existing.spec_id != spec.id or existing.manifest_hash != manifest(spec, proposed) or existing.source_template != source):
                raise Error('请求编号已被不同内容使用', 409)
            return teacher_view(row)
        if not db.session.execute(update(Challenge).where(Challenge.id == row.id, Challenge.current_revision == expected)
                .values(current_revision=expected+1, published_revision=None).execution_options(synchronize_session=False)).rowcount:
            raise Error('版本已更新，请重新加载', 409)
        db.session.add(Version(id=request_id, challenge_id=row.id, revision=expected+1, spec_id=spec.id,
            candidate=proposed, manifest_hash=manifest(spec, proposed), origin=origin, source_template=source))
        save(); db.session.expire_all()
        return teacher_view(row)

    @staticmethod
    def validate(user_id, challenge_id, body, *, generation_token=None):
        object_fields(body, {'request_id', 'manifest_hash'}, {'request_id', 'manifest_hash'})
        request_id = identifier(body['request_id'])
        row = owned_challenge(user_id, challenge_id)
        version = version_for(row)
        spec = check_manifest(version)
        if version.origin == 'model_generated':
            task = GenerationTask.query.filter_by(version_id=version.id).first()
            if (not task or not generation_token or task.lease_token != generation_token
                    or task.status != 'running' or not task.lease_until or task.lease_until <= utc_now()):
                raise Error('模型候选由后台任务完成验证；如需修改或重新验证，请先创建人工修订版本', 409)
        if version.blocked_reason:
            raise Error('此版本发现材料问题，请修订基准或代码并创建新版本', 409)
        if body['manifest_hash'] != version.manifest_hash:
            raise Error('版本已更新，请重新加载', 409)
        prior = db.session.get(Validation, request_id)
        now, token = utc_now(), str(uuid.uuid4())
        if prior:
            if prior.version_id != version.id or prior.actor_id != user_id or prior.manifest_hash != version.manifest_hash:
                raise Error('请求编号已被不同内容使用', 409)
            if prior.status in {'passed', 'failed'}:
                return report_view(prior)
            if prior.status == 'processing' and prior.lease_until > now:
                raise Error('该验证仍在执行，请稍后重试', 409)
        latest = db.session.get(Validation, version.latest_report_id) if version.latest_report_id else None
        if latest and latest.status == 'processing' and latest.lease_until > now:
            raise Error('此版本正在验证，请稍后重试', 409)
        expected_report = version.latest_report_id
        if not db.session.execute(update(Version).where(Version.id == version.id,
                Version.latest_report_id == expected_report).values(latest_report_id=request_id)
                .execution_options(synchronize_session=False)).rowcount:
            raise Error('此版本正在验证，请稍后重试', 409)
        db.session.execute(update(Challenge).where(Challenge.id == row.id,
            Challenge.published_revision == version.revision).values(published_revision=None)
            .execution_options(synchronize_session=False))
        if prior:
            if not db.session.execute(update(Validation).where(Validation.id == request_id,
                    Validation.lease_token == prior.lease_token, Validation.status == prior.status)
                    .values(status='processing', lease_token=token, lease_until=now+timedelta(seconds=120),
                            report=None, completed_at=None).execution_options(synchronize_session=False)).rowcount:
                raise Error('验证状态已变化，请重试', 409)
        else:
            db.session.add(Validation(id=request_id, version_id=version.id, actor_id=user_id,
                manifest_hash=version.manifest_hash, status='processing', lease_token=token,
                lease_until=now+timedelta(seconds=120)))
        spec_content, proposed, vid, expected_hash = deepcopy(spec.content), deepcopy(version.candidate), version.id, version.manifest_hash
        save()  # No database transaction spans sandbox execution.
        unavailable = None
        try:
            result = validate(spec_content, proposed)
            status = 'passed' if result['passed'] else 'failed'
        except ExecutionUnavailable as exc:
            unavailable = exc
            result, status = {'passed': False, 'reason': exc.reason, 'retryable': True}, 'unavailable'
        # Never let a slow/expired worker overwrite another attempt's report.
        db.session.rollback()
        row = owned_challenge(user_id, challenge_id)
        version = db.session.get(Version, vid, populate_existing=True)
        check_manifest(version)
        if row.current_revision != version.revision or version.manifest_hash != expected_hash:
            db.session.execute(update(Validation).where(Validation.id == request_id,
                Validation.lease_token == token, Validation.status == 'processing')
                .values(status='superseded', report=result, completed_at=utc_now()))
            save()
            raise Error('验证期间版本已变化，请验证新版本', 409)
        if not db.session.execute(update(Validation).where(Validation.id == request_id,
                Validation.lease_token == token, Validation.status == 'processing', Validation.lease_until > utc_now())
                .values(status=status, report=result, completed_at=utc_now()).execution_options(synchronize_session=False)).rowcount:
            raise Error('验证请求已过期，请使用原请求编号重试', 409)
        save(); db.session.expire_all()
        if unavailable:
            raise unavailable
        return report_view(db.session.get(Validation, request_id))

    @staticmethod
    def review(user_id, challenge_id, body):
        object_fields(body, {'action', 'manifest_hash', 'validation_id', 'note', 'checks'}, {'action', 'manifest_hash'})
        row = owned_challenge(user_id, challenge_id)
        version = version_for(row)
        check_manifest(version)
        if body['manifest_hash'] != version.manifest_hash:
            raise Error('版本已变化，请重新审核', 409)
        if body['action'] == 'withdraw':
            if not db.session.execute(update(Challenge).where(Challenge.id == row.id,
                    Challenge.current_revision == version.revision).values(published_revision=None)
                    .execution_options(synchronize_session=False)).rowcount:
                raise Error('版本已变化，请重新加载后撤回', 409)
            save(); db.session.expire_all()
            return teacher_view(row)
        if body['action'] != 'publish':
            raise Error('action 必须为 publish 或 withdraw')
        if version.origin == 'model_generated':
            task = GenerationTask.query.filter_by(version_id=version.id).first()
            audit = task.pedagogy_review if task else None
            if (not task or task.status != 'ready' or not audit or audit.get('verdict') != 'pass'
                    or audit.get('error_code') or audit.get('manifest_hash') != version.manifest_hash
                    or audit.get('validation_id') != version.latest_report_id):
                raise Error('模型候选须先完成当前版本的执行验证与教学审核；可修订为新版本后重新送审', 409)
        if version.blocked_reason:
            raise Error('此版本发现材料问题，须创建新版本后重新验证', 409)
        validation = db.session.get(Validation, identifier(body.get('validation_id')))
        if (not validation or validation.id != version.latest_report_id or validation.version_id != version.id
                or validation.status != 'passed' or validation.manifest_hash != version.manifest_hash
                or not validation.report or not validation.report.get('passed')):
            raise Error('必须先通过当前版本的隔离验证，任何审核都不能越过此门槛', 409)
        checks = body.get('checks')
        required = {'single_clear_bug', 'statement_consistent', 'explanation_correct', 'difficulty_appropriate'}
        if not isinstance(checks, dict) or set(checks) != required or any(value is not True for value in checks.values()):
            raise Error('请逐项完成教学审核')
        note = text(body.get('note'), '审核说明', 1500)
        if not db.session.execute(update(Version).where(Version.id == version.id,
                Version.latest_report_id == validation.id, Version.manifest_hash == body['manifest_hash'])
                .values(reviewed_report_id=validation.id, reviewer_id=user_id, review_note=note, reviewed_at=utc_now())
                .execution_options(synchronize_session=False)).rowcount:
            raise Error('验证状态已变化，请重新审核', 409)
        if not db.session.execute(update(Challenge).where(Challenge.id == row.id, Challenge.current_revision == version.revision)
                .values(published_revision=version.revision).execution_options(synchronize_session=False)).rowcount:
            raise Error('版本已变化，请重新审核', 409)
        save(); db.session.expire_all()
        return teacher_view(row)

    @staticmethod
    def get_teacher(user_id, challenge_id, revision=None):
        row = owned_challenge(user_id, challenge_id)
        if revision is not None:
            integer(revision, 'revision', 1, row.current_revision)
        return teacher_view(row, revision)

    @staticmethod
    def get_student(user_id, challenge_id):
        user = actor(user_id, {'student'})
        row = db.session.get(Challenge, identifier(challenge_id), populate_existing=True)
        if not row or row.class_id != user.class_id or not row.published_revision or row.published_revision != row.current_revision:
            raise Error('反例挑战不存在', 404)
        version = version_for(row, row.published_revision)
        spec = check_manifest(version)
        if version.blocked_reason:
            raise Error('反例挑战暂不可用', 404)
        report = db.session.get(Validation, version.reviewed_report_id) if version.reviewed_report_id else None
        if (not report or report.status != 'passed' or report.manifest_hash != version.manifest_hash
                or report.version_id != version.id or report.id != version.latest_report_id
                or not report.report or report.report.get('passed') is not True):
            raise Error('反例挑战暂不可用', 404)
        public = {key: spec.content[key] for key in ('title', 'statement', 'concept_id', 'input_contract', 'output_contract', 'allowed_bug_exceptions')}
        return {**public, 'id': row.id, 'revision': version.revision, 'version': version.manifest_hash,
                'buggy_code': version.candidate['buggy_code'], 'signature': 'solve(data)'}

    @staticmethod
    def list_student(user_id):
        user = actor(user_id, {'student'})
        rows = Challenge.query.filter(Challenge.class_id == user.class_id, Challenge.published_revision.is_not(None)).order_by(Challenge.created_at.desc()).limit(100).all()
        items = []
        for row in rows:
            try:
                items.append(CounterexampleService.get_student(user_id, row.id))
            except Error:
                continue  # A corrupted/unpublished revision must never leak.
        return {'items': items}
