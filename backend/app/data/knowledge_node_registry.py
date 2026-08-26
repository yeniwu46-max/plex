# -*- coding: utf-8 -*-
"""统一知识节点注册表（2026-07-30 重排为 8 大类 / 26 节点）。

这里是全站知识点的**唯一权威定义**，以下产物都由它派生，必须保持一致：

- `app/data/kg_topology.py`        —— 知识图谱节点与边
- `knowledge_nodes` 数据库表        —— 由 scripts/knowledge_rebuild/load_mysql.py 同步
- `frontend/src/data/knowledgeNodeRegistry.ts` 及 `starPathDomains.ts`

8 大类顺序即教学推荐顺序：语言入门 → 顺序结构 → 分支结构 → 循环结构 → 数组 →
字符串 → 函数与递归 → 查找与搜索。

关于旧 knowledge_key 的兼容：历史作答记录（trial_question_progress 约 9.7k 行、
student_mistakes 约 0.7k 行）里存的是旧 key（intro/var/cond/loop/...），
`LEGACY_KEY_TO_NODE` 负责把它们映射到新节点，保证历史进度不失效。旧库里还有一批
面向进阶专题的 key（数据库设计、REST、栈与树、动态规划等），它们不属于本次 8 大类
覆盖的 Python 入门范围，登记在 `OUT_OF_SCOPE_LEGACY_KEYS` 中并**明确不参与**新知识
图谱统计——把它们硬塞进某个入门节点会让该节点的掌握度失真。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeDomain:
    """知识点大类（前端称"星域"）。"""
    key: str
    title: str
    order: int
    description: str
    focus: str


KNOWLEDGE_DOMAINS: tuple[KnowledgeDomain, ...] = (
    KnowledgeDomain('lang-basics', '语言入门', 1, '认识 Python，写出第一段可运行的程序', '输出、注释、变量、输入'),
    KnowledgeDomain('sequence', '顺序结构', 2, '按书写顺序一步步执行的程序', '算术运算、表达式、类型转换'),
    KnowledgeDomain('branch', '分支结构', 3, '让程序根据条件走不同的路', 'if / elif / else 与复合条件'),
    KnowledgeDomain('loop', '循环结构', 4, '把重复的事情交给循环去做', 'for、while、嵌套与循环控制'),
    KnowledgeDomain('array', '数组', 5, '用列表把一组数据装在一起处理', '列表创建、遍历统计、二维列表'),
    KnowledgeDomain('string', '字符串', 6, '把文本当作可以逐字处理的数据', '索引切片、常用方法、字符统计'),
    KnowledgeDomain('function', '函数与递归', 7, '把一段逻辑打包复用，并让它调用自己', '定义调用、参数返回、递归'),
    KnowledgeDomain('search', '查找与搜索', 8, '在数据里高效地找到想要的东西', '顺序查找、二分查找、排序、统计'),
)


@dataclass(frozen=True)
class KnowledgeNodeEntry:
    kg_id: str
    label: str
    domain_key: str
    star_path_id: str | None
    scope_names: tuple[str, ...]
    knowledge_keys: tuple[str, ...]
    level: str
    default_difficulty: int
    document_id: str | None = None
    summary: str = ''


# star_path_id 与 kg_id 保持一致：重排后不再需要两套 id 空间（旧版是
# 'intro' / 'stage1-intro' 两套，容易前后端对不上）。
KNOWLEDGE_NODE_REGISTRY: tuple[KnowledgeNodeEntry, ...] = (
    # ---- 1. 语言入门 ----
    KnowledgeNodeEntry(
        'lang-print', 'print 输出与注释', 'lang-basics', 'lang-print',
        ('print 输出', '注释'), ('lang-print', 'intro', 'print', 'python', 'lang', 'comment'),
        'basic', 1, 'python-lang-print', '用 print 输出信息，用注释解释代码',
    ),
    KnowledgeNodeEntry(
        'lang-var', '变量与类型', 'lang-basics', 'lang-var',
        ('变量', '数字类型', '字符串', '布尔值'), ('lang-var', 'var', 'syntax', 'basic'),
        'basic', 1, 'python-lang-var', '给数据起名字，认识整数、小数、字符串和布尔值',
    ),
    KnowledgeNodeEntry(
        'lang-input', '输入 input', 'lang-basics', 'lang-input',
        ('输入 input', '文件读取', '异常处理'), ('lang-input', 'io', 'input', 'file', 'except', 'exception'),
        'basic', 1, 'python-lang-input', '用 input 读取用户输入，并处理读入时的异常',
    ),
    # ---- 2. 顺序结构 ----
    KnowledgeNodeEntry(
        'seq-arith', '算术运算', 'sequence', 'seq-arith',
        ('算术运算',), ('seq-arith', 'ops', 'arith'),
        'basic', 1, 'python-seq-arith', '加减乘除、整除、取余与幂运算',
    ),
    KnowledgeNodeEntry(
        'seq-expr', '表达式与优先级', 'sequence', 'seq-expr',
        ('比较运算', '逻辑运算', '表达式'), ('seq-expr', 'expr', 'operator-priority'),
        'basic', 2, 'python-seq-expr', '把多个运算组合起来，理解谁先算谁后算',
    ),
    KnowledgeNodeEntry(
        'seq-type', '数据类型与转换', 'sequence', 'seq-type',
        ('类型转换', '数字类型'), ('seq-type', 'datatype', 'cast', 'hightype'),
        'basic', 2, 'python-seq-type', 'int / float / str 之间的相互转换与取整',
    ),
    # ---- 3. 分支结构 ----
    KnowledgeNodeEntry(
        'branch-if', '单分支与双分支', 'branch', 'branch-if',
        ('if 条件分支',), ('branch-if', 'cond', 'condition', 'if'),
        'basic', 1, 'python-branch-if', 'if 与 if-else：让程序二选一',
    ),
    KnowledgeNodeEntry(
        'branch-elif', '多分支 elif', 'branch', 'branch-elif',
        ('if 条件分支',), ('branch-elif', 'elif', 'multi-branch'),
        'basic', 2, 'python-branch-elif', '用 elif 串起三条以上的分支，如成绩等第',
    ),
    KnowledgeNodeEntry(
        'branch-nested', '嵌套与复合条件', 'branch', 'branch-nested',
        ('if 条件分支', '逻辑运算'), ('branch-nested', 'nested-condition', 'nested_condition'),
        'intermediate', 3, 'python-branch-nested', '分支里再套分支，以及 and / or / not 复合判断',
    ),
    # ---- 4. 循环结构 ----
    KnowledgeNodeEntry(
        'loop-for', 'for 与 range', 'loop', 'loop-for',
        ('for 循环', 'range'), ('loop-for', 'loop', 'for', 'range'),
        'basic', 1, 'python-loop-for', '用 for 配合 range 重复固定次数',
    ),
    KnowledgeNodeEntry(
        'loop-while', 'while 循环', 'loop', 'loop-while',
        ('while 循环', '循环边界'), ('loop-while', 'while'),
        'basic', 2, 'python-loop-while', '条件成立就一直做，重点是想清楚终止条件',
    ),
    KnowledgeNodeEntry(
        'loop-nested', '嵌套循环', 'loop', 'loop-nested',
        ('for 循环', 'while 循环'), ('loop-nested', 'nested', 'nested_loop'),
        'intermediate', 3, 'python-loop-nested', '双重循环打印图形、遍历组合',
    ),
    KnowledgeNodeEntry(
        'loop-control', 'break 与 continue', 'loop', 'loop-control',
        ('break', 'continue', '循环边界'), ('loop-control', 'break', 'continue'),
        'intermediate', 3, 'python-loop-control', '提前跳出循环或跳过本轮',
    ),
    # ---- 5. 数组 ----
    KnowledgeNodeEntry(
        'array-basic', '列表基础', 'array', 'array-basic',
        ('列表', '集合'), ('array-basic', 'list', 'array', 'tuple', 'set', 'dict'),
        'basic', 2, 'python-array-basic', '创建列表、索引取值、切片与增删改',
    ),
    KnowledgeNodeEntry(
        'array-traverse', '遍历与统计', 'array', 'array-traverse',
        ('列表', '累加求和', '计数统计'), ('array-traverse', 'list-traverse'),
        'intermediate', 2, 'python-array-traverse', '遍历列表求和、计数、找最值',
    ),
    KnowledgeNodeEntry(
        'array-2d', '二维列表', 'array', 'array-2d',
        ('列表', 'for 循环'), ('array-2d', 'list-2d', 'matrix'),
        'intermediate', 3, 'python-array-2d', '用嵌套列表表示表格与矩阵',
    ),
    # ---- 6. 字符串 ----
    KnowledgeNodeEntry(
        'string-index', '索引与切片', 'string', 'string-index',
        ('字符串',), ('string-index', 'str', 'string'),
        'basic', 2, 'python-string-index', '按下标取字符、用切片截取子串与反转',
    ),
    KnowledgeNodeEntry(
        'string-method', '常用方法', 'string', 'string-method',
        ('字符串方法',), ('string-method', 'str-method', 'string_ops'),
        'intermediate', 2, 'python-string-method', 'split / join / replace / strip / upper 等',
    ),
    KnowledgeNodeEntry(
        'string-scan', '遍历与统计', 'string', 'string-scan',
        ('字符串', '计数统计'), ('string-scan', 'str-scan'),
        'intermediate', 3, 'python-string-scan', '逐字符遍历，统计字符出现次数与回文判断',
    ),
    # ---- 7. 函数与递归 ----
    KnowledgeNodeEntry(
        'func-define', '定义与调用', 'function', 'func-define',
        ('函数',), ('func-define', 'func', 'function', 'def'),
        'intermediate', 2, 'python-func-define', '用 def 把一段逻辑打包，然后反复调用',
    ),
    KnowledgeNodeEntry(
        'func-param', '参数与返回值', 'function', 'func-param',
        ('参数', '返回值'), ('func-param', 'parameter', 'return'),
        'intermediate', 3, 'python-func-param', '传入参数、返回结果，理解作用域',
    ),
    KnowledgeNodeEntry(
        'func-recursion', '递归', 'function', 'func-recursion',
        ('函数', '递归'), ('func-recursion', 'recursion'),
        'advanced', 4, 'python-func-recursion', '函数调用自己，关键是找到出口条件',
    ),
    # ---- 8. 查找与搜索 ----
    KnowledgeNodeEntry(
        'search-linear', '顺序查找', 'search', 'search-linear',
        ('线性查找',), ('search-linear', 'algo-search', 'search'),
        'basic', 2, 'python-search-linear', '从头到尾逐个比对，找到目标就停',
    ),
    KnowledgeNodeEntry(
        'search-binary', '二分查找', 'search', 'search-binary',
        ('线性查找', '循环边界'), ('search-binary', 'algo-binary', 'binary-search'),
        'advanced', 4, 'python-search-binary', '在有序数据里每次砍掉一半',
    ),
    KnowledgeNodeEntry(
        'search-sort', '排序思想', 'search', 'search-sort',
        ('简单排序思想',), ('search-sort', 'algo-sort', 'sort', 'algo-bubble', 'algo-selection'),
        'advanced', 4, 'python-search-sort', '冒泡与选择排序：交换与选最小',
    ),
    KnowledgeNodeEntry(
        'search-stat', '统计与去重', 'search', 'search-stat',
        ('累加求和', '计数统计', '最大值最小值', '集合'),
        ('search-stat', 'algo-sum', 'algo', 'sum', 'count', 'algo-dedup', 'dedup'),
        'intermediate', 3, 'python-search-stat', '求和、计数、找最值与去重',
    ),
)


# 旧库里存在、但不属于本次 8 大类（Python 入门）覆盖范围的 knowledge_key。
# 这些 key 来自教师针对进阶专题创建的试炼，故意**不**映射到任何入门节点：
# 把"REST API 鉴权""动态规划"的作答计入"顺序查找"之类的节点会让掌握度失真。
# 知识图谱统计会跳过它们，历史记录本身仍完整保留在库中。
OUT_OF_SCOPE_LEGACY_KEYS: frozenset[str] = frozenset({
    'db-design', 'be-rest', 'be-auth',
    'ds-stack', 'ds-tree', 'ds-graph', 'graph',
    'dp', 'algo-dp-intro', 'algo-greedy', 'algo-complexity',
})

# 旧的教师阶段 key（stage1~stage4），映射到各阶段的代表节点。
_STAGE_ALIASES = {
    'stage1': 'lang-print',
    'stage2': 'branch-if',
    'stage3': 'array-basic',
    'stage4': 'search-stat',
}

DEFAULT_NODE_ID = 'lang-var'

_KG_BY_ID = {e.kg_id: e for e in KNOWLEDGE_NODE_REGISTRY}
_STAR_BY_ID = {e.star_path_id: e for e in KNOWLEDGE_NODE_REGISTRY if e.star_path_id}
_DOMAIN_BY_KEY = {d.key: d for d in KNOWLEDGE_DOMAINS}

LEGACY_KEY_TO_NODE: dict[str, str] = {}
for _entry in KNOWLEDGE_NODE_REGISTRY:
    for _key in _entry.knowledge_keys:
        LEGACY_KEY_TO_NODE[_key.lower()] = _entry.kg_id
LEGACY_KEY_TO_NODE.update(_STAGE_ALIASES)


def domains() -> tuple[KnowledgeDomain, ...]:
    return KNOWLEDGE_DOMAINS


def get_domain(domain_key: str) -> KnowledgeDomain | None:
    return _DOMAIN_BY_KEY.get(domain_key)


def get_entry(kg_id: str) -> KnowledgeNodeEntry | None:
    return _KG_BY_ID.get(kg_id)


def nodes_for_domain(domain_key: str) -> list[KnowledgeNodeEntry]:
    return [e for e in KNOWLEDGE_NODE_REGISTRY if e.domain_key == domain_key]


def all_node_ids() -> list[str]:
    return [e.kg_id for e in KNOWLEDGE_NODE_REGISTRY]


def kg_id_from_star_path(star_path_id: str) -> str | None:
    entry = _STAR_BY_ID.get(star_path_id)
    return entry.kg_id if entry else None


def is_out_of_scope(knowledge_key: str | None) -> bool:
    """该 key 是否属于旧的进阶专题（不参与新知识图谱统计）。"""
    return bool(knowledge_key) and knowledge_key.lower() in OUT_OF_SCOPE_LEGACY_KEYS


def kg_id_from_key(knowledge_key: str | None, default: str = DEFAULT_NODE_ID) -> str:
    if not knowledge_key:
        return default
    return LEGACY_KEY_TO_NODE.get(knowledge_key.lower(), default)


def resolve_node_id(knowledge_key: str | None) -> str | None:
    """把任意 knowledge_key 解析为新节点 id；无法归属时返回 None（而不是硬塞默认值）。"""
    if not knowledge_key:
        return None
    key = knowledge_key.lower()
    if key in OUT_OF_SCOPE_LEGACY_KEYS:
        return None
    return LEGACY_KEY_TO_NODE.get(key)


def scope_names_for_kg(kg_id: str) -> list[str]:
    entry = get_entry(kg_id)
    return list(entry.scope_names) if entry else []


def kg_node_to_scope_map() -> dict[str, list[str]]:
    return {e.kg_id: list(e.scope_names) for e in KNOWLEDGE_NODE_REGISTRY}


def registry_as_dicts() -> list[dict]:
    return [
        {
            'kg_id': e.kg_id,
            'label': e.label,
            'domain_key': e.domain_key,
            'domain_title': _DOMAIN_BY_KEY[e.domain_key].title,
            'domain_order': _DOMAIN_BY_KEY[e.domain_key].order,
            'star_path_id': e.star_path_id,
            'scope_names': list(e.scope_names),
            'knowledge_keys': list(e.knowledge_keys),
            'level': e.level,
            'default_difficulty': e.default_difficulty,
            'document_id': e.document_id,
            'summary': e.summary,
        }
        for e in KNOWLEDGE_NODE_REGISTRY
    ]


def domains_as_dicts() -> list[dict]:
    return [
        {
            'key': d.key,
            'title': d.title,
            'order': d.order,
            'description': d.description,
            'focus': d.focus,
            'node_ids': [e.kg_id for e in nodes_for_domain(d.key)],
        }
        for d in KNOWLEDGE_DOMAINS
    ]
