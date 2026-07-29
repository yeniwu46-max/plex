"""Build PLEX A3 competition submission archive (<= 1 GB compressed).

Organizes runnable multi-agent source, datasets, config samples, docs and reports
into a standard directory layout, then creates a zip archive.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent

EXCLUDED_PARTS = {
    ".agents",
    ".codex",
    ".git",
    ".npm-cache",
    ".codegraph",
    ".cursor",
    ".playwright-cli",
    ".playwright-mcp",
    ".turix",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "dist",
    "instance",
    "uploads",
    "outputs",
    "output",
    "test-results",
}
EXCLUDED_PREFIXES = (".venv",)
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".log"}
SECRET_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.spark.local",
    "credentials.json",
}
MAX_COMPRESSED_BYTES = 1024 * 1024 * 1024  # 1 GB

SOURCE_ROOT_FILES = (
    "README.md",
    "start.bat",
    "TECH_PLAN.md",
    "backend_api_design.md",
    "frontend_design_v2.md",
    "技术选型与约定.md",
    "AGENTS.md",
    ".gitignore",
    ".github",
)

SOURCE_DIRS = ("backend", "frontend", "picture", "ppplex")

DATA_PATHS = (
    "backend/data",
    "data",
)

CONFIG_SAMPLES = (
    ("docs/submission/config-samples/backend.env.submission", "backend.env.submission"),
    ("docs/submission/config-samples/backend.env.production-ready", "backend.env.production-ready"),
    ("docs/submission/config-samples/api-keys.spark.local", "api-keys.spark.local"),
    ("docs/submission/config-samples/API-接入说明.md", "API-接入说明.md"),
    ("backend/.env.example", "backend.env.example"),
    ("frontend/.env.development", "frontend.env.development"),
    ("frontend/.env.example", "frontend.env.example"),
)

DOCS_PATH = "docs/submission"

REPORT_PATHS = (
    "backend/reports",
    "frontend/reports",
)


def _git_value(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return None


def _include(path: Path) -> bool:
    relative = path.relative_to(REPO_ROOT)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if any(part.startswith(EXCLUDED_PREFIXES) for part in relative.parts):
        return False
    if path.name in SECRET_NAMES:
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def _to_crlf(path: Path) -> None:
    """Windows batch labels require CRLF line endings."""
    if path.suffix.lower() != ".bat":
        return
    text = path.read_text(encoding="utf-8")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
    path.write_bytes(normalized.encode("utf-8"))


def _copy_tree(src: Path, dst: Path) -> tuple[int, int]:
    """Copy included files under src into dst; return (file_count, total_bytes)."""
    count = 0
    total = 0
    if not src.exists():
        return count, total
    if src.is_file():
        if _include(src):
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            _to_crlf(dst)
            size = dst.stat().st_size
            return 1, size
        return count, total
    for path in sorted(src.rglob("*")):
        if not path.is_file() or not _include(path):
            continue
        rel = path.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        _to_crlf(target)
        count += 1
        total += target.stat().st_size
    return count, total


def _write_launcher(dest: Path) -> None:
    bat = dest / "一键启动.bat"
    bat.write_bytes(
        """@echo off
setlocal EnableExtensions
chcp 65001 >nul

cd /d "%~dp0"
set "PACKAGE_ROOT=%CD%"
set "SOURCE=%PACKAGE_ROOT%\\source"
set "NO_PROXY=127.0.0.1,localhost,::1"
set "no_proxy=127.0.0.1,localhost,::1"

echo ========================================
echo PLEX A3 提交包 - 一键启动
echo ========================================

if not exist "%SOURCE%\\start.bat" (
    echo [ERROR] 未找到 source\\start.bat，请确认已完整解压提交包。
    pause
    exit /b 1
)

call :ensure_config
if errorlevel 1 exit /b 1

echo.
echo 正在启动 PLEX Universe（后端 + 预构建前端）...
if exist "%PACKAGE_ROOT%\\runtime\\frontend-dist\\index.html" (
    echo [模式] 预构建前端 + Python /api 反代（无需 npm install）
)
echo 启动完成后浏览器访问: http://localhost:5180
echo 演示账号见 source\\README.md
echo 仅检查环境不启动服务: 一键启动.bat --check
echo.

cd /d "%SOURCE%"
set "PLEX_PACKAGE_ROOT=%PACKAGE_ROOT%"
call start.bat %*
set "EXIT_CODE=%ERRORLEVEL%"
cd /d "%PACKAGE_ROOT%"
exit /b %EXIT_CODE%

