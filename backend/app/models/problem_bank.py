"""标准化题库：清洗自旧版 Mulberry/HydroOJ 风格题库 dump 的题目与提交记录。

字段设计与清洗规则见 backend/scripts/problem_bank_import/REPORT.md 与
backend/scripts/problem_bank_import/schema.sql（两者字段名保持一致）。

`Problem.id` / `ProblemSubmission.id` 沿用旧系统的 `problem.id` / `solution.id`，
不使用自增，便于审计追溯、以及 `legacy_prev_solution_id` 重试链回溯。
"""
from . import db


class KnowledgeNode(db.Model):
    """知识点节点（8 大类 / ~25 节点）在库内的镜像。

    权威定义在 app/data/knowledge_node_registry.py，本表由
    scripts/knowledge_rebuild/load_mysql.py 同步写入，目的是让知识点在 SQL 里
    可直接 JOIN、可人工核对，而不必读 Python 源码。
    """
    __tablename__ = 'knowledge_nodes'

    id = db.Column(db.String(48), primary_key=True)
    domain_key = db.Column(db.String(32), nullable=False, index=True)
    domain_title = db.Column(db.String(64), nullable=False)
    domain_order = db.Column(db.Integer, nullable=False, default=0)
    title = db.Column(db.String(64), nullable=False)
    summary = db.Column(db.String(255))
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    level = db.Column(db.String(16), nullable=False, default='basic')
    default_difficulty = db.Column(db.Integer, nullable=False, default=1)
    knowledge_keys_json = db.Column(db.JSON)
    # 旧 kg_id（intro/var/cond/...）列表，用于把历史作答记录映射到新节点
    legacy_kg_ids_json = db.Column(db.JSON)
    document_id = db.Column(db.String(64))
    pos_x = db.Column(db.Integer)
    pos_y = db.Column(db.Integer)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'domain_key': self.domain_key,
            'domain_title': self.domain_title,
            'domain_order': self.domain_order,
            'title': self.title,
            'summary': self.summary,
            'sort_order': self.sort_order,
            'level': self.level,
            'default_difficulty': self.default_difficulty,
            'knowledge_keys': self.knowledge_keys_json or [],
            'document_id': self.document_id,
        }


