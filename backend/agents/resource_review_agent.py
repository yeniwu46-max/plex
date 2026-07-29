# -*- coding: utf-8 -*-
"""资源生成 AI 审核智能体（OpenAI）。

在六步规则审核之后，对资源包做内容异常判定：
- 正常 → 建议自动批准（教师无需逐条处理）
- 异常 → 进入教师端「异常待审」区，并给学生端警示文案
"""
from __future__ import annotations

import json
import os
from typing import Any


SYSTEM_PROMPT = """你是高校 Python 程序设计课程的「资源审核智能体」。
你的职责是审核 AI 生成的个性化学习资源是否适合自动发布给学生。

判定标准：
1. 知识是否明显错误、过时或与课程知识点无关
2. 是否含不当内容（暴力、歧视、色情、作弊诱导、泄露隐私等）
3. 练习/代码是否明显不可用或误导学生
4. 表述是否混乱到会误导初学者

输出必须是 JSON 对象，字段：
- decision: "auto_approve" | "needs_review" | "reject"
- is_anomaly: boolean（内容异常、需教师重点处理时为 true）
- anomaly_codes: string[]（如 factual_error / off_topic / unsafe / low_quality / incomplete）
- confidence: 0~1
- teacher_summary: 给教师的简短中文说明（1~2句）
- student_warning: 给学生的警示说明；仅当 is_anomaly 为 true 时填写，否则为空字符串
- review_reason: 自动批准或驳回时写入审核记录的中文说明

决策指引：
- 内容正常、可学习 → auto_approve，is_anomaly=false
- 有疑点但可先给学生预习 → needs_review，is_anomaly=true，必须给 student_warning
- 明显有害/严重错误 → reject，is_anomaly=true，必须给 student_warning
"""


DEFAULT_STUDENT_WARNING = (
    '本资源由 AI 生成且尚未通过教师最终确认，内容可能存在不准确之处，'
    '请以课堂讲解与教材为准，遇到疑惑及时向老师提问。'
)


def append_review_notes(bundle: dict, knowledge_key: str, audit_report: dict) -> str | None:
    """兼容旧接口：返回简短备注，不改变裁决（完整审核由 review_generated_resource 负责）。"""
    if isinstance(audit_report.get('metadata'), dict):
        existing = audit_report['metadata'].get('ai_agent_review') or {}
        if existing.get('teacher_summary'):
            return str(existing['teacher_summary'])[:400]
    return _local_notes(bundle, knowledge_key, audit_report)


def review_generated_resource(
    *,
    bundle: dict | None,
    knowledge_key: str,
    audit_report: dict | None = None,
    risk_reasons: list[str] | None = None,
    title: str = '',
) -> dict[str, Any]:
    """调用 OpenAI 审核资源；无密钥或失败时回退到规则判定。"""
    audit_report = audit_report or {}
    risk_reasons = list(risk_reasons or [])
    openai_result = _openai_review(
        bundle=bundle or {},
        knowledge_key=knowledge_key,
        audit_report=audit_report,
        risk_reasons=risk_reasons,
        title=title,
    )
    if openai_result:
        return openai_result
    return _rules_fallback(bundle or {}, knowledge_key, audit_report, risk_reasons)


def _openai_review(
    *,
    bundle: dict,
    knowledge_key: str,
    audit_report: dict,
    risk_reasons: list[str],
    title: str,
) -> dict[str, Any] | None:
    from agents.llm_client import chat_json, openai_agent_provider

    provider = openai_agent_provider('quality_reviewer')
    if not provider:
        return None

    excerpt = _bundle_excerpt(bundle)
    user_payload = {
        'knowledge_key': knowledge_key,
        'title': title,
        'six_step_verdict': audit_report.get('verdict'),
        'suggested_publish': audit_report.get('suggested_publish'),
        'dimension_scores': audit_report.get('dimensions') or {},
        'existing_risk_reasons': risk_reasons,
        'resource_excerpt': excerpt,
    }
    raw = chat_json(
        system=SYSTEM_PROMPT,
        user=json.dumps(user_payload, ensure_ascii=False),
        timeout=float(os.getenv('RESOURCE_AI_REVIEW_TIMEOUT', '25') or 25),
        max_tokens=700,
        provider=provider,
        temperature=0.2,
        force_json_object=True,
    )
    if not isinstance(raw, dict):
        return None
    return _normalize_result(raw, backend='openai', audit_report=audit_report, risk_reasons=risk_reasons)


HARD_RISK_CODES = frozenset({
    'safety_blocked',
    'out_of_scope',
    'ai_reject',
})
# 仅安全/越界/严重幻觉类 audit FAIL 算硬异常。
# schema_invalid、audit_syntax、题量类 FAIL 视为软风险，不挡学生立即可见。
HARD_AUDIT_MARKERS = ('fantasy', 'unsafe', 'hallucin', 'injection', 'safety')


def is_hard_risk(code: str) -> bool:
    text = str(code or '').strip()
    if not text:
        return False
    if text in HARD_RISK_CODES:
        return True
    if text.startswith('audit_'):
        body = text[6:].lower()
        return any(marker in body for marker in HARD_AUDIT_MARKERS)
    return False


