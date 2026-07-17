"""学生端：教师发布试炼题目的拉取与作答"""
from datetime import datetime

from app.models import Class, Trial, TrialParticipation, TrialQuestion, TrialQuestionProgress, User, db
from app.services.daily_quest import DailyQuestService
from app.services.question_generator import QuestionGenerator
from app.services.trial import TrialService
from app.utils.time import utc_now


class AssignmentService:
    @staticmethod
    def _option_label(index: int | None) -> str | None:
        if index is None or index < 0:
            return None
        return chr(65 + int(index))

    @staticmethod
    def _option_text(question: TrialQuestion, index: int | None) -> str | None:
        if index is None:
            return None
        options = question.to_dict()['options']
        idx = int(index)
        if idx < 0 or idx >= len(options):
            return None
        return options[idx]

    @staticmethod
    def _touch_question_start(progress: TrialQuestionProgress) -> None:
        if progress.status == 'pending' and not progress.started_at:
            progress.started_at = utc_now()

    @staticmethod
    def _build_answer_record(question: TrialQuestion, progress: TrialQuestionProgress | None) -> dict:
        if not progress or progress.status != 'completed':
            qtype = question.question_type or 'mcq'
            return {
                'question_id': question.id,
                'sort_order': question.sort_order,
                'question_type': qtype,
                'stem': question.stem,
                'knowledge_key': question.knowledge_key,
                'knowledge_label': QuestionGenerator.label_for_key(question.knowledge_key),
                'status': progress.status if progress else 'pending',
                'selected_index': None,
                'selected_label': None,
                'selected_text': None,
                'correct_index': question.correct_index if qtype == 'mcq' else None,
                'correct_label': AssignmentService._option_label(question.correct_index) if qtype == 'mcq' else None,
                'is_correct': None,
                'code_passed': None,
                'started_at': progress.started_at.isoformat() if progress and progress.started_at else None,
                'answered_at': None,
                'time_spent_sec': None,
                'agent_trace': [],
            }

        qtype = question.question_type or 'mcq'
        if qtype == 'coding':
            return {
                'question_id': question.id,
                'sort_order': question.sort_order,
                'question_type': qtype,
                'stem': question.stem,
                'knowledge_key': question.knowledge_key,
                'knowledge_label': QuestionGenerator.label_for_key(question.knowledge_key),
                'status': progress.status,
                'code_passed': progress.code_passed,
                'is_correct': progress.code_passed,
                'submitted_code': progress.submitted_code,
                'started_at': progress.started_at.isoformat() if progress.started_at else None,
                'answered_at': progress.answered_at.isoformat() if progress.answered_at else None,
                'time_spent_sec': progress.time_spent_sec,
                'agent_trace': progress.agent_trace(),
            }

        selected_index = progress.selected_index
        return {
            'question_id': question.id,
            'sort_order': question.sort_order,
            'stem': question.stem,
            'knowledge_key': question.knowledge_key,
            'knowledge_label': QuestionGenerator.label_for_key(question.knowledge_key),
            'status': progress.status,
            'selected_index': selected_index,
            'selected_label': progress.selected_label or AssignmentService._option_label(selected_index),
            'selected_text': AssignmentService._option_text(question, selected_index),
            'correct_index': question.correct_index,
            'correct_label': AssignmentService._option_label(question.correct_index),
            'is_correct': progress.is_correct,
            'started_at': progress.started_at.isoformat() if progress.started_at else None,
            'answered_at': progress.answered_at.isoformat() if progress.answered_at else None,
            'time_spent_sec': progress.time_spent_sec,
            'agent_trace': progress.agent_trace(),
        }

    @staticmethod
    def _questions_for_trial(trial_id: int):
        return (
            TrialQuestion.query.filter_by(trial_id=trial_id)
            .order_by(TrialQuestion.sort_order.asc(), TrialQuestion.id.asc())
            .all()
        )

    @staticmethod
    def _progress_for_user(user_id: int, question_ids: list[int]) -> dict[int, TrialQuestionProgress]:
        if not question_ids:
            return {}
        rows = TrialQuestionProgress.query.filter(
            TrialQuestionProgress.user_id == user_id,
            TrialQuestionProgress.question_id.in_(question_ids),
        ).all()
        return {row.question_id: row for row in rows}

    @staticmethod
    def _question_is_correct(question: TrialQuestion, progress: TrialQuestionProgress | None) -> bool:
        if not progress or progress.status != 'completed':
            return False
        if (question.question_type or 'mcq') == 'coding':
            return bool(progress.code_passed)
        return bool(progress.is_correct)

    @staticmethod
    def _serialize_question_item(question: TrialQuestion, progress: TrialQuestionProgress | None, trial: Trial):
        teacher_name = trial.teacher.real_name if trial.teacher else '老师'
        qtype = question.question_type or 'mcq'
        payload = {
            'id': question.id,
            'trial_id': trial.id,
            'trial_title': trial.title,
            'teacher_name': teacher_name,
            'question_type': qtype,
            'knowledge_key': question.knowledge_key,
            'knowledge_label': QuestionGenerator.label_for_key(question.knowledge_key),
            'stem': question.stem,
            'options': question.to_dict()['options'],
            'coding_meta': question.coding_meta() if qtype == 'coding' else None,
            'status': progress.status if progress else 'pending',
            'is_correct': progress.is_correct if progress and qtype == 'mcq' else None,
            'code_passed': progress.code_passed if progress and qtype == 'coding' else None,
            'selected_index': progress.selected_index if progress else None,
            'submitted_code': progress.submitted_code if progress else None,
            'sort_order': question.sort_order,
            'published_at': trial.starts_at.isoformat() if trial.starts_at else None,
        }
        from app.services.learning_adaptation import LearningAdaptationService
        adaptation = LearningAdaptationService.active_for_key(progress.user_id if progress else 0, question.knowledge_key)
        if adaptation:
            payload['adaptive_plan'] = adaptation['action_plan']
            payload['effective_difficulty'] = 'lower'
        else:
            payload['adaptive_plan'] = None
            payload['effective_difficulty'] = 'normal'
        return payload

    @staticmethod
    def compute_trial_score(user_id: int, trial_id: int) -> tuple[int, int, int]:
        """返回 (score, answered_count, correct_count)。"""
        questions = AssignmentService._questions_for_trial(trial_id)
        if not questions:
            return 0, 0, 0
        progress_map = AssignmentService._progress_for_user(user_id, [q.id for q in questions])
        answered = 0
        correct = 0
        for question in questions:
            progress = progress_map.get(question.id)
            if not progress or progress.status != 'completed':
                continue
            answered += 1
            if AssignmentService._question_is_correct(question, progress):
                correct += 1
        if not answered:
            return 0, answered, correct
        score = round((correct / len(questions)) * 100)
        return score, answered, correct

    @staticmethod
    def trial_answer_summary(trial_id: int) -> dict:
        questions = AssignmentService._questions_for_trial(trial_id)
        question_count = len(questions)
        if not question_count:
            return {
                'question_count': 0,
                'avg_score': 0,
                'completion_rate': 0,
                'question_stats': [],
            }

        question_ids = [q.id for q in questions]
        progress_rows = TrialQuestionProgress.query.filter(
            TrialQuestionProgress.question_id.in_(question_ids),
            TrialQuestionProgress.status == 'completed',
        ).all()
        by_question: dict[int, list[TrialQuestionProgress]] = {qid: [] for qid in question_ids}
        for row in progress_rows:
            by_question.setdefault(row.question_id, []).append(row)

        question_stats = []
        for question in questions:
            rows = by_question.get(question.id, [])
            answered = len(rows)
            correct = len([r for r in rows if AssignmentService._question_is_correct(question, r)])
            avg_time = round(sum(r.time_spent_sec or 0 for r in rows) / answered) if answered else 0
            question_stats.append(
                {
                    'question_id': question.id,
                    'sort_order': question.sort_order,
                    'stem': question.stem,
                    'knowledge_key': question.knowledge_key,
                    'knowledge_label': QuestionGenerator.label_for_key(question.knowledge_key),
                    'answered_count': answered,
                    'correct_count': correct,
                    'correct_rate': round((correct / answered) * 100) if answered else 0,
                    'avg_time_spent_sec': avg_time,
                }
            )

        parts = TrialParticipation.query.filter_by(trial_id=trial_id).all()
        completed_parts = [p for p in parts if p.status == 'completed']
        avg_score = round(sum(p.score or 0 for p in completed_parts) / len(completed_parts)) if completed_parts else 0
        participant_count = len({p.user_id for p in parts})
        completion_rate = round((len(completed_parts) / participant_count) * 100) if participant_count else 0
        return {
            'question_count': question_count,
            'avg_score': avg_score,
            'completion_rate': completion_rate,
            'question_stats': question_stats,
        }

    @staticmethod
    def _maybe_auto_complete_trial(user_id: int, trial_id: int):
        trial = db.session.get(Trial, trial_id)
        if not trial:
            return None
        questions = AssignmentService._questions_for_trial(trial_id)
        if not questions:
            return None
        progress_map = AssignmentService._progress_for_user(user_id, [q.id for q in questions])
        for question in questions:
            progress = progress_map.get(question.id)
            if not progress or progress.status != 'completed':
                return None
        part = TrialParticipation.query.filter_by(trial_id=trial_id, user_id=user_id).first()
        if part and part.status == 'completed':
            return None
        score, _, _ = AssignmentService.compute_trial_score(user_id, trial_id)
        return TrialService.complete_trial(user_id, trial_id, score)

    @staticmethod
    def _active_trials_for_student(user: User):
        if not user.class_id:
            return []
        trials = (
            Trial.query.filter_by(class_id=user.class_id)
            .filter(Trial.status.in_(('running', 'scheduled')))
            .order_by(Trial.created_at.desc())
            .all()
        )
        dirty = False
        active = []
        for trial in trials:
            if TrialService._sync_trial_status(trial):
                dirty = True
            if TrialService.effective_status(trial) in ('running', 'scheduled'):
                active.append(trial)
        if dirty:
            db.session.commit()
        return active

    @staticmethod
    def _get_or_create_progress(user_id: int, question_id: int) -> TrialQuestionProgress:
        row = TrialQuestionProgress.query.filter_by(user_id=user_id, question_id=question_id).first()
        if row:
            return row
        row = TrialQuestionProgress(user_id=user_id, question_id=question_id, status='pending')
        row.started_at = utc_now()
        db.session.add(row)
        db.session.flush()
        return row

    @staticmethod
    def list_for_student(user_id: int, include_completed: bool = False):
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError('用户不存在')

        trials = AssignmentService._active_trials_for_student(user)
        for trial in trials:
            QuestionGenerator.materialize_trial_questions(trial)

        items = []
        pending_count = 0
        for trial in trials:
            teacher_name = trial.teacher.real_name if trial.teacher else '老师'
            questions = (
                TrialQuestion.query.filter_by(trial_id=trial.id)
                .order_by(TrialQuestion.sort_order.asc(), TrialQuestion.id.asc())
                .all()
            )
            for question in questions:
                progress = AssignmentService._get_or_create_progress(user_id, question.id)
                if progress.status == 'completed' and not include_completed:
                    continue
                if progress.status == 'pending':
                    pending_count += 1
                items.append(
                    {
                        'id': question.id,
                        'trial_id': trial.id,
                        'trial_title': trial.title,
                        'teacher_name': teacher_name,
                        'knowledge_key': question.knowledge_key,
                        'knowledge_label': QuestionGenerator.label_for_key(question.knowledge_key),
                        'stem': question.stem,
                        'options': question.to_dict()['options'],
                        'status': progress.status,
                        'is_correct': progress.is_correct,
                        'selected_index': progress.selected_index,
                        'sort_order': question.sort_order,
                        'published_at': trial.starts_at.isoformat() if trial.starts_at else None,
                    }
                )
        db.session.commit()

        return {
            'pending_count': pending_count,
            'total_count': len(items) if include_completed else pending_count,
            'items': items,
        }

    @staticmethod
    def submit_answer(user_id: int, question_id: int, selected_index: int, time_spent_sec: int | None = None):
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError('用户不存在')
        question = db.session.get(TrialQuestion, question_id)
        if not question:
            raise ValueError('题目不存在')

        trial = db.session.get(Trial, question.trial_id)
        if not trial or trial.class_id != user.class_id:
            raise PermissionError('无权作答该题目')
        if TrialService.effective_status(trial) not in ('running', 'scheduled'):
            raise ValueError('试炼已结束，无法作答')

        progress = AssignmentService._get_or_create_progress(user_id, question_id)
        if progress.status == 'completed':
            raise ValueError('该题已完成')

        AssignmentService._touch_question_start(progress)
        now = utc_now()
        selected = int(selected_index)
        is_correct = selected == int(question.correct_index)
        elapsed = time_spent_sec
        if elapsed is None and progress.started_at:
            elapsed = max(1, int((now - progress.started_at).total_seconds()))
        if elapsed is None:
            elapsed = 0

        progress.status = 'completed'
        progress.selected_index = selected
        progress.selected_label = AssignmentService._option_label(selected)
        progress.is_correct = is_correct
        progress.answered_at = now
        progress.time_spent_sec = int(elapsed)

        from app.services.grading_orchestrator import GradingOrchestrator

        grade_result = {'correct': is_correct}
        agent_trace = GradingOrchestrator.run_after_submit(
            user_id=user_id,
            question=question,
            progress=progress,
            grade_result=grade_result,
        )
        progress.set_agent_trace(agent_trace)
        agent_trace_summary = GradingOrchestrator.summarize_trace(agent_trace)
        db.session.commit()

        from app.services.mistake import MistakeService

        if is_correct:
            MistakeService.record_mcq_correct(user_id, question_id)
        else:
            MistakeService.record_mcq_wrong(user_id, question)
        from app.services.learning_adaptation import LearningAdaptationService
        adaptation = LearningAdaptationService.record_answer(user_id, question, is_correct)

        daily_payload = None
        incentive = None
        if is_correct:
            try:
                daily_payload = DailyQuestService.advance_progress(user_id, 'fragment-repair')
                incentive = daily_payload.get('incentive')
            except Exception:
                daily_payload = DailyQuestService.get_today(user_id)

        assignments = AssignmentService.list_for_student(user_id)
        trial_complete = AssignmentService._maybe_auto_complete_trial(user_id, trial.id)
        return {
            'correct': is_correct,
            'correct_index': question.correct_index,
            'time_spent_sec': progress.time_spent_sec,
            'answered_at': progress.answered_at.isoformat() if progress.answered_at else None,
            'assignments': assignments,
            'daily': daily_payload,
            'incentive': incentive,
            'trial_complete': trial_complete,
            'adaptation': adaptation,
            'agent_trace': agent_trace_summary,
        }

    @staticmethod
    def submit_code_answer(user_id: int, question_id: int, code: str, time_spent_sec: int | None = None):
        from app.services.code_execution import CodeExecutionService

        user = db.session.get(User, user_id)
        if not user:
            raise ValueError('用户不存在')
        question = db.session.get(TrialQuestion, question_id)
        if not question or (question.question_type or 'mcq') != 'coding':
            raise ValueError('编程题目不存在')

        trial = db.session.get(Trial, question.trial_id)
        if not trial or trial.class_id != user.class_id:
            raise PermissionError('无权作答该题目')
        if TrialService.effective_status(trial) not in ('running', 'scheduled'):
            raise ValueError('试炼已结束，无法作答')

        meta = question.coding_meta()
        test_cases = meta.get('test_cases') or []
        if not test_cases:
            raise ValueError('题目缺少测试用例')

        progress = AssignmentService._get_or_create_progress(user_id, question_id)
        if progress.status == 'completed':
            raise ValueError('该题已完成')

        AssignmentService._touch_question_start(progress)
        now = utc_now()
        elapsed = time_spent_sec
        if elapsed is None and progress.started_at:
            elapsed = max(1, int((now - progress.started_at).total_seconds()))
        if elapsed is None:
            elapsed = 0

        submit_result = CodeExecutionService.submit(
            'python',
            code,
            test_cases,
            meta.get('run_mode') or 'stdout',
        )
        all_passed = bool(submit_result.get('all_passed'))
        results = submit_result.get('results') or []

        progress.status = 'completed'
        progress.submitted_code = code
        progress.code_passed = all_passed
        progress.is_correct = all_passed
        progress.set_code_results(results)
        progress.answered_at = now
        progress.time_spent_sec = int(elapsed)

        from app.services.grading_orchestrator import GradingOrchestrator

        grade_result = {
            'code_passed': all_passed,
            'passed_count': submit_result.get('passed_count', 0),
            'total': submit_result.get('total', len(test_cases)),
            'results': results,
            'execution_backend': submit_result.get('backend'),
        }
        agent_trace = GradingOrchestrator.run_after_submit(
            user_id=user_id,
            question=question,
            progress=progress,
            grade_result=grade_result,
        )
        progress.set_agent_trace(agent_trace)
        agent_trace_summary = GradingOrchestrator.summarize_trace(agent_trace)
        db.session.commit()

        from app.services.mistake import MistakeService

        if not all_passed:
            MistakeService.record_code_trial_run(
                user_id,
                {
                    'question_id': str(question.id),
                    'title': question.stem[:80],
                    'topic': question.knowledge_key or 'coding',
                    'passed_count': submit_result.get('passed_count', 0),
                    'total_cases': submit_result.get('total', len(test_cases)),
                },
            )
        from app.services.learning_adaptation import LearningAdaptationService
        adaptation = LearningAdaptationService.record_answer(user_id, question, all_passed)

        trial_complete = AssignmentService._maybe_auto_complete_trial(user_id, trial.id)
        return {
            'code_passed': all_passed,
            'passed_count': submit_result.get('passed_count', 0),
            'total': submit_result.get('total', len(test_cases)),
            'results': results,
            'time_spent_sec': progress.time_spent_sec,
            'answered_at': progress.answered_at.isoformat() if progress.answered_at else None,
            'trial_complete': trial_complete,
            'adaptation': adaptation,
            'agent_trace': agent_trace_summary,
        }

    @staticmethod
    def list_for_trial(user_id: int, trial_id: int):
        user = db.session.get(User, user_id)
        trial = db.session.get(Trial, trial_id)
        if not user or not trial:
            raise ValueError('试炼或用户不存在')
        if not user.class_id or user.class_id != trial.class_id:
            raise PermissionError('无权访问该试炼题目')
        if TrialService.effective_status(trial) not in ('running', 'scheduled', 'ended'):
            raise ValueError('试炼不可用')

        QuestionGenerator.materialize_trial_questions(trial)
        questions = AssignmentService._questions_for_trial(trial_id)
        progress_map = AssignmentService._progress_for_user(user_id, [q.id for q in questions])
        items = []
        pending_count = 0
        for question in questions:
            progress = progress_map.get(question.id)
            if not progress:
                progress = AssignmentService._get_or_create_progress(user_id, question.id)
            else:
                AssignmentService._touch_question_start(progress)
            if progress.status == 'pending':
                pending_count += 1
            items.append(AssignmentService._serialize_question_item(question, progress, trial))
        db.session.commit()

        score, answered_count, correct_count = AssignmentService.compute_trial_score(user_id, trial_id)
        part = TrialParticipation.query.filter_by(trial_id=trial_id, user_id=user_id).first()
        return {
            'trial_id': trial_id,
            'trial_title': trial.title,
            'question_count': len(items),
            'pending_count': pending_count,
            'answered_count': answered_count,
            'correct_count': correct_count,
            'score': score,
            'my_status': part.status if part else None,
            'items': items,
        }

    @staticmethod
    def _class_students(class_id: int) -> list[User]:
        students = User.query.filter_by(class_id=class_id).all()
        return [s for s in students if s.role and s.role.name == 'student']

    @staticmethod
    def _student_progress_rows_for_trial(trial: Trial, students: list[User]) -> list[dict]:
        QuestionGenerator.materialize_trial_questions(trial)
        questions = AssignmentService._questions_for_trial(trial.id)
        question_ids = [q.id for q in questions]
        rows = []
        for student in students:
            part = TrialParticipation.query.filter_by(trial_id=trial.id, user_id=student.id).first()
            progress_map = AssignmentService._progress_for_user(student.id, question_ids)
            answered = 0
            correct = 0
            total_time = 0
            answer_records = []
            for question in questions:
                progress = progress_map.get(question.id)
                record = AssignmentService._build_answer_record(question, progress)
                answer_records.append(record)
                if progress and progress.status == 'completed':
                    answered += 1
                    if AssignmentService._question_is_correct(question, progress):
                        correct += 1
                    if progress.time_spent_sec:
                        total_time += int(progress.time_spent_sec)
            rows.append(
                {
                    'user_id': student.id,
                    'username': student.username,
                    'real_name': student.real_name or student.username,
                    'participation_status': part.status if part else None,
                    'score': part.score if part else 0,
                    'answered_count': answered,
                    'correct_count': correct,
                    'question_total': len(question_ids),
                    'total_time_spent_sec': total_time,
                    'joined_at': part.joined_at.isoformat() if part and part.joined_at else None,
                    'completed_at': part.completed_at.isoformat() if part and part.completed_at else None,
                    'answers': answer_records,
                }
            )
        return rows

    @staticmethod
    def get_trial_detail_for_teacher(current_user_id: int, trial_id: int, role_name: str):
        trial = db.session.get(Trial, trial_id)
        if not trial:
            raise ValueError('试炼不存在')
        TrialService._get_teacher_class(trial.class_id, current_user_id, role_name)
        if role_name == 'teacher' and trial.teacher_id != current_user_id:
            raise PermissionError('不能查看他人创建的试炼')

        if trial.status == 'draft':
            questions_payload = trial.draft_questions()
            questions = []
        else:
            QuestionGenerator.materialize_trial_questions(trial)
            questions = AssignmentService._questions_for_trial(trial_id)
            questions_payload = [q.to_dict(include_answer=True) for q in questions]

        cls = db.session.get(Class, trial.class_id)
        student_rows = (
            AssignmentService._student_progress_rows_for_trial(
                trial, AssignmentService._class_students(trial.class_id)
            )
            if trial.status != 'draft'
            else []
        )
        answer_summary = (
            AssignmentService.trial_answer_summary(trial_id)
            if trial.status != 'draft'
            else {'question_count': len(questions_payload), 'avg_score': 0, 'completion_rate': 0, 'question_stats': []}
        )
        return {
            'trial': trial.to_dict(
                include_stats=True,
                effective_status=TrialService.effective_status(trial),
            ),
            'class_name': cls.name if cls else '',
            'teacher_name': (trial.teacher.real_name or trial.teacher.username) if trial.teacher else '',
            'questions': questions_payload,
            'draft_questions': trial.draft_questions() if trial.status == 'draft' else [],
            'students': student_rows,
            'summary': answer_summary,
        }

    @staticmethod
    def get_class_answer_board(current_user_id: int, class_id: int, role_name: str):
        TrialService._get_teacher_class(class_id, current_user_id, role_name)
        cls = db.session.get(Class, class_id)
        if not cls:
            raise ValueError('班级不存在')

        trials = (
            Trial.query.filter_by(class_id=class_id)
            .order_by(Trial.created_at.desc())
            .limit(30)
            .all()
        )
        dirty = False
        for trial in trials:
            if TrialService._sync_trial_status(trial):
                dirty = True
        if dirty:
            db.session.commit()

        students = AssignmentService._class_students(class_id)
        trial_items = []
        for trial in trials:
            student_rows = AssignmentService._student_progress_rows_for_trial(trial, students)
            has_activity = any(s['answered_count'] > 0 or s['participation_status'] for s in student_rows)
            trial_items.append(
                {
                    'trial': trial.to_dict(
                        include_stats=True,
                        effective_status=TrialService.effective_status(trial),
                    ),
                    'summary': AssignmentService.trial_answer_summary(trial.id),
                    'students': student_rows,
                    'has_activity': has_activity,
                }
            )

        active_count = sum(1 for item in trial_items if item['trial'].get('effective_status') == 'running')
        submitted_total = sum(
            sum(1 for s in item['students'] if s['answered_count'] > 0) for item in trial_items
        )
        return {
            'class_id': class_id,
            'class_name': cls.name,
            'student_count': len(students),
            'trial_count': len(trial_items),
            'active_trial_count': active_count,
            'submitted_total': submitted_total,
            'sync_note': '数据来自学生端试炼关卡 / 探索舱 / 今日委托的实时提交',
            'trials': trial_items,
        }

    @staticmethod
    def get_student_answer_board(current_user_id: int, student_id: int, role_name: str):
        student = db.session.get(User, student_id)
        if not student or not student.class_id:
            raise ValueError('学生不存在或未分班')
        if not student.role or student.role.name != 'student':
            raise ValueError('目标用户不是学生')

        TrialService._get_teacher_class(student.class_id, current_user_id, role_name)

        trials = (
            Trial.query.filter_by(class_id=student.class_id)
            .order_by(Trial.created_at.desc())
            .limit(30)
            .all()
        )
        for trial in trials:
            TrialService._sync_trial_status(trial, commit=False)
        db.session.commit()

        items = []
        for trial in trials:
            rows = AssignmentService._student_progress_rows_for_trial(trial, [student])
            row = rows[0] if rows else None
            if not row:
                continue
            items.append(
                {
                    'trial': trial.to_dict(
                        include_stats=True,
                        effective_status=TrialService.effective_status(trial),
                    ),
                    'participation_status': row['participation_status'],
                    'score': row['score'],
                    'answered_count': row['answered_count'],
                    'correct_count': row['correct_count'],
                    'question_total': row['question_total'],
                    'total_time_spent_sec': row['total_time_spent_sec'],
                    'joined_at': row['joined_at'],
                    'completed_at': row['completed_at'],
                    'answers': row['answers'],
                }
            )

        return {
            'student_id': student.id,
            'username': student.username,
            'real_name': student.real_name or student.username,
            'class_id': student.class_id,
            'trials': items,
        }

    @staticmethod
    def list_admin_trials(class_id: int | None = None):
        query = Trial.query.order_by(Trial.created_at.desc())
        if class_id:
            query = query.filter_by(class_id=class_id)
        trials = query.limit(100).all()
        dirty = False
        for trial in trials:
            if TrialService._sync_trial_status(trial):
                dirty = True
        if dirty:
            db.session.commit()

        rows = []
        for trial in trials:
            cls = db.session.get(Class, trial.class_id)
            summary = AssignmentService.trial_answer_summary(trial.id)
            row = trial.to_dict(
                include_stats=True,
                effective_status=TrialService.effective_status(trial),
            )
            row['class_name'] = cls.name if cls else ''
            row['teacher_name'] = (trial.teacher.real_name or trial.teacher.username) if trial.teacher else ''
            row['question_count'] = summary['question_count']
            row['avg_score'] = summary['avg_score']
            rows.append(row)
        return {'trials': rows, 'total': len(rows)}
