"""Server-owned submissions and exams. Browser tests are never grading authority."""
import copy
import random
import uuid
from datetime import timedelta

from sqlalchemy import or_, update
from sqlalchemy.exc import IntegrityError
from app.models import db
from app.models.student_practice import PracticeAttempt, QuestionFavorite, MockExam
from app.services.practice_question import PracticeQuestionService
from app.services.tutor_context import TutorContextService, TutorContextError, _text
from app.services.code_execution import CodeExecutionService
from app.services.execution_errors import ExecutionUnavailable
from app.utils.time import utc_now


class StudentPractice:
    @staticmethod
    def question(uid, ref):
        task = TutorContextService.task(uid, ref)
        if not task:
            raise TutorContextError('该题暂不支持正式提交', 404)
        item = PracticeQuestionService.get_by_ref(task['ref'])
        if not item:
            raise TutorContextError('题目不存在', 404)
        return task, item

    @staticmethod
    def catalog(uid, args):
        # Filtering precedes pagination and runs against the entire accessible pool.
        items = PracticeQuestionService.list_for_student(knowledge_key=args.get('knowledge_key') or None, limit=100000, user_id=uid)
        favorites = {r.question_ref for r in QuestionFavorite.query.filter_by(user_id=uid)}
        done = {r[0] for r in db.session.query(PracticeAttempt.question_ref).filter_by(user_id=uid).distinct()}
        needle = str(args.get('q') or '').strip().lower()
        visible = []
        for item in items:
            try:
                task = TutorContextService.task(uid, item['id'])
            except TutorContextError:
                continue
            if not task:
                continue
            ref = task['ref']
            if needle and needle not in (item['title'] + ' ' + item.get('description', '')).lower():
                continue
            if args.get('difficulty') and item['difficulty'] != args['difficulty']:
                continue
            if args.get('done') in ('yes', 'no') and ((ref in done) != (args['done'] == 'yes')):
                continue
            if str(args.get('favorite', '')).lower() in ('1', 'true') and ref not in favorites:
                continue
            visible.append({**item, 'canonical_ref': ref, 'done': ref in done, 'favorite': ref in favorites})
        page = max(1, int(args.get('page') or 1))
        size = max(1, min(500, int(args.get('page_size') or args.get('limit') or 24)))
        return {'items': visible[(page - 1)*size:page*size], 'total': len(visible), 'page': page, 'page_size': size}

    @staticmethod
    def favorite(uid, ref, enabled):
        task, _ = StudentPractice.question(uid, ref)
        key = (uid, task['ref'])
        row = db.session.get(QuestionFavorite, key)
        if enabled and not row:
            db.session.add(QuestionFavorite(user_id=uid, question_ref=task['ref']))
        elif not enabled and row:
            db.session.delete(row)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        return {'favorite': enabled, 'question_ref': task['ref']}

    @staticmethod
    def record(uid, task, code, result, *, source='practice', identity=None):
        row = PracticeAttempt(id=identity or str(uuid.uuid4()), user_id=uid,
            question_ref=task['ref'], question_version=task['version'], title=task['title'][:200],
            code=code, result=result, source=source)
        db.session.add(row)
        if source != 'teacher':
            from app.services.learner_state import LearnerStateService
            from app.models.tutor_session import TutorSession, TutorTurn
            from app.models.learner_state import TutorDisplayReceipt
            assisted = db.session.query(TutorTurn.id).join(TutorSession, TutorSession.id == TutorTurn.session_id).join(TutorDisplayReceipt, TutorDisplayReceipt.id == TutorTurn.receipt_id).filter(
                TutorSession.user_id == uid, TutorSession.question_ref == task['ref'],
                TutorSession.question_version == task['version'], TutorDisplayReceipt.displayed_at.isnot(None)).first() is not None
            LearnerStateService.append(user_id=uid, kind='submission_graded', source_type='practice_attempt',
                source_id=row.id, source_version=task['version'], payload={
                    'concept_id': task.get('concept_id'), 'question_ref': task['ref'], 'question_title': task['title'],
                    'correct': bool(result.get('all_passed')), 'assisted': assisted,
                    'evidence_scope': 'server_graded', 'backend': result.get('backend'),
                    'passed_count': result.get('passed_count'), 'test_count': result.get('total')})
        return row

    @staticmethod
    def submit(uid, ref, body):
        rid = str(uuid.UUID(str(body.get('request_id', ''))))
        code = _text(body.get('code'), '代码', 65536)
        task, item = StudentPractice.question(uid, ref)
        choice = body.get('selected_index') if task.get('question_type') == 'mcq' else None
        previous = db.session.get(PracticeAttempt, rid)
        if previous:
            if previous.user_id != uid or previous.question_ref != task['ref'] or previous.code != code or previous.result.get('selected_index') != choice:
                raise TutorContextError('提交编号已用于其他作答', 409)
            return previous.to_dict()
        if task['formal_question_id']:
            raise TutorContextError('请从教师试卷入口提交本题')
        if MockExam.query.filter_by(user_id=uid, status='active').first():
            raise TutorContextError('模拟考试进行中，请从试卷交卷', 409)
        if task.get('question_type') != 'mcq' and (not code.strip() or not item.get('test_cases')):
            raise TutorContextError('代码为空或题目尚未配置测试')
        version = body.get('question_version')
        if version and version != task['version']:
            raise TutorContextError('题目已更新，请重新加载', 409)
        if task.get('question_type') == 'mcq':
            options = task.get('options') or []
            if type(choice) is not int or not 0 <= choice < len(options) or item.get('correct_index') is None:
                raise TutorContextError('请选择有效选项')
            correct = choice == item['correct_index']
            result = {'all_passed': correct, 'selected_index': choice, 'passed_count': int(correct), 'total': 1, 'backend': 'server_mcq'}
        else:
            result = CodeExecutionService.submit('python', code, item['test_cases'], item.get('run_mode') or 'stdout')
        if TutorContextService.task(uid, ref)['version'] != task['version']:
            raise TutorContextError('题目在判题期间发生变化，请重新提交', 409)
        row = StudentPractice.record(uid, task, code, result, identity=rid)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return StudentPractice.submit(uid, ref, body)
        return row.to_dict()

    @staticmethod
    def history(uid, args):
        q = PracticeAttempt.query.filter_by(user_id=uid)
        if args.get('question_ref'):
            task, _ = StudentPractice.question(uid, args['question_ref'])
            q = q.filter_by(question_ref=task['ref'])
        page = max(1, int(args.get('page') or 1))
        return {'items': [r.to_dict() for r in q.order_by(PracticeAttempt.created_at.desc()).offset((page-1)*20).limit(20)], 'total': q.count()}


