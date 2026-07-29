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
REPORTS_OUT = BACKEND_ROOT / "reports/a3-submission"


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
    if not force and (src_dist / "index.html").exists():
        print("Using existing frontend/dist (skip npm build)")
    else:
        if not (FRONTEND_ROOT / "node_modules").exists():
            _run(["npm", "ci"], cwd=FRONTEND_ROOT)
        _run(["npm", "run", "build"], cwd=FRONTEND_ROOT)
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
| `python-wheels/` | CrewAI 等多智能体依赖离线 wheel |
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


def build(skip_frontend: bool = False, skip_wheels: bool = False, skip_smoke: bool = False, force_frontend: bool = False) -> dict:
    result: dict = {"neo4j": copy_neo4j_compose()}
    if not skip_frontend:
        result["frontend_dist"] = build_frontend_dist(force=force_frontend)
    if not skip_wheels:
        result["agent_wheels"] = download_agent_wheels()
    if not skip_smoke:
        result["api_smoke"] = run_api_smoke()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-frontend-build", action="store_true")
    parser.add_argument("--skip-wheels", action="store_true")
    parser.add_argument("--skip-smoke", action="store_true")
    parser.add_argument("--force-frontend-build", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            build(
                skip_frontend=args.skip_frontend_build,
                skip_wheels=args.skip_wheels,
                skip_smoke=args.skip_smoke,
                force_frontend=args.force_frontend_build,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
