"""公告 API 测试"""
import unittest

from flask_jwt_extended import create_access_token

from app import create_app
from app.models import Role, SystemAnnouncement, User, db


class AnnouncementTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            admin_role = Role.query.filter_by(name='admin').first()
            student_role = Role.query.filter_by(name='student').first()
            self.admin = User.query.filter_by(role_id=admin_role.id).first()
            self.student = User.query.filter_by(role_id=student_role.id).first()
            if not self.student:
                from werkzeug.security import generate_password_hash

                self.student = User(
                    username='announce-student',
                    email='announce-student@example.com',
                    password_hash=generate_password_hash('student123'),
                    real_name='公告学生',
                    role_id=student_role.id,
                )
                db.session.add(self.student)
                db.session.commit()
            self.admin_token = create_access_token(identity=str(self.admin.id))
            self.student_token = create_access_token(identity=str(self.student.id))

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def auth(self, token):
        return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    def test_admin_create_list_update_delete(self):
        create_resp = self.client.post(
            '/api/v1/admin/announcements',
            headers=self.auth(self.admin_token),
            json={
                'title': '测试公告',
                'body': '这是一条测试公告内容',
                'target_role': 'student',
            },
        )
        self.assertEqual(create_resp.status_code, 200)
        created = create_resp.get_json()['data']
        self.assertEqual(created['title'], '测试公告')
        ann_id = created['id']

        list_resp = self.client.get('/api/v1/admin/announcements', headers=self.auth(self.admin_token))
        self.assertEqual(list_resp.status_code, 200)
        items = list_resp.get_json()['data']
        self.assertTrue(any(item['id'] == ann_id for item in items))

        patch_resp = self.client.patch(
            f'/api/v1/admin/announcements/{ann_id}',
            headers=self.auth(self.admin_token),
            json={'title': '更新后的公告'},
        )
        self.assertEqual(patch_resp.status_code, 200)
        self.assertEqual(patch_resp.get_json()['data']['title'], '更新后的公告')

        delete_resp = self.client.delete(
            f'/api/v1/admin/announcements/{ann_id}',
            headers=self.auth(self.admin_token),
        )
        self.assertEqual(delete_resp.status_code, 200)

        with self.app.app_context():
            row = db.session.get(SystemAnnouncement, ann_id)
            self.assertIsNotNone(row)
            self.assertFalse(row.is_active)

    def test_student_sees_student_target_announcement(self):
        self.client.post(
            '/api/v1/admin/announcements',
            headers=self.auth(self.admin_token),
            json={'title': '学生公告', 'body': '给学生', 'target_role': 'student'},
        )

        resp = self.client.get('/api/v1/student/announcements', headers=self.auth(self.student_token))
        self.assertEqual(resp.status_code, 200)
        titles = [item['title'] for item in resp.get_json()['data']]
        self.assertIn('学生公告', titles)


if __name__ == '__main__':
    unittest.main()