:ensure_config
if exist "%PACKAGE_ROOT%\\config-samples\\backend.env.production-ready" goto :apply_production_env
if not exist "%PACKAGE_ROOT%\\config-samples\\backend.env.submission" goto :ensure_config_fallback
if not exist "%SOURCE%\\backend\\.env" goto :copy_submission_env
findstr /C:"mysql+pymysql" "%SOURCE%\\backend\\.env" >nul 2>&1
if not errorlevel 1 goto :copy_submission_env
findstr /C:"AGENT_BACKEND=local_rules" "%SOURCE%\\backend\\.env" >nul 2>&1
if not errorlevel 1 goto :copy_submission_env
goto :ensure_config_spark

:apply_production_env
echo [配置] 注入 API 接入配置（AGENT_BACKEND=auto + 讯飞/DeepSeek 凭证）
copy /Y "%PACKAGE_ROOT%\\config-samples\\backend.env.production-ready" "%SOURCE%\\backend\\.env" >nul
goto :ensure_config_spark

:copy_submission_env
echo [配置] 使用 SQLite + API 模板配置
copy /Y "%PACKAGE_ROOT%\\config-samples\\backend.env.submission" "%SOURCE%\\backend\\.env" >nul
goto :ensure_config_spark

:ensure_config_spark
if exist "%PACKAGE_ROOT%\\config-samples\\api-keys.spark.local" (
    echo [配置] 注入讯飞 Spark / 星辰 Agent 凭证
    copy /Y "%PACKAGE_ROOT%\\config-samples\\api-keys.spark.local" "%SOURCE%\\backend\\.env.spark.local" >nul
)
goto :ensure_config_database

:ensure_config_database
if not exist "%PACKAGE_ROOT%\\data\\database\\learning_system.db" goto :ensure_config_fallback
if not exist "%SOURCE%\\backend\\instance" mkdir "%SOURCE%\\backend\\instance"
echo [配置] 注入预置演示数据库（用户/班级/试炼/画像）
copy /Y "%PACKAGE_ROOT%\\data\\database\\learning_system.db" "%SOURCE%\\backend\\instance\\learning_system.db" >nul
goto :ensure_config_frontend

:ensure_config_fallback
if not exist "%SOURCE%\\backend\\.env" (
    if exist "%PACKAGE_ROOT%\\config-samples\\backend.env.example" (
        echo [WARN] 未找到 submission 配置，回退到 backend.env.example
        copy /Y "%PACKAGE_ROOT%\\config-samples\\backend.env.example" "%SOURCE%\\backend\\.env" >nul
    ) else (
        echo [WARN] 未找到 backend 配置样例，将使用后端内置 SQLite 默认值。
    )
)

:ensure_config_frontend
if not exist "%SOURCE%\\frontend\\.env.development" (
    if exist "%PACKAGE_ROOT%\\config-samples\\frontend.env.development" (
        echo [配置] 首次运行：复制 frontend 开发环境配置
        copy /Y "%PACKAGE_ROOT%\\config-samples\\frontend.env.development" "%SOURCE%\\frontend\\.env.development" >nul
    )
)
exit /b 0
""".replace("\n", "\r\n").encode("utf-8")
    )

    sh = dest / "start.sh"
    sh.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
PACKAGE_ROOT="$(cd "$(dirname "$0")" && pwd)"
SOURCE="$PACKAGE_ROOT/source"

echo "========================================"
echo "PLEX A3 提交包 - 一键启动"
echo "========================================"

if [[ ! -f "$SOURCE/start.bat" && ! -f "$SOURCE/backend/run.py" ]]; then
  echo "[ERROR] 未找到 source 目录，请确认已完整解压提交包。"
  exit 1
fi

if [[ ! -f "$SOURCE/backend/.env" && -f "$PACKAGE_ROOT/config-samples/backend.env.example" ]]; then
  echo "[配置] 首次运行：复制 backend.env.example -> source/backend/.env"
  cp "$PACKAGE_ROOT/config-samples/backend.env.example" "$SOURCE/backend/.env"
fi
if [[ ! -f "$SOURCE/frontend/.env.development" && -f "$PACKAGE_ROOT/config-samples/frontend.env.development" ]]; then
  echo "[配置] 首次运行：复制 frontend 开发环境配置"
  cp "$PACKAGE_ROOT/config-samples/frontend.env.development" "$SOURCE/frontend/.env.development"
fi

echo
echo "Linux/macOS 请手动启动："
echo "  终端1: cd source/backend && python3 -m venv .venv && source .venv/bin/activate"
echo "         pip install -r requirements.txt -r requirements-agents.txt"
echo "         python manage.py init && python run.py"
echo "  终端2: cd source/frontend && npm ci && npm run dev"
echo "浏览器访问: http://localhost:5180"
""",
        encoding="utf-8",
    )


