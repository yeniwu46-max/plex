# -*- coding: utf-8 -*-
"""测试账号：满级后 XP 不再增长，可通过 bootstrap 脚本一键解锁学习路径。"""

# 与 IncentiveService.LEVEL_THRESHOLDS[MAX_LEVEL] 保持一致
MAX_LEVEL = 10
MAX_LEVEL_TOTAL_POINTS = 24_000

# 默认开发测试学生账号
TEST_SANDBOX_USERNAMES = frozenset({'student001'})


def is_test_sandbox_user(user) -> bool:
    return bool(user and getattr(user, 'username', None) in TEST_SANDBOX_USERNAMES)

# 与 frontend starPathDomains 知识点 id 对齐（每知识点 5 槽 gen-{id}-s0..s4）
STAR_PATH_KNOWLEDGE_POINT_IDS: tuple[str, ...] = (
    'stage1-intro',
    'stage1-comment',
    'stage1-var',
    'stage1-io',
    'stage2-ops',
    'stage2-cond',
    'stage2-loop',
    'stage2-range',
    'stage3-str',
    'stage3-list',
    'stage3-dict',
    'stage3-func',
    'stage4-algo-sum',
    'stage4-bubble',
    'stage4-selection',
    'stage4-binary',
)

SLOTS_PER_KNOWLEDGE_POINT = 5

# 各星域用于推导 100% 进度的代表 knowledge_key（与 DOMAIN_CATALOG 对齐）
DOMAIN_PROGRESS_KEYS: tuple[tuple[str, str], ...] = (
    ('data-vars', 'intro'),
    ('operators', 'ops'),
    ('flow-control', 'cond'),
    ('strings', 'str'),
    ('lists-dicts', 'list'),
    ('functions', 'func'),
    ('recursion-iter', 'algo-sum'),
)
