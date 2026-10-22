"""Transactional arrival numbers, self-reported profiles, and appearance."""
from sqlalchemy.exc import IntegrityError
from app.models import db, StudentOnboarding, AdventurerCounter, UserAppearance
from app.services.student_profile import StudentProfileService
from app.utils.time import utc_now

OPTIONS = {
    'age_range': dict(zip(['under13', '13_15', '16_18', '19_24', '25_34', '35plus', 'private'],
        ['12 岁及以下', '13–15 岁', '16–18 岁', '19–24 岁', '25–34 岁', '35 岁及以上', '不愿透露'])),
    'programming_level': dict(zip(['none', 'syntax', 'exercises', 'projects', 'professional', 'unknown'],
        ['完全零基础', '了解基本语法', '能独立完成小练习', '做过完整项目', '有工作经验', '暂不确定'])),
    'field': dict(zip(['student', 'software', 'engineering', 'education', 'creative', 'business', 'other', 'private'],
        ['在校学习', '软件与互联网', '理工与制造', '教育与科研', '设计与内容', '商业与运营', '其他', '暂不透露'])),
}


class OnboardingService:
    @staticmethod
    def init_counter():
        if db.session.get(AdventurerCounter, 1) is None:
            highest = db.session.query(db.func.max(StudentOnboarding.adventurer_number)).scalar() or 200
            db.session.add(AdventurerCounter(id=1, last_number=max(200, highest)))
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

    @staticmethod
    def enroll(user):
        """Call within the new-account transaction, never from demo seed/login."""
        db.session.flush()
        db.session.add(StudentOnboarding(user_id=user.id, status='pending'))

    @staticmethod
    def summary(user_id):
        row = db.session.get(StudentOnboarding, user_id)
        status = row.status if row else 'exempt'
        number = row.adventurer_number if row else None
        welcome = bool(number is not None and row.welcomed_at is None)
        return {'status': status, 'adventurer_number': number, 'welcome_pending': welcome,
                'required': status == 'pending' or welcome}

    @staticmethod
    def account_fields(user_id):
        appearance = db.session.get(UserAppearance, user_id)
        return {'onboarding': OnboardingService.summary(user_id),
                'preferences': appearance.to_dict() if appearance else None}

    @staticmethod
    def get(user_id):
        row = db.session.get(StudentOnboarding, user_id)
        return {**OnboardingService.account_fields(user_id), 'answers': (row.answers or {}) if row else {},
                'draft': (row.draft or {}) if row else {}, 'step': row.step if row else 1,
                'survey_version': 1, 'options': OPTIONS}

    @staticmethod
    def validate_answers(raw, partial=False):
        if not isinstance(raw, dict) or set(raw) - {*OPTIONS, 'field_detail'}:
            raise ValueError('问卷字段无效')
        clean = {}
        for key, choices in OPTIONS.items():
            value = raw.get(key)
            if partial and value in (None, ''):
                continue
            if not isinstance(value, str) or value not in choices:
                raise ValueError('请选择有效的年龄范围、编程基础和从事领域')
            clean[key] = value
        detail = raw.get('field_detail', '')
        if not isinstance(detail, str) or len(detail.strip()) > 50:
            raise ValueError('领域补充说明不能超过 50 字')
        clean['field_detail'] = detail.strip() if clean.get('field') == 'other' else ''
        return clean

    @staticmethod
    def set_appearance(user_id, raw):
        if not isinstance(raw, dict) or set(raw) != {'visual_style', 'color_mode'}:
            raise ValueError('外观设置字段无效')
        if raw['visual_style'] not in ('space', 'comic') or raw['color_mode'] not in ('dark', 'light', 'auto'):
            raise ValueError('请选择有效的主题与明暗模式')
        # Serialize writes for the same account, including first preference save.
        from app.models import User
        User.query.filter_by(id=user_id).update({User.id: User.id}, synchronize_session=False)
        values = {'user_id': user_id, **raw}
        # An upsert avoids InnoDB gap locks when several accounts save their
        # first preference simultaneously. Read the row only after insertion.
        if db.engine.dialect.name == 'mysql':
            from sqlalchemy.dialects.mysql import insert
            statement = insert(UserAppearance).values(**values).on_duplicate_key_update(**raw)
        else:
            from sqlalchemy.dialects.sqlite import insert
            statement = insert(UserAppearance).values(**values).on_conflict_do_update(index_elements=['user_id'], set_=raw)
        db.session.execute(statement)
        return db.session.get(UserAppearance, user_id, populate_existing=True, with_for_update=True)

    @staticmethod
    def apply_profile(user_id, answers):
        profile = StudentProfileService.get_or_create(user_id, persist=True, commit=False)
        changes = {}
        for field, dimension, unknown in [('programming_level', 'knowledge_foundation', 'unknown'), ('field', 'major_background', 'private')]:
            code = answers[field]
            if code == unknown or (field == 'field' and code == 'other' and not answers['field_detail']):
                old = (profile.dimensions or {}).get(dimension) or {}
                if old.get('origin') == 'onboarding':
                    changes[dimension] = {'value': None, 'confidence': 0, 'evidence': ['入驻问卷：用户选择暂不说明'], 'source': 'confirmed', 'origin': 'onboarding'}
                continue
            label = OPTIONS[field][code]
            if field == 'field' and code == 'other':
                if not answers['field_detail']:
                    continue
                label = answers['field_detail']
            changes[dimension] = {'value': label, 'confidence': .7, 'source': 'confirmed', 'origin': 'onboarding',
                                  'evidence': [f'入驻问卷 v1：用户自述“{label}”，未经能力测评']}
        if changes:
            StudentProfileService.apply_changes(user_id, changes, reason='onboarding_survey', commit=False)

    @staticmethod
    def patch(user_id, payload):
        if set(payload) - {'answers', 'step', 'preferences', 'draft_only'} or 'answers' not in payload:
            raise ValueError('问卷字段无效')
        if 'draft_only' in payload and type(payload['draft_only']) is not bool:
            raise ValueError('草稿标记无效')
        # A write lock precedes reads so edits cannot race completion.
        from app.models import User
        User.query.filter_by(id=user_id).update({User.id: User.id}, synchronize_session=False)
        row = db.session.get(StudentOnboarding, user_id, populate_existing=True, with_for_update=True)
        if row is None:
            row = StudentOnboarding(user_id=user_id, status='exempt')
            db.session.add(row)
        pending = row.status == 'pending'
        if payload.get('draft_only') and not pending:
            db.session.rollback()
            return OnboardingService.get(user_id)
        answers = OnboardingService.validate_answers(payload['answers'], partial=pending)
        if 'preferences' in payload:
            OnboardingService.set_appearance(user_id, payload['preferences'])
        if pending:
            step = payload.get('step', 1)
            if type(step) is not int or step not in (1, 2):
                raise ValueError('问卷步骤无效')
            row.draft, row.step = answers, step
        else:
            row.answers = answers
            OnboardingService.apply_profile(user_id, answers)
        db.session.commit()
        return OnboardingService.get(user_id)

    @staticmethod
    def complete(user_id, payload):
        if set(payload) - {'action', 'answers', 'preferences'} or payload.get('action') not in ('submit', 'skip'):
            raise ValueError('请选择提交或稍后填写')
        from app.models import User
        User.query.filter_by(id=user_id).update({User.id: User.id}, synchronize_session=False)
        row = db.session.get(StudentOnboarding, user_id, populate_existing=True, with_for_update=True)
        if not row or row.status == 'exempt':
            raise ValueError('已有账号请通过入驻资料入口补填')
        if row.status != 'pending':
            db.session.rollback()
            return OnboardingService.get(user_id)
        answers = OnboardingService.validate_answers(payload.get('answers')) if payload['action'] == 'submit' else {}
        OnboardingService.set_appearance(user_id, payload.get('preferences'))
        claimed = StudentOnboarding.query.filter_by(user_id=user_id, status='pending').update(
            {'status': 'completed' if payload['action'] == 'submit' else 'skipped'}, synchronize_session=False)
        if claimed != 1:
            db.session.rollback()
            return OnboardingService.get(user_id)
        updated = AdventurerCounter.query.filter_by(id=1).update(
            {AdventurerCounter.last_number: AdventurerCounter.last_number + 1}, synchronize_session=False)
        if updated != 1:
            raise RuntimeError('Onboarding counter migration is missing')
        number = db.session.query(AdventurerCounter.last_number).filter_by(id=1).scalar()
        row = db.session.get(StudentOnboarding, user_id, populate_existing=True)
        row.adventurer_number, row.answers, row.draft = number, answers, {}
        row.completed_at = utc_now()
        if answers:
            OnboardingService.apply_profile(user_id, answers)
        db.session.commit()
        return OnboardingService.get(user_id)

    @staticmethod
    def acknowledge(user_id):
        StudentOnboarding.query.filter(StudentOnboarding.user_id == user_id,
            StudentOnboarding.adventurer_number.isnot(None), StudentOnboarding.welcomed_at.is_(None)).update(
                {'welcomed_at': utc_now()}, synchronize_session=False)
        db.session.commit()
        return OnboardingService.get(user_id)
