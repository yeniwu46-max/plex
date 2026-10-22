"""Frozen, bounded text-token estimates; never an invoice or a zero-cost fallback."""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_FLOOR, ROUND_CEILING
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse

from flask import current_app
from sqlalchemy import select, func

DEFAULT_CARD = Path(__file__).parents[1] / 'data/model_rates_v1.json'
AMOUNT_QUANTUM = Decimal('0.0000000001')
MAX_TOKENS = 2147483647
ESTIMATED = ('estimated', 'estimated_range')


def _time(value):
    if not isinstance(value, str):
        raise ValueError('invalid timestamp')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('UTC offset required')
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def _label(value, limit=128):
    if not isinstance(value, str) or not value or len(value) > limit:
        raise ValueError('invalid label')
    return value


def _rates(value):
    if not isinstance(value, dict) or set(value) != {'min', 'max'}:
        raise ValueError('invalid price range')
    for number in value.values():
        if not isinstance(number, str) or not re.fullmatch(r'\d{1,5}(\.\d{1,6})?', number):
            raise ValueError('decimal strings required')
    lo, hi = Decimal(value['min']), Decimal(value['max'])
    if not 0 <= lo <= hi <= 10000:
        raise ValueError('invalid price bounds')
    return {'min': str(lo), 'max': str(hi)}


def validate_card(raw):
    if not isinstance(raw, dict) or raw.get('schema_version') != 1:
        raise ValueError('invalid rate card schema')
    version = _label(raw.get('version'), 64)
    rows = raw.get('rates')
    if not isinstance(rows, list) or len(rows) > 100:
        raise ValueError('invalid rate entries')
    result, ids = [], set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('invalid rate entry')
        entry = {key: _label(row.get(key)) for key in ('id', 'provider', 'endpoint_host', 'basis')}
        if entry['id'] in ids:
            raise ValueError('duplicate rate ID')
        ids.add(entry['id'])
        if not re.fullmatch(r'[a-z0-9.-]+', entry['endpoint_host']):
            raise ValueError('invalid endpoint host')
        models = row.get('models')
        if not isinstance(models, list) or not 1 <= len(models) <= 20:
            raise ValueError('explicit model names required')
        entry['models'] = [_label(model) for model in models]
        for key in ('verified_at', 'effective_from', 'valid_until'):
            entry[key] = row.get(key); _time(entry[key])
        if not _time(entry['verified_at']) <= _time(entry['effective_from']) < _time(entry['valid_until']):
            raise ValueError('invalid validity period')
        currency = row.get('currency')
        if not isinstance(currency, str) or not re.fullmatch('[A-Z]{3}', currency):
            raise ValueError('ISO currency required')
        entry['currency'] = currency
        source = row.get('source_url'); url = urlparse(_label(source, 500))
        if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError('plain HTTPS pricing source required')
        entry['source_url'] = source
        for key in ('input', 'cached_input', 'output'):
            entry[key] = _rates(row.get(key))
        if any(Decimal(entry['cached_input'][edge]) > Decimal(entry['input'][edge]) for edge in ('min', 'max')):
            raise ValueError('cached input cannot exceed input for this pricing scheme')
        for previous in result:
            same_scope = previous['provider'] == entry['provider'] and previous['endpoint_host'] == entry['endpoint_host']
            overlap = max(_time(previous['effective_from']), _time(entry['effective_from'])) < min(_time(previous['valid_until']), _time(entry['valid_until']))
            if same_scope and overlap and set(previous['models']) & set(entry['models']):
                raise ValueError('overlapping model rates')
        result.append(entry)
    card = {'schema_version': 1, 'version': version, 'rates': result}
    card['hash'] = hashlib.sha256(json.dumps(card, sort_keys=True).encode()).hexdigest()
    return card


