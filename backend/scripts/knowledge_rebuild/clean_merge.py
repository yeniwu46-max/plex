# -*- coding: utf-8 -*-
"""清洗 + 去重 collect_sources.py 的产物，得到统一题库。

## 剔除规则（"缺失过于严重"）

1. 题干为空或纯空白 —— 无法展示，直接丢弃。
2. 编程题三缺：既无参考答案、又无测试点、也无样例 —— 无法判题也无法自学，丢弃。
3. 选择题选项少于 2 个，或 correct_index 越界/缺失 —— 无法作答，丢弃。
4. 题干过短（去空白后 < 6 个字符）且没有任何样例/测试点 —— 属于占位残留，丢弃。
5. 考点属于进阶专题（数据库设计 / REST 与鉴权 / 栈与树与图 / 动态规划 / 复杂度分析），
   不在本次 8 大类（Python 入门）覆盖范围内 —— 强行归类会污染入门节点的掌握度统计，
   因此不进统一题库。**原始数据仍完整保留在 `trial_questions` 表中**，历史试炼不受影响。

## 去重规则（三级）

L1 题干归一化完全相同（去除空白、标点、大小写、Markdown 记号）。
L2 参考答案/起始代码归一化相同，且题干相似度 >= 0.9（difflib.SequenceMatcher）。
L3 指向同一 `legacy_problem_id`（旧题库主键），即同一道题被投放到多个班级试炼。

同一组内保留"信息量最完整"的一条，打分依据（分值见 COMPLETENESS_WEIGHTS）：
有样例 > 有参考答案 > 有测试点 > 有背景故事 > 有输入输出格式 > 描述更长。
被合并掉的条目记入保留条目的 `merged_from`，供人工复核确认没有误删。

用法：
    python scripts/knowledge_rebuild/clean_merge.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.data.knowledge_node_registry import OUT_OF_SCOPE_LEGACY_KEYS  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / 'output'
INPUT_PATH = OUTPUT_DIR / 'collected_questions.json'
OUTPUT_PATH = OUTPUT_DIR / 'cleaned_questions.json'
REPORT_PATH = OUTPUT_DIR / 'cleaning_report.md'

MIN_STEM_LENGTH = 6
SIMILARITY_THRESHOLD = 0.9

COMPLETENESS_WEIGHTS = {
    'samples': 40,
    'reference_answer': 30,
    'test_cases': 25,
    'background': 15,
    'io_format': 10,
    'title': 5,
    'notes': 3,
    'hint': 2,
}

# 来源可信度：旧题库经过完整清洗流水线，元数据最全；前端静态题有测试点；
# 试炼题是运行时投放的副本，信息最少。同分时按此优先级保留。
SOURCE_PRIORITY = {
    'legacy_bank': 5,
    'frontend_static': 4,
    'builtin_coding': 3,
    'builtin_mcq': 2,
    'trial_question': 1,
}

_MARKUP_RE = re.compile(r'[`*_~#>\[\]\(\)（）【】「」“”\'"]+')
_NON_WORD_RE = re.compile(r'[\s\u3000,.;:!?，。；：！？、…—\-]+')


def normalize_text(value: str | None) -> str:
    """归一化用于比较的文本：去 Markdown 记号、去标点空白、转小写。"""
    if not value:
        return ''
    text = _MARKUP_RE.sub('', str(value))
    text = _NON_WORD_RE.sub('', text)
    return text.lower()


def normalize_code(value: str | None) -> str:
    """归一化代码：去掉注释与所有空白，只比较实际语句。"""
    if not value:
        return ''
    lines = []
    for line in str(value).splitlines():
        stripped = line.split('#', 1)[0].strip()
        if stripped:
            lines.append(stripped)
    return re.sub(r'\s+', '', ''.join(lines)).lower()


def stem_text(record: dict) -> str:
    return (record.get('stem') or '').strip()


def completeness_score(record: dict) -> int:
    score = 0
    if record.get('samples'):
        score += COMPLETENESS_WEIGHTS['samples']
    if (record.get('reference_answer') or '').strip():
        score += COMPLETENESS_WEIGHTS['reference_answer']
    if record.get('test_cases'):
        score += COMPLETENESS_WEIGHTS['test_cases']
    if (record.get('background') or '').strip():
        score += COMPLETENESS_WEIGHTS['background']
    if (record.get('input_format') or '').strip() or (record.get('output_format') or '').strip():
        score += COMPLETENESS_WEIGHTS['io_format']
    if (record.get('title_cn') or '').strip():
        score += COMPLETENESS_WEIGHTS['title']
    if record.get('notes'):
        score += COMPLETENESS_WEIGHTS['notes']
    if (record.get('hint') or '').strip():
        score += COMPLETENESS_WEIGHTS['hint']
    score += SOURCE_PRIORITY.get(record.get('source_kind'), 0)
    # 描述长度作为最后的细粒度区分（截断避免长脏文本压过结构化字段）
    score += min(len(stem_text(record)) // 40, 10)
    return score


def reject_reason(record: dict) -> str | None:
    stem = stem_text(record)
    if not stem:
        return '题干为空或纯空白'

    legacy_key = (record.get('legacy_knowledge_key') or '').lower()
    if legacy_key in OUT_OF_SCOPE_LEGACY_KEYS:
        return f'考点 `{legacy_key}` 属于进阶专题，不在本次 8 大类（Python 入门）覆盖范围'

    qtype = record.get('question_type')
    has_samples = bool(record.get('samples'))
    has_tests = bool(record.get('test_cases'))
    has_answer = bool((record.get('reference_answer') or '').strip())

    if len(normalize_text(stem)) < MIN_STEM_LENGTH and not (has_samples or has_tests):
        return f'题干过短（归一化后不足 {MIN_STEM_LENGTH} 字）且无样例/测试点，判定为占位残留'

    if qtype == 'mcq':
        options = [o for o in (record.get('options') or []) if str(o).strip()]
        if len(options) < 2:
            return f'选择题有效选项只有 {len(options)} 个，无法作答'
        index = record.get('correct_index')
        if not isinstance(index, int) or not (0 <= index < len(options)):
            return f'选择题 correct_index={index} 越界或缺失（选项数 {len(options)}）'
        return None

    if not (has_answer or has_tests or has_samples):
        return '编程题既无参考答案、也无测试点与样例，无法判题或自学'
    return None


def merge_group(records: list[dict], rule: str) -> dict:
    """保留信息量最完整的一条，其余记入 merged_from。"""
    ranked = sorted(records, key=completeness_score, reverse=True)
    keeper = dict(ranked[0])
    merged = keeper.setdefault('merged_from', [])
    for other in ranked[1:]:
        merged.append({
            'source_ref': other.get('source_ref'),
            'source_kind': other.get('source_kind'),
            'rule': rule,
            'title': (other.get('title_cn') or stem_text(other))[:60],
        })
        # 补齐 keeper 缺失、而被合并条目有的字段：合并而不是简单丢弃
        for field in (
            'title_cn', 'title_en', 'background', 'input_format', 'output_format',
            'reference_answer', 'starter_code', 'hint', 'run_mode',
            'legacy_knowledge_key', 'legacy_concept', 'legacy_concept_group',
            'legacy_problem_id', 'legacy_problem_no', 'star_difficulty', 'difficulty',
        ):
            if not keeper.get(field) and other.get(field):
                keeper[field] = other[field]
        for field in ('samples', 'notes', 'test_cases', 'options'):
            if not keeper.get(field) and other.get(field):
                keeper[field] = other[field]
    return keeper


def dedupe(records: list[dict]) -> tuple[list[dict], dict[str, int]]:
    stats = Counter()

    # ---- L3：同一 legacy_problem_id 的多次投放 ----
    by_legacy: dict[int, list[dict]] = defaultdict(list)
    rest: list[dict] = []
    for record in records:
        legacy_id = record.get('legacy_problem_id')
        if isinstance(legacy_id, int):
            by_legacy[legacy_id].append(record)
        else:
            rest.append(record)
    stage1: list[dict] = []
    for legacy_id, group in by_legacy.items():
        if len(group) > 1:
            stats['L3_legacy_problem_id'] += len(group) - 1
            stage1.append(merge_group(group, 'L3:同一 legacy_problem_id'))
        else:
            stage1.append(group[0])
    stage1.extend(rest)

    # ---- L1：题干归一化完全相同 ----
    by_stem: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for record in stage1:
        by_stem[(record.get('question_type') or 'coding', normalize_text(stem_text(record)))].append(record)
    stage2: list[dict] = []
    for group in by_stem.values():
        if len(group) > 1:
            stats['L1_same_stem'] += len(group) - 1
            stage2.append(merge_group(group, 'L1:题干归一化相同'))
        else:
            stage2.append(group[0])

    # ---- L2：代码相同 + 题干高度相似 ----
    by_code: dict[tuple[str, str], list[dict]] = defaultdict(list)
    no_code: list[dict] = []
    for record in stage2:
        code = normalize_code(record.get('reference_answer')) or normalize_code(record.get('starter_code'))
        # 起始代码常常只有一行注释，太短的代码指纹没有区分度，不参与 L2
        if code and len(code) >= 12:
            by_code[(record.get('question_type') or 'coding', code)].append(record)
        else:
            no_code.append(record)

    stage3: list[dict] = []
    for group in by_code.values():
        if len(group) == 1:
            stage3.append(group[0])
            continue
        buckets: list[list[dict]] = []
        for record in group:
            target = normalize_text(stem_text(record))
            for bucket in buckets:
                probe = normalize_text(stem_text(bucket[0]))
                if SequenceMatcher(None, probe, target).ratio() >= SIMILARITY_THRESHOLD:
                    bucket.append(record)
                    break
            else:
                buckets.append([record])
        for bucket in buckets:
            if len(bucket) > 1:
                stats['L2_same_code_similar_stem'] += len(bucket) - 1
                stage3.append(merge_group(bucket, 'L2:代码相同且题干相似'))
            else:
                stage3.append(bucket[0])
    stage3.extend(no_code)

    return stage3, dict(stats)


def main() -> None:
    records = json.loads(INPUT_PATH.read_text(encoding='utf-8'))
    total = len(records)

    kept: list[dict] = []
    rejected: list[dict] = []
    for record in records:
        reason = reject_reason(record)
        if reason:
            rejected.append({**record, '_reject_reason': reason})
        else:
            kept.append(record)

    deduped, dedupe_stats = dedupe(kept)
    deduped.sort(key=lambda r: (
        SOURCE_PRIORITY.get(r.get('source_kind'), 0) * -1,
        r.get('source_ref') or '',
    ))

    OUTPUT_PATH.write_text(json.dumps(deduped, ensure_ascii=False, indent=2), encoding='utf-8')

    reject_by_reason = Counter(r['_reject_reason'] for r in rejected)
    reject_by_source = Counter(r['source_kind'] for r in rejected)
    kept_by_source = Counter(r['source_kind'] for r in deduped)
    kept_by_type = Counter(r['question_type'] for r in deduped)

    lines: list[str] = []
    lines.append('# 题目清洗与去重报告')
    lines.append('')
    lines.append(f'原始收集 **{total}** 条 → 剔除 **{len(rejected)}** 条 → 去重合并 **{sum(dedupe_stats.values())}** 条 → 最终保留 **{len(deduped)}** 条。')
    lines.append('')
    lines.append('## 一、剔除明细（缺失过于严重）')
    lines.append('')
    lines.append('| 剔除原因 | 条数 |')
    lines.append('| --- | ---: |')
    for reason, count in reject_by_reason.most_common():
        lines.append(f'| {reason} | {count} |')
    lines.append('')
    lines.append('按来源分布：' + '、'.join(f'{k} {v} 条' for k, v in reject_by_source.most_common()) if rejected else '（无）')
    lines.append('')
    lines.append('## 二、去重明细')
    lines.append('')
    lines.append('| 规则 | 合并掉的条数 |')
    lines.append('| --- | ---: |')
    rule_labels = {
        'L1_same_stem': 'L1 题干归一化完全相同',
        'L2_same_code_similar_stem': 'L2 代码相同且题干相似度 ≥ 0.9',
        'L3_legacy_problem_id': 'L3 指向同一旧题库 problem_id（跨班级重复投放）',
    }
    for rule, count in sorted(dedupe_stats.items()):
        lines.append(f'| {rule_labels.get(rule, rule)} | {count} |')
    lines.append('')
    lines.append('去重时保留"信息量最完整"的一条，判定依据：有样例 > 有参考答案 > 有测试点 > 有背景故事 > 有输入输出格式 > 描述更长；同分时按来源可信度（旧题库 > 前端静态题 > 内置题库 > 试炼投放副本）。被合并条目登记在保留条目的 `merged_from` 字段，最终会写入 `problems.merged_from_json`，可在 SQL 里核对是否误删。')
    lines.append('')
    lines.append('## 三、保留结果分布')
    lines.append('')
    lines.append('| 来源 | 保留条数 |')
    lines.append('| --- | ---: |')
    for source, count in kept_by_source.most_common():
        lines.append(f'| {source} | {count} |')
    lines.append('')
    lines.append('| 题型 | 条数 |')
    lines.append('| --- | ---: |')
    for qtype, count in kept_by_type.most_common():
        lines.append(f'| {qtype} | {count} |')
    lines.append('')
    lines.append('## 四、被剔除条目清单（供追溯）')
    lines.append('')
    lines.append('| source_ref | 原因 | 题干片段 |')
    lines.append('| --- | --- | --- |')
    for item in rejected:
        snippet = re.sub(r'\s+', ' ', stem_text(item))[:40] or '(空)'
        lines.append(f'| `{item.get("source_ref")}` | {item["_reject_reason"]} | {snippet} |')
    lines.append('')

    REPORT_PATH.write_text('\n'.join(lines), encoding='utf-8')

    print(f'原始 {total} → 剔除 {len(rejected)} → 去重合并 {sum(dedupe_stats.values())} → 保留 {len(deduped)}')
    print('剔除原因：')
    for reason, count in reject_by_reason.most_common():
        print(f'  {count:4d}  {reason}')
    print('去重规则命中：')
    for rule, count in sorted(dedupe_stats.items()):
        print(f'  {count:4d}  {rule_labels.get(rule, rule)}')
    print('保留分布：', dict(kept_by_source), dict(kept_by_type))
    print(f'\n-> {OUTPUT_PATH}\n-> {REPORT_PATH}')


if __name__ == '__main__':
    main()
