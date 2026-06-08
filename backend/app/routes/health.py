"""Public, secret-free health endpoints."""
from flask import Blueprint
from sqlalchemy import text

from app.models import db
from app.services.iflytek_spark import IflytekSparkService
from app.services.personalized_resource import PersonalizedResourceService
from app.services.rag_service import RagService
from app.utils.response import success_response

health_bp = Blueprint('health', __name__, url_prefix='/api/v1')


@health_bp.route('/system/ai-health', methods=['GET'])
def ai_health():
    spark = IflytekSparkService.status()
    return success_response({
        'spark': spark,
        'fallback': {'backend': 'local_rules', 'available': True},
        'effective_backend': 'iflytek_spark' if spark['configured'] else 'local_rules',
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
        'spark': IflytekSparkService.status(),
    })
