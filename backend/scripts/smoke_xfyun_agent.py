"""Secret-safe smoke test for the published iFlytek Xingchen workflow Agent."""
from __future__ import annotations

import json
from pathlib import Path
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / '.env')
load_dotenv(ROOT / '.env.spark.local', override=True)

from app.services.xfyun_agent import XfyunAgentService, XfyunAgentServiceError  # noqa: E402


def main() -> int:
    status = XfyunAgentService.status()
    if not status['configured']:
        print(json.dumps({
            'ok': False,
            'reason': 'not_configured',
            'required_env': [
                'XFYUN_AGENT_FLOW_ID',
                'XFYUN_AGENT_API_KEY',
                'XFYUN_AGENT_API_SECRET',
            ],
            'status': status,
        }, ensure_ascii=False, indent=2))
        return 2

    try:
        reply = XfyunAgentService.chat_text(
            user_id=0,
            message='What does print("hello") do in Python?',
            context='Smoke test after publishing. Reply briefly in Chinese.',
            timeout=90,
        )
    except XfyunAgentServiceError as exc:
        print(json.dumps({
            'ok': False,
            'reason': exc.code,
            'message': str(exc),
            'status': XfyunAgentService.status(),
        }, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps({
        'ok': True,
        'reply_preview': reply[:120],
        'status': XfyunAgentService.status(),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
