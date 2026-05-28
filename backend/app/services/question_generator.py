"""按知识点随机生成试炼题目"""
import random

from app.models import Trial, TrialQuestion, db

from app.data.knowledge_catalog import DOMAIN_LABELS, KNOWLEDGE_UNIVERSE, POINT_TO_BANK

KNOWLEDGE_LABELS = {
    'dp': '动态规划',
    'graph': '图论基础',
    'ds': '数据结构',
    'data': '数据结构',
    'algo': '算法基础',
    'greedy': '贪心',
    'tree': '树结构',
    'frontend': '前端开发',
    'front': '前端开发',
    'fe': '前端开发',
    'back': '后端开发',
    'be': '后端开发',
    'db': '数据库',
    'sql': 'SQL',
    'cs': '计算机基础',
    **DOMAIN_LABELS,
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
        {
            'stem': '大 O 记号主要描述算法的？',
            'options': ['渐近上界', '精确运行时间', '内存地址', '编译优化级别'],
            'correct_index': 0,
        },
    ],
    'back': [
        {
            'stem': 'RESTful API 中 GET 请求通常用于？',
            'options': ['获取资源', '删除资源', '仅上传文件', '开启事务'],
            'correct_index': 0,
        },
        {
            'stem': 'JWT 常用于？',
            'options': ['无状态认证', '数据库索引', '前端路由', '图片压缩'],
            'correct_index': 0,
        },
        {
            'stem': 'ORM 的主要作用是？',
            'options': ['对象与关系表映射', '压缩 HTTP', '渲染 UI', '负载均衡'],
            'correct_index': 0,
        },
    ],
    'cs': [
        {
            'stem': '进程与线程的主要区别是？',
            'options': ['线程共享进程资源', '进程一定比线程快', '线程不能并发', '进程没有地址空间'],
            'correct_index': 0,
        },
        {
            'stem': 'TCP 属于 OSI 模型的哪一层？',
            'options': ['传输层', '应用层', '物理层', '表示层'],
            'correct_index': 0,
        },
        {
            'stem': '虚拟内存的主要目的是？',
            'options': ['扩展可用地址空间', '提高 CPU 主频', '加密磁盘', '减少网络延迟'],
            'correct_index': 0,
        },
    ],
    'db': [
        {
            'stem': 'SQL 中 PRIMARY KEY 约束表示？',
            'options': ['唯一标识一行', '允许重复', '必须为 NULL', '自动排序'],
            'correct_index': 0,
        },
        {
            'stem': '数据库索引的主要作用是？',
            'options': ['加快查询', '增加存储冗余', '禁止更新', '替代事务'],
            'correct_index': 0,
        },
        {
            'stem': 'ACID 中 A 表示？',
            'options': ['原子性', '可用性', '异步', '聚合'],
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
        if key in POINT_TO_BANK:
            return POINT_TO_BANK[key]
        if key in QUESTION_BANK:
            return key
        if key in ('data', 'tree', 'stack'):
            return 'ds'
        if key in ('front', 'css', 'react', 'fe'):
            return 'frontend'
        if key in ('be',):
            return 'back'
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

        keys = trial.knowledge_keys() if hasattr(trial, 'knowledge_keys') else []
        if not keys and trial.knowledge_key:
            keys = [trial.knowledge_key]

        pick_count = count or QuestionGenerator.QUESTIONS_PER_TRIAL
        created = []
        used_stems: set[str] = set()

        if len(keys) > 1:
            for index, raw_key in enumerate(keys[:pick_count]):
                bank_key = QuestionGenerator._normalize_key(raw_key)
                bank = QuestionGenerator.bank_for_key(raw_key)
                candidates = [item for item in bank if item['stem'] not in used_stems]
                if not candidates:
                    candidates = bank
                item = random.choice(candidates)
                used_stems.add(item['stem'])
                question = TrialQuestion(
                    trial_id=trial.id,
                    sort_order=index + 1,
                    stem=item['stem'],
                    options=item['options'],
                    correct_index=int(item['correct_index']),
                    knowledge_key=raw_key,
                )
                db.session.add(question)
                created.append(question)
        else:
            bank = QuestionGenerator.bank_for_key(keys[0] if keys else trial.knowledge_key)
            sample_count = min(pick_count, len(bank))
            picked = random.sample(bank, sample_count)
            key = QuestionGenerator._normalize_key(keys[0] if keys else trial.knowledge_key)
            for index, item in enumerate(picked):
                question = TrialQuestion(
                    trial_id=trial.id,
                    sort_order=index + 1,
                    stem=item['stem'],
                    options=item['options'],
                    correct_index=int(item['correct_index']),
                    knowledge_key=keys[0] if keys else key,
                )
                db.session.add(question)
                created.append(question)

        db.session.commit()
        return created

    @staticmethod
    def label_for_key(knowledge_key: str | None) -> str:
        if not knowledge_key:
            return '综合练习'
        if knowledge_key in POINT_TO_BANK:
            for domain in KNOWLEDGE_UNIVERSE:
                for point in domain['points']:
                    if point['key'] == knowledge_key:
                        return point['label']
        key = QuestionGenerator._normalize_key(knowledge_key)
        return KNOWLEDGE_LABELS.get(key, KNOWLEDGE_LABELS.get(knowledge_key, '综合练习'))
