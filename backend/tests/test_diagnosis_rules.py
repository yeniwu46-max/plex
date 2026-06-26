# -*- coding: utf-8 -*-
"""知识诊断引擎四层错因模型 golden cases。"""

import unittest

from agents.diagnosis import DiagnosisContext, diagnose


def _diagnose(payload: dict):
    return diagnose(DiagnosisContext.from_payload(payload))


class DiagnosisRuleTests(unittest.TestCase):
    def test_missing_colon_is_syntax(self):
        result = _diagnose({
            'code': 'for i in range(5)\n    print(i)',
            'stderr': "SyntaxError: expected ':'",
            'knowledgePoints': ['for 循环'],
            'attemptCount': 1,
        })
        self.assertEqual(result.error_layer, 'syntax')
        self.assertEqual(result.error_subtype, 'missing_colon')
        self.assertEqual(result.proficiency, 'cannot')

    def test_indentation_is_syntax(self):
        result = _diagnose({
            'code': 'for i in range(5):\nprint(i)',
            'stderr': 'IndentationError: expected an indented block',
            'knowledgePoints': ['for 循环'],
            'attemptCount': 1,
        })
        self.assertEqual(result.error_layer, 'syntax')
        self.assertEqual(result.error_subtype, 'indentation')

    def test_name_typo_detected(self):
        result = _diagnose({
            'code': 'count = 0\nprint(cnt)',
            'stderr': "NameError: name 'cnt' is not defined",
            'knowledgePoints': ['变量'],
            'attemptCount': 1,
        })
        self.assertEqual(result.error_layer, 'syntax')
        self.assertEqual(result.error_subtype, 'name_typo')

    def test_range_off_by_one_is_rule(self):
        result = _diagnose({
            'code': 's = 0\nfor i in range(1, n):\n    s += i\nprint(s)',
            'expectedOutput': '15',
            'stdout': '10',
            'knowledgePoints': ['range', 'for 循环'],
            'attemptCount': 1,
        })
        self.assertEqual(result.error_layer, 'rule')
        self.assertEqual(result.error_subtype, 'range_exclusive_end')

    def test_index_error_is_rule(self):
        result = _diagnose({
            'code': 'nums = [1, 2, 3]\nfor i in range(len(nums) + 1):\n    print(nums[i])',
            'stderr': 'IndexError: list index out of range',
            'knowledgePoints': ['列表'],
            'attemptCount': 1,
        })
        self.assertEqual(result.error_layer, 'rule')
        self.assertEqual(result.error_subtype, 'index_out_of_range')

    def test_while_no_termination_is_logic(self):
        result = _diagnose({
            'code': 'i = 0\nwhile i < 5:\n    print(i)',
            'expectedOutput': '0\n1\n2\n3\n4',
            'stdout': '',
            'knowledgePoints': ['while 循环'],
            'attemptCount': 1,
        })
        self.assertEqual(result.error_layer, 'logic')
        self.assertEqual(result.error_subtype, 'while_termination')
        self.assertEqual(result.strategy.type, 'trace_variables')

    def test_transfer_gap_when_base_mastered(self):
        result = _diagnose({
            'code': 'total = 0\nfor x in nums:\n    total += x\nprint(total)',
            'questionRequirements': '求列表中的最大值',
            'expectedOutput': '9',
            'stdout': '15',
            'knowledgePoints': ['最大值最小值'],
            'knowledgeMastery': [
                {'name': '累加求和', 'status': 'mastered'},
                {'name': 'for 循环', 'status': 'mastered'},
            ],
            'attemptCount': 1,
        })
        self.assertEqual(result.error_layer, 'transfer')
        self.assertEqual(result.proficiency, 'transfer_gap')
        self.assertEqual(result.strategy.type, 'pattern_compare')

    def test_can_but_wrong_when_node_mastered(self):
        result = _diagnose({
            'code': 's = 0\nfor i in range(1, n):\n    s += i\nprint(s)',
            'expectedOutput': '15',
            'stdout': '10',
            'knowledgePoints': ['range'],
            'knowledgeMastery': [{'name': 'range', 'status': 'mastered'}],
            'attemptCount': 3,
        })
        self.assertEqual(result.proficiency, 'can_but_wrong')

    def test_correct_answer_consolidate(self):
        result = _diagnose({
            'code': 'print(42)',
            'answerStatus': 'correct',
            'knowledgePoints': ['print 输出'],
            'attemptCount': 1,
        })
        self.assertEqual(result.error_layer, 'none')
        self.assertEqual(result.proficiency, 'mastered')
        self.assertEqual(result.strategy.type, 'consolidate')

    def test_to_dict_has_all_fields_and_legacy(self):
        result = _diagnose({
            'code': 'for i in range(1, n):\n    s += i',
            'stderr': 'wrong answer',
            'knowledgePoints': ['for 循环', 'range'],
            'attemptCount': 2,
        })
        data = result.to_dict()
        for key in (
            'errorLayer', 'errorSubtype', 'proficiency', 'proficiencyReason',
            'relatedKnowledgePoints', 'remediationStrategy', 'evidence',
            'errorType', 'weakPoints', 'diagnosis', 'confidence',
        ):
            self.assertIn(key, data)
        # 向后兼容：errorType 仍是旧枚举之一
        self.assertIn(data['errorType'], ('syntax', 'logic', 'concept', 'input_output', 'unknown'))
        self.assertTrue(0 <= data['confidence'] <= 1)
        self.assertIsInstance(data['remediationStrategy']['steps'], list)


if __name__ == '__main__':
    unittest.main()