def _write_readme(dest: Path, meta: dict) -> None:
    content = f"""# PLEX A3 多智能体提交包

**生成时间（UTC）**：{meta["generated_at"]}  
**Git 提交**：{meta.get("git_commit") or "unknown"}  
**分支**：{meta.get("git_branch") or "unknown"}  

## 目录说明

| 目录/文件 | 内容 |
|---|---|
| `一键启动.bat` | **Windows 双击即可启动**（自动复制配置样例并启动前后端） |
| `source/` | 可完整运行的项目源码（Flask 后端 + Vue 3 前端 + 多智能体模块） |
| `data/` | 课程知识库、**预置 SQLite 演示库**、Learning Core SQL |
| `runtime/` | 预构建前端 dist、CrewAI 离线 wheel、Neo4j compose |
| `data/database/` | 预置 `learning_system.db`（用户/班级/试炼/画像，一键启动自动注入） |
| `config-samples/` | 环境变量与模型部署配置样例（不含真实密钥） |
| `docs/` | 初赛配套文档（需求、设计、多智能体、测试、部署等） |
| `reports/` | 本地评测、安全、性能与 bundle 报告 |
| `release-manifest.json` | 候选文件 SHA-256 清单 |

## 快速运行（Windows）

解压后**双击 `一键启动.bat`**，或在命令行执行：

```bat
一键启动.bat
```

仅检查环境、不启动服务：

```bat
一键启动.bat --check
```

浏览器访问 `http://localhost:5180`。默认演示账号见 `source/README.md`。

## 手动运行

```bash
cd source/backend
pip install -r requirements.txt
pip install -r requirements-agents.txt
python manage.py init
python run.py
```

另开终端：

```bash
cd source/frontend
npm ci
npm run dev
```

## 多智能体相关入口

- 智能体实现：`source/backend/agents/`
- 编排服务：`source/backend/app/services/agent_orchestrator.py`
- 资源审核：`source/backend/app/services/resource_audit/`
- 课程知识库：`data/backend/data/rag_docs/`
- 模型配置样例：`config-samples/backend.env.example`

## 体积说明

- 未压缩文件数：{meta["file_count"]}
- 未压缩总大小：{meta["uncompressed_mb"]:.2f} MB
- 压缩包大小：{meta["compressed_mb"]:.2f} MB（上限 1024 MB）

## 排除项

已排除虚拟环境、`node_modules`、`.env` 真实密钥、数据库文件、日志与开发工具缓存。
"""
    (dest / "README.md").write_text(content, encoding="utf-8")


