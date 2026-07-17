"""统一智能体注册表 — 与前端 gradingAgents.ts / PlexAgentFlow 节点 ID 对齐。"""

from __future__ import annotations

from typing import Any

# 教师检查智能体（grading）
GRADING_AGENTS: list[dict[str, Any]] = [
    {
        'id': 'answer-correctness',
        'name': '标准答案比对智能体',
        'nameEn': 'Answer Correctness Agent',
        'description': '对照参考答案与评分要点，判定客观题与填空题正误。',
        'category': 'correctness',
        'checkType': 'answer_match',
        'role': 'grading',
        'status': 'ready',
        'mandatoryFor': ['mcq'],
        'learningAgentId': None,
    },
    {
        'id': 'code-syntax',
        'name': '代码语法审查智能体',
        'nameEn': 'Code Syntax Agent',
        'description': '静态分析 Python 代码语法、缩进与命名规范，标记可修复问题。',
        'category': 'code',
        'checkType': 'syntax_check',
        'role': 'grading',
        'status': 'ready',
        'mandatoryFor': [],
        'learningAgentId': 'code_analysis',
    },
    {
        'id': 'sandbox-runtime',
        'name': '沙箱运行验证智能体',
        'nameEn': 'Sandbox Runtime Agent',
        'description': '在隔离沙箱执行学生代码，比对输出与边界用例。',
        'category': 'code',
        'checkType': 'runtime_verify',
        'role': 'grading',
        'status': 'ready',
        'mandatoryFor': ['coding'],
        'learningAgentId': None,
    },
    {
        'id': 'logic-step',
        'name': '解题步骤逻辑智能体',
        'nameEn': 'Logic Step Agent',
        'description': '逐步审查推导链是否完整，识别跳步与逻辑漏洞。',
        'category': 'logic',
        'checkType': 'logic_chain',
        'role': 'grading',
        'status': 'ready',
        'mandatoryFor': [],
        'learningAgentId': 'learning_diagnosis',
    },
    {
        'id': 'knowledge-coverage',
        'name': '知识点覆盖检查智能体',
        'nameEn': 'Knowledge Coverage Agent',
        'description': '核对作答是否覆盖试炼关联知识点与能力项。',
        'category': 'logic',
        'checkType': 'knowledge_coverage',
        'role': 'grading',
        'status': 'ready',
        'mandatoryFor': [],
        'learningAgentId': 'knowledge_graph',
    },
    {
        'id': 'rubric-alignment',
        'name': '评分细则对齐智能体',
        'nameEn': 'Rubric Alignment Agent',
        'description': '按教师配置的评分量表逐项打分并给出扣分依据。',
        'category': 'feedback',
        'checkType': 'rubric_scoring',
        'role': 'grading',
        'status': 'ready',
        'mandatoryFor': [],
        'learningAgentId': 'feedback',
    },
    {
        'id': 'feedback-coach',
        'name': '个性化反馈教练智能体',
        'nameEn': 'Feedback Coach Agent',
        'description': '基于错因生成可操作建议与下一道巩固题推荐。',
        'category': 'feedback',
        'checkType': 'student_feedback',
        'role': 'grading',
        'status': 'ready',
        'mandatoryFor': [],
        'learningAgentId': 'feedback',
    },
    {
        'id': 'plagiarism-guard',
        'name': '抄袭相似度检测智能体',
        'nameEn': 'Plagiarism Guard Agent',
        'description': '比对同班历史提交与公开题解，标记异常相似片段。',
        'category': 'integrity',
        'checkType': 'plagiarism_scan',
        'role': 'grading',
        'status': 'beta',
        'mandatoryFor': [],
        'learningAgentId': None,
    },
]

