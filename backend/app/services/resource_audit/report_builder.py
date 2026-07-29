"""Step 6: aggregate scores and verdict."""
from __future__ import annotations

from app.services.pedagogical_resource import validate_bundle_risks

from .schema import AuditReport, DimensionScores, StepResult, Verdict


def _citations_are_valid(citations: list[dict]) -> bool:
    from app.data.course_knowledge import document_ids

    valid_ids = frozenset(document_ids().values())
    return bool(citations) and all(
        isinstance(item, dict) and item.get('document_id') in valid_ids
        for item in citations
    )


def _ai_trustworthiness(
    bundle: dict,
    knowledge_key: str,
    *,
    confidence: float,
    citations: list[dict] | None,
    step1: StepResult,
) -> tuple[int, list]:
    score = 100
    notes: list[str] = []
    risks = validate_bundle_risks(bundle)
    if risks:
        score -= min(40, 10 * len(risks))
        notes.append(f'结构风险：{", ".join(risks)}')
    if confidence < 0.55:
        score -= 12
        notes.append(f'置信度偏低 {confidence:.0%}')
    elif confidence < 0.7:
        score -= 5
        notes.append(f'置信度一般 {confidence:.0%}')
    if citations is not None:
        if not citations:
            score -= 8
            notes.append('缺少引用')
        elif not _citations_are_valid(citations):
            score -= 10
            notes.append('引用待核对')
        elif any(c.get('section') != knowledge_key for c in citations):
            score -= 5
            notes.append('引用章节不匹配')
    rag_checks = [c for c in step1.checks if c.id == 'rag_consistency']
    if rag_checks and rag_checks[0].level == 'WARNING':
        score -= 5
        notes.append('RAG 一致性弱')
    if any(c.id == 'fantasy_api' and c.level == 'FAIL' for c in step1.checks):
        score -= 25
        notes.append('检测到课程外 API')
    return max(0, min(100, score)), notes


def build_report(
    bundle: dict,
    knowledge_key: str,
    steps: list[StepResult],
    *,
    confidence: float = 0.9,
    citations: list[dict] | None = None,
    backend: str = 'sequential',
) -> AuditReport:
    step1 = steps[0] if steps else StepResult(1, '知识正确性')
    ai_score, ai_notes = _ai_trustworthiness(
        bundle, knowledge_key, confidence=confidence, citations=citations, step1=step1
    )
    dimensions = DimensionScores(
        knowledge_accuracy=steps[0].score if len(steps) > 0 else 100,
        teaching_quality=steps[1].score if len(steps) > 1 else 100,
        case_quality=steps[2].score if len(steps) > 2 else 100,
        exercise_quality=steps[3].score if len(steps) > 3 else 100,
        code_quality=steps[4].score if len(steps) > 4 else 100,
        ai_trustworthiness=ai_score,
    )

    hard_fail_markers = ('fantasy', 'unsafe', 'hallucin', 'injection', 'safety')
    hard_fails = [
        check
        for step in steps
        for check in (step.checks or [])
        if check.level == 'FAIL' and any(m in str(check.id).lower() for m in hard_fail_markers)
    ]
    soft_fails = [
        check
        for step in steps
        for check in (step.checks or [])
        if check.level == 'FAIL' and check not in hard_fails
    ]
    has_warning = any(step.has_warning for step in steps) or bool(soft_fails)
    min_dim = dimensions.min_score()

    verdict: Verdict
    # 仅安全/幻觉等硬 FAIL 才 REJECT；结构/题量/编译等软问题降为 NEED_MODIFY，便于自动通过链路
    if hard_fails:
        verdict = 'REJECT'
        summary = '存在安全或严重知识错误，建议驳回或大幅修改后再审'
    elif has_warning or min_dim < 55:
        verdict = 'NEED_MODIFY'
        summary = '存在提示项或低分维度，可先发布预习并由教师抽检'
    else:
        verdict = 'PASS'
        summary = '六步审核通过，可作为发布参考（仍需教师确认）'

    step6 = StepResult(
        step=6,
        name='审核报告',
        checks=[],
        score=min_dim,
        summary=summary,
    )
    all_steps = steps + [step6]

    return AuditReport(
        verdict=verdict,
        suggested_publish=verdict == 'PASS',
        summary=summary,
        steps=all_steps,
        dimensions=dimensions,
        knowledge_key=knowledge_key,
        backend=backend,
        metadata={
            'ai_trust_notes': ai_notes,
            'min_dimension_score': min_dim,
        },
    )
