# -*- coding: utf-8 -*-
import os
import unittest

from app import create_app
from app.services.code_execution import CodeExecutionService


class CodeExecutionServiceTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_wrap_python_expression(self):
        wrapped = CodeExecutionService.wrap_python_case(
            'def add(a, b):\n    return a + b',
            setup='',
            invoke='add(2, 3)',
            run_mode='expression',
        )
        self.assertIn('_plex_result = add(2, 3)', wrapped)
        self.assertIn('print(_plex_result)', wrapped)

    def test_mock_python_stdout(self):
        result = CodeExecutionService.run('python', 'print("Hello, PLEX!")')
        self.assertEqual(result['status']['id'], 3)
        self.assertIn('Hello, PLEX!', result['stdout'])

    def test_fullwidth_python_syntax_is_normalized(self):
        result = CodeExecutionService.run('python', 'print（＂Hello, PLEX!＂）')
        self.assertEqual(result['status']['id'], 3)
        self.assertEqual(result['stdout'].strip(), 'Hello, PLEX!')

    def test_fullwidth_punctuation_inside_strings_is_preserved(self):
        result = CodeExecutionService.run('python', 'print("（中文标点）")')
        self.assertEqual(result['status']['id'], 3)
        self.assertEqual(result['stdout'].strip(), '（中文标点）')

    def test_unsupported_language_rejected(self):
        with self.assertRaises(ValueError):
            CodeExecutionService.run('cpp', 'int main(){}')

    def test_mock_submit_with_setup(self):
        payload = CodeExecutionService.submit(
            'python',
            'print(a + b)',
            [{'id': 't1', 'label': 'case', 'setup': 'a = 3\nb = 5', 'expected': '8'}],
            'stdout',
        )
        self.assertTrue(payload['all_passed'])
        self.assertEqual(payload['passed_count'], 1)

    def test_backend_defaults_mock_without_env(self):
        os.environ.pop('JUDGE0_API_URL', None)
        self.assertEqual(CodeExecutionService.backend_name(), 'mock')


if __name__ == '__main__':
    unittest.main()