def _rules_fallback(
    bundle: dict,
    knowledge_key: str,
    audit_report: dict,
    risk_reasons: list[str],
) -> dict[str, Any]:
    verdict = str(audit_report.get('verdict') or 'NEED_MODIFY')
    dims = audit_report.get('dimensions') or {}
    min_dim = min(dims.values()) if dims else 100
    has_hard = any(is_hard_risk(r) for r in risk_reasons)
    # NEED_MODIFY 常见于风格/完备性提示，不应整包拦下；硬风险或 REJECT 才异常。
    soft_ok = (
        verdict in ('PASS', 'NEED_MODIFY')
        and not has_hard
        and min_dim >= 60
    )
    if soft_ok:
        return {
            'decision': 'auto_approve',
            'is_anomaly': False,
            'anomaly_codes': [],
            'confidence': 0.78 if verdict == 'PASS' else 0.72,
            'teacher_summary': _local_notes(bundle, knowledge_key, audit_report),
            'student_warning': '',
            'review_reason': (
                'AI 审核智能体（规则回退）：六步审核通过，内容符合发布标准，已自动批准。'
                if verdict == 'PASS'
                else 'AI 审核智能体（规则回退）：六步建议修订但无硬伤，已自动批准；教师可抽检。'
            ),
            'backend': 'rules_fallback',
        }

    is_reject = verdict == 'REJECT' or 'safety_blocked' in risk_reasons
    codes = list(dict.fromkeys(risk_reasons or (['low_quality'] if verdict != 'PASS' else ['needs_human_check'])))
    warning = DEFAULT_STUDENT_WARNING
    if 'safety_blocked' in risk_reasons:
        warning = '本资源触发了内容安全检查，仅供参考预览，请勿当作正式学习依据，请等待教师处理。'
    return {
        'decision': 'reject' if is_reject else 'needs_review',
        'is_anomaly': True,
        'anomaly_codes': codes[:8],
        'confidence': 0.7,
        'teacher_summary': _local_notes(bundle, knowledge_key, audit_report),
        'student_warning': warning,
        'review_reason': (
            'AI 审核智能体（规则回退）：内容存在异常或未达自动发布标准，已提交教师复核。'
        ),
        'backend': 'rules_fallback',
    }


def _normalize_result(
    raw: dict,
    *,
    backend: str,
    audit_report: dict,
    risk_reasons: list[str],
) -> dict[str, Any]:
    decision = str(raw.get('decision') or '').strip().lower()
    if decision not in {'auto_approve', 'needs_review', 'reject'}:
        decision = 'needs_review'

    # 硬风险不允许 OpenAI 直接自动通过
    hard_blocked = any(is_hard_risk(r) for r in risk_reasons)
    if decision == 'auto_approve' and (
        hard_blocked or audit_report.get('verdict') == 'REJECT'
    ):
        decision = 'needs_review'

    is_anomaly = bool(raw.get('is_anomaly'))
    if decision != 'auto_approve':
        is_anomaly = True

    anomaly_codes = raw.get('anomaly_codes') or []
    if not isinstance(anomaly_codes, list):
        anomaly_codes = [str(anomaly_codes)]
    anomaly_codes = [str(c).strip() for c in anomaly_codes if str(c).strip()][:8]

    try:
        confidence = float(raw.get('confidence', 0.75))
    except (TypeError, ValueError):
        confidence = 0.75
    confidence = max(0.0, min(1.0, confidence))

    teacher_summary = str(raw.get('teacher_summary') or '').strip()[:400]
    student_warning = str(raw.get('student_warning') or '').strip()[:500]
    review_reason = str(raw.get('review_reason') or '').strip()[:500]

    if is_anomaly and not student_warning:
        student_warning = DEFAULT_STUDENT_WARNING
    if not is_anomaly:
        student_warning = ''

    if not review_reason:
        if decision == 'auto_approve':
            review_reason = 'AI 审核智能体：内容正常，已自动批准发布。'
        elif decision == 'reject':
            review_reason = 'AI 审核智能体：内容异常，建议驳回。'
        else:
            review_reason = 'AI 审核智能体：内容存疑，需教师人工复核。'

    if not teacher_summary:
        teacher_summary = review_reason

    return {
        'decision': decision,
        'is_anomaly': is_anomaly,
        'anomaly_codes': anomaly_codes,
        'confidence': round(confidence, 3),
        'teacher_summary': teacher_summary,
        'student_warning': student_warning,
        'review_reason': review_reason,
        'backend': backend,
    }


def _bundle_excerpt(bundle: dict, limit: int = 3500) -> str:
    if not isinstance(bundle, dict):
        return str(bundle)[:limit]
    payload = {
        'node': bundle.get('node') or bundle.get('knowledge_key'),
        'objectives': bundle.get('objectives') or bundle.get('learning_objectives'),
        'concept': (bundle.get('concept') or bundle.get('explanation') or '')[:800],
        'cases': (bundle.get('cases') or [])[:2],
        'exercises': (bundle.get('exercises') or [])[:3],
        'code_lab': bundle.get('code_lab') or bundle.get('coding_lab'),
        'common_mistakes': (bundle.get('common_mistakes') or [])[:3],
    }
    text = json.dumps(payload, ensure_ascii=False, default=str)
    return text[:limit]


def _local_notes(bundle: dict, knowledge_key: str, audit_report: dict) -> str:
    label = str(bundle.get('node') or knowledge_key)
    verdict = audit_report.get('verdict', 'UNKNOWN')
    dims = audit_report.get('dimensions') or {}
    weakest = min(dims.items(), key=lambda item: item[1]) if dims else ('', 100)
    cases = len(bundle.get('cases') or [])
    exercises = len(bundle.get('exercises') or [])
    return (
        f'「{label}」审核建议为 {verdict}。'
        f'案例 {cases} 条、练习 {exercises} 题；'
        f'最弱维度 {weakest[0]}（{weakest[1]} 分）。'
        f'请结合六步报告与课程目标做最终发布判断。'
    )
