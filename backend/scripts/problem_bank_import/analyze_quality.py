"""Read-only data-quality analysis over the incoming dump.

Produces the counts/samples used in REPORT.md and manual_review.md. Does not
modify anything. Run with: python analyze_quality.py
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict

from _dump_reader import load_table, read_dump_text

HILITE_RE = re.compile(r'\{\[(.*?)\]\}', re.DOTALL)


def section(title):
    print('\n' + '=' * 100)
    print(title)
    print('=' * 100)


def main():
    text = read_dump_text()
    problems = load_table(text, 'problem')
    solutions = load_table(text, 'solution')
    groups = load_table(text, 'group')
    users = load_table(text, 'user')
    user_infos = load_table(text, 'user_info')
    gen_hints = load_table(text, 'gen_hint')

    section(f'problem: {len(problems)} rows')
    print('distinct status ->', Counter(p['status'] for p in problems))
    print('distinct category ->', Counter(p['category'] for p in problems))
    print('distinct concept ->', Counter(p['concept'] for p in problems))
    print('distinct topic ->', Counter(p['topic'] for p in problems))
    print('distinct place ->', Counter(p['place'] for p in problems))
    print('remove_time != 0 count ->', sum(1 for p in problems if p['remove_time']))
    print('remove_time != 0 ids ->', [p['id'] for p in problems if p['remove_time']])

    title_counter = Counter(p['title'] for p in problems)
    cn_title_counter = Counter(p['cn_title'] for p in problems)
    dup_titles = {k: v for k, v in title_counter.items() if v > 1}
    dup_cn_titles = {k: v for k, v in cn_title_counter.items() if v > 1}
    print('duplicate title ->', dup_titles)
    print('duplicate cn_title ->', dup_cn_titles)

    placeholder_desc = [p['id'] for p in problems if (p.get('description') or '').strip() == 'English Description']
    print(f'description == literal placeholder "English Description": {len(placeholder_desc)} ids ->', placeholder_desc)

    empty_desc = [p['id'] for p in problems if not (p.get('description') or '').strip()]
    empty_cn_desc = [p['id'] for p in problems if not (p.get('cn_description') or '').strip()]
    print('empty description ids ->', empty_desc)
    print('empty cn_description ids ->', empty_cn_desc)

    empty_sample_ids = []
    for p in problems:
        cn = p.get('cn_description') or ''
        if re.search(r'\{\[\s*\]\}', cn):
            empty_sample_ids.append(p['id'])
    print(f'cn_description containing empty {{[ ]}} sample markers: {len(empty_sample_ids)} ->', empty_sample_ids)

    has_hr = [p['id'] for p in problems if '<hr' in (p.get('cn_description') or '') + (p.get('description') or '')]
    has_codeblock = [p['id'] for p in problems if '```' in (p.get('cn_description') or '') + (p.get('description') or '')]
    has_html_tags = [p['id'] for p in problems if re.search(r'<(sup|b|a |br|i|u|table|tr|td)[ >]', (p.get('cn_description') or '') + (p.get('description') or ''), re.I)]
    hilite_counts = Counter()
    for p in problems:
        hilite_counts[p['id']] = len(HILITE_RE.findall((p.get('cn_description') or '') + (p.get('description') or '')))
    total_hilite = sum(hilite_counts.values())
    print(f'rows containing <hr>: {len(has_hr)} -> {has_hr}')
    print(f'rows containing ``` code block: {len(has_codeblock)} -> {has_codeblock}')
    print(f'rows containing other HTML tags: {len(has_html_tags)} -> {has_html_tags}')
    print(f'total {{[...]}} highlight-markup occurrences across problem table: {total_hilite}')

    answer_empty = [p['id'] for p in problems if not (p.get('answer') or '').strip()]
    print('answer empty ids ->', answer_empty)

    section(f'solution: {len(solutions)} rows')
    status_counter = Counter(s['status'] for s in solutions)
    print('distinct status ->', status_counter)

    # cross tab status vs (compile_success, test_success)
    cross = defaultdict(Counter)
    for s in solutions:
        cross[s['status']][(s['compile_success'], s['test_success'])] += 1
    for st, c in cross.items():
        print(f'status={st!r} -> (compile_success,test_success) distribution: {dict(c)}')

    # output field pattern analysis
    output_patterns = Counter()
    for s in solutions:
        out = s.get('output') or ''
        m = re.match(r'^([01])\$\$(.*)\$\$([A-Z]+)##$', out, re.DOTALL)
        if m:
            output_patterns[(m.group(1), m.group(3))] += 1
        elif out == '':
            output_patterns[('<empty>', '')] += 1
        else:
            output_patterns[('<other>', out[:30])] += 1
    print('output field pattern (leading_bit, trailing_code) counts ->', output_patterns.most_common(20))

    # relationship between leading bit / trailing code and test_success/status
    lead_vs_test = defaultdict(Counter)
    trail_vs_status = defaultdict(Counter)
    for s in solutions:
        out = s.get('output') or ''
        m = re.match(r'^([01])\$\$(.*)\$\$([A-Z]+)##$', out, re.DOTALL)
        if not m:
            continue
        lead_vs_test[m.group(1)][s['test_success']] += 1
        trail_vs_status[m.group(3)][s['status']] += 1
    print('leading bit vs test_success ->', {k: dict(v) for k, v in lead_vs_test.items()})
    print('trailing code vs status ->', {k: dict(v) for k, v in trail_vs_status.items()})

    # points vs total_points vs test_success
    points_vs = Counter((s['test_success'], s['points'], s['total_points']) for s in solutions)
    print('sample of (test_success, points, total_points) combos ->', points_vs.most_common(20))

    empty_content = [s['id'] for s in solutions if not (s.get('content') or '').strip()]
    print(f'solution.content empty/blank: {len(empty_content)} sample ids ->', empty_content[:20])

    # duplicates: exact same (user_id, problem_id, content)
    dup_counter = Counter((s['user_id'], s['problem_id'], s['content']) for s in solutions)
    exact_dups = {k: v for k, v in dup_counter.items() if v > 1}
    print(f'exact duplicate (user_id,problem_id,content) submission groups: {len(exact_dups)}; total redundant rows: {sum(v - 1 for v in exact_dups.values())}')

    remove_time_solutions = sum(1 for s in solutions if s['remove_time'])
    print('solution remove_time != 0 count ->', remove_time_solutions)

    orphan_problem_ids = set(s['problem_id'] for s in solutions) - set(p['id'] for p in problems)
    print('solution rows referencing missing problem ids ->', orphan_problem_ids)

    orphan_user_ids = set(s['user_id'] for s in solutions) - set(u['id'] for u in users)
    print('solution rows referencing missing user ids ->', orphan_user_ids)

    time_spent_stats = [s['time_spent'] for s in solutions if s['time_spent'] is not None]
    print('time_spent min/max/avg ->', min(time_spent_stats), max(time_spent_stats), sum(time_spent_stats) / len(time_spent_stats))
    test_time_stats = [s['test_time'] for s in solutions if s['test_time'] is not None]
    print('test_time(ms?) min/max/avg ->', min(test_time_stats), max(test_time_stats), sum(test_time_stats) / len(test_time_stats))
    test_space_stats = [s['test_space'] for s in solutions if s['test_space'] is not None]
    print('test_space min/max/avg ->', min(test_space_stats), max(test_space_stats), sum(test_space_stats) / len(test_space_stats))

    section(f'gen_hint: {len(gen_hints)} rows')
    orphan_gen_hint = set(g['solution_id'] for g in gen_hints) - set(s['id'] for s in solutions)
    print('gen_hint rows referencing missing solution ids ->', len(orphan_gen_hint))

    section(f'group: {len(groups)} rows (whitespace check)')
    for g in groups:
        desc = g.get('description') or ''
        if desc != desc.strip() or '\t' in desc or '  ' in desc:
            print('group', g['id'], repr(desc))

    section(f'user_info: {len(user_infos)} rows (masked name pattern check)')
    non_masked = [u for u in user_infos if not re.match(r'^学生_\d+$', u.get('stu_name') or '')]
    print(f'stu_name not matching 学生_NNN pattern: {len(non_masked)} ->', [u['user_id'] for u in non_masked][:20])

    section(f'user: {len(users)} rows')
    users_sample = users[:2]
    print(json.dumps(users_sample, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
