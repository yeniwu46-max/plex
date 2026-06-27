# -*- coding: utf-8 -*-
"""多智能体编排服务（对接 agents.crew）。"""

from agents.crew import backend_name, get_agents_status, run_learning_path_plan, run_student_diagnose, run_teacher_suggestion
from app.data.knowledge_node_registry import kg_node_to_scope_map
from app.services.mistake import MistakeService

_KG_NODE_TO_SCOPE = kg_node_to_scope_map()


class AgentOrchestrator:
    @staticmethod
    def backend_name() -> str:
        return backend_name()

    @staticmethod
    def _knowledge_mastery(user_id: int) -> list[dict]:
        """把学生知识图谱节点状态映射为诊断引擎可用的掌握度列表。"""
        try:
            from app.services.knowledge_graph import KnowledgeGraphService

            graph = KnowledgeGraphService.get_student_graph(user_id)
        except Exception:
            return []
        mastery: list[dict] = []
        for node in graph.get('nodes', []):
            status = node.get('status', 'unknown')
            for scope_name in _KG_NODE_TO_SCOPE.get(node.get('id'), []):
                mastery.append({'name': scope_name, 'status': status})
        return mastery

    @staticmethod
    def student_diagnose(user_id: int | None, payload: dict) -> dict:
        enriched = dict(payload)
        if user_id:
            enriched['user_id'] = user_id
            if not enriched.get('recentMistakes'):
                try:
                    enriched['recentMistakes'] = MistakeService.list_recent_with_meta(user_id, limit=8)
                except Exception:
                    enriched['recentMistakes'] = []
            if not enriched.get('knowledgeMastery'):
                enriched['knowledgeMastery'] = AgentOrchestrator._knowledge_mastery(user_id)
        if not enriched.get('questionRequirements'):
            enriched['questionRequirements'] = (
                enriched.get('questionPrompt') or enriched.get('questionTitle') or ''
            )
        return run_student_diagnose(enriched)

    @staticmethod
    def diagnose_learning_overview(user_id: int) -> dict:
        """Run the diagnosis crew against the student's persisted mistake evidence.

        This is intentionally separate from a single code-submission diagnosis: the
        messenger has no editor payload, but it does have a reliable server-side
        record of the student's active mistakes and their execution metadata.
        """
        mistakes = MistakeService.list_for_student(user_id, active_only=True)
        recent = MistakeService.list_recent_with_meta(user_id, limit=8)
        focus = mistakes[0] if mistakes else {}
        meta = focus.get('meta') if isinstance(focus.get('meta'), dict) else {}
        error_types = focus.get('error_types') or []
        error_summary = '；'.join(str(item) for item in error_types if item) or str(
            focus.get('error_type') or ''
        )
        knowledge_points = [
            str(item.get('knowledge_label') or item.get('knowledge_key'))
            for item in mistakes[:3]
            if item.get('knowledge_label') or item.get('knowledge_key')
        ]
        payload = {
            'exerciseId': str(focus.get('question_id') or focus.get('question_ref') or 'learning-overview'),
            'questionTitle': str(focus.get('question_title') or '近期学习表现'),
            'questionPrompt': str(meta.get('stem_preview') or focus.get('question_title') or ''),
            # Historical mistakes do not always retain submitted source.  The
            # diagnosis engine still uses stderr, error type and mistake history;
            # a harmless placeholder keeps its input contract explicit.
            'code': str(meta.get('code') or '# 从近期错题记录生成学习诊断'),
            'stderr': error_summary,
            'knowledgePoints': knowledge_points or ['Python 基础'],
            'attemptCount': int(focus.get('fail_count') or 0),
            'answerStatus': 'wrong' if focus else 'correct',
            'recentMistakes': recent,
        }
        return AgentOrchestrator.student_diagnose(user_id, payload)

    @staticmethod
    def run_code_learning_cycle(user_id: int, payload: dict) -> dict:
        """One reliable endpoint for sandbox evidence and the full learning loop."""
        from app.services.learning_cycle import LearningCycleService

        return LearningCycleService.execute(user_id, payload)

    @staticmethod
    def plan_learning_path(user_id: int | None, payload: dict | None = None) -> dict:
        body = dict(payload or {})
        if user_id:
            body['user_id'] = user_id
        return run_learning_path_plan(body)

    @staticmethod
    def code_hint(payload: dict) -> dict:
        code = str(payload.get('code') or '').rstrip()
        question_title = str(payload.get('questionTitle') or payload.get('exerciseId') or '当前题目')
        topic = str(payload.get('topic') or '')
        expected = str(payload.get('expectedOutput') or '').strip()
        actual = str(payload.get('stdout') or '').strip()
        stderr = str(payload.get('stderr') or '').strip()
        failed_cases = payload.get('failedCases') or []

        comments: list[str] = []
        if stderr:
            comments.append('先处理运行错误，定位报错行附近的变量名、缩进或类型。')
        elif expected or actual:
            comments.append('对比实际输出和预期输出，优先检查格式、边界条件和循环范围。')
        else:
            comments.append('先补齐核心思路，再运行测试收集更具体的反馈。')

        if failed_cases:
            label = failed_cases[0].get('label') if isinstance(failed_cases[0], dict) else str(failed_cases[0])
            comments.append(f'重点复查未通过用例「{label}」覆盖的输入场景。')
        if topic:
            comments.append(f'本题关联「{topic}」，先确认这一知识点在代码里有对应实现。')
        comments.append('不要直接改成固定输出，应该让代码能处理同类输入。')

        header = [
            '# AI 提示（不会直接给答案）',
            f'# 题目：{question_title}',
            *[f'# - {item}' for item in comments[:4]],
            '',
        ]
        lines = code.splitlines() or ['']
        annotated_lines: list[str] = []
        inserted_focus = False
        for index, line in enumerate(lines):
            stripped = line.strip()
            if not inserted_focus and stripped and not stripped.startswith('#'):
                annotated_lines.append('# TODO: 从这里开始检查变量、条件和输出是否符合题意')
                inserted_focus = True
            annotated_lines.append(line)
            if (
                not inserted_focus
                and index == len(lines) - 1
            ):
                annotated_lines.append('# TODO: 在这里补充解题逻辑，再运行测试观察差异')

        return {
            'annotated_code': '\n'.join(header + annotated_lines).rstrip() + '\n',
            'comments': comments[:4],
            'policy': 'hint_only_no_direct_answer',
            'backend': AgentOrchestrator.backend_name(),
        }

    @staticmethod
    def teacher_suggestion(user_id: int | None, payload: dict | None = None) -> dict:
        body = dict(payload or {})
        if user_id and not body.get('weakPointStats'):
            weak = MistakeService.list_weak_knowledge(user_id, limit=5)
            body['weakPointStats'] = [
                {'knowledgePoint': w['knowledge_label'], 'count': w.get('mistake_count', 1)}
                for w in weak
            ]
        return run_teacher_suggestion(body)

    @staticmethod
    def agents_status() -> dict:
        return {
            'agents': get_agents_status(),
            'backend': backend_name(),
        }

    # ---- 兼容旧版分散接口 ----

    @staticmethod
    def diagnose(user_id: int | None, payload: dict) -> dict:
        result = AgentOrchestrator.student_diagnose(user_id, payload)
        d = result['diagnosis']
        return {
            'agent': 'LearningDiagnosisAgent',
            'status': 'completed',
            'weak_points': d['weakPoints'],
            'error_types': [{'type': d['errorType'], 'explanation': d['diagnosis']}],
            'overall_assessment': d['diagnosis'],
            'confidence': d['confidence'],
            'diagnosed_at': result.get('completedAt'),
            'backend': result.get('backend'),
        }

    @staticmethod
    def recommend_path(payload: dict) -> dict:
        user_id = payload.get('user_id')
        if user_id:
            result = AgentOrchestrator.plan_learning_path(int(user_id), payload)
        else:
            from agents import learning_path_agent
            result = learning_path_agent.execute(payload)
        steps = [
            {'step': i + 1, 'node': n.get('label', n.get('id')), 'action': 'practice'}
            for i, n in enumerate(result.get('ordered_nodes', [])[:4])
        ]
        return {
            'agent': 'LearningPathAgent',
            'status': 'completed',
            'path': {
                'title': '下一步：' + result.get('nextKnowledgePoint', ''),
                'steps': steps,
                'total_nodes': len(result.get('ordered_nodes', [])),
            },
            'ordered_nodes': result.get('ordered_nodes'),
            'next_best_action': result.get('next_best_action'),
            'remediation_paths': result.get('remediation_paths'),
            'confidence': 0.86,
            'recommended_at': result,
            'backend': backend_name(),
        }

    @staticmethod
    def analyze_code(payload: dict) -> dict:
        from agents import code_analysis_agent

        analysis = code_analysis_agent.execute(payload)
        return {
            'agent': 'CodeAnalysisAgent',
            'status': 'completed',
            'error_type': analysis.get('codeIssueSummary', ''),
            'explanation': analysis.get('possibleCause', ''),
            'suggestions': [analysis.get('fixDirection', '')],
            'code_analysis': analysis,
            'analyzed_at': analysis,
            'backend': backend_name(),
        }

    @staticmethod
    def generate_feedback(payload: dict) -> dict:
        from agents import feedback_agent

        fb = feedback_agent.execute(payload)
        return {
            'agent': 'FeedbackAgent',
            'status': 'completed',
            'feedback': {
                'summary': fb['shortFeedback'],
                'encouragement': fb['encouragement'],
                'next_action': fb['nextAction'],
                'step_hints': fb['stepHints'],
            },
            'generated_at': fb,
            'backend': backend_name(),
        }