# 学习协同流水线（learning）— PlexAgentFlow 节点
LEARNING_PIPELINE_AGENTS: list[dict[str, Any]] = [
    {
        'id': 'learning_diagnosis',
        'flowNodeId': 'diagnose',
        'name': '学习诊断智能体',
        'nameEn': 'Learning Diagnostics',
        'description': '分析学生答题记录与代码运行结果，识别薄弱点',
        'role': 'learning',
    },
    {
        'id': 'code_analysis',
        'flowNodeId': 'code',
        'name': '代码分析智能体',
        'nameEn': 'Code Analyzer',
        'description': '解析编译错误、运行时错误与逻辑问题',
        'role': 'learning',
    },
    {
        'id': 'knowledge_graph',
        'flowNodeId': 'kg',
        'name': '知识图谱智能体',
        'nameEn': 'Knowledge Graph',
        'description': '基于知识图谱定位相关前置知识与关联节点',
        'role': 'learning',
    },
    {
        'id': 'learning_path',
        'flowNodeId': 'path',
        'name': '路径推荐智能体',
        'nameEn': 'Path Planner',
        'description': '结合能力画像生成个性化学习路径',
        'role': 'learning',
    },
    {
        'id': 'feedback',
        'flowNodeId': 'feedback',
        'name': '反馈生成智能体',
        'nameEn': 'Feedback Generator',
        'description': '整合诊断与路径结果，生成自然语言学习反馈',
        'role': 'learning',
    },
    {
        'id': 'teacher_assistant',
        'flowNodeId': 'teacher',
        'name': '教师助理智能体',
        'nameEn': 'Teacher Assistant',
        'description': '汇总班级数据，生成教学干预建议与讲解重点',
        'role': 'learning',
    },
    {
        'id': 'trial_error_diagnosis',
        'flowNodeId': 'trial-error',
        'name': '报错分析智能体',
        'nameEn': 'Trial Error Diagnosis',
        'description': '分析运行报错与未通过用例，用引导式提问帮助学生定位问题，不直接给答案',
        'role': 'learning',
    },
    {
        'id': 'trial_code_quality',
        'flowNodeId': 'trial-quality',
        'name': '代码质量分析智能体',
        'nameEn': 'Trial Code Quality',
        'description': '评价代码结构与可读性，给出改进方向但不提供可直接提交的解法',
        'role': 'learning',
    },
    {
        'id': 'trial_optimization',
        'flowNodeId': 'trial-optimize',
        'name': '优化建议智能体',
        'nameEn': 'Trial Optimization Coach',
        'description': '提出效率与结构优化思路，禁止输出完整答案代码',
        'role': 'learning',
    },
]

GRADING_AGENT_MAP = {item['id']: item for item in GRADING_AGENTS}
LEARNING_AGENT_MAP = {item['id']: item for item in LEARNING_PIPELINE_AGENTS}

DEFAULT_ORCHESTRATION = {
    'enabled': True,
    'grading_agents': [
        'answer-correctness',
        'sandbox-runtime',
        'feedback-coach',
    ],
    'learning_pipeline': [
        'learning_diagnosis',
        'code_analysis',
        'knowledge_graph',
        'feedback',
    ],
}


def normalize_orchestration(raw: dict | None) -> dict:
    base = {
        'enabled': bool(DEFAULT_ORCHESTRATION['enabled']),
        'grading_agents': list(DEFAULT_ORCHESTRATION['grading_agents']),
        'learning_pipeline': list(DEFAULT_ORCHESTRATION['learning_pipeline']),
    }
    if not raw:
        return base
    if 'enabled' in raw:
        base['enabled'] = bool(raw['enabled'])
    if isinstance(raw.get('grading_agents'), list):
        valid = [aid for aid in raw['grading_agents'] if aid in GRADING_AGENT_MAP]
        base['grading_agents'] = valid
    if isinstance(raw.get('learning_pipeline'), list):
        valid = [aid for aid in raw['learning_pipeline'] if aid in LEARNING_AGENT_MAP]
        base['learning_pipeline'] = valid
    return base


def build_runtime_info(config: dict | None = None) -> dict:
    from agents.crew import backend_name, crewai_venv_available, get_agents_health
    from agents.llm_client import api_key_configured

    cfg = normalize_orchestration(config)
    health = get_agents_health()
    backend = backend_name()
    venv_ok = crewai_venv_available()
    key_ok = api_key_configured()
    return {
        'crewai_venv': venv_ok,
        'api_key_configured': key_ok,
        'llm_available': key_ok,
        'enabled_grading_count': len(cfg.get('grading_agents') or []),
        'enabled_learning_count': len(cfg.get('learning_pipeline') or []),
        'avg_latency_ms': health.get('avg_latency_ms'),
        'success_rate': health.get('success_rate'),
        'registered_agent_count': health.get('registered_count'),
        'ready_for_llm': backend == 'crewai' and venv_ok and key_ok,
        'degraded_reason': (
            None
            if (backend == 'crewai' and venv_ok and key_ok) or (key_ok and not venv_ok)
            else (
                'missing_crewai_venv'
                if backend == 'crewai' and not venv_ok and not key_ok
                else 'missing_api_key' if backend == 'crewai' and not key_ok else None
            )
        ),
    }


def registry_payload(config: dict | None = None) -> dict:
    from agents.crew import backend_name, get_agents_status

    cfg = normalize_orchestration(config)
    return {
        'grading_agents': GRADING_AGENTS,
        'learning_pipeline_agents': LEARNING_PIPELINE_AGENTS,
        'defaults': DEFAULT_ORCHESTRATION,
        'agent_backend': backend_name(),
        'runtime_status': get_agents_status(),
        'runtime': build_runtime_info(cfg),
    }
