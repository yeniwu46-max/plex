"""增强 #3：洛谷风格标签系统 —— 生成 `problem_tags` / `problem_tag_map` 数据。

标签维度（详见 REPORT.md 增强篇）：
  - concept  知识点分组标签，直接复用题号字母分组（A~G），每题固定 1 个。
  - topic    更细的关键词/算法标签，规则匹配 reference_answer 源码 + 描述正文
             关键词得出（字符串处理/数学运算/递归/列表.../嵌套循环...），0~N 个，
             不调用 AI（这类结构化特征规则匹配已经足够可靠，比 AI 判断更稳定）。
  - difficulty 难度分档标签，与增强 #4 的 star_difficulty 一一对应，每题固定 1 个。
  - source   来源标签。**不编造任何比赛/年份信息**——本题库不是真实 NOIP/洛谷
             题目。改用真实存在的旧系统 quest 章节标题（如"来源：受伤的兔子"，
             取自 problem_legacy_quest_map，是清洗自旧 dump 的真实数据），没有
             对应 quest 映射的题目退回一个如实说明的通用标签"来源：Mulberry题库"。

用法（在 backend/ 目录下执行，需要先跑过 clean_and_transform.py）：
    python scripts/problem_bank_import/generate_tags.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent / 'output'

TAG_CONCEPT_LABELS = {
    'A': '基础语法', 'B': '运算符', 'C': '条件分支', 'D': '循环',
    'E': '函数', 'F': '数据类型', 'G': '高级类型',
}
CONCEPT_COLOR = '#2080f0'
TOPIC_COLOR = '#0e7490'
SOURCE_COLOR = '#9463f7'
DIFFICULTY_COLOR_BY_STAR = {1: '#18a058', 2: '#36ad6a', 3: '#f0a020', 4: '#e88080', 5: '#d03050'}
DIFFICULTY_LABEL_BY_STAR = {1: '入门', 2: '简单', 3: '中等', 4: '较难', 5: '困难'}

# topic 规则：(code, label, 源码正则 or None, 描述关键词 or None) —— 源码信号优先
# （更可靠，直接反映题目真正考察的实现方式），描述关键词作为源码没命中时的补充。
TOPIC_RULES: list[tuple[str, str, str | None, list[str]]] = [
    ('string_ops', '字符串处理', r'\.(format|split|join|strip|replace|upper|lower|find)\(|f["\']|%s', ['字符串', 'string']),
    ('math_ops', '数学运算', r'\bmath\.|\*\*|//|%\s*\d|abs\(|round\(', ['平方', '倍数', '整除', '算术']),
    ('recursion', '递归', None, []),  # 单独用 AST 检测，见 _detect_recursion
    ('list_ops', '列表/数组', r'\[[^\]\n]*,[^\]\n]*\]|\.append\(|\.sort\(|\.extend\(|\blist\(|\bfor\s+\w+\s+in\s+\[', ['列表', '数组']),
    ('dict_ops', '字典', r'\{[^{}]*:[^{}]*\}|\.get\(|\.keys\(\)|\.values\(\)', ['字典']),
    ('exception_handling', '异常处理', r'\btry\s*:|\bexcept\b', []),
    ('nested_loop', '嵌套循环', None, []),  # 单独检测
    ('nested_condition', '嵌套条件', None, []),  # 单独检测
]


def _detect_recursion(code: str) -> bool:
    match = re.search(r'def\s+(\w+)\s*\(', code)
    if not match:
        return False
    name = match.group(1)
    body = code[match.end():]
    return bool(re.search(rf'\b{re.escape(name)}\s*\(', body))


def _detect_nested(code: str, keyword_re: str) -> bool:
    """粗略缩进检测：某一行匹配 for/while 或 if，且更深缩进处再次出现同类关键词。"""
    lines = code.splitlines()
    stack: list[int] = []
    for line in lines:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if re.match(keyword_re, stripped):
            if any(indent > s for s in stack):
                return True
            stack.append(indent)
    return False


def _topic_tags_for(problem: dict) -> list[str]:
    code = problem.get('reference_answer') or ''
    desc = f"{problem.get('description_cn') or ''} {problem.get('description_en') or ''}"
    codes: list[str] = []
    for code_id, _label, pattern, keywords in TOPIC_RULES:
        if code_id == 'recursion':
            if _detect_recursion(code):
                codes.append(code_id)
            continue
        if code_id == 'nested_loop':
            if _detect_nested(code, r'(for|while)\b'):
                codes.append(code_id)
            continue
        if code_id == 'nested_condition':
            if _detect_nested(code, r'if\b'):
                codes.append(code_id)
            continue
        hit = bool(pattern and re.search(pattern, code))
        if not hit and keywords:
            hit = any(kw in desc for kw in keywords)
        if hit:
            codes.append(code_id)
    return codes


def _source_tag_for(problem_id: int, quest_map: list[dict]) -> tuple[str, str]:
    rows = [q for q in quest_map if q['problem_id'] == problem_id]
    if rows:
        rows.sort(key=lambda r: r.get('sort_order') or 0)
        title = rows[0].get('legacy_quest_title_cn') or 'Mulberry题库'
    else:
        title = 'Mulberry题库'
    code = f'source:{title}'
    label = f'来源：{title}'
    return code, label


def build_tags_and_map(problems: list[dict], quest_map: list[dict]) -> tuple[list[dict], list[dict]]:
    tag_registry: dict[str, dict] = {}

    def register(code: str, label: str, tag_type: str, color: str, sort_order: int) -> str:
        if code not in tag_registry:
            tag_registry[code] = {
                'code': code, 'label': label, 'tag_type': tag_type,
                'color': color, 'sort_order': sort_order,
            }
        return code

    tag_map: list[dict] = []
    topic_sort = {rule[0]: i for i, rule in enumerate(TOPIC_RULES)}
    topic_label = {rule[0]: rule[1] for rule in TOPIC_RULES}

    for p in problems:
        group = p['concept_group']
        concept_code = register(f'concept:{group}', TAG_CONCEPT_LABELS.get(group, group), 'concept', CONCEPT_COLOR, ord(group))
        tag_map.append({'problem_id': p['id'], 'tag_code': concept_code})

        star = p.get('star_difficulty') or 3
        diff_code = register(
            f'difficulty:{star}', DIFFICULTY_LABEL_BY_STAR.get(star, '中等'), 'difficulty',
            DIFFICULTY_COLOR_BY_STAR.get(star, '#f0a020'), star,
        )
        tag_map.append({'problem_id': p['id'], 'tag_code': diff_code})

        src_code, src_label = _source_tag_for(p['id'], quest_map)
        src_code = register(src_code, src_label, 'source', SOURCE_COLOR, 0)
        tag_map.append({'problem_id': p['id'], 'tag_code': src_code})

        for topic_id in _topic_tags_for(p):
            code = register(f'topic:{topic_id}', topic_label[topic_id], 'topic', TOPIC_COLOR, topic_sort[topic_id])
            tag_map.append({'problem_id': p['id'], 'tag_code': code})

    tags = sorted(tag_registry.values(), key=lambda t: (t['tag_type'], t['sort_order'], t['code']))
    return tags, tag_map


def main():
    with open(OUT_DIR / 'problems.json', 'r', encoding='utf-8') as fh:
        problems = json.load(fh)
    with open(OUT_DIR / 'problem_legacy_quest_map.json', 'r', encoding='utf-8') as fh:
        quest_map = json.load(fh)

    tags, tag_map = build_tags_and_map(problems, quest_map)

    with open(OUT_DIR / 'problem_tags.json', 'w', encoding='utf-8') as fh:
        json.dump(tags, fh, ensure_ascii=False, indent=2)
    with open(OUT_DIR / 'problem_tag_map.json', 'w', encoding='utf-8') as fh:
        json.dump(tag_map, fh, ensure_ascii=False, indent=2)

    by_type: dict[str, int] = {}
    for t in tags:
        by_type[t['tag_type']] = by_type.get(t['tag_type'], 0) + 1
    print(f'wrote {len(tags)} tags ({by_type}), {len(tag_map)} tag-map rows')


if __name__ == '__main__':
    main()
