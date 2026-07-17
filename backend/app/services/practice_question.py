"""学生端编程练习题库：合并导入的 learning_core 题目与内置题库。"""
from __future__ import annotations

import re

from app.data.coding_question_bank import CODING_QUESTION_BANK
from app.models import Trial, TrialQuestion
from app.services.question_generator import QuestionGenerator

# 题号前缀：字母 + 数字（如 P0042、L0123）
KNOWLEDGE_CODE_PREFIX: dict[str, str] = {
    'intro': 'P',
    'print': 'P',
    'comment': 'P',
    'var': 'V',
    'io': 'I',
    'input': 'I',
    'ops': 'O',
    'cond': 'C',
    'loop': 'L',
    'range': 'R',
    'list': 'S',
    'dict': 'D',
    'str': 'T',
    'func': 'F',
    'file': 'A',
    'except': 'E',
    'algo-sum': 'G',
    'algo-search': 'H',
}

BUILTIN_QUESTION_CODES: dict[str, str] = {
    'hello-print': 'P0001',
    'var-sum': 'V0001',
    'max-of-two': 'C0001',
    'sum-1-to-n': 'L0001',
    'print-calc': 'O0001',
    'print-name': 'P0002',
    'var-product': 'V0002',
    'loop-sum': 'L0002',
    'fizz-n': 'L0003',
    'list-max': 'S0001',
    'capstone-fizz': 'C0002',
}

SEMANTIC_TITLE_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r'哥德巴赫|Goldbach|质数之和|二个质数|两个质数|两.*质数.*之和', re.I), '哥德巴赫分解'),
    (re.compile(r'冒泡|bubble.?sort|相邻.*交换', re.I), '冒泡排序'),
    (re.compile(r'选择排序|selection.?sort|每轮.*最小', re.I), '选择排序'),
    (re.compile(r'二分|binary.?search|有序.*查找', re.I), '二分查找'),
    (re.compile(r'斐波那契|爬楼梯|台阶.*方案', re.I), '爬楼梯方案数'),
    (re.compile(r'最大子段|Kadane|连续子数组.*最大和', re.I), '最大子段和'),
    (re.compile(r'水仙花'), '水仙花数判定'),
    (re.compile(r'质数|素数|prime', re.I), '质数判定'),
    (re.compile(r'阶乘|factorial', re.I), '阶乘计算'),
    (re.compile(r'Hello|PLEX|问候', re.I), '问候语输出'),
    (re.compile(r'print|输出', re.I), '标准输出'),
    (re.compile(r'input|输入', re.I), '输入读取'),
    (re.compile(r'if|分支|判断|奇偶', re.I), '条件分支'),
    (re.compile(r'for|while|循环|累加|计数', re.I), '循环统计'),
    (re.compile(r'列表|list|数组', re.I), '列表处理'),
    (re.compile(r'字典|dict|键值', re.I), '字典操作'),
    (re.compile(r'字符串|strip|split|切片', re.I), '字符串处理'),
    (re.compile(r'函数|def|return', re.I), '函数封装'),
    (re.compile(r'三个数.*排序|从小到大', re.I), '三数排序'),
    (re.compile(r'较大|最大|max', re.I), '取较大值'),
    (re.compile(r'千位'), '千位数字提取'),
    (re.compile(r'Fizz|Buzz', re.I), 'Fizz 信号'),
]


