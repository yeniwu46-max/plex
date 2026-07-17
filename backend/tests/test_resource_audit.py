"""Tests for six-step resource audit pipeline."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app import create_app
from app.services.pedagogical_resource import analyze_pedagogy, build_knowledge_node, build_local_bundle
from app.services.resource_audit import ResourceAuditService
from app.services.resource_audit.code_tools import run_static_suite


class ResourceAuditTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')

    def test_audit_local_bundle_passes(self):
        with self.app.app_context():
            node = build_knowledge_node('loop')
            analysis = analyze_pedagogy(
                node,
                target='大学',
                learning_stage='学习',
                learning_styles=['案例'],
                profile={'knowledge_foundation': '有基础'},
            )
            bundle = build_local_bundle('loop', analysis=analysis, profile={'knowledge_foundation': '有基础'})
            report = ResourceAuditService.audit_bundle(
                bundle,
                'loop',
                {'knowledge_foundation': '有基础'},
                confidence=0.9,
                citations=[{
                    'document_id': 'python-stage2-loop',
                    'title': '循环',
                    'section': 'loop',
                    'snippet': '循环',
                }],
            )
            self.assertIn(report.verdict, ('PASS', 'NEED_MODIFY'))
            self.assertEqual(len(report.steps), 6)
            self.assertGreaterEqual(report.dimensions.knowledge_accuracy, 60)
            self.assertIn('knowledge_accuracy', report.dimensions.to_dict())

    def test_audit_detects_fantasy_api(self):
        with self.app.app_context():
            node = build_knowledge_node('loop')
            analysis = analyze_pedagogy(
                node,
                target='大学',
                learning_stage='学习',
                learning_styles=['案例'],
                profile={},
            )
            bundle = build_local_bundle('loop', analysis=analysis, profile={})
            bundle['code'][0]['source'] = 'import django\nprint(1)\n'
            report = ResourceAuditService.audit_bundle(bundle, 'loop', {})
            fail_ids = [
                check.id
                for step in report.steps
                for check in step.checks
                if check.level == 'FAIL'
            ]
            self.assertIn('fantasy_api', fail_ids)
            self.assertEqual(report.verdict, 'REJECT')

    def test_static_suite_missing_tools_warns_not_fails(self):
        with patch('app.services.resource_audit.code_tools.shutil.which', return_value=None):
            with patch('app.services.resource_audit.code_tools._tool_module', return_value=False):
                results = run_static_suite([('demo', 'print("ok")\n')])
        compile_rows = [row for row in results if row['tool'] == 'compile']
        self.assertTrue(compile_rows)
        self.assertEqual(compile_rows[0]['level'], 'PASS')
        skipped = [row for row in results if '未安装' in row.get('detail', '')]
        self.assertGreaterEqual(len(skipped), 1)

    def test_audit_report_to_dict_roundtrip(self):
        with self.app.app_context():
            node = build_knowledge_node('var')
            analysis = analyze_pedagogy(
                node,
                target='大学',
                learning_stage='学习',
                learning_styles=['图文'],
                profile={},
            )
            bundle = build_local_bundle('var', analysis=analysis, profile={})
            report = ResourceAuditService.audit_bundle(bundle, 'var', {})
            payload = report.to_dict()
            self.assertEqual(payload['verdict'], report.verdict)
            self.assertEqual(len(payload['steps']), 6)
            self.assertTrue(payload['dimensions']['code_quality'] >= 0)


if __name__ == '__main__':
    unittest.main()
