"""Conservative, geometry-aware PDF margin cleanup; never execute extracted code."""
from __future__ import annotations

from collections import defaultdict
from math import ceil
import re
from statistics import median
import textwrap


POLICY = 'pdf-margins-v1'
_MONO = re.compile(r'courier|mono|consolas|typewriter', re.I)
_CODE = re.compile(r'[=(){}\[\]<>`]|^\s*(?:#|def\b|return\b|import\b|from\b|class\b|if\b|for\b|while\b|else:|print\b)')
_PAGE = re.compile(r'^(?:page\s+(\d+)(?:\s+of\s+\d+)?|第\s*(\d+)\s*页(?:\s*/\s*共\s*\d+\s*页)?|[-–—]?\s*(\d+)\s*[-–—]?)$', re.I)


def _key(text):
    return re.sub(r'\s+', ' ', text).strip()


def _mono(line):
    chars = [c for c in line['chars'] if c.get('text', '').strip()]
    return bool(chars) and sum(bool(_MONO.search(c.get('fontname', ''))) for c in chars) / len(chars) >= .8


def _candidate(lines, index, height, typical_size):
    """Only isolated outermost lines, not a repeated sentence somewhere in a page."""
    row = lines[index]
    text = _key(row['text'])
    if not text or len(text) > 100 or _CODE.search(text) or _mono(row):
        return None
    # Preserve typographic headings and numbered section headings, even at the edge.
    if any(float(c['size']) > typical_size * 1.1 or re.search(r'bold|black', c.get('fontname', ''), re.I) for c in row['chars']):
        return None
    if re.match(r'^(?:#{1,6}\s|\d+[.、]|第.+[章节])', text):
        return None
    band = min(36, height * .05)
    if index == 0 and len(lines) > 1 and row['bottom'] <= band and lines[1]['top'] - row['bottom'] >= 12:
        edge = 'top'
    elif index == len(lines) - 1 and index > 0 and row['top'] >= height - band and row['top'] - lines[index - 1]['bottom'] >= 12:
        edge = 'bottom'
    else:
        return None
    number = _PAGE.fullmatch(text)
    if number:
        value = int(next(group for group in number.groups() if group is not None))
        # A stable printed-page offset is checked across pages before removal.
        return edge, 'page_number', value
    return edge, 'text', text


def clean_pdf_pages(pages):
    """Input contains extracted lines/coordinates, not PDF handles. Return lines + counts.

    Repeated text anywhere outside the candidate edge protects that text globally.
    Number-only lines require a stable printed-page offset and the same repetition gate.
    """
    occurrences = defaultdict(list)
    body_text = set()
    for page_index, page in enumerate(pages):
        sizes = [float(c['size']) for line in page['lines'] for c in line['chars'] if c.get('text', '').strip()]
        typical_size = median(sizes) if sizes else 12
        for line_index, line in enumerate(page['lines']):
            candidate = _candidate(page['lines'], line_index, page['height'], typical_size)
            if candidate:
                edge, kind, value = candidate
                signature = (edge, kind, value - page_index if kind == 'page_number' else value)
                occurrences[signature].append((page_index, line_index))
            else:
                body_text.add(_key(line['text']))
    threshold = max(3, ceil(len(pages) * .6))
    removed = set()
    for signature, positions in occurrences.items():
        if len({p for p, _ in positions}) < threshold:
            continue
        if signature[1] == 'text' and signature[2] in body_text:
            continue
        if signature[1] == 'page_number' and any(_key(pages[p]['lines'][i]['text']) in body_text for p, i in positions):
            continue
        removed.update(positions)
    cleaned = []
    for page_index, page in enumerate(pages):
        cleaned.append([line for line_index, line in enumerate(page['lines']) if (page_index, line_index) not in removed])
    return cleaned, {
        'policy': POLICY, 'removed_line_count': len(removed),
        'affected_page_count': len({p for p, _ in removed}),
        'page_count': len(pages), 'minimum_repeated_pages': threshold,
    }


def lines_to_markdown(lines):
    """Preserve relative horizontal spacing; fence identifiable monospaced code.

    PDF spacing is geometric, not original source indentation. No OCR/column repair
    or inferred runnable code is claimed. Large single-line titles become headings.
    """
    if not lines:
        return ''
    body_sizes = [float(c['size']) for line in lines for c in line['chars'] if c.get('text', '').strip()]
    typical_size = median(body_sizes) if body_sizes else 12
    base_indent = min(len(line['text']) - len(line['text'].lstrip(' ')) for line in lines)
    output, code = [], []

    def flush_code():
        if code:
            text = textwrap.dedent('\n'.join(code))
            # A literal fence within extracted code must not terminate the wrapper.
            longest = max((len(m.group()) for m in re.finditer(r'`+', text)), default=0)
            fence = '`' * max(3, longest + 1)
            output.append(f'{fence}\n{text}\n{fence}')
            code.clear()

    previous_code_top = None
    for line in lines:
        value = line['text'][base_indent:].rstrip()
        if _mono(line):
            if code and previous_code_top is not None:
                # extract_text_lines omits empty layout rows (default y_density=13).
                # Keep the visible blank rows inside monospaced examples as well.
                blank_rows = max(0, round((line['top'] - previous_code_top) / 13) - 1)
                code.extend([''] * min(blank_rows, 64))
            code.append(value)
            previous_code_top = line['top']
            continue
        flush_code()
        previous_code_top = None
        if len(value.strip()) < 120 and line['chars'] and all(float(c['size']) >= typical_size * 1.2 for c in line['chars'] if c.get('text', '').strip()):
            output.append('## ' + _key(value))
        else:
            output.append(value)
    flush_code()
    return textwrap.dedent('\n\n'.join(output)).strip('\n')