class Problem(db.Model):
    """统一题库表：编程题（coding）与选择题（mcq）共用。

    2026-07-30 知识点重排后，`problems` 从"旧 dump 导入的编程题库"升级为全站唯一
    的题库表，五个历史来源（旧题库 dump / trial_questions / 内置编程题库 /
    前端静态题 / 后端选择题库）清洗去重后全部落在这里，`source_kind` 记录出处。
    """
    __tablename__ = 'problems'

    # 2026-07-30 增强 #5：题目本身没有逐题时间限制数据，全平台统一默认值见
    # app/services/problem_bank.py::DEFAULT_TIME_LIMIT_MS；此处为空表示
    # "使用平台默认值"，非空表示未来人工为该题设置的自定义值。
    DEFAULT_TIME_LIMIT_MS = 1000

    id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    problem_no = db.Column(db.String(8), nullable=False, unique=True, index=True)
    concept = db.Column(db.String(50))
    # 旧系统 A-G 分组字母；合并进来的选择题/前端静态题没有该概念，故可空
    concept_group = db.Column(db.String(1), index=True)
    title_en = db.Column(db.String(200))
    title_cn = db.Column(db.String(200), nullable=False)
    background = db.Column(db.Text)
    # 'ai:spark' | 'ai:xfyun_agent' | 'ai:deepseek' | 'template'，见
    # generate_backgrounds.py；用于前端/报告透明标注来源，不面向学生展示。
    background_source = db.Column(db.String(32))
    description_en = db.Column(db.Text)
    description_cn = db.Column(db.Text)
    # 增强 #6：是否有实质英文版本，决定前端"中/EN"切换按钮是否展示。
    has_english = db.Column(db.Boolean, nullable=False, default=False)
    input_format_en = db.Column(db.Text)
    output_format_en = db.Column(db.Text)
    input_format_cn = db.Column(db.Text)
    output_format_cn = db.Column(db.Text)
    samples_json = db.Column(db.JSON)
    # 'parsed_from_description' | 'executed_reference_answer:<reason>'，见
    # clean_and_transform.py::backfill via sandbox_exec.py。
    samples_source = db.Column(db.String(64))
    notes_json = db.Column(db.JSON)
    difficulty = db.Column(db.Integer)
    level = db.Column(db.Integer)
    # 增强 #4：洛谷风格 1-5 星难度（5 最难），由 difficulty 映射而来。
    star_difficulty = db.Column(db.SmallInteger)
    # 增强 #5：逐题自定义时间限制（毫秒）；为空则前端展示平台统一默认值。
    time_limit_ms = db.Column(db.Integer)
    topic = db.Column(db.Integer)
    reference_answer = db.Column(db.Text)
    template = db.Column(db.Text)
    legacy_problem_name = db.Column(db.String(100))
    legacy_author_user_id = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)

    # ---- 知识点重排（20260730_0011）新增 ----
    # 'coding' | 'mcq'
    question_type = db.Column(db.String(16), nullable=False, default='coding', index=True)
    kg_node_id = db.Column(db.String(48), db.ForeignKey('knowledge_nodes.id'), index=True)
    domain_key = db.Column(db.String(32), index=True)
    # 选择题专用：选项数组与正确选项下标
    options_json = db.Column(db.JSON)
    correct_index = db.Column(db.Integer)
    # 编程题专用：判题测试点、起始代码、运行模式、提示
    test_cases_json = db.Column(db.JSON)
    starter_code = db.Column(db.Text)
    run_mode = db.Column(db.String(16))
    hint = db.Column(db.Text)
    # 'legacy_bank' | 'trial_question' | 'builtin_coding' | 'frontend_static'
    # | 'builtin_mcq' | 'ai_generated'
    source_kind = db.Column(db.String(24), nullable=False, default='legacy_bank')
    source_ref = db.Column(db.String(128))
    # 去重时被合并掉的同义题目标识，供人工复核确认没有误删
    merged_from_json = db.Column(db.JSON)
    needs_review = db.Column(db.Boolean, nullable=False, default=False, index=True)
    review_note = db.Column(db.Text)

    created_at = db.Column(db.DateTime, nullable=False, default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.now(), onupdate=db.func.now())

    quest_map = db.relationship(
        'ProblemLegacyQuestMap', backref='problem', cascade='all, delete-orphan', lazy=True,
    )
    submissions = db.relationship(
        'ProblemSubmission', backref='problem', cascade='all, delete-orphan', lazy=True,
    )
    tag_map = db.relationship(
        'ProblemTagMap', backref='problem', cascade='all, delete-orphan', lazy=True,
    )

    def to_dict(self, include_answer: bool = False) -> dict:
        payload = {
            'id': self.id,
            'problem_no': self.problem_no,
            'concept': self.concept,
            'concept_group': self.concept_group,
            'title_en': self.title_en,
            'title_cn': self.title_cn,
            'background': self.background,
            'description_en': self.description_en,
            'description_cn': self.description_cn,
            'has_english': self.has_english,
            'input_format_en': self.input_format_en,
            'output_format_en': self.output_format_en,
            'input_format_cn': self.input_format_cn,
            'output_format_cn': self.output_format_cn,
            'samples': self.samples_json or [],
            'notes': self.notes_json or [],
            'difficulty': self.difficulty,
            'level': self.level,
            'star_difficulty': self.star_difficulty,
            'time_limit_ms': self.time_limit_ms or self.DEFAULT_TIME_LIMIT_MS,
            'time_limit_is_default': self.time_limit_ms is None,
            'is_active': self.is_active,
            'question_type': self.question_type,
            'kg_node_id': self.kg_node_id,
            'domain_key': self.domain_key,
            'source_kind': self.source_kind,
            'needs_review': self.needs_review,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'tags': [m.tag.to_dict() for m in sorted(self.tag_map, key=lambda m: (m.tag.tag_type, m.tag.sort_order))] if self.tag_map else [],
        }
        if self.question_type == 'mcq':
            payload['options'] = self.options_json or []
            payload['correct_index'] = self.correct_index
        else:
            payload['starter_code'] = self.starter_code
            payload['run_mode'] = self.run_mode
            payload['hint'] = self.hint
            payload['test_cases'] = self.test_cases_json or []
        if include_answer:
            payload['reference_answer'] = self.reference_answer
            payload['template'] = self.template
        return payload

    def to_summary_dict(self) -> dict:
        return {
            'id': self.id,
            'problem_no': self.problem_no,
            'concept_group': self.concept_group,
            'concept': self.concept,
            'title_en': self.title_en,
            'title_cn': self.title_cn,
            'difficulty': self.difficulty,
            'star_difficulty': self.star_difficulty,
            'question_type': self.question_type,
            'kg_node_id': self.kg_node_id,
            'domain_key': self.domain_key,
        }

    def to_practice_dict(self) -> dict:
        """试炼中心/星轨练习使用的题目结构（与 TrialQuestion 的练习格式对齐）。"""
        samples = self.samples_json or []
        return {
            'id': f'bank-{self.id}',
            'problem_id': self.id,
            'problem_no': self.problem_no,
            'question_type': self.question_type,
            'title': self.title_cn,
            'stem': self.description_cn or self.title_cn,
            'background': self.background,
            'knowledge_key': self.kg_node_id,
            'kg_node_id': self.kg_node_id,
            'domain_key': self.domain_key,
            'difficulty': self.star_difficulty or self.difficulty,
            'star_difficulty': self.star_difficulty,
            'input_format': self.input_format_cn,
            'output_format': self.output_format_cn,
            'examples': [
                {'input': item.get('input', ''), 'output': item.get('output', '')}
                for item in samples
                if isinstance(item, dict)
            ],
            'notes': self.notes_json or [],
            'options': self.options_json or [],
            'correct_index': self.correct_index,
            'starter_code': self.starter_code or self.template,
            'run_mode': self.run_mode or 'stdout',
            'hint': self.hint,
            'test_cases': self.test_cases_json or [],
            'source_kind': self.source_kind,
        }