def load_card():
    try:
        # Testing may inject a card, but callers cannot provide pricing via HTTP.
        raw = current_app.config.get('AI_MODEL_RATE_CARD')
        if raw is None:
            path = Path(current_app.config.get('AI_MODEL_RATE_CARD_FILE') or DEFAULT_CARD)
            with path.open('rb') as handle:
                data = handle.read(65537)
            if len(data) > 65536:
                raise ValueError('rate card too large')
            raw = json.loads(data)
        return validate_card(deepcopy(raw))
    except OSError:
        return {'error': 'rate_card_unavailable'}
    except (ValueError, TypeError, InvalidOperation, OverflowError):
        return {'error': 'invalid_rate_card'}


def billing_context(url, body):
    parsed = urlparse(url)
    text_only = all(isinstance(m, dict) and (m.get('content') is None or isinstance(m.get('content'), str))
                    for m in body.get('messages', []))
    # Other endpoints, hosted tools, modalities and tiers need their own verified rates.
    eligible = parsed.scheme == 'https' and parsed.path.rstrip('/') in {'/chat/completions', '/v1/chat/completions'}
    eligible = eligible and not body.get('tools') and not body.get('audio') and not body.get('prediction')
    eligible = eligible and body.get('modalities', ['text']) == ['text'] and text_only
    return {'host': parsed.hostname, 'eligible': bool(eligible), 'tier': body.get('service_tier') or 'default'}


def _count(value):
    return value if type(value) is int and 0 <= value <= MAX_TOKENS else None


def token_parts(usage):
    """Validate accounting categories without retaining arbitrary provider metadata."""
    if not isinstance(usage, dict):
        return None, 'missing_usage'
    p, c = _count(usage.get('prompt_tokens')), _count(usage.get('completion_tokens'))
    if p is None or c is None:
        return None, 'missing_usage'
    if 'total_tokens' in usage and _count(usage['total_tokens']) != p + c:
        return None, 'inconsistent_usage'
    details = usage.get('prompt_tokens_details') or {}
    output = usage.get('completion_tokens_details') or {}
    if not isinstance(details, dict) or not isinstance(output, dict):
        return None, 'inconsistent_usage'
    # Cache writes, audio and speculative outputs need different billing rules.
    for container, keys in ((details, ('audio_tokens', 'cache_write_tokens')), (usage, ('cache_write_tokens',)),
                            (output, ('audio_tokens', 'rejected_prediction_tokens', 'accepted_prediction_tokens'))):
        if any(key in container and _count(container[key]) != 0 for key in keys):
            return None, 'unsupported_usage'
    hits = []
    if 'cached_tokens' in details: hits.append(_count(details['cached_tokens']))
    if 'prompt_cache_hit_tokens' in usage: hits.append(_count(usage['prompt_cache_hit_tokens']))
    if 'prompt_cache_miss_tokens' in usage:
        miss = _count(usage['prompt_cache_miss_tokens'])
        if miss is None or miss > p: return None, 'inconsistent_usage'
        hits.append(p - miss)
    if hits and (None in hits or len(set(hits)) != 1 or not 0 <= hits[0] <= p):
        return None, 'inconsistent_usage'
    # Reasoning is already part of completion_tokens; do not add it again.
    if 'reasoning_tokens' in output and (_count(output['reasoning_tokens']) is None or output['reasoning_tokens'] > c):
        return None, 'inconsistent_usage'
    return {'prompt': p, 'completion': c, 'cached': hits[0] if hits else (0 if p == 0 else None)}, None


