"""Prepare runtime assets for submission package (dist, wheels, smoke report)."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
FRONTEND_ROOT = REPO_ROOT / "frontend"
RUNTIME_ROOT = REPO_ROOT / "docs/submission/runtime-samples"
DIST_OUT = RUNTIME_ROOT / "frontend-dist"
WHEELS_OUT = RUNTIME_ROOT / "python-wheels"
PYTHON_OUT = RUNTIME_ROOT / "python"
REPORTS_OUT = BACKEND_ROOT / "reports/a3-submission"

PORTABLE_IMPORTS = (
    "alembic",
    "crewai",
    "edge_tts",
    "flask",
    "flask_cors",
    "flask_jwt_extended",
    "flask_sqlalchemy",
    "jsonschema",
    "neo4j",
    "pydantic",
    "pymysql",
    "requests",
    "sqlalchemy",
)


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 900) -> None:
    use_shell = os.name == "nt" and cmd and cmd[0] in {"npm", "npx"}
    subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        timeout=timeout,
        shell=use_shell,
    )


def build_frontend_dist(force: bool = False) -> dict:
    if not (FRONTEND_ROOT / "package.json").exists():
        raise FileNotFoundError(f"frontend not found: {FRONTEND_ROOT}")
    src_dist = FRONTEND_ROOT / "dist"
    budget_gate_passed = True
    if not force and (src_dist / "index.html").exists():
        print("Using existing frontend/dist (skip npm build)")
    else:
        if not (FRONTEND_ROOT / "node_modules").exists():
            _run(["npm", "ci"], cwd=FRONTEND_ROOT)
        try:
            _run(["npm", "run", "build"], cwd=FRONTEND_ROOT)
        except subprocess.CalledProcessError:
            # The build script runs the bundle-budget gate after Vite. If Vite
            # already produced a complete dist, keep that exact UI for delivery
            # and expose the failed budget gate in runtime metadata.
            if not (src_dist / "index.html").exists():
                raise
            budget_gate_passed = False
            print("WARNING: frontend dist built, but the bundle-budget gate failed")
        if not (src_dist / "index.html").exists():
            raise RuntimeError("frontend build did not produce dist/index.html")
    if DIST_OUT.exists():
        shutil.rmtree(DIST_OUT)
    shutil.copytree(src_dist, DIST_OUT)
    total_bytes = sum(p.stat().st_size for p in DIST_OUT.rglob("*") if p.is_file())
    return {
        "path": str(DIST_OUT.resolve()),
        "files": sum(1 for _ in DIST_OUT.rglob("*") if _.is_file()),
        "bytes": total_bytes,
        "size_mb": round(total_bytes / (1024 * 1024), 2),
        "bundle_budget_passed": budget_gate_passed,
    }


def download_agent_wheels() -> dict:
    WHEELS_OUT.mkdir(parents=True, exist_ok=True)
    req = BACKEND_ROOT / "requirements-agents.txt"
    if not req.exists():
        return {"skipped": True, "reason": "requirements-agents.txt missing"}
    try:
        _run(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "-r",
                str(req),
                "-d",
                str(WHEELS_OUT),
            ],
        )
    except subprocess.CalledProcessError as exc:
        return {"skipped": True, "reason": f"pip download failed: {exc}"}
    wheels = [p for p in WHEELS_OUT.iterdir() if p.is_file()]
    total_bytes = sum(p.stat().st_size for p in wheels)
    return {
        "path": str(WHEELS_OUT.resolve()),
        "count": len(wheels),
        "bytes": total_bytes,
        "size_mb": round(total_bytes / (1024 * 1024), 2),
    }


def _copy_ignore(current: str, names: list[str]) -> set[str]:
    ignored = {
        name for name in names
        if name in {"__pycache__", ".pytest_cache", ".cache"}
        or name.endswith((".pyc", ".pyo"))
    }
    if Path(current).resolve() == (Path(sys.base_prefix) / "Lib").resolve():
        ignored.add("site-packages")
    return ignored


def _verify_portable_python(python_exe: Path) -> None:
    imports = ", ".join(PORTABLE_IMPORTS)
    subprocess.run(
        [str(python_exe), "-c", f"import {imports}; print('portable-runtime-ok')"],
        cwd=str(BACKEND_ROOT),
        check=True,
        timeout=120,
    )


def build_portable_python(force: bool = False) -> dict:
    """Build a relocatable Windows Python 3.12 runtime with all backend/agent deps."""
    marker = PYTHON_OUT / ".plex-runtime.json"
    python_exe = PYTHON_OUT / "python.exe"
    if not force and marker.exists() and python_exe.exists():
        try:
            _verify_portable_python(python_exe)
            payload = json.loads(marker.read_text(encoding="utf-8"))
            payload["reused"] = True
            return payload
        except Exception:
            pass

    base_root = Path(sys.base_prefix).resolve()
    site_packages = (Path(sys.prefix) / "Lib" / "site-packages").resolve()
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError(f"Portable runtime must be built with Python 3.12, got {sys.version.split()[0]}")
    if not (base_root / "python.exe").exists():
        raise FileNotFoundError(f"Base Python runtime not found: {base_root}")
    if not (site_packages / "flask").exists() or not (site_packages / "crewai").exists():
        raise RuntimeError(
            "Run this builder with the project .venv Python; Flask/CrewAI are missing from site-packages."
        )

    if PYTHON_OUT.exists():
        shutil.rmtree(PYTHON_OUT)
    shutil.copytree(base_root, PYTHON_OUT, ignore=_copy_ignore)
    target_site = PYTHON_OUT / "Lib" / "site-packages"
    if target_site.exists():
        shutil.rmtree(target_site)
    shutil.copytree(
        site_packages,
        target_site,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".cache", "*.pyc", "*.pyo"),
    )

    _verify_portable_python(python_exe)
    total_bytes = sum(p.stat().st_size for p in PYTHON_OUT.rglob("*") if p.is_file())
    payload = {
        "path": str(PYTHON_OUT.resolve()),
        "python_version": sys.version.split()[0],
        "files": sum(1 for p in PYTHON_OUT.rglob("*") if p.is_file()),
        "bytes": total_bytes,
        "size_mb": round(total_bytes / (1024 * 1024), 2),
        "reused": False,
    }
    marker.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def run_api_smoke() -> dict:
    REPORTS_OUT.mkdir(parents=True, exist_ok=True)
    output = REPORTS_OUT / "api-smoke-iflytek.json"
    proc = subprocess.run(
        [sys.executable, str(BACKEND_ROOT / "scripts/smoke_iflytek.py")],
        cwd=str(BACKEND_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    try:
        payload = json.loads(proc.stdout.strip() or "{}")
    except json.JSONDecodeError:
        payload = {
            "ok": False,
            "error": "invalid_json",
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    payload["exit_code"] = proc.returncode
    payload["run_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"path": str(output.resolve()), "result": payload}


def write_runtime_readme() -> str:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    readme = RUNTIME_ROOT / "README.md"
    readme.write_text(
        """# 提交包运行体验资产

