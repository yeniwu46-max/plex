import json
import unittest
from urllib.parse import parse_qs, urlparse
from unittest.mock import Mock, patch

from app import create_app
from app.models import User, db


def _redirect_fragment(location):
    parsed = urlparse(location)
    return parse_qs(parsed.fragment)


class AuthOAuthTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app.config.update(
            FRONTEND_BASE_URL='http://localhost:5173',
            GOOGLE_CLIENT_ID='google-client',
            GOOGLE_CLIENT_SECRET='google-secret',
            GITHUB_CLIENT_ID='github-client',
            GITHUB_CLIENT_SECRET='github-secret',
        )
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_register_then_login_with_email(self):
        register = self.client.post('/api/v1/auth/register', json={
            'username': 'email_login_user',
            'email': 'email-login@example.com',
            'password': 'secret123',
            'real_name': 'Email Login User',
        })
        self.assertEqual(register.status_code, 201)
        self.assertTrue(register.get_json()['data']['access_token'])

        login = self.client.post('/api/v1/auth/login', json={
            'username': 'email-login@example.com',
            'password': 'secret123',
        })
        self.assertEqual(login.status_code, 200)
        body = login.get_json()
        self.assertEqual(body['code'], 0)
        self.assertEqual(body['data']['username'], 'email_login_user')
        self.assertTrue(body['data']['access_token'])

    def test_google_oauth_callback_creates_student_session(self):
        start = self.client.get('/api/v1/auth/oauth/google?redirect=/student')
        self.assertEqual(start.status_code, 302)
        state = parse_qs(urlparse(start.headers['Location']).query)['state'][0]

        token_response = Mock()
        token_response.json.return_value = {'access_token': 'google-token'}
        token_response.raise_for_status.return_value = None

        profile_response = Mock()
        profile_response.json.return_value = {
            'sub': 'google-123',
            'email': 'google-user@example.com',
            'name': 'Google User',
            'picture': 'https://example.com/avatar.png',
        }
        profile_response.raise_for_status.return_value = None

        with patch('app.routes.auth.requests.post', return_value=token_response), \
                patch('app.routes.auth.requests.get', return_value=profile_response):
            callback = self.client.get(f'/api/v1/auth/oauth/google/callback?code=ok&state={state}')

        self.assertEqual(callback.status_code, 302)
        fragment = _redirect_fragment(callback.headers['Location'])
        session = json.loads(fragment['session'][0])
        self.assertEqual(fragment['redirect'][0], '/student')
        self.assertEqual(session['email'], 'google-user@example.com')
        self.assertEqual(session['role'], 'student')
        self.assertTrue(session['access_token'])

        with self.app.app_context():
            self.assertIsNotNone(User.query.filter_by(email='google-user@example.com').first())

    def test_github_oauth_callback_uses_primary_verified_email(self):
        start = self.client.get('/api/v1/auth/oauth/github?redirect=/student')
        self.assertEqual(start.status_code, 302)
        state = parse_qs(urlparse(start.headers['Location']).query)['state'][0]

        token_response = Mock()
        token_response.json.return_value = {'access_token': 'github-token'}
        token_response.raise_for_status.return_value = None

        user_response = Mock()
        user_response.json.return_value = {
            'id': 123,
            'login': 'github-user',
            'name': 'GitHub User',
            'email': None,
            'avatar_url': 'https://example.com/github.png',
        }
        user_response.raise_for_status.return_value = None

        emails_response = Mock()
        emails_response.json.return_value = [
            {'email': 'github-user@example.com', 'primary': True, 'verified': True},
        ]
        emails_response.raise_for_status.return_value = None

        with patch('app.routes.auth.requests.post', return_value=token_response), \
                patch('app.routes.auth.requests.get', side_effect=[user_response, emails_response]):
            callback = self.client.get(f'/api/v1/auth/oauth/github/callback?code=ok&state={state}')

        self.assertEqual(callback.status_code, 302)
        session = json.loads(_redirect_fragment(callback.headers['Location'])['session'][0])
        self.assertEqual(session['email'], 'github-user@example.com')
        self.assertTrue(session['access_token'])

    def test_oauth_start_reports_missing_provider_config(self):
        self.app.config['GOOGLE_CLIENT_SECRET'] = None
        response = self.client.get('/api/v1/auth/oauth/google')
        self.assertEqual(response.status_code, 302)
        fragment = _redirect_fragment(response.headers['Location'])
        self.assertIn('Client ID/Secret', fragment['error'][0])


if __name__ == '__main__':
    unittest.main()
