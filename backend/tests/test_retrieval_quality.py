"""Evidence regression, not model-quality or learning-outcome evaluation."""
from copy import deepcopy
import json
from unittest.mock import patch

import pytest

from app.models import db, KnowledgeDocument
from app.services.knowledge import KnowledgeService
from app.services.knowledge.query_preparation import prepare_query
from app.services.knowledge.context_selection import evidence_key, select_context
from app.services.knowledge.rag_service import KnowledgeRagService
from app.services.knowledge.retrieval_service import RetrievalService
from app.services.knowledge.schemas import RetrievedChunk
from app.services.knowledge.settings import retrieval_config
from app.services.knowledge.lexical_index import _Bm25Index
from app.services.knowledge.text_utils import tokenize
from scripts.evaluate_knowledge_retrieval import seed_corpus, evaluate, DATASET
from test_learner_state import app


@pytest.mark.parametrize('technical', [
    'range(3, 0, -1) 不包含 0', 'x <= 5 与 x < 5', 'a != b', 'not (x > 0)',
    '举一个递归终止条件错误的例子', '"请帮我  保留空格"',
    '```python\nif True:\n    x = "a  b"\n    print(x)\n```',
])
def test_query_cleanup_preserves_technical_constraints_and_code(technical):
    result, rules = prepare_query('请帮我解释一下，' + technical + '；请用通俗的语言解释一下。')
    assert technical in result
    assert '通俗' not in result and rules


def test_query_cleanup_is_auditable_and_does_not_empty_request():
    question = '你好，小E，请帮我讲解一下 range 的停止值，最好举一个简单的例子。'
    cleaned, rules = prepare_query(question)
    assert 'range 的停止值' in cleaned
    assert not any(w in cleaned for w in ('你好', '小E', '简单', '讲解'))
    assert set(rules) == {'polite_prefix', 'response_format_clause'}
    assert prepare_query('请帮我解释一下')[0] == '请帮我解释一下'
    assert prepare_query(question, enabled=False)[1] == []


def test_requesting_a_simple_explanation_does_not_filter_out_advanced_topic_material(app):
    with app.app_context(), patch('app.services.knowledge.graph_service.GraphService.concept_lexicon', return_value=[]):
        qu = RetrievalService.understand('请帮我讲解一下递归调用，最好举一个简单的例子。')
        assert qu.difficulty_hint is None
        assert RetrievalService.understand('递归入门').difficulty_hint == 1


def chunk(cid, text, score, vector=None, doc=None):
    return RetrievedChunk(cid, doc or cid, text, final_score=score, selection_vector=vector or [])


def test_exact_copies_do_not_fill_context_but_code_differences_survive():
    a = chunk('a', '边界说明', .95)
    b = chunk('b', '边界说明', .94)
    c = chunk('c', 'if x < 5:\n    print(x)', .9)
    d = chunk('d', 'if x <= 5:\n    print(x)', .89)
    e = chunk('e', 'if x < 5:\nprint(x)', .88)
    selected = select_context([a, b, c, d, e], limit=4, per_document=3, config={})
    assert [r.chunk_id for r in selected] == ['a', 'c', 'd', 'e']
    assert evidence_key('a\r\nb') == evidence_key('a\nb')
    assert evidence_key('"a  b"') != evidence_key('"a b"')


def test_optional_mmr_compares_existing_vectors_preserving_per_document_limit():
    a = chunk('a', '循环规则', 1., [1., 0.], doc='one')
    b = chunk('b', '循环规则的近似改写', .98, [1., 0.], doc='one')
    c = chunk('c', '边界输入检查', .9, [0., 1.], doc='two')
    selected = select_context([a, b, c], limit=2, per_document=2, config={'mmr_enabled': True})
    assert [r.chunk_id for r in selected] == ['a', 'c']
    assert a.final_score == 1. and c.final_score == .9  # selection does not overwrite relevance
    assert 'selection_vector' not in a.to_debug_dict() and 'selection_vector' not in a.to_source_dict()
    selected = select_context([a, b, c], limit=3, per_document=1, config={'mmr_enabled': False})
    assert [r.chunk_id for r in selected] == ['a', 'c']


