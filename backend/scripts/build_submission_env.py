"""Build production-ready env files for submission package (includes local API keys)."""
from __future__ import annotations

import argparse
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
TEMPLATE = REPO_ROOT / "docs/submission/config-samples/backend.env.submission"
OUTPUT_DIR = REPO_ROOT / "docs/submission/config-samples"

SPARK_KEY_PREFIXES = ("IFLYTEK_", "XFYUN_")
API_KEY_NAMES = {
    "AGENT_BACKEND",
    "ALIYUN_API_KEY",
    "ALIYUN_MODEL",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_TRIAL_GEN_API_KEY",
    "DEEPSEEK_MESSENGER_API_KEY",
    "DEEPSEEK_EMERGENCY_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_MODEL",
    "IFLYTEK_SPARK_CREDENTIALS",
    "IFLYTEK_SPARK_APP_ID",
    "IFLYTEK_SPARK_API_KEY",
    "IFLYTEK_SPARK_API_PASSWORD",
    "IFLYTEK_SPARK_MODEL",
    "IFLYTEK_SPARK_URL",
    "IFLYTEK_SPARK_TRIAL_CREDENTIALS",
    "IFLYTEK_SPARK_TRIAL_API_PASSWORD",
    "IFLYTEK_SPARK_SUPPLY_CREDENTIALS",
    "IFLYTEK_SPARK_SUPPLY_API_PASSWORD",
    "XFYUN_AGENT_FLOW_ID",
    "XFYUN_AGENT_API_KEY",
    "XFYUN_AGENT_API_SECRET",
    "XFYUN_AGENT_BOT_ID",
    "XFYUN_AGENT_URL",
    "XFYUN_AGENT_USER_INPUT_KEY",
    "RESOURCE_TASK_SYNC",
    "NEO4J_ENABLED",
    "NEO4J_URI",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
}


def _parse_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value:
            values[key] = value
    return values


def _render_env(base_lines: list[str], overrides: dict[str, str]) -> str:
    rendered: list[str] = []
    seen: set[str] = set()
    for line in base_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            rendered.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in overrides:
            rendered.append(f"{key}={overrides[key]}")
            seen.add(key)
        else:
            rendered.append(line)
    for key in sorted(overrides):
        if key not in seen:
            rendered.append(f"{key}={overrides[key]}")
    return "\n".join(rendered).rstrip() + "\n"


def build(output_dir: Path | None = None) -> dict:
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    template_lines = TEMPLATE.read_text(encoding="utf-8").splitlines()
    merged = _parse_env(TEMPLATE)
    for src in (BACKEND_ROOT / ".env", BACKEND_ROOT / ".env.spark.local"):
        merged.update(_parse_env(src))

    merged["DATABASE_URL"] = "sqlite:///instance/learning_system.db"
    merged["AGENT_BACKEND"] = "auto"
    merged.setdefault("FLASK_ENV", "development")
    merged.setdefault("FLASK_DEBUG", "True")
    merged.setdefault("SERVER_PORT", "5100")
    merged.setdefault("CORS_ORIGINS", "http://localhost:5180")
    merged.setdefault("FRONTEND_BASE_URL", "http://localhost:5180")

    main_overrides = {k: v for k, v in merged.items() if k in API_KEY_NAMES or k.startswith("DEEPSEEK_") or k.startswith("OPENAI_")}
    main_overrides.update({
        "DATABASE_URL": merged["DATABASE_URL"],
        "AGENT_BACKEND": "auto",
        "FLASK_ENV": merged.get("FLASK_ENV", "development"),
        "FLASK_DEBUG": merged.get("FLASK_DEBUG", "True"),
        "SERVER_HOST": merged.get("SERVER_HOST", "0.0.0.0"),
        "SERVER_PORT": merged.get("SERVER_PORT", "5100"),
        "SECRET_KEY": merged.get("SECRET_KEY", "submission-dev-secret-key-change-me-32b"),
        "JWT_SECRET_KEY": merged.get("JWT_SECRET_KEY", "submission-dev-jwt-secret-key-change-me-32b"),
        "CORS_ORIGINS": merged.get("CORS_ORIGINS", "http://localhost:5180"),
        "FRONTEND_BASE_URL": merged.get("FRONTEND_BASE_URL", "http://localhost:5180"),
    })

    spark_overrides = {
        k: v for k, v in merged.items()
        if any(k.startswith(prefix) for prefix in SPARK_KEY_PREFIXES) or k == "RESOURCE_TASK_SYNC"
    }

    main_path = out / "backend.env.production-ready"
    spark_path = out / "api-keys.spark.local"
    main_path.write_text(_render_env(template_lines, main_overrides), encoding="utf-8")
    spark_lines = [
        "# 讯飞 Spark / 星辰 Agent 凭证（由打包脚本从开发机注入，启动时复制到 backend/.env.spark.local）",
        "# 请勿公开传播此文件。",
    ]
    for key in sorted(spark_overrides):
        spark_lines.append(f"{key}={spark_overrides[key]}")
    spark_path.write_text("\n".join(spark_lines).rstrip() + "\n", encoding="utf-8")

    configured = sorted(
        key for key, value in {**main_overrides, **spark_overrides}.items()
        if value and any(token in key for token in ("KEY", "SECRET", "CREDENTIALS", "PASSWORD", "BACKEND"))
    )
    return {
        "main_env": str(main_path),
        "spark_env": str(spark_path),
        "configured_api_fields": configured,
        "agent_backend": main_overrides.get("AGENT_BACKEND"),
        "has_deepseek": bool(main_overrides.get("DEEPSEEK_API_KEY")),
        "has_spark": bool(spark_overrides.get("IFLYTEK_SPARK_CREDENTIALS") or spark_overrides.get("IFLYTEK_SPARK_API_KEY")),
        "has_xfyun_agent": bool(spark_overrides.get("XFYUN_AGENT_API_KEY")),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    import json
    print(json.dumps(build(args.output), ensure_ascii=False, indent=2))
