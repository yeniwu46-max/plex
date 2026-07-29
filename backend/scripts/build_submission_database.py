"""Copy pre-seeded SQLite demo database into submission data samples."""
from __future__ import annotations

import argparse
import shutil
import sqlite3
from pathlib import Path

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
        users = conn.execute("SELECT count(*) FROM users").fetchone()[0]
        trials = conn.execute("SELECT count(*) FROM trials").fetchone()[0]
        classes = conn.execute("SELECT count(*) FROM classes").fetchone()[0]
        profiles = conn.execute("SELECT count(*) FROM student_profiles").fetchone()[0]
        resources = conn.execute("SELECT count(*) FROM learning_resources").fetchone()[0]
    finally:
        conn.close()
    return {
        "tables": tables,
        "users": users,
        "trials": trials,
        "classes": classes,
        "profiles": profiles,
        "resources": resources,
        "bytes": path.stat().st_size,
    }


def build(output_db: Path | None = None) -> dict:
    target = output_db or OUTPUT_DB
    if not SOURCE_DB.exists():
        raise FileNotFoundError(
            f"Source database not found: {SOURCE_DB}. "
            "Run start.bat --check in the repo first to create demo data."
        )

    stats = _stats(SOURCE_DB)
    if stats["tables"] < MIN_TABLES or stats["users"] < MIN_USERS:
        raise RuntimeError(
            f"Source database looks empty (tables={stats['tables']}, users={stats['users']}). "
            "Seed demo data before building submission package."
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_DB, target)

    readme = target.parent / "README.md"
    readme.write_text(
        f"""# 预置演示数据库

**文件**：`learning_system.db`（SQLite）  
**大小**：{stats['bytes'] / (1024 * 1024):.2f} MB  

## 数据概览（打包时快照）

| 指标 | 数量 |
|---|---|
| 数据表 | {stats['tables']} |
| 用户 | {stats['users']} |
| 班级 | {stats['classes']} |
| 试炼 | {stats['trials']} |
| 学生画像 | {stats['profiles']} |
| 学习资源 | {stats['resources']} |

## 演示账号

| 角色 | 用户名 | 密码 |
|---|---|---|
| 管理员 | admin | admin123 |
| 教师 | teacher001 | teacher123 |
| 学生 | student001 | student123 |
| 学生演示 | explorer01 ~ explorer10 | student123 |

## 运行时路径

一键启动时会自动复制到：

`source/backend/instance/learning_system.db`

与 `backend.env.production-ready` 中的 `DATABASE_URL=sqlite:///instance/learning_system.db` 对应。
""",
        encoding="utf-8",
    )

    return {
        "source": str(SOURCE_DB.resolve()),
        "output": str(target.resolve()),
        "stats": stats,
        "size_mb": round(stats["bytes"] / (1024 * 1024), 2),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_DB)
    args = parser.parse_args()
    import json
    print(json.dumps(build(args.output), ensure_ascii=False, indent=2))
