"""One-off exploration script: prints CREATE TABLE DDL + row counts + samples
for every table of interest in the incoming dump. Read-only, does not write
anything. Run with: python inspect_dump.py [table_name]
"""
from __future__ import annotations

import json
import sys

from _dump_reader import DUMP_PATH, iter_create_table, load_table, read_dump_text

TABLES = ['group', 'user', 'user_info', 'quest', 'problem', 'player', 'quest_problem', 'solution', 'gen_hint']


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    print(f'dump: {DUMP_PATH}')
    text = read_dump_text()
    print(f'dump length: {len(text)} chars')
    for table in TABLES:
        if only and table != only:
            continue
        ddl = iter_create_table(text, table)
        print('=' * 100)
        print(f'TABLE `{table}`')
        print('-' * 100)
        print(ddl)
        rows = load_table(text, table)
        print(f'row count parsed: {len(rows)}')
        for row in rows[:3]:
            print(json.dumps(row, ensure_ascii=False, default=str)[:2000])


if __name__ == '__main__':
    main()
