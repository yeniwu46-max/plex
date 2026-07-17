"""Public entry for six-step resource audit."""
from __future__ import annotations

from typing import Any

from .graph import run_audit_graph
from .schema import AuditReport


class ResourceAuditService:
    @staticmethod
    def audit_bundle(
        bundle: dict,
        knowledge_key: str,
        profile: dict | None = None,
        *,
        confidence: float = 0.9,
        citations: list[dict] | None = None,
    ) -> AuditReport:
        if not isinstance(bundle, dict) or bundle.get('format') != 'pedagogical_v2':
            bundle = dict(bundle or {})
            bundle.setdefault('format', 'pedagogical_v2')
        return run_audit_graph({
            'bundle': bundle,
            'knowledge_key': knowledge_key,
            'profile': profile or {},
            'confidence': confidence,
            'citations': citations,
        })

    @staticmethod
    def audit_from_resource_content(
        content: dict,
        knowledge_key: str,
        profile: dict | None = None,
        *,
        confidence: float = 0.9,
        citations: list[dict] | None = None,
    ) -> AuditReport | None:
        if not isinstance(content, dict):
            return None
        if content.get('format') == 'pedagogical_v2':
            return ResourceAuditService.audit_bundle(
                content, knowledge_key, profile, confidence=confidence, citations=citations
            )
        if content.get('resource_type') == 'learning_bundle' and isinstance(content.get('content'), dict):
            inner = content['content']
            if inner.get('format') == 'pedagogical_v2':
                return ResourceAuditService.audit_bundle(
                    inner, knowledge_key, profile, confidence=confidence, citations=citations
                )
        return None

    @staticmethod
    def enrich_with_crewai_notes(report: AuditReport, bundle: dict, knowledge_key: str) -> AuditReport:
        """Optional natural-language commentary; does not change verdict."""
        try:
            from agents.resource_review_agent import append_review_notes

            notes = append_review_notes(bundle, knowledge_key, report.to_dict())
            if notes:
                metadata = dict(report.metadata or {})
                metadata['crewai_notes'] = notes
                report.metadata = metadata
        except Exception:
            pass
        return report
