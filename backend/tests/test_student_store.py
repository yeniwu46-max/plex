"""Student store catalog and mock entitlement API coverage."""
import unittest
from datetime import timedelta

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Problem, Role, StoreProduct, StoreProductProblem, User, UserEntitlement, db
from app.services.student_store import CHALLENGE_CODE, StudentStoreService
from app.utils.time import utc_now


class StudentStoreTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            student_role = Role.query.filter_by(name='student').first()
            teacher_role = Role.query.filter_by(name='teacher').first()
            self.student = self._add_user('store-student', student_role.id)
            self.other = self._add_user('store-other', student_role.id)
            self.teacher = self._add_user('store-teacher', teacher_role.id)
            for number in range(10):
                db.session.add(Problem(
                    id=8100 + number,
                    problem_no=f'S{8100 + number}',
                    title_cn=f'算法练习 {number}',
                    description_cn='输入一个整数并输出结果。',
                    question_type='coding',
                    is_active=True,
                    needs_review=False,
                    star_difficulty=number % 4 + 1,
                    kg_node_id='lang-print',
                    test_cases_json=[{'input': '1', 'expected': '1'}],
                ))
            db.session.commit()
            self.student_token = create_access_token(identity=str(self.student.id))
            self.other_token = create_access_token(identity=str(self.other.id))
            self.teacher_token = create_access_token(identity=str(self.teacher.id))

    @staticmethod
    def _add_user(username, role_id):
        user = User(
            username=username,
            email=f'{username}@example.com',
            password_hash=generate_password_hash('student123'),
            real_name=username,
            role_id=role_id,
        )
        db.session.add(user)
        db.session.flush()
        return user

    def auth(self, token):
        return {'Authorization': f'Bearer {token}'}

    def activate(self, token, product_code):
        return self.client.post(
            '/api/v1/student/store/mock-activation',
            json={'product_code': product_code},
            headers=self.auth(token),
        )

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_catalog_requires_student_and_contains_seeded_products(self):
        self.assertEqual(self.client.get('/api/v1/student/store/catalog').status_code, 401)
        self.assertEqual(self.client.get('/api/v1/student/store/catalog', headers=self.auth(self.teacher_token)).status_code, 403)
        response = self.client.get('/api/v1/student/store/catalog', headers=self.auth(self.student_token))
        self.assertEqual(response.status_code, 200)
        data = response.get_json()['data']
        products = {item['code']: item for item in data['products']}
        self.assertEqual(products['explorer_monthly']['price_cents'], 990)
        self.assertEqual(products['explorer_annual']['price_cents'], 6800)
        self.assertEqual(products[CHALLENGE_CODE]['price_cents'], 600)
        self.assertTrue(products[CHALLENGE_CODE]['available'])
        self.assertIn('挑战通关进度跨设备保存', products[CHALLENGE_CODE]['benefits'])
        with self.app.app_context():
            self.assertEqual(len(StoreProduct.query.filter_by(code=CHALLENGE_CODE).first().challenge_problems), 10)

    def test_challenge_progress_is_saved_and_scoped_to_owner(self):
        self.activate(self.student_token, CHALLENGE_CODE)
        pack_url = f'/api/v1/student/store/challenge-packs/{CHALLENGE_CODE}'
        before = self.client.get(pack_url, headers=self.auth(self.student_token)).get_json()['data']
        self.assertEqual(before['progress']['completed_count'], 0)
        self.assertEqual(before['progress']['total'], 10)
        with self.app.app_context():
            first_problem_id = StoreProductProblem.query.join(StoreProduct).filter(
                StoreProduct.code == CHALLENGE_CODE,
            ).order_by(StoreProductProblem.sort_order).first().problem_id

        progress_url = f'/api/v1/student/store/challenge-packs/{CHALLENGE_CODE}/progress/{first_problem_id}'
        saved = self.client.post(progress_url, headers=self.auth(self.student_token)).get_json()['data']
        self.assertTrue(saved['completed'])
        self.assertFalse(saved['already_completed'])
        self.assertEqual(saved['progress']['completed_count'], 1)
        repeated = self.client.post(progress_url, headers=self.auth(self.student_token)).get_json()['data']
        self.assertTrue(repeated['already_completed'])
        after = self.client.get(pack_url, headers=self.auth(self.student_token)).get_json()['data']
        self.assertTrue(after['questions'][0]['completed'])
        self.assertEqual(after['progress']['percent'], 10)
        self.assertEqual(self.client.post(progress_url, headers=self.auth(self.other_token)).status_code, 403)

    def test_membership_unlocks_pack_and_report_then_expiry_revokes_access(self):
        denied = self.client.get(
            f'/api/v1/student/store/challenge-packs/{CHALLENGE_CODE}',
            headers=self.auth(self.student_token),
        )
        self.assertEqual(denied.status_code, 403)
        grant_response = self.activate(self.student_token, 'explorer_monthly')
        self.assertEqual(grant_response.status_code, 201)
        self.assertEqual(grant_response.get_json()['data']['grant']['source'], 'mock')
        self.assertEqual(self.client.get(
            f'/api/v1/student/store/challenge-packs/{CHALLENGE_CODE}',
            headers=self.auth(self.student_token),
        ).status_code, 200)
        self.assertEqual(self.client.get(
            f'/api/v1/student/practice-questions/bank-8100?pack_code={CHALLENGE_CODE}',
            headers=self.auth(self.student_token),
        ).status_code, 200)
        self.assertEqual(self.client.get(
            f'/api/v1/student/practice-questions/bank-99999?pack_code={CHALLENGE_CODE}',
            headers=self.auth(self.student_token),
        ).status_code, 400)
        self.assertEqual(self.client.post(
            '/api/v1/student/learning-report/generate', json={'period': '7d'},
            headers=self.auth(self.student_token),
        ).status_code, 200)
        entitlements = self.client.get(
            '/api/v1/student/entitlements/me', headers=self.auth(self.student_token),
        ).get_json()['data']
        self.assertIn('phase_report', entitlements['active_features'])

        with self.app.app_context():
            UserEntitlement.query.filter_by(user_id=self.student.id).update(
                {UserEntitlement.expires_at: utc_now() - timedelta(seconds=1)},
            )
            db.session.commit()
        expired = self.client.get(
            '/api/v1/student/entitlements/me', headers=self.auth(self.student_token),
        ).get_json()['data']
        self.assertFalse(expired['membership_active'])
        self.assertNotIn('phase_report', expired['active_features'])
        self.assertEqual(self.client.get(
            f'/api/v1/student/store/challenge-packs/{CHALLENGE_CODE}',
            headers=self.auth(self.student_token),
        ).status_code, 403)
        self.assertEqual(self.client.post(
            '/api/v1/student/learning-report/generate', json={'period': '7d'},
            headers=self.auth(self.student_token),
        ).status_code, 403)

    def test_permanent_pack_is_idempotent_and_cannot_be_granted_to_another_user(self):
        first = self.client.post(
            '/api/v1/student/store/mock-activation',
            json={'product_code': CHALLENGE_CODE, 'user_id': self.other.id},
            headers=self.auth(self.student_token),
        )
        second = self.activate(self.student_token, CHALLENGE_CODE)
        self.assertEqual(first.status_code, 201)
        self.assertFalse(first.get_json()['data']['already_owned'])
        self.assertTrue(second.get_json()['data']['already_owned'])
        self.assertEqual(len(self.client.get(
            '/api/v1/student/store/history', headers=self.auth(self.student_token),
        ).get_json()['data']), 1)
        self.assertEqual(self.client.get(
            f'/api/v1/student/store/challenge-packs/{CHALLENGE_CODE}',
            headers=self.auth(self.student_token),
        ).status_code, 200)
        self.assertEqual(self.client.get(
            f'/api/v1/student/store/challenge-packs/{CHALLENGE_CODE}',
            headers=self.auth(self.other_token),
        ).status_code, 403)
        self.assertFalse(self.client.get(
            '/api/v1/student/entitlements/me', headers=self.auth(self.other_token),
        ).get_json()['data']['challenge_pack_owned'])

    def test_membership_activation_extends_from_current_expiry(self):
        self.assertEqual(self.activate(self.student_token, 'explorer_monthly').status_code, 201)
        with self.app.app_context():
            grant = UserEntitlement.query.filter_by(user_id=self.student.id).one()
            grant.expires_at = utc_now() + timedelta(days=4)
            expected_end = grant.expires_at + timedelta(days=30)
            db.session.commit()
        response = self.activate(self.student_token, 'explorer_monthly')
        self.assertEqual(response.status_code, 201)
        with self.app.app_context():
            grants = UserEntitlement.query.filter_by(user_id=self.student.id).all()
            self.assertEqual(len(grants), 2)
            self.assertEqual(max(row.expires_at for row in grants), expected_end)

    def test_mock_activation_is_disabled_when_debug_and_testing_are_off(self):
        self.app.config.update(DEBUG=False, TESTING=False, STORE_MOCK_ACTIVATION_ENABLED=False)
        response = self.activate(self.student_token, 'explorer_monthly')
        self.assertEqual(response.status_code, 403)

    def test_switching_membership_products_extends_existing_membership(self):
        self.assertEqual(self.activate(self.student_token, 'explorer_monthly').status_code, 201)
        with self.app.app_context():
            existing = UserEntitlement.query.filter_by(user_id=self.student.id).one()
            expected_end = existing.expires_at + timedelta(days=365)
        response = self.activate(self.student_token, 'explorer_annual')
        self.assertEqual(response.status_code, 201)
        with self.app.app_context():
            self.assertEqual(max(
                grant.expires_at for grant in UserEntitlement.query.filter_by(user_id=self.student.id).all()
            ), expected_end)


if __name__ == '__main__':
    unittest.main()
