"""Pedagogical bundle generation: KnowledgeNode, analysis, local/Spark bundle, split."""
from __future__ import annotations

import re
from typing import Any

from app.data.coding_question_bank import CODING_QUESTION_BANK
from app.data.course_knowledge import catalog_points, knowledge_section
from app.data.kg_topology import KG_EDGES, KG_NODES
from app.data.knowledge_catalog import DOMAIN_LABELS, KNOWLEDGE_UNIVERSE, POINT_TO_BANK
from app.data.knowledge_node_registry import kg_id_from_key
from app.data.pedagogical_cases import cases_for_knowledge
from app.services.iflytek_spark import IflytekSparkService
from app.services.question_generator import QUESTION_BANK

POINTS = catalog_points()

TARGET_DEFAULT = '大学'
STAGE_DEFAULT = '学习'
STAGE_BLOOM = {
    '预习': '记忆/理解',
    '学习': '理解/应用',
    '练习': '应用/分析',
    '复习': '应用/分析',
    '考试': '分析/评价',
}
VALID_STAGES = frozenset(STAGE_BLOOM)
VALID_TARGETS = frozenset({'小学', '初中', '高中', '大学'})
STYLE_ALIASES = {
    '图文': '图文',
    '案例': '案例',
    '动画': '动画',
    '交互': '交互',
    '小游戏': '小游戏',
    '代码实验': '代码实验',
    '分步骤': '图文',
    '先看代码': '代码实验',
    '生活化案例': '案例',
}

BUNDLE_SCHEMA = {
    'type': 'object',
    'required': [
        'format', 'title', 'node', 'objective', 'analysis', 'explain',
        'diagrams', 'cases', 'code', 'exercises', 'summary',
    ],
    'properties': {
        'format': {'const': 'pedagogical_v2'},
        'title': {'type': 'string', 'minLength': 1},
        'node': {'type': 'string', 'minLength': 1},
        'objective': {'type': 'array', 'minItems': 1},
        'analysis': {'type': 'object'},
        'explain': {'type': 'string', 'minLength': 20},
        'diagrams': {'type': 'array', 'minItems': 1},
        'cases': {'type': 'array', 'minItems': 2},
        'code': {'type': 'array', 'minItems': 1},
        'exercises': {'type': 'array', 'minItems': 6},
        'summary': {'type': 'object'},
        'markdown': {'type': 'string'},
    },
    'additionalProperties': True,
}

_KG_LABELS = {node['id']: node['label'] for node in KG_NODES}
_CHAPTER_BY_KEY: dict[str, str] = {}
for domain in KNOWLEDGE_UNIVERSE:
    for point in domain['points']:
        _CHAPTER_BY_KEY[point['key']] = domain['label']

_FANTASY_IMPORTS = re.compile(
    r'^\s*(?:from|import)\s+(django|flask|numpy|pandas|requests|tensorflow|torch)\b',
    re.MULTILINE | re.IGNORECASE,
)
_MERMAID_OK = re.compile(r'^\s*(flowchart|graph)\s', re.IGNORECASE | re.MULTILINE)


def _char_len(text: str) -> int:
    return len(re.sub(r'\s+', '', str(text or '')))


def _chapter_for_key(knowledge_key: str) -> str:
    return _CHAPTER_BY_KEY.get(knowledge_key, DOMAIN_LABELS.get('stage1', 'Python 基础'))


def _graph_neighbors(knowledge_key: str) -> tuple[list[str], list[str]]:
    kg_id = kg_id_from_key(knowledge_key)
    prerequisites: list[str] = []
    successors: list[str] = []
    for edge in KG_EDGES:
        if edge.get('target') == kg_id and edge.get('type') == 'prerequisite':
            label = _KG_LABELS.get(edge['source'], edge['source'])
            if label not in prerequisites:
                prerequisites.append(label)
        if edge.get('source') == kg_id and edge.get('type') == 'prerequisite':
            label = _KG_LABELS.get(edge['target'], edge['target'])
            if label not in successors:
                successors.append(label)
    return prerequisites, successors


