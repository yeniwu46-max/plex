"""Build a portable SQLite snapshot from the database used by the local app."""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import MetaData, Table, create_engine, inspect, select, text


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
SOURCE_DB = BACKEND_ROOT / "instance/learning_system.db"
OUTPUT_DIR = REPO_ROOT / "docs/submission/data-samples/database"
OUTPUT_DB = OUTPUT_DIR / "learning_system.db"

MIN_USERS = 3
MIN_TABLES = 20


def _stats(path: Path) -> dict:
    conn = sqlite3.connect(path)
    try:
        tables = conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]

        def count(table: str) -> int:
            present = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            return conn.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0] if present else 0

        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        return {
            "tables": tables,
            "users": count("users"),
            "trials": count("trials"),
            "classes": count("classes"),
            "profiles": count("student_profiles"),
            "problems": count("problems"),
            "submissions": count("problem_submissions"),
            "resources": count("learning_resources"),
            "integrity": integrity,
            "bytes": path.stat().st_size,
        }
    finally:
        conn.close()


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


def _create_empty_sqlite(path: Path) -> None:
    if path.exists():
        path.unlink()
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": _sqlite_url(path),
            "FLASK_ENV": "development",
            "FLASK_DEBUG": "0",
        }
    )
    subprocess.run(
        [sys.executable, str(BACKEND_ROOT / "manage.py"), "init"],
        cwd=str(BACKEND_ROOT),
        env=env,
        check=True,
        timeout=300,
    )


def _copy_database(source_url: str, target: Path) -> dict[str, int]:
    """Copy all shared application tables while keeping the target migration head."""
    source_engine = create_engine(source_url, pool_pre_ping=True)
    target_engine = create_engine(_sqlite_url(target))
    copied: dict[str, int] = {}
    try:
        source_tables = set(inspect(source_engine).get_table_names())
        target_tables = set(inspect(target_engine).get_table_names())
        with source_engine.connect() as source_conn, target_engine.connect() as target_conn:
            target_conn.execute(text("PRAGMA foreign_keys=OFF"))
            for name in sorted(target_tables):
                if name in {"alembic_version", "sqlite_sequence"} or name not in source_tables:
                    continue
                source_table = Table(name, MetaData(), autoload_with=source_engine)
                target_table = Table(name, MetaData(), autoload_with=target_engine)
                columns = [column.name for column in target_table.columns if column.name in source_table.c]
                if not columns:
                    continue

                target_conn.execute(target_table.delete())
                result = source_conn.execution_options(stream_results=True).execute(
                    select(*(source_table.c[column] for column in columns))
                ).mappings()
                batch: list[dict] = []
                total = 0
                for row in result:
                    batch.append({column: row[column] for column in columns})
                    if len(batch) >= 500:
                        target_conn.execute(target_table.insert(), batch)
                        total += len(batch)
                        batch.clear()
                if batch:
                    target_conn.execute(target_table.insert(), batch)
                    total += len(batch)
                target_conn.commit()
                copied[name] = total
            target_conn.execute(text("PRAGMA foreign_keys=ON"))
            target_conn.commit()
    finally:
        source_engine.dispose()
        target_engine.dispose()
    return copied


def _active_database_url() -> str | None:
    raw = dotenv_values(BACKEND_ROOT / ".env").get("DATABASE_URL")
    return str(raw).strip() if raw else None


def build(output_db: Path | None = None) -> dict:
    target = (output_db or OUTPUT_DB).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    building = target.with_name(f"{target.stem}.building{target.suffix}")
    if building.exists():
        building.unlink()

    source_url = _active_database_url()
    source_kind = "sqlite-fallback"
    copied_tables: dict[str, int] = {}

    try:
        if source_url and not source_url.startswith("sqlite:"):
            source_kind = source_url.split(":", 1)[0]
            _create_empty_sqlite(building)
            copied_tables = _copy_database(source_url, building)
        else:
            source_path = SOURCE_DB
            if source_url and source_url.startswith("sqlite:///"):
                raw = source_url[len("sqlite:///") :]
                candidate = Path(raw)
                source_path = candidate if candidate.is_absolute() else BACKEND_ROOT / candidate
            if not source_path.exists():
                raise FileNotFoundError(
                    f"Source database not found: {source_path}. Run start.bat --check first."
                )
            shutil.copy2(source_path, building)

        stats = _stats(building)
        if stats["integrity"] != "ok":
            raise RuntimeError(f"SQLite snapshot integrity check failed: {stats['integrity']}")
        if stats["tables"] < MIN_TABLES or stats["users"] < MIN_USERS:
            raise RuntimeError(
                f"Database snapshot looks empty (tables={stats['tables']}, users={stats['users']})."
            )
        os.replace(building, target)
    finally:
        if building.exists():
            building.unlink()

    readme = target.parent / "README.md"
    readme.write_text(
        f"""# 预置可运行数据库快照

**文件**：`learning_system.db`（SQLite）  
**来源**：打包时本地正在使用的 `{source_kind}` 数据库
**大小**：{stats['bytes'] / (1024 * 1024):.2f} MB  
**完整性检查**：`{stats['integrity']}`

## 数据概览（打包时快照）

| 指标 | 数量 |
|---|---:|
| 数据表 | {stats['tables']} |
| 用户 | {stats['users']} |
| 班级 | {stats['classes']} |
| 试炼 | {stats['trials']} |
| 学生画像 | {stats['profiles']} |
| 题目 | {stats['problems']} |
| 题目提交 | {stats['submissions']} |
| 学习资源 | {stats['resources']} |

## 演示账号

| 角色 | 用户名 | 密码 |
|---|---|---|
| 管理员 | admin | admin123 |
| 教师 | teacher001 | teacher123 |
| 学生 | student001 | student123 |
| 学生演示 | explorer01 ~ explorer10 | student123 |

首次一键启动时会复制到 `source/backend/instance/learning_system.db`；后续启动不会覆盖，使用过程中新增的数据会被保留。
""",
        encoding="utf-8",
    )

    return {
        "output": str(target),
        "source_kind": source_kind,
        "copied_table_count": len(copied_tables),
        "copied_rows": sum(copied_tables.values()),
        "stats": stats,
        "size_mb": round(stats["bytes"] / (1024 * 1024), 2),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_DB)
    args = parser.parse_args()
    import json

    print(json.dumps(build(args.output), ensure_ascii=False, indent=2))
