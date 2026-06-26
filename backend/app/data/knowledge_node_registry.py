# -*- coding: utf-8 -*-
"""统一知识节点注册表：kg_id / star_path_id / scope_names / knowledge_keys。"""
from __future__ import annotations

from dataclasses import dataclass


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


KNOWLEDGE_NODE_REGISTRY: tuple[KnowledgeNodeEntry, ...] = (
    KnowledgeNodeEntry('intro', 'Python 入门', 'stage1', 'stage1-intro', ('print 输出',), ('intro', 'print', 'python', 'lang'), 'basic', 1, 'python-stage1-program-structure'),
    KnowledgeNodeEntry('comment', '注释', 'stage1', 'stage1-comment', ('print 输出',), ('comment',), 'basic', 1, 'python-stage1-comments'),
    KnowledgeNodeEntry('var', '变量与类型', 'stage1', 'stage1-var', ('变量', '数字类型', '字符串', '布尔值', '类型转换'), ('var', 'syntax', 'basic'), 'basic', 1, 'python-stage1-variables-types'),
    KnowledgeNodeEntry('io', '输入 input', 'stage1', 'stage1-io', ('输入 input', '类型转换'), ('io', 'input'), 'basic', 1, 'python-stage1-input-output'),
    KnowledgeNodeEntry('ops', '运算与表达式', 'stage2', 'stage2-ops', ('算术运算', '比较运算', '逻辑运算'), ('ops',), 'basic', 1, 'python-stage2-operators'),
    KnowledgeNodeEntry('cond', '条件分支', 'stage2', 'stage2-cond', ('if 条件分支',), ('cond', 'condition'), 'basic', 1, 'python-stage2-condition'),
    KnowledgeNodeEntry('loop', '循环结构', 'stage2', 'stage2-loop', ('for 循环', 'while 循环'), ('loop',), 'basic', 1, 'python-stage2-loop'),
    KnowledgeNodeEntry('range', 'range 与控制', 'stage2', 'stage2-range', ('range', 'break', 'continue', '循环边界'), ('range',), 'basic', 2, 'python-stage2-range'),
    KnowledgeNodeEntry('list', '列表 list', 'stage3', 'stage3-list', ('列表',), ('list',), 'basic', 1, 'python-stage3-list'),
    KnowledgeNodeEntry('tuple', '元组与集合', 'stage3', None, ('集合',), ('tuple', 'set'), 'basic', 2),
    KnowledgeNodeEntry('dict', '字典 dict', 'stage3', 'stage3-dict', ('字典', '键值访问'), ('dict',), 'intermediate', 2, 'python-stage3-dict'),
    KnowledgeNodeEntry('str', '字符串处理', 'stage3', 'stage3-str', ('字符串', '字符串方法'), ('str', 'string'), 'basic', 1, 'python-stage3-string'),
    KnowledgeNodeEntry('func', '函数基础', 'stage3', 'stage3-func', ('函数', '参数', '返回值'), ('func', 'function'), 'intermediate', 2, 'python-stage3-function'),
    KnowledgeNodeEntry('file', '文件读写', 'stage4', 'stage4-file', ('文件读取',), ('file',), 'intermediate', 2, 'python-stage4-file'),
    KnowledgeNodeEntry('except', '异常处理', 'stage4', 'stage4-except', ('异常处理',), ('except', 'exception'), 'intermediate', 2, 'python-stage4-exception'),
    KnowledgeNodeEntry('algo-sum', '求和与统计', 'stage4', 'stage4-algo-sum', ('累加求和', '计数统计', '最大值最小值'), ('algo-sum', 'algo', 'sum', 'count'), 'basic', 1, 'python-stage4-sum-statistics'),
    KnowledgeNodeEntry('algo-search', '线性查找', 'stage4', 'stage4-algo-search', ('线性查找',), ('algo-search', 'search'), 'basic', 1, 'python-stage4-linear-search'),
    KnowledgeNodeEntry('algo-sort', '简单排序思想', 'stage4', None, ('简单排序思想',), ('algo-sort', 'sort'), 'intermediate', 3),
    KnowledgeNodeEntry('algo-dedup', '去重与频率', 'stage4', None, ('集合',), ('algo-dedup'), 'intermediate', 2),
    KnowledgeNodeEntry('nested', '嵌套循环', 'stage4', None, ('for 循环', 'while 循环'), ('nested',), 'intermediate', 3),
)

_KG_BY_ID = {e.kg_id: e for e in KNOWLEDGE_NODE_REGISTRY}
_STAR_BY_ID = {e.star_path_id: e for e in KNOWLEDGE_NODE_REGISTRY if e.star_path_id}
_KEY_TO_KG: dict[str, str] = {}
for entry in KNOWLEDGE_NODE_REGISTRY:
    for key in entry.knowledge_keys:
        _KEY_TO_KG[key.lower()] = entry.kg_id


def get_entry(kg_id: str) -> KnowledgeNodeEntry | None:
    return _KG_BY_ID.get(kg_id)


def kg_id_from_star_path(star_path_id: str) -> str | None:
    entry = _STAR_BY_ID.get(star_path_id)
    return entry.kg_id if entry else None


def kg_id_from_key(knowledge_key: str | None, default: str = 'var') -> str:
    if not knowledge_key:
        return default
    key = knowledge_key.lower()
    if key in _KEY_TO_KG:
        return _KEY_TO_KG[key]
    if key.startswith('stage') and key in _KEY_TO_KG:
        return _KEY_TO_KG[key]
    return default


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
            'star_path_id': e.star_path_id,
            'scope_names': list(e.scope_names),
            'knowledge_keys': list(e.knowledge_keys),
            'level': e.level,
            'default_difficulty': e.default_difficulty,
            'document_id': e.document_id,
        }
        for e in KNOWLEDGE_NODE_REGISTRY
    ]
