"""Opt-in Spark Lite connectivity smoke test. Never prints credentials or prompts."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.iflytek_spark import IflytekSparkService, SparkServiceError


def main() -> int:
    if not IflytekSparkService.configured():
        print(json.dumps({'ok': False, 'error': 'not_configured'}, ensure_ascii=False))
        return 2
    try:
        result = IflytekSparkService.chat_json(
            '只输出 JSON 对象，格式为 {"ok": true}。',
            '执行一次不包含用户数据的连通性检查。',
            timeout=15,
        )
    except SparkServiceError as exc:
        print(json.dumps({'ok': False, 'error': exc.code}, ensure_ascii=False))
        return 1
    print(json.dumps({
        'ok': result.get('ok') is True,
        'status': IflytekSparkService.status(),
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