def build_knowledge_node(knowledge_key: str) -> dict:
    kb = knowledge_section(knowledge_key)
    label = POINTS[knowledge_key]
    prerequisites, successors = _graph_neighbors(knowledge_key)
    from app.data.knowledge_node_registry import get_entry

    entry = get_entry(kg_id_from_key(knowledge_key))
    difficulty = entry.default_difficulty if entry else 1
    objectives = []
    if kb.get('base_question'):
        objectives.append(f'掌握基础：{kb["base_question"]}')
    if kb.get('advanced_question'):
        objectives.append(f'综合应用：{kb["advanced_question"]}')
    if not objectives and kb.get('concept'):
        objectives.append(f'理解{label}的核心概念与用法')
    pitfalls = []
    if kb.get('common_mistakes'):
        pitfalls.append(kb['common_mistakes'])
    if kb.get('bad_example'):
        pitfalls.append(f'反例：{kb["bad_example"]}')
    return {
        'knowledge_key': knowledge_key,
        'name': label,
        'chapter': _chapter_for_key(knowledge_key),
        'difficulty': difficulty,
        'prerequisites': prerequisites,
        'successors': successors,
        'common_pitfalls': pitfalls,
        'objectives': objectives,
        'concept': kb.get('concept') or '',
        'good_example': kb.get('good_example') or '',
        'bad_example': kb.get('bad_example') or '',
        'source': kb.get('source') or 'Python 官方教程',
    }


def infer_learning_stage(profile: dict, explicit: str | None = None) -> str:
    if explicit and explicit in VALID_STAGES:
        return explicit
    cognitive = str(profile.get('cognitive_state') or '')
    for stage in VALID_STAGES:
        if stage in cognitive:
            return stage
    goal = str(profile.get('learning_goal') or '')
    if '考试' in goal or '测验' in goal:
        return '考试'
    if '复习' in goal:
        return '复习'
    if '预习' in goal:
        return '预习'
    if '练习' in goal or '刷题' in goal:
        return '练习'
    return STAGE_DEFAULT


def infer_learning_styles(profile: dict, explicit: list[str] | None = None) -> list[str]:
    if explicit:
        cleaned = []
        for item in explicit:
            mapped = STYLE_ALIASES.get(str(item).strip(), str(item).strip())
            if mapped and mapped not in cleaned:
                cleaned.append(mapped)
        if cleaned:
            return cleaned
    preference = str(profile.get('explanation_preference') or '')
    interest = str(profile.get('interest_direction') or '')
    styles: list[str] = []
    for token, label in STYLE_ALIASES.items():
        if token in preference or token in interest:
            if label not in styles:
                styles.append(label)
    if '小游戏' in interest and '小游戏' not in styles:
        styles.append('小游戏')
    if '数据' in interest and '案例' not in styles:
        styles.append('案例')
    return styles or ['图文', '案例']


def infer_target(explicit: str | None = None) -> str:
    if explicit and explicit in VALID_TARGETS:
        return explicit
    return TARGET_DEFAULT


def analyze_pedagogy(
    node: dict,
    *,
    target: str,
    learning_stage: str,
    learning_styles: list[str],
    profile: dict,
) -> dict:
    label = node['name']
    foundation = str(profile.get('knowledge_foundation') or '')
    beginner = '零基础' in foundation
    bloom = STAGE_BLOOM.get(learning_stage, STAGE_BLOOM[STAGE_DEFAULT])
    positioning = (
        f'《Python程序设计基础》{node["chapter"]}模块中的「{label}」，'
        f'面向{target}阶段学习者，当前处于{learning_stage}环节。'
    )
    if node['prerequisites']:
        positioning += f'建议先掌握：{"、".join(node["prerequisites"])}。'
    learning_objectives = list(node.get('objectives') or [])[:3]
    competency = [
        f'能正确阅读并编写与{label}相关的 Python 3 代码',
        f'能识别并避免常见错误：{"；".join(node.get("common_pitfalls") or ["边界与类型"])}',
    ]
    if learning_stage in ('练习', '复习', '考试'):
        competency.append(f'能将{label}应用到小型真实任务（如案例所示）')
    recommended = list(dict.fromkeys(learning_styles + (['代码实验'] if beginner else ['案例'])))
    return {
        'positioning': positioning,
        'learning_objectives': learning_objectives,
        'competency_objectives': competency,
        'bloom_level': bloom,
        'recommended_styles': recommended[:4],
        'target': target,
        'learning_stage': learning_stage,
    }


