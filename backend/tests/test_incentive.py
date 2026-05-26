"""Incentive loop: points, level, achievements, ranking."""
import unittest

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Achievement, Class, Role, User, UserAchievement, db
from app.services.incentive import IncentiveService


class IncentiveTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        with self.app.app_context():
            student_role = Role.query.filter_by(name='student').first()
            teacher = User.query.filter_by(username='teacher001').first()
            self.student = User(
                username='incentive-student',
                email='incentive@example.com',
                password_hash=generate_password_hash('student123'),
                real_name='激励学生',
                role_id=student_role.id,
                total_points=0,
                level=1,
            )
            db.session.add(self.student)
            db.session.flush()
            self.cls = Class(name='激励班', description='i', grade_level=1, teacher_id=teacher.id)
            db.session.add(self.cls)
            db.session.flush()
            self.student.class_id = self.cls.id
            db.session.add(
                Achievement(
                    name='测试成就',
                    description='500分',
                    rarity='common',
                    condition_type='total_points',
                    condition_value=500,
                )
            )
            db.session.commit()
            self.student_id = self.student.id
            self.class_id = self.cls.id
            self.token = create_access_token(identity=str(self.student_id))

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_points_level_achievement_ranking(self):
        with self.app.app_context():
            feedback = IncentiveService.record_points(self.student_id, 520, 'test_grant')
            db.session.commit()
            self.assertTrue(feedback['level_up'])
            self.assertEqual(feedback['level'], 2)
            self.assertGreaterEqual(len(feedback['unlocked_achievements']), 1)

            user = User.query.get(self.student_id)
            self.assertEqual(user.level, 2)
            unlocked = UserAchievement.query.filter_by(user_id=self.student_id).count()
            self.assertGreaterEqual(unlocked, 1)

            IncentiveService.refresh_class_ranking(self.class_id)
            db.session.commit()
            rank = IncentiveService.class_rank_for_user(user)
            self.assertEqual(rank, 1)

    def test_me_returns_incentive_block(self):
        resp = self.app.test_client().get(
            '/api/v1/users/me',
            headers={'Authorization': f'Bearer {self.token}'},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()['data']
        self.assertIn('level_profile', body)
        self.assertIn('incentive', body)


if __name__ == '__main__':
    unittest.main()