def estimate(card, *, provider, model, started_at, status, usage, context, response_tier=None):
    result = {'cost_status': 'unknown', 'cost_currency': None, 'cost_min': None, 'cost_max': None,
              'price_snapshot': None, 'cached_input_tokens': None}
    def unknown(reason):
        result['cost_status'] = reason
        return result
    if status != 'succeeded': return unknown('call_not_succeeded')
    if not model: return unknown('model_not_reported')
    if card.get('error'): return unknown(card['error'])
    if not context or not context.get('eligible'): return unknown('unsupported_billing')
    tier = response_tier if response_tier is not None else context.get('tier')
    if tier != 'default': return unknown('unsupported_tier')
    candidates = [r for r in card['rates'] if r['provider'] == provider and model in r['models'] and r['endpoint_host'] == context['host']]
    valid = [r for r in candidates if _time(r['effective_from']) <= started_at < _time(r['valid_until'])]
    if len(valid) > 1: return unknown('ambiguous_rate')
    if not valid: return unknown('rate_outside_validity' if candidates else 'rate_not_found')
    rate = valid[0]
    result['price_snapshot'] = {**deepcopy(rate), 'card_version': card['version'], 'card_hash': card['hash'],
                                'matched_model': model, 'captured_at': started_at.isoformat() + 'Z'}
    parts, reason = token_parts(usage)
    if reason: return unknown(reason)
    p, c, hit = parts['prompt'], parts['completion'], parts['cached']
    result['cached_input_tokens'] = hit
    amounts = []
    for edge, rounding in (('min', ROUND_FLOOR), ('max', ROUND_CEILING)):
        # Unknown cache split widens the interval; it never silently means zero hits.
        cached = (p if edge == 'min' else 0) if hit is None else hit
        amount = (Decimal(p - cached) * Decimal(rate['input'][edge]) + Decimal(cached) * Decimal(rate['cached_input'][edge])
                  + Decimal(c) * Decimal(rate['output'][edge])) / Decimal(1000000)
        amounts.append(amount.quantize(AMOUNT_QUANTUM, rounding=rounding))
    result.update(cost_status='estimated' if amounts[0] == amounts[1] else 'estimated_range', cost_currency=rate['currency'],
                  cost_min=amounts[0], cost_max=amounts[1])
    result['price_snapshot']['cache_split'] = 'reported' if hit is not None else 'unknown_bounded'
    return result


def summary(session, *conditions):
    from app.models.ai_runtime import AiModelCall as Call
    query = select(Call.workflow, Call.cost_status, Call.cost_currency, func.count(), func.sum(Call.cost_min), func.sum(Call.cost_max)).where(*conditions)
    by_currency, reasons, by_workflow = {}, {}, {}
    total = estimated = 0
    for workflow, status, currency, count, lo, hi in session.execute(query.group_by(Call.workflow, Call.cost_status, Call.cost_currency)):
        total += count
        bucket = by_workflow.setdefault(workflow, {'estimated_calls': 0, 'unpriced_calls': 0, 'by_currency': {}})
        if status in ESTIMATED and currency and lo is not None and hi is not None:
            estimated += count; bucket['estimated_calls'] += count
            for target in (by_currency, bucket['by_currency']):
                group = target.setdefault(currency, {'currency': currency, 'min': Decimal(0), 'max': Decimal(0), 'calls': 0, 'range_calls': 0})
                group['min'] += lo; group['max'] += hi; group['calls'] += count
                if status == 'estimated_range': group['range_calls'] += count
        else:
            bucket['unpriced_calls'] += count
            reason = status or 'historical_unpriced'
            reasons[reason] = reasons.get(reason, 0) + count
    def amounts(groups):
        return [{**group, 'min': format(group['min'], '.10f'), 'max': format(group['max'], '.10f')} for _, group in sorted(groups.items())]
    return {'status': 'no_calls' if total == 0 else 'unpriced' if estimated == 0 else 'partial' if estimated < total else 'estimated',
            'basis': 'published_rates_estimate', 'invoice_verified': False, 'estimated_calls': estimated, 'unpriced_calls': total - estimated,
            'by_currency': amounts(by_currency), 'unpriced_reasons': reasons,
            'by_workflow': {key: {**value, 'by_currency': amounts(value['by_currency'])} for key, value in sorted(by_workflow.items())}}
