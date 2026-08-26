# -*- coding: utf-8 -*-
"""多智能体编排服务（对接 agents.crew）。"""

from agents.crew import backend_name, get_agents_status, run_learning_path_plan, run_student_diagnose, run_teacher_suggestion
from app.data.knowledge_node_registry import kg_node_to_scope_map
from app.services.iflytek_spark import IflytekSparkService
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
    def student_diagnose(user_id: int | None, payload: dict, *, fast: bool = False) -> dict:
        enriched = dict(payload)
        if user_id:
            enriched['user_id'] = user_id
            # The trial button already sends the current execution evidence.
            # Avoid remote graph/history enrichment on its latency-sensitive path.
            if not fast and not enriched.get('recentMistakes'):
                try:
                    enriched['recentMistakes'] = MistakeService.list_recent_with_meta(user_id, limit=8)
                except Exception:
                    enriched['recentMistakes'] = []
            if not fast and not enriched.get('knowledgeMastery'):
                enriched['knowledgeMastery'] = AgentOrchestrator._knowledge_mastery(user_id)
        if not enriched.get('questionRequirements'):
            enriched['questionRequirements'] = (
                enriched.get('questionPrompt') or enriched.get('questionTitle') or ''
            )
        return run_student_diagnose(enriched, fast=fast)

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
    def _annotate_code(code: str, question_title: str, comments: list[str], focus_hint: str | None) -> str:
        """Insert hint comments into the student's code without rewriting logic."""
        header = [
            '# AI 提示（不会直接给答案）',
            f'# 题目：{question_title}',
            *[f'# - {item}' for item in comments[:4]],
            '',
        ]
        focus = focus_hint or '从这里开始检查变量、条件和输出是否符合题意'
        lines = code.splitlines() or ['']
        annotated_lines: list[str] = []
        inserted_focus = False
        for index, line in enumerate(lines):
            stripped = line.strip()
            if not inserted_focus and stripped and not stripped.startswith('#'):
                annotated_lines.append(f'# TODO: {focus}')
                inserted_focus = True
            annotated_lines.append(line)
            if not inserted_focus and index == len(lines) - 1:
                annotated_lines.append(f'# TODO: {focus}')
        return '\n'.join(header + annotated_lines).rstrip() + '\n'

    @staticmethod
    def _spark_code_hint(payload: dict, code: str, question_title: str) -> dict:
        """Ask the real model for context-aware, hint-only feedback on the code."""
        system = (
            '你叫小E，是 A3 学习系统里陪学生做编程题的学习伙伴。你只能给启发式提示，'
            '帮助学生自己找到问题，绝对不能给出完整答案或可以直接通过测试的代码。'
            '请仔细阅读学生的真实代码、题目和失败用例，用温和具体的口吻给出针对性提示，'
            '不要提及 AI、模型或接口。'
            '只输出JSON对象：{"comments":["3到4条中文提示，针对当前代码的具体问题"],'
            '"focus_hint":"一句话指出最该先检查的位置"}。'
        )
        user_payload = {
            'question_title': question_title,
            'topic': payload.get('topic') or '',
            'student_code': code,
            'expected_output': payload.get('expectedOutput') or '',
            'actual_output': payload.get('stdout') or '',
            'error': payload.get('stderr') or '',
            'failed_cases': payload.get('failedCases') or [],
        }
        result = IflytekSparkService.chat_json(system, str(user_payload), timeout=8)
        raw_comments = result.get('comments')
        comments = [str(item).strip() for item in raw_comments if str(item).strip()] if isinstance(raw_comments, list) else []
        if not comments:
            raise ValueError('spark_code_hint_empty')
        focus_hint = str(result.get('focus_hint') or '').strip() or None
        comments = comments[:4]
        return {
            'annotated_code': AgentOrchestrator._annotate_code(code, question_title, comments, focus_hint),
            'comments': comments,
            'policy': 'hint_only_no_direct_answer',
            'backend': 'iflytek_spark',
        }

    @staticmethod
    def _rules_code_hint(payload: dict, code: str, question_title: str) -> dict:
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

        comments = comments[:4]
        return {
            'annotated_code': AgentOrchestrator._annotate_code(code, question_title, comments, None),
            'comments': comments,
            'policy': 'hint_only_no_direct_answer',
            'backend': AgentOrchestrator.backend_name(),
        }

    @staticmethod
    def trial_coach(payload: dict) -> dict:
        """试炼编程页 · 三类辅导智能体（报错/质量/优化），禁止直接给答案。"""
        from agents.trial_coach_agents import VALID_INTENTS, execute

        intent = str(payload.get('intent') or '').strip()
        if intent not in VALID_INTENTS:
            raise ValueError(f'unsupported intent: {intent}')
        return execute(intent, payload)

    @staticmethod
    def code_hint(payload: dict) -> dict:
        code = str(payload.get('code') or '').rstrip()
        question_title = str(payload.get('questionTitle') or payload.get('exerciseId') or '当前题目')

        # Prefer real, model-grounded feedback when a Spark key is configured;
        # otherwise fall back to a deterministic, still context-aware hint.
        if IflytekSparkService.configured():
            try:
                return AgentOrchestrator._spark_code_hint(payload, code, question_title)
            except Exception:
                pass
        return AgentOrchestrator._rules_code_hint(payload, code, question_title)

    @staticmethod
    def trial_feedback(user_id: int | None, payload: dict) -> dict:
        """On-demand trial feedback with a bounded, lightweight diagnosis pipeline."""
        code = str(payload.get('code') or '').strip()
        if not code:
            raise ValueError('code required')
        return AgentOrchestrator.student_diagnose(user_id, payload, fast=True)

    @staticmethod
    def messenger_quick_action(user_id: int, action: str) -> dict:
        """Contextual 小E replies for messenger shortcut buttons — LLM first."""
        from app.services.messenger_chat import MessengerChatService
        from app.services.practice_question import PracticeQuestionService

        action = (action or '').strip()
        valid = {'weak_points', 'next_trial', 'repair_path', 'recent_growth'}
        if action not in valid:
            raise ValueError(f'unsupported action: {action}')

        action_prompts = {
            'weak_points': '小E，请根据我最近 7 天的练习情况，诊断薄弱知识点并给出 2-3 条具体可执行的改进建议。',
            'next_trial': '小E，请结合我的掌握情况，推荐我接下来最该练的一类 Python 入门题，并简要说明原因。',
            'repair_path': '小E，请帮我规划一条学习修复路线，按先后顺序列出 3-4 个具体步骤。',
            'recent_growth': '小E，请总结我最近一周的学习成长情况，并指出 1-2 个需要关注的方向。',
        }

        llm = MessengerChatService.chat(user_id, action_prompts[action], [])
        result: dict = {'action': action, 'reply': llm.get('reply') or '小E 暂时无法生成回复，请稍后再试。'}

        if action == 'next_trial':
            pick = PracticeQuestionService.recommend_for_student(user_id)
            if pick:
                result['question_pick'] = {
                    'code': pick['code'],
                    'id': pick['id'],
                    'title': pick['title'],
                    'topic': pick.get('topic'),
                    'knowledge_key': pick.get('knowledge_key'),
                    'practice_path': f'/student/trials/practice/{pick["id"]}',
                }

        return result

    @staticmethod
    def _aggregate_class(class_id: int) -> dict:
        """聚合班级真实错题，产出薄弱统计、常见错误类型与学生分组所需名单。"""
        from collections import defaultdict

        from app.models import User

        students = User.query.filter_by(class_id=class_id).all()
        student_rows: list[dict] = []
        weak_counter: dict[str, int] = defaultdict(int)
        error_counter: dict[str, int] = defaultdict(int)

        for student in students:
            if not student.role or student.role.name != 'student':
                continue
            try:
                weak = MistakeService.list_weak_knowledge(student.id, limit=3)
                recent = MistakeService.list_recent_with_meta(student.id, limit=5)
                active = MistakeService.list_for_student(student.id, active_only=True)
            except Exception:
                weak, recent, active = [], [], []
            for item in weak:
                label = item.get('knowledge_label')
                if label:
                    weak_counter[label] += int(item.get('fail_count') or 1)
            for item in recent:
                err = item.get('error_type')
                if err:
                    error_counter[err] += 1
            student_rows.append({
                'id': student.id,
                'name': student.real_name or student.username,
                'weakPoints': [w['knowledge_label'] for w in weak if w.get('knowledge_label')],
                'activeCount': len(active),
            })

        weak_stats = sorted(
            ({'knowledgePoint': k, 'count': v} for k, v in weak_counter.items()),
            key=lambda x: -x['count'],
        )[:6]
        common_errors = [k for k, _ in sorted(error_counter.items(), key=lambda x: -x[1])][:4]
        attention = sorted(
            (row for row in student_rows if row['activeCount'] > 0),
            key=lambda row: -row['activeCount'],
        )[:6]
        return {
            'classStudents': student_rows,
            'weakPointStats': weak_stats,
            'commonErrorTypes': common_errors,
            'attentionStudents': attention,
            'studentCount': len(student_rows),
        }

    @staticmethod
    def teacher_suggestion(user_id: int | None, payload: dict | None = None) -> dict:
        body = dict(payload or {})
        class_id = body.get('classId') or body.get('class_id')
        if class_id:
            try:
                agg = AgentOrchestrator._aggregate_class(int(class_id))
                if not body.get('weakPointStats') and agg['weakPointStats']:
                    body['weakPointStats'] = agg['weakPointStats']
                if not body.get('commonErrorTypes') and agg['commonErrorTypes']:
                    body['commonErrorTypes'] = agg['commonErrorTypes']
                if not body.get('classStudents'):
                    body['classStudents'] = agg['classStudents']
            except Exception:
                pass
        if user_id and not body.get('weakPointStats'):
            weak = MistakeService.list_weak_knowledge(user_id, limit=5)
            body['weakPointStats'] = [
                {'knowledgePoint': w['knowledge_label'], 'count': w.get('fail_count', 1)}
                for w in weak
            ]
        return run_teacher_suggestion(body)

    @staticmethod
    def class_diagnosis(class_id: int) -> dict:
        """班级一键学情诊断：聚合班级错题 + 知识图谱薄弱点，调用教师助理智能体产出干预方案。"""
        from app.models import Class, db

        cls = db.session.get(Class, class_id)
        agg = AgentOrchestrator._aggregate_class(class_id)

        weak_nodes: list[dict] = []
        try:
            from app.services.knowledge_graph import KnowledgeGraphService

            graph = KnowledgeGraphService.get_class_graph(class_id)
            for node in graph.get('nodes', []):
                if node.get('status') == 'weak':
                    weak_nodes.append({
                        'id': node.get('id'),
                        'label': node.get('label') or node.get('title') or node.get('id'),
                        'weakCount': node.get('weak_count', 0),
                        'studentCount': node.get('student_count', agg['studentCount']),
                    })
        except Exception:
            weak_nodes = []

        suggestion = run_teacher_suggestion({
            'classId': str(class_id),
            'weakPointStats': agg['weakPointStats'],
            'commonErrorTypes': agg['commonErrorTypes'],
            'classStudents': agg['classStudents'],
        })

        from app.utils.time import utc_now

        return {
            'classId': class_id,
            'className': cls.name if cls else None,
            'studentCount': agg['studentCount'],
            'weakPointStats': agg['weakPointStats'],
            'commonErrorTypes': agg['commonErrorTypes'],
            'attentionStudents': agg['attentionStudents'],
            'weakNodes': weak_nodes,
            'suggestion': suggestion,
            'backend': backend_name(),
            'generatedAt': utc_now().isoformat() + 'Z',
        }

    @staticmethod
    def agents_status() -> dict:
        from agents.crew import get_agents_health

        return {
            'agents': get_agents_status(),
            'backend': backend_name(),
            'health': get_agents_health(),
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
