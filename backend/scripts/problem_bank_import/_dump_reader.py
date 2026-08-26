"""Shared reader/tokenizer for the mysqldump file.

The dump uses the standard `mysqldump` extended-insert format:
    INSERT INTO `table` (`c1`,`c2`,...) VALUES (v1,v2,...),(v1,v2,...),...;

Values are either:
  - the bare word NULL
  - a decimal number (optionally signed / with a leading dot)
  - a single-quoted string, where mysqldump escapes backslash, quote and
    control characters with a leading backslash (\\', \\\\, \\n, \\r, \\t, \\0, \\Z)

This module implements a small hand-written tokenizer good enough to
losslessly split a VALUES clause into rows of Python values (str / int /
float / None), without depending on any third-party SQL parser.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

DUMP_PATH = Path(__file__).resolve().parents[3] / '_incoming_data' / 'learning_core_groups_masked_normal.sql'

_ESCAPES = {
    '0': '\0', "'": "'", '"': '"', 'b': '\b', 'n': '\n', 'r': '\r',
    't': '\t', 'Z': '\x1a', '\\': '\\', '%': '%', '_': '_',
}


def unescape_mysql_string(raw: str) -> str:
    """Decode the inside of a mysqldump single-quoted string literal."""
    out = []
    i = 0
    n = len(raw)
    while i < n:
        ch = raw[i]
        if ch == '\\' and i + 1 < n:
            nxt = raw[i + 1]
            out.append(_ESCAPES.get(nxt, nxt))
            i += 2
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


def split_values_tuple(tuple_text: str) -> list:
    """Parse the inside of one `(...)` VALUES tuple into Python values."""
    values = []
    i = 0
    n = len(tuple_text)
    while i < n:
        ch = tuple_text[i]
        if ch in ' \t\n\r':
            i += 1
            continue
        if ch == ',':
            i += 1
            continue
        if ch == "'":
            j = i + 1
            buf = []
            while j < n:
                c = tuple_text[j]
                if c == '\\' and j + 1 < n:
                    buf.append(c)
                    buf.append(tuple_text[j + 1])
                    j += 2
                    continue
                if c == "'":
                    if j + 1 < n and tuple_text[j + 1] == "'":
                        buf.append("'")
                        j += 2
                        continue
                    break
                buf.append(c)
                j += 1
            values.append(unescape_mysql_string(''.join(buf)))
            i = j + 1
            continue
        # bare token: NULL / number
        j = i
        while j < n and tuple_text[j] not in ',()':
            j += 1
        token = tuple_text[i:j].strip()
        if token.upper() == 'NULL':
            values.append(None)
        elif token == '':
            pass
        else:
            try:
                if re.fullmatch(r'-?\d+', token):
                    values.append(int(token))
                else:
                    values.append(float(token))
            except ValueError:
                values.append(token)
        i = j
    return values


def split_top_level_tuples(values_clause: str) -> Iterator[str]:
    """Split `(a,b),(c,d)` into ["a,b", "c,d"], respecting quoted strings."""
    depth = 0
    in_str = False
    start = None
    i = 0
    n = len(values_clause)
    while i < n:
        ch = values_clause[i]
        if in_str:
            if ch == '\\':
                i += 2
                continue
            if ch == "'":
                in_str = False
            i += 1
            continue
        if ch == "'":
            in_str = True
            i += 1
            continue
        if ch == '(':
            if depth == 0:
                start = i + 1
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0 and start is not None:
                yield values_clause[start:i]
                start = None
        i += 1


def read_dump_text(path: Path = DUMP_PATH) -> str:
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        return fh.read()


def iter_create_table(text: str, table: str):
    pattern = re.compile(
        r'CREATE TABLE `' + re.escape(table) + r'`\s*\((.*?)\)\s*ENGINE',
        re.DOTALL,
    )
    m = pattern.search(text)
    return m.group(0) if m else None


def iter_insert_rows(text: str, table: str, columns_hint: list | None = None):
    """Yield (columns, row_values) for every row inserted into `table`."""
    insert_pattern = re.compile(
        r'INSERT INTO `' + re.escape(table) + r'`\s*\(([^)]*)\)\s*VALUES\s*(.*?);\n',
        re.DOTALL,
    )
    for m in insert_pattern.finditer(text):
        cols = [c.strip(' `') for c in m.group(1).split(',')]
        values_clause = m.group(2)
        for tuple_text in split_top_level_tuples(values_clause):
            row = split_values_tuple(tuple_text)
            if len(row) != len(cols):
                # tolerate mismatch by skipping malformed tuple
                continue
            yield dict(zip(cols, row))


def load_table(text: str, table: str) -> list[dict]:
    return list(iter_insert_rows(text, table))
