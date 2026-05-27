"""按知识点随机生成试炼题目"""
import random

from app.models import Trial, TrialQuestion, db

KNOWLEDGE_LABELS = {
    'dp': '动态规划',
    'graph': '图论基础',
    'ds': '数据结构',
    'data': '数据结构',
    'algo': '算法综合',
    'greedy': '贪心',
    'tree': '树结构',
    'frontend': '前端工程化',
    'front': '前端工程化',
    'back': '后端开发',
    'db': '数据库',
    'sql': 'SQL',
}

# 每知识点题库（stem, options, correct_index）
QUESTION_BANK: dict[str, list[dict]] = {
    'dp': [
        {
            'stem': '斐波那契数列用动态规划求 F(n)，状态转移方程是？',
            'options': ['F(n)=F(n-1)+F(n-2)', 'F(n)=F(n-1)*F(n-2)', 'F(n)=2F(n-1)', 'F(n)=n+F(n-1)'],
            'correct_index': 0,
        },
        {
            'stem': '0-1 背包问题中，dp[i][w] 通常表示？',
            'options': [
                '前 i 件物品在容量 w 下的最大价值',
                '第 i 件物品是否必选',
                '容量 w 的最小物品数',
                '前 i 件物品的总重量',
            ],
            'correct_index': 0,
        },
        {
            'stem': '最长公共子序列 LCS 的经典 DP 时间复杂度（两串长度 m,n）为？',
            'options': ['O(mn)', 'O(m+n)', 'O(m log n)', 'O(m²)'],
            'correct_index': 0,
        },
        {
            'stem': '「重叠子问题」是动态规划的必要特征之一，含义是？',
            'options': [
                '子问题会被多次重复求解',
                '子问题互不相交',
                '必须使用递归',
                '只能用于图论',
            ],
            'correct_index': 0,
        },
    ],
    'graph': [
        {
            'stem': '无向连通图有 n 个顶点，最少需要多少条边？',
            'options': ['n-1', 'n', 'n+1', '2n'],
            'correct_index': 0,
        },
        {
            'stem': 'Dijkstra 算法不能正确处理哪种边权？',
            'options': ['负权边', '零权边', '正权边', '无权边'],
            'correct_index': 0,
        },
        {
            'stem': '拓扑排序适用于哪类图？',
            'options': ['有向无环图 DAG', '无向完全图', '带负环的有向图', '任意稠密图'],
            'correct_index': 0,
        },
        {
            'stem': 'BFS 常用于求无权图上的？',
            'options': ['最短路径（边权为 1）', '最小生成树', '强连通分量', '欧拉回路'],
            'correct_index': 0,
        },
    ],
    'ds': [
        {
            'stem': '二叉搜索树中序遍历序列的特点是？',
            'options': ['单调非降', '单调非增', '随机', '与插入顺序相同'],
            'correct_index': 0,
        },
        {
            'stem': '栈的典型应用场景是？',
            'options': ['表达式括号匹配', '最短路径', '归并排序', '哈希冲突处理'],
            'correct_index': 0,
        },
        {
            'stem': '链表单节点删除（已知节点指针）平均时间复杂度？',
            'options': ['O(1)', 'O(log n)', 'O(n)', 'O(n log n)'],
            'correct_index': 0,
        },
        {
            'stem': '哈希表平均查找复杂度通常为？',
            'options': ['O(1)', 'O(log n)', 'O(n)', 'O(n²)'],
            'correct_index': 0,
        },
    ],
    'frontend': [
        {
            'stem': 'Vue 3 中响应式 ref 在 script 里读取值需要？',
            'options': ['.value', '.data', '.get()', '直接当普通变量'],
            'correct_index': 0,
        },
        {
            'stem': 'HTTP 缓存头 Cache-Control: no-store 表示？',
            'options': ['不存储任何缓存副本', '永久缓存', '仅 CDN 缓存', '只缓存 HTML'],
            'correct_index': 0,
        },
        {
            'stem': 'Flex 布局中 justify-content 控制的是？',
            'options': ['主轴对齐', '交叉轴对齐', '换行', '子项缩放'],
            'correct_index': 0,
        },
        {
            'stem': 'TypeScript 中 interface 与 type 都可描述对象，常见区别是？',
            'options': ['interface 可声明合并', 'type 一定更快', 'interface 不能继承', 'type 不能用于函数'],
            'correct_index': 0,
        },
    ],
    'algo': [
        {
            'stem': '快速排序平均时间复杂度是？',
            'options': ['O(n log n)', 'O(n²)', 'O(n)', 'O(log n)'],
            'correct_index': 0,
        },
        {
            'stem': '二分查找的前提条件是？',
            'options': ['序列有序', '序列唯一', '序列链表存储', '序列长度为奇数'],
            'correct_index': 0,
        },
    ],
}

DEFAULT_BANK = QUESTION_BANK['algo']


class QuestionGenerator:
    QUESTIONS_PER_TRIAL = 3

    @staticmethod
    def _normalize_key(knowledge_key: str | None) -> str:
        key = (knowledge_key or 'algo').lower().strip()
        if key in QUESTION_BANK:
            return key
        if key in ('data', 'tree', 'stack'):
            return 'ds'
        if key in ('front', 'css', 'react'):
            return 'frontend'
        return 'algo'

    @staticmethod
    def bank_for_key(knowledge_key: str | None) -> list[dict]:
        return QUESTION_BANK.get(QuestionGenerator._normalize_key(knowledge_key), DEFAULT_BANK)

    @staticmethod
    def ensure_for_trial(trial: Trial, count: int | None = None) -> list[TrialQuestion]:
        """为试炼生成题目（已存在则跳过）。"""
        existing = TrialQuestion.query.filter_by(trial_id=trial.id).order_by(TrialQuestion.sort_order).all()
        if existing:
            return existing

        bank = QuestionGenerator.bank_for_key(trial.knowledge_key)
        pick_count = min(count or QuestionGenerator.QUESTIONS_PER_TRIAL, len(bank))
        picked = random.sample(bank, pick_count)
        key = QuestionGenerator._normalize_key(trial.knowledge_key)

        created = []
        for index, item in enumerate(picked):
            question = TrialQuestion(
                trial_id=trial.id,
                sort_order=index + 1,
                stem=item['stem'],
                options=item['options'],
                correct_index=int(item['correct_index']),
                knowledge_key=key,
            )
            db.session.add(question)
            created.append(question)
        db.session.commit()
        return created

    @staticmethod
    def label_for_key(knowledge_key: str | None) -> str:
        key = QuestionGenerator._normalize_key(knowledge_key)
        return KNOWLEDGE_LABELS.get(key, KNOWLEDGE_LABELS.get(knowledge_key or '', '综合练习'))
