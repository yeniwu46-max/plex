"""错题本：写入、查询、薄弱知识点"""
from collections import defaultdict
from datetime import datetime, timedelta

from app.models import StudentMistake, TrialQuestion, User, db
from app.services.question_generator import QuestionGenerator
from app.utils.time import utc_now


class MistakeService:
    SM2_MIN_EASE_FACTOR = 1.3

    @staticmethod
    def _new_review_schedule(now: datetime | None = None) -> dict:
        """Create the initial SM-2 state for a newly recorded mistake."""
        current = now or utc_now()
        return {
            'algorithm': 'SM-2',
            'ease_factor': 2.5,
            'interval_days': 0,
            'repetitions': 0,
            'review_count': 0,
            'last_quality': None,
            'last_reviewed_at': None,
            'due_at': current.isoformat() + 'Z',
        }

    @staticmethod
    def _parse_review_time(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace('Z', ''))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def calculate_sm2(schedule: dict | None, quality: int, now: datetime | None = None) -> dict:
        """Advance an SM-2 schedule using a 0..5 recall-quality score."""
        if isinstance(quality, bool) or not isinstance(quality, int) or not 0 <= quality <= 5:
            raise ValueError('quality 必须是 0 到 5 的整数')

        current = now or utc_now()
        state = dict(schedule or MistakeService._new_review_schedule(current))
        repetitions = max(0, int(state.get('repetitions') or 0))
        previous_interval = max(0, int(state.get('interval_days') or 0))
        ease_factor = max(
            MistakeService.SM2_MIN_EASE_FACTOR,
            float(state.get('ease_factor') or 2.5),
        )

        if quality < 3:
            repetitions = 0
            interval_days = 1
        else:
            if repetitions == 0:
                interval_days = 1
            elif repetitions == 1:
                interval_days = 6
            else:
                interval_days = max(1, round(previous_interval * ease_factor))
            repetitions += 1

        ease_factor = max(
            MistakeService.SM2_MIN_EASE_FACTOR,
            ease_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02),
        )
        due_at = current + timedelta(days=interval_days)
        return {
            'algorithm': 'SM-2',
            'ease_factor': round(ease_factor, 2),
            'interval_days': interval_days,
            'repetitions': repetitions,
            'review_count': int(state.get('review_count') or 0) + 1,
            'last_quality': quality,
            'last_reviewed_at': current.isoformat() + 'Z',
            'due_at': due_at.isoformat() + 'Z',
        }

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
        now = utc_now()
        key = QuestionGenerator._normalize_key(knowledge_key)
        ref = str(question_ref)
        row = StudentMistake.query.filter_by(
            user_id=user_id,
            source=source,
            question_ref=ref,
        ).first()

        merged_meta = dict(meta or {})
        if question_title:
            merged_meta['question_title'] = question_title
        merged_meta['knowledge_label'] = QuestionGenerator.label_for_key(key)

        if not passed:
            existing_meta = row.meta if row and isinstance(row.meta, dict) else {}
            previous_schedule = existing_meta.get('review_schedule')
            schedule = dict(previous_schedule) if isinstance(previous_schedule, dict) else MistakeService._new_review_schedule(now)
            # A fresh failure makes the item immediately due while preserving its review history.
            schedule['repetitions'] = 0
            schedule['interval_days'] = 0
            schedule['due_at'] = now.isoformat() + 'Z'
            merged_meta['review_schedule'] = schedule

        if passed:
            if not row:
                row = StudentMistake(
                    user_id=user_id,
                    source=source,
                    knowledge_key=key,
                    question_ref=ref,
                    question_title=question_title,
                    fail_count=0,
                    last_failed_at=now,
                    last_passed_at=now,
                    meta=merged_meta or None,
                )
                db.session.add(row)
            else:
                row.last_passed_at = now
                if merged_meta:
                    existing = row.meta if isinstance(row.meta, dict) else {}
                    existing.update(merged_meta)
                    row.meta = existing
            db.session.commit()
            return row

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
        question = db.session.get(TrialQuestion, question_id)
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
        # 诊断引擎可在记录错题时回填四层错因，供历史错因链使用（无需 DB 迁移，meta 为 JSON）。
        if payload.get('error_layer'):
            meta['error_layer'] = payload['error_layer']
        if payload.get('error_subtype'):
            meta['error_subtype'] = payload['error_subtype']

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
    def is_accepted(row: StudentMistake) -> bool:
        if not row.last_passed_at:
            return False
        if not row.last_failed_at:
            return True
        return row.last_passed_at >= row.last_failed_at

    @staticmethod
    def list_accepted_question_refs(user_id: int) -> list[str]:
        rows = StudentMistake.query.filter_by(user_id=user_id).all()
        return [row.question_ref for row in rows if MistakeService.is_accepted(row)]

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
    def list_due_reviews(user_id: int, *, limit: int = 20, now: datetime | None = None) -> dict:
        """Return due SM-2 reviews and lazily enroll historical active mistakes."""
        current = now or utc_now()
        capped_limit = min(max(int(limit), 1), 100)
        rows = StudentMistake.query.filter_by(user_id=user_id).order_by(
            StudentMistake.last_failed_at.desc()
        ).all()
        due_rows = []
        changed = False
        for row in rows:
            meta = dict(row.meta) if isinstance(row.meta, dict) else {}
            schedule = meta.get('review_schedule')
            if not isinstance(schedule, dict):
                if not MistakeService._is_active(row):
                    continue
                schedule = MistakeService._new_review_schedule(row.last_failed_at or current)
                meta['review_schedule'] = schedule
                row.meta = meta
                changed = True
            due_at = MistakeService._parse_review_time(schedule.get('due_at'))
            if due_at is None or due_at <= current:
                due_rows.append(row)

        if changed:
            db.session.commit()
        due_rows.sort(
            key=lambda item: MistakeService._parse_review_time(
                ((item.meta or {}).get('review_schedule') or {}).get('due_at')
            ) or datetime.min
        )
        items = [row.to_dict() for row in due_rows[:capped_limit]]
        return {'items': items, 'total': len(due_rows), 'limit': capped_limit}

    @staticmethod
    def submit_review(user_id: int, mistake_id: int, quality: int) -> dict:
        """Record recall quality, update mastery state, and schedule the next review."""
        row = StudentMistake.query.filter_by(id=mistake_id, user_id=user_id).first()
        if not row:
            raise ValueError('错题不存在')

        now = utc_now()
        meta = dict(row.meta) if isinstance(row.meta, dict) else {}
        schedule = MistakeService.calculate_sm2(meta.get('review_schedule'), quality, now)
        meta['review_schedule'] = schedule
        row.meta = meta
        if quality >= 3:
            row.last_passed_at = now
        else:
            row.fail_count = (row.fail_count or 0) + 1
            row.last_failed_at = now
        db.session.commit()
        return row.to_dict()

    @staticmethod
    def list_recent_with_meta(user_id: int, limit: int = 8) -> list[dict]:
        """返回最近活跃错题的结构化信息（含 error_layer），供诊断历史错因链使用。"""
        rows = (
            StudentMistake.query.filter_by(user_id=user_id)
            .order_by(StudentMistake.last_failed_at.desc())
            .all()
        )
        active = [row for row in rows if MistakeService._is_active(row)]
        result: list[dict] = []
        for row in active[:limit]:
            data = row.to_dict()
            meta = data.get('meta') or {}
            result.append({
                'knowledge_key': data.get('knowledge_key'),
                'knowledge_label': data.get('knowledge_label'),
                'error_type': data.get('error_type'),
                'error_layer': meta.get('error_layer'),
                'error_subtype': meta.get('error_subtype'),
                'fail_count': data.get('fail_count', 1),
                'meta': meta,
            })
        return result

    @staticmethod
    def list_weak_knowledge(user_id: int, limit: int = 5) -> list[dict]:
        rows = StudentMistake.query.filter_by(user_id=user_id).all()
        active = [row for row in rows if MistakeService._is_active(row)]
        if not active:
            return []

        scores: dict[str, dict] = defaultdict(lambda: {'fail_count': 0, 'weight': 0.0})
        now = utc_now()
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

        student = db.session.get(User, student_id)
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
            question = db.session.get(TrialQuestion, progress.question_id)
            if question:
                MistakeService.record_mcq_wrong(user_id, question)
