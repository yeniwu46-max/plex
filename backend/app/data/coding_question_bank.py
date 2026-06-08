"""内置 Python 编程试炼题库（供教师组卷选用）"""

CODING_QUESTION_BANK = [
    {
        'id': 'hello-print',
        'stem': '编写程序，向 PLEX 宇宙输出一句问候语。要求使用 print()，且输出内容必须与样例完全一致（区分大小写）。',
        'knowledge_key': 'intro',
        'starter_code': 'print("Hello, PLEX!")\n',
        'run_mode': 'stdout',
        'hint': '字符串需要用英文双引号包裹。',
        'test_cases': [
            {'id': 't1', 'label': '基础输出', 'expected': 'Hello, PLEX!'},
        ],
    },
    {
        'id': 'var-sum',
        'stem': '已有两个整数变量 a 与 b（由测试数据注入）。请计算它们的和并 print 输出，不要修改给定变量名。',
        'knowledge_key': 'var',
        'starter_code': '# a、b 已由测试数据提供\n# 输出 a + b\n',
        'run_mode': 'stdout',
        'hint': 'print(a + b)',
        'test_cases': [
            {'id': 't1', 'label': '样例 1', 'setup': 'a = 3\nb = 5', 'expected': '8'},
            {'id': 't2', 'label': '样例 2', 'setup': 'a = 12\nb = 30', 'expected': '42'},
        ],
    },
    {
        'id': 'max-of-two',
        'stem': '变量 a 与 b 已给定。请 print 输出两者中的较大值。',
        'knowledge_key': 'cond',
        'starter_code': '# 输出 a 与 b 的较大值\n',
        'run_mode': 'stdout',
        'hint': '可使用 max(a, b) 或 if 比较。',
        'test_cases': [
            {'id': 't1', 'label': 'a 更大', 'setup': 'a = 7\nb = 3', 'expected': '7'},
            {'id': 't2', 'label': 'b 更大', 'setup': 'a = 2\nb = 9', 'expected': '9'},
        ],
    },
    {
        'id': 'sum-1-to-n',
        'stem': '变量 n 已给定。请计算 1 到 n 的累加和并输出。',
        'knowledge_key': 'loop',
        'starter_code': '# 计算 1..n 的和\n',
        'run_mode': 'stdout',
        'hint': '使用 for 循环与累加变量 total。',
        'test_cases': [
            {'id': 't1', 'label': 'n=5', 'setup': 'n = 5', 'expected': '15'},
            {'id': 't2', 'label': 'n=10', 'setup': 'n = 10', 'expected': '55'},
        ],
    },
    {
        'id': 'list-sum',
        'stem': '列表 nums 已给定。请输出 nums 中所有元素之和。',
        'knowledge_key': 'list',
        'starter_code': '# 输出列表元素之和\n',
        'run_mode': 'stdout',
        'hint': '遍历列表并累加。',
        'test_cases': [
            {'id': 't1', 'label': '样例 1', 'setup': 'nums = [1, 2, 3, 4]', 'expected': '10'},
            {'id': 't2', 'label': '样例 2', 'setup': 'nums = [5, 5]', 'expected': '10'},
        ],
    },
    {
        'id': 'str-count-a',
        'stem': '字符串 s 已给定。请输出字母 a 在 s 中出现的次数（区分大小写）。',
        'knowledge_key': 'str',
        'starter_code': '# 统计字符 a 出现次数\n',
        'run_mode': 'stdout',
        'hint': '可以遍历字符串并计数，或使用 count 方法。',
        'test_cases': [
            {'id': 't1', 'label': '样例 1', 'setup': 's = "banana"', 'expected': '3'},
            {'id': 't2', 'label': '样例 2', 'setup': 's = "apple"', 'expected': '1'},
        ],
    },
    {
        'id': 'func-add',
        'stem': '请定义函数 add(a, b) 返回两数之和，并 print 输出 add(3, 4) 的结果。',
        'knowledge_key': 'func',
        'starter_code': 'def add(a, b):\n    pass\n\nprint(add(3, 4))\n',
        'run_mode': 'stdout',
        'hint': '函数体使用 return a + b。',
        'test_cases': [
            {'id': 't1', 'label': '基础调用', 'expected': '7'},
        ],
    },
    {
        'id': 'linear-search',
        'stem': '列表 nums 与目标 target 已给定。若找到 target，输出其索引；否则输出 -1。',
        'knowledge_key': 'algo-search',
        'starter_code': '# 线性查找 target\n',
        'run_mode': 'stdout',
        'hint': '遍历索引 i，若 nums[i] == target 则输出 i。',
        'test_cases': [
            {'id': 't1', 'label': '找到', 'setup': 'nums = [2, 4, 6, 8]\ntarget = 6', 'expected': '2'},
            {'id': 't2', 'label': '未找到', 'setup': 'nums = [1, 3, 5]\ntarget = 4', 'expected': '-1'},
        ],
    },
]
