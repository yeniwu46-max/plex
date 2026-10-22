"""Conservative query cleanup; never add inferred answers or graph vocabulary."""
import re

from .text_utils import normalize_text

VERSION = 'query-cleanup-1'
# Do not edit code, quoted values, operators, negation or numbers. Formatting
# requests are removed only when they form a complete clause, not as substrings
# of a technical question (e.g. "举一个递归错误的例子").
_PROTECTED = re.compile(r'(```[\s\S]*?```|`[^`\n]*`|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')')
_PREFIX = re.compile(
    r'^(?:(?:你好[，,！!\s]*)?(?:小\s*[Ee][，,：:\s]*)?'
    r'(?:请问|请帮我|麻烦你|麻烦|能否帮我|能不能帮我|帮我|请)\s*)'
    r'(?:(?:解释|讲解|说明)(?:一下)?\s*)?', re.I)
_EN_PREFIX = re.compile(r'^(?:(?:could|can|would) you (?:please )?|please )'
                        r'(?:(?:help me )?(?:explain|describe)\s+)?', re.I)
_FORMAT_CLAUSE = re.compile(
    r'^(?:(?:最好|请|可以|能否|希望你|麻烦你)\s*)?'
    r'(?:用(?:简单|通俗|简洁|容易理解)的?(?:语言|话)(?:解释|讲解|说明)(?:一下)?|'
    r'(?:举|给)(?:一个|个)(?:简单的?)?(?:例子|示例)|'
    r'(?:详细|简单)(?:解释|说明)(?:一下)?|谢谢(?:你)?|你好|您好|小\s*[Ee])$')


def prepare_query(query: str, *, enabled: bool = True) -> tuple[str, list[str]]:
    original = normalize_text(query)
    if not enabled:
        return original, []
    pieces = _PROTECTED.split(query or '')
    changed = set()
    for i in range(0, len(pieces), 2):
        clauses = re.split(r'([，,。.!！?？;；\n])', pieces[i])
        for j in range(0, len(clauses), 2):
            value = clauses[j].strip()
            if _FORMAT_CLAUSE.fullmatch(value):
                clauses[j] = ''
                changed.add('response_format_clause')
                continue
            # Remove prefixes only at a clause boundary. If the complete query
            # becomes empty, the original is restored below.
            stripped = _EN_PREFIX.sub('', _PREFIX.sub('', value))
            if stripped != value:
                changed.add('polite_prefix')
                clauses[j] = stripped
        pieces[i] = ''.join(clauses)
    result = ''.join(p if i % 2 else normalize_text(p) for i, p in enumerate(pieces)).strip(' ,.!?;')
    if not result or not re.search(r'[\w\u4e00-\u9fff]', result):
        return original, []
    return result, sorted(changed)