class PracticeQuestionService:
    @staticmethod
    def _prefix_for_key(key: str) -> str:
        return KNOWLEDGE_CODE_PREFIX.get((key or '').strip().lower(), 'Q')

    @staticmethod
    def _strip_verbose(stem: str) -> str:
        line = re.sub(r'\s+', ' ', (stem or '').strip().split('\n')[0])
        verbose_prefixes = (
            '编写程序，', '编写程序', '设计一个程序来', '设计一个程序', '设计程序',
            '请编写', '请实现', '实现一个', '实现函数', '那个兔子又对你说：', '那个兔子',
            '用户输入', '输入三个整数', '输入{[三个整数]}，你的程序',
        )
        for prefix in verbose_prefixes:
            if line.startswith(prefix):
                line = line[len(prefix):].lstrip('：:，, ')
        line = re.split(r'[。；;！!？?]', line)[0].strip()
        line = re.sub(r'^(给定|已有|已知|请|你)', '', line).strip()
        return re.sub(r'[`"{\[]', '', line).strip()

    @staticmethod
    def _infer_semantic_title(stem: str, fallback: str) -> str:
        raw = (stem or '').strip()
        if not raw:
            return fallback
        for pattern, title in SEMANTIC_TITLE_RULES:
            if pattern.search(raw):
                return title[:20]
        return PracticeQuestionService._smart_title(stem, fallback)

    @staticmethod
    def _smart_title(stem: str, fallback: str = '编程练习', max_len: int = 20) -> str:
        line = PracticeQuestionService._strip_verbose(stem)
        if not line:
            return fallback
        if len(line) > max_len:
            line = line[: max_len - 1].rstrip('，, ') + '…'
        return line or fallback

    @staticmethod
    def _display_title(code: str, stem: str, fallback: str) -> str:
        short = PracticeQuestionService._infer_semantic_title(stem, fallback)
        return f'{code} · {short}'

    @staticmethod
    def _code_for_imported(question: TrialQuestion) -> str:
        key = question.knowledge_key or 'intro'
        prefix = PracticeQuestionService._prefix_for_key(key)
        return f'{prefix}{question.id:04d}'

    @staticmethod
    def _code_for_builtin(item: dict) -> str:
        qid = str(item.get('id') or '')
        if qid in BUILTIN_QUESTION_CODES:
            return BUILTIN_QUESTION_CODES[qid]
        key = item.get('knowledge_key') or 'intro'
        prefix = PracticeQuestionService._prefix_for_key(key)
        slug = re.sub(r'[^a-z0-9]', '', qid.lower())[:4] or '0000'
        return f'{prefix}{slug.upper()[:1]}{abs(hash(qid)) % 1000:03d}'

    @staticmethod
    def _clean_legacy_markup(text: str) -> str:
        cleaned = re.sub(r'\{\[([^\]]*)\]\}', r'\1', text or '')
        cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)
        cleaned = re.sub(r'\*([^*\n]+)\*', r'\1', cleaned)
        return cleaned.strip()

    @staticmethod
    def _extract_embedded_tests(stem: str) -> tuple[str, list[dict], list[dict]]:
        """从题干剥离嵌入的测试样例，返回 (净题干, examples, test_cases)。"""
        raw = PracticeQuestionService._clean_legacy_markup(stem or '')
        examples: list[dict] = []
        test_cases: list[dict] = []

        io_pattern = re.compile(
            r'(?:输入数据|输入)\s*[:：]?\s*([\s\S]+?)\s*(?:输出结果|输出)\s*[:：]?\s*([^\n#]+)',
            re.I,
        )
        for index, match in enumerate(io_pattern.finditer(raw)):
            input_text = match.group(1).strip()
            output_text = match.group(2).strip()
            examples.append({'input': input_text, 'output': output_text})
            test_cases.append({
                'id': f'embedded-{index + 1}',
                'label': f'样例 {index + 1}',
                'setup': input_text if input_text else None,
                'expected': output_text,
            })
        raw = io_pattern.sub('', raw)

        raw = re.sub(
            r'(?:^|\n)\s*#{1,3}\s*测试样例[\s\S]*?(?=\n\s*#{1,3}\s|\n\s*要求|\n\s*提示|$)',
            '\n',
            raw,
            flags=re.I,
        )
        raw = re.sub(r'(?:^|\n)\s*#{1,6}\s[^\n]*', '\n', raw)
        raw = re.sub(r'那个兔子又对你说：[^\n]*', '', raw)
        raw = re.sub(r'兔子期末考试[^\n]*', '', raw)

        clean_stem = re.sub(r'\n{3,}', '\n\n', raw).strip()
        return clean_stem, examples, test_cases

    @staticmethod
    def _normalize_question_payload(
        stem: str,
        examples: list[dict] | None,
        test_cases: list[dict] | None,
    ) -> tuple[str, list[dict], list[dict]]:
        clean_stem, embedded_examples, embedded_tests = PracticeQuestionService._extract_embedded_tests(stem)
        merged_examples = examples if examples else embedded_examples
        merged_tests = test_cases if test_cases else embedded_tests
        if not merged_examples and merged_tests:
            merged_examples = PracticeQuestionService._infer_examples_from_test_cases(merged_tests)
        merged_examples = [
            {
                'input': PracticeQuestionService._clean_legacy_markup(str(ex.get('input') or '')),
                'output': PracticeQuestionService._clean_legacy_markup(str(ex.get('output') or '')),
            }
            for ex in merged_examples
        ]
        return clean_stem, merged_examples, merged_tests

    @staticmethod
    def _infer_examples_from_test_cases(test_cases: list[dict]) -> list[dict]:
        examples: list[dict] = []
        for tc in (test_cases or [])[:3]:
            setup = str(tc.get('setup') or '').strip()
            invoke = str(tc.get('invoke') or '').strip()
            expected = str(tc.get('expected') or '')
            if setup:
                input_text = ', '.join(line.strip() for line in setup.splitlines() if line.strip())
            elif invoke:
                input_text = invoke
            else:
                input_text = '（无输入）'
            examples.append({'input': input_text, 'output': expected})
        return examples

    @staticmethod
    def _bank_item_to_payload(item: dict) -> dict:
        key = item.get('knowledge_key') or 'intro'
        qid = str(item.get('id') or key)
        stem = PracticeQuestionService._clean_legacy_markup(item.get('stem') or '')
        code = PracticeQuestionService._code_for_builtin(item)
        label = QuestionGenerator.label_for_key(key)
        test_cases = item.get('test_cases') or []
        examples = item.get('examples') or []
        stem, examples, test_cases = PracticeQuestionService._normalize_question_payload(
            stem, examples, test_cases
        )
        return {
            'id': qid,
            'code': code,
            'title': PracticeQuestionService._display_title(code, stem, label),
            'topic': QuestionGenerator.label_for_key(key),
            'difficulty': '基础',
            'reward_xp': 20,
            'duration_min': 10,
            'tags': [key],
            'description': stem,
            'constraints': [],
            'examples': examples,
            'test_cases': test_cases,
            'starter_code': item.get('starter_code') or '',
            'run_mode': item.get('run_mode') or 'stdout',
            'hint': item.get('hint') or '',
            'knowledge_key': key,
            'source': 'builtin',
        }

    @staticmethod
    def _db_row_to_payload(question: TrialQuestion) -> dict:
        meta = question.coding_meta()
        key = question.knowledge_key or 'intro'
        source_problem_id = meta.get('source_problem_id')
        qid = f'lc-{question.id}'
        stem = PracticeQuestionService._clean_legacy_markup(question.stem or '')
        code = PracticeQuestionService._code_for_imported(question)
        label = QuestionGenerator.label_for_key(key)
        title = PracticeQuestionService._display_title(code, stem, label)
        difficulty = meta.get('difficulty')
        if isinstance(difficulty, (int, float)):
            diff_label = '挑战' if difficulty >= 4 else '进阶' if difficulty >= 3 else '基础'
        else:
            diff_label = '基础'
        test_cases = meta.get('test_cases') or []
        examples = meta.get('examples') or []
        stem, examples, test_cases = PracticeQuestionService._normalize_question_payload(
            stem, examples, test_cases
        )
        return {
            'id': qid,
            'code': code,
            'title': title,
            'topic': QuestionGenerator.label_for_key(key),
            'difficulty': diff_label,
            'reward_xp': 25,
            'duration_min': 12,
            'tags': [key],
            'description': stem,
            'constraints': meta.get('constraints') or [],
            'examples': examples,
            'test_cases': test_cases,
            'starter_code': meta.get('starter_code') or '# 在此编写代码\n',
            'run_mode': meta.get('run_mode') or 'stdout',
            'hint': meta.get('hint') or '',
            'knowledge_key': key,
            'source': 'imported',
            'source_problem_id': source_problem_id,
            'db_question_id': question.id,
        }

    @staticmethod
    def list_for_student(knowledge_key: str | None = None, limit: int = 500) -> list[dict]:
        """返回去重后的练习题目，导入题优先于同 knowledge_key 的内置题。"""
        items: list[dict] = []
        seen_ids: set[str] = set()
        seen_codes: set[str] = set()
        seen_source_problems: set[int] = set()

        query = (
            TrialQuestion.query.filter(TrialQuestion.question_type == 'coding')
            .join(Trial, Trial.id == TrialQuestion.trial_id)
            .order_by(TrialQuestion.id.asc())
        )
        if knowledge_key:
            query = query.filter(TrialQuestion.knowledge_key == knowledge_key)

        for row in query.limit(limit).all():
            payload = PracticeQuestionService._db_row_to_payload(row)
            source_pid = payload.get('source_problem_id')
            if isinstance(source_pid, int):
                if source_pid in seen_source_problems:
                    continue
                seen_source_problems.add(source_pid)
            if payload['id'] in seen_ids or payload['code'] in seen_codes:
                continue
            seen_ids.add(payload['id'])
            seen_codes.add(payload['code'])
            items.append(payload)

        for bank_item in CODING_QUESTION_BANK:
            key = bank_item.get('knowledge_key')
            if knowledge_key and key != knowledge_key:
                continue
            payload = PracticeQuestionService._bank_item_to_payload(bank_item)
            if payload['id'] in seen_ids or payload['code'] in seen_codes:
                continue
            seen_ids.add(payload['id'])
            seen_codes.add(payload['code'])
            items.append(payload)

        return items

    @staticmethod
    def search_for_student(query: str, limit: int = 20) -> list[dict]:
        needle = (query or '').strip().lower()
        if not needle:
            return []
        results: list[dict] = []
        for item in PracticeQuestionService.list_for_student(limit=500):
            haystacks = [
                str(item.get('code') or '').lower(),
                str(item.get('id') or '').lower(),
                str(item.get('title') or '').lower(),
                str(item.get('topic') or '').lower(),
                str(item.get('description') or '').lower(),
                str(item.get('knowledge_key') or '').lower(),
            ]
            if any(needle in text for text in haystacks):
                results.append(item)
            if len(results) >= limit:
                break
        return results

    @staticmethod
    def get_by_ref(question_ref: str) -> dict | None:
        ref = (question_ref or '').strip()
        if not ref:
            return None
        ref_lower = ref.lower()
        if ref.startswith('lc-'):
            try:
                db_id = int(ref[3:])
            except ValueError:
                return None
            row = TrialQuestion.query.get(db_id)
            if row and (row.question_type or 'mcq') == 'coding':
                return PracticeQuestionService._db_row_to_payload(row)
            return None
        for item in PracticeQuestionService.list_for_student():
            if item['id'] == ref:
                return item
            if str(item.get('code') or '').lower() == ref_lower:
                return item
        return None

    @staticmethod
    def recommend_for_student(user_id: int) -> dict | None:
        """基于薄弱知识点与题库匹配一道推荐题（供驿站快捷推荐）。"""
        from app.services.mistake import MistakeService

        weak = MistakeService.list_weak_knowledge(user_id, limit=5)
        knowledge_key = None
        if weak:
            knowledge_key = weak[0].get('knowledge_key')

        candidates = PracticeQuestionService.list_for_student(knowledge_key=knowledge_key, limit=30)
        if not candidates:
            candidates = PracticeQuestionService.list_for_student(limit=30)
        if not candidates:
            return None

        mistake_refs = {
            str(item.get('question_ref') or item.get('question_id') or '')
            for item in MistakeService.list_for_student(user_id, active_only=True)
        }
        for item in candidates:
            if item['id'] not in mistake_refs:
                return item
        return candidates[0]
