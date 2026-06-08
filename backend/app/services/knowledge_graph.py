# -*- coding: utf-8 -*-
"""知识图谱：Python 初学者静态拓扑 + 学情驱动节点状态。"""
from collections import Counter, defaultdict

from app.models import TrialQuestion, TrialQuestionProgress, User, db
from app.services.mistake import MistakeService
from app.services.recommendation import RecommendationService

KG_NODES = [
    {'id': 'intro', 'label': 'Python 入门', 'domain': '入门', 'level': 'basic', 'description': '认识 Python 与 print 输出', 'x': 80, 'y': 180},
    {'id': 'comment', 'label': '注释', 'domain': '入门', 'level': 'basic', 'description': '单行与多行注释', 'x': 80, 'y': 320},
    {'id': 'var', 'label': '变量与类型', 'domain': '基础', 'level': 'basic', 'description': '变量、数字、字符串、布尔与类型转换', 'x': 240, 'y': 180},
    {'id': 'io', 'label': '输入 input', 'domain': '基础', 'level': 'basic', 'description': '使用 input 读取用户输入', 'x': 240, 'y': 320},
    {'id': 'ops', 'label': '运算与表达式', 'domain': '基础', 'level': 'basic', 'description': '算术、比较、逻辑运算与格式化输出', 'x': 400, 'y': 180},
    {'id': 'cond', 'label': '条件分支', 'domain': '控制流', 'level': 'basic', 'description': 'if / elif / else', 'x': 400, 'y': 320},
    {'id': 'loop', 'label': '循环结构', 'domain': '控制流', 'level': 'basic', 'description': 'while 与 for 循环', 'x': 560, 'y': 180},
    {'id': 'range', 'label': 'range 与控制', 'domain': '控制流', 'level': 'basic', 'description': 'range、break、continue', 'x': 560, 'y': 320},
    {'id': 'list', 'label': '列表 list', 'domain': '容器', 'level': 'basic', 'description': '列表创建、索引、切片与遍历', 'x': 720, 'y': 180},
    {'id': 'tuple', 'label': '元组与集合', 'domain': '容器', 'level': 'basic', 'description': 'tuple 与 set 基础', 'x': 720, 'y': 320},
    {'id': 'dict', 'label': '字典 dict', 'domain': '容器', 'level': 'intermediate', 'description': '键值对与常见操作', 'x': 880, 'y': 180},
    {'id': 'str', 'label': '字符串处理', 'domain': '容器', 'level': 'basic', 'description': '索引、切片、常用方法与简单统计', 'x': 880, 'y': 320},
    {'id': 'func', 'label': '函数基础', 'domain': '函数', 'level': 'intermediate', 'description': '定义函数、参数与返回值', 'x': 1040, 'y': 250},
    {'id': 'file', 'label': '文件读写', 'domain': '工程', 'level': 'intermediate', 'description': '读取与写入文本文件', 'x': 1200, 'y': 180},
    {'id': 'except', 'label': '异常处理', 'domain': '工程', 'level': 'intermediate', 'description': 'try / except 与常见错误', 'x': 1200, 'y': 320},
    {'id': 'algo-sum', 'label': '求和与统计', 'domain': '算法入门', 'level': 'basic', 'description': '累加、计数、最大值最小值', 'x': 1360, 'y': 180},
    {'id': 'algo-search', 'label': '线性查找', 'domain': '算法入门', 'level': 'basic', 'description': '在列表中查找目标元素', 'x': 1360, 'y': 320},
    {'id': 'algo-sort', 'label': '简单排序思想', 'domain': '算法入门', 'level': 'intermediate', 'description': '理解冒泡排序的基本过程', 'x': 1520, 'y': 180},
    {'id': 'algo-dedup', 'label': '去重与频率', 'domain': '算法入门', 'level': 'intermediate', 'description': '集合去重与简单频率统计', 'x': 1520, 'y': 320},
    {'id': 'nested', 'label': '嵌套循环', 'domain': '算法入门', 'level': 'intermediate', 'description': '双重循环解决简单组合问题', 'x': 1680, 'y': 250},
]

