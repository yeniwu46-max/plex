"""驿站对话：LLM（可选）+ 规则兜底"""
import os

import requests

from app.services.evaluation import EvaluationService
from app.services.rag_service import RagService
from app.services.recommendation import RecommendationService


class MessengerChatService:
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
    def _llm_reply(user_id: int, message: str) -> dict | None:
        api_key = os.getenv('OPENROUTER_API_KEY', '').strip()
        if not api_key:
            return None
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
        model = os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini')
        try:
            resp = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
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
        llm = MessengerChatService._llm_reply(user_id, text)
        if llm:
            return llm
        return MessengerChatService._rag_rule_reply(user_id, text)
