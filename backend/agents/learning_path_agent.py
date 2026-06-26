# -*- coding: utf-8 -*-
"""学习路径智能体：LangGraph 编排 + 确定性路径规划。"""
from __future__ import annotations

ROLE = 'Python 学习路径规划师'
GOAL = '将知识图谱转化为可执行的学习路线，含前置、顺序、掌握度、资源与补救'
BACKSTORY = (
    '你坚持先补前置、不跳级，结合掌握度缺口推荐下一步，'
    '并为薄弱点生成补救微练习路径。'
)


def execute(payload: dict) -> dict:
    from agents.graphs.learning_path_graph import run_learning_path_graph

    return run_learning_path_graph(payload)
