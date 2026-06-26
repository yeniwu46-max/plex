"""Evaluate deterministic personalization across all course knowledge points."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data.course_knowledge import validate_course_knowledge
from app.services.personalized_resource import (
    POINTS,
    RESOURCE_TYPES,
    PersonalizedResourceService,
)


PROFILES = {
    'beginner_lifestyle': {
        'major_background': '非计算机专业大一',
        'knowledge_foundation': 'Python 零基础',
        'learning_goal': '掌握 Python 基础并完成校园小工具',
        'explanation_preference': '分步骤讲解和生活化案例',
        'mistake_pattern': '循环边界与缩进容易出错',
        'learning_pace': '每天 30 分钟',
        'interest_direction': '校园生活自动化',
    },
    'algorithm_improver': {
        'major_background': '软件工程专业',
        'knowledge_foundation': '具备 Python 编程基础',
        'learning_goal': '提升算法设计与复杂度分析能力',
        'explanation_preference': '先看代码和挑战题',
        'mistake_pattern': '复杂边界条件考虑不足',
        'learning_pace': '周末集中学习 3 小时',
        'interest_direction': '算法竞赛',
    },
}


def _serialized_bundle(resources: list[dict]) -> str:
    return json.dumps(resources, ensure_ascii=False, sort_keys=True)


def _bundle_metrics(knowledge_key: str, profile_name: str, profile: dict) -> dict:
    resources = PersonalizedResourceService._local_resources(
        knowledge_key, list(RESOURCE_TYPES), profile
    )
    quality = PersonalizedResourceService._quality_report(resources, knowledge_key)
    serialized = _serialized_bundle(resources)
    expected_difficulty = 40 if '零基础' in profile['knowledge_foundation'] else 65
    constraints = {
        'difficulty': all(item['difficulty'] == expected_difficulty for item in resources),
        'explanation': profile['explanation_preference'] in serialized,
        'interest': profile['interest_direction'] in serialized,
        'pace': profile['learning_pace'] in serialized,
    }
    return {
        'profile': profile_name,
        'knowledge_key': knowledge_key,
        'knowledge_label': POINTS[knowledge_key],
        'resource_count': len(resources),
        'resource_types': [item['resource_type'] for item in resources],
        'schema_pass_count': quality['schema_pass_count'],
        'citation_pass_count': quality['citation_pass_count'],
        'approved_count': quality['approved_count'],
        'pending_review_count': quality['pending_review_count'],
        'difficulty_min': min(item['difficulty'] for item in resources),
        'difficulty_max': max(item['difficulty'] for item in resources),
        'estimated_minutes_min': min(item['estimated_minutes'] for item in resources),
        'estimated_minutes_max': max(item['estimated_minutes'] for item in resources),
        'constraint_matches': constraints,
        'constraint_coverage_rate': round(
            sum(constraints.values()) / len(constraints), 4
        ),
        'bundle_hash': hashlib.sha256(serialized.encode('utf-8')).hexdigest(),
        'resources': resources,
    }


def _resource_features(resources: list[dict]) -> dict:
    by_type = {item['resource_type']: item for item in resources}
    return {
        'difficulty': [item['difficulty'] for item in resources],
        'estimated_minutes': [item['estimated_minutes'] for item in resources],
        'recommendation_reasons': [
            item['recommendation_reason'] for item in resources
        ],
        'lesson_markdown': by_type['lesson_document']['content']['markdown'],
        'exercise_levels': [
            item['level']
            for item in by_type['exercise_set']['content']['questions']
        ],
        'exercise_questions': [
            item['question']
            for item in by_type['exercise_set']['content']['questions']
        ],
        'reading_markdown': by_type['extended_reading']['content']['markdown'],
        'coding_scenario': by_type['coding_lab']['content']['scenario'],
    }


def _counterfactual_checks() -> list[dict]:
    knowledge_key = 'loop'
    base_profile = dict(PROFILES['beginner_lifestyle'])
    base = _resource_features(PersonalizedResourceService._local_resources(
        knowledge_key, list(RESOURCE_TYPES), base_profile
    ))
    changes = {
        'knowledge_foundation': '具备 Python 编程基础',
        'explanation_preference': '先看代码和挑战题',
        'interest_direction': '算法竞赛',
        'learning_pace': '周末集中学习 3 小时',
    }
    rows = []
    for dimension, value in changes.items():
        profile = {**base_profile, dimension: value}
        changed = _resource_features(PersonalizedResourceService._local_resources(
            knowledge_key, list(RESOURCE_TYPES), profile
        ))
        if dimension == 'knowledge_foundation':
            expected_changes = (
                base['difficulty'] != changed['difficulty']
                and base['estimated_minutes'] != changed['estimated_minutes']
                and base['exercise_levels'] != changed['exercise_levels']
            )
            stable_unrelated = (
                base['lesson_markdown'] == changed['lesson_markdown']
                and base['exercise_questions'] == changed['exercise_questions']
                and base['coding_scenario'] == changed['coding_scenario']
            )
        elif dimension == 'explanation_preference':
            expected_changes = (
                base['lesson_markdown'] != changed['lesson_markdown']
                and base['recommendation_reasons'] != changed['recommendation_reasons']
            )
            stable_unrelated = (
                base['difficulty'] == changed['difficulty']
                and base['estimated_minutes'] == changed['estimated_minutes']
                and base['exercise_levels'] == changed['exercise_levels']
                and base['coding_scenario'] == changed['coding_scenario']
            )
        elif dimension == 'interest_direction':
            expected_changes = (
                base['lesson_markdown'] != changed['lesson_markdown']
                and base['exercise_questions'] != changed['exercise_questions']
                and base['reading_markdown'] != changed['reading_markdown']
                and base['coding_scenario'] != changed['coding_scenario']
            )
            stable_unrelated = (
                base['difficulty'] == changed['difficulty']
                and base['estimated_minutes'] == changed['estimated_minutes']
                and base['exercise_levels'] == changed['exercise_levels']
                and base['recommendation_reasons'] == changed['recommendation_reasons']
            )
        else:
            expected_changes = (
                base['recommendation_reasons'] != changed['recommendation_reasons']
            )
            stable_unrelated = all(
                base[key] == changed[key]
                for key in (
                    'difficulty',
                    'estimated_minutes',
                    'lesson_markdown',
                    'exercise_levels',
                    'exercise_questions',
                    'reading_markdown',
                    'coding_scenario',
                )
            )
        rows.append({
            'dimension': dimension,
            'expected_changes_passed': expected_changes,
            'unrelated_features_stable': stable_unrelated,
            'passed': expected_changes and stable_unrelated,
        })
    return rows


def evaluate() -> dict:
    knowledge_report = validate_course_knowledge()
    if knowledge_report['status'] != 'passed':
        raise RuntimeError(
            'knowledge base validation failed: ' + '; '.join(knowledge_report['errors'])
        )

    bundles = []
    comparisons = []
    for knowledge_key in POINTS:
        by_profile = {
            profile_name: _bundle_metrics(knowledge_key, profile_name, profile)
            for profile_name, profile in PROFILES.items()
        }
        bundles.extend(by_profile.values())
        beginner = by_profile['beginner_lifestyle']
        advanced = by_profile['algorithm_improver']
        beginner_resources = {
            item['resource_type']: item for item in beginner['resources']
        }
        advanced_resources = {
            item['resource_type']: item for item in advanced['resources']
        }
        changed_types = [
            resource_type
            for resource_type in RESOURCE_TYPES
            if beginner_resources[resource_type] != advanced_resources[resource_type]
        ]
        beginner_text = _serialized_bundle(beginner['resources'])
        advanced_text = _serialized_bundle(advanced['resources'])
        comparisons.append({
            'knowledge_key': knowledge_key,
            'knowledge_label': POINTS[knowledge_key],
            'difficulty_difference': (
                advanced['difficulty_min'] - beginner['difficulty_min']
            ),
            'expression_difference': (
                PROFILES['beginner_lifestyle']['explanation_preference'] in beginner_text
                and PROFILES['algorithm_improver']['explanation_preference'] in advanced_text
            ),
            'case_difference': (
                PROFILES['beginner_lifestyle']['interest_direction'] in beginner_text
                and PROFILES['algorithm_improver']['interest_direction'] in advanced_text
            ),
            'exercise_level_difference': (
                beginner_resources['exercise_set']['content']['questions'][0]['level']
                != advanced_resources['exercise_set']['content']['questions'][0]['level']
            ),
            'changed_resource_type_count': len(changed_types),
            'changed_resource_types': changed_types,
            'bundle_hash_difference': beginner['bundle_hash'] != advanced['bundle_hash'],
        })

    total_resources = sum(item['resource_count'] for item in bundles)
    schema_passes = sum(item['schema_pass_count'] for item in bundles)
    citation_passes = sum(item['citation_pass_count'] for item in bundles)
    expected_bundles = len(POINTS) * len(PROFILES)
    successful_bundles = sum(
        item['resource_count'] == len(RESOURCE_TYPES) for item in bundles
    )
    counterfactuals = _counterfactual_checks()
    return {
        'run_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'backend': 'local_rules',
        'knowledge_point_count': len(POINTS),
        'profile_count': len(PROFILES),
        'bundle_count': len(bundles),
        'resource_count': total_resources,
        'summary': {
            'task_success_rate': round(successful_bundles / expected_bundles, 4),
            'schema_pass_rate': round(schema_passes / total_resources, 4),
            'citation_valid_rate': round(citation_passes / total_resources, 4),
            'average_profile_constraint_coverage': round(
                sum(item['constraint_coverage_rate'] for item in bundles) / len(bundles),
                4,
            ),
            'difficulty_difference_pass_rate': round(
                sum(item['difficulty_difference'] > 0 for item in comparisons)
                / len(comparisons),
                4,
            ),
            'expression_difference_pass_rate': round(
                sum(item['expression_difference'] for item in comparisons)
                / len(comparisons),
                4,
            ),
            'case_difference_pass_rate': round(
                sum(item['case_difference'] for item in comparisons)
                / len(comparisons),
                4,
            ),
            'exercise_level_difference_pass_rate': round(
                sum(item['exercise_level_difference'] for item in comparisons)
                / len(comparisons),
                4,
            ),
            'bundle_difference_pass_rate': round(
                sum(item['bundle_hash_difference'] for item in comparisons)
                / len(comparisons),
                4,
            ),
            'counterfactual_pass_rate': round(
                sum(item['passed'] for item in counterfactuals)
                / len(counterfactuals),
                4,
            ),
        },
        'profiles': PROFILES,
        'knowledge_base': {
            key: knowledge_report[key]
            for key in (
                'status',
                'knowledge_point_count',
                'valid_knowledge_point_count',
                'coverage_rate',
                'document_id_count',
                'source_file_count',
            )
        },
        'comparisons': comparisons,
        'counterfactuals': counterfactuals,
        'bundles': bundles,
    }


def _write_csv(report: dict, path: Path) -> None:
    fields = [
        'knowledge_key',
        'knowledge_label',
        'difficulty_difference',
        'expression_difference',
        'case_difference',
        'exercise_level_difference',
        'changed_resource_type_count',
        'changed_resource_types',
        'bundle_hash_difference',
    ]
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report['comparisons']:
            writer.writerow({
                **row,
                'changed_resource_types': ','.join(row['changed_resource_types']),
            })


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--output',
        type=Path,
        default=ROOT / 'reports' / 'personalization',
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    report = evaluate()
    (args.output / 'personalization-evaluation.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    _write_csv(report, args.output / 'personalization-comparisons.csv')
    print(json.dumps(report['summary'], ensure_ascii=False, indent=2))
    return 0 if all(value == 1 for value in report['summary'].values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
