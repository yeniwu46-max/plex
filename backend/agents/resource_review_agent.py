# -*- coding: utf-8 -*-
"""Optional CrewAI commentary for resource audit (does not change verdict)."""
from __future__ import annotations

import os
from typing import Any


def append_review_notes(bundle: dict, knowledge_key: str, audit_report: dict) -> str | None:
    backend = os.getenv('AGENT_BACKEND', 'auto').lower()
    if backend not in ('crewai', 'auto'):
        return None
    if not os.getenv('OPENAI_API_KEY', '').strip():
        return _local_notes(bundle, knowledge_key, audit_report)
    try:
        from agents.crew import backend_name

        if backend_name() != 'crewai':
            return _local_notes(bundle, knowledge_key, audit_report)
    except Exception:
        return _local_notes(bundle, knowledge_key, audit_report)
    return _local_notes(bundle, knowledge_key, audit_report)


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
