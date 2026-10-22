"""Published-rate estimates preserve uncertainty, provenance and account boundaries."""
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy import text

from test_learner_state import app
from test_tutor_context import headers
from test_model_accounting import Response, metadata, post, BODY
from app.models import db, User
from app.models.ai_runtime import AiModelCall as Call
from app.services import model_accounting as accounting, model_pricing as pricing
from agents import http_client

NOW = datetime(2026, 10, 18, 12)


def card():
    raw = json.loads(pricing.DEFAULT_CARD.read_text())
    for row in raw['rates']:
        row['verified_at'] = row['effective_from'] = '2026-10-01T00:00:00Z'
        row['valid_until'] = '2099-01-01T00:00:00Z'
    return raw


def estimate(usage, **extra):
    args = dict(provider='deepseek', model='deepseek-flash', started_at=NOW, status='succeeded', usage=usage,
                context={'host': 'api.deepseek.com', 'eligible': True, 'tier': 'default'})
    args.update(extra)
    return pricing.estimate(pricing.validate_card(card()), **args)


def test_pricing_exact_cache_counts_and_reasoning_not_added_twice():
    value = estimate({'prompt_tokens': 1000, 'completion_tokens': 200, 'total_tokens': 1200,
                      'prompt_cache_hit_tokens': 600, 'prompt_cache_miss_tokens': 400,
                      'prompt_tokens_details': {'cached_tokens': 600}, 'completion_tokens_details': {'reasoning_tokens': 150}})
    assert value['cost_status'] == 'estimated_range' and value['cached_input_tokens'] == 600
    assert value['cost_min'] == Decimal('0.0001818') and value['cost_max'] == Decimal('0.0003636')
    assert value['price_snapshot']['cache_split'] == 'reported'
    assert value['price_snapshot']['source_url'].startswith('https://api-docs.deepseek.com/')