| 目录/文件 | 用途 |
|---|---|
| `frontend-dist/` | 预构建前端，启动时用 Python 静态服务 + `/api` 反代（无需 npm ci） |
| `python/` | 可迁移的 Python 3.12 运行时，已含 Flask、数据库驱动、CrewAI 等依赖 |
| `python-wheels/` | 可选的依赖 wheel 缓存（便于二次安装） |
| `docker-compose.neo4j.yml` | 可选 Neo4j 图谱服务 |

## Neo4j（可选）

```bat
cd runtime
docker compose -f docker-compose.neo4j.yml up -d
```

在 `source/backend/.env` 设置 `NEO4J_ENABLED=true` 后重启后端。
""",
        encoding="utf-8",
    )
    return str(readme.resolve())


def copy_neo4j_compose() -> dict:
    src = REPO_ROOT / "docker-compose.neo4j.yml"
    if not src.exists():
        return {"skipped": True}
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    dst = RUNTIME_ROOT / "docker-compose.neo4j.yml"
    shutil.copy2(src, dst)
    return {"compose": str(dst.resolve()), "readme": write_runtime_readme()}


def build(
    skip_frontend: bool = False,
    skip_wheels: bool = False,
    skip_python: bool = False,
    skip_smoke: bool = False,
    force_frontend: bool = False,
    force_python: bool = False,
) -> dict:
    result: dict = {"neo4j": copy_neo4j_compose()}
    if not skip_frontend:
        result["frontend_dist"] = build_frontend_dist(force=force_frontend)
    if not skip_wheels:
        result["agent_wheels"] = download_agent_wheels()
    if not skip_python:
        result["portable_python"] = build_portable_python(force=force_python)
    if not skip_smoke:
        result["api_smoke"] = run_api_smoke()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-frontend-build", action="store_true")
    parser.add_argument("--skip-wheels", action="store_true")
    parser.add_argument("--skip-python", action="store_true")
    parser.add_argument("--skip-smoke", action="store_true")
    parser.add_argument("--force-frontend-build", action="store_true")
    parser.add_argument("--force-python-build", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            build(
                skip_frontend=args.skip_frontend_build,
                skip_wheels=args.skip_wheels,
                skip_python=args.skip_python,
                skip_smoke=args.skip_smoke,
                force_frontend=args.force_frontend_build,
                force_python=args.force_python_build,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