KG_EDGES = [
    {'id': 'e1', 'source': 'intro', 'target': 'comment', 'type': 'prerequisite', 'label': '前置'},
    {'id': 'e2', 'source': 'intro', 'target': 'var', 'type': 'prerequisite', 'label': '前置'},
    {'id': 'e3', 'source': 'var', 'target': 'io', 'type': 'prerequisite', 'label': '前置'},
    {'id': 'e4', 'source': 'var', 'target': 'ops', 'type': 'prerequisite', 'label': '前置'},
    {'id': 'e5', 'source': 'ops', 'target': 'cond', 'type': 'prerequisite', 'label': '前置'},
    {'id': 'e6', 'source': 'cond', 'target': 'loop', 'type': 'prerequisite', 'label': '前置'},
    {'id': 'e7', 'source': 'loop', 'target': 'range', 'type': 'related', 'label': '相关'},
    {'id': 'e8', 'source': 'loop', 'target': 'list', 'type': 'prerequisite', 'label': '前置'},
    {'id': 'e9', 'source': 'list', 'target': 'tuple', 'type': 'related', 'label': '相关'},
    {'id': 'e10', 'source': 'list', 'target': 'dict', 'type': 'prerequisite', 'label': '前置'},
    {'id': 'e11', 'source': 'var', 'target': 'str', 'type': 'related', 'label': '相关'},
    {'id': 'e12', 'source': 'str', 'target': 'func', 'type': 'prerequisite', 'label': '前置'},
    {'id': 'e13', 'source': 'loop', 'target': 'func', 'type': 'prerequisite', 'label': '前置'},
    {'id': 'e14', 'source': 'func', 'target': 'file', 'type': 'path', 'label': '推荐路径'},
    {'id': 'e15', 'source': 'file', 'target': 'except', 'type': 'related', 'label': '相关'},
    {'id': 'e16', 'source': 'loop', 'target': 'algo-sum', 'type': 'prerequisite', 'label': '前置'},
    {'id': 'e17', 'source': 'list', 'target': 'algo-search', 'type': 'prerequisite', 'label': '前置'},
    {'id': 'e18', 'source': 'algo-sum', 'target': 'algo-sort', 'type': 'path', 'label': '推荐路径'},
    {'id': 'e19', 'source': 'list', 'target': 'algo-dedup', 'type': 'path', 'label': '推荐路径'},
    {'id': 'e20', 'source': 'loop', 'target': 'nested', 'type': 'prerequisite', 'label': '前置'},
]

KNOWLEDGE_KEY_TO_NODE = {
    'intro': 'intro',
    'comment': 'comment',
    'python': 'intro',
    'lang': 'intro',
    'syntax': 'var',
    'basic': 'var',
    'var': 'var',
    'io': 'io',
    'input': 'io',
    'ops': 'ops',
    'cond': 'cond',
    'condition': 'cond',
    'loop': 'loop',
    'range': 'range',
    'list': 'list',
    'tuple': 'tuple',
    'set': 'tuple',
    'dict': 'dict',
    'str': 'str',
    'string': 'str',
    'func': 'func',
    'function': 'func',
    'file': 'file',
    'except': 'except',
    'exception': 'except',
    'algo': 'algo-sum',
    'algo-sum': 'algo-sum',
    'algo-search': 'algo-search',
    'algo-sort': 'algo-sort',
    'algo-dedup': 'algo-dedup',
    'nested': 'nested',
    'stage1': 'intro',
    'stage2': 'cond',
    'stage3': 'list',
    'stage4': 'algo-sum',
}


