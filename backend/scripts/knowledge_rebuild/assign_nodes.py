# -*- coding: utf-8 -*-
"""把清洗后的每道题挂到 8 大类 / 26 个知识点节点上。

判定顺序：

1. **代码特征（最可信）** —— 对参考答案 / 起始代码做 Python AST 解析，看它实际
   用了什么语法结构（递归、嵌套循环、列表、字符串方法、while、break…）。
   题面可能写得含糊，但代码不会撒谎，所以 AST 特征给最高权重。
2. **题面关键词** —— 中文关键词与节点的对应表，权重次之。
3. **旧 knowledge_key / concept 分组** —— 作为先验，权重最低（旧分组只有 7 类，
   粒度比新的 26 节点粗，只能定"大类"不能定"节点"）。

三路得分相加后取最高分的节点。当出现下列情况之一时转 DeepSeek 判定：
- 最高分为 0（完全没有匹配到任何特征）
- 最高分与次高分的差距 < AMBIGUOUS_MARGIN（两个节点难分伯仲）

**所有走 AI 判定的题目都会被标记 needs_review=1**，因为 AI 的归类只是建议，
需要老师确认。规则判定的不标记。

用法：
    python scripts/knowledge_rebuild/assign_nodes.py            # 规则 + AI
    python scripts/knowledge_rebuild/assign_nodes.py --no-ai    # 只用规则（歧义项落到大类默认节点并标记复核）
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.data.knowledge_node_registry import (  # noqa: E402
    KNOWLEDGE_DOMAINS,
    KNOWLEDGE_NODE_REGISTRY,
    LEGACY_KEY_TO_NODE,
    get_entry,
    nodes_for_domain,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai_client  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / 'output'
INPUT_PATH = OUTPUT_DIR / 'cleaned_questions.json'
OUTPUT_PATH = OUTPUT_DIR / 'assigned_questions.json'

AMBIGUOUS_MARGIN = 3
AI_BATCH_SIZE = 10

ALL_NODE_IDS = [e.kg_id for e in KNOWLEDGE_NODE_REGISTRY]
NODE_TO_DOMAIN = {e.kg_id: e.domain_key for e in KNOWLEDGE_NODE_REGISTRY}
DOMAIN_DEFAULT_NODE = {d.key: nodes_for_domain(d.key)[0].kg_id for d in KNOWLEDGE_DOMAINS}

# 旧题库的 A-G concept_group 本身就是按教学主题分好的（A Basics / B Operators /
# C Conditionals / D Loops / E Functions / F DataTypes / G HighTypes），是判定
# **大类**最可靠的依据；具体落到大类下的哪个节点，仍由代码特征与关键词决定。
LEGACY_GROUP_TO_DOMAIN = {
    'A': 'lang-basics',
    'B': 'sequence',
    'C': 'branch',
    'D': 'loop',
    'E': 'function',
    'F': 'sequence',
    'G': 'string',
}
LEGACY_GROUP_DOMAIN_BONUS = 12

# 旧库里 F 组 DataTypes 专讲类型转换，可以直接锚到节点而不只是大类
LEGACY_CONCEPT_TO_NODE = {
    'datatypes': 'seq-type',
    'hightypes': 'array-basic',
}

# 前端静态题的 topic 是人工标注的，粒度刚好等于新节点，直接采信
FRONTEND_TOPIC_TO_NODE = {
    'print 与字符串': 'lang-print',
    'print 多行': 'lang-print',
    'print 与变量': 'lang-print',
    'print 与表达式': 'seq-arith',
    '变量与算术': 'seq-arith',
    '变量与减法': 'seq-arith',
    '变量与乘法': 'seq-arith',
    '变量与整除': 'seq-type',
    '条件分支': 'branch-if',
    'for 循环': 'loop-for',
    '列表索引': 'array-basic',
    '列表与内置函数': 'array-traverse',
    '列表与循环': 'array-traverse',
    '函数定义': 'func-define',
    '二分查找': 'search-binary',
    '冒泡排序': 'search-sort',
    '选择排序': 'search-sort',
    '综合：函数与循环': 'func-param',
    '综合：条件与循环': 'loop-control',
}
FRONTEND_TOPIC_BONUS = 20

# ---- 题面关键词 → 节点，按区分度分三档 ----
# A 档：只可能属于该节点的专有名词，权重最高，足以压过通用代码特征。
#      （例如"冒泡排序"一定是排序题，哪怕它也用了嵌套循环和函数定义）
# B 档：强指向但仍可能被其他节点共享。
# C 档：泛化词，只作为微弱倾向。
KEYWORDS_TIER_A: dict[str, tuple[str, ...]] = {
    'func-recursion': ('递归', '自己调用自己', '斐波那契', '汉诺塔'),
    'search-binary': ('二分', '折半'),
    'search-sort': ('冒泡', '选择排序', '排序算法', '交换排序'),
    'array-2d': ('二维', '矩阵', '行列'),
    'string-scan': ('回文', '元音', '统计字符', '字符出现', '逐个字符'),
    'loop-control': ('break', 'continue', '跳出循环', '跳过本轮'),
    'string-method': ('split', 'join', 'replace', 'strip', 'upper', 'lower',
                      '删除空格', '去除空格', '转大写', '转小写', '字符串方法'),
    'branch-elif': ('elif', '多分支', '等第', '等级', '分档'),
    'branch-nested': ('嵌套条件', '嵌套判断', '复合条件', '嵌套 if'),
    'loop-nested': ('嵌套循环', '双重循环', '乘法表', '方阵', '平行四边形'),
    'func-param': ('返回值', '形参', '实参', '函数参数'),
    # 注意：旧题库几乎每道题的题面都以"用户输入…"开头（那是旧 OJ 的固定行文，
    # 不代表考点是输入），所以这里只收真正以输入/文件读取本身为考点的说法。
    'lang-input': ('input() 函数', '文件读取', '异常处理', 'try-except'),
    'seq-expr': ('优先级', '四则运算', '运算符'),
    'seq-type': ('类型转换', '四舍五入', '保留小数', '开平方', '平方根'),
    'array-traverse': ('遍历列表', '列表元素', '数组元素', '列表中所有'),
}

KEYWORDS_TIER_B: dict[str, tuple[str, ...]] = {
    'lang-print': ('打招呼', '问候', '注释', '输出一句', '欢迎'),
    'lang-var': ('变量名', '合法的变量', '布尔', '变量与类型'),
    'seq-arith': ('面积', '平均', '总分', '摄氏', '华氏', '温度转换', '速度', 'bmi', '周长'),
    'branch-if': ('较大值', '较小值', '奇偶', '二选一', 'if-else'),
    'loop-while': ('while', '直到', '反复', '不断'),
    'loop-for': ('倍数', '阶乘', '从 a 加到', 'for 循环'),
    'array-basic': ('列表', '数组', '下标', '元组', '集合', '字典'),
    'string-index': ('切片', '子串', '反转', '第几个字符'),
    'func-define': ('定义函数', '编写函数', '定义一个函数'),
    'search-linear': ('查找', '搜索', '是否存在'),
    'search-stat': ('最大值', '最小值', '出现次数', '去重', '计数'),
    'string-scan': ('字符个数',),
    'search-sort': ('升序', '降序', '从小到大', '排序'),
}

KEYWORDS_TIER_C: dict[str, tuple[str, ...]] = {
    'lang-print': ('hello', 'print'),
    'seq-arith': ('求和', '相加', '计算'),
    'branch-if': ('判断', '是否'),
    'loop-for': ('循环', '重复', '累加'),
    'search-linear': ('寻找', '找出'),
    'search-stat': ('统计', '个数'),
    'string-index': ('字符串',),
    'func-define': ('函数',),
}

TIER_WEIGHTS = {'A': 22, 'B': 9, 'C': 4}

# 命中 A 档关键词时，压制这些容易"抢题"的通用节点：一道冒泡排序题即便用了
# 嵌套循环和函数定义，它的教学定位仍是排序，而不是"嵌套循环"或"定义与调用"。
TIER_A_SUPPRESS: dict[str, tuple[str, ...]] = {
    'func-recursion': ('func-define', 'func-param', 'loop-for'),
    'search-binary': ('loop-while', 'loop-for', 'func-define', 'array-basic'),
    'search-sort': ('loop-nested', 'loop-for', 'func-define', 'array-basic', 'array-traverse'),
    'array-2d': ('loop-nested', 'array-basic'),
    'string-scan': ('loop-for', 'func-define', 'string-index'),
    'string-method': ('string-index', 'func-define'),
    'loop-control': ('loop-for', 'loop-while'),
    'branch-elif': ('branch-if',),
    'branch-nested': ('branch-if',),
    'loop-nested': ('loop-for',),
    'array-traverse': ('array-basic', 'loop-for'),
    'func-param': ('func-define',),
}


class CodeFeatures:
    """参考答案 / 起始代码的 AST 特征。解析失败时全部为 False（不猜）。"""

    __slots__ = (
        'parsed', 'has_def', 'is_recursive', 'has_for', 'has_while', 'has_nested_loop',
        'has_break_continue', 'has_if', 'has_elif', 'has_nested_if', 'has_list_literal',
        'has_list_ops', 'has_2d_list', 'has_str_method', 'has_str_iter', 'has_input',
        'has_range', 'has_cast', 'has_arith', 'has_sum_count', 'has_sort', 'has_slice',
        'only_print', 'has_param_return',
    )

    STR_METHODS = {'split', 'join', 'replace', 'strip', 'upper', 'lower', 'find', 'startswith',
                   'endswith', 'count', 'lstrip', 'rstrip', 'title', 'isdigit', 'isalpha'}
    LIST_METHODS = {'append', 'extend', 'insert', 'remove', 'pop', 'index', 'sort', 'reverse'}

    def __init__(self, code: str | None):
        for slot in self.__slots__:
            setattr(self, slot, False)
        if not code or not code.strip():
            return
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return
        self.parsed = True

        func_names: set[str] = set()
        called_names: set[str] = set()
        statements = 0
        print_calls = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self.has_def = True
                func_names.add(node.name)
                returns_value = False
                for inner in ast.walk(node):
                    if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) \
                            and inner.func.id == node.name:
                        self.is_recursive = True
                    if isinstance(inner, ast.Return) and inner.value is not None:
                        returns_value = True
                # 「参数与返回值」的判据：函数既接收参数又返回结果，
                # 而不是只靠 def 关键字——那样所有算法题都会被算成函数题。
                if node.args.args and returns_value:
                    self.has_param_return = True
            elif isinstance(node, ast.For):
                self.has_for = True
                if any(isinstance(child, (ast.For, ast.While)) for child in ast.walk(node) if child is not node):
                    self.has_nested_loop = True
                if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) \
                        and node.iter.func.id == 'range':
                    self.has_range = True
            elif isinstance(node, ast.While):
                self.has_while = True
                if any(isinstance(child, (ast.For, ast.While)) for child in ast.walk(node) if child is not node):
                    self.has_nested_loop = True
            elif isinstance(node, (ast.Break, ast.Continue)):
                self.has_break_continue = True
            elif isinstance(node, ast.If):
                self.has_if = True
                if node.orelse:
                    # elif 在 AST 里表现为 orelse 中只有一个 If
                    if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                        self.has_elif = True
                if any(isinstance(child, ast.If) for child in ast.walk(node) if child is not node):
                    self.has_nested_if = True
            elif isinstance(node, ast.List):
                self.has_list_literal = True
                if any(isinstance(elt, ast.List) for elt in node.elts):
                    self.has_2d_list = True
            elif isinstance(node, ast.Subscript):
                if isinstance(node.slice, ast.Slice):
                    self.has_slice = True
            elif isinstance(node, ast.BinOp):
                if isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
                                        ast.Mod, ast.Pow)):
                    self.has_arith = True
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    called_names.add(func.id)
                    if func.id == 'input':
                        self.has_input = True
                    elif func.id == 'print':
                        print_calls += 1
                    elif func.id in {'int', 'float', 'str', 'bool', 'round'}:
                        self.has_cast = True
                    elif func.id in {'sum', 'len', 'max', 'min', 'count'}:
                        self.has_sum_count = True
                    elif func.id in {'sorted', 'list', 'set'}:
                        self.has_sort = func.id == 'sorted'
                        if func.id in {'list', 'set'}:
                            self.has_list_ops = True
                    elif func.id == 'range':
                        self.has_range = True
                elif isinstance(func, ast.Attribute):
                    if func.attr in self.STR_METHODS:
                        self.has_str_method = True
                    if func.attr in self.LIST_METHODS:
                        self.has_list_ops = True
                        if func.attr == 'sort':
                            self.has_sort = True
            if isinstance(node, ast.stmt):
                statements += 1

        # for ch in <字符串变量>：粗略判定为字符串遍历（迭代对象不是 range/列表字面量）
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name):
                self.has_str_iter = True

        # 「只有 print」要求输出的全是字面量：print(a - b) 的考点是算术而不是输出，
        # 不能因为整个程序只有一行 print 就判成 print 教学题。
        prints_literals_only = True
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'print':
                for arg in node.args:
                    if not isinstance(arg, ast.Constant):
                        prints_literals_only = False
        self.only_print = (
            print_calls > 0
            and prints_literals_only
            and statements <= print_calls + 1
            and not (self.has_for or self.has_while or self.has_if or self.has_def or self.has_input)
        )


# ---- 代码特征 → 节点加分（权重 10，最可信）----
def code_scores(f: CodeFeatures) -> Counter:
    score = Counter()
    if not f.parsed:
        return score
    if f.is_recursive:
        score['func-recursion'] += 24
    if f.has_param_return and not f.is_recursive:
        score['func-param'] += 9
    if f.has_def and not f.is_recursive:
        # def 本身区分度很低（大量算法题都会封装成函数），只给弱倾向
        score['func-define'] += 5
    if f.has_2d_list:
        score['array-2d'] += 18
    if f.has_list_ops or f.has_list_literal:
        score['array-basic'] += 8
        if f.has_for:
            score['array-traverse'] += 8
    if f.has_str_method:
        score['string-method'] += 14
    if f.has_slice:
        score['string-index'] += 10
    if f.has_sort:
        score['search-sort'] += 10
    if f.has_nested_loop:
        score['loop-nested'] += 14
    if f.has_break_continue:
        score['loop-control'] += 12
    if f.has_while and not f.has_nested_loop:
        score['loop-while'] += 10
    if f.has_for and f.has_range and not f.has_nested_loop:
        score['loop-for'] += 8
    if f.has_nested_if:
        score['branch-nested'] += 10
    if f.has_elif:
        score['branch-elif'] += 12
    if f.has_if and not (f.has_elif or f.has_nested_if):
        score['branch-if'] += 8
    # 旧题库几乎所有题都用 input() 读数据，所以只有当程序"基本上就是读一个输入
    # 再原样输出"时，考点才真的是输入本身。
    if f.has_input and not (f.has_for or f.has_while or f.has_if or f.has_def
                            or f.has_arith or f.has_list_ops or f.has_str_method):
        score['lang-input'] += 8
    if f.has_cast:
        score['seq-type'] += 6
    if f.has_arith and not (f.has_for or f.has_while or f.has_def):
        score['seq-arith'] += 6
    if f.has_sum_count:
        score['search-stat'] += 4
    if f.only_print:
        score['lang-print'] += 14
    return score


def stem_scores(text: str) -> Counter:
    score = Counter()
    lowered = text.lower()
    hit_tier_a: list[str] = []

    for tier, table in (('A', KEYWORDS_TIER_A), ('B', KEYWORDS_TIER_B), ('C', KEYWORDS_TIER_C)):
        for node_id, keywords in table.items():
            if any(keyword.lower() in lowered for keyword in keywords):
                score[node_id] += TIER_WEIGHTS[tier]
                if tier == 'A':
                    hit_tier_a.append(node_id)

    for node_id in hit_tier_a:
        for suppressed in TIER_A_SUPPRESS.get(node_id, ()):
            if suppressed not in hit_tier_a:
                score[suppressed] -= 12
    return score


def legacy_scores(record: dict) -> Counter:
    score = Counter()

    # 前端静态题的 topic 标注粒度与新节点一致，直接采信
    topic_node = FRONTEND_TOPIC_TO_NODE.get(record.get('frontend_topic') or '')
    if topic_node:
        score[topic_node] += FRONTEND_TOPIC_BONUS

    key = (record.get('legacy_knowledge_key') or '').lower()
    if key:
        node_id = LEGACY_KEY_TO_NODE.get(key)
        if node_id:
            # 选择题没有代码可分析，旧 key 是唯一可靠信号，权重给足
            score[node_id] += 12 if record.get('question_type') == 'mcq' else 5

    concept_node = LEGACY_CONCEPT_TO_NODE.get((record.get('legacy_concept') or '').lower())
    if concept_node:
        score[concept_node] += 14

    group = record.get('legacy_concept_group')
    domain = LEGACY_GROUP_TO_DOMAIN.get(group) if group else None
    if domain:
        # 整个大类等量抬升：锚定大类，但不干扰大类内部各节点的相对排序
        for entry in nodes_for_domain(domain):
            score[entry.kg_id] += LEGACY_GROUP_DOMAIN_BONUS
    return score


def rule_assign(record: dict) -> tuple[str | None, int, int, dict]:
    """返回 (节点 id, 最高分, 与次高分的差距, 得分明细)。"""
    code = record.get('reference_answer') or record.get('starter_code') or ''
    features = CodeFeatures(code)
    text_parts = [
        record.get('stem') or '',
        record.get('title_cn') or '',
        record.get('legacy_concept') or '',
        ' '.join(record.get('frontend_tags') or []),
        record.get('frontend_topic') or '',
        ' '.join(str(o) for o in (record.get('options') or [])),
        record.get('hint') or '',
    ]
    combined = Counter()
    cs = code_scores(features)
    ss = stem_scores(' '.join(text_parts))
    ls = legacy_scores(record)
    for part in (cs, ss, ls):
        combined.update(part)

    if not combined:
        return None, 0, 0, {'code': dict(cs), 'stem': dict(ss), 'legacy': dict(ls)}

    ranked = combined.most_common()
    top_id, top_score = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0
    return top_id, top_score, top_score - runner_up, {'code': dict(cs), 'stem': dict(ss), 'legacy': dict(ls)}


def build_ai_catalog() -> str:
    lines = []
    for domain in KNOWLEDGE_DOMAINS:
        node_desc = '; '.join(
            f'{e.kg_id}={e.label}（{e.summary}）' for e in nodes_for_domain(domain.key)
        )
        lines.append(f'- 大类「{domain.title}」: {node_desc}')
    return '\n'.join(lines)


AI_SYSTEM = (
    '你是 Python 入门课程的教研老师。你的任务是把题目归类到给定的知识点节点上。'
    '只能从给定的节点 id 里选择，不要发明新的 id。'
    '严格输出 JSON 数组，不要任何解释文字。'
)


def ai_assign(records: list[dict], catalog: str) -> dict[str, str]:
    """批量让 AI 判定归属，返回 {source_ref: node_id}。"""
    result: dict[str, str] = {}
    for start in range(0, len(records), AI_BATCH_SIZE):
        batch = records[start:start + AI_BATCH_SIZE]
        items = []
        for record in batch:
            items.append({
                'ref': record['source_ref'],
                'type': record['question_type'],
                'title': (record.get('title_cn') or '')[:60],
                'stem': re.sub(r'\s+', ' ', (record.get('stem') or ''))[:400],
                'code': (record.get('reference_answer') or record.get('starter_code') or '')[:400],
            })
        user = (
            f'可选知识点节点：\n{catalog}\n\n'
            '请为下列每道题选择最贴切的一个节点 id。判断依据优先看题目实际考察的语法结构。\n'
            f'题目列表（JSON）：\n{json.dumps(items, ensure_ascii=False)}\n\n'
            '输出格式：[{"ref": "...", "node_id": "..."}]'
        )
        print(f'    [AI] 判定第 {start + 1}-{start + len(batch)} 题 ...')
        parsed = ai_client.chat_json(AI_SYSTEM, user, max_tokens=1500)
        if not isinstance(parsed, list):
            continue
        for item in parsed:
            if not isinstance(item, dict):
                continue
            ref, node_id = item.get('ref'), item.get('node_id')
            if ref and node_id in NODE_TO_DOMAIN:
                result[ref] = node_id
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-ai', action='store_true', help='不调用 AI，歧义项落到大类默认节点并标记复核')
    args = parser.parse_args()

    records = json.loads(INPUT_PATH.read_text(encoding='utf-8'))
    ambiguous: list[dict] = []
    stats = Counter()

    for record in records:
        node_id, top, margin, detail = rule_assign(record)
        record['_score_detail'] = detail
        if node_id and top > 0 and margin >= AMBIGUOUS_MARGIN:
            record['kg_node_id'] = node_id
            record['assign_method'] = 'rule'
            record['needs_review'] = False
            stats['rule'] += 1
        else:
            record['kg_node_id'] = node_id
            record['assign_method'] = 'pending'
            ambiguous.append(record)

    print(f'规则直接判定 {stats["rule"]} 题，歧义/无匹配 {len(ambiguous)} 题')

    if ambiguous and not args.no_ai and ai_client.is_available():
        catalog = build_ai_catalog()
        decisions = ai_assign(ambiguous, catalog)
        for record in ambiguous:
            decided = decisions.get(record['source_ref'])
            if decided:
                record['kg_node_id'] = decided
                record['assign_method'] = 'ai'
                record['needs_review'] = True
                record['review_note'] = 'AI 判定的知识点归属，请老师确认是否贴切'
                stats['ai'] += 1
            else:
                _fallback(record, stats)
    else:
        if ambiguous and not args.no_ai:
            print('  DeepSeek 不可用，歧义项走规则兜底')
        for record in ambiguous:
            _fallback(record, stats)

    for record in records:
        record['domain_key'] = NODE_TO_DOMAIN.get(record['kg_node_id'])
        record.pop('_score_detail', None)

    OUTPUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')

    by_node = Counter(r['kg_node_id'] for r in records)
    print(f'\n判定方式：{dict(stats)}')
    print('\n各节点题目数（目标 ≥4）：')
    short = []
    for domain in KNOWLEDGE_DOMAINS:
        print(f'  [{domain.title}]')
        for entry in nodes_for_domain(domain.key):
            count = by_node.get(entry.kg_id, 0)
            flag = '' if count >= 4 else f'  <-- 缺 {4 - count} 题'
            print(f'    {entry.kg_id:16s} {entry.label:12s} {count:3d}{flag}')
            if count < 4:
                short.append((entry.kg_id, 4 - count))
    print(f'\n共 {len(short)} 个节点不足 4 题，合计需补 {sum(n for _, n in short)} 道')
    print(f'-> {OUTPUT_PATH}')


def _fallback(record: dict, stats: Counter) -> None:
    """AI 不可用/未给结论时的兜底：用规则的最高分节点，没有就落到语言入门。"""
    node_id = record.get('kg_node_id')
    if not node_id:
        group = record.get('legacy_concept_group')
        domain = LEGACY_GROUP_TO_DOMAIN.get(group) if group else 'lang-basics'
        node_id = DOMAIN_DEFAULT_NODE.get(domain, 'lang-var')
    record['kg_node_id'] = node_id
    record['assign_method'] = 'rule_fallback'
    record['needs_review'] = True
    record['review_note'] = '规则得分不明确且 AI 未给出结论，暂按最接近的节点归类，请人工确认'
    stats['fallback'] += 1


if __name__ == '__main__':
    main()