class MockExams:
    @staticmethod
    def owned(uid, eid):
        row = db.session.get(MockExam, eid)
        if not row or row.user_id != uid:
            raise TutorContextError('试卷不存在', 404)
        return row

    @staticmethod
    def create(uid, body):
        existing = MockExam.query.filter_by(active_user_id=uid).first()
        if existing:
            return MockExams.view(uid, existing.id)
        keys = body.get('knowledge_keys') or []
        if not isinstance(keys, list) or len(keys) > 6 or any(not isinstance(k, str) for k in keys) or len(set(keys)) != len(keys):
            raise TutorContextError('请选择最多六个不同知识点')
        pool = []
        for item in PracticeQuestionService.list_for_student(limit=100000, user_id=uid):
            if (item.get('question_type') or 'coding') != 'coding' or not item.get('test_cases'):
                continue
            if keys and item.get('knowledge_key') not in keys:
                continue
            try:
                task, payload = StudentPractice.question(uid, item['id'])
            except TutorContextError:
                continue
            # Published teacher papers keep their own grading and policy.
            if task['formal_question_id'] or task['tutoring_policy'] == 'disabled':
                continue
            pool.append({'task': task, 'item': payload})
        pool = list({p['task']['ref']: p for p in pool}.values())
        counts = {k: sum(p['item']['knowledge_key'] == k for p in pool) for k in keys}
        if len(pool) < 6 or any(n == 0 for n in counts.values()):
            raise TutorContextError(f'当前范围可用 {len(pool)} 道题，需要至少六道且每个知识点有题；请调整范围')
        random.SystemRandom().shuffle(pool)
        selected = []
        if keys:
            while len(selected) < 6:
                for key in keys:
                    candidate = next((p for p in pool if p['item']['knowledge_key'] == key and p not in selected), None)
                    if candidate and len(selected) < 6:
                        selected.append(candidate)
        else:
            selected = pool[:6]
        now = utc_now()
        row = MockExam(id=str(uuid.uuid4()), user_id=uid, active_user_id=uid, questions=selected,
                       answers={}, results={}, started_at=now, deadline=now + timedelta(minutes=120))
        db.session.add(row)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            row = MockExam.query.filter_by(active_user_id=uid).one()
        return MockExams.view(uid, row.id)

    @staticmethod
    def view(uid, eid):
        row = MockExams.owned(uid, eid)
        if row.status == 'active' and row.deadline <= utc_now():
            MockExams.lock(uid, eid)
            db.session.refresh(row)
        questions = []
        for snapshot in row.questions:
            item = copy.deepcopy(snapshot['item'])
            for key in ('test_cases', 'hint', 'correct_index'):
                item.pop(key, None)
            item['question_version'] = snapshot['task']['version']
            questions.append(item)
        return {'id': row.id, 'status': row.status, 'questions': questions, 'answers': row.answers,
                'results': row.results if row.status == 'completed' else {}, 'revision': row.revision,
                'deadline': row.deadline.isoformat()+'Z', 'server_time': utc_now().isoformat()+'Z',
                'score': row.score, 'submitted_at': row.submitted_at.isoformat()+'Z' if row.submitted_at else None}

    @staticmethod
    def save(uid, eid, body):
        row = MockExams.owned(uid, eid)
        answers = body.get('answers')
        refs = {p['item']['id'] for p in row.questions}
        if not isinstance(answers, dict) or set(answers)-refs:
            raise TutorContextError('答案题号无效')
        answers = {k: _text(v, '代码', 65536) for k, v in answers.items()}
        changed = db.session.execute(update(MockExam).where(MockExam.id == eid, MockExam.user_id == uid,
            MockExam.status == 'active', MockExam.deadline > utc_now(), MockExam.revision == body.get('revision')).values(
            answers=answers, revision=MockExam.revision+1)).rowcount
        db.session.commit()
        if not changed:
            raise TutorContextError('试卷已截止或在其他标签页更新，请重新载入', 409)
        return MockExams.view(uid, eid)

    @staticmethod
    def lock(uid, eid):
        MockExams.owned(uid, eid)
        db.session.execute(update(MockExam).where(MockExam.id == eid, MockExam.status == 'active').values(
            status='pending', submitted_at=utc_now(), revision=MockExam.revision+1))
        db.session.commit()

    @staticmethod
    def grade(eid):
        now = utc_now()
        claimed = db.session.execute(update(MockExam).where(MockExam.id == eid,
            MockExam.status.in_(['pending', 'grading']), or_(MockExam.lease_until.is_(None), MockExam.lease_until < now)).values(
                status='grading', lease_until=now + timedelta(minutes=10))).rowcount
        db.session.commit()
        if not claimed:
            return
        row = db.session.get(MockExam, eid)
        try:
            results = dict(row.results or {})
            for snapshot in row.questions:
                item, task = snapshot['item'], snapshot['task']
                ref = item['id']
                if ref in results:
                    continue
                code = row.answers.get(ref, '')
                result = CodeExecutionService.submit('python', code, item['test_cases'], item.get('run_mode') or 'stdout') if code.strip() else {'all_passed': False, 'results': [], 'reason': '未作答'}
                aid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'plex-exam:{eid}:{ref}'))
                if not db.session.get(PracticeAttempt, aid):
                    StudentPractice.record(row.user_id, task, code, result, source='mock_exam', identity=aid)
                results[ref] = {**result, 'attempt_id': aid}
                row.results = dict(results)
                db.session.commit()
            row.score = round(sum(bool(r.get('all_passed')) for r in results.values()) / 6 * 100, 2)
            row.status, row.active_user_id, row.lease_until = 'completed', None, None
            db.session.commit()
        except Exception:
            db.session.rollback()
            row = db.session.get(MockExam, eid)
            row.status, row.lease_until = 'pending', utc_now() + timedelta(seconds=30)
            db.session.commit()
            raise

    @staticmethod
    def sweep():
        now = utc_now()
        db.session.execute(update(MockExam).where(MockExam.status == 'active', MockExam.deadline <= now).values(status='pending', submitted_at=now))
        db.session.commit()
        ids = [r.id for r in MockExam.query.filter(MockExam.status.in_(['pending', 'grading']), or_(MockExam.lease_until.is_(None), MockExam.lease_until < now)).limit(5)]
        for eid in ids:
            try:
                MockExams.grade(eid)
            except Exception:
                from flask import current_app
                current_app.logger.exception('Mock exam grading deferred: %s', eid)