class KnowledgeGraphService:
    @staticmethod
    def _default_node_id() -> str:
        return 'var'

    @staticmethod
    def _node_stats(user_id: int) -> dict[str, dict]:
        stats: dict[str, dict] = defaultdict(lambda: {'answered': 0, 'correct': 0, 'fail_count': 0})
        rows = TrialQuestionProgress.query.filter(
            TrialQuestionProgress.user_id == user_id,
            TrialQuestionProgress.status == 'completed',
        ).all()
        default_node = KnowledgeGraphService._default_node_id()
        for row in rows:
            question = TrialQuestion.query.get(row.question_id)
            key = (question.knowledge_key if question else None) or 'var'
            node_id = KNOWLEDGE_KEY_TO_NODE.get(key.lower(), default_node)
            bucket = stats[node_id]
            bucket['answered'] += 1
            if row.is_correct:
                bucket['correct'] += 1
        for item in MistakeService.list_weak_knowledge(user_id, limit=20):
            node_id = KNOWLEDGE_KEY_TO_NODE.get(item['knowledge_key'].lower(), default_node)
            stats[node_id]['fail_count'] = max(stats[node_id]['fail_count'], item.get('fail_count', 0))
        return stats

    @staticmethod
    def _resolve_status(node_id: str, stats: dict, recommended_ids: set[str]) -> str:
        bucket = stats.get(node_id, {'answered': 0, 'correct': 0, 'fail_count': 0})
        answered = bucket['answered']
        if node_id in recommended_ids:
            return 'recommended'
        if bucket['fail_count'] >= 2 or (answered >= 1 and answered and bucket['correct'] / answered < 0.4):
            return 'weak'
        if answered >= 2 and bucket['correct'] / answered >= 0.8:
            return 'mastered'
        if answered >= 1:
            return 'learning'
        return 'unlearned'

    @staticmethod
    def get_student_graph(user_id: int) -> dict:
        stats = KnowledgeGraphService._node_stats(user_id)
        recommended_ids = set()
        default_node = KnowledgeGraphService._default_node_id()
        if User.query.get(user_id):
            rec = RecommendationService.get_student_recommendations(user_id, '7d')
            for weak in rec.get('weak_knowledge') or []:
                node_id = KNOWLEDGE_KEY_TO_NODE.get(weak['knowledge_key'].lower(), default_node)
                recommended_ids.add(node_id)
        nodes = []
        for base in KG_NODES:
            nodes.append({
                **base,
                'status': KnowledgeGraphService._resolve_status(base['id'], stats, recommended_ids),
            })
        return {'nodes': nodes, 'edges': KG_EDGES, 'scope': 'student', 'user_id': user_id}

    @staticmethod
    def get_class_graph(class_id: int) -> dict:
        students = User.query.filter_by(class_id=class_id).all()
        weak_counter: Counter[str] = Counter()
        mastery_counter: Counter[str] = Counter()
        for student in students:
            stats = KnowledgeGraphService._node_stats(student.id)
            for node_id, bucket in stats.items():
                if bucket['answered'] >= 1 and bucket['correct'] / bucket['answered'] < 0.4:
                    weak_counter[node_id] += 1
                if bucket['answered'] >= 2 and bucket['correct'] / bucket['answered'] >= 0.8:
                    mastery_counter[node_id] += 1
        total = max(len(students), 1)
        nodes = []
        for base in KG_NODES:
            weak_ratio = weak_counter[base['id']] / total
            master_ratio = mastery_counter[base['id']] / total
            if weak_ratio >= 0.35:
                status = 'weak'
            elif master_ratio >= 0.5:
                status = 'mastered'
            elif weak_counter[base['id']] > 0 or mastery_counter[base['id']] > 0:
                status = 'learning'
            else:
                status = 'unlearned'
            nodes.append({**base, 'status': status, 'weak_count': weak_counter[base['id']], 'student_count': total})
        return {
            'nodes': nodes,
            'edges': KG_EDGES,
            'scope': 'class',
            'class_id': class_id,
            'student_count': len(students),
        }

    @staticmethod
    def get_admin_graph() -> dict:
        nodes = [{**base, 'status': 'unlearned'} for base in KG_NODES]
        return {'nodes': nodes, 'edges': KG_EDGES, 'scope': 'admin'}
