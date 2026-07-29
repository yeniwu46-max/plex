"""教师试炼 AI 出题（DeepSeek 优先，OpenRouter 备选，失败回退题库随机）"""
import json
import os
import random
import re

import requests

from app.services.question_generator import QuestionGenerator

_ALLOWED_TYPES = {'mcq', 'multiple', 'coding'}


class AiQuestionGenerator:
    @staticmethod
    def generate(
        knowledge_keys: list[str],
        count: int = 3,
        question_types: list[str] | None = None,
        difficulty: int = 60,
    ) -> list[dict]:
        keys = [k for k in knowledge_keys if k]
        if not keys:
            keys = ['intro']
        types = [t for t in (question_types or ['mcq']) if t in _ALLOWED_TYPES]
        if not types:
            types = ['mcq']
        count = max(1, min(20, int(count or 3)))
        difficulty = max(0, min(100, int(difficulty or 60)))

        llm = AiQuestionGenerator._llm_generate(keys, count, types, difficulty)
        if llm:
            return llm
        return AiQuestionGenerator._fallback(keys, count, types)

    @staticmethod
    def _fallback(keys: list[str], count: int, types: list[str]) -> list[dict]:
        items = []
        for index in range(count):
            key = keys[index % len(keys)]
            qtype = types[index % len(types)]
            if qtype == 'coding':
                label = QuestionGenerator.label_for_key(key)
                items.append(
                    {
                        'question_type': 'coding',
                        'stem': f'请编写 Python 程序，完成与「{label}」相关的基础练习（例如输入输出或简单计算）。',
                        'starter_code': '# 在此编写代码\n',
                        'run_mode': 'stdout',
                        'hint': f'围绕 {label} 的核心语法完成题目要求。',
                        'test_cases': [{'id': 't1', 'label': '样例 1', 'expected': ''}],
                        'knowledge_key': key,
                    }
                )
                continue
            bank = QuestionGenerator.bank_for_key(key)
            item = random.choice(bank)
            payload = {
                'stem': item['stem'],
                'options': item['options'],
                'correct_index': int(item['correct_index']),
                'knowledge_key': key,
            }
            if qtype == 'multiple' and len(item['options']) >= 3:
                indexes = sorted({int(item['correct_index']), min(len(item['options']) - 1, int(item['correct_index']) + 1)})
                payload['question_type'] = 'multiple'
                payload['correct_indexes'] = indexes
            else:
                payload['question_type'] = 'mcq'
            items.append(payload)
        return items

    @staticmethod
    def _deepseek_config() -> tuple[str, str, str] | None:
        api_key = (
            os.getenv('DEEPSEEK_TRIAL_GEN_API_KEY', '').strip()
            or os.getenv('DEEPSEEK_API_KEY', '').strip()
        )
        if not api_key:
            return None
        base = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1').rstrip('/')
        model = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
        return api_key, base, model

    @staticmethod
    def _llm_generate(
        keys: list[str],
        count: int,
        types: list[str],
        difficulty: int,
    ) -> list[dict] | None:
        deepseek = AiQuestionGenerator._deepseek_config()
        if deepseek:
            result = AiQuestionGenerator._chat_generate(deepseek, keys, count, types, difficulty)
            if result:
                return result
        api_key = os.getenv('OPENROUTER_API_KEY', '').strip()
        if api_key:
            return AiQuestionGenerator._openrouter_generate(api_key, keys, count, types, difficulty)
        return None

    @staticmethod
    def _type_prompt(types: list[str]) -> str:
        labels = []
        if 'mcq' in types:
            labels.append('单选题(mcq)')
        if 'multiple' in types:
            labels.append('多选题(multiple，需 correct_indexes 数组)')
        if 'coding' in types:
            labels.append('编程题(coding，含 starter_code、run_mode、test_cases)')
        return '、'.join(labels) if labels else '单选题(mcq)'

    @staticmethod
    def _chat_generate(
        provider: tuple[str, str, str],
        keys: list[str],
        count: int,
        types: list[str],
        difficulty: int,
    ) -> list[dict] | None:
        api_key, base, model = provider
        labels = [QuestionGenerator.label_for_key(k) for k in keys]
        type_hint = AiQuestionGenerator._type_prompt(types)
        prompt = (
            f'为 Python 初学者知识点 {", ".join(labels)} 生成 {count} 道中文试题。'
            f'难度系数约 {difficulty}/100。题型可包含：{type_hint}。'
            '题目应围绕 Python 语法基础与少量算法思想，不要出竞赛级难题。'
            '返回 JSON 数组，每项字段：question_type(mcq|multiple|coding)、stem、'
            'options(选择题4项)、correct_index、correct_indexes(多选)、knowledge_key、'
            'starter_code、run_mode(stdout|expression)、hint、test_cases([{id,label,expected})。'
        )
        try:
            resp = requests.post(
                f'{base}/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': model,
                    'messages': [
                        {'role': 'system', 'content': '只输出合法 JSON 数组，不要 markdown。'},
                        {'role': 'user', 'content': prompt},
                    ],
                    'max_tokens': 2400,
                },
                # 例外：批量出题无法在 5s 内完成，失败时回退本地题库
                timeout=30,
            )
            resp.raise_for_status()
            text = resp.json()['choices'][0]['message']['content']
            return AiQuestionGenerator._parse_llm_items(text, keys, count, types)
        except Exception:
            return None

    @staticmethod
    def _openrouter_generate(
        api_key: str,
        keys: list[str],
        count: int,
        types: list[str],
        difficulty: int,
    ) -> list[dict] | None:
        model = os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini')
        return AiQuestionGenerator._chat_generate((api_key, 'https://openrouter.ai/api/v1', model), keys, count, types, difficulty)

    @staticmethod
    def _parse_llm_items(text: str, keys: list[str], count: int, types: list[str]) -> list[dict] | None:
        match = re.search(r'\[[\s\S]*\]', text)
        if not match:
            return None
        parsed = json.loads(match.group())
        result = []
        for index, item in enumerate(parsed[:count]):
            qtype = str(item.get('question_type') or types[index % len(types)] or 'mcq')
            key = item.get('knowledge_key') or keys[index % len(keys)]
            if qtype == 'coding':
                cases = item.get('test_cases') or [{'id': 't1', 'label': '样例 1', 'expected': ''}]
                result.append(
                    {
                        'question_type': 'coding',
                        'stem': str(item.get('stem') or f'编程题 {index + 1}'),
                        'starter_code': str(item.get('starter_code') or '# 在此编写代码\n'),
                        'run_mode': str(item.get('run_mode') or 'stdout'),
                        'hint': str(item.get('hint') or ''),
                        'test_cases': cases,
                        'knowledge_key': key,
                    }
                )
                continue
            options = item.get('options') or []
            if len(options) < 2:
                continue
            correct_index = min(max(int(item.get('correct_index', 0)), 0), len(options) - 1)
            payload = {
                'question_type': 'multiple' if qtype == 'multiple' else 'mcq',
                'stem': str(item.get('stem') or f'题目 {index + 1}'),
                'options': [str(o) for o in options[:6]],
                'correct_index': correct_index,
                'knowledge_key': key,
            }
            if qtype == 'multiple':
                raw_indexes = item.get('correct_indexes') or [correct_index]
                indexes = sorted(
                    {
                        min(max(int(i), 0), len(options) - 1)
                        for i in raw_indexes
                        if isinstance(i, (int, float, str)) and str(i).isdigit()
                    }
                )
                payload['correct_indexes'] = indexes or [correct_index]
            result.append(payload)
        return result if result else None
