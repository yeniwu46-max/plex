# -*- coding: utf-8 -*-
"""把开发期 SQLite 库的全量数据搬运到 MySQL 主库。

前置条件：MySQL 目标库的表结构已由 `python manage.py init` 建好（本脚本只搬数据，
不建表、不改结构）。搬运按外键依赖排序，并在整个过程中关闭外键检查，避免自引用
表（如 problem_submissions.legacy_prev_solution_id）导致的顺序死锁。

幂等性：每张表搬运前先 DELETE 目标表全部行，再整表重灌，因此可重复执行。
只有 SQLite 里存在的表才会被处理；MySQL 独有的新表原样保留。

用法：
    python scripts/migrate_sqlite_to_mysql.py                 # 使用 .env 的 DATABASE_URL 作目标
    python scripts/migrate_sqlite_to_mysql.py --dry-run       # 只打印行数对照，不写入
    python scripts/migrate_sqlite_to_mysql.py --sqlite path   # 指定源 SQLite 文件
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import create_engine, inspect, text  # noqa: E402

from app.config import Config  # noqa: E402

DEFAULT_SQLITE = BACKEND_ROOT / 'instance' / 'learning_system.db'
BATCH_SIZE = 1000


def sqlite_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return sorted(row[0] for row in rows)


def order_tables(engine, tables: list[str]) -> list[str]:
    """按外键依赖拓扑排序：被依赖的表先搬。环（自引用/互相引用）按字典序兜底。"""
    inspector = inspect(engine)
    known = set(tables)
    deps: dict[str, set[str]] = {}
    for table in tables:
        parents = set()
        for fk in inspector.get_foreign_keys(table):
            parent = fk.get('referred_table')
            if parent and parent in known and parent != table:
                parents.add(parent)
        deps[table] = parents

    ordered: list[str] = []
    remaining = dict(deps)
    while remaining:
        ready = sorted(t for t, parents in remaining.items() if not (parents - set(ordered)))
        if not ready:
            # 存在环，剩余表按字典序处理（外键检查已关闭，不影响写入）
            ready = sorted(remaining)
        for table in ready:
            ordered.append(table)
            remaining.pop(table, None)
    return ordered


def copy_table(sqlite_conn: sqlite3.Connection, mysql_conn, table: str, columns: list[str]) -> int:
    quoted = ', '.join(f'`{col}`' for col in columns)
    placeholders = ', '.join(f':{col}' for col in columns)
    insert_sql = text(f'INSERT INTO `{table}` ({quoted}) VALUES ({placeholders})')

    cursor = sqlite_conn.execute(f'SELECT {", ".join(chr(34) + c + chr(34) for c in columns)} FROM "{table}"')
    total = 0
    while True:
        rows = cursor.fetchmany(BATCH_SIZE)
        if not rows:
            break
        payload = [dict(zip(columns, row)) for row in rows]
        mysql_conn.execute(insert_sql, payload)
        total += len(payload)
    return total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--sqlite', default=str(DEFAULT_SQLITE), help='源 SQLite 文件路径')
    parser.add_argument('--target', default=None, help='目标 MySQL URI，默认取 .env 的 DATABASE_URL')
    parser.add_argument('--dry-run', action='store_true', help='只打印行数对照，不写入')
    args = parser.parse_args()

    sqlite_path = Path(args.sqlite)
    if not sqlite_path.exists():
        raise SystemExit(f'源 SQLite 文件不存在: {sqlite_path}')

    target_uri = args.target or Config.SQLALCHEMY_DATABASE_URI
    if target_uri.startswith('sqlite'):
        raise SystemExit(f'目标仍指向 SQLite，请先在 .env 中把 DATABASE_URL 改为 MySQL：{target_uri}')

    engine = create_engine(target_uri, future=True)
    sqlite_conn = sqlite3.connect(str(sqlite_path))
    sqlite_conn.text_factory = bytes_or_str

    src_tables = sqlite_tables(sqlite_conn)
    dst_tables = set(inspect(engine).get_table_names())
    shared = [t for t in src_tables if t in dst_tables and t != 'alembic_version']
    skipped_src = [t for t in src_tables if t not in dst_tables]
    mysql_only = sorted(dst_tables - set(src_tables) - {'alembic_version'})

    ordered = order_tables(engine, shared)
    print(f'源表 {len(src_tables)} / 目标表 {len(dst_tables)} / 待搬运 {len(ordered)}')
    if skipped_src:
        print(f'  跳过（目标库无此表）: {skipped_src}')
    if mysql_only:
        print(f'  目标库独有（保留不动）: {mysql_only}')

    results: list[tuple[str, int, int]] = []
    with engine.begin() as mysql_conn:
        mysql_conn.execute(text('SET FOREIGN_KEY_CHECKS = 0'))
        for table in ordered:
            columns = [row[1] for row in sqlite_conn.execute(f'PRAGMA table_info("{table}")')]
            dst_columns = {col['name'] for col in inspect(engine).get_columns(table)}
            usable = [c for c in columns if c in dst_columns]
            dropped = [c for c in columns if c not in dst_columns]
            src_count = sqlite_conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]

            if args.dry_run:
                results.append((table, src_count, -1))
                if dropped:
                    print(f'  {table}: 源有目标无的列 {dropped}（将被忽略）')
                continue

            mysql_conn.execute(text(f'DELETE FROM `{table}`'))
            written = copy_table(sqlite_conn, mysql_conn, table, usable) if usable else 0
            results.append((table, src_count, written))
            if dropped:
                print(f'  {table}: 源有目标无的列 {dropped}（已忽略）')
        mysql_conn.execute(text('SET FOREIGN_KEY_CHECKS = 1'))

    # 重新连一次做独立核对，确认数据真正落库（而不是只看事务内计数）
    print()
    print(f'{"表名":<38}{"SQLite":>10}{"MySQL":>10}  结果')
    print('-' * 70)
    mismatched = []
    with engine.connect() as conn:
        for table, src_count, _written in results:
            if args.dry_run:
                print(f'{table:<38}{src_count:>10}{"-":>10}  dry-run')
                continue
            dst_count = conn.execute(text(f'SELECT COUNT(*) FROM `{table}`')).scalar_one()
            ok = dst_count == src_count
            if not ok:
                mismatched.append((table, src_count, dst_count))
            print(f'{table:<38}{src_count:>10}{dst_count:>10}  {"OK" if ok else "MISMATCH"}')

    sqlite_conn.close()
    if mismatched:
        raise SystemExit(f'\n行数不一致的表: {mismatched}')
    if not args.dry_run:
        print('\n全部表行数一致，迁移完成。')


def bytes_or_str(raw: bytes):
    """SQLite 里可能混有非 UTF-8 字节（历史脏数据），解码失败时退回替换字符而不是崩溃。"""
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw.decode('utf-8', errors='replace')


if __name__ == '__main__':
    main()
