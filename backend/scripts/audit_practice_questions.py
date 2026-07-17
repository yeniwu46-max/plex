"""Audit and migrate embedded test data out of coding question stems."""
from __future__ import annotations

from app import create_app
from app.models import TrialQuestion, db
from app.services.practice_question import PracticeQuestionService


def audit_and_migrate(dry_run: bool = True) -> dict:
    app = create_app()
    with app.app_context():
        rows = (
            TrialQuestion.query.filter(TrialQuestion.question_type == 'coding')
            .order_by(TrialQuestion.id.asc())
            .all()
        )
        updated = 0
        scanned = 0
        for row in rows:
            scanned += 1
            meta = row.coding_meta()
            stem = row.stem or ''
            test_cases = meta.get('test_cases') or []
            examples = meta.get('examples') or []
            clean_stem, merged_examples, merged_tests = PracticeQuestionService._normalize_question_payload(
                stem, examples, test_cases
            )
            changed = clean_stem != stem or merged_tests != test_cases or merged_examples != examples
            if not changed:
                continue
            updated += 1
            if dry_run:
                continue
            row.stem = clean_stem
            meta['test_cases'] = merged_tests
            meta['examples'] = merged_examples
            row.set_coding_meta(meta)
        if not dry_run:
            db.session.commit()
        return {'scanned': scanned, 'updated': updated, 'dry_run': dry_run}


if __name__ == '__main__':
    report = audit_and_migrate(dry_run=False)
    print(report)