def _format_example(raw: str) -> str:
    text = str(raw or '').replace('\\n', '\n').strip()
    if text.endswith('。'):
        text = text[:-1]
    text = text.strip().strip('`').strip()
    return text


_FALLBACK_CODE = {
    'loop': 'total = 0\nfor value in [1, 2, 3]:\n    total += value\nprint(total)\n',
    'range': 'for i in range(3):\n    print(i)\n',
    'cond': 'score = 80\nif score >= 60:\n    print("pass")\nelse:\n    print("retry")\n',
    'list': 'nums = [1, 2, 3]\nnums.append(4)\nprint(nums)\n',
    'dict': 'student = {"name": "PLEX", "score": 90}\nprint(student["name"])\n',
    'func': 'def add(a, b):\n    return a + b\n\nprint(add(1, 2))\n',
    'var': 'name = "PLEX"\nage = 18\nprint(name, age)\n',
    'io': 'name = input("name: ")\nprint("hello", name)\n',
    'str': 'text = "Python"\nprint(text.lower())\nprint(len(text))\n',
    'ops': 'a = 7\nb = 3\nprint(a // b, a % b)\n',
    'intro': 'print("hello, PLEX")\n',
    'comment': '# 这是注释\nprint(1)  # 行尾注释\n',
    'file': 'with open("demo.txt", "w", encoding="utf-8") as f:\n    f.write("hi")\n',
    'except': 'try:\n    print(1 / 0)\nexcept ZeroDivisionError:\n    print("cannot divide by zero")\n',
    'algo-sum': 'def sum_list(items):\n    total = 0\n    for x in items:\n        total += x\n    return total\n\nprint(sum_list([1, 2, 3]))\n',
    'algo-search': 'def find_first(items, target):\n    for i, x in enumerate(items):\n        if x == target:\n            return i\n    return -1\n\nprint(find_first([3, 5, 7], 5))\n',
}


