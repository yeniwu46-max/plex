"""Run a 100-node local grounding/risk-control benchmark.

This measures the deterministic RAG/citation guard, not the hallucination rate
of a live model.  The report keeps those claims separate.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.services.pedagogical_resource import POINTS
from app.services.personalized_resource import PersonalizedResourceService
from scripts.evaluate_personalization import PROFILES, _generate_resources


def main():
    clean_failures = []
    negative_controls = []
    profile = PROFILES['beginner_lifestyle']
    for index, knowledge_key in enumerate(POINTS):
        resources = _generate_resources(knowledge_key, profile)
        quality = PersonalizedResourceService._quality_report(resources, knowledge_key, allow_remote_review=False)
        clean_risks = sorted({risk for item in quality['items'] for risk in item['risk_reasons']})
        if any(risk in clean_risks for risk in ('invalid_citation', 'schema_invalid', 'out_of_scope', 'fantasy_api')):
            clean_failures.append({'knowledge_key': knowledge_key, 'risks': clean_risks})
        if index % 10 == 0:
            corrupted = [dict(item) for item in resources]
            corrupted[0]['citations'] = [{'document_id': 'fake-document', 'section': 'outside-course'}]
            corrupted_quality = PersonalizedResourceService._quality_report(corrupted, knowledge_key, allow_remote_review=False)
            detected = any('invalid_citation' in item['risk_reasons'] for item in corrupted_quality['items'])
            negative_controls.append({'knowledge_key': knowledge_key, 'detected_invalid_citation': detected})
    report = {
        'benchmark': 'local-rag-grounding-and-hallucination-guard',
        'sample_count': len(POINTS),
        'clean_hallucination_rate': round(len(clean_failures) / max(len(POINTS), 1), 4),
        'clean_failures': clean_failures,
        'negative_control_count': len(negative_controls),
        'negative_control_detection_rate': round(sum(item['detected_invalid_citation'] for item in negative_controls) / max(len(negative_controls), 1), 4),
        'backend': 'local_rules',
        'remote_model_hallucination_verified': False,
        'note': '本地 RAG/图谱约束基准；不能替代真实讯飞输出的幻觉率测评。',
    }
    output = Path(__file__).resolve().parents[1] / 'reports' / 'iflytek-990-hallucination-local-20260828.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
