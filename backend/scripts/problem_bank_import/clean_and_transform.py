"""Core cleaning pipeline for the legacy Mulberry/HydroOJ-style problem bank
dump (task 1: 题库更新——原始数据清洗并导入 MySQL).

Reads the raw mysqldump text, applies the filtering/cleaning rules described
in REPORT.md, and writes three JSON intermediates plus manual_review.md:

    output/problems.json                 -> rows for the `problems` table
    output/problem_legacy_quest_map.json -> rows for `problem_legacy_quest_map`
    output/problem_submissions.json      -> rows for `problem_submissions`
    output/stats.json                    -> before/after counts for REPORT.md
    manual_review.md                     -> human-review checklist (committed)

This script is read-only with respect to the incoming dump and is
idempotent: re-running it on the same dump always produces byte-identical
JSON (sorted iteration order, no wall-clock-derived values).

Usage:
    python clean_and_transform.py
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from _dump_reader import load_table, read_dump_text
from sandbox_exec import execute_reference_answer
from text_cleaning import (
    HILITE_RE,
    clean_body_text,
    clean_sample_value,
    extract_notes,
    parse_description,
    split_input_output_format,
)

OUT_DIR = Path(__file__).resolve().parent / 'output'
MANUAL_REVIEW_PATH = Path(__file__).resolve().parent / 'manual_review.md'
MANUAL_REVIEW_ITEMS_PATH = OUT_DIR / 'manual_review_items_clean.json'

# 2026-07-30 增强 #6：判定"是否展示中/英切换按钮"的英文正文最短有效长度。
# 低于此阈值的 description_en（含清洗后为空字符串、占位符置空后的 None）一律
# 视为"无有效英文版本"，见 REPORT.md 增强篇。
HAS_ENGLISH_MIN_LENGTH = 12

# concept -> single-letter group used to build the "A001" style problem_no.
# Basics/Operators/Conditionals/Functions follow the mapping the task brief
# spelled out verbatim; Loops/For Loops/While Loops are merged into one
# "D" bucket (they are the same pedagogical stage at different granularity).
# DataTypes and HighTypes were not covered by the brief's example, so they
# are appended after Functions in curriculum order (basic data types before
# "high" / advanced types) as F and G respectively -- this extension is our
# own documented decision, see REPORT.md.
CONCEPT_GROUP_MAP = {
    'Basics': 'A',
    'Operators': 'B',
    'Conditionals': 'C',
    'Loops': 'D',
    'For Loops': 'D',
    'While Loops': 'D',
    'Functions': 'E',
    'DataTypes': 'F',
    'HighTypes': 'G',
}
PROBLEM_NO_WIDTH = 3

OUTPUT_BLOCK_RE = re.compile(r'(.*?)\$\$(.*?)\$\$([A-Z]+)##', re.DOTALL)
PLACEHOLDER_EN_DESC = 'english description'


def to_utc_datetime(unix_ts) -> datetime | None:
    if not unix_ts:
        return None
    return datetime.fromtimestamp(int(unix_ts), tz=timezone.utc).replace(tzinfo=None)


def normalize_title(raw: str) -> str:
    return clean_body_text(raw or '')


def compute_star_difficulty(difficulty, level) -> tuple[int, str]:
    """Map the legacy 0-5 `difficulty` scale onto a Luogu-style 1-5 star
    rating (5 = hardest). See REPORT.md 增强篇 for the full rationale.

    `difficulty` in this dataset is already an intentional 0-5 difficulty
    score set by the original problem authors (distribution: 0:2, 1:25,
    2:22, 3:13, 4:6, 5:2 across the 70 kept problems) -- i.e. it is nearly
    a 1:1 fit for a 1-5 star scale already. We clamp the floor to 1 (a
    "0" and a "1" are both "trivial/tutorial" tier from a *player-facing*
    difficulty label's point of view -- no title needs a literal "0 star"
    badge) and the ceiling to 5. `level` (1-12) looks like an in-group
    stage/level *sequence* number rather than a difficulty score (it keeps
    climbing within one concept group as more problems are added), so it is
    only used as a defensive fallback when `difficulty` is missing.
    """
    if difficulty is not None:
        return max(1, min(5, int(difficulty))), 'difficulty_clamped_1_5'
    if level is not None:
        # defensive fallback only: bucket the level range into 5 tiers.
        bucket = max(1, min(5, (int(level) - 1) // 3 + 1))
        return bucket, 'level_bucketed_fallback'
    return 3, 'default_no_source_data'


class ManualReview:
    def __init__(self):
        self.items: list[dict] = []

    def add(self, table: str, pk, issue: str, suggestion: str):
        self.items.append({'table': table, 'id': pk, 'issue': issue, 'suggestion': suggestion})

    def by_table(self):
        grouped = defaultdict(list)
        for item in self.items:
            grouped[item['table']].append(item)
        return grouped


def assign_problem_numbers(problems: list[dict]) -> dict[int, str]:
    """Deterministic, idempotent A001-style numbering.

    Group by concept -> letter (see CONCEPT_GROUP_MAP), then order each
    group by (create_time, id) so re-running the script on an unchanged
    dump always yields the same numbers even if row iteration order
    differs.
    """
    by_group: dict[str, list[dict]] = defaultdict(list)
    for p in problems:
        group = CONCEPT_GROUP_MAP.get(p['concept'], 'Z')
        by_group[group].append(p)

    numbers: dict[int, str] = {}
    for group, rows in by_group.items():
        rows.sort(key=lambda r: (r['create_time'], r['id']))
        for i, row in enumerate(rows, start=1):
            numbers[row['id']] = f"{group}{str(i).zfill(PROBLEM_NO_WIDTH)}"
    return numbers


def clean_problems(text: str, review: ManualReview) -> tuple[list[dict], dict[int, str]]:
    raw_problems = load_table(text, 'problem')
    stats = {'raw_count': len(raw_problems)}

    # --- rule 1: status filter -------------------------------------------------
    # every row in this masked export has status == 1; we still enforce the
    # filter for future re-imports where a disabled/draft problem (status != 1)
    # might be present. remove_time != 0 marks a soft-deleted problem.
    kept = [p for p in raw_problems if p['status'] == 1 and p['remove_time'] == 0]
    stats['dropped_inactive_or_removed'] = len(raw_problems) - len(kept)

    # --- rule 2: duplicate title/cn_title --------------------------------------
    title_counter = Counter(p['title'] for p in kept)
    cn_title_counter = Counter(p['cn_title'] for p in kept)
    seen_titles: set[str] = set()
    deduped = []
    for p in sorted(kept, key=lambda r: (r['create_time'], r['id'])):
        if title_counter[p['title']] > 1 or cn_title_counter[p['cn_title']] > 1:
            if p['title'] in seen_titles:
                review.add('problem', p['id'], f"duplicate title/cn_title of an earlier row ({p['title']!r})", '丢弃：保留最早创建的同标题题目')
                continue
            seen_titles.add(p['title'])
        deduped.append(p)
    stats['dropped_duplicate_title'] = len(kept) - len(deduped)
    kept = deduped

    problem_numbers = assign_problem_numbers(kept)

    cleaned = []
    for p in kept:
        pid = p['id']
        title_en = normalize_title(p.get('title'))
        title_cn = normalize_title(p.get('cn_title'))

        raw_desc_en = (p.get('description') or '').strip()
        is_placeholder_en = raw_desc_en.strip().lower() == PLACEHOLDER_EN_DESC
        if is_placeholder_en:
            review.add('problem', pid, "description (英文) 为占位符 'English Description'，原文缺失", '已置空 description_en，如需英文版本需人工翻译补充')
            parsed_en = parse_description('')
        else:
            parsed_en = parse_description(raw_desc_en)

        parsed_cn = parse_description(p.get('cn_description') or '')

        description_en = parsed_en.body if not is_placeholder_en else None
        description_cn = parsed_cn.body

        # prefer whichever language actually produced usable samples;
        # fall back the other way if one side is empty (see id=56/57 in
        # REPORT.md: the EN description has empty `{[]}` sample markers
        # while the CN description carries the real values).
        samples = parsed_cn.samples or parsed_en.samples
        samples_source = 'parsed_from_description' if samples else None

        # --- 2026-07-30 增强 #2：15 题样例口径核实 + 7 题真实沙箱补齐 ---------
        # v1 报告的“7 题缺样例”只统计了“中英文都解析不到样例”的情况；这一轮
        # 用户复核发现还有 15 题是“中文能解析到样例，但英文侧解析不到”（多数
        # 因为英文描述本身是占位符或只剩空的 `{[]}` 样例骨架，没有真正的英文
        # 叙述可供解析）。由于最终对外展示只用一份共享的 samples_json（不分
        # 语言），这 15 题的“显示”其实完好（走中文兜底），因此不需要伪造英文
        # 样例；这里只对真正“中英文都没有可展示样例”的 7 题尝试用参考答案在
        # 本地沙箱里真实执行，生成一条可验证正确的样例。
        if not samples:
            answer_probe = (p.get('answer') or '').strip()
            if answer_probe:
                executed_sample, reason = execute_reference_answer(
                    answer_probe, [p.get('cn_description') or '', raw_desc_en],
                )
            else:
                executed_sample, reason = None, 'no_reference_answer'
            if executed_sample:
                samples = [executed_sample]
                samples_source = f'executed_reference_answer:{reason}'
                review.add(
                    'problem', pid,
                    f'样例原本缺失，已通过本地沙箱真实执行参考答案自动生成一条样例（{reason}），'
                    '建议人工复核该样例是否完整覆盖题意（沙箱只生成 1 组，不代表全部边界情况）',
                    '建议复核；如需更多样例可在此基础上人工补充',
                )
            else:
                review.add(
                    'problem', pid,
                    f'中英文描述均未能解析出结构化样例，且无法安全执行参考答案自动生成（原因：{reason}）',
                    '需人工从原始描述/参考答案中补充 samples_json，或确认该题确无样例',
                )

        input_format_en, output_format_en = split_input_output_format(parsed_en.body) if not is_placeholder_en else ('', '')
        input_format_cn, output_format_cn = split_input_output_format(parsed_cn.body)

        answer_code = (p.get('answer') or '').strip()
        expects_stdin = 'input(' in answer_code
        if expects_stdin and not input_format_cn and not input_format_en:
            review.add(
                'problem', pid,
                '参考答案中调用了 input()，但未能从描述正文中提炼出输入格式说明',
                '需人工补充 input_format_cn/input_format_en',
            )

        # 2026-07-30 增强 #2 附带发现：描述正文声称"用户会输入"但参考答案完全
        # 不读取任何输入（Python 无 input()、Java 无 Scanner/System.in），例如
        # id=26《切开那个数》。这类题面/代码不一致不属于清洗脚本能安全修正的
        # 范畴（不确定是题面表达随意还是代码遗漏了本该有的输入），只标记待人工
        # 复核，样例仍按代码的真实运行行为生成（见上面的沙箱执行结果）。
        mentions_input_narrative = bool(re.search(r'(用户.{0,4}输入|user.{0,4}input)', (p.get('cn_description') or '') + raw_desc_en, re.IGNORECASE))
        code_reads_input = expects_stdin or bool(re.search(r'Scanner|System\.in|BufferedReader', answer_code))
        if mentions_input_narrative and not code_reads_input and answer_code:
            review.add(
                'problem', pid,
                '题目描述提到"用户输入"，但参考答案代码完全不读取任何输入，题面与代码行为不一致',
                '需人工确认：是题面描述过时/表达随意，还是参考答案遗漏了输入逻辑；样例已按代码真实行为（不消费任何输入）生成',
            )

        notes = extract_notes(parsed_cn.body) or extract_notes(parsed_en.body)

        if not answer_code:
            review.add('problem', pid, 'answer(参考答案) 字段为空', '需人工补充参考答案代码')

        # --- 2026-07-30 增强 #4：洛谷风格 1-5 星难度 -------------------------
        star_difficulty, star_source = compute_star_difficulty(p.get('difficulty'), p.get('level'))

        # --- 2026-07-30 增强 #6：中/英切换按钮可见性判定 ---------------------
        # 只有真正有实质英文正文的题目才允许前端显示切换按钮；占位符
        # 'English Description' 与"只剩空 {[]} 样例骨架、正文为空"（如
        # id=56/57）在上面都已经让 description_en 归一成 None/''，这里统一用
        # 长度阈值兜底判断，不需要对两种情况分别特判。
        has_english = bool(description_en) and len(description_en.strip()) >= HAS_ENGLISH_MIN_LENGTH

        cleaned.append({
            'id': pid,
            'problem_no': problem_numbers[pid],
            'concept': p.get('concept'),
            'concept_group': CONCEPT_GROUP_MAP.get(p.get('concept'), 'Z'),
            'title_en': title_en,
            'title_cn': title_cn,
            'background': None,
            'background_source': None,
            'description_en': description_en,
            'description_cn': description_cn,
            'has_english': has_english,
            'input_format_en': input_format_en or None,
            'output_format_en': output_format_en or None,
            'input_format_cn': input_format_cn or None,
            'output_format_cn': output_format_cn or None,
            'samples_json': samples,
            'samples_source': samples_source,
            'notes_json': notes,
            'difficulty': p.get('difficulty'),
            'level': p.get('level'),
            'star_difficulty': star_difficulty,
            'star_difficulty_source': star_source,
            'time_limit_ms': None,
            'topic': p.get('topic'),
            'reference_answer': answer_code or None,
            'template': (p.get('template') or '').strip() or None,
            'legacy_problem_name': p.get('name'),
            'legacy_author_user_id': p.get('user_id'),
            'is_active': True,
            'created_at': to_utc_datetime(p['create_time']),
            'updated_at': to_utc_datetime(p.get('update_time')) or to_utc_datetime(p['create_time']),
        })

    return cleaned, stats, {p['id'] for p in cleaned}


def clean_quest_map(text: str, kept_problem_ids: set[int]) -> list[dict]:
    quests = {q['id']: q for q in load_table(text, 'quest')}
    quest_problems = load_table(text, 'quest_problem')
    rows = []
    for qp in quest_problems:
        if qp['problem_id'] not in kept_problem_ids:
            continue
        if qp['remove_time']:
            continue
        quest = quests.get(qp['quest_id'])
        rows.append({
            'problem_id': qp['problem_id'],
            'legacy_quest_id': qp['quest_id'],
            'legacy_quest_title_cn': quest.get('cn_title') if quest else None,
            'required': bool(qp.get('required')),
            'sort_order': qp.get('order') or 0,
        })
    rows.sort(key=lambda r: (r['problem_id'], r['sort_order']))
    return rows


def parse_judge_output(raw_output: str | None):
    """Reverse-engineer the legacy `solution.output` mini-format.

    Format (see REPORT.md "输出编码格式推断依据"): the judge concatenates one
    block per executed test case, `<echo>$$<actual_stdout>$$<verdict>##`,
    where `<echo>` is usually the test case's stdin/label and `<verdict>` is
    `S` (passed) or `F` (failed). When compilation fails (or the process
    crashes before any test case completes) there are no `$$...##` blocks at
    all and the field instead holds a raw Python traceback, which we keep
    verbatim in `raw_judge_output` for audit/debugging.
    """
    if not raw_output:
        return [], None
    blocks = OUTPUT_BLOCK_RE.findall(raw_output)
    if not blocks:
        return [], raw_output
    results = []
    for seq, (echo, output, verdict) in enumerate(blocks, start=1):
        results.append({
            'seq': seq,
            'label': echo.strip() or None,
            'output': output,
            'passed': verdict == 'S',
        })
    return results, None


def clean_submissions(text: str, kept_problem_ids: set[int], review: ManualReview) -> tuple[list[dict], dict]:
    raw_solutions = load_table(text, 'solution')
    users = {u['id']: u for u in load_table(text, 'user')}
    user_infos = {u['user_id']: u for u in load_table(text, 'user_info')}
    groups = {g['id']: g for g in load_table(text, 'group')}

    stats = {'raw_count': len(raw_solutions)}

    kept = [s for s in raw_solutions if s['problem_id'] in kept_problem_ids and not s['remove_time']]
    stats['dropped_orphan_or_removed'] = len(raw_solutions) - len(kept)

    empty_content = [s for s in kept if not (s.get('content') or '').strip()]
    for s in empty_content:
        review.add('solution', s['id'], 'content(提交代码) 为空/空白', '丢弃：无代码内容，无法展示/评分')
    empty_ids = {s['id'] for s in empty_content}
    kept = [s for s in kept if s['id'] not in empty_ids]
    stats['dropped_empty_content'] = len(empty_ids)

    # exact-duplicate resubmission collapsing: keep the earliest attempt in
    # each (user_id, problem_id, content) cluster, drop byte-identical
    # repeats (double-submits / accidental resubmits carry no extra signal).
    kept.sort(key=lambda s: (s['user_id'], s['problem_id'], s['content'], s['create_time'], s['id']))
    seen_keys: set[tuple] = set()
    deduped = []
    dropped_dupe_count = 0
    for s in kept:
        key = (s['user_id'], s['problem_id'], s['content'])
        if key in seen_keys:
            dropped_dupe_count += 1
            continue
        seen_keys.add(key)
        deduped.append(s)
    stats['dropped_exact_duplicate'] = dropped_dupe_count
    kept = deduped

    cleaned = []
    for s in kept:
        user = users.get(s['user_id'])
        user_info = user_infos.get(s['user_id'])
        group = groups.get(s['group_id']) if s.get('group_id') else None

        test_case_results, raw_judge_output = parse_judge_output(s.get('output'))

        total = s.get('total_points')
        points = s.get('points')
        score_percent = round(points / total * 100, 1) if total else None

        cleaned.append({
            'id': s['id'],
            'problem_id': s['problem_id'],
            'legacy_user_id': s['user_id'],
            'legacy_username': user.get('user_name') if user else None,
            'legacy_student_name': user_info.get('stu_name') if user_info else None,
            'legacy_group_id': s.get('group_id'),
            'legacy_group_name': group.get('name') if group else None,
            'code_content': s.get('content'),
            'status': s.get('status'),
            'is_accepted': s.get('status') == 'AC',
            'compile_success': bool(s.get('compile_success')),
            'test_success': bool(s.get('test_success')),
            'score_points': points,
            'score_total': total,
            'score_percent': score_percent,
            'test_case_results_json': test_case_results,
            'raw_judge_output': raw_judge_output,
            'exec_time_ms': s.get('test_time'),
            'exec_memory_kb': s.get('test_space'),
            'time_spent_seconds': s.get('time_spent'),
            'self_confidence': s.get('confidence'),
            'legacy_error_name': s.get('error_name'),
            'returncode': s.get('returncode'),
            'legacy_prev_solution_id': s.get('prev_solution') or None,
            'submitted_at': to_utc_datetime(s['create_time']),
        })

    return cleaned, stats


def main():
    text = read_dump_text()
    review = ManualReview()

    problems, problem_stats, kept_problem_ids = clean_problems(text, review)
    quest_map = clean_quest_map(text, kept_problem_ids)
    submissions, submission_stats = clean_submissions(text, kept_problem_ids, review)

    gen_hints = load_table(text, 'gen_hint')
    kept_submission_ids = {s['id'] for s in submissions}
    orphan_gen_hints = [g for g in gen_hints if g['solution_id'] not in kept_submission_ids]

    OUT_DIR.mkdir(exist_ok=True)

    def dump(name, payload):
        with open(OUT_DIR / name, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)

    # `generate_backgrounds.py` runs *after* this script and writes the
    # "小E" narrative background straight into problems.json. Re-running
    # this cleaning script (the dump itself never changes) must not wipe
    # that work back to null -- carry forward any already-generated
    # background/background_source for unchanged problem ids so the whole
    # multi-script pipeline stays idempotent regardless of run order.
    previous_path = OUT_DIR / 'problems.json'
    if previous_path.exists():
        try:
            with open(previous_path, 'r', encoding='utf-8') as fh:
                previous_by_id = {row['id']: row for row in json.load(fh)}
        except (json.JSONDecodeError, OSError):
            previous_by_id = {}
        for row in problems:
            prev = previous_by_id.get(row['id'])
            if prev and prev.get('background'):
                row['background'] = prev['background']
                row['background_source'] = prev.get('background_source')

    dump('problems.json', problems)
    dump('problem_legacy_quest_map.json', quest_map)
    dump('problem_submissions.json', submissions)

    stats = {
        'problem': problem_stats,
        'solution': submission_stats,
        'gen_hint_not_imported': len(gen_hints),
        'gen_hint_orphaned_by_submission_cleanup': len(orphan_gen_hints),
        'problem_no_distribution': dict(Counter(p['concept_group'] for p in problems)),
        'final_problem_count': len(problems),
        'final_submission_count': len(submissions),
        'manual_review_count': len(review.items),
    }
    dump('stats.json', stats)

    with open(MANUAL_REVIEW_ITEMS_PATH, 'w', encoding='utf-8') as fh:
        json.dump(review.items, fh, ensure_ascii=False, indent=2)

    # 独立可用：单独跑本脚本也能直接看到一份完整的 manual_review.md（只是还
    # 不含后续 generate_backgrounds.py / generate_tags.py 才会发现的问题）。
    # 跑完全部流水线后，请再跑一次 `finalize_manual_review.py` 合并三份来源，
    # 生成最终版 manual_review.md（见 REPORT.md 增强篇「本地验证步骤」）。
    write_manual_review(review.items, source_note='仅包含 clean_and_transform.py 阶段发现的问题；完整清单见运行 finalize_manual_review.py 后的版本。')

    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f'wrote {len(problems)} problems, {len(quest_map)} quest-map rows, {len(submissions)} submissions to {OUT_DIR}')
    print(f'wrote {len(review.items)} manual review items to {MANUAL_REVIEW_PATH} (run finalize_manual_review.py after the full pipeline for the merged version)')


def write_manual_review(items: list[dict], source_note: str = ''):
    grouped = defaultdict(list)
    for item in items:
        grouped[item['table']].append(item)
    lines = [
        '# 人工核对清单（题库导入）',
        '',
        '本文件由脚本自动生成，请勿手工编辑；如需记录人工处理结果，请在业务系统/工单中跟踪，',
        '或在本文件末尾新增"处理记录"小节。',
    ]
    if source_note:
        lines.append('')
        lines.append(f'> {source_note}')
    lines.append('')
    lines.append(f'共 {len(items)} 条待人工确认的记录。')
    lines.append('')
    for table, rows in grouped.items():
        lines.append(f'## 表 `{table}`（{len(rows)} 条）')
        lines.append('')
        lines.append('| 主键 | 问题描述 | 处理建议 |')
        lines.append('| --- | --- | --- |')
        for item in rows:
            issue = item['issue'].replace('|', '\\|')
            suggestion = item['suggestion'].replace('|', '\\|')
            lines.append(f"| {item['id']} | {issue} | {suggestion} |")
        lines.append('')
    with open(MANUAL_REVIEW_PATH, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
