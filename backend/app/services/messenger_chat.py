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
        '当学生明确要求解释概念、定义、写法、区别或示例时：先用 80-160 字讲清要点，'
        '必要时给一个短 ```python 示例，再在结尾只留 1 个思考题；'
        '禁止反问「你遇到了什么问题」「能否告诉我具体困惑」或装作没听懂。'
        '仅当问题确实含糊（如只说「不会/报错了」且无上下文）时，才用 1 个具体澄清问题。'
        '调试/卡住场景可用轻量苏格拉底式：先给关键提示，再问 1 个具体小问题，不要一次抛多个问题。'
        '语气像学习伙伴一样温和、聪明、具体，不要官腔，不要模板化，不要重复学生原话。'
        '可以使用 Markdown 排版：加粗关键概念、用短列表拆步骤、代码一律放进 ``` 代码块并注明语言。'
        '一般控制在 120-220 字。'
    )
    CLEAR_QUESTION_RE = re.compile(
        r'(解释|什么是|是什么|怎么写|如何|举例|示例|区别|原理|用法|推导式|语法|含义|作用)',
    )
    EVASIVE_REPLY_RE = re.compile(
        r'(能否告诉我|具体遇到了什么问题|似乎有些困惑|没有理解你的问题|'
        r'你具体想问|可以更详细|请问你想了解|看起来你在学习.*但似乎)',
    )
    TOPIC_TOKEN_RE = re.compile(
        r'(列表推导式|列表推导|推导式|装饰器|生成器|迭代器|递归|异常处理|'
        r'字典|元组|切片|闭包|lambda|字符串格式化|循环嵌套|分支语句)',
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

    @classmethod
    def _is_evasive_reply(cls, reply: str, user_message: str) -> bool:
        """Reject vague clarification when the student already asked a clear topic question."""
        text = (reply or '').strip()
        if not text:
            return True
        if not cls.CLEAR_QUESTION_RE.search(user_message or ''):
            return False
        if '```' in text or '列表推导' in text:
            return False
        if cls.EVASIVE_REPLY_RE.search(text):
            return True
        # Short reply that only asks back without teaching content
        if len(text) < 90 and ('？' in text or '?' in text) and '例如' not in text:
            return True
        return False

    @classmethod
    def _is_off_topic_reply(cls, reply: str, user_message: str) -> bool:
        """Reject replies that ignore an explicit course topic in the question."""
        topic = cls.TOPIC_TOKEN_RE.search(user_message or '')
        if not topic:
            return False
        token = topic.group(1)
        text = reply or ''
        if token in text:
            return False
        # 允许近义短写：列表推导式 ↔ 推导式
        if '推导' in token and '推导' in text:
            return False
        return True

    @classmethod
    def _is_low_quality_reply(cls, reply: str, user_message: str) -> bool:
        return cls._is_evasive_reply(reply, user_message) or cls._is_off_topic_reply(reply, user_message)

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
    def _student_context_light(user_id: int, message: str, history=None) -> tuple[dict, str, bool]:
        """流式首字前的轻量上下文：跳过完整学情报告与重 RAG，避免阻塞 TTFT。"""
        history_rows = MessengerChatService._normalize_history(history)
        weak: list = []
        try:
            from app.services.mistake import MistakeService

            weak = MistakeService.list_weak_knowledge(user_id, limit=3) or []
        except Exception:
            weak = []
        weak_labels = '、'.join(
            str(item.get('knowledge_label') or item.get('knowledge_key') or '')
            for item in weak[:3]
        ) or '暂无明显薄弱知识点'
        rag_context = ''
        try:
            # mock/轻量检索即可；完整 LlamaIndex 查询会拖慢首 token
            rag = RagService._mock_query(message) if hasattr(RagService, '_mock_query') else {}
            snippets = [s.get('snippet', '') for s in (rag.get('sources') or []) if s.get('snippet')]
            rag_context = '\n'.join(f'- {s}' for s in snippets)[:280]
        except Exception:
            rag_context = ''
        context = (
            f'{MessengerChatService.ASSISTANT_SYSTEM_PROMPT}\n\n'
            f'最近对话（最多 18 条，越靠后越新）：\n{MessengerChatService._format_history(history_rows)}\n\n'
            f'学生薄弱知识（轻量）：{weak_labels}。\n'
            f'内部课程参考（只用于理解问题，不要说明来源）：{rag_context or "无"}'
        )
        report = {
            'summary': {},
            'weak_knowledge': weak,
            'recommendations': [],
        }
        return report, context, bool(rag_context)

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
        # 仅检查凭证是否配置；单次失败不应永久禁用（凭证轮换后可立刻恢复）
        return bool(IflytekSparkService._resolve_api_password('messenger'))

    @staticmethod
    def _xfyun_recently_failed() -> bool:
        """短时熔断：星辰 Agent 刚超时/鉴权失败时跳过，避免拖垮整条对话。"""
        status = XfyunAgentService.status()
        return status.get('error_code') in {
            'timeout',
            'authentication_failed',
            'network_error',
            'rate_limited',
            'upstream_error',
        }

    @staticmethod
    def _xfyun_agent_reply(user_id: int, message: str, history=None) -> dict | None:
        """Prefer the published iFlytek Xingchen Agent when API credentials are configured."""
        if not XfyunAgentService.configured():
            return None
        if MessengerChatService._xfyun_recently_failed():
            return None
        report, context, rag_used = MessengerChatService._student_context(user_id, message, history)
        try:
            reply = XfyunAgentService.chat_text(
                user_id=user_id,
                message=message[:500],
                context=context,
                timeout=5,
            )
            cleaned = MessengerChatService._clean_reply(reply)
            if not cleaned or MessengerChatService._is_low_quality_reply(cleaned, message):
                return None
            return {
                'reply': cleaned,
                'source': 'xfyun_agent',
                'recommendations': report.get('recommendations') or [],
                'rag_used': rag_used,
            }
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning('xfyun_agent messenger failed: %s', exc)
            return None

    @staticmethod
    def _spark_reply(user_id: int, message: str, history=None) -> dict | None:
        """Use the configured Spark provider for a real, per-request conversation reply."""
        if not MessengerChatService._spark_messenger_enabled():
            return None
        report, context, rag_used = MessengerChatService._student_context_light(user_id, message, history)
        try:
            # 问题置顶，避免冗长学情/RAG 上下文把模型带偏主题
            spark_user = (
                f'学生问题（必须围绕此问题回答，不要答成别的概念）：{message[:500]}\n\n'
                f'补充上下文（仅供参考）：\n{context[:900]}'
            )
            reply = IflytekSparkService.chat_text(
                MessengerChatService.ASSISTANT_SYSTEM_PROMPT,
                spark_user,
                timeout=12,
                purpose='messenger',
                temperature=0.35,
                max_tokens=480,
            )
            cleaned = MessengerChatService._clean_reply(reply)
            if not cleaned or MessengerChatService._is_low_quality_reply(cleaned, message):
                return None
            return {
                'reply': cleaned,
                'source': 'spark',
                'recommendations': report.get('recommendations') or [],
                'rag_used': rag_used,
            }
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning('spark messenger failed: %s', exc)
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
        # 概念讲解用轻量上下文，减少学情查询拖垮超时
        report, context, rag_used = MessengerChatService._student_context_light(user_id, message, history)
        history_rows = MessengerChatService._normalize_history(history)
        messages: list[dict] = [{'role': 'system', 'content': context}]
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
                    'max_tokens': 320,
                    'temperature': 0.4,
                },
                timeout=(3, 12),
            )
            resp.raise_for_status()
            data = resp.json()
            text = data['choices'][0]['message']['content'].strip()
            cleaned = MessengerChatService._clean_reply(text)
            if not cleaned or MessengerChatService._is_low_quality_reply(cleaned, message):
                return None
            return {
                'reply': cleaned,
                'source': 'llm',
                'recommendations': report.get('recommendations') or [],
                'rag_used': rag_used,
            }
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning('deepseek messenger failed: %s', exc)
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

    # 供应商降级链的总等待预算（秒）：需覆盖「低质回复熔断后换下一家」。
    CHAT_TOTAL_BUDGET_SECONDS = 14.0
    ILLUSTRATION_HINTS = (
        '图', '示意', '画', '图解', '流程图', '结构', '对比', '可视化',
        '怎么看', '画一下', '示意图',
    )

    @classmethod
    def _wants_illustration(cls, message: str) -> bool:
        text = message or ''
        return any(token in text for token in cls.ILLUSTRATION_HINTS)

    @classmethod
    def _build_illustration(cls, message: str, *, timeout: tuple[float, float] = (2, 10)) -> dict | None:
        """按需生成答疑图解；短超时，失败返回 None，避免拖垮对话流。"""
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
            # 默认 2K 生图可达数十秒；流式路径强制用 1K + 短超时
            image_url = ArkMediaService.generate_image(prompt, size='1K', timeout=timeout)
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
        import logging
        import time

        text = (message or '').strip()
        if not text:
            raise ValueError('消息不能为空')
        CourseSafetyService.ensure_safe(text, enforce_course_scope=True)
        started = time.monotonic()
        logger = logging.getLogger(__name__)

        def within_budget() -> bool:
            return time.monotonic() - started < MessengerChatService.CHAT_TOTAL_BUDGET_SECONDS

        # 统一 DeepSeek 优先；讯飞星火/星辰仅作兜底（未配置时立刻跳过，不会卡住）
        order = ('_deepseek_reply', '_spark_reply', '_xfyun_agent_reply')
        for method_name in order:
            if not within_budget():
                break
            method = getattr(MessengerChatService, method_name)
            result = method(user_id, text, history)
            if result:
                if MessengerChatService._is_low_quality_reply(result.get('reply') or '', text):
                    logger.info('messenger.chat reject low-quality from %s', method_name)
                    continue
                return result
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

        def within_rewrite_budget() -> bool:
            return time.monotonic() - t0 < 20.0

        # 立刻推送阶段，让前端马上离开「正在思考」空白态
        yield {
            'type': 'stage',
            'stage': 'context',
            'label': '整理你的学习情况',
        }
        try:
            report, context, rag_used = MessengerChatService._student_context_light(
                user_id, text, history,
            )
        except Exception:
            report, context, rag_used = {}, MessengerChatService.ASSISTANT_SYSTEM_PROMPT, False
        thinking.append({
            'id': 'context',
            'label': '整理学情',
            'summary': '已快速汇总薄弱知识点与近期对话（轻量路径，优先首字速度）。',
            'latencyMs': int((time.monotonic() - t0) * 1000),
        })
        yield {
            'type': 'stage',
            'stage': 'reasoning',
            'label': '梳理解题思路',
        }
        thinking.append({
            'id': 'reasoning',
            'label': '梳理思路',
            'summary': '对照对话上下文与薄弱点，决定用提问引导还是给出关键提示。',
            'latencyMs': max(1, int((time.monotonic() - t0) * 1000) - thinking[0]['latencyMs']),
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
                # 连接 3s / 读流 45s：星火流式按 token 推送，避免过短读超时造成卡顿重连
                for delta in iter_openai_stream(provider, messages, max_tokens=480, timeout=(3, 45)):
                    emitted = True
                    collected.append(delta)
                    yield {'type': 'delta', 'text': delta}
            except Exception:
                if not emitted:
                    continue
            if emitted:
                reply = MessengerChatService._clean_reply(''.join(collected))
                # 流式已吐字无法撤回：低质时用 DeepSeek 同步重写最终 reply（前端以 done.reply 为准）
                if (not reply or MessengerChatService._is_low_quality_reply(reply, text)) and within_rewrite_budget():
                    rewritten = MessengerChatService._deepseek_reply(user_id, text, history)
                    if rewritten and rewritten.get('reply'):
                        reply = rewritten['reply']
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
                # 图解短超时尽力而为；失败不影响文字已完成
                if MessengerChatService._wants_illustration(text):
                    yield {
                        'type': 'stage',
                        'stage': 'illustration',
                        'label': '绘制图解说明',
                    }
                illustration = MessengerChatService._build_illustration(text, timeout=(2, 8))
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
        if MessengerChatService._wants_illustration(text):
            yield {
                'type': 'stage',
                'stage': 'illustration',
                'label': '绘制图解说明',
            }
        illustration = MessengerChatService._build_illustration(text, timeout=(2, 8))
        if illustration:
            yield {'type': 'illustration', 'illustration': illustration}

    @staticmethod
    def generate_knowledge_graph(user_id: int, topic: str) -> dict:
        """生成知识图：DeepSeek 产出 Mermaid 结构，可选 Ark 配图。"""
        text = (topic or '').strip()
        if len(text) < 2:
            raise ValueError('请描述要生成的知识主题')
        CourseSafetyService.ensure_safe(text, enforce_course_scope=True)

        from agents.http_client import direct_post
        from agents.llm_client import messenger_provider

        provider = messenger_provider()
        mermaid = (
            f'graph TD\n  A["{text[:24]}"] --> B["核心概念"]\n  B --> C["常见易错点"]\n  B --> D["练习建议"]'
        )
        backend = 'local_template'
        if provider:
            api_key, endpoint, model = provider
            try:
                response = direct_post(
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
                                    '你是 Python 教学助手。根据主题输出简洁 Mermaid 思维导图，'
                                    '使用 graph TD，节点标签用中文，6-10 个节点。只输出 mermaid 代码。'
                                ),
                            },
                            {'role': 'user', 'content': f'主题：{text[:200]}'},
                        ],
                        'temperature': 0.35,
                        'max_tokens': 480,
                    },
                    timeout=(3, 15),
                )
                response.raise_for_status()
                content = (response.json()['choices'][0]['message']['content'] or '').strip()
                if 'graph' in content:
                    mermaid = content.replace('```mermaid', '').replace('```', '').strip()
                    backend = 'deepseek'
            except Exception:
                pass

        # 配图改为短超时尽力而为：同步等满 2K 生图会 ~40s，拖慢「生成知识图」主路径
        illustration = None
        try:
            from app.services.ark_media import ArkMediaService

            if ArkMediaService.image_configured():
                prompt = (
                    'Clean educational mind map infographic, Chinese labels, white background, '
                    f'topic: {text[:120]}'
                )
                url = ArkMediaService.generate_image(prompt, size='1K', timeout=(3, 12))
                if url:
                    illustration = {'url': url, 'caption': '知识图预览'}
        except Exception:
            pass

        return {
            'topic': text,
            'mermaid': mermaid,
            'illustration': illustration,
            'backend': backend,
        }

    @staticmethod
    def generate_learning_document(user_id: int, topic: str) -> dict:
        """生成学习文档：DeepSeek 产出 Markdown 提纲与正文摘要。"""
        text = (topic or '').strip()
        if len(text) < 2:
            raise ValueError('请描述要生成的文档主题')
        CourseSafetyService.ensure_safe(text, enforce_course_scope=True)

        from agents.http_client import direct_post
        from agents.llm_client import messenger_provider

        title = f'{text[:40]} · 学习文档'
        markdown = (
            f'# {title}\n\n'
            f'## 学习目标\n- 理解「{text}」的核心概念\n\n'
            '## 建议步骤\n1. 阅读示例代码\n2. 完成 2 道配套练习\n3. 回顾易错点\n'
        )
        backend = 'local_template'
        provider = messenger_provider()
        if provider:
            api_key, endpoint, model = provider
            try:
                response = direct_post(
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
                                    '你是 Python 课程助教。根据主题写一份 Markdown 学习文档，'
                                    '含标题、学习目标、分步讲解、小练习与易错提醒，400-600 字。'
                                ),
                            },
                            {'role': 'user', 'content': f'主题：{text[:200]}'},
                        ],
                        'temperature': 0.5,
                        'max_tokens': 900,
                    },
                    timeout=(3, 18),
                )
                response.raise_for_status()
                content = (response.json()['choices'][0]['message']['content'] or '').strip()
                if content:
                    markdown = content.replace('```markdown', '').replace('```', '').strip()
                    backend = 'deepseek'
                    first_line = markdown.splitlines()[0].lstrip('# ').strip()
                    if first_line:
                        title = first_line
            except Exception:
                pass

        return {
            'title': title,
            'markdown': markdown,
            'backend': backend,
        }
