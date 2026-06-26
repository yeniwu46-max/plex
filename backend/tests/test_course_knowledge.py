import tempfile
import unittest
from pathlib import Path

from app.data.course_knowledge import (
    COURSE_KNOWLEDGE_SOURCES,
    KNOWLEDGE_ROOT,
    validate_course_knowledge,
)
from scripts.evaluate_personalization import evaluate
from scripts.evaluate_profile_extraction import evaluate as evaluate_profile_extraction


class CourseKnowledgeTestCase(unittest.TestCase):
    def test_canonical_knowledge_base_is_complete(self):
        report = validate_course_knowledge()
        self.assertEqual(report['status'], 'passed', report['errors'])
        self.assertEqual(report['knowledge_point_count'], 16)
        self.assertEqual(report['valid_knowledge_point_count'], 16)
        self.assertEqual(report['coverage_rate'], 1)
        self.assertEqual(report['document_id_count'], 16)
        self.assertEqual(len(COURSE_KNOWLEDGE_SOURCES), 16)

    def test_duplicate_document_id_fails_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for source in KNOWLEDGE_ROOT.glob('*.md'):
                (root / source.name).write_text(
                    source.read_text(encoding='utf-8'),
                    encoding='utf-8',
                )
            target = root / '04-functions-practice.md'
            text = target.read_text(encoding='utf-8')
            text = text.replace(
                'python-stage4-linear-search',
                'python-stage4-sum-statistics',
            )
            target.write_text(text, encoding='utf-8')
            report = validate_course_knowledge(root)
        self.assertEqual(report['status'], 'failed')
        self.assertTrue(
            any('duplicate source document_id' in error for error in report['errors'])
        )

    def test_two_profile_evaluation_meets_local_gate(self):
        report = evaluate()
        self.assertEqual(report['bundle_count'], 32)
        self.assertEqual(report['resource_count'], 160)
        self.assertTrue(all(value == 1 for value in report['summary'].values()))
        self.assertTrue(all(
            row['changed_resource_type_count'] == 5
            for row in report['comparisons']
        ))
        self.assertTrue(all(row['passed'] for row in report['counterfactuals']))

    def test_profile_extraction_label_set_meets_accuracy_gate(self):
        report = evaluate_profile_extraction()
        self.assertGreaterEqual(report['summary']['balanced_field_accuracy'], 0.85)
        self.assertGreaterEqual(report['summary']['exact_case_match_rate'], 0.85)


if __name__ == '__main__':
    unittest.main()
