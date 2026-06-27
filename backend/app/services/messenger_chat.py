"""驿站对话：LLM（可选）+ 规则兜底"""
import os

import requests

from app.services.course_safety import CourseSafetyService
from app.services.evaluation import EvaluationService
from app.services.iflytek_spark import IflytekSparkService
from app.services.rag_service import RagService
from app.services.recommendation import RecommendationService
from app.services.xfyun_agent import XfyunAgentService


class MessengerChatService:
    @staticmethod
    def _student_context(user_id: int, message: str) -> tuple[dict, str, bool]:
        report = EvaluationService.get_student_learning_report(user_id, '7d')
        summary = report.get('summary') or {}
        weak = report.get('weak_knowledge') or []
        rag_context = RagService.build_context(message)
        weak_labels = '、'.join(
            str(item.get('knowledge_label') or item.get('knowledge_key') or '')
            for item in weak[:3]
        ) or '暂无明显薄弱知识点'
        context = (
            f'你是 A3 学习系统的驿站助手小E，请用自然、友好的中文回答，不要模板化。\n'
            f'学习指数：{summary.get("index", 0)}；正确率：{summary.get("correct_rate", 0)}%；'
            f'当前薄弱知识：{weak_labels}。\n'
            f'可参考的课程知识：{rag_context[:1200] if rag_context else "无"}\n'
            '回答要求：先直接解决学生问题，再给一条具体且可执行的下一步；总字数控制在 200 字以内。'
        )
        return report, context, bool(rag_context)

    @staticmethod
    def _xfyun_agent_reply(user_id: int, message: str) -> dict | None:
        """Prefer the published iFlytek Xingchen Agent when API credentials are configured."""
        if not XfyunAgentService.configured():
            return None
        report, context, rag_used = MessengerChatService._student_context(user_id, message)
        try:
            reply = XfyunAgentService.chat_text(
                user_id=user_id,
                message=message[:500],
                context=context,
                timeout=90,
            )
            return {
                'reply': reply,
                'source': 'xfyun_agent',
                'recommendations': report.get('recommendations') or [],
                'rag_used': rag_used,
            }
        except Exception:
            return None

    @staticmethod
    def _spark_reply(user_id: int, message: str) -> dict | None:
        """Use the configured Spark provider for a real, per-request conversation reply."""
        if not IflytekSparkService.configured():
            return None
        report, context, rag_used = MessengerChatService._student_context(user_id, message)
        try:
            reply = IflytekSparkService.chat_text(
                '你是 A3 学习系统的驿站助手小E。用自然、友好的中文直接回答学生，避免固定模板。',
                f'{context}\n\n学生问题：{message[:500]}',
                timeout=20,
            )
            return {
                'reply': reply,
                'source': 'spark',
                'recommendations': report.get('recommendations') or [],
                'rag_used': rag_used,
            }
        except Exception:
            return None
        return None

    @staticmethod
    def _rule_reply(user_id: int, message: str) -> dict:
        rec = RecommendationService.get_student_recommendations(user_id, '7d')
        weak = rec.get('weak_knowledge') or []
        recommendations = rec.get('recommendations') or []
        weak_text = weak[0]['knowledge_label'] if weak else '暂无突出薄弱点'
        rec_text = recommendations[0]['detail'] if recommendations else '保持每日委托与试炼节奏。'
        reply = (
            f'收到你的问题：「{message[:120]}」。\n'
            f'根据近期学情，当前薄弱方向：{weak_text}。\n'
            f'建议：{rec_text}'
        )
        return {'reply': reply, 'source': 'rules', 'recommendations': recommendations[:3]}

    @staticmethod
    def _llm_provider() -> tuple[str, str, str] | None:
        """Resolve an available OpenAI-compatible chat provider.

        Returns ``(api_key, endpoint, model)`` for the first configured backend,
        preferring OpenRouter when present and otherwise falling back to the
        official OpenAI endpoint so a plain ``OPENAI_API_KEY`` also yields real
        replies instead of the rule-based template.
        """
        openrouter = os.getenv('OPENROUTER_API_KEY', '').strip()
        if openrouter:
            return (
                openrouter,
                'https://openrouter.ai/api/v1/chat/completions',
                os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini'),
            )
        openai_key = os.getenv('OPENAI_API_KEY', '').strip()
        if openai_key:
            base = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
            return (
                openai_key,
                f'{base}/chat/completions',
                os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            )
        return None

    @staticmethod
    def _llm_reply(user_id: int, message: str) -> dict | None:
        provider = MessengerChatService._llm_provider()
        if not provider:
            return None
        api_key, endpoint, model = provider
        report = EvaluationService.get_student_learning_report(user_id, '7d')
        summary = report.get('summary') or {}
        weak = report.get('weak_knowledge') or []
        rag_context = RagService.build_context(message)
        context = (
            f'学习指数 {summary.get("index", 0)}，等级 {summary.get("level_label", "")}，'
            f'正确率 {summary.get("correct_rate", 0)}%，薄弱知识点：'
            f'{", ".join(w["knowledge_label"] for w in weak[:3]) or "无"}'
        )
        if rag_context:
            context += f'\n\n课程知识库检索：\n{rag_context}'
        try:
            resp = requests.post(
                endpoint,
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': model,
                    'messages': [
                        {
                            'role': 'system',
                            'content': (
                                '你是 A3 学习系统的驿站助手小E，用简洁中文回答，'
                                '结合学情给出可执行建议，不超过 200 字。'
                            ),
                        },
                        {'role': 'user', 'content': f'学情摘要：{context}\n\n学生问题：{message}'},
                    ],
                    'max_tokens': 320,
                },
                timeout=25,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data['choices'][0]['message']['content'].strip()
            return {
                'reply': text,
                'source': 'llm',
                'recommendations': report.get('recommendations') or [],
                'rag_used': bool(rag_context),
            }
        except Exception:
            return None

    @staticmethod
    def _rag_rule_reply(user_id: int, message: str) -> dict:
        rag = RagService.query(message)
        base = MessengerChatService._rule_reply(user_id, message)
        if rag.get('sources'):
            base['reply'] = f'{rag["answer"]}\n\n{base["reply"]}'
            base['source'] = 'rag'
            base['rag_sources'] = rag.get('sources')
        return base

    @staticmethod
    def chat(user_id: int, message: str) -> dict:
        text = (message or '').strip()
        if not text:
            raise ValueError('消息不能为空')
        CourseSafetyService.ensure_safe(text, enforce_course_scope=True)
        agent = MessengerChatService._xfyun_agent_reply(user_id, text)
        if agent:
            return agent
        spark = MessengerChatService._spark_reply(user_id, text)
        if spark:
            return spark
        llm = MessengerChatService._llm_reply(user_id, text)
        if llm:
            return llm
        return MessengerChatService._rag_rule_reply(user_id, text)