def build(output_zip: Path, staging_root: Path | None = None) -> dict:
    package_name = "PLEX-A3-submission"
    staging = staging_root or (output_zip.parent / package_name)
    if staging.exists():
        try:
            shutil.rmtree(staging)
        except PermissionError:
            staging = output_zip.parent / f"{package_name}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    staging.mkdir(parents=True, exist_ok=True)

    stats = {"file_count": 0, "total_bytes": 0}

    def add(path: Path, dest: Path) -> None:
        nonlocal stats
        c, b = _copy_tree(path, dest)
        stats["file_count"] += c
        stats["total_bytes"] += b

    source = staging / "source"
    for name in SOURCE_ROOT_FILES:
        add(REPO_ROOT / name, source / name)
    for name in SOURCE_DIRS:
        add(REPO_ROOT / name, source / name)

    data = staging / "data"
    for rel in DATA_PATHS:
        add(REPO_ROOT / rel, data / rel)

    api_meta: dict = {}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "build_submission_env",
            BACKEND_ROOT / "scripts/build_submission_env.py",
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        api_meta = module.build(REPO_ROOT / "docs/submission/config-samples")
    except Exception as exc:
        api_meta = {"error": str(exc)}

    db_meta: dict = {}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "build_submission_database",
            BACKEND_ROOT / "scripts/build_submission_database.py",
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        db_meta = module.build()
        db_src = Path(db_meta["output"])
        db_dir = staging / "data" / "database"
        db_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(db_src, db_dir / "learning_system.db")
        readme = db_src.parent / "README.md"
        if readme.exists():
            shutil.copy2(readme, db_dir / "README.md")
        stats["file_count"] += 1 + int(readme.exists())
        stats["total_bytes"] += db_src.stat().st_size
        if readme.exists():
            stats["total_bytes"] += readme.stat().st_size
    except Exception as exc:
        db_meta = {"error": str(exc)}

    runtime_meta: dict = {}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "build_submission_runtime",
            BACKEND_ROOT / "scripts/build_submission_runtime.py",
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        runtime_src = REPO_ROOT / "docs/submission/runtime-samples"
        if not (runtime_src / "frontend-dist" / "index.html").exists():
            runtime_meta = module.build(skip_wheels=True)
        else:
            runtime_meta = {
                "frontend_dist": {"path": str((runtime_src / "frontend-dist").resolve()), "reused": True},
                "neo4j": module.copy_neo4j_compose(),
            }
            if not (REPORTS_OUT := BACKEND_ROOT / "reports/a3-submission/api-smoke-iflytek.json").exists():
                try:
                    runtime_meta["api_smoke"] = module.run_api_smoke()
                except Exception:
                    pass
        runtime_dst = staging / "runtime"
        if runtime_src.exists():
            if runtime_dst.exists():
                shutil.rmtree(runtime_dst)
            shutil.copytree(runtime_src, runtime_dst)
            for path in runtime_dst.rglob("*"):
                if path.is_file():
                    stats["file_count"] += 1
                    stats["total_bytes"] += path.stat().st_size
        smoke = BACKEND_ROOT / "reports/a3-submission/api-smoke-iflytek.json"
        if smoke.exists():
            reports_dir = staging / "reports" / "a3-submission"
            reports_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(smoke, reports_dir / "api-smoke-iflytek.json")
            stats["file_count"] += 1
            stats["total_bytes"] += smoke.stat().st_size
    except Exception as exc:
        runtime_meta = {"error": str(exc)}

    config_dir = staging / "config-samples"
    for src_rel, dst_name in CONFIG_SAMPLES:
        src = REPO_ROOT / src_rel
        if src.exists() and _include(src):
            config_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, config_dir / dst_name)
            stats["file_count"] += 1
            stats["total_bytes"] += src.stat().st_size

    add(REPO_ROOT / DOCS_PATH, staging / "docs")

    reports = staging / "reports"
    for rel in REPORT_PATHS:
        add(REPO_ROOT / rel, reports / Path(rel).name)

    manifest_src = BACKEND_ROOT / "reports/a3-submission/release-manifest.json"
    if manifest_src.exists():
        shutil.copy2(manifest_src, staging / "release-manifest.json")
        stats["file_count"] += 1
        stats["total_bytes"] += manifest_src.stat().st_size

    _write_launcher(staging)
    stats["file_count"] += 2
    stats["total_bytes"] += sum(
        p.stat().st_size for p in (staging / "一键启动.bat", staging / "start.sh") if p.exists()
    )

    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": _git_value("rev-parse", "HEAD"),
        "git_branch": _git_value("branch", "--show-current"),
        "file_count": stats["file_count"],
        "uncompressed_mb": stats["total_bytes"] / (1024 * 1024),
        "api_integration": api_meta,
        "database": db_meta,
        "runtime": runtime_meta,
    }
    _write_readme(staging, {**meta, "compressed_mb": 0.0})

    output_zip.parent.mkdir(parents=True, exist_ok=True)
    if output_zip.exists():
        output_zip.unlink()

    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                arcname = path.relative_to(staging.parent).as_posix()
                zf.write(path, arcname)

    compressed = output_zip.stat().st_size
    meta["compressed_mb"] = compressed / (1024 * 1024)
    meta["compressed_bytes"] = compressed
    meta["passed_size_limit"] = compressed <= MAX_COMPRESSED_BYTES
    meta["output_zip"] = str(output_zip.resolve())
    meta["staging_dir"] = str(staging.resolve())

    _write_readme(staging, meta)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                arcname = path.relative_to(staging.parent).as_posix()
                zf.write(path, arcname)

    meta_path = staging / "package-meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    with zipfile.ZipFile(output_zip, "a", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(meta_path, f"{package_name}/package-meta.json")

    return meta


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build PLEX A3 submission zip package.")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT.parent / "PLEX-A3-submission.zip",
        help="Output zip path (default: ../PLEX-A3-submission.zip)",
    )
    parser.add_argument(
        "--keep-staging",
        action="store_true",
        help="Keep extracted staging directory after zipping.",
    )
    args = parser.parse_args()

    result = build(args.output.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not args.keep_staging:
        staging = Path(result["staging_dir"])
        if staging.exists():
            shutil.rmtree(staging)

    if not result["passed_size_limit"]:
        print(f"ERROR: compressed size exceeds 1 GB limit.", file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(0)
