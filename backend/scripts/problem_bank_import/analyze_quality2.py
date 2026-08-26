from __future__ import annotations

import json
import re
from collections import Counter

from _dump_reader import load_table, read_dump_text


def main():
    text = read_dump_text()
    solutions = load_table(text, 'solution')
    problems = load_table(text, 'problem')

    print('hints distinct sample ->', Counter(s['hints'] for s in solutions).most_common(10))
    print('confidence distinct ->', Counter(s['confidence'] for s in solutions).most_common(10))
    print('returncode distinct ->', Counter(s['returncode'] for s in solutions).most_common(10))
    print('error_name distinct (top 20) ->', Counter(s['error_name'] for s in solutions).most_common(20))

    # error_name vs status
    from collections import defaultdict
    err_vs_status = defaultdict(Counter)
    for s in solutions:
        if s['error_name']:
            err_vs_status[s['error_name']][s['status']] += 1
    for k, v in sorted(err_vs_status.items(), key=lambda kv: -sum(kv[1].values()))[:15]:
        print('error_name', k, '-> status', dict(v))

    # returncode vs status
    rc_vs_status = defaultdict(Counter)
    for s in solutions:
        rc_vs_status[s['returncode']][s['status']] += 1
    print('returncode vs status ->', {k: dict(v) for k, v in rc_vs_status.items()})

    # output block parsing test on a handful of multi-block examples
    sample_outputs = [s['output'] for s in solutions if s['output'] and s['output'].count('##') > 1][:5]
    block_re = re.compile(r'(.*?)\$\$(.*?)\$\$([A-Z]+)##')
    for out in sample_outputs:
        blocks = block_re.findall(out)
        print('---RAW:', out[:200])
        print('PARSED:', blocks)

    # correlate number of parsed S/F blocks with points/total_points for a sample
    checked = 0
    mismatches = 0
    for s in solutions:
        out = s.get('output') or ''
        blocks = block_re.findall(out)
        if not blocks:
            continue
        checked += 1
        s_count = sum(1 for b in blocks if b[2] == 'S')
        total_count = len(blocks)
        if s.get('total_points') is not None and total_count != s.get('total_points'):
            mismatches += 1
        if s.get('points') is not None and s_count != s.get('points') and mismatches < 20:
            pass
    print(f'rows with parsable output blocks: {checked}')

    exact_block_match = 0
    total_with_blocks = 0
    points_match = 0
    for s in solutions:
        out = s.get('output') or ''
        blocks = block_re.findall(out)
        if not blocks:
            continue
        total_with_blocks += 1
        s_count = sum(1 for b in blocks if b[2] == 'S')
        if len(blocks) == s.get('total_points'):
            exact_block_match += 1
        if s_count == s.get('points'):
            points_match += 1
    print(f'total_with_blocks={total_with_blocks} block_count==total_points: {exact_block_match} ({exact_block_match/total_with_blocks:.2%})')
    print(f'S_block_count==points: {points_match} ({points_match/total_with_blocks:.2%})')

    # rows with NO parsable blocks (likely tracebacks / compile errors)
    no_block = [s for s in solutions if s.get('output') and not block_re.findall(s['output'])]
    print(f'rows with output text but no parsable S/F block: {len(no_block)}')
    print('status distribution of those ->', Counter(s['status'] for s in no_block))
    for s in no_block[:3]:
        print('sample output(no block):', (s['output'] or '')[:200])

    # description input/output structure check: look for explicit "Input" "Output" markers
    input_marker = re.compile(r'(Input|输入数据|输入格式|输入[:：])', re.I)
    output_marker = re.compile(r'(Output|输出结果|输出格式|输出[:：])', re.I)
    has_input_marker = sum(1 for p in problems if input_marker.search(p.get('cn_description') or '') or input_marker.search(p.get('description') or ''))
    has_output_marker = sum(1 for p in problems if output_marker.search(p.get('cn_description') or '') or output_marker.search(p.get('description') or ''))
    print(f'problems with an Input-like marker in description: {has_input_marker}/{len(problems)}')
    print(f'problems with an Output-like marker in description: {has_output_marker}/{len(problems)}')


if __name__ == '__main__':
    main()
