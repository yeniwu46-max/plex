"""教师试炼 AI 出题（可选 OpenRouter，失败回退题库随机）"""
import os
import random

import requests

from app.services.question_generator import QuestionGenerator


class AiQuestionGenerator:
    @staticmethod
    def generate(knowledge_keys: list[str], count: int = 3) -> list[dict]:
        keys = [k for k in knowledge_keys if k]
        if not keys:
            keys = ['intro']
        llm = AiQuestionGenerator._llm_generate(keys, count)
        if llm:
            return llm
        return AiQuestionGenerator._fallback(keys, count)

    @staticmethod
    def _fallback(keys: list[str], count: int) -> list[dict]:
        items = []
        for index in range(count):
            key = keys[index % len(keys)]
            bank = QuestionGenerator.bank_for_key(key)
            item = random.choice(bank)
            items.append(
                {
                    'stem': item['stem'],
                    'options': item['options'],
                    'correct_index': int(item['correct_index']),
                    'knowledge_key': key,
                }
            )
        return items

    @staticmethod
    def _llm_generate(keys: list[str], count: int) -> list[dict] | None:
        api_key = os.getenv('OPENROUTER_API_KEY', '').strip()
        if not api_key:
            return None
        labels = [QuestionGenerator.label_for_key(k) for k in keys]
        model = os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini')
        prompt = (
            f'为 Python 初学者知识点 {", ".join(labels)} 生成 {count} 道中文选择题。'
            '题目应围绕 Python 语法基础与少量算法思想，不要出竞赛级难题。'
            '返回 JSON 数组，每项含 stem, options(4项), correct_index(0-3), knowledge_key。'
        )
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
                        {'role': 'system', 'content': '只输出合法 JSON 数组，不要 markdown。'},
                        {'role': 'user', 'content': prompt},
                    ],
                    'max_tokens': 1200,
                },
                timeout=30,
            )
            resp.raise_for_status()
            import json
            import re

            text = resp.json()['choices'][0]['message']['content']
            match = re.search(r'\[[\s\S]*\]', text)
            if not match:
                return None
            parsed = json.loads(match.group())
            result = []
            for index, item in enumerate(parsed[:count]):
                options = item.get('options') or []
                if len(options) < 2:
                    continue
                result.append(
                    {
                        'stem': str(item.get('stem') or f'题目 {index + 1}'),
                        'options': [str(o) for o in options[:6]],
                        'correct_index': min(max(int(item.get('correct_index', 0)), 0), len(options) - 1),
                        'knowledge_key': item.get('knowledge_key') or keys[index % len(keys)],
                    }
                )
            return result if result else None
        except Exception:
            return None
