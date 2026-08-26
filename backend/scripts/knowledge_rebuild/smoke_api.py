# -*- coding: utf-8 -*-
"""知识点重排后的接口冒烟：8 域全解锁 / 26 节点 / 每节点题量。

`create_app()` 会起非守护后台线程，跑完后进程不会自己退出，所以最后用 os._exit。
"""
from __future__ import annotations

import logging
import os
import sys
from collections import Counter
from pathlib import Path

logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('neo4j').setLevel(logging.ERROR)

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import create_app  # noqa: E402
from app.models import Problem, User, db  # noqa: E402


def main() -> int:
    app = create_app()
    failures: list[str] = []

    with app.app_context():
        from app.data.knowledge_node_registry import KNOWLEDGE_DOMAINS, all_node_ids
        from app.services.knowledge_graph import KnowledgeGraphService
        from app.services.practice_question import PracticeQuestionService
        from app.services.student_progress import StudentProgressService

        node_ids = all_node_ids()
        print(f'注册表：{len(KNOWLEDGE_DOMAINS)} 个大类 / {len(node_ids)} 个节点')

        counts = Counter(
            row.kg_node_id
            for row in Problem.query.filter(Problem.is_active.is_(True)).all()
        )
        thin = [nid for nid in node_ids if counts.get(nid, 0) < 4]
        print(f'题量：合计 {sum(counts.values())}，最少的节点 {min(counts.get(n, 0) for n in node_ids)} 道')
        if thin:
            failures.append(f'不足 4 题的节点：{thin}')

        graph = KnowledgeGraphService.get_admin_graph()
        print(f'知识图谱：{len(graph["nodes"])} 节点 / {len(graph["edges"])} 条边')
        if len(graph['nodes']) != len(node_ids):
            failures.append(f'图谱节点数 {len(graph["nodes"])} != 注册表 {len(node_ids)}')

        student = User.query.filter(User.role.has(name='student')).first()
        if not student:
            failures.append('库里没有学生账号，跳过学情接口')
        else:
            path = StudentProgressService.get_learning_path(student.id)
            locked_domains = [d['key'] for d in path['domains'] if d['locked']]
            locked_nodes = [n['id'] for n in path['ordered_nodes'] if n['locked']]
            print(f'学习路径（{student.username}）：{len(path["domains"])} 域 / {len(path["ordered_nodes"])} 节点')
            print(f'  锁住的域 {locked_domains or "无"}；锁住的节点 {locked_nodes or "无"}')
            if locked_domains:
                failures.append(f'仍有星域被锁：{locked_domains}')
            if locked_nodes:
                failures.append(f'仍有节点被锁：{locked_nodes}')
            if len(path['domains']) != len(KNOWLEDGE_DOMAINS):
                failures.append(f'学习路径星域数 {len(path["domains"])}')
            if len(path['ordered_nodes']) != len(node_ids):
                failures.append(
                    f'学习路径只返回 {len(path["ordered_nodes"])} 个节点，应为 {len(node_ids)}'
                )

        practice = PracticeQuestionService.list_for_student()
        by_node = Counter(item['knowledge_key'] for item in practice)
        print(f'练习题接口：{len(practice)} 道，覆盖 {len(by_node)} 个节点')
        if len(practice) < 100:
            failures.append(f'练习题只返回 {len(practice)} 道，疑似没走统一题库')

        loop_only = PracticeQuestionService.list_for_student(knowledge_key='loop')
        print(f'  按旧 key "loop" 过滤：{len(loop_only)} 道（应全部落在 loop-for）')
        if not loop_only:
            failures.append('旧 knowledge_key 过滤取不到题')

        db.session.remove()

    if failures:
        print('\n[FAIL]')
        for item in failures:
            print(f'  - {item}')
        return 1
    print('\n[OK] 冒烟全部通过')
    return 0


if __name__ == '__main__':
    code = main()
    sys.stdout.flush()
    os._exit(code)
