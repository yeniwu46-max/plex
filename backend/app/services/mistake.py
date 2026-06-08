"""错题本：写入、查询、薄弱知识点"""
from collections import defaultdict
from datetime import datetime

from app.models import StudentMistake, TrialQuestion, User, db
from app.services.question_generator import QuestionGenerator


class MistakeService:
    @staticmethod
    def _upsert(
        user_id: int,
        *,
        source: str,
        knowledge_key: str,
        question_ref: str,
        question_title: str | None = None,
        error_type: str | None = None,
        meta: dict | None = None,
        passed: bool = False,
    ) -> StudentMistake | None:
        now = datetime.utcnow()
        key = QuestionGenerator._normalize_key(knowledge_key)
        ref = str(question_ref)
        row = StudentMistake.query.filter_by(
            user_id=user_id,
            source=source,
            question_ref=ref,
        ).first()

        if passed:
            if not row:
                return None
            row.last_passed_at = now
            db.session.commit()
            return row

        merged_meta = dict(meta or {})
        if question_title:
            merged_meta['question_title'] = question_title
        merged_meta['knowledge_label'] = QuestionGenerator.label_for_key(key)

        if row:
            row.fail_count = (row.fail_count or 0) + 1
            row.last_failed_at = now
            row.knowledge_key = key
            row.error_type = error_type or row.error_type
            if merged_meta:
                existing = row.meta if isinstance(row.meta, dict) else {}
                existing.update(merged_meta)
                row.meta = existing
            if question_title:
                row.question_title = question_title
        else:
            row = StudentMistake(
                user_id=user_id,
                source=source,
                knowledge_key=key,
                question_ref=ref,
                question_title=question_title,
                error_type=error_type,
                fail_count=1,
                last_failed_at=now,
                meta=merged_meta,
            )
            db.session.add(row)

        db.session.commit()
        from app.services.student_profile import StudentProfileService

        StudentProfileService.create_behavior_suggestion(user_id)
        return row

    @staticmethod
    def record_mcq_wrong(user_id: int, question: TrialQuestion):
        return MistakeService._upsert(
            user_id,
            source='mcq',
            knowledge_key=question.knowledge_key or 'algo',
            question_ref=str(question.id),
            question_title=(question.stem or '')[:200],
            error_type='wrong_answer',
            meta={
                'stem_preview': (question.stem or '')[:120],
                'trial_id': question.trial_id,
            },
        )

    @staticmethod
    def record_mcq_correct(user_id: int, question_id: int):
        question = TrialQuestion.query.get(question_id)
        if not question:
            return None
        return MistakeService._upsert(
            user_id,
            source='mcq',
            knowledge_key=question.knowledge_key or 'algo',
            question_ref=str(question_id),
            passed=True,
        )

    @staticmethod
    def record_code_trial_run(user_id: int, payload: dict):
        question_id = str(payload.get('question_id') or '')
        if not question_id:
            raise ValueError('question_id 不能为空')

        cases = payload.get('cases') or []
        all_passed = bool(cases) and all(item.get('passed') for item in cases)
        failed = [item for item in cases if not item.get('passed')]
        error_types = []
        if failed:
            if any(item.get('error') for item in failed):
                error_types.append('runtime_error')
            if any(not item.get('error') for item in failed):
                error_types.append('wrong_output')

        knowledge_key = payload.get('knowledge_key') or 'algo'
        meta = {
            'topic': payload.get('topic') or '',
            'tags': payload.get('tags') or [],
            'star_path_node_id': payload.get('star_path_node_id'),
            'star_path_node_title': payload.get('star_path_node_title'),
            'failed_case_labels': [item.get('label') for item in failed if item.get('label')],
            'error_types': error_types,
        }

        if all_passed:
            return MistakeService._upsert(
                user_id,
                source='code_trial',
                knowledge_key=knowledge_key,
                question_ref=question_id,
                question_title=payload.get('question_title'),
                meta=meta,
                passed=True,
            )

        primary_error = error_types[0] if error_types else 'wrong_output'
        return MistakeService._upsert(
            user_id,
            source='code_trial',
            knowledge_key=knowledge_key,
            question_ref=question_id,
            question_title=payload.get('question_title'),
            error_type=primary_error,
            meta=meta,
        )

    @staticmethod
    def record_emergency_wrong(user_id: int, focus_key: str, question_stems: list[str]):
        for index, stem in enumerate(question_stems):
            MistakeService._upsert(
                user_id,
                source='emergency',
                knowledge_key=focus_key,
                question_ref=f'emergency:{focus_key}:{index}',
                question_title=(stem or '')[:200],
                error_type='wrong_answer',
            )

    @staticmethod
    def _is_active(row: StudentMistake) -> bool:
        if not row.last_failed_at:
            return False
        if not row.last_passed_at:
            return True
        return row.last_passed_at < row.last_failed_at

    @staticmethod
    def list_for_student(user_id: int, *, knowledge_key: str | None = None, active_only: bool = True):
        query = StudentMistake.query.filter_by(user_id=user_id).order_by(
            StudentMistake.last_failed_at.desc()
        )
        if knowledge_key:
            key = QuestionGenerator._normalize_key(knowledge_key)
            query = query.filter_by(knowledge_key=key)

        rows = query.all()
        if active_only:
            rows = [row for row in rows if MistakeService._is_active(row)]
        return [row.to_dict() for row in rows]

    @staticmethod
    def list_weak_knowledge(user_id: int, limit: int = 5) -> list[dict]:
        rows = StudentMistake.query.filter_by(user_id=user_id).all()
        active = [row for row in rows if MistakeService._is_active(row)]
        if not active:
            return []

        scores: dict[str, dict] = defaultdict(lambda: {'fail_count': 0, 'weight': 0.0})
        now = datetime.utcnow()
        for row in active:
            key = row.knowledge_key or 'algo'
            bucket = scores[key]
            bucket['fail_count'] += row.fail_count or 1
            days_ago = max(0, (now - row.last_failed_at).days) if row.last_failed_at else 7
            bucket['weight'] += (row.fail_count or 1) * (1.0 + max(0, 7 - days_ago) * 0.15)

        ranked = sorted(scores.items(), key=lambda item: -item[1]['weight'])
        result = []
        for key, stats in ranked[:limit]:
            result.append(
                {
                    'knowledge_key': key,
                    'knowledge_label': QuestionGenerator.label_for_key(key),
                    'fail_count': stats['fail_count'],
                    'weight': round(stats['weight'], 2),
                }
            )
        return result

    @staticmethod
    def list_for_teacher_student(current_user_id: int, student_id: int, role_name: str):
        from app.services.trial import TrialService

        student = User.query.get(student_id)
        if not student or not student.class_id:
            raise ValueError('学生不存在或未分班')
        if not student.role or student.role.name != 'student':
            raise ValueError('目标用户不是学生')

        TrialService._get_teacher_class(student.class_id, current_user_id, role_name)
        rows = StudentMistake.query.filter_by(user_id=student_id).order_by(
            StudentMistake.last_failed_at.desc()
        ).all()
        items = [row.to_dict() for row in rows]
        weak = MistakeService.list_weak_knowledge(student_id)
        return {
            'student_id': student.id,
            'username': student.username,
            'real_name': student.real_name or student.username,
            'items': items,
            'weak_knowledge': weak,
            'active_count': len([row for row in rows if MistakeService._is_active(row)]),
        }

    @staticmethod
    def sync_mcq_from_progress(user_id: int):
        """从已有错题进度回填错题本（幂等，供迁移或修复）。"""
        from app.models import TrialQuestionProgress

        rows = (
            TrialQuestionProgress.query.filter_by(user_id=user_id, status='completed', is_correct=False)
            .order_by(TrialQuestionProgress.answered_at.desc())
            .all()
        )
        for progress in rows:
            question = TrialQuestion.query.get(progress.question_id)
            if question:
                MistakeService.record_mcq_wrong(user_id, question)
