# -*- coding: utf-8 -*-
import unittest

from app import create_app
from app.data.knowledge_node_registry import all_node_ids
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

    def test_nothing_is_locked_when_unlock_all(self):
        """UNLOCK_ALL 打开后，零基础学生也应当能进入任意节点。"""
        plan = LearningPathService.plan(self.user.id, focus_node_id='func-recursion')
        self.assertTrue(plan['ordered_nodes'])
        for node in plan['ordered_nodes']:
            self.assertFalse(node['locked'], f"{node['id']} 不应被锁定")
            self.assertIsNot(node['prerequisites_met'], False)

    def test_focus_node_in_plan(self):
        plan = LearningPathService.plan(self.user.id, focus_node_id='loop-for')
        ids = [n['id'] for n in plan['ordered_nodes']]
        self.assertIn('loop-for', ids)

    def test_plan_covers_all_registry_nodes(self):
        plan = LearningPathService.plan(self.user.id)
        ids = {n['id'] for n in plan['ordered_nodes']}
        self.assertEqual(ids, set(all_node_ids()))
