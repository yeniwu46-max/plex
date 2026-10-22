"""Validate a server-owned rate card without calling providers or reading secrets."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from app.services.model_pricing import DEFAULT_CARD, validate_card, _time
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path, default=DEFAULT_CARD)
    args = parser.parse_args()
    try:
        with args.file.open('rb') as handle: raw = handle.read(65537)
        if len(raw) > 65536: raise ValueError('too large')
        card = validate_card(json.loads(raw))
    except (OSError, ValueError, TypeError):
        print(json.dumps({'status': 'invalid_rate_card'})); return 1
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    entries = [{'id': row['id'], 'provider': row['provider'], 'models': row['models'], 'currency': row['currency'],
                'valid_until': row['valid_until'], 'currently_valid': _time(row['effective_from']) <= now < _time(row['valid_until']),
                'source_url': row['source_url']} for row in card['rates']]
    valid = bool(entries) and all(row['currently_valid'] for row in entries)
    print(json.dumps({'status': 'valid' if valid else 'needs_review', 'version': card['version'], 'hash': card['hash'], 'entries': entries}))
    return 0 if valid else 1


if __name__ == '__main__':
    sys.exit(main())