class ProblemLegacyQuestMap(db.Model):
    __tablename__ = 'problem_legacy_quest_map'

    id = db.Column(db.Integer, primary_key=True)
    problem_id = db.Column(db.Integer, db.ForeignKey('problems.id', ondelete='CASCADE'), nullable=False, index=True)
    legacy_quest_id = db.Column(db.Integer, nullable=False)
    legacy_quest_title_cn = db.Column(db.String(100))
    required = db.Column(db.Boolean)
    sort_order = db.Column(db.Integer, default=0)


class ProblemTag(db.Model):
    """洛谷风格标签字典表（增强 #3）。

    `tag_type` 取值：
      - concept：知识点分组标签（复用 concept_group，如"循环"），每题固定 1 个。
      - topic：更细粒度的关键词/算法标签（如"字符串处理""递归"），规则匹配得出，0-N 个。
      - difficulty：难度分档标签，与 star_difficulty 一一对应，每题固定 1 个。
      - source：来源标签，取自旧系统 quest 章节标题（如"来源：受伤的兔子"），
        刻意不编造比赛/年份信息，见 REPORT.md 增强篇的替代设计说明。
    """
    __tablename__ = 'problem_tags'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), nullable=False, unique=True, index=True)
    label = db.Column(db.String(50), nullable=False)
    tag_type = db.Column(db.String(16), nullable=False, index=True)
    color = db.Column(db.String(16))
    sort_order = db.Column(db.Integer, default=0)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'code': self.code,
            'label': self.label,
            'tag_type': self.tag_type,
            'color': self.color,
        }


class ProblemTagMap(db.Model):
    __tablename__ = 'problem_tag_map'
    __table_args__ = (db.UniqueConstraint('problem_id', 'tag_id', name='uq_problem_tag'),)

    id = db.Column(db.Integer, primary_key=True)
    problem_id = db.Column(db.Integer, db.ForeignKey('problems.id', ondelete='CASCADE'), nullable=False, index=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('problem_tags.id', ondelete='CASCADE'), nullable=False, index=True)

    tag = db.relationship('ProblemTag', lazy=True)


class ProblemSubmission(db.Model):
    __tablename__ = 'problem_submissions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    problem_id = db.Column(db.Integer, db.ForeignKey('problems.id', ondelete='CASCADE'), nullable=False, index=True)
    legacy_user_id = db.Column(db.Integer, nullable=False, index=True)
    legacy_username = db.Column(db.String(100))
    legacy_student_name = db.Column(db.String(50))
    legacy_group_id = db.Column(db.Integer)
    legacy_group_name = db.Column(db.String(150))
    code_content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(8), nullable=False, index=True)
    is_accepted = db.Column(db.Boolean, nullable=False, default=False)
    compile_success = db.Column(db.Boolean, nullable=False, default=False)
    test_success = db.Column(db.Boolean, nullable=False, default=False)
    score_points = db.Column(db.Integer)
    score_total = db.Column(db.Integer)
    score_percent = db.Column(db.Numeric(5, 1))
    test_case_results_json = db.Column(db.JSON)
    raw_judge_output = db.Column(db.Text)
    exec_time_ms = db.Column(db.Integer)
    exec_memory_kb = db.Column(db.Integer)
    time_spent_seconds = db.Column(db.Integer)
    self_confidence = db.Column(db.Integer)
    legacy_error_name = db.Column(db.String(100))
    returncode = db.Column(db.Integer)
    legacy_prev_solution_id = db.Column(db.Integer)
    submitted_at = db.Column(db.DateTime, nullable=False, index=True)

    def to_dict(self, include_code: bool = True) -> dict:
        payload = {
            'id': self.id,
            'problem_id': self.problem_id,
            'legacy_user_id': self.legacy_user_id,
            'legacy_username': self.legacy_username,
            'legacy_student_name': self.legacy_student_name,
            'legacy_group_name': self.legacy_group_name,
            'status': self.status,
            'is_accepted': self.is_accepted,
            'compile_success': self.compile_success,
            'test_success': self.test_success,
            'score_points': self.score_points,
            'score_total': self.score_total,
            'score_percent': float(self.score_percent) if self.score_percent is not None else None,
            'exec_time_ms': self.exec_time_ms,
            'exec_memory_kb': self.exec_memory_kb,
            'time_spent_seconds': self.time_spent_seconds,
            'self_confidence': self.self_confidence,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
        }
        if include_code:
            payload['code_content'] = self.code_content
            payload['test_case_results'] = self.test_case_results_json or []
            payload['raw_judge_output'] = self.raw_judge_output
            payload['legacy_error_name'] = self.legacy_error_name
        return payload
