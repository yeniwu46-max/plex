"""教师端 · Python 初学者知识点目录"""

KNOWLEDGE_UNIVERSE = [
    {
        'key': 'stage1',
        'label': '会写第一段 Python',
        'points': [
            {'key': 'intro', 'label': 'Python 与 print'},
            {'key': 'comment', 'label': '注释'},
            {'key': 'var', 'label': '变量与类型'},
            {'key': 'io', 'label': '输入 input'},
        ],
    },
    {
        'key': 'stage2',
        'label': '条件与循环',
        'points': [
            {'key': 'ops', 'label': '运算与表达式'},
            {'key': 'cond', 'label': 'if 分支'},
            {'key': 'loop', 'label': '循环结构'},
            {'key': 'range', 'label': 'range / break / continue'},
        ],
    },
    {
        'key': 'stage3',
        'label': '容器、字符串与函数',
        'points': [
            {'key': 'list', 'label': '列表 list'},
            {'key': 'dict', 'label': '字典 dict'},
            {'key': 'str', 'label': '字符串处理'},
            {'key': 'func', 'label': '函数基础'},
        ],
    },
    {
        'key': 'stage4',
        'label': '简单算法小任务',
        'points': [
            {'key': 'file', 'label': '文件读写'},
            {'key': 'except', 'label': '异常处理'},
            {'key': 'algo-sum', 'label': '求和与统计'},
            {'key': 'algo-search', 'label': '线性查找'},
        ],
    },
]

POINT_TO_BANK = {
    'intro': 'intro',
    'comment': 'intro',
    'var': 'var',
    'io': 'var',
    'ops': 'ops',
    'cond': 'cond',
    'loop': 'loop',
    'range': 'loop',
    'list': 'list',
    'dict': 'list',
    'str': 'str',
    'func': 'func',
    'file': 'file',
    'except': 'file',
    'algo-sum': 'algo',
    'algo-search': 'algo',
}

DOMAIN_LABELS = {d['key']: d['label'] for d in KNOWLEDGE_UNIVERSE}
