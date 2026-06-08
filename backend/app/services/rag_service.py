# -*- coding: utf-8 -*-
"""RAG 知识库：Mock / LlamaIndex 可切换。"""
import os
from datetime import datetime

MOCK_DOCUMENTS = [
    {
        'id': 'doc_001',
        'name': 'Python-basics.pdf',
        'size': 2048576,
        'type': 'pdf',
        'status': 'indexed',
        'chunk_count': 128,
        'uploaded_at': '2026-05-20T10:30:00',
        'uploader': 'teacher001',
    },
    {
        'id': 'doc_002',
        'name': 'Algorithm-slides.pptx',
        'size': 5242880,
        'type': 'pptx',
        'status': 'indexed',
        'chunk_count': 256,
        'uploaded_at': '2026-05-22T14:15:00',
        'uploader': 'teacher001',
    },
    {
        'id': 'doc_003',
        'name': 'DataStruct-exercises.docx',
        'size': 1048576,
        'type': 'docx',
        'status': 'processing',
        'chunk_count': 0,
        'uploaded_at': '2026-05-28T09:00:00',
        'uploader': 'teacher001',
    },
]

MOCK_QA = {
    'loop': 'for 循环与 while 循环是两种基本循环结构，注意边界条件避免死循环。',
    'recursion': '递归是函数调用自身的技术，需要基线条件与递归条件。',
    'sort': '常见排序：冒泡 O(n^2)、快排 O(nlogn)、归并 O(nlogn)。',
    'list': '列表是 Python 最常用的数据结构，支持 append、切片、排序等操作。',
    'python': 'Python 强调可读性，变量无需声明类型，使用缩进表示代码块。',
    '变量': '变量用于存储数据，Python 中通过赋值创建变量。',
    '函数': '函数通过 def 定义，可接收参数并返回结果。',
}

DEFAULT_ANSWER = '根据课程知识库，该问题与计算思维核心概念相关，建议查阅对应章节。'


class RagService:
    @staticmethod
    def backend_name() -> str:
        return os.getenv('RAG_BACKEND', 'mock').lower()

    @staticmethod
    def upload(filename: str) -> dict:
        task_id = 'task_' + datetime.utcnow().strftime('%Y%m%d%H%M%S')
        return {
            'task_id': task_id,
            'filename': filename,
            'status': 'processing',
            'estimated_time': '30s',
            'backend': RagService.backend_name(),
        }

    @staticmethod
    def query(question: str) -> dict:
        backend = RagService.backend_name()
        if backend == 'llamaindex':
            try:
                return RagService._llamaindex_query(question)
            except Exception:
                pass
        return RagService._mock_query(question)

    @staticmethod
    def _mock_query(question: str) -> dict:
        answer = DEFAULT_ANSWER
        sources = []
        for keyword, ans in MOCK_QA.items():
            if keyword.lower() in question.lower():
                answer = ans
                sources = [{'doc_id': 'doc_001', 'score': 0.92, 'snippet': ans[:80]}]
                break
        return {
            'answer': answer,
            'sources': sources,
            'confidence': 0.92 if sources else 0.55,
            'backend': 'mock',
        }

    @staticmethod
    def _llamaindex_query(question: str) -> dict:
        from llama_index.core import Settings
        from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

        data_dir = os.getenv('RAG_DATA_DIR', 'backend/data/rag_docs')
        if not os.path.isdir(data_dir):
            return RagService._mock_query(question)
        docs = SimpleDirectoryReader(data_dir).load_data()
        index = VectorStoreIndex.from_documents(docs)
        engine = index.as_query_engine(similarity_top_k=3)
        response = engine.query(question)
        text = str(response)
        sources = [{'doc_id': 'local', 'score': 0.85, 'snippet': text[:120]}]
        return {'answer': text, 'sources': sources, 'confidence': 0.85, 'backend': 'llamaindex'}

    @staticmethod
    def list_documents():
        return {'documents': MOCK_DOCUMENTS, 'total': len(MOCK_DOCUMENTS)}

    @staticmethod
    def status():
        indexed = len([d for d in MOCK_DOCUMENTS if d['status'] == 'indexed'])
        return {
            'status': 'healthy',
            'backend': RagService.backend_name(),
            'total_documents': len(MOCK_DOCUMENTS),
            'indexed_documents': indexed,
            'processing_documents': len(MOCK_DOCUMENTS) - indexed,
            'total_chunks': sum(d['chunk_count'] for d in MOCK_DOCUMENTS),
            'last_sync': datetime.utcnow().isoformat(),
        }

    @staticmethod
    def build_context(question: str) -> str:
        result = RagService.query(question)
        if not result.get('sources'):
            return ''
        snippets = [s.get('snippet', '') for s in result['sources'] if s.get('snippet')]
        if not snippets:
            return result.get('answer', '')
        return '\n'.join(f'- {s}' for s in snippets)
