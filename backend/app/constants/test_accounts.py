# -*- coding: utf-8 -*-
"""测试账号：满级后 XP 不再增长，可通过 bootstrap 脚本一键解锁学习路径。"""
from app.data.knowledge_node_registry import (
    KNOWLEDGE_DOMAINS,
    KNOWLEDGE_NODE_REGISTRY,
    nodes_for_domain,
)

# 与 IncentiveService.LEVEL_THRESHOLDS[MAX_LEVEL] 保持一致
MAX_LEVEL = 10
MAX_LEVEL_TOTAL_POINTS = 24_000

# 默认开发测试学生账号
TEST_SANDBOX_USERNAMES = frozenset({'student001'})


def is_test_sandbox_user(user) -> bool:
    return bool(user and getattr(user, 'username', None) in TEST_SANDBOX_USERNAMES)

# 与 frontend starPathDomains 知识点 id 对齐（每知识点 5 槽 gen-{id}-s0..s4）。
# 重排后 star_path_id 与 kg_id 相同，所以直接取注册表的节点 id。
STAR_PATH_KNOWLEDGE_POINT_IDS: tuple[str, ...] = tuple(
    entry.star_path_id or entry.kg_id for entry in KNOWLEDGE_NODE_REGISTRY
)

SLOTS_PER_KNOWLEDGE_POINT = 5

# 各星域用于推导 100% 进度的代表 knowledge_key：取该大类下第一个节点的 id。
DOMAIN_PROGRESS_KEYS: tuple[tuple[str, str], ...] = tuple(
    (domain.key, nodes_for_domain(domain.key)[0].kg_id)
    for domain in KNOWLEDGE_DOMAINS
    if nodes_for_domain(domain.key)
)
