"""Free-chat quality at the current structured review boundary.

The reviewer is a deterministic fixture here: this tests publication policy,
not the real model's ability to recognize off-topic or evasive prose.
"""
import pytest
from test_learner_state import app
from test_tutoring_modes import dependencies, Provider, APPROVED
from test_messenger_tutoring import generated, send, message
from app.services.tutor_intents import infer_mode
from app.models.tutor_session import TutorTurn


@pytest.mark.parametrize('reply', [
    '能否告诉我你具体遇到了什么问题呢？',
    '变量用来保存数据，例如 my_variable = 10。',
])
def test_reviewer_rejected_evasive_or_off_topic_answer_is_not_published(app, dependencies, reply):
    raw = generated()
    raw['summary'] = reply
    review = {**APPROVED, 'policy_violation': True}
    result = send(app, message('请解释列表推导式并给例子'), Provider(raw, review)).json['data']
    assert result['tutor']['status'] == 'safe_fallback'
    assert reply not in result['reply']
    with app.app_context():
        assert reply not in str(TutorTurn.query.one().response)


def test_reviewed_substantive_explanation_is_preserved(app, dependencies):
    raw = generated()
    raw['summary'] = '列表推导式用一行表达式生成列表。'
    raw['example'] = {'code': '[x*x for x in range(5)]', 'explanation': '生成平方数列表。'}
    provider = Provider(raw)
    result = send(app, message('请解释列表推导式并给例子'), provider).json['data']
    assert result['tutor']['status'] == 'ok'
    assert raw['summary'] in result['reply']
    assert raw['example']['code'] in result['reply']
    assert len(provider.calls) == 2


def test_vague_question_uses_clarification_and_explicit_question_uses_explanation():
    assert infer_mode('不会') == 'clarify'
    assert infer_mode('请解释列表推导式并给例子') == 'concept_explain'


def test_missing_review_fields_fail_closed(app, dependencies):
    raw = generated()
    result = send(app, message(), Provider(raw, {})).json['data']
    assert result['tutor']['status'] == 'safe_fallback'
    assert raw['summary'] not in result['reply']