def test_copies_cannot_inflate_confidence():
    a = chunk('a', '唯一一份证据', .9)
    a.score_breakdown['lexical_abs'] = .35
    copies = [deepcopy(a) for _ in range(6)]
    for i, row in enumerate(copies):
        row.chunk_id = str(i)
    with patch('app.services.knowledge.providers.embedding.get_embedding_provider') as provider:
        provider.return_value.absolute_similarity_reliable = False
        assert KnowledgeRagService._confidence([a], []) == KnowledgeRagService._confidence(copies, [])
        provider.return_value.absolute_similarity_reliable = True
        copies[-1].score_breakdown['vector_abs'] = .9
        assert KnowledgeRagService._confidence([copies[-1]], []) == KnowledgeRagService._confidence(copies, [])


def test_small_corpus_keeps_common_topic_terms_as_evidence_without_accepting_unknowns():
    dataset = json.loads(DATASET.read_text(encoding='utf-8'))
    docs = [d for d in dataset['documents'] if d['id'] in {'range-stop', 'range-negative', 'range-trace'}]
    index = _Bm25Index([(d['id'], {}, tokenize(d['title'] + ' ' + d['content'])) for d in docs])

    def score(question, offset):
        query, _ = prepare_query(question)
        coverage = index.coverage(query, [d['id'] for d in docs], idf_offset=offset)
        rows = [chunk(d['id'], d['content'], 1.) for d in docs]
        for row in rows:
            row.score_breakdown['lexical_abs'] = coverage[row.chunk_id]
        return KnowledgeRagService._confidence(rows, [])

    with patch('app.services.knowledge.providers.embedding.get_embedding_provider') as provider:
        provider.return_value.absolute_similarity_reliable = False
        positive = next(q['query'] for q in dataset['queries'] if q['id'] == 'range-long')
        assert score(positive, 1.)[0] > score(positive, 0.)[0]
        assert score(positive, 1.)[2]
        for question in (q['query'] for q in dataset['queries'] if not q['relevant']):
            assert not score(question, 1.)[2], question


def test_engineering_corpus_long_questions_unknowns_and_ablation(app):
    dataset = json.loads(DATASET.read_text(encoding='utf-8'))
    with app.app_context():
        seed_corpus(dataset)
        report = evaluate(dataset, app.config['TEST_STUDENT'])
        baseline = report['baseline']['metrics']
        revised = report['cleanup_dedup_coverage']['metrics']
        assert revised['answerable_grounded_rate'] > baseline['answerable_grounded_rate']
        assert revised['recall_at_3'] >= baseline['recall_at_3']
        assert revised['false_grounded_rate'] == 0 and revised['duplicate_rate_at_3'] == 0
        cases = {c['id']: c for c in report['cleanup_dedup_coverage']['cases']}
        assert cases['range-long']['grounded'] and cases['range-polite']['grounded']
        forbidden = {'private-secret', 'hidden-solution'}
        assert not any(forbidden & set(c['chunks']) for r in report.values() for c in r['cases'])
        assert retrieval_config()['rerank']['mmr_enabled'] is False


def test_cleaning_cannot_turn_graph_expansion_into_query_evidence(app):
    dataset = json.loads(DATASET.read_text(encoding='utf-8'))
    with app.app_context():
        seed_corpus(dataset)
        # Even an authoritative task concept cannot prove a different topic.
        plan = KnowledgeService.prepare('未收录的量子隧穿计算', user_id=app.config['TEST_STUDENT'],
            context={'concept_hint': 'loop-for', 'task_type': 'practice'})
        assert 'loop-for' in plan.retrieval.understanding.concept_ids
        assert not plan.knowledge_grounded


def test_retracted_copies_are_never_selected_after_cleanup(app):
    dataset = json.loads(DATASET.read_text(encoding='utf-8'))
    with app.app_context():
        seed_corpus(dataset)
        for row in KnowledgeDocument.query.filter(KnowledgeDocument.id.in_(['range-copy-a', 'range-copy-b'])):
            row.published = False
        db.session.commit()
        plan = KnowledgeService.prepare('请帮我解释一下 range 停止值，最好举一个简单的例子', user_id=app.config['TEST_STUDENT'])
        assert 'range-stop' in [c.chunk_id for c in plan.chunks]
        assert not {'range-copy-a', 'range-copy-b'} & {c.chunk_id for c in plan.chunks}
