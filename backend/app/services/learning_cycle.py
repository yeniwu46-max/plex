"""Reliable, student-facing multi-agent code learning cycle.

The cycle deliberately keeps the sandbox result authoritative.  Agents enrich
that evidence; they never replace it.  Every optional LLM call has a local,
structured fallback so a model or network failure cannot turn a coding attempt
into a 5xx response.
"""
from __future__ import annotations

import time
from typing import Any

from agents.crew import run_student_diagnose
from app.services.code_execution import CodeExecutionService
from app.services.evaluation import EvaluationService
from app.services.iflytek_spark import IflytekSparkService
from app.services.knowledge_graph import KnowledgeGraphService
from app.services.mistake import MistakeService
from app.services.student_profile import StudentProfileService
from app.utils.time import utc_now


class LearningCycleService:
    """Orchestrate one submit -> diagnose -> remediate -> verify learning loop."""

    @staticmethod
    def _trace(agent_id: str, name: str, summary: str, started: float, backend: str = 'local_rules') -> dict:
        return {
            'agentId': agent_id,
            'name': name,
            'role': name,
            'status': 'success',
            'latencyMs': round((time.perf_counter() - started) * 1000, 1),
            'summary': summary,
            'backend': backend,
        }

    @staticmethod
    def _knowledge_key(payload: dict, subtype: str) -> str:
        values = [str(payload.get('topic') or ''), *[str(item) for item in payload.get('knowledgePoints') or []]]
        if subtype.startswith('while_') or any('循环' in item or 'loop' in item.lower() for item in values):
            return 'loop'
        return str((payload.get('knowledgeKeys') or ['loop'])[0] or 'loop')

    @staticmethod
    def _profile_snapshot(user_id: int, payload: dict, graph: dict) -> dict:
        dimensions: dict[str, Any] = {}
        try:
            dimensions = StudentProfileService.get_or_create(user_id).dimensions or {}
        except Exception:
            pass

        raw_preference = str(
            payload.get('learningPreference')
            or (dimensions.get('explanation_preference') or {}).get('value')
            or ''
        )
        visual = any(word in raw_preference.lower() for word in ('图', '图解', 'visual', '流程图', 'diagram'))
        loop_node = next((node for node in graph.get('nodes', []) if node.get('id') == 'loop'), {})
        return {
            'explanationPreference': raw_preference or ('图解优先' if visual else '待持续确认'),
            'visualPreferenceConfirmed': visual,
            'interventionPresentation': '变量执行图' if visual else '变量执行图（由当前循环诊断策略触发）',
            'loopMastery': loop_node.get('status', 'recommended'),
            'loopMasteryScore': loop_node.get('mastery_score'),
            'evidence': [
                '学生画像中的讲解偏好' if visual else '当前缺少明确图解偏好证据，使用诊断策略提供图示支持',
                f"循环节点状态：{loop_node.get('status', 'recommended')}",
            ],
        }

    @staticmethod
    def _local_resources() -> dict:
        return {
            'executionDiagram': {
                'title': '循环变量执行图',
                'description': '每轮循环都必须让条件相关变量向退出条件推进。',
                'steps': [
                    {'round': 0, 'condition': 'i < 3', 'i': 0, 'action': '进入循环'},
                    {'round': 1, 'condition': 'i < 3', 'i': 0, 'action': '打印后执行 i += 1'},
                    {'round': 2, 'condition': 'i < 3', 'i': 1, 'action': '继续推进变量'},
                    {'round': 3, 'condition': 'i < 3', 'i': 3, 'action': '条件为假，安全退出'},
                ],
            },
            'microFix': {
                'title': '微型修复题：让循环停下来',
                'prompt': '在不改变循环条件的前提下，只补一行代码，使 i 从 0 递增到 3 后退出。',
                'starterCode': 'i = 0\nwhile i < 3:\n    print(i)\n    # 在这里补一行',
                'expectedOutcome': '依次输出 0、1、2，随后退出循环。',
                'answerPolicy': '只给目标和追问，不直接展示修复代码。',
            },
            'backend': 'local_rules',
        }

    @classmethod
    def _resources(cls, profile: dict) -> dict:
        resources = cls._local_resources()
        if not IflytekSparkService.configured():
            return resources
        prompt = (
            '只输出 JSON 对象，键为 tutorQuestion 和 diagramCaption。'
            '针对 Python while 循环变量未更新，不能给出完整修复代码；'
            'tutorQuestion 必须是一个启发式问题，diagramCaption 不超过40字。'
            f'学习画像：{profile}'
        )
        try:
            generated = IflytekSparkService.chat_json('你是严谨的编程教育资源生成智能体。', prompt, timeout=5)
            question = generated.get('tutorQuestion') if isinstance(generated, dict) else None
            caption = generated.get('diagramCaption') if isinstance(generated, dict) else None
            if isinstance(question, str) and question.strip():
                resources['tutorQuestion'] = question.strip()[:180]
            if isinstance(caption, str) and caption.strip():
                resources['executionDiagram']['description'] = caption.strip()[:80]
            resources['backend'] = 'iflytek_spark'
        except Exception:
            # The resource contract remains usable even when Spark is unavailable.
            pass
        return resources

    @staticmethod
    def _tutor(resources: dict, passed: bool) -> dict:
        if passed:
            return {
                'mode': 'reflection',
                'question': '现在代码能退出了：是哪一行让循环条件最终变为假？如果把它删掉会发生什么？',
                'nextAction': '用自己的话解释变量如何变化，再提交一次微型修复题。',
            }
        return {
            'mode': 'socratic',
            'question': resources.get('tutorQuestion') or '如果 i 的值始终不变，while i < 3 这个条件有机会变成假吗？你准备在哪一行让 i 变化？',
            'nextAction': '先在变量执行图中标出 i 的每一轮值，再只修改一行并重新运行测试。',
        }

    @staticmethod
    def _report(user_id: int, passed: bool, profile: dict, path_label: str, diagnosis: dict) -> dict:
        try:
            base = EvaluationService.get_student_learning_report(user_id, '7d')
        except Exception:
            base = {'summary': {}, 'recommendations': [], 'weak_knowledge': []}
        action = '已通过测试，继续巩固循环变量变化。' if passed else f'回退到「{path_label}」，完成变量图和微型修复题后再测。'
        return {
            'headline': '本次代码学习闭环报告',
            'generatedAt': utc_now().isoformat() + 'Z',
            'outcome': 'passed' if passed else 'needs_remediation',
            'diagnosis': diagnosis.get('diagnosis', ''),
            'learningProfile': profile,
            'nextActions': [action, '保留本次执行证据，下一次提交将继续更新循环节点。'],
            'weeklySnapshot': base.get('summary') or {},
            'riskTags': base.get('risk_tags') or [],
        }

    @classmethod
    def execute(cls, user_id: int, payload: dict) -> dict:
        """Return a complete, serializable result for both failure and success paths."""
        code = str(payload.get('code') or '')
        language = str(payload.get('language') or 'python')
        test_cases = payload.get('test_cases') or []
        if not code.strip():
            raise ValueError('code required')
        if not isinstance(test_cases, list) or not test_cases:
            raise ValueError('test_cases required')

        started = time.perf_counter()
        execution = CodeExecutionService.submit(language, code, test_cases, str(payload.get('run_mode') or 'stdout'))
        trace = [cls._trace(
            'code_sandbox', '代码沙箱',
            '检测到超时，已保留执行证据。' if any(item.get('status', {}).get('id') == 5 for item in execution['results'])
            else ('测试全部通过。' if execution['all_passed'] else '测试未通过，开始协同诊断。'),
            started, execution.get('backend', 'mock'),
        )]

        failed = next((item for item in execution['results'] if not item.get('passed')), {})
        status_id = int((failed.get('status') or {}).get('id') or 3)
        answer_status = 'correct' if execution['all_passed'] else 'wrong'
        diagnose_payload = {
            'user_id': user_id,
            'exerciseId': payload.get('exerciseId') or payload.get('question_id') or 'code-cycle',
            'code': code,
            'stdout': failed.get('actual') or '',
            'stderr': failed.get('error') or ('Execution timed out' if status_id == 5 else ''),
            'expectedOutput': failed.get('expected') or '',
            'knowledgePoints': payload.get('knowledgePoints') or [payload.get('topic') or '循环变量变化'],
            'attemptCount': int(payload.get('attemptCount') or 1),
            'answerStatus': answer_status,
            'questionTitle': payload.get('questionTitle') or '循环变量变化',
            'questionPrompt': payload.get('questionPrompt') or '',
        }
        agent_result = run_student_diagnose(diagnose_payload)
        diagnosis = agent_result['diagnosis']
        subtype = str(diagnosis.get('errorSubtype') or '')
        knowledge_key = cls._knowledge_key(payload, subtype)

        # Persist the evidence before reading the graph; graph status is derived from this record.
        MistakeService.record_code_trial_run(user_id, {
            'question_id': diagnose_payload['exerciseId'],
            'question_title': diagnose_payload['questionTitle'],
            'knowledge_key': knowledge_key,
            'topic': payload.get('topic') or '循环变量变化',
            'tags': payload.get('knowledgePoints') or [],
            'cases': execution['results'],
            'error_layer': diagnosis.get('errorLayer'),
            'error_subtype': diagnosis.get('errorSubtype'),
        })
        graph = KnowledgeGraphService.get_student_graph(user_id)
        profile_started = time.perf_counter()
        profile = cls._profile_snapshot(user_id, payload, graph)
        trace.append(cls._trace('learning_profile', '学习画像智能体',
            f"循环掌握度为 {profile['loopMastery']}；{profile['interventionPresentation']}。", profile_started))

        path_started = time.perf_counter()
        path_label = '循环变量变化' if not execution['all_passed'] else agent_result['recommendation'].get('nextKnowledgePoint', '循环变量变化')
        learning_path = {
            **agent_result['recommendation'],
            'nextKnowledgePoint': path_label,
            'reason': '循环条件关联变量未更新，先修复循环变量变化再继续后续任务。' if not execution['all_passed'] else '测试通过，保持循环知识点的巩固练习。',
        }
        trace.append(cls._trace('learning_path', '路径智能体', f"建议：{path_label}", path_started))

        resource_started = time.perf_counter()
        resources = cls._resources(profile)
        trace.append(cls._trace('resource_generation', '资源生成智能体', '生成变量执行图与微型修复题。', resource_started, resources['backend']))
        tutor_started = time.perf_counter()
        tutor = cls._tutor(resources, execution['all_passed'])
        trace.append(cls._trace('dialogue_tutor', '对话辅导智能体', '已生成启发式追问，不直接给出答案。', tutor_started, resources['backend']))

        node = next((item for item in graph.get('nodes', []) if item.get('id') == 'loop'), {})
        graph_update = {
            'nodeId': 'loop',
            'nodeLabel': node.get('label', '循环'),
            'status': node.get('status', 'recommended'),
            'action': 'consolidated' if execution['all_passed'] else 'reinforce',
            'evidence': '测试通过并清除该题活跃错误。' if execution['all_passed'] else '超时/失败记录已写入，循环节点进入补强路径。',
        }
        trace.append(cls._trace('knowledge_graph_update', '知识图谱智能体', graph_update['evidence'], time.perf_counter()))
        report_started = time.perf_counter()
        report = cls._report(user_id, execution['all_passed'], profile, path_label, diagnosis)
        trace.append(cls._trace('learning_report', '学习报告智能体', '已生成本次个性化学习报告。', report_started))

        return {
            **agent_result,
            'execution': execution,
            'learningProfile': profile,
            'learningPath': learning_path,
            'resources': resources,
            'tutor': tutor,
            'knowledgeGraphUpdate': graph_update,
            'learningReport': report,
            'pipelineTrace': trace + (agent_result.get('pipelineTrace') or []),
            'backend': resources['backend'] if resources['backend'] == 'iflytek_spark' else agent_result.get('backend', 'local_rules'),
            'completedAt': utc_now().isoformat() + 'Z',
        }
