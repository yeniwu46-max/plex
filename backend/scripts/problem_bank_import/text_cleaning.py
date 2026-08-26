"""Text-cleaning and description-parsing helpers for the problem bank import.

All functions are pure (no I/O) so they can be unit-exercised independently
from the dump-parsing / DB-writing code in ``clean_and_transform.py``.

Design notes (see REPORT.md for the full write-up):

* The legacy dump uses a custom ``{[...]}`` highlight markup to bold/emphasise
  keywords and to wrap sample input/output tokens. Inside free-flowing
  narrative text we convert it to Markdown ``**...**`` so the existing
  markdown-it based renderer on the frontend keeps the emphasis. Inside a
  *sample* (input/output) value we strip the markup entirely and unescape
  any markdown-escaped punctuation (e.g. ``\\*`` -> ``*``) because that text
  must be byte-for-byte copy/paste-able into a terminal.
* HTML remnants (``<sup>``, ``<b>``, ``<a href>``, ``<hr>``, ``&radic;`` ...)
  are normalised to their closest Markdown/plain-text equivalent.
* Whitespace: trims leading/trailing blank lines, collapses runs of spaces
  and full-width spaces, strips trailing spaces per line, and collapses 3+
  consecutive blank lines to a single blank line.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

HILITE_RE = re.compile(r'\{\[(.*?)\]\}', re.DOTALL)
HR_RE = re.compile(r'<hr\s*/?>', re.IGNORECASE)
SUP_RE = re.compile(r'<sup>(.*?)</sup>', re.IGNORECASE | re.DOTALL)
BOLD_TAG_RE = re.compile(r'<b>(.*?)</b>', re.IGNORECASE | re.DOTALL)
LINK_TAG_RE = re.compile(r'<a\s+[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
BR_RE = re.compile(r'<br\s*/?>', re.IGNORECASE)
GENERIC_TAG_RE = re.compile(r'</?(i|u|table|tr|td|th|span|p|div)[^>]*>', re.IGNORECASE)

# Labels that introduce a sample input/output pair, EN + CN.
INPUT_LABEL_RE = re.compile(r'(输入数据|Input\s*Data|Input\s*[:：])', re.IGNORECASE)
OUTPUT_LABEL_RE = re.compile(r'(输出结果|Output\s*Data|Output\s*[:：])', re.IGNORECASE)
SAMPLE_HEADER_RE = re.compile(r'#{1,3}\s*(测试样例|样例|Sample|Example)s?\s*', re.IGNORECASE)
LEAD_IN_TAIL_RE = re.compile(
    r'(The following (?:are|is) examples? of input and output:?|以下(?:是|为).{0,10}样例[:：]?)\s*$',
    re.IGNORECASE,
)

NOTE_MARKERS = ['注意：', '注意:', '提示：', '提示:', 'Note:', 'Hint:', '数据范围', '结果保留', '保留两位小数', '精度要求']

FULLWIDTH_SPACE = '\u3000'


def unescape_markdown_punct(text: str) -> str:
    """Undo author-added markdown escapes (``\\*`` -> ``*``) inside sample text.

    The source dump stores sample output such as ``*``/``**`` triangles as
    ``\\*``/``\\*\\*`` so that, when the description is rendered as Markdown,
    the asterisks are not misread as emphasis markers. A *sample* value is
    not rendered as Markdown though (it is copy-pasted verbatim into a
    terminal), so the escaping must be undone.
    """
    return re.sub(r'\\([*_`~\[\]()#+.!-])', r'\1', text)


def strip_html(text: str) -> str:
    text = html.unescape(text)
    text = SUP_RE.sub(lambda m: '^' + m.group(1), text)
    text = BOLD_TAG_RE.sub(lambda m: f'**{m.group(1)}**', text)
    text = LINK_TAG_RE.sub(lambda m: f'[{m.group(2)}]({m.group(1)})', text)
    text = BR_RE.sub('\n', text)
    text = GENERIC_TAG_RE.sub('', text)
    return text


def normalize_whitespace(text: str) -> str:
    if text is None:
        return ''
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace(FULLWIDTH_SPACE, ' ')
    # collapse runs of horizontal whitespace (but not newlines)
    text = re.sub(r'[ \t]+', ' ', text)
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    # collapse 3+ blank lines to exactly one
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def hilite_to_markdown(text: str) -> str:
    """Convert `{[x]}` highlight markup to Markdown bold, for narrative text."""
    return HILITE_RE.sub(lambda m: f'**{m.group(1).strip()}**' if m.group(1).strip() else '', text)


def hilite_to_plain(text: str) -> str:
    """Strip `{[x]}` highlight markup down to plain inner text, for samples."""
    return HILITE_RE.sub(lambda m: m.group(1), text)


def clean_body_text(raw: str) -> str:
    """Clean narrative/body text: HTML -> Markdown, highlight -> bold, whitespace."""
    text = strip_html(raw or '')
    text = hilite_to_markdown(text)
    text = HR_RE.sub('', text)
    return normalize_whitespace(text)


def clean_sample_value(raw: str) -> str:
    """Clean one sample input/output value so it is byte-for-byte copyable."""
    text = strip_html(raw or '')
    text = hilite_to_plain(text)
    text = unescape_markdown_punct(text)
    text = text.replace(FULLWIDTH_SPACE, ' ')
    lines = [line.rstrip() for line in text.replace('\r\n', '\n').split('\n')]
    return '\n'.join(lines).strip('\n')


@dataclass
class ParsedDescription:
    body: str = ''
    samples: list = field(default_factory=list)  # [{'input': str, 'output': str}]


def _cut_leading_lead_in(body: str) -> str:
    return LEAD_IN_TAIL_RE.sub('', body).rstrip()


def parse_description(raw: str) -> ParsedDescription:
    """Split a raw description into (cleaned body, structured samples).

    Heuristics (documented in REPORT.md):
    1. Locate the start of the "samples region": the first ``### 测试样例``
       style heading, or (if absent) the first bare ``Input:``/``输入数据``
       label. Everything before that point is the narrative body.
    2. Within the samples region, every ``Input``-label position starts one
       sample; its input text runs up to the next ``Output``-label, and its
       output text runs up to the next ``Input``-label (or end of string).
       ``<hr>`` tags are pure visual separators and are ignored.
    3. Each side of a sample is taken from the `{[...]}` highlighted tokens
       inside it (joined with newlines for multi-line stdin/stdout); if none
       are present the raw stripped text is used instead.
    4. A sample whose extracted text is empty on the input or output side
       (a genuinely blank ``{[]}`` in the source) is dropped rather than
       kept as a fake empty string.
    """
    if not raw:
        return ParsedDescription(body='', samples=[])

    header_match = SAMPLE_HEADER_RE.search(raw)
    input_match = INPUT_LABEL_RE.search(raw)

    if header_match:
        cut = header_match.start()
    elif input_match:
        cut = input_match.start()
    else:
        return ParsedDescription(body=clean_body_text(raw), samples=[])

    body_raw = raw[:cut]
    samples_region = raw[cut:]
    body = clean_body_text(_cut_leading_lead_in(body_raw))

    input_positions = list(INPUT_LABEL_RE.finditer(samples_region))
    samples = []
    for idx, m in enumerate(input_positions):
        input_start = m.end()
        out_match = OUTPUT_LABEL_RE.search(samples_region, input_start)
        next_input_start = input_positions[idx + 1].start() if idx + 1 < len(input_positions) else len(samples_region)
        if not out_match or out_match.start() >= next_input_start:
            continue
        input_chunk = samples_region[input_start:out_match.start()]
        output_chunk = samples_region[out_match.end():next_input_start]
        output_chunk = HR_RE.split(output_chunk)[0]

        input_tokens = HILITE_RE.findall(input_chunk)
        output_tokens = HILITE_RE.findall(output_chunk)
        input_value = clean_sample_value('\n'.join(input_tokens)) if input_tokens else clean_sample_value(input_chunk)
        output_value = clean_sample_value('\n'.join(output_tokens)) if output_tokens else clean_sample_value(output_chunk)

        if not input_value and not output_value:
            continue
        samples.append({'input': input_value, 'output': output_value})

    return ParsedDescription(body=body, samples=samples)


def split_input_output_format(body: str) -> tuple[str, str]:
    """Best-effort extraction of an input-format / output-format summary
    from the narrative body text (which has already had samples removed).

    Strategy (documented in REPORT.md):
    1. If the body text contains an explicit "output"-ish keyword, split the
       body there: everything before is treated as the input-format summary
       (only kept if an "input"-ish keyword also precedes it), everything
       from the keyword onward is the output-format summary.
    2. Otherwise, rather than leaving the field blank, the *entire* body is
       used verbatim as the output-format summary (every one of these
       beginner problems produces some kind of output) and the input-format
       is left empty. Callers cross-check this against whether the
       reference answer actually calls ``input()`` and route the mismatch
       to manual_review.md instead of guessing further.
    """
    if not body:
        return '', ''
    out_kw = re.search(r'(输出|print|Output)', body, re.IGNORECASE)
    if not out_kw:
        return '', body
    in_kw = re.search(r'(输入|input\(|Input)', body[:out_kw.start()], re.IGNORECASE)
    input_format = body[:out_kw.start()].strip() if in_kw else ''
    output_format = body[out_kw.start():].strip()
    return input_format, output_format


def extract_notes(body: str) -> list[str]:
    """Pull out explicit constraint/hint sentences using a conservative,
    marker-based allowlist (never invents constraints that are not present
    verbatim in the source text).
    """
    notes = []
    for marker in NOTE_MARKERS:
        idx = body.find(marker)
        if idx == -1:
            continue
        end = len(body)
        for terminator in ('\n', '。'):
            t_idx = body.find(terminator, idx)
            if t_idx != -1:
                end = min(end, t_idx)
        sentence = body[idx:end].strip(' 。\n')
        if sentence and sentence not in notes:
            notes.append(sentence)
    return notes
