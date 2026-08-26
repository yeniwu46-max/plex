"""放行全部待审个性化资源（开发/演示）。

用法（在 backend 目录）:
  python -m scripts.release_all_resources
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.services.personalized_resource import PersonalizedResourceService


def main() -> int:
    app = create_app()
    with app.app_context():
        result = PersonalizedResourceService.release_all_pending(reviewer_id=0)
        print(
            f"released={result.get('approved_count')} "
            f"total_pending={result.get('total')} "
            f"env={result.get('env')}"
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
