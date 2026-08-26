"""Public, secret-free health endpoints."""
import json
import time
from pathlib import Path

from flask import Blueprint, request
from sqlalchemy import text

from agents.llm_client import api_key_configured, llm_provider
from app.models import db
from app.services.iflytek_spark import IflytekSparkService
from app.services.personalized_resource import PersonalizedResourceService
from app.services.rag_service import RagService
from app.services.xfyun_agent import XfyunAgentService
from app.utils.response import success_response

health_bp = Blueprint('health', __name__, url_prefix='/api/v1')

# Debug-mode agent log sink (session c22abe); workspace root is parents[4] (d:\zhongruan).
_DEBUG_LOG = Path(__file__).resolve().parents[4] / '.cursor' / 'debug-c22abe.log'


@health_bp.route('/debug/agent-log', methods=['POST'])
def debug_agent_log():
    """Append one NDJSON line for Cursor debug-mode instrumentation."""
    try:
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            payload = {'raw': str(payload)}
        payload.setdefault('sessionId', 'c22abe')
        payload.setdefault('timestamp', int(time.time() * 1000))
        _DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _DEBUG_LOG.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + '\n')
    except Exception as exc:
        return success_response({'ok': False, 'error': type(exc).__name__})
    return success_response({'ok': True})


def _deepseek_status() -> dict:
    configured = api_key_configured()
    provider = llm_provider() if configured else None
    return {
        'configured': configured,
        'backend': 'deepseek' if provider and 'deepseek' in provider[1] else ('llm' if provider else 'unavailable'),
        'model': provider[2] if provider else None,
        'status': 'available' if configured else 'unavailable',
    }


@health_bp.route('/system/ai-health', methods=['GET'])
def ai_health():
    xfyun_agent = XfyunAgentService.status()
    spark = IflytekSparkService.status()
    deepseek = _deepseek_status()
    deepseek_configured = bool(deepseek.get('configured'))
    # DeepSeek 优先；讯飞仅在已配置且实测可用时声明
    xfyun_ok = bool(xfyun_agent.get('configured')) and xfyun_agent.get('status') == 'available'
    spark_ok = bool(spark.get('configured')) and spark.get('status') == 'available'
    if deepseek_configured:
        effective = 'deepseek' if deepseek['backend'] == 'deepseek' else 'llm'
    elif spark_ok:
        effective = 'iflytek_spark'
    elif xfyun_ok:
        effective = 'xfyun_agent'
    elif spark.get('configured'):
        effective = 'iflytek_spark'
    elif xfyun_agent.get('configured'):
        effective = 'xfyun_agent'
    else:
        effective = 'local_rules'
    return success_response({
        'deepseek': deepseek,
        'xfyun_agent': xfyun_agent,
        'spark': spark,
        'fallback': {'backend': 'local_rules', 'available': True},
        'effective_backend': effective,
    })


@health_bp.route('/health', methods=['GET'])
def health():
    database = 'healthy'
    try:
        db.session.execute(text('SELECT 1'))
    except Exception:
        database = 'unhealthy'
    rag = RagService.status()
    return success_response({
        'status': 'healthy' if database == 'healthy' else 'degraded',
        'database': database,
        'knowledge_base': {
            'status': rag.get('status'),
            'backend': rag.get('backend'),
            'indexed_documents': rag.get('indexed_documents'),
        },
        'task_executor': PersonalizedResourceService.executor_status(),
        'deepseek': _deepseek_status(),
        'xfyun_agent': XfyunAgentService.status(),
        'spark': IflytekSparkService.status(),
    })
