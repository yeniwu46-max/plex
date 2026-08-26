# -*- coding: utf-8 -*-
"""额外清理：同知识点下「问候 / Hello / print Hello」近重复题，只留最早一条。"""
import re
import sys

sys.path.insert(0, r'd:\zhongruan\zhongruan\backend')
from app import create_app
from app.models import Problem, db

HELLO_RE = re.compile(r'Hello|PLEX|问候|你好', re.I)


def main():
    app = create_app('development')
    with app.app_context():
        rows = (
            Problem.query.filter(
                Problem.is_active.is_(True),
                Problem.kg_node_id == 'lang-print',
            )
            .order_by(Problem.id.asc())
            .all()
        )
        hello_rows = [
            row for row in rows
            if HELLO_RE.search(row.title_cn or '')
            or HELLO_RE.search(row.description_cn or '')
            or HELLO_RE.search(row.title_en or '')
        ]
        if len(hello_rows) <= 1:
            print(f'hello-like active={len(hello_rows)}, nothing to drop')
            return
        keep = hello_rows[0]
        dropped = []
        for row in hello_rows[1:]:
            row.is_active = False
            note = (row.review_note or '') + f' [dedup:hello_near_dup; keep={keep.problem_no}]'
            row.review_note = note[:500]
            row.needs_review = True
            dropped.append(row.problem_no)
        db.session.commit()
        print(f'kept={keep.problem_no} deactivated={len(dropped)} -> {dropped}')


if __name__ == '__main__':
    main()
