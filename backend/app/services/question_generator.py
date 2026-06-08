"""按知识点随机生成试炼题目"""
import random

from app.models import Trial, TrialQuestion, db

from app.data.knowledge_catalog import DOMAIN_LABELS, KNOWLEDGE_UNIVERSE, POINT_TO_BANK

KNOWLEDGE_LABELS = {
    'intro': 'Python 入门',
    'var': '变量与类型',
    'ops': '运算与表达式',
    'cond': '条件分支',
    'loop': '循环结构',
    'list': '列表与容器',
    'str': '字符串处理',
    'func': '函数基础',
    'file': '文件与异常',
    'algo': '算法入门',
    **DOMAIN_LABELS,
}

# 每知识点题库（stem, options, correct_index）
QUESTION_BANK: dict[str, list[dict]] = {
    'intro': [
        {
            'stem': 'Python 中用于输出内容的函数是？',
            'options': ['print()', 'echo()', 'output()', 'write()'],
            'correct_index': 0,
        },
        {
            'stem': '单行注释使用哪个符号开头？',
            'options': ['#', '//', '/*', '--'],
            'correct_index': 0,
        },
        {
            'stem': 'print("Hello") 的输出结果是？',
            'options': ['Hello', 'Hello()', '"Hello"', '报错'],
            'correct_index': 0,
        },
    ],
    'var': [
        {
            'stem': '下列哪个是合法的变量名？',
            'options': ['score1', '1score', 'for', 'my-score'],
            'correct_index': 0,
        },
        {
            'stem': 'input() 返回的数据类型通常是？',
            'options': ['str', 'int', 'float', 'bool'],
            'correct_index': 0,
        },
        {
            'stem': 'int("12") 的结果是？',
            'options': ['12', '"12"', '报错', '12.0'],
            'correct_index': 0,
        },
    ],
    'ops': [
        {
            'stem': '表达式 10 // 3 的结果是？',
            'options': ['3', '3.33', '4', '1'],
            'correct_index': 0,
        },
        {
            'stem': '比较运算 5 > 3 的结果是？',
            'options': ['True', 'False', '5', '3'],
            'correct_index': 0,
        },
        {
            'stem': '逻辑运算 True and False 的结果是？',
            'options': ['False', 'True', 'None', '0'],
            'correct_index': 0,
        },
    ],
    'cond': [
        {
            'stem': '判断年龄是否成年，最合适的结构是？',
            'options': ['if-else', 'while', 'for', 'try-except'],
            'correct_index': 0,
        },
        {
            'stem': 'elif 的作用是？',
            'options': ['再判断一个条件', '结束循环', '定义函数', '捕获异常'],
            'correct_index': 0,
        },
        {
            'stem': 'score=85 时，grade="B" 需要用到？',
            'options': ['if-elif-else', 'print', 'input', 'import'],
            'correct_index': 0,
        },
    ],
    'loop': [
        {
            'stem': 'for i in range(3) 会循环几次？',
            'options': ['3', '2', '4', '0'],
            'correct_index': 0,
        },
        {
            'stem': 'break 的作用是？',
            'options': ['提前结束循环', '跳过本次循环', '重新开始程序', '定义变量'],
            'correct_index': 0,
        },
        {
            'stem': '打印 1 到 5 的和，通常使用？',
            'options': ['循环 + 累加变量', '只用一个 print', 'input', '注释'],
            'correct_index': 0,
        },
    ],
    'list': [
        {
            'stem': '列表 nums = [1,2,3]，nums[0] 的值是？',
            'options': ['1', '2', '3', '0'],
            'correct_index': 0,
        },
        {
            'stem': 'len([10,20,30]) 的结果是？',
            'options': ['3', '30', '2', '10'],
            'correct_index': 0,
        },
        {
            'stem': '字典 student = {"name":"A"}，取姓名应写？',
            'options': ['student["name"]', 'student.name', 'name(student)', 'getname()'],
            'correct_index': 0,
        },
    ],
    'str': [
        {
            'stem': '"hello".upper() 的结果是？',
            'options': ['HELLO', 'hello', 'Hello', '报错'],
            'correct_index': 0,
        },
        {
            'stem': '字符串 "abc"[1] 的结果是？',
            'options': ['b', 'a', 'c', '1'],
            'correct_index': 0,
        },
        {
            'stem': '统计字符串长度应使用？',
            'options': ['len(s)', 'count(s)', 'size(s)', 'length()'],
            'correct_index': 0,
        },
    ],
    'func': [
        {
            'stem': '定义函数使用哪个关键字？',
            'options': ['def', 'function', 'fn', 'fun'],
            'correct_index': 0,
        },
        {
            'stem': '函数中 return 的作用是？',
            'options': ['返回结果并结束函数', '打印输出', '导入模块', '开始循环'],
            'correct_index': 0,
        },
        {
            'stem': '封装“求两数之和”最适合用？',
            'options': ['函数', '注释', 'print', 'break'],
            'correct_index': 0,
        },
    ],
    'file': [
        {
            'stem': '读取文本文件通常配合哪个语句？',
            'options': ['with open(...) as f', 'for break', 'if else', 'def return'],
            'correct_index': 0,
        },
        {
            'stem': 'try-except 主要用于？',
            'options': ['捕获运行错误', '循环遍历', '定义变量', '格式化输出'],
            'correct_index': 0,
        },
    ],
    'algo': [
        {
            'stem': '在列表中逐个查找目标值，属于？',
            'options': ['线性查找', '快速排序', '递归回溯', '动态规划'],
            'correct_index': 0,
        },
        {
            'stem': '统计列表元素出现次数，常用结构是？',
            'options': ['循环 + 计数器', '只写 print', 'input', '注释'],
            'correct_index': 0,
        },
        {
            'stem': '使用 set 的主要好处之一是？',
            'options': ['自动去重', '自动排序', '只能存数字', '不能遍历'],
            'correct_index': 0,
        },
    ],
}

