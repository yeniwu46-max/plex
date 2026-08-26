"""教师端 · Python 初学者知识点目录。

内容全部由 `knowledge_node_registry` 派生：8 个大类、26 个知识点。之前这里手写了
一份 stage1~stage4 的目录，和知识图谱、星轨各维护各的，改一处就会漂移；现在只保留
"换个形状展示"的逻辑，定义仍然只有注册表一份。
"""
from app.data.knowledge_node_registry import (
    KNOWLEDGE_DOMAINS,
    KNOWLEDGE_NODE_REGISTRY,
    nodes_for_domain,
)

KNOWLEDGE_UNIVERSE = [
    {
        'key': domain.key,
        'label': domain.title,
        'points': [
            {'key': entry.kg_id, 'label': entry.label}
            for entry in nodes_for_domain(domain.key)
        ],
    }
    for domain in KNOWLEDGE_DOMAINS
]

# 知识点 → 题库分组。重排后题库直接按知识点节点组织（problems.kg_node_id），
# 于是这张表退化成恒等映射；保留它是因为若干调用方仍按"点 → 题库"的语义取题。
POINT_TO_BANK = {entry.kg_id: entry.kg_id for entry in KNOWLEDGE_NODE_REGISTRY}

DOMAIN_LABELS = {d['key']: d['label'] for d in KNOWLEDGE_UNIVERSE}
