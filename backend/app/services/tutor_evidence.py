"""Course evidence for tutoring; retrieval scores never enter student payloads."""
import hashlib
import re

from app.models import KnowledgeChunk, KnowledgeDocument, User, db
from app.services.knowledge import KnowledgeService
from app.services.knowledge.settings import retrieval_config

MODE_TYPES = {
    'error_explanation': ['concept_explanation', 'misconception'],
    'thought_check': ['concept_explanation', 'summary', 'misconception'],
    'next_step': ['concept_explanation', 'misconception'],
    'local_pseudocode': ['concept_explanation', 'summary'],
}
FOCUS_QUERIES = {'loop': 'for range 循环 遍历 结束边界', 'branch': '条件分支 边界 判断',
                 'output': 'print 输出格式 空格 换行', 'NameError': '变量 定义 名称 作用域',
                 'IndexError': '列表 索引 下标 边界', 'TypeError': '数据类型 类型转换 运算',
                 'SyntaxError': 'Python 语法 缩进 括号 冒号', 'ZeroDivisionError': '除法 零 异常'}


def _hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def _allowed(doc, chunk, user_id):
    user = db.session.get(User, user_id)
    if not user or user.status != 'active' or not doc or not chunk:
        return False
    # Builtin course texts are public course evidence. Uploaded materials are
    # deliberately excluded until this branch has an explicit publication ACL.
    return (doc.source == 'builtin' and doc.status == 'READY' and doc.teacher_verified
            and doc.course_id == retrieval_config().get('course_id', 'python-basics')
            and chunk.document_id == doc.id and chunk.status == 'active'
            and chunk.course_id == doc.course_id
            and chunk.version == doc.version and chunk.teacher_verified
            and chunk.knowledge_type in {'concept_explanation', 'misconception', 'summary'})


def prepare(user_id, context, mode, focus):
    documents = KnowledgeDocument.query.filter_by(source='builtin', status='READY', teacher_verified=True).all()
    if not documents:
        return {'status': 'insufficient', 'sources': []}
    query = ' '.join(filter(None, [FOCUS_QUERIES.get(focus), context.get('topic'), context['questionTitle'],
                                  context['questionPrompt'][:300], context['userQuestion'][:300]]))
    try:
        retrieval = KnowledgeService.retrieve(
            query, user_id=user_id, role='student',
            context={'task_type': 'trial', 'task_id': context['exerciseId'],
                     'concept_hint': FOCUS_QUERIES.get(focus, ''), 'title': context['questionTitle']},
            knowledge_types=MODE_TYPES[mode], document_ids=[doc.id for doc in documents],
            require_verified=True, top_k=3, log=False,
        )
        if not retrieval.get('knowledge_grounded'):
            return {'status': 'insufficient', 'sources': []}
        sources = []
        for hit in retrieval.get('reranked', [])[:3]:
            chunk = db.session.get(KnowledgeChunk, hit.get('chunk_id'))
            doc = db.session.get(KnowledgeDocument, chunk.document_id) if chunk else None
            if not _allowed(doc, chunk, user_id) or chunk.knowledge_type not in MODE_TYPES[mode]:
                continue
            # Do not feed embedded example programs into an exercise hint.
            excerpt = re.sub(r'```[\s\S]*?```', '', chunk.content).strip()[:900]
            if not excerpt:
                continue
            sources.append({'label': f'S{len(sources) + 1}', 'chunkId': chunk.chunk_id,
                            'documentId': doc.id, 'version': doc.version,
                            'contentHash': _hash(chunk.content), 'title': doc.title,
                            'chapter': chunk.title or chunk.chapter or doc.chapter,
                            'excerpt': excerpt})
        return {'status': 'available' if sources else 'insufficient', 'sources': sources}
    except Exception:
        db.session.rollback()
        return {'status': 'unavailable', 'sources': []}


def validate(user_id, sources):
    for source in sources:
        chunk = db.session.get(KnowledgeChunk, source['chunkId'], populate_existing=True)
        doc = db.session.get(KnowledgeDocument, source['documentId'], populate_existing=True)
        if (not _allowed(doc, chunk, user_id) or doc.version != source['version']
                or _hash(chunk.content) != source['contentHash']):
            raise ValueError('课程依据已更新或不可访问，请重新提问')


def public_sources(sources, labels):
    return [{key: source[key] for key in ('label', 'title', 'chapter')}
            for source in sources if source['label'] in labels]
