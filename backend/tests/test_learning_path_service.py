# -*- coding: utf-8 -*-
import unittest

from app import create_app
from app.models import Role, User, db
from app.services.learning_path import LearningPathService
from werkzeug.security import generate_password_hash


class LearningPathServiceTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        student_role = Role.query.filter_by(name='student').first()
        self.user = User(
            username='lp-student',
            email='lp@example.com',
            password_hash=generate_password_hash('student123'),
            real_name='路径学生',
            role_id=student_role.id,
        )
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_plan_returns_ordered_nodes(self):
        plan = LearningPathService.plan(self.user.id)
        self.assertIn('ordered_nodes', plan)
        self.assertGreater(len(plan['ordered_nodes']), 0)
        self.assertIn('next_best_action', plan)
        self.assertIn('graph_backend', plan)

    def test_prerequisite_locking_for_advanced_without_basics(self):
        plan = LearningPathService.plan(self.user.id, focus_node_id='nested')
        nested = next((n for n in plan['ordered_nodes'] if n['id'] == 'nested'), None)
        if nested:
            self.assertTrue(nested['locked'] or nested['prerequisites_met'] is False)

    def test_focus_node_in_plan(self):
        plan = LearningPathService.plan(self.user.id, focus_node_id='loop')
        ids = [n['id'] for n in plan['ordered_nodes']]
        self.assertIn('loop', ids)
