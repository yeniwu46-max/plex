"""驿站对话：DeepSeek LLM（优先）+ 规则兜底"""
import re
from collections.abc import Iterator

from agents.http_client import direct_post
from agents.llm_client import messenger_provider
from app.services.course_safety import CourseSafetyService
from app.services.evaluation import EvaluationService
from app.services.iflytek_spark import IflytekSparkService
from app.services.llm_stream import chunk_text, iter_openai_stream, stream_provider_chain
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
        '可以使用 Markdown 排版：加粗关键概念、用短列表拆步骤、代码一律放进 ``` 代码块并注明语言。'
        '一般控制在 120-200 字；结尾用一个最值得学生立刻思考的问题收束。'
    )

    @classmethod
    def _clean_reply(cls, reply: str) -> str:
        """Remove provider labels if an upstream model adds them anyway.

        Markdown 语法（加粗、列表、代码块）予以保留，由前端统一渲染。
        """
        text = (reply or '').strip()
        previous = None
        while text and previous != text:
            previous = text
            text = cls.PROVIDER_LABEL_RE.sub('', text).strip()
            text = cls.SELF_PREFIX_RE.sub('', text).strip()
        return text

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
    def _spark_messenger_enabled() -> bool:
        if not IflytekSparkService.configured():
            return False
        error_code = (IflytekSparkService.status() or {}).get('error_code')
        return error_code not in {'network_error', 'timeout', 'authentication_failed', 'not_configured'}

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
                timeout=5,
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
        if not MessengerChatService._spark_messenger_enabled():
            return None
        report, context, rag_used = MessengerChatService._student_context(user_id, message, history)
        try:
            reply = IflytekSparkService.chat_text(
                MessengerChatService.ASSISTANT_SYSTEM_PROMPT,
                f'{context}\n\n学生问题：{message[:500]}',
                timeout=8,
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
            resp = direct_post(
                endpoint,
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': model,
                    'messages': messages,
                    'max_tokens': 256,
                    'temperature': 0.55,
                },
                timeout=(2, 5),
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

    # 供应商降级链的总等待预算（秒）：超过预算直接走规则兜底，避免串行累加。
    CHAT_TOTAL_BUDGET_SECONDS = 5.0
    ILLUSTRATION_HINTS = (
        '图', '示意', '画', '图解', '流程图', '结构', '对比', '可视化',
        '怎么看', '画一下', '示意图',
    )

    @classmethod
    def _wants_illustration(cls, message: str) -> bool:
        text = message or ''
        return any(token in text for token in cls.ILLUSTRATION_HINTS)

    @classmethod
    def _build_illustration(cls, message: str) -> dict | None:
        """按需生成答疑图解；未配置或失败返回 None，不阻塞文字回复。"""
        if not cls._wants_illustration(message):
            return None
        try:
            from app.services.ark_media import ArkMediaService

            if not ArkMediaService.image_configured():
                return None
            prompt = (
                'Educational illustration for university Python course, clean textbook style, '
                f'Chinese labels, topic: {message[:180]}. White background, high contrast.'
            )
            image_url = ArkMediaService.generate_image(prompt)
            if image_url:
                return {
                    'url': image_url,
                    'caption': '小E 为你生成的图解说明',
                }
        except Exception:
            pass
        return None

    @staticmethod
    def chat(user_id: int, message: str, history=None) -> dict:
        import time

        text = (message or '').strip()
        if not text:
            raise ValueError('消息不能为空')
        CourseSafetyService.ensure_safe(text, enforce_course_scope=True)
        started = time.monotonic()

        def within_budget() -> bool:
            return time.monotonic() - started < MessengerChatService.CHAT_TOTAL_BUDGET_SECONDS

        # 优先星火 / 星辰 Agent，避免 DeepSeek 超时拖垮体感
        if within_budget():
            spark = MessengerChatService._spark_reply(user_id, text, history)
            if spark:
                return spark
        if within_budget():
            agent = MessengerChatService._xfyun_agent_reply(user_id, text, history)
            if agent:
                return agent
        if within_budget():
            deepseek = MessengerChatService._deepseek_reply(user_id, text, history)
            if deepseek:
                return deepseek
        return MessengerChatService._rag_rule_reply(user_id, text, history)

    @staticmethod
    def chat_stream(user_id: int, message: str, history=None) -> Iterator[dict]:
        """流式驿站对话：阶段进度 + delta + done，图解在 done 之后异步推送。

        事件契约：
        - ``{'type': 'stage', 'stage': str, 'label': str}``
        - ``{'type': 'delta', 'text': str}``
        - ``{'type': 'done', ..., 'thinking': list}``
        - ``{'type': 'illustration', 'illustration': {...}}``（可选，done 之后）
        """
        import time

        text = (message or '').strip()
        if not text:
            raise ValueError('消息不能为空')

        thinking: list[dict] = []
        t0 = time.monotonic()
        yield {
            'type': 'stage',
            'stage': 'context',
            'label': '整理你的学习情况',
        }
        # 轻量上下文：失败不阻塞首字输出
        try:
            report, context, rag_used = MessengerChatService._student_context(user_id, text, history)
        except Exception:
            report, context, rag_used = {}, MessengerChatService.ASSISTANT_SYSTEM_PROMPT, False
        thinking.append({
            'id': 'context',
            'label': '整理学情',
            'summary': '已汇总近 7 天学习指数、正确率与薄弱知识点。',
            'latencyMs': int((time.monotonic() - t0) * 1000),
        })

        history_rows = MessengerChatService._normalize_history(history)
        messages: list[dict] = [{'role': 'system', 'content': context}]
        for row in history_rows:
            messages.append({'role': row['role'], 'content': row['content']})
        messages.append({'role': 'user', 'content': text[:500]})

        yield {
            'type': 'stage',
            'stage': 'llm',
            'label': '组织回答',
        }
        t1 = time.monotonic()

        for provider in stream_provider_chain('messenger'):
            emitted = False
            collected: list[str] = []
            try:
                for delta in iter_openai_stream(provider, messages, max_tokens=480, timeout=(2, 12)):
                    emitted = True
                    collected.append(delta)
                    yield {'type': 'delta', 'text': delta}
            except Exception:
                if not emitted:
                    continue
            if emitted:
                reply = MessengerChatService._clean_reply(''.join(collected))
                if not reply:
                    reply = MessengerChatService._clean_reply(
                        MessengerChatService._rag_rule_reply(user_id, text, history).get('reply') or ''
                    )
                thinking.append({
                    'id': 'llm',
                    'label': '生成回复',
                    'summary': '已根据学情与对话上下文组织回答。',
                    'latencyMs': int((time.monotonic() - t1) * 1000),
                })
                yield {
                    'type': 'done',
                    'source': 'llm_stream',
                    'recommendations': report.get('recommendations') or [],
                    'rag_used': rag_used,
                    'reply': reply or '结合你的近况，建议先巩固薄弱知识点，再做一道对应试炼。',
                    'thinking': thinking,
                }
                illustration = MessengerChatService._build_illustration(text)
                if illustration:
                    yield {'type': 'illustration', 'illustration': illustration}
                return

        # 兜底：规则/RAG 伪流式，保证必有可见文字
        result = MessengerChatService._rag_rule_reply(user_id, text, history)
        full = MessengerChatService._clean_reply(result.get('reply') or '') or (
            '结合你的近况，建议先巩固薄弱知识点，再做一道对应试炼。'
        )
        for piece in chunk_text(full):
            yield {'type': 'delta', 'text': piece}
        thinking.append({
            'id': 'llm',
            'label': '生成回复',
            'summary': f'已用备用路径完成回答（{result.get("source") or "rules"}）。',
            'latencyMs': int((time.monotonic() - t1) * 1000),
        })
        yield {
            'type': 'done',
            'source': result.get('source') or 'rules',
            'recommendations': result.get('recommendations') or report.get('recommendations') or [],
            'rag_used': bool(result.get('rag_used')) or rag_used,
            'reply': full,
            'thinking': thinking,
        }
        illustration = MessengerChatService._build_illustration(text)
        if illustration:
            yield {'type': 'illustration', 'illustration': illustration}