DEFAULT_BANK = QUESTION_BANK['intro']


class QuestionGenerator:
    QUESTIONS_PER_TRIAL = 3

    @staticmethod
    def _normalize_key(knowledge_key: str | None) -> str:
        key = (knowledge_key or 'intro').lower().strip()
        if key in POINT_TO_BANK:
            return POINT_TO_BANK[key]
        if key in QUESTION_BANK:
            return key
        if key in ('python', 'lang', 'syntax', 'basic', 'comment', 'input', 'io'):
            return 'var' if key in ('input', 'io') else 'intro'
        if key in ('condition', 'range'):
            return 'cond' if key == 'condition' else 'loop'
        if key in ('tuple', 'set', 'dict'):
            return 'list'
        if key in ('string', 'function'):
            return 'str' if key == 'string' else 'func'
        if key in ('except', 'exception'):
            return 'file'
        if key.startswith('algo'):
            return 'algo'
        return 'intro'

    @staticmethod
    def bank_for_key(knowledge_key: str | None) -> list[dict]:
        return QUESTION_BANK.get(QuestionGenerator._normalize_key(knowledge_key), DEFAULT_BANK)

    @staticmethod
    def ensure_from_custom(trial: Trial, custom_questions: list[dict]) -> list[TrialQuestion]:
        """用教师自定义题干覆盖随机生成（兼容仅 MCQ 的旧调用）。"""
        normalized = []
        for entry in custom_questions:
            qtype = (entry.get('question_type') or 'mcq').lower()
            if qtype == 'coding':
                normalized.append({**entry, 'question_type': 'coding'})
            else:
                normalized.append({**entry, 'question_type': 'mcq'})
        return QuestionGenerator.ensure_from_payload(trial, normalized)

    @staticmethod
    def ensure_from_payload(trial: Trial, questions: list[dict]) -> list[TrialQuestion]:
        """按题型写入试炼题目（MCQ + 编程混排）。"""
        TrialQuestion.query.filter_by(trial_id=trial.id).delete()
        db.session.flush()
        created = []
        for index, entry in enumerate(questions):
            qtype = (entry.get('question_type') or 'mcq').lower()
            if qtype == 'coding':
                test_cases = entry.get('test_cases') or []
                if not test_cases:
                    continue
                meta = {
                    'starter_code': entry.get('starter_code') or '# 在此编写代码\n',
                    'run_mode': entry.get('run_mode') or 'stdout',
                    'hint': entry.get('hint') or '',
                    'test_cases': test_cases,
                    'constraints': entry.get('constraints') or [],
                    'examples': entry.get('examples') or [],
                }
                question = TrialQuestion(
                    trial_id=trial.id,
                    sort_order=index + 1,
                    question_type='coding',
                    stem=str(entry.get('stem') or f'编程题 {index + 1}'),
                    options=[],
                    correct_index=0,
                    knowledge_key=entry.get('knowledge_key') or trial.knowledge_key,
                )
                question.set_coding_meta(meta)
            else:
                options = entry.get('options') or []
                if len(options) < 2:
                    continue
                question = TrialQuestion(
                    trial_id=trial.id,
                    sort_order=index + 1,
                    question_type='mcq',
                    stem=str(entry.get('stem') or f'题目 {index + 1}'),
                    options=[str(o) for o in options[:6]],
                    correct_index=min(max(int(entry.get('correct_index', 0)), 0), len(options) - 1),
                    knowledge_key=entry.get('knowledge_key') or trial.knowledge_key,
                )
            db.session.add(question)
            created.append(question)
        if not created:
            return QuestionGenerator.ensure_for_trial(trial)
        db.session.commit()
        return created

    @staticmethod
    def materialize_trial_questions(trial: Trial) -> list[TrialQuestion]:
        """已发布试炼：确保题目已落库；草稿仅返回空列表。"""
        if trial.status == 'draft':
            return []
        existing = TrialQuestion.query.filter_by(trial_id=trial.id).order_by(TrialQuestion.sort_order).all()
        if existing:
            return existing
        draft = trial.draft_questions()
        if draft:
            return QuestionGenerator.ensure_from_payload(trial, draft)
        return QuestionGenerator.ensure_for_trial(trial)

    @staticmethod
    def ensure_for_trial(trial: Trial, count: int | None = None) -> list[TrialQuestion]:
        """为试炼生成题目（已存在则跳过）。"""
        existing = TrialQuestion.query.filter_by(trial_id=trial.id).order_by(TrialQuestion.sort_order).all()
        if existing:
            return existing

        keys = trial.knowledge_keys() if hasattr(trial, 'knowledge_keys') else []
        if not keys and trial.knowledge_key:
            keys = [trial.knowledge_key]

        pick_count = count or QuestionGenerator.QUESTIONS_PER_TRIAL
        created = []
        used_stems: set[str] = set()

        if len(keys) > 1:
            for index, raw_key in enumerate(keys[:pick_count]):
                bank_key = QuestionGenerator._normalize_key(raw_key)
                bank = QuestionGenerator.bank_for_key(raw_key)
                candidates = [item for item in bank if item['stem'] not in used_stems]
                if not candidates:
                    candidates = bank
                item = random.choice(candidates)
                used_stems.add(item['stem'])
                question = TrialQuestion(
                    trial_id=trial.id,
                    sort_order=index + 1,
                    stem=item['stem'],
                    options=item['options'],
                    correct_index=int(item['correct_index']),
                    knowledge_key=raw_key,
                )
                db.session.add(question)
                created.append(question)
        else:
            bank = QuestionGenerator.bank_for_key(keys[0] if keys else trial.knowledge_key)
            sample_count = min(pick_count, len(bank))
            picked = random.sample(bank, sample_count)
            key = QuestionGenerator._normalize_key(keys[0] if keys else trial.knowledge_key)
            for index, item in enumerate(picked):
                question = TrialQuestion(
                    trial_id=trial.id,
                    sort_order=index + 1,
                    stem=item['stem'],
                    options=item['options'],
                    correct_index=int(item['correct_index']),
                    knowledge_key=keys[0] if keys else key,
                )
                db.session.add(question)
                created.append(question)

        db.session.commit()
        return created

    @staticmethod
    def label_for_key(knowledge_key: str | None) -> str:
        if not knowledge_key:
            return '综合练习'
        if knowledge_key in POINT_TO_BANK:
            for domain in KNOWLEDGE_UNIVERSE:
                for point in domain['points']:
                    if point['key'] == knowledge_key:
                        return point['label']
        key = QuestionGenerator._normalize_key(knowledge_key)
        return KNOWLEDGE_LABELS.get(key, KNOWLEDGE_LABELS.get(knowledge_key, '综合练习'))