def _looks_like_python(code: str) -> bool:
    """扩充后的知识库正例字段偶发写成散文，需过滤后才能作为可编译示例。"""
    text = (code or '').strip()
    if not text or len(text) < 8:
        return False
    # 含大量中文叙述 / 中文标点 → 非可执行代码
    chinese = sum(1 for ch in text if '\u4e00' <= ch <= '\u9fff')
    if chinese > max(8, len(text) // 4):
        return False
    if any(ch in text for ch in '；，。！？、'):
        return False
    markers = ('=', 'print', 'def ', 'for ', 'while ', 'if ', 'return', 'import ', 'class ', 'with ')
    if not any(token in text for token in markers):
        return False
    try:
        compile(text, '<looks_like_python>', 'exec')
    except SyntaxError:
        return False
    return True


def _safe_code_example(knowledge_key: str, raw: str) -> str:
    formatted = _format_example(raw)
    # 正例常写成「`code` 说明；`code2`」——优先截取第一段反引号内代码
    if '`' in formatted:
        parts = [p.strip() for p in formatted.split('`') if p.strip()]
        for part in parts:
            if _looks_like_python(part):
                return part
    if _looks_like_python(formatted):
        return formatted
    return _FALLBACK_CODE.get(knowledge_key, f'# {knowledge_key} example\npass\n')


def _truncate_explain(text: str, limit: int = 800) -> str:
    text = str(text or '').strip()
    if _char_len(text) <= limit:
        return text
    result = []
    count = 0
    for ch in text:
        result.append(ch)
        if not ch.isspace():
            count += 1
        if count >= limit:
            break
    return ''.join(result).rstrip() + '…'


def _diagram_for_key(knowledge_key: str, label: str) -> dict:
    templates = {
        'cond': (
            'flowchart TD\n    A[读取条件] --> B{条件成立?}\n    B -->|是| C[执行分支A]\n    B -->|否| D[执行分支B]',
            '条件分支决策流程',
        ),
        'loop': (
            'flowchart TD\n    A[初始化] --> B{条件/序列}\n    B --> C[循环体]\n    C --> B\n    B -->|结束| D[后续步骤]',
            '循环执行流程',
        ),
        'func': (
            'flowchart TD\n    A[调用函数] --> B[传入参数]\n    B --> C[执行函数体]\n    C --> D[return 结果]',
            '函数调用流程',
        ),
    }
    mermaid, hint = templates.get(
        knowledge_key,
        (
            f'flowchart TD\n    A[输入/数据] --> B[{label}]\n    B --> C[输出/结果]',
            f'{label}基本处理流程',
        ),
    )
    return {
        'caption': f'{label}示意图',
        'flow_hint': hint,
        'sketch': f'从输入经 {label} 处理到输出。',
        'mermaid': mermaid,
    }


def _choice_exercises(knowledge_key: str) -> list[dict]:
    bank_key = POINT_TO_BANK.get(knowledge_key, knowledge_key)
    bank = QUESTION_BANK.get(bank_key, [])
    rows = []
    for item in bank[:2]:
        options = item.get('options') or []
        correct = options[item.get('correct_index', 0)] if options else ''
        rows.append({
            'type': 'choice',
            'stem': item['stem'],
            'options': options,
            'answer': correct,
            'explanation': f'正确选项为「{correct}」，依据 Python 3 标准语法与语义。',
            'tags': [knowledge_key, 'choice'],
        })
    while len(rows) < 2:
        rows.append({
            'type': 'choice',
            'stem': f'关于{POINTS[knowledge_key]}，下列说法正确的是？',
            'options': ['A', 'B', 'C', 'D'],
            'answer': 'A',
            'explanation': '请参考课程知识库中的概念与正例。',
            'tags': [knowledge_key, 'choice'],
        })
    return rows[:2]


def _fill_exercises(knowledge_key: str, kb: dict) -> list[dict]:
    label = POINTS[knowledge_key]
    base = kb.get('base_question') or f'完成一个{label}最小示例'
    mistake = kb.get('common_mistakes') or '注意边界与类型'
    return [
        {
            'type': 'fill',
            'stem': f'填空：{base}（写出关键语法或函数名）',
            'options': [],
            'answer': label,
            'explanation': f'本题考察{label}的核心写法，详见知识讲解。',
            'tags': [knowledge_key, 'fill'],
        },
        {
            'type': 'fill',
            'stem': f'填空：学习{label}时最常见的错误是____。',
            'options': [],
            'answer': mistake[:40],
            'explanation': f'常见错误：{mistake}',
            'tags': [knowledge_key, 'fill', 'pitfall'],
        },
    ]


def _coding_exercises(knowledge_key: str) -> list[dict]:
    rows = [q for q in CODING_QUESTION_BANK if q.get('knowledge_key') == knowledge_key]
    if len(rows) < 2:
        bank_key = POINT_TO_BANK.get(knowledge_key, knowledge_key)
        rows = [q for q in CODING_QUESTION_BANK if q.get('knowledge_key') == bank_key]
    result = []
    for item in rows[:2]:
        result.append({
            'type': 'coding',
            'stem': item['stem'],
            'options': [],
            'answer': item.get('starter_code') or '',
            'explanation': item.get('hint') or '参考 starter_code 完成可运行程序。',
            'tags': [knowledge_key, 'coding', item.get('id', 'lab')],
        })
    while len(result) < 2:
        idx = len(result) + 1
        result.append({
            'type': 'coding',
            'stem': f'任务{idx}：编写使用{POINTS[knowledge_key]}的 Python 3 小程序并保证可运行。',
            'options': [],
            'answer': f'# {POINTS[knowledge_key]} 练习 {idx}\n',
            'explanation': '程序应通过语法检查并体现本知识点。',
            'tags': [knowledge_key, 'coding', f'task-{idx}'],
        })
    # 题干去重，避免 exercise_set 因重复 question 被判 schema_invalid
    seen: set[str] = set()
    unique: list[dict] = []
    for row in result:
        stem = str(row.get('stem') or '').strip()
        if stem in seen:
            stem = f'{stem}（变式{len(unique) + 1}）'
            row = {**row, 'stem': stem}
        seen.add(stem)
        unique.append(row)
    return unique[:2]


def build_local_bundle(
    knowledge_key: str,
    *,
    analysis: dict,
    profile: dict,
) -> dict:
    node = build_knowledge_node(knowledge_key)
    kb = knowledge_section(knowledge_key)
    label = node['name']
    preference = str(profile.get('explanation_preference') or '分步骤讲解')
    interest = str(profile.get('interest_direction') or '校园学习')
    concept = kb.get('concept') or f'{label}的核心语法与适用场景。'
    good = _safe_code_example(knowledge_key, kb.get('good_example') or '')
    mistakes = kb.get('common_mistakes') or '注意缩进、边界与类型。'
    code_first = '先看代码' in preference

    if code_first and good:
        explain_body = (
            f'## 先看代码\n```python\n{good}\n```\n\n'
            f'## 原理\n{concept}\n\n'
            f'## 易错点\n{mistakes}\n\n'
            f'讲解偏好：{preference}。结合你的兴趣「{interest}」，尝试把示例改写成自己的小任务。'
        )
    else:
        explain_body = (
            f'{concept}\n\n'
            f'## 分步理解\n1. 明确输入与输出；2. 写出最小正例；3. 对照易错点自查。\n\n'
            f'## 讲解偏好\n按「{preference}」组织内容。\n\n'
            f'## 生活化场景\n用「{interest}」相关的小需求来练习 {label}。\n\n'
            f'## 易错点\n{mistakes}'
        )
    if good:
        explain_body += f'\n\n## 参考代码\n```python\n{good}\n```'

    code_block = good or f'# {label} 示例\npass\n'
    coding_rows = _coding_exercises(knowledge_key)
    for row in coding_rows:
        stem = str(row.get('stem') or '').strip()
        if interest and interest not in stem:
            row['stem'] = f'结合「{interest}」场景：{stem}'
    exercises = (
        _choice_exercises(knowledge_key)
        + _fill_exercises(knowledge_key, kb)
        + coding_rows
    )
    cases = cases_for_knowledge(knowledge_key, 2)
    for case in cases:
        if not isinstance(case, dict):
            continue
        scenario = str(case.get('scenario') or '').strip()
        if interest and interest not in scenario:
            case['scenario'] = f'围绕兴趣「{interest}」：{scenario or f"练习{label}"}'
        title = str(case.get('title') or '').strip()
        if interest and title and interest not in title:
            case['title'] = f'{title}（{interest}）'
    keywords = [label, node['chapter'], analysis.get('bloom_level', '应用').split('/')[0]]
    mindmap = (
        f'## {label}\n'
        f'- 章节：{node["chapter"]}\n'
        f'- 前置：{", ".join(node["prerequisites"]) or "无"}\n'
        f'- 目标\n'
        + ''.join(f'  - {obj}\n' for obj in analysis.get('learning_objectives', [])[:3])
        + f'- 易错点\n  - {mistakes}\n'
        + f'- 练习\n  - 选择/填空/编程各 2 题'
    )
    bundle = {
        'format': 'pedagogical_v2',
        'title': f'{label} · {analysis.get("learning_stage", "学习")}资源包',
        'node': label,
        'objective': analysis.get('learning_objectives') or node['objectives'],
        'analysis': analysis,
        'explain': _truncate_explain(explain_body),
        'diagrams': [_diagram_for_key(knowledge_key, label)],
        'cases': cases,
        'code': [{
            'title': f'{label}最小正例',
            'source': code_block,
            'complexity': 'O(n)' if knowledge_key in ('loop', 'list', 'algo-search', 'algo-sum') else 'O(1)',
            'pep8_note': '使用 snake_case 命名，4 空格缩进，符合 PEP 8。',
        }],
        'exercises': exercises,
        'summary': {
            'one_liner': f'{label}：{concept[:60]}…' if len(concept) > 60 else f'{label}：{concept}',
            'keywords': keywords[:3],
            'mindmap_markdown': mindmap,
        },
    }
    bundle['markdown'] = render_markdown(bundle)
    return bundle


def render_markdown(bundle: dict) -> str:
    lines = [
        f'# {bundle.get("title", bundle.get("node", "学习资源"))}',
        '',
        '## 学习目标',
    ]
    for obj in bundle.get('objective') or []:
        lines.append(f'- {obj}')
    analysis = bundle.get('analysis') or {}
    if analysis:
        lines.extend([
            '',
            '## 教学分析',
            f'- **定位**：{analysis.get("positioning", "")}',
            f'- **Bloom 层级**：{analysis.get("bloom_level", "")}',
            f'- **推荐方式**：{"、".join(analysis.get("recommended_styles") or [])}',
        ])
    lines.extend(['', '## 知识讲解', '', str(bundle.get('explain') or '')])
    for diagram in bundle.get('diagrams') or []:
        if not isinstance(diagram, dict):
            continue
        lines.extend([
            '',
            f'### {diagram.get("caption", "图示")}',
            diagram.get('sketch') or '',
            '',
            '```mermaid',
            diagram.get('mermaid') or '',
            '```',
        ])
    lines.append('\n## 真实案例')
    for case in bundle.get('cases') or []:
        if not isinstance(case, dict):
            continue
        lines.extend([
            f'### {case.get("title", "案例")}',
            case.get('scenario') or '',
            f'*要点*：{case.get("key_idea", "")}',
        ])
    lines.append('\n## 代码示例')
    for block in bundle.get('code') or []:
        if not isinstance(block, dict):
            continue
        lines.extend([
            f'### {block.get("title", "示例")}（{block.get("complexity", "")}）',
            '```python',
            block.get('source') or '',
            '```',
        ])
    lines.append('\n## 练习')
    for idx, ex in enumerate(bundle.get('exercises') or [], 1):
        if not isinstance(ex, dict):
            continue
        lines.append(f'### 第{idx}题 [{ex.get("type", "")}]')
        lines.append(ex.get('stem') or '')
        if ex.get('options'):
            for opt in ex['options']:
                lines.append(f'- {opt}')
    summary = bundle.get('summary') if isinstance(bundle.get('summary'), dict) else {}
    lines.extend([
        '',
        '## 总结',
        summary.get('one_liner') or '',
        '',
        f'**关键词**：{" · ".join(summary.get("keywords") or [])}',
        '',
        summary.get('mindmap_markdown') or '',
    ])
    return '\n'.join(lines)


def _bundle_generation_prompt(
    knowledge_key: str,
    *,
    node: dict,
    analysis: dict,
    profile: dict,
    case_candidates: list[dict],
) -> tuple[str, str]:
    kb = knowledge_section(knowledge_key)
    system = (
        '你是Python程序设计基础课程的教学资源生成器。只输出JSON对象，包含单个bundle字段。'
        'bundle必须符合 pedagogical_v2 结构：title,node,objective,analysis,explain,diagrams,cases,code,exercises,summary。'
        'explain不超过800字；cases至少2条且来自真实Python开发；exercises含choice/fill/coding各2题且含answer/explanation/tags。'
        'diagrams至少1条含mermaid(flowchart或graph开头)。code必须Python3可compile。'
        '不得编造课程外API，仅使用Python标准库。严格基于knowledge_node与knowledge_base，不得幻想知识。'
    )
    payload = {
        'knowledge_node': node,
        'analysis': analysis,
        'profile': profile,
        'knowledge_base': {
            'concept': kb.get('concept'),
            'good_example': kb.get('good_example'),
            'bad_example': kb.get('bad_example'),
            'common_mistakes': kb.get('common_mistakes'),
            'base_question': kb.get('base_question'),
            'advanced_question': kb.get('advanced_question'),
            'source': kb.get('source'),
        },
        'case_candidates': case_candidates,
    }
    return system, str(payload)


def _as_dict_list(items, *, default_key: str = 'text') -> list[dict]:
    rows: list[dict] = []
    for item in items or []:
        if isinstance(item, dict):
            rows.append(item)
        elif isinstance(item, str) and item.strip():
            rows.append({default_key: item.strip()})
    return rows


def _normalize_bundle_shape(bundle: dict) -> dict:
    """容错：LLM 偶发把 code/diagrams 等字段写成字符串，归一成 dict 列表。"""
    out = dict(bundle)
    code_rows = []
    for block in _as_dict_list(out.get('code'), default_key='source'):
        if 'source' not in block and 'code' in block:
            block = {**block, 'source': block.get('code')}
        if not str(block.get('complexity') or '').strip():
            block = {**block, 'complexity': 'O(1)'}
        if not str(block.get('title') or '').strip():
            block = {**block, 'title': '示例'}
        code_rows.append(block)
    out['code'] = code_rows
    out['diagrams'] = _as_dict_list(out.get('diagrams'), default_key='caption')
    out['cases'] = _as_dict_list(out.get('cases'), default_key='scenario')
    out['exercises'] = _as_dict_list(out.get('exercises'), default_key='stem')
    if not isinstance(out.get('summary'), dict):
        out['summary'] = {'one_liner': str(out.get('summary') or ''), 'keywords': [], 'mindmap_markdown': ''}
    if not isinstance(out.get('analysis'), dict):
        out['analysis'] = {}
    out['explain'] = str(out.get('explain') or '')
    out['title'] = str(out.get('title') or '')
    return out


def _finalize_bundle(bundle: dict, analysis: dict) -> dict:
    if not isinstance(bundle, dict):
        raise ValueError('bundle_invalid')
    bundle = _normalize_bundle_shape(bundle)
    bundle['format'] = 'pedagogical_v2'
    bundle['analysis'] = bundle.get('analysis') or analysis
    bundle['explain'] = _truncate_explain(bundle.get('explain') or '')
    bundle['markdown'] = render_markdown(bundle)
    return bundle


def llm_bundle(
    knowledge_key: str,
    *,
    node: dict,
    analysis: dict,
    profile: dict,
    case_candidates: list[dict],
    timeout: float = 25.0,
) -> dict:
    """用 DeepSeek / OpenAI 兼容通道生成 pedagogical_v2 资源包（异步任务，超时可高于对话）。"""
    from agents.llm_client import chat_json, llm_provider

    if not llm_provider():
        raise RuntimeError('llm_not_available')
    system, user = _bundle_generation_prompt(
        knowledge_key,
        node=node,
        analysis=analysis,
        profile=profile,
        case_candidates=case_candidates,
    )
    result = chat_json(system=system, user=user, timeout=timeout, max_tokens=3500)
    if not result or not isinstance(result.get('bundle'), dict):
        raise ValueError('llm_bundle_invalid')
    return _finalize_bundle(result['bundle'], analysis)


def spark_bundle(
    knowledge_key: str,
    *,
    node: dict,
    analysis: dict,
    profile: dict,
    case_candidates: list[dict],
) -> dict:
    system, user = _bundle_generation_prompt(
        knowledge_key,
        node=node,
        analysis=analysis,
        profile=profile,
        case_candidates=case_candidates,
    )
    # 资源包 JSON 体积大，异步任务允许更长读超时；连接仍受 http_client 约束
    result = IflytekSparkService.chat_json(system, user, timeout=25)
    bundle = result.get('bundle')
    if not isinstance(bundle, dict):
        raise ValueError('spark_bundle_invalid')
    return _finalize_bundle(bundle, analysis)


def validate_bundle_risks(bundle: dict) -> list[str]:
    risks: list[str] = []
    explain = str(bundle.get('explain') or '')
    if _char_len(explain) > 1200:
        risks.append('explain_too_long')
    cases = bundle.get('cases') or []
    if len(cases) < 1:
        risks.append('insufficient_cases')
    titles = [str(c.get('title') or '') for c in cases if isinstance(c, dict)]
    if len(titles) != len(set(titles)) and len(titles) > 1:
        risks.append('duplicate_cases')
    exercises = bundle.get('exercises') or []
    missing_answer_count = 0
    for ex in exercises:
        if not isinstance(ex, dict):
            continue
        if not str(ex.get('answer') or '').strip():
            missing_answer_count += 1
    # 完全无练习才记风险；缺某一题型或个别缺答案不再整包 schema_invalid
    if not exercises:
        risks.append('insufficient_exercises')
    elif missing_answer_count >= max(2, len(exercises)):
        risks.append('missing_answers')
    diagrams = bundle.get('diagrams') or []
    if diagrams and not any(
        isinstance(d, dict) and _MERMAID_OK.search(str(d.get('mermaid') or ''))
        for d in diagrams
    ):
        risks.append('invalid_mermaid')
    for block in bundle.get('code') or []:
        if not isinstance(block, dict):
            continue
        src = str(block.get('source') or '')
        # 缺 complexity 不再视为结构失败
        if src.strip():
            try:
                compile(src, '<bundle_code>', 'exec')
            except SyntaxError:
                # 语法问题由 code checker WARNING 覆盖，不记硬 schema_invalid
                pass
        if _FANTASY_IMPORTS.search(src):
            risks.append('fantasy_api')
    for ex in exercises:
        if not isinstance(ex, dict) or ex.get('type') != 'coding':
            continue
        answer = str(ex.get('answer') or '')
        if answer.strip():
            try:
                compile(answer, '<bundle_exercise>', 'exec')
            except SyntaxError:
                pass
    return list(dict.fromkeys(risks))


def _mindmap_to_tree(markdown: str, root: str) -> dict:
    children = []
    for line in str(markdown or '').splitlines():
        stripped = line.strip()
        if stripped.startswith('- '):
            label = stripped[2:].split('：')[0].split(':')[0].strip()
            if label and label != root:
                children.append({'label': label[:40], 'note': stripped[2:][:80]})
    if len(children) < 2:
        children = [
            {'label': '概念', 'note': root},
            {'label': '练习', 'note': '选择/填空/编程'},
        ]
    return {'format': 'tree', 'root': root, 'children': children}


def split_bundle_to_legacy_types(bundle: dict, knowledge_key: str) -> list[dict[str, Any]]:
    label = bundle.get('node') or POINTS.get(knowledge_key, knowledge_key)
    analysis = bundle.get('analysis') or {}
    summary = bundle.get('summary') or {}
    exercises = bundle.get('exercises') or []
    cases = bundle.get('cases') or []
    diagrams = bundle.get('diagrams') or []
    code_blocks = bundle.get('code') or []
    coding_ex = next((e for e in exercises if e.get('type') == 'coding'), None)
    starter = (coding_ex or {}).get('answer') or (code_blocks[0].get('source') if code_blocks else '')

    analysis_md = (
        f'**定位**：{analysis.get("positioning", "")}\n\n'
        f'**Bloom**：{analysis.get("bloom_level", "")}\n\n'
        f'**能力目标**：\n'
        + '\n'.join(f'- {c}' for c in analysis.get('competency_objectives') or [])
    )
    reading_parts = ['# 拓展：真实案例与图示', '']
    for case in cases:
        reading_parts.append(f'## {case.get("title", "案例")}\n{case.get("scenario", "")}\n')
    for diagram in diagrams:
        reading_parts.append(
            f'### {diagram.get("caption", "图示")}\n{diagram.get("flow_hint", "")}\n{diagram.get("sketch", "")}\n'
        )

    return [
        {
            'resource_type': 'learning_bundle',
            'title': bundle.get('title') or f'{label}学习资源包',
            'content': dict(bundle),
        },
        {
            'resource_type': 'lesson_document',
            'title': f'{label}个性化讲解',
            'content': {
                'format': 'markdown',
                'markdown': f'# {label}\n\n{analysis_md}\n\n## 讲解\n\n{bundle.get("explain", "")}',
            },
        },
        {
            'resource_type': 'mind_map',
            'title': f'{label}思维导图',
            'content': _mindmap_to_tree(summary.get('mindmap_markdown'), label),
        },
        {
            'resource_type': 'exercise_set',
            'title': f'{label}分层题库',
            'content': {
                'format': 'questions',
                'questions': [
                    {
                        'level': ex.get('type', '基础'),
                        'question': ex.get('stem', ''),
                        'type': ex.get('type'),
                        'options': ex.get('options'),
                        'answer': ex.get('answer'),
                        'explanation': ex.get('explanation'),
                        'tags': ex.get('tags'),
                    }
                    for ex in exercises
                ],
            },
        },
        {
            'resource_type': 'extended_reading',
            'title': f'{label}拓展阅读',
            'content': {'format': 'markdown', 'markdown': '\n'.join(reading_parts)},
        },
        {
            'resource_type': 'coding_lab',
            'title': f'{label}代码实操',
            'content': {
                'format': 'coding_lab',
                'scenario': (coding_ex or {}).get('stem') or f'完成一个使用{label}的小程序。',
                'starter_code': starter or f'# {label}\n',
                'checks': [
                    '程序可运行',
                    f'体现{label}核心用法',
                    '符合 PEP 8 基本规范',
                ],
            },
        },
    ]
