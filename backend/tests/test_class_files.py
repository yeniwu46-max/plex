"""班级文件共享接口测试。"""
import io
import shutil
import unittest
from pathlib import Path

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Class, Role, User, db


class ClassFileSharingTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()

        with self.app.app_context():
            student_role = Role.query.filter_by(name='student').first()
            teacher_role = Role.query.filter_by(name='teacher').first()

            self.teacher = User(
                username='cf-teacher',
                email='cf-teacher@test.com',
                password_hash=generate_password_hash('pw'),
                real_name='文件教师',
                role_id=teacher_role.id,
            )
            self.student = User(
                username='cf-student',
                email='cf-student@test.com',
                password_hash=generate_password_hash('pw'),
                real_name='文件学生',
                role_id=student_role.id,
            )
            db.session.add_all([self.teacher, self.student])
            db.session.flush()

            self.class_obj = Class(
                name='文件共享班',
                teacher_id=self.teacher.id,
                join_code='ABC123',
            )
            db.session.add(self.class_obj)
            db.session.flush()

            self.student.class_id = self.class_obj.id
            self.class_obj.student_count = 1
            db.session.commit()

            self.class_id = self.class_obj.id
            self.teacher_id = self.teacher.id
            self.student_id = self.student.id
            self.teacher_token = create_access_token(identity=str(self.teacher.id))
            self.student_token = create_access_token(identity=str(self.student.id))

    def tearDown(self):
        with self.app.app_context():
            db.session.rollback()
            class_obj = db.session.get(Class, self.class_id)
            if class_obj:
                db.session.delete(class_obj)
            for user_id in [self.student_id, self.teacher_id]:
                user = db.session.get(User, user_id)
                if user:
                    db.session.delete(user)
            db.session.commit()
            upload_root = Path(self.app.instance_path) / 'uploads' / 'files'
            for user_id in [self.student_id, self.teacher_id]:
                target = upload_root / str(user_id)
                if target.exists():
                    shutil.rmtree(target, ignore_errors=True)

    def _upload(self, token, filename, content, role, scene, mime='application/octet-stream'):
        data = {
            'file': (io.BytesIO(content), filename, mime),
            'role': role,
            'scene': scene,
        }
        return self.client.post(
            '/api/v1/upload',
            headers={'Authorization': f'Bearer {token}'},
            data=data,
            content_type='multipart/form-data',
        )

    def test_teacher_material_visible_to_student(self):
        upload = self._upload(
            self.teacher_token,
            'notes.pdf',
            b'%PDF-1.4 fake pdf',
            'teacher',
            'course-material',
            'application/pdf',
        )
        self.assertEqual(upload.status_code, 200)
        url = upload.get_json()['data']['url']

        listed = self.client.get('/api/v1/class-files', headers={'Authorization': f'Bearer {self.student_token}'})
        self.assertEqual(listed.status_code, 200)
        items = listed.get_json()['data']['items']
        self.assertTrue(any(item['scene'] == 'course-material' and item['url'] == url for item in items))

        fetched = self.client.get(url, headers={'Authorization': f'Bearer {self.student_token}'})
        self.assertEqual(fetched.status_code, 200)

    def test_student_submission_visible_to_teacher(self):
        upload = self._upload(
            self.student_token,
            'work.py',
            b'print("hello")',
            'student',
            'code-file',
            'text/x-python',
        )
        self.assertEqual(upload.status_code, 200)
        url = upload.get_json()['data']['url']

        listed = self.client.get('/api/v1/class-files', headers={'Authorization': f'Bearer {self.teacher_token}'})
        self.assertEqual(listed.status_code, 200)
        items = listed.get_json()['data']['items']
        self.assertTrue(any(item['scene'] == 'code-file' and item['url'] == url for item in items))

        fetched = self.client.get(url, headers={'Authorization': f'Bearer {self.teacher_token}'})
        self.assertEqual(fetched.status_code, 200)


if __name__ == '__main__':
    unittest.main()
