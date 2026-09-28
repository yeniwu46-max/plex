"""Student store catalog, mock activations, and server-side entitlement checks."""
from datetime import timedelta

from flask import current_app
from sqlalchemy import or_

from app.models import (
    Problem, StoreProduct, StoreProductProblem, UserEntitlement,
    UserChallengeProgress, db,
)
from app.utils.time import utc_now


MEMBERSHIP_CODES = ('explorer_monthly', 'explorer_annual')
CHALLENGE_CODE = 'challenge_pack_algorithms_01'
CHALLENGE_COUNT = 10
CHALLENGE_PROBLEM_CODES = (
    'A001', 'B003', 'BR002', 'D009', 'D015',
    'AR001', 'FN002', 'LP001', 'SE003', 'SE005',
)

PRODUCTS = (
    {
        'code': 'explorer_monthly', 'name': '探索月卡',
        'description': '30 天会员：当前星际挑战包、进阶阶段报告与挑战进度云端存档。',
        'product_type': 'membership', 'price_cents': 990, 'duration_days': 30,
        'benefits_json': [
            '算法基础星际挑战包访问权', '进阶阶段学习报告',
            '挑战通关进度跨设备保存', '会员有效期内可体验当前主题挑战包',
        ], 'sort_order': 10,
    },
    {
        'code': 'explorer_annual', 'name': '探索年卡',
        'description': '365 天会员：当前星际挑战包、进阶阶段报告与挑战进度云端存档。',
        'product_type': 'membership', 'price_cents': 6800, 'duration_days': 365,
        'benefits_json': [
            '算法基础星际挑战包访问权', '进阶阶段学习报告',
            '挑战通关进度跨设备保存', '会员有效期内可体验当前主题挑战包',
        ], 'sort_order': 20,
    },
    {
        'code': CHALLENGE_CODE, 'name': '算法基础 · 星轨挑战包',
        'description': '十道由基础指令逐步进阶到算法实战的星际任务，不影响免费学习主线。',
        'product_type': 'challenge_pack', 'price_cents': 600, 'duration_days': None,
        'benefits_json': [
            '10 道算法基础编程任务', '星际任务简报与分关挑战路线',
            '挑战通关进度跨设备保存', '永久保留该挑战包访问权',
        ], 'sort_order': 30,
    },
)


