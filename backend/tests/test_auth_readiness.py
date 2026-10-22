"""Real-user account flows, without external mail or production data."""
import unittest
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs

from werkzeug.security import check_password_hash
from app import create_app, ensure_dev_login_users
from app.models import AuthToken, User, db
from app.services.auth import AuthService
from app.services.auth_security import hash_token
from app.utils.time import utc_now


class AuthReadinessTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app.config.update(SMTP_HOST='', SMTP_USER='', SMTP_PASSWORD='', GOOGLE_CLIENT_ID='', GITHUB_CLIENT_ID='')
        self.client = self.app.test_client()
        self.payload = dict(username='trial_user', email='trial_user@example.org', real_name='试用学生', password='TrialPass123')

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def post(self, path, body, token=None):
        return self.client.post('/api/v1/auth/' + path, json=body, headers={'Authorization': 'Bearer '+token} if token else {})

    def register(self):
        result = self.post('register', self.payload)
        self.assertEqual(result.status_code, 201)
        return result.json['data']

    def enable_mail(self):
        self.app.config.update(SMTP_HOST='smtp.invalid', SMTP_USER='test@example.org', SMTP_PASSWORD='test-only')

    def recovery_token(self):
        self.enable_mail()
        with patch('app.services.auth_security.send_reset_mail') as mail:
            result = self.post('forgot-password', {'email':self.payload['email']})
            self.assertEqual(result.status_code, 200)
            token = mail.call_args.args[1]
            self.assertNotIn(token, result.get_data(as_text=True))
            return token

    def test_real_registration_login_and_case_insensitive_duplicates(self):
        account = self.register()
        self.assertEqual(account['email'], self.payload['email'])
        for identity in ['trial_user', 'TRIAL_USER@EXAMPLE.ORG']:
            self.assertEqual(self.post('login', {'username':identity, 'password':self.payload['password']}).status_code, 200)
        self.assertEqual(self.post('register', {**self.payload, 'username':'TRIAL_USER','email':'another@example.org'}).status_code, 400)
        self.assertEqual(self.post('register', {**self.payload, 'username':'another','email':'TRIAL_USER@EXAMPLE.ORG'}).status_code, 400)

    def test_invalid_registration_and_privileged_roles(self):
        for changes in [{'email':'fake@plex.local'}, {'email':'not-an-email'}, {'password':'12345678'}, {'password':'abcdefgh'}, {'username':'a'}, {'username':[]}, {'real_name':52*'x'}]:
            self.assertEqual(self.post('register', {**self.payload, **changes}).status_code, 400)
        self.assertEqual(self.post('register', {**self.payload,'role':'admin'}).status_code, 403)
        for body in [None, [], 'bad']:
            self.assertEqual(self.post('register', body).status_code, 400)

    def test_login_failure_does_not_enumerate_accounts(self):
        self.register()
        known = self.post('login', {'username':'trial_user','password':'wrong'})
        unknown = self.post('login', {'username':'missing','password':'wrong'})
        self.assertEqual(known.status_code, 401)
        self.assertEqual(known.json, unknown.json)

    def test_frozen_user_cannot_refresh_or_use_existing_access(self):
        session = self.register()
        with self.app.app_context():
            user=db.session.get(User,session['id']);user.status='frozen';db.session.commit()
        self.assertEqual(self.post('refresh',{},session['refresh_token']).status_code,401)
        self.assertEqual(self.post('logout',{},session['access_token']).status_code,401)

    def test_logout_revokes_family_but_keeps_other_device(self):
        first=self.register()
        second=self.post('login',{'username':'trial_user','password':self.payload['password']}).json['data']
        refreshed=self.post('refresh',{},first['refresh_token']).json['data']['access_token']
        self.assertEqual(self.post('logout',{'refresh_token':first['refresh_token']},first['access_token']).status_code,200)
        self.assertEqual(self.post('refresh',{},first['refresh_token']).status_code,401)
        self.assertEqual(self.post('logout',{},refreshed).status_code,401)
        self.assertEqual(self.post('refresh',{},second['refresh_token']).status_code,200)

    def test_recovery_disabled_without_mail(self):
        cap=self.client.get('/api/v1/auth/capabilities').json['data']
        self.assertFalse(cap['password_reset_enabled'])
        self.assertEqual(cap['oauth_providers'],[])
        self.assertEqual(self.post('forgot-password',{'email':'student@example.org'}).status_code,503)

    def test_malformed_logout_preserves_valid_session(self):
        session = self.register()
        self.assertEqual(self.post('logout', ['invalid'], session['access_token']).status_code, 400)
        self.assertEqual(self.post('refresh', {}, session['refresh_token']).status_code, 200)

    def test_legacy_oauth_predictable_password_is_rejected(self):
        from werkzeug.security import generate_password_hash
        self.register()
        with self.app.app_context():
            user = User.query.filter_by(username='trial_user').one()
            user.password_hash = generate_password_hash('oauth:github:123')
            db.session.commit()
        self.assertEqual(self.post('login', {'username':'trial_user','password':'oauth:github:123'}).status_code, 401)

    def test_oauth_username_collision_is_not_account_linking(self):
        self.register()
        with self.app.app_context():
            AuthService.register('github_125', 'taken@example.org', 'TrialPass123', 'Existing')
            session = AuthService.login_or_register_oauth('github', 125, 'verified@example.org')
            self.assertNotEqual(session['username'], 'github_125')
            self.assertEqual(session['email'], 'verified@example.org')

    def test_recovery_single_use_and_invalidates_all_sessions(self):
        session=self.register()
        token=self.recovery_token()
        with self.app.app_context():
            self.assertIsNotNone(db.session.get(AuthToken,hash_token(token)))
        response=self.post('reset-password',{'token':token,'password':'UpdatedPass123'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.post('reset-password',{'token':token,'password':'AnotherPass123'}).status_code,400)
        self.assertEqual(self.post('refresh',{},session['refresh_token']).status_code,401)
        self.assertEqual(self.post('logout',{},session['access_token']).status_code,401)
        self.assertEqual(self.post('login',{'username':'trial_user','password':self.payload['password']}).status_code,401)
        self.assertEqual(self.post('login',{'username':'trial_user','password':'UpdatedPass123'}).status_code,200)

    def test_expired_and_sibling_recovery_tokens(self):
        self.register()
        old=self.recovery_token()
        with self.app.app_context():
            db.session.get(AuthToken,hash_token(old)).expires_at=utc_now()-timedelta(seconds=1);db.session.commit()
        self.assertEqual(self.post('reset-password',{'token':old,'password':'UpdatedPass123'}).status_code,400)
        one=self.recovery_token();two=self.recovery_token()
        self.assertEqual(self.post('reset-password',{'token':one,'password':'UpdatedPass123'}).status_code,200)
        self.assertEqual(self.post('reset-password',{'token':two,'password':'UpdatedPass456'}).status_code,400)

    def test_recovery_unknown_account_and_mail_failure_are_generic(self):
        self.register();self.enable_mail()
        with patch('app.services.auth_security.send_reset_mail',side_effect=RuntimeError('secret provider response')):
            known=self.post('forgot-password',{'email':self.payload['email']})
        unknown=self.post('forgot-password',{'email':'missing@example.org'})
        self.assertEqual(known.json,unknown.json)
        with self.app.app_context():self.assertEqual(AuthToken.query.filter_by(purpose='reset').count(),0)

    def test_password_change_and_startup_preserve_password(self):
        self.register()
        with self.app.app_context():
            user=User.query.filter_by(username='student001').one()
            AuthService.change_password(user.id,'student123','UpdatedPass123')
            ensure_dev_login_users()
            self.assertTrue(check_password_hash(user.password_hash,'UpdatedPass123'))

    def test_persistent_rate_limit_across_clients(self):
        self.app.config['AUTH_RATE_LIMIT_ENABLED']=True
        for _ in range(15):
            self.assertEqual(self.post('login',{'username':'missing','password':'wrong'}).status_code,401)
        other=self.app.test_client()
        result=other.post('/api/v1/auth/login',json={'username':'missing','password':'wrong'})
        self.assertEqual(result.status_code,429)
        self.assertIn('Retry-After',result.headers)

    def test_oauth_requires_browser_state_and_verified_email(self):
        self.app.config.update(GITHUB_CLIENT_ID='test',GITHUB_CLIENT_SECRET='test')
        start=self.client.get('/api/v1/auth/oauth/github?redirect=//evil.example')
        state=parse_qs(urlparse(start.location).query)['state'][0]
        other=self.app.test_client()
        with patch('app.routes.auth.requests.post') as post:
            result=other.get('/api/v1/auth/oauth/github/callback',query_string={'state':state,'code':'test'})
            self.assertIn('error=',result.location);post.assert_not_called()
        with patch('app.routes.auth.requests.post') as post, patch('app.routes.auth._provider_profile',return_value={'id':123,'email':None}):
            post.return_value.json.return_value={'access_token':'test'}
            result=self.client.get('/api/v1/auth/oauth/github/callback',query_string={'state':state,'code':'test'})
            self.assertIn('error=',result.location)

    def test_oauth_identity_does_not_link_existing_email_and_password_is_random(self):
        self.register()
        with self.app.app_context():
            with self.assertRaises(ValueError):AuthService.login_or_register_oauth('github',123,self.payload['email'])
            created=AuthService.login_or_register_oauth('github',124,'oauth@example.org')
            user=db.session.get(User,created['id'])
            self.assertFalse(check_password_hash(user.password_hash,'oauth:github:124'))
            self.assertEqual(AuthService.login_or_register_oauth('github',124,'oauth@example.org')['id'],user.id)


if __name__=='__main__':unittest.main()
