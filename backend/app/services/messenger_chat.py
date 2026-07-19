"""驿站对话：DeepSeek LLM（优先）+ 规则兜底"""
import os
import re

import requests

from agents.llm_client import messenger_provider, strip_asterisks
from app.services.course_safety import CourseSafetyService
from app.services.evaluation import EvaluationService
from app.services.iflytek_spark import IflytekSparkService
from app.services.rag_service import RagService
from app.services.recommendation import RecommendationService
from app.services.xfyun_agent import XfyunAgentService


class MessengerChatService:
    PROVIDER_LABEL_RE = re.compile(
        r'\s*[（(]\s*(?:(?:讯飞星火|讯飞星辰\s*Agent|星火|LLM|OpenAI|模型|AI接口)(?:\s*\+\s*(?:课程)?知识库)?|(?:课程)?知识库\s*\+\s*学情|规则分析)\s*[）)]\s*$',
        re.IGNORECASE,
    )
    SELF_PREFIX_RE = re.compile(r'^\s*(?:小E|小e|助手|AI)\s*[:：]\s*', re.IGNORECASE)
    MAX_HISTORY_ITEMS = 18
    MAX_HISTORY_CHARS = 500
    ASSISTANT_SYSTEM_PROMPT = (
        '你叫小E，是 A3 学习系统的驿站助手；记住学生最近 18 条对话并优先承接上下文。'
        '只以小E身份和学生对话，不要提到讯飞、星火、OpenAI、LLM、模型、接口、知识库来源或供应商。'
        '不要在句子末尾添加“（讯飞星火）”“（LLM）”这类来源尾注。'
        '不要用“小E：”“助手：”这类自我署名开头，直接回答学生的问题。'
        '如果学生追问“这个/上面/刚才”，要根据最近对话判断指代，不要装作第一次听到。'
        '采用苏格拉底式提问：不要急着给完整答案，先用 2-4 个循序渐进的小问题引导学生自己发现关键点。'
        '每次最多只揭示一个必要提示；如果学生明显卡住，再给一个很短的示例或判断方向。'
        '问题要具体，围绕学生当前代码、概念或上一轮对话，不要泛泛地问“你觉得呢”。'
        '语气像学习伙伴一样温和、聪明、具体，不要官腔，不要模板化，不要重复学生原话。'
        '不要使用星号（*）或 Markdown 加粗。'
        '一般控制在 120-200 字；结尾用一个最值得学生立刻思考的问题收束。'
    )

    @classmethod
    def _clean_reply(cls, reply: str) -> str:
        """Remove provider labels if an upstream model adds them anyway."""
        text = (reply or '').strip()
        previous = None
        while text and previous != text:
            previous = text
            text = cls.PROVIDER_LABEL_RE.sub('', text).strip()
            text = cls.SELF_PREFIX_RE.sub('', text).strip()
        return strip_asterisks(text)

    @staticmethod
    def _normalize_history(history) -> list[dict]:
        if not isinstance(history, list):
            return []
        rows = []
        for item in history[-MessengerChatService.MAX_HISTORY_ITEMS:]:
            if not isinstance(item, dict):
                continue
            role = item.get('role')
            if role not in ('user', 'assistant'):
                continue
            content = str(item.get('content') or item.get('text') or '').strip()
            if not content:
                continue
            rows.append({
                'role': role,
                'content': content[:MessengerChatService.MAX_HISTORY_CHARS],
            })
        return rows

    @staticmethod
    def _format_history(history: list[dict]) -> str:
        if not history:
            return '无'
        label = {'user': '学生', 'assistant': '你'}
        return '\n'.join(
            f'{idx + 1}. {label.get(item["role"], item["role"])}：{item["content"]}'
            for idx, item in enumerate(history)
        )

    @staticmethod
    def _student_context(user_id: int, message: str, history=None) -> tuple[dict, str, bool]:
        report = EvaluationService.get_student_learning_report(user_id, '7d')
        summary = report.get('summary') or {}
        weak = report.get('weak_knowledge') or []
        rag_context = RagService.build_context(message)
        history_rows = MessengerChatService._normalize_history(history)
        weak_labels = '、'.join(
            str(item.get('knowledge_label') or item.get('knowledge_key') or '')
            for item in weak[:3]
        ) or '暂无明显薄弱知识点'
        context = (
            f'{MessengerChatService.ASSISTANT_SYSTEM_PROMPT}\n\n'
            f'最近对话（最多 18 条，越靠后越新）：\n{MessengerChatService._format_history(history_rows)}\n\n'
            f'学生近 7 天学情：学习指数 {summary.get("index", 0)}；正确率 {summary.get("correct_rate", 0)}%；'
            f'当前薄弱知识：{weak_labels}。\n'
            f'内部课程参考（只用于理解问题，不要说明来源）：{rag_context[:600] if rag_context else "无"}'
        )
        return report, context, bool(rag_context)

    @staticmethod
    def _xfyun_agent_reply(user_id: int, message: str, history=None) -> dict | None:
        """Prefer the published iFlytek Xingchen Agent when API credentials are configured."""
        if not XfyunAgentService.configured():
            return None
        report, context, rag_used = MessengerChatService._student_context(user_id, message, history)
        try:
            reply = XfyunAgentService.chat_text(
                user_id=user_id,
                message=message[:500],
                context=context,
                timeout=90,
            )
            return {
                'reply': MessengerChatService._clean_reply(reply),
                'source': 'xfyun_agent',
                'recommendations': report.get('recommendations') or [],
                'rag_used': rag_used,
            }
        except Exception:
            return None

    @staticmethod
    def _spark_reply(user_id: int, message: str, history=None) -> dict | None:
        """Use the configured Spark provider for a real, per-request conversation reply."""
        if not IflytekSparkService.configured():
            return None
        report, context, rag_used = MessengerChatService._student_context(user_id, message, history)
        history_rows = MessengerChatService._normalize_history(history)
        try:
            reply = IflytekSparkService.chat_text(
                MessengerChatService.ASSISTANT_SYSTEM_PROMPT,
                f'{context}\n\n学生问题：{message[:500]}',
                timeout=12,
            )
            return {
                'reply': MessengerChatService._clean_reply(reply),
                'source': 'spark',
                'recommendations': report.get('recommendations') or [],
                'rag_used': rag_used,
            }
        except Exception:
            return None

    @staticmethod
    def _rule_reply(user_id: int, message: str, history=None) -> dict:
        rec = RecommendationService.get_student_recommendations(user_id, '7d')
        weak = rec.get('weak_knowledge') or []
        recommendations = rec.get('recommendations') or []
        weak_text = weak[0]['knowledge_label'] if weak else '暂无突出薄弱点'
        rec_text = recommendations[0]['detail'] if recommendations else '保持每日委托与试炼节奏。'
        history_rows = MessengerChatService._normalize_history(history)
        context_hint = '我们接着刚才的思路往下推。' if history_rows else '可以先把问题拆小一点。'
        reply = (
            f'{context_hint}\n'
            f'先问自己两个问题：这一步最依赖哪个知识点？如果把输入换成一个最小例子，结果会怎么变？\n'
            f'结合最近表现，优先关注「{weak_text}」。下一步可以这样验证：{rec_text}'
        )
        return {'reply': MessengerChatService._clean_reply(reply), 'source': 'rules', 'recommendations': recommendations[:3]}

    @staticmethod
    def _deepseek_reply(user_id: int, message: str, history=None) -> dict | None:
        provider = messenger_provider()
        if not provider:
            return None
        api_key, endpoint, model = provider
        report, context, rag_used = MessengerChatService._student_context(user_id, message, history)
        history_rows = MessengerChatService._normalize_history(history)
        messages: list[dict] = [{'role': 'system', 'content': MessengerChatService.ASSISTANT_SYSTEM_PROMPT}]
        for row in history_rows:
            messages.append({'role': row['role'], 'content': row['content']})
        messages.append({'role': 'user', 'content': message[:500]})
        try:
            resp = requests.post(
                endpoint,
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': model,
                    'messages': messages,
                    'max_tokens': 420,
                    'temperature': 0.55,
                },
                timeout=8,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data['choices'][0]['message']['content'].strip()
            return {
                'reply': MessengerChatService._clean_reply(text),
                'source': 'llm',
                'recommendations': report.get('recommendations') or [],
                'rag_used': rag_used,
            }
        except Exception:
            return None

    @staticmethod
    def _llm_provider() -> tuple[str, str, str] | None:
        return messenger_provider()

    @staticmethod
    def _llm_reply(user_id: int, message: str, history=None) -> dict | None:
        return MessengerChatService._deepseek_reply(user_id, message, history)

    @staticmethod
    def _rag_rule_reply(user_id: int, message: str, history=None) -> dict:
        rag = RagService.query(message)
        base = MessengerChatService._rule_reply(user_id, message, history)
        if rag.get('sources'):
            base['reply'] = f'{rag["answer"]}\n\n{base["reply"]}'
            base['source'] = 'rag'
            base['rag_sources'] = rag.get('sources')
        base['reply'] = MessengerChatService._clean_reply(base['reply'])
        return base

    @staticmethod
    def chat(user_id: int, message: str, history=None) -> dict:
        text = (message or '').strip()
        if not text:
            raise ValueError('消息不能为空')
        CourseSafetyService.ensure_safe(text, enforce_course_scope=True)
        spark = MessengerChatService._spark_reply(user_id, text, history)
        if spark:
            return spark
        deepseek = MessengerChatService._deepseek_reply(user_id, text, history)
        if deepseek:
            return deepseek
        agent = MessengerChatService._xfyun_agent_reply(user_id, text, history)
        if agent:
            return agent
        return MessengerChatService._rag_rule_reply(user_id, text, history)
