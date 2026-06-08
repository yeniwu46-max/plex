# -*- coding: utf-8 -*-
"""多智能体编排服务（对接 agents.crew）。"""

from agents.crew import backend_name, get_agents_status, run_student_diagnose, run_teacher_suggestion
from app.services.mistake import MistakeService


class AgentOrchestrator:
    @staticmethod
    def backend_name() -> str:
        return backend_name()

    @staticmethod
    def student_diagnose(user_id: int | None, payload: dict) -> dict:
        if user_id and not payload.get('recentMistakes'):
            weak = MistakeService.list_weak_knowledge(user_id, limit=5)
            payload = {
                **payload,
                'recentMistakes': [w['knowledge_label'] for w in weak],
            }
        return run_student_diagnose(payload)

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
        from agents import path_recommendation_agent

        rec = path_recommendation_agent.execute(payload)
        steps = [
            {'step': i + 1, 'node': n, 'action': 'review' if i == 0 else 'practice'}
            for i, n in enumerate(rec.get('reviewPlan', [])[:4])
        ]
        return {
            'agent': 'PathRecommendationAgent',
            'status': 'completed',
            'path': {
                'title': '下一步：' + rec['nextKnowledgePoint'],
                'steps': steps,
                'total_nodes': len(steps),
            },
            'confidence': 0.86,
            'recommended_at': rec,
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
