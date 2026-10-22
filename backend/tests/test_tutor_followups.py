"""Regressions from the synthetic ordinary-student tutoring flow."""
import json
from unittest.mock import patch

import pytest

from test_learner_state import app
from test_tutoring_modes import dependencies, ask, body, candidate, Provider, APPROVED
from test_tutor_context import headers
from app.models import db, TrialQuestion
from app.models.tutor_session import TutorTurn
from app.services.knowledge import KnowledgeService
from scripts.evaluate_knowledge_retrieval import seed_corpus


@pytest.mark.parametrize("question", [
    "range(3, 0, -1) 不包含 0 吗？",
    "只提示下一步：我要核对 x <= 5 和 x < 5 的差别。",
    "这个题的未收录量子隧穿算法怎样计算？",
])
def test_specific_question_is_not_diluted_by_title_or_previous_topic(app, dependencies, question):
    first = ask(app, body(app), Provider(candidate())).json['data']
    app.test_client().post('/api/v1/student/tutor-responses/' + first['display_receipt_id'] + '/displayed', headers=headers(app))
    ask(app, body(app, question=question, session_id=first['session_id']), Provider(candidate()))
    assert dependencies[0].call_args.args[0] == question


def test_shortcut_retrieves_real_course_evidence_without_lowering_confidence(app):
    with app.app_context():
        seed_corpus({'documents': [{'id': 'ordinary-range', 'concept': 'loop-for',
            'title': 'for 循环与边界核对',
            'content': 'range(start, stop) 包含 start，不包含 stop。列表的合法索引从 0 到长度减一。例如 range(1, 4) 提供 1、2、3。先手工列出循环访问的索引，再核对是否处理最后一个元素。空序列不会执行循环体，累加器应在循环前初始化。单元素输入适合检查末项遗漏。'}]})
        q = db.session.get(TrialQuestion, app.config['TEST_QUESTION'])
        q.knowledge_key = 'loop-for'
        q.stem = '从标准输入读取一行空格分隔的整数，输出它们的总和。空行的总和为 0。请编写完整的 Python 程序。'
        db.session.commit()
    app.config['TUTOR_MODELS_ENABLED'] = False
    result = ask(app, body(app, question='只提示下一步'), Provider(candidate())).json['data']
    assert result['evidence_status'] == 'grounded'
    # A task concept is not evidence for a substantive unrelated question.
    unknown = ask(app, body(app, question='未收录的量子隧穿计算'), Provider(candidate())).json['data']
    assert unknown['evidence_status'] == 'insufficient_evidence'


def test_rejected_followup_does_not_ask_again_for_results_already_supplied(app, dependencies):
    first = ask(app, body(app), Provider(candidate())).json['data']
    app.test_client().post('/api/v1/student/tutor-responses/' + first['display_receipt_id'] + '/displayed', headers=headers(app))
    generated = candidate()
    generated['next_step'] = '核对停止值与列表长度的关系。'
    generated['summary'] = 'REJECTED-CANDIDATE-CONTENT'
    review = {**APPROVED, 'unsupported_claims': True, 'citation_mismatch': True}
    result = ask(app, body(app, session_id=first['session_id'], question='我按提示列出了长度为 3 时的索引 0、1，最后的索引 2 没有被访问。stop 是否包含？'), Provider(generated, review)).json['data']
    assert result['status'] == 'safe_fallback' and result['display_receipt_id'] is None
    assert '请描述你按上一条提示' not in result['next_step']
    assert result['policy_result']['review_failures'] == ['citation_mismatch', 'unsupported_claims']
    assert result['citations'] == [] and 'REJECTED-CANDIDATE-CONTENT' not in str(result)
    with app.app_context():
        assert 'REJECTED-CANDIDATE-CONTENT' not in str(db.session.get(TutorTurn, result['request_id']).response)


@pytest.mark.parametrize('review', [{'unsupported_claims': 'false', 'injected': 'secret-candidate'}, [], None])
def test_malformed_review_never_persists_untrusted_diagnostics(app, dependencies, review):
    provider = Provider(candidate())
    provider.review = review
    result = ask(app, body(app), provider).json['data']
    assert result['status'] == 'safe_fallback'
    assert result['policy_result']['review_failures'] == ['invalid_review']
    assert 'secret-candidate' not in json.dumps(result)
