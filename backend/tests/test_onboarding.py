"""Arrival transactions and access boundaries, using an isolated SQLite file."""
import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from app import create_app, ensure_dev_login_users
from app.config import TestingConfig
from app.models import db, User, StudentOnboarding, AdventurerCounter, UserAppearance, StudentProfile, StudentProfileHistory
from app.services.auth import AuthService
from app.services.onboarding import OnboardingService
from app.services.student_profile import StudentProfileService
from app.services.user import UserService

ANSWERS = {'age_range': '19_24', 'programming_level': 'syntax', 'field': 'software'}
PREFS = {'visual_style': 'comic', 'color_mode': 'light'}


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        uri = 'sqlite:///' + self.directory.name.replace('\\', '/') + '/arrival.db'
        self.mysql_schema = os.environ.get('PLEX_ONBOARDING_TEST_MYSQL_SCHEMA')
        if self.mysql_schema:
            import re
            from sqlalchemy.engine import make_url
            from app.config import DevelopmentConfig
            if not re.fullmatch(r'plex_onboarding_test_[a-f0-9]{12}', self.mysql_schema):
                raise ValueError('Only an explicitly isolated test schema is allowed')
            uri = make_url(DevelopmentConfig.SQLALCHEMY_DATABASE_URI).set(database=self.mysql_schema)
        self.config = patch.multiple(TestingConfig, SQLALCHEMY_DATABASE_URI=uri, SQLALCHEMY_ECHO=False)
        self.config.start()
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.serial = 0

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            if self.mysql_schema:
                from sqlalchemy import inspect, text
                assert db.engine.url.database == self.mysql_schema
                # Existing users/classes have circular FKs; isolate teardown to
                # the explicitly named scratch schema, never the application DB.
                with db.engine.begin() as connection:
                    connection.execute(text('SET FOREIGN_KEY_CHECKS=0'))
                    try:
                        quote = connection.dialect.identifier_preparer.quote
                        for table in inspect(connection).get_table_names():
                            connection.execute(text('DROP TABLE ' + quote(table)))
                    finally:
                        connection.execute(text('SET FOREIGN_KEY_CHECKS=1'))
            db.engine.dispose()
        self.config.stop()
        self.directory.cleanup()

    def register(self):
        self.serial += 1
        result = self.client.post('/api/v1/auth/register', json=dict(username=f'arrival_{self.serial}', email=f'arrival_{self.serial}@example.org', real_name='新旅人', password='ArrivalPass123'))
        self.assertEqual(result.status_code, 201, result.json)
        return result.json['data']

    def request(self, account, method='GET', suffix='', body=None, client=None):
        return (client or self.client).open('/api/v1/student/onboarding' + suffix, method=method, json=body,
            headers={'Authorization': 'Bearer ' + account['access_token']})

    def complete(self, account, action='submit', **kw):
        result = self.request(account, 'POST', '/complete', {'action': action, 'answers': ANSWERS, 'preferences': PREFS, **kw})
        self.assertEqual(result.status_code, 200, result.json)
        return result.json['data']

    def test_submission_history_and_welcome_recovery(self):
        a = self.register()
        self.assertTrue(a['onboarding']['required'])
        result = self.complete(a)
        self.assertEqual(result['onboarding']['adventurer_number'], 201)
        self.assertTrue(self.request(a).json['data']['onboarding']['welcome_pending'])
        repeated = self.complete(a, 'skip')
        self.assertEqual(repeated, result)
        with self.app.app_context():
            profile = StudentProfile.query.filter_by(user_id=a['id']).one()
            self.assertEqual(profile.dimensions['knowledge_foundation']['value'], '了解基本语法')
            self.assertEqual(profile.dimensions['major_background']['origin'], 'onboarding')
            self.assertNotIn('age_range', json.dumps(profile.dimensions))
            self.assertEqual(StudentProfileHistory.query.filter_by(user_id=a['id'], reason='onboarding_survey').count(), 1)
        acknowledged = self.request(a, 'POST', '/acknowledge').json['data']
        self.assertFalse(acknowledged['onboarding']['required'])
        self.assertEqual(self.request(a, 'POST', '/acknowledge').json['data'], acknowledged)

    def test_skip_discards_draft_and_later_edit_keeps_number(self):
        a = self.register()
        draft = self.request(a, 'PATCH', body={'answers': ANSWERS, 'step': 2})
        self.assertEqual(draft.status_code, 200)
        self.assertEqual(self.request(a).json['data']['step'], 2)
        result = self.complete(a, 'skip')
        self.assertEqual(result['draft'], {})
        self.assertEqual(result['answers'], {})
        self.assertEqual(result['preferences'], PREFS)
        late_draft = self.request(a, 'PATCH', body={'answers': ANSWERS, 'draft_only': True}).json['data']
        self.assertEqual(late_draft['answers'], {})
        self.request(a, 'POST', '/acknowledge')
        edited = self.request(a, 'PATCH', body={'answers': ANSWERS}).json['data']
        self.assertEqual(edited['onboarding']['adventurer_number'], 201)
        self.assertFalse(edited['onboarding']['required'])
        self.assertEqual(self.complete(self.register())['onboarding']['adventurer_number'], 202)

    def test_unknown_answers_do_not_fabricate_foundation(self):
        a = self.register()
        self.complete(a, answers={'age_range': 'private', 'programming_level': 'unknown', 'field': 'private'})
        with self.app.app_context():
            profile = StudentProfileService.get_or_create(a['id'])
            self.assertIsNone(profile.dimensions['knowledge_foundation']['value'])
        self.request(a, 'PATCH', body={'answers': ANSWERS})
        self.request(a, 'PATCH', body={'answers': {'age_range': 'private', 'programming_level': 'unknown', 'field': 'other'}})
        with self.app.app_context():
            profile = StudentProfile.query.filter_by(user_id=a['id']).one()
            self.assertIsNone(profile.dimensions['knowledge_foundation']['value'])
            self.assertIsNone(profile.dimensions['major_background']['value'])

    def test_failure_rolls_back_profile_counter_answers_and_preferences(self):
        a = self.register()
        real_apply = StudentProfileService.apply_changes
        def fail_after_flush(*args, **kwargs):
            real_apply(*args, **kwargs)
            raise RuntimeError('test transaction failure')
        with patch.object(StudentProfileService, 'apply_changes', side_effect=fail_after_flush):
            response = self.request(a, 'POST', '/complete', {'action': 'submit', 'answers': ANSWERS, 'preferences': PREFS})
        self.assertEqual(response.status_code, 500)
        with self.app.app_context():
            self.assertEqual(db.session.get(AdventurerCounter, 1).last_number, 200)
            self.assertEqual(db.session.get(StudentOnboarding, a['id']).status, 'pending')
            self.assertIsNone(db.session.get(UserAppearance, a['id']))
            self.assertEqual(StudentProfileHistory.query.filter_by(user_id=a['id']).count(), 0)
        self.assertEqual(self.complete(a)['onboarding']['adventurer_number'], 201)

    def test_legacy_exempt_oauth_and_managed_accounts_pending(self):
        legacy = self.client.post('/api/v1/auth/login', json={'username':'student001','password':'student123'}).json['data']
        self.assertFalse(legacy['onboarding']['required'])
        result = self.request(legacy, 'PATCH', body={'answers': ANSWERS}).json['data']
        self.assertIsNone(result['onboarding']['adventurer_number'])
        with self.app.app_context():
            oauth = AuthService.login_or_register_oauth('github', 'new-arrival', 'new-arrival@example.org')
            self.assertTrue(oauth['onboarding']['required'])
            managed = UserService.create_student('managed_arrival', 'managed@example.org', 'ManagedPass123', '代建学生')
            self.assertTrue(OnboardingService.summary(managed.id)['required'])
            ensure_dev_login_users()
            self.assertTrue(OnboardingService.summary(managed.id)['required'])
            self.assertEqual(db.session.get(AdventurerCounter, 1).last_number, 200)

    def test_validation_self_only_and_staff_excluded(self):
        a, b = self.register(), self.register()
        for body in [{'answers': ANSWERS, 'user_id': b['id']}, {'answers': {**ANSWERS,'field_detail': 'x'*51}}, {'answers': {'age_range': []}}, {'answers': ANSWERS,'step': True}]:
            self.assertEqual(self.request(a, 'PATCH', body=body).status_code, 400)
        self.assertEqual(self.request(a, 'POST', '/complete', {'action':'submit','answers':{},'preferences':PREFS}).status_code, 400)
        self.assertEqual(self.client.get('/api/v1/student/onboarding').status_code, 401)
        for username, password in [('teacher001','teacher123'),('admin','admin123')]:
            staff = self.client.post('/api/v1/auth/login', json={'username': username, 'password': password}).json['data']
            self.assertFalse(staff['onboarding']['required'])
            self.assertEqual(self.request(staff).status_code, 403)
        self.complete(a)
        self.assertEqual(self.request(b).json['data']['answers'], {})
        self.assertIsNone(self.request(b).json['data']['preferences'])

    def test_concurrent_accounts_and_same_account_retries(self):
        accounts = [self.register() for _ in range(3)]
        requests = [accounts[0], accounts[0], accounts[1], accounts[2]]
        barrier = Barrier(len(requests))
        def complete(account):
            with self.app.test_client() as client:
                barrier.wait(timeout=10)
                response = self.request(account, 'POST', '/complete', {'action': 'skip', 'preferences': PREFS}, client)
                self.assertEqual(response.status_code, 200, response.json)
                return response.json['data']['onboarding']['adventurer_number']
        with ThreadPoolExecutor(max_workers=4) as pool:
            numbers = list(pool.map(complete, requests))
        self.assertEqual(numbers[0], numbers[1])
        self.assertEqual(set(numbers), {201,202,203})

    def test_preferences_survive_new_session_and_are_account_scoped(self):
        a, b = self.register(), self.register()
        headers = {'Authorization': 'Bearer '+a['access_token']}
        for style in ['space','comic']:
            for mode in ['dark','light','auto']:
                value = {'visual_style': style, 'color_mode': mode}
                self.assertEqual(self.client.patch('/api/v1/users/me/preferences', json=value, headers=headers).json['data'], value)
        login = self.client.post('/api/v1/auth/login', json={'username':a['username'],'password':'ArrivalPass123'}).json['data']
        self.assertEqual(login['preferences'], {'visual_style':'comic','color_mode':'auto'})
        self.assertIsNone(self.request(b).json['data']['preferences'])

    def test_sqlite_migration_backfills_and_preserves_state(self):
        import importlib.util
        from pathlib import Path
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        spec = importlib.util.spec_from_file_location('arrival_migration', Path(__file__).parents[1] / 'migrations/versions/20261014_0017_student_onboarding.py')
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        a = self.register()
        self.complete(a)
        with self.app.app_context():
            with db.engine.begin() as connection:
                with Operations.context(MigrationContext.configure(connection)):
                    migration.upgrade()
                    migration.upgrade()
            db.session.expire_all()
            legacy = User.query.filter_by(username='student001').one()
            self.assertEqual(db.session.get(StudentOnboarding, legacy.id).status, 'exempt')
            self.assertEqual(db.session.get(StudentOnboarding, a['id']).adventurer_number, 201)
            self.assertEqual(db.session.get(AdventurerCounter, 1).last_number, 201)

    def test_migration_creates_new_tables_on_existing_database(self):
        import importlib.util
        from pathlib import Path
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        spec = importlib.util.spec_from_file_location('arrival_migration', Path(__file__).parents[1] / 'migrations/versions/20261014_0017_student_onboarding.py')
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with self.app.app_context():
            db.session.remove()
            with db.engine.begin() as connection:
                for model in [UserAppearance, AdventurerCounter, StudentOnboarding]:
                    model.__table__.drop(connection)
                with Operations.context(MigrationContext.configure(connection)):
                    migration.upgrade()
            self.assertEqual(db.session.get(AdventurerCounter, 1).last_number, 200)
            legacy = User.query.filter_by(username='student001').one()
            self.assertEqual(db.session.get(StudentOnboarding, legacy.id).status, 'exempt')
        self.assertEqual(self.complete(self.register())['onboarding']['adventurer_number'], 201)
