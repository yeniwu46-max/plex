"""文件上传接口测试：角色/扩展名/大小/权限校验。"""
import io
import unittest

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Role, User, db


class FileUploadTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()

        with self.app.app_context():
            student_role = Role.query.filter_by(name='student').first()
            teacher_role = Role.query.filter_by(name='teacher').first()
            admin_role   = Role.query.filter_by(name='admin').first()

            self.student = User(
                username='upload-student',
                email='upload-student@test.com',
                password_hash=generate_password_hash('pw'),
                real_name='上传测试学生',
                role_id=student_role.id,
            )
            self.teacher = User(
                username='upload-teacher',
                email='upload-teacher@test.com',
                password_hash=generate_password_hash('pw'),
                real_name='上传测试教师',
                role_id=teacher_role.id,
            )
            self.admin = User(
                username='upload-admin',
                email='upload-admin@test.com',
                password_hash=generate_password_hash('pw'),
                real_name='上传测试管理员',
                role_id=admin_role.id,
            )
            db.session.add_all([self.student, self.teacher, self.admin])
            db.session.flush()
            db.session.commit()

            self.student_token = create_access_token(identity=str(self.student.id))
            self.teacher_token = create_access_token(identity=str(self.teacher.id))
            self.admin_token   = create_access_token(identity=str(self.admin.id))

    def tearDown(self):
        with self.app.app_context():
            db.session.rollback()
            for user in [self.student, self.teacher, self.admin]:
                db.session.delete(db.session.get(User, user.id))
            db.session.commit()

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

    # ─── 正常上传 ────────────────────────────────────────────

    def test_student_upload_cpp_blocked(self):
        resp = self._upload(
            self.student_token, 'main.cpp', b'int main(){}', 'student', 'code-file', 'text/plain'
        )
        self.assertEqual(resp.status_code, 400)

    def test_student_upload_python_file(self):
        resp = self._upload(
            self.student_token, 'hello.py', b'print("hello")', 'student', 'code-file', 'text/x-python'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['code'], 0)
        self.assertEqual(data['data']['scene'], 'code-file')
        self.assertIn('/api/v1/uploads/files/', data['data']['url'])

    def test_teacher_upload_pdf(self):
        resp = self._upload(
            self.teacher_token, 'lecture.pdf', b'%PDF-1.4 fake', 'teacher', 'course-material', 'application/pdf'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['code'], 0)

    def test_admin_upload_json_config(self):
        resp = self._upload(
            self.admin_token, 'config.json', b'{"key": "val"}', 'admin', 'system-config', 'application/json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['code'], 0)

    # ─── 禁止文件类型 ────────────────────────────────────────

    def test_student_upload_exe_blocked(self):
        resp = self._upload(
            self.student_token, 'malware.exe', b'MZ\x90\x00', 'student', 'code-file', 'application/octet-stream'
        )
        self.assertEqual(resp.status_code, 400)

    def test_executable_disguised_as_pdf_is_blocked(self):
        resp = self._upload(
            self.teacher_token, 'lecture.pdf', b'MZ\x90\x00payload', 'teacher', 'course-material', 'application/pdf'
        )
        self.assertEqual(resp.status_code, 400)

    def test_invalid_json_content_is_blocked(self):
        resp = self._upload(
            self.admin_token, 'config.json', b'{not-json}', 'admin', 'system-config', 'application/json'
        )
        self.assertEqual(resp.status_code, 400)

    def test_student_upload_sh_blocked(self):
        resp = self._upload(
            self.student_token, 'hack.sh', b'#!/bin/bash\nrm -rf /', 'student', 'code-file', 'text/x-shellscript'
        )
        self.assertEqual(resp.status_code, 400)

    # ─── 扩展名不匹配场景 ─────────────────────────────────────

    def test_student_upload_wrong_ext_for_scene(self):
        # code-file 场景不接受 .pdf
        resp = self._upload(
            self.student_token, 'report.pdf', b'%PDF data', 'student', 'code-file', 'application/pdf'
        )
        self.assertEqual(resp.status_code, 400)

    # ─── 角色权限 ────────────────────────────────────────────

    def test_teacher_cannot_use_student_scene(self):
        # teacher 不允许上传 code-file
        resp = self._upload(
            self.teacher_token, 'main.py', b'x=1', 'teacher', 'code-file', 'text/x-python'
        )
        # role 不匹配 → 403（JWT teacher 但请求 role=teacher，scene 不允许 teacher → 400）
        self.assertIn(resp.status_code, (400, 403))

    def test_student_cannot_use_teacher_scene(self):
        # student token 但 role=teacher → 403（JWT role 不符）
        resp = self._upload(
            self.student_token, 'notes.pdf', b'PDF', 'teacher', 'course-material', 'application/pdf'
        )
        self.assertEqual(resp.status_code, 403)

    def test_student_cannot_use_admin_scene(self):
        resp = self._upload(
            self.student_token, 'kb.md', b'# content', 'admin', 'knowledge-doc', 'text/markdown'
        )
        self.assertEqual(resp.status_code, 403)

    # ─── 空文件 & 大小限制 ───────────────────────────────────

    def test_empty_file_rejected(self):
        resp = self._upload(
            self.student_token, 'empty.py', b'', 'student', 'code-file', 'text/x-python'
        )
        self.assertEqual(resp.status_code, 400)

    def test_oversized_file_rejected(self):
        # code-file 上限 2MB；发送 2MB+1
        big_data = b'x' * (2 * 1024 * 1024 + 1)
        resp = self._upload(
            self.student_token, 'big.py', big_data, 'student', 'code-file', 'text/x-python'
        )
        self.assertEqual(resp.status_code, 400)

    # ─── 无 Token 访问 ───────────────────────────────────────

    def test_upload_without_token(self):
        data = {
            'file': (io.BytesIO(b'code'), 'f.py', 'text/x-python'),
            'role': 'student',
            'scene': 'code-file',
        }
        resp = self.client.post(
            '/api/v1/upload',
            data=data,
            content_type='multipart/form-data',
        )
        self.assertIn(resp.status_code, (401, 422))

    # ─── 文件可下载（本人） ────────────────────────────────────

    def test_uploaded_file_accessible_by_owner(self):
        upload_resp = self._upload(
            self.student_token, 'myscript.py', b'print(1)', 'student', 'code-file', 'text/x-python'
        )
        self.assertEqual(upload_resp.status_code, 200)
        url = upload_resp.get_json()['data']['url']
        # url 格式：/api/v1/uploads/files/{user_id}/code-file/{filename}
        get_resp = self.client.get(url, headers={'Authorization': f'Bearer {self.student_token}'})
        self.assertEqual(get_resp.status_code, 200)

    def test_uploaded_file_not_accessible_by_other(self):
        upload_resp = self._upload(
            self.student_token, 'secret.py', b'pw=123', 'student', 'code-file', 'text/x-python'
        )
        self.assertEqual(upload_resp.status_code, 200)
        url = upload_resp.get_json()['data']['url']
        # teacher 访问 student 文件 → 403
        get_resp = self.client.get(url, headers={'Authorization': f'Bearer {self.teacher_token}'})
        self.assertEqual(get_resp.status_code, 403)

    def test_admin_can_access_any_file(self):
        upload_resp = self._upload(
            self.student_token, 'adminview.py', b'x=2', 'student', 'code-file', 'text/x-python'
        )
        self.assertEqual(upload_resp.status_code, 200)
        url = upload_resp.get_json()['data']['url']
        get_resp = self.client.get(url, headers={'Authorization': f'Bearer {self.admin_token}'})
        self.assertEqual(get_resp.status_code, 200)


if __name__ == '__main__':
    unittest.main()
