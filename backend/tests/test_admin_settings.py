"""Admin settings API tests."""
import json
import unittest

from flask_jwt_extended import create_access_token

from app import create_app
from app.models import SystemSetting, User, db


class AdminSettingsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            self.admin = User.query.filter_by(username='admin').first()
            self.admin_token = create_access_token(identity=str(self.admin.id))

    def auth(self, token):
        return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_get_and_save_settings(self):
        get_resp = self.client.get('/api/v1/admin/settings', headers=self.auth(self.admin_token))
        self.assertEqual(get_resp.status_code, 200)
        self.assertIn('rules', get_resp.get_json()['data']['settings'])

        save_resp = self.client.put(
            '/api/v1/admin/settings',
            headers=self.auth(self.admin_token),
            json={'settings': {'rules': {'daily_limit': '5', 'difficulty': 60}}},
        )
        self.assertEqual(save_resp.status_code, 200)
        self.assertEqual(save_resp.get_json()['data']['settings']['rules']['daily_limit'], '5')

        with self.app.app_context():
            row = SystemSetting.query.filter_by(class_id=None).first()
            self.assertIsNotNone(row)
            payload = json.loads(row.payload_json)
            self.assertEqual(payload['rules']['daily_limit'], '5')


if __name__ == '__main__':
    unittest.main()