class StudentStoreService:
    @staticmethod
    def mock_enabled() -> bool:
        return bool(current_app.config.get('STORE_MOCK_ACTIVATION_ENABLED', False))

    @staticmethod
    def ensure_catalog() -> None:
        existing = {row.code: row for row in StoreProduct.query.all()}
        for data in PRODUCTS:
            if data['code'] not in existing:
                product = StoreProduct(**data, is_active=True)
                db.session.add(product)
                existing[product.code] = product
        db.session.flush()

        pack = existing.get(CHALLENGE_CODE)
        if pack and len(pack.challenge_problems) < CHALLENGE_COUNT:
            already = {link.problem_id for link in pack.challenge_problems}
            preferred = Problem.query.filter(
                Problem.problem_no.in_(CHALLENGE_PROBLEM_CODES),
                Problem.is_active.is_(True),
                Problem.question_type == 'coding',
                or_(Problem.needs_review.is_(False), Problem.needs_review.is_(None)),
                ~Problem.id.in_(already or {-1}),
            ).all()
            preferred_by_code = {problem.problem_no: problem for problem in preferred}
            ordered_preferred = [
                preferred_by_code[code] for code in CHALLENGE_PROBLEM_CODES
                if code in preferred_by_code
            ]
            fallback = (
                Problem.query.filter(
                    Problem.is_active.is_(True),
                    Problem.question_type == 'coding',
                    or_(Problem.needs_review.is_(False), Problem.needs_review.is_(None)),
                    ~Problem.id.in_(already | {problem.id for problem in ordered_preferred} or {-1}),
                )
                .order_by(Problem.star_difficulty, Problem.problem_no)
                .limit(max(0, CHALLENGE_COUNT - len(already) - len(ordered_preferred)))
                .all()
            )
            candidates = (ordered_preferred + fallback)[:CHALLENGE_COUNT - len(already)]
            for problem in candidates:
                db.session.add(StoreProductProblem(
                    product_id=pack.id,
                    problem_id=problem.id,
                    sort_order=len(already),
                ))
                already.add(problem.id)
        db.session.commit()

    @classmethod
    def catalog(cls, user_id: int) -> dict:
        cls.ensure_catalog()
        products = StoreProduct.query.filter_by(is_active=True).order_by(StoreProduct.sort_order).all()
        now = utc_now()
        grants = UserEntitlement.query.filter_by(user_id=user_id).all()
        by_product: dict[int, list[UserEntitlement]] = {}
        for grant in grants:
            by_product.setdefault(grant.product_id, []).append(grant)
        member_end = cls._membership_end(user_id, now)
        member_active = cls._membership_active(user_id, now)
        items = []
        for product in products:
            product_grants = by_product.get(product.id, [])
            permanent = any(grant.expires_at is None for grant in product_grants)
            active = permanent or any(
                grant.starts_at <= now and grant.expires_at and grant.expires_at > now
                for grant in product_grants
            )
            expires = max(
                (g.expires_at for g in product_grants if g.expires_at and g.expires_at > now),
                default=None,
            )
            if product.code == CHALLENGE_CODE and member_active and member_end and member_end > (expires or now):
                active = True
                expires = member_end
            available = product.product_type != 'challenge_pack' or len(product.challenge_problems) == CHALLENGE_COUNT
            items.append(product.to_dict(
                owned=bool(product_grants) or (product.code == CHALLENGE_CODE and member_active),
                active=active,
                expires_at=expires,
                available=available,
            ))
        return {'products': items, 'mock_activation_enabled': cls.mock_enabled()}

    @staticmethod
    def _membership_end(user_id: int, now=None):
        now = now or utc_now()
        future = (
            UserEntitlement.query.join(StoreProduct)
            .filter(
                UserEntitlement.user_id == user_id,
                StoreProduct.code.in_(MEMBERSHIP_CODES),
                UserEntitlement.expires_at > now,
            )
            .all()
        )
        return max((row.expires_at for row in future), default=None)

    @staticmethod
    def _membership_active(user_id: int, now=None) -> bool:
        now = now or utc_now()
        return UserEntitlement.query.join(StoreProduct).filter(
            UserEntitlement.user_id == user_id,
            StoreProduct.code.in_(MEMBERSHIP_CODES),
            UserEntitlement.starts_at <= now,
            UserEntitlement.expires_at > now,
        ).first() is not None

    @staticmethod
    def _challenge_pack_available() -> bool:
        product = StoreProduct.query.filter_by(code=CHALLENGE_CODE).first()
        return bool(product and len(product.challenge_problems) == CHALLENGE_COUNT)

    @classmethod
    def entitlements(cls, user_id: int) -> dict:
        cls.ensure_catalog()
        now = utc_now()
        membership_end = cls._membership_end(user_id, now)
        permanent_pack = (
            UserEntitlement.query.join(StoreProduct)
            .filter(
                UserEntitlement.user_id == user_id,
                StoreProduct.code == CHALLENGE_CODE,
                UserEntitlement.expires_at.is_(None),
            ).first() is not None
        )
        membership_active = cls._membership_active(user_id, now)
        return {
            'membership_active': membership_active,
            'expires_at': membership_end.isoformat() + 'Z' if membership_end else None,
            'active_features': ['phase_report', 'member_challenge_pack'] if membership_active else [],
            'challenge_pack_owned': permanent_pack,
            'challenge_pack_available': cls._challenge_pack_available(),
            'mock_activation_enabled': cls.mock_enabled(),
        }

    @classmethod
    def history(cls, user_id: int) -> list[dict]:
        cls.ensure_catalog()
        rows = UserEntitlement.query.filter_by(user_id=user_id).order_by(UserEntitlement.created_at.desc()).limit(100).all()
        return [row.to_dict() for row in rows]

    @classmethod
    def mock_activate(cls, user_id: int, product_code: str) -> dict:
        if not cls.mock_enabled():
            raise PermissionError('模拟开通仅在开发或测试环境开放')
        cls.ensure_catalog()
        product = StoreProduct.query.filter_by(code=product_code, is_active=True).first()
        if not product:
            raise ValueError('商品不存在或暂未开放')
        if product.product_type == 'challenge_pack' and len(product.challenge_problems) != CHALLENGE_COUNT:
            raise ValueError('挑战包正在准备中，暂不可开通')
        now = utc_now()
        if product.duration_days is None:
            existing = UserEntitlement.query.filter_by(
                user_id=user_id, product_id=product.id, expires_at=None,
            ).first()
            if existing:
                return {'grant': existing.to_dict(), 'already_owned': True}
            grant = UserEntitlement(user_id=user_id, product_id=product.id, source='mock', starts_at=now)
        else:
            later_end = max(
                (row.expires_at for row in UserEntitlement.query.join(StoreProduct).filter(
                    UserEntitlement.user_id == user_id,
                    StoreProduct.code.in_(MEMBERSHIP_CODES),
                ).all() if row.expires_at and row.expires_at > now),
                default=now,
            )
            grant = UserEntitlement(
                user_id=user_id,
                product_id=product.id,
                source='mock',
                starts_at=later_end,
                expires_at=later_end + timedelta(days=product.duration_days),
            )
        db.session.add(grant)
        db.session.commit()
        db.session.refresh(grant)
        return {'grant': grant.to_dict(), 'already_owned': False}

    @classmethod
    def challenge_pack(cls, user_id: int, product_code: str) -> dict:
        cls.ensure_catalog()
        if product_code != CHALLENGE_CODE:
            raise ValueError('挑战包不存在')
        if not cls.has_challenge_access(user_id, product_code):
            raise PermissionError('需要开通探索会员或永久解锁该挑战包')
        product = StoreProduct.query.filter_by(code=product_code, is_active=True).first()
        if not product or len(product.challenge_problems) != CHALLENGE_COUNT:
            raise ValueError('挑战包正在准备中')
        from app.services.practice_question import PracticeQuestionService

        progress_rows = UserChallengeProgress.query.filter_by(
            user_id=user_id, product_id=product.id,
        ).all()
        completed_ids = {row.problem_id for row in progress_rows}
        questions = []
        for index, link in enumerate(product.challenge_problems, start=1):
            payload = PracticeQuestionService._problem_to_payload(link.problem)
            questions.append({
                'id': payload['id'], 'code': payload['code'], 'title': payload['title'],
                'topic': payload['topic'], 'difficulty': payload['difficulty'],
                'duration_min': payload['duration_min'], 'question_type': payload['question_type'],
                'problem_id': link.problem_id,
                'stage': index,
                'completed': link.problem_id in completed_ids,
            })
        total = len(questions)
        completed_count = len(completed_ids)
        return {
            'product_code': product.code,
            'title': product.name,
            'description': product.description,
            'questions': questions,
            'total': total,
            'progress': {
                'completed_count': completed_count,
                'total': total,
                'percent': round(completed_count / total * 100) if total else 0,
            },
        }

    @classmethod
    def complete_challenge_question(cls, user_id: int, product_code: str, problem_id: int) -> dict:
        cls.ensure_catalog()
        product = StoreProduct.query.filter_by(code=product_code, is_active=True).first()
        if not product or not cls.has_challenge_access(user_id, product_code):
            raise PermissionError('没有该挑战包的访问权益')
        link = StoreProductProblem.query.filter_by(
            product_id=product.id, problem_id=problem_id,
        ).first()
        if not link:
            raise ValueError('题目不属于此挑战包')
        record = UserChallengeProgress.query.filter_by(
            user_id=user_id, product_id=product.id, problem_id=problem_id,
        ).first()
        already_completed = record is not None
        if not record:
            record = UserChallengeProgress(
                user_id=user_id,
                product_id=product.id,
                problem_id=problem_id,
            )
            db.session.add(record)
            db.session.commit()
            db.session.refresh(record)
        completed_count = UserChallengeProgress.query.filter_by(
            user_id=user_id, product_id=product.id,
        ).count()
        total = len(product.challenge_problems)
        return {
            'problem_id': problem_id,
            'completed': True,
            'already_completed': already_completed,
            'completed_at': record.completed_at.isoformat() + 'Z',
            'progress': {
                'completed_count': completed_count,
                'total': total,
                'percent': round(completed_count / total * 100) if total else 0,
            },
        }

    @classmethod
    def has_challenge_access(cls, user_id: int, product_code: str) -> bool:
        now = utc_now()
        if product_code in MEMBERSHIP_CODES:
            return False
        product = StoreProduct.query.filter_by(code=product_code, is_active=True).first()
        if not product:
            return False
        own_pack = UserEntitlement.query.filter_by(
            user_id=user_id, product_id=product.id, expires_at=None,
        ).first()
        return bool(own_pack or cls._membership_active(user_id, now))

    @classmethod
    def challenge_question(cls, user_id: int, product_code: str, question_ref: str) -> dict:
        cls.ensure_catalog()
        product = StoreProduct.query.filter_by(code=product_code, is_active=True).first()
        if not product or not cls.has_challenge_access(user_id, product_code):
            raise PermissionError('没有该挑战包的访问权益')
        if not question_ref.startswith('bank-'):
            raise ValueError('题目不属于此挑战包')
        try:
            problem_id = int(question_ref[5:])
        except ValueError as exc:
            raise ValueError('题目编号无效') from exc
        linked = StoreProductProblem.query.filter_by(product_id=product.id, problem_id=problem_id).first()
        if not linked:
            raise ValueError('题目不属于此挑战包')
        from app.services.practice_question import PracticeQuestionService

        payload = PracticeQuestionService.get_by_ref(question_ref)
        if not payload:
            raise ValueError('题目不存在')
        return payload