def test_pricing_missing_cache_is_bounded_not_assumed_zero_and_zero_is_explicit():
    value = estimate({'prompt_tokens': 1000, 'completion_tokens': 200})
    assert value['cached_input_tokens'] is None
    assert value['cost_min'] == Decimal('0.000123') and value['cost_max'] == Decimal('0.00054')
    assert value['price_snapshot']['cache_split'] == 'unknown_bounded'
    zero = estimate({'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0})
    assert zero['cost_status'] == 'estimated' and zero['cost_min'] == Decimal(0)
    assert estimate(None)['cost_min'] is None


@pytest.mark.parametrize('usage,reason', [
    ({'total_tokens': 10}, 'missing_usage'),
    ({'prompt_tokens': True, 'completion_tokens': 3}, 'missing_usage'),
    ({'prompt_tokens': -1, 'completion_tokens': 3}, 'missing_usage'),
    ({'prompt_tokens': 10, 'completion_tokens': 3, 'total_tokens': 12}, 'inconsistent_usage'),
    ({'prompt_tokens': 10, 'completion_tokens': 3, 'prompt_cache_hit_tokens': 11}, 'inconsistent_usage'),
    ({'prompt_tokens': 10, 'completion_tokens': 3, 'prompt_cache_hit_tokens': 2, 'prompt_cache_miss_tokens': 9}, 'inconsistent_usage'),
    ({'prompt_tokens': 10, 'completion_tokens': 3, 'prompt_tokens_details': {'cache_write_tokens': 2}}, 'unsupported_usage'),
    ({'prompt_tokens': 10, 'completion_tokens': 3, 'completion_tokens_details': {'audio_tokens': 2}}, 'unsupported_usage'),
    ({'prompt_tokens': 10, 'completion_tokens': 3, 'completion_tokens_details': {'reasoning_tokens': 4}}, 'inconsistent_usage'),
])
def test_pricing_bad_or_unsupported_usage_never_becomes_free(usage, reason):
    value = estimate(usage)
    assert value['cost_status'] == reason and value['cost_min'] is None and value['cost_currency'] is None


@pytest.mark.parametrize('extra,reason', [
    ({'model': None}, 'model_not_reported'),
    ({'model': 'deepseek-chat'}, 'rate_not_found'),  # Never infer the response model from a request alias.
    ({'status': 'failed'}, 'call_not_succeeded'),
    ({'status': 'interrupted'}, 'call_not_succeeded'),
    ({'started_at': datetime(2100, 1, 1)}, 'rate_outside_validity'),
    ({'started_at': datetime(2026, 9, 30)}, 'rate_outside_validity'),
    ({'context': {'host': 'proxy.test', 'eligible': True, 'tier': 'default'}}, 'rate_not_found'),
    ({'response_tier': 'priority'}, 'unsupported_tier'),
    ({'response_tier': 0}, 'unsupported_tier'),
    ({'context': None}, 'unsupported_billing'),
])
def test_pricing_unmatched_context_remains_unknown(extra, reason):
    value = estimate({'prompt_tokens': 10, 'completion_tokens': 5}, **extra)
    assert value['cost_status'] == reason and value['cost_min'] is None


def test_pricing_overlapping_or_invalid_cards_fail_closed_without_blocking_ai(app, tmp_path):
    raw = card(); raw['rates'].append({**deepcopy(raw['rates'][0]), 'id': 'overlap'})
    with pytest.raises(ValueError, match='overlapping'): pricing.validate_card(raw)
    for value in ('NaN', '-1', '1e10', '10001'):
        raw = card(); raw['rates'][0]['input']['max'] = value
        with pytest.raises(ValueError): pricing.validate_card(raw)
    path = tmp_path / 'rates.json'; path.write_text('{broken')
    with app.app_context():
        app.config['AI_MODEL_RATE_CARD_FILE'] = str(path)
        assert pricing.load_card()['error'] == 'invalid_rate_card'
        app.config['AI_MODEL_RATE_CARD_FILE'] = str(tmp_path / 'absent.json')
        assert pricing.load_card()['error'] == 'rate_card_unavailable'


def test_pricing_transport_freezes_card_and_returns_actual_model(app, monkeypatch):
    app.config['AI_MODEL_RATE_CARD'] = card()
    def response(*a, **k):
        # A configuration update during the call must not change that call's rate.
        app.config['AI_MODEL_RATE_CARD']['rates'][0]['output']['min'] = '99'
        app.config['AI_MODEL_RATE_CARD']['rates'][0]['output']['max'] = '99'
        return Response(data={'model': 'deepseek-flash', 'choices': [{'message': {'content': 'private reply'}}],
                              'usage': {'prompt_tokens': 1000, 'completion_tokens': 200, 'prompt_cache_hit_tokens': 600}})
    monkeypatch.setattr(http_client._DIRECT, 'post', response)
    with app.app_context():
        with accounting.scope(**metadata(app)): post()
        row = Call.query.one()
        assert row.model == 'deepseek-flash' and row.price_snapshot['output']['min'] == '0.60'
        assert row.cost_min == Decimal('0.0001818')
        assert row.cost_status == 'estimated_range'
        assert 'private' not in repr(row.price_snapshot)
        before = accounting.summary(app.config['TEST_STUDENT'])['cost_estimate']
        app.config['AI_MODEL_RATE_CARD'] = {'invalid': True}
        assert accounting.summary(app.config['TEST_STUDENT'])['cost_estimate'] == before


def test_pricing_stream_metadata_and_failed_response_are_separate(app, monkeypatch):
    app.config['AI_MODEL_RATE_CARD'] = card()
    lines = [b'data: {"model":"gpt-4o-mini-2024-07-18","service_tier":"default","choices":[]}',
             b'data: {"usage":{"prompt_tokens":1000,"completion_tokens":200,"prompt_tokens_details":{"cached_tokens":600}}}', b'data: [DONE]']
    with app.app_context(), patch.object(http_client._DIRECT, 'post', side_effect=[Response(lines=lines), Response(500, {})]):
        with accounting.scope(**metadata(app)):
            stream = http_client.direct_post('https://api.openai.com/v1/chat/completions', json=BODY, stream=True)
            list(stream.iter_lines()); stream.close(); post()
        rows = Call.query.order_by(Call.started_at).all()
        assert rows[0].cost_min == rows[0].cost_max == Decimal('0.000225')
        assert rows[0].cost_status == 'estimated' and rows[1].cost_min is None
        result = accounting.summary(app.config['TEST_STUDENT'])['cost_estimate']
        assert result['status'] == 'partial' and result['estimated_calls'] == result['unpriced_calls'] == 1
        assert result['unpriced_reasons'] == {'call_not_succeeded': 1}


def test_pricing_billing_context_rejects_modalities_tools_and_custom_endpoints():
    assert pricing.billing_context('https://api.openai.com/v1/chat/completions', BODY)['eligible']
    for url, body in [('http://api.openai.com/v1/chat/completions', BODY), ('https://api.openai.com/v1/responses', BODY),
                      ('https://api.openai.com/v1/chat/completions', {**BODY, 'tools': [{'type': 'web_search'}]}),
                      ('https://api.openai.com/v1/chat/completions', {**BODY, 'messages': [{'content': [{'type': 'image_url'}]}]})]:
        assert not pricing.billing_context(url, body)['eligible']


def test_pricing_summary_never_converts_currencies_or_crosses_owner_class(app, monkeypatch):
    app.config['AI_MODEL_RATE_CARD'] = card()
    monkeypatch.setattr(http_client._DIRECT, 'post', lambda *a, **k: Response(data={
        'model': 'deepseek-flash', 'choices': [{}], 'usage': {'prompt_tokens': 1000, 'completion_tokens': 200}}))
    with app.app_context():
        uid = app.config['TEST_STUDENT']; cid = db.session.get(User, uid).class_id; db.session.rollback()
        for currency, workflow in [('USD', 'resource'), ('CNY', 'counterexample')]:
            app.config['AI_MODEL_RATE_CARD']['rates'][0]['currency'] = currency
            with accounting.scope(**metadata(app, class_id=cid, workflow=workflow)): post()
        with accounting.scope(**metadata(app, user_id=app.config['TEST_TEACHER'])): post()
        db.session.rollback()
        result = accounting.summary(uid)['cost_estimate']
        assert result['estimated_calls'] == 2 and result['unpriced_calls'] == 0
        assert [v['currency'] for v in result['by_currency']] == ['CNY', 'USD']
        assert result['by_workflow']['resource']['estimated_calls'] == 1
    client = app.test_client()
    own = client.get('/api/v1/ai/usage?user_id='+str(app.config['TEST_TEACHER']), headers=headers(app)).json['data']
    cohort = client.get(f'/api/v1/teacher/classes/{cid}/ai-usage', headers=headers(app, True)).json['data']
    assert own['cost_estimate'] == cohort['cost_estimate'] == result
    assert client.get(f'/api/v1/teacher/classes/{cid}/ai-usage', headers=headers(app)).status_code == 403


def test_pricing_migration_does_not_backfill_historical_costs(app):
    names = ['cached_input_tokens', 'cost_status', 'cost_currency', 'cost_min', 'cost_max', 'price_snapshot']
    with app.app_context():
        with accounting.scope(**metadata(app)) as scope: accounting.Record(scope).finish(status='unreported')
        db.session.remove()
        with db.engine.begin() as conn:
            for name in names: conn.execute(text('ALTER TABLE ai_model_calls DROP COLUMN ' + name))
            path = Path(__file__).parents[1] / 'migrations/versions/20261018_0033_model_pricing.py'
            spec = importlib.util.spec_from_file_location('price_migration', path); module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            with Operations.context(MigrationContext.configure(conn)): module.upgrade(); module.upgrade()
        row = Call.query.one()
        assert all(getattr(row, name) is None for name in names)
        assert accounting.summary(app.config['TEST_STUDENT'])['cost_estimate']['unpriced_reasons'] == {'historical_unpriced': 1}
