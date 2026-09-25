# -*- coding: utf-8 -*-
"""Knowledge Intelligence Layer（知识图谱 + 向量知识库 + 个性化 Graph-enhanced RAG）。

对外统一入口：``KnowledgeService``。其余模块为内部实现，Agent / 路由不应直接依赖 providers。
"""
from .knowledge_service import KnowledgeService

__all__ = ['KnowledgeService']
