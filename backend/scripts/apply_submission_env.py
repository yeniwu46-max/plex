"""Apply submission-package API env files into backend runtime directory."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def apply(package_root: Path) -> dict:
    config_dir = package_root / "config-samples"
    main_src = config_dir / "backend.env.production-ready"
    spark_src = config_dir / "api-keys.spark.local"
    legacy_src = config_dir / "backend.env.submission"

    backend_env = BACKEND_ROOT / ".env"
    spark_env = BACKEND_ROOT / ".env.spark.local"

    applied = {"backend_env": False, "spark_env": False, "source": None}
    if main_src.exists():
        shutil.copy2(main_src, backend_env)
        applied["backend_env"] = True
        applied["source"] = main_src.name
    elif legacy_src.exists():
        shutil.copy2(legacy_src, backend_env)
        applied["backend_env"] = True
        applied["source"] = legacy_src.name

    if spark_src.exists():
        shutil.copy2(spark_src, spark_env)
        applied["spark_env"] = True

    if applied["backend_env"]:
        text = backend_env.read_text(encoding="utf-8")
        text = text.replace("AGENT_BACKEND=local_rules", "AGENT_BACKEND=auto")
        backend_env.write_text(text, encoding="utf-8")

    return applied


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("package_root", type=Path)
    args = parser.parse_args()
    import json
    print(json.dumps(apply(args.package_root.resolve()), ensure_ascii=False, indent=2))
