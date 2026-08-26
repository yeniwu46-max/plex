import tempfile
import unittest
from pathlib import Path

from app.data.course_knowledge import (
    COURSE_KNOWLEDGE_SOURCES,
    KNOWLEDGE_ROOT,
    validate_course_knowledge,
)
from app.data.knowledge_node_registry import all_node_ids
from app.services.pedagogical_resource import POINTS
from scripts.evaluate_personalization import PROFILES, evaluate
from scripts.evaluate_profile_extraction import evaluate as evaluate_profile_extraction
from app.services.personalized_resource import RESOURCE_TYPES


class CourseKnowledgeTestCase(unittest.TestCase):
    def test_canonical_knowledge_base_is_complete(self):
        node_count = len(all_node_ids())
        report = validate_course_knowledge()
        self.assertEqual(report['status'], 'passed', report['errors'])
        self.assertEqual(report['knowledge_point_count'], node_count)
        self.assertEqual(report['valid_knowledge_point_count'], node_count)
        self.assertEqual(report['coverage_rate'], 1)
        self.assertEqual(report['document_id_count'], node_count)
        self.assertEqual(len(COURSE_KNOWLEDGE_SOURCES), node_count)
        self.assertEqual(len(POINTS), node_count)

    def test_duplicate_document_id_fails_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for source in KNOWLEDGE_ROOT.glob('*.md'):
                (root / source.name).write_text(
                    source.read_text(encoding='utf-8'),
                    encoding='utf-8',
                )
            target = root / '04-loop.md'
            text = target.read_text(encoding='utf-8')
            text = text.replace(
                'python-loop-for',
                'python-func-define',
            )
            target.write_text(text, encoding='utf-8')
            report = validate_course_knowledge(root)
        self.assertEqual(report['status'], 'failed')
        self.assertTrue(
            any('duplicate source document_id' in error for error in report['errors'])
        )

    def test_two_profile_evaluation_meets_local_gate(self):
        report = evaluate()
        expected_bundles = len(POINTS) * len(PROFILES)
        self.assertEqual(report['bundle_count'], expected_bundles)
        self.assertEqual(report['resource_count'], expected_bundles * len(RESOURCE_TYPES))
        self.assertEqual(report['summary']['task_success_rate'], 1)
        self.assertEqual(report['summary']['citation_valid_rate'], 1)
        self.assertGreaterEqual(report['summary']['counterfactual_pass_rate'], 0.75)
        self.assertTrue(all(
            row['changed_resource_type_count'] >= 5
            for row in report['comparisons']
        ))

    def test_profile_extraction_label_set_meets_accuracy_gate(self):
        report = evaluate_profile_extraction()
        self.assertGreaterEqual(report['summary']['balanced_field_accuracy'], 0.85)
        self.assertGreaterEqual(report['summary']['exact_case_match_rate'], 0.85)


if __name__ == '__main__':
    unittest.main()
