"""题库（清洗自旧版 Mulberry/HydroOJ dump）查询服务。

字段与清洗规则详见 backend/scripts/problem_bank_import/REPORT.md（含 2026-07-30
增强篇：题目背景故事、样例沙箱补齐、标签系统、星级难度、班级口径统计、中英切换）。
"""
from app.data.knowledge_node_registry import (
    KNOWLEDGE_DOMAINS,
    kg_id_from_key,
    nodes_for_domain,
)
from app.models import Problem, ProblemSubmission, ProblemTag, ProblemTagMap


# 旧题库的 A~G 分组。重排后不再是主分类（主分类见 domain_key / kg_node_id），
# 但 70 道旧题上仍带着它，保留作为审计线索与旧筛选入口。
CONCEPT_GROUP_LABELS = {
    'A': 'Basics 基础语法',
    'B': 'Operators 运算符',
    'C': 'Conditionals 条件分支',
    'D': 'Loops 循环',
    'E': 'Functions 函数',
    'F': 'DataTypes 数据类型',
    'G': 'HighTypes 高级类型',
}


class ProblemBankService:
    @staticmethod
    def list_concept_groups() -> list[dict]:
        return [{'group': k, 'label': v} for k, v in CONCEPT_GROUP_LABELS.items()]

    @staticmethod
    def list_domains() -> list[dict]:
        """8 个大类及其知识点节点，供题库页按新分类筛选。"""
        return [
            {
                'key': domain.key,
                'title': domain.title,
                'order': domain.order,
                'nodes': [
                    {'id': entry.kg_id, 'label': entry.label}
                    for entry in nodes_for_domain(domain.key)
                ],
            }
            for domain in KNOWLEDGE_DOMAINS
        ]

    @staticmethod
    def list_problems(
        concept_group: str | None = None,
        keyword: str | None = None,
        tag: str | None = None,
        domain_key: str | None = None,
        kg_node_id: str | None = None,
    ) -> dict:
        query = Problem.query.filter_by(is_active=True)
        if concept_group:
            query = query.filter_by(concept_group=concept_group.upper())
        if domain_key:
            query = query.filter(Problem.domain_key == domain_key)
        if kg_node_id:
            query = query.filter(Problem.kg_node_id == kg_id_from_key(kg_node_id, kg_node_id))
        if keyword:
            like = f'%{keyword.strip()}%'
            query = query.filter(
                (Problem.title_cn.ilike(like))
                | (Problem.title_en.ilike(like))
                | (Problem.problem_no.ilike(like))
            )
        if tag:
            query = query.join(ProblemTagMap, ProblemTagMap.problem_id == Problem.id).join(
                ProblemTag, ProblemTag.id == ProblemTagMap.tag_id
            ).filter(ProblemTag.code == tag)
        items = query.order_by(Problem.problem_no).all()
        return {
            'items': [row.to_summary_dict() for row in items],
            'total': len(items),
            'concept_groups': ProblemBankService.list_concept_groups(),
            'domains': ProblemBankService.list_domains(),
            'active_tag': tag or None,
            'active_domain_key': domain_key or None,
            'active_kg_node_id': kg_node_id or None,
        }

    @staticmethod
    def get_problem_detail(problem_id: int, include_answer: bool = False) -> dict:
        problem = Problem.query.get(problem_id)
        if not problem:
            raise ValueError(f'题目 {problem_id} 不存在')
        return problem.to_dict(include_answer=include_answer)

    @staticmethod
    def list_submissions(problem_id: int, legacy_user_id: int | None = None, limit: int = 100) -> dict:
        problem = Problem.query.get(problem_id)
        if not problem:
            raise ValueError(f'题目 {problem_id} 不存在')
        query = ProblemSubmission.query.filter_by(problem_id=problem_id)
        if legacy_user_id:
            query = query.filter_by(legacy_user_id=legacy_user_id)
        query = query.order_by(ProblemSubmission.submitted_at.desc()).limit(min(limit, 500))
        items = query.all()
        return {
            'problem_id': problem_id,
            'items': [row.to_dict(include_code=False) for row in items],
            'total': len(items),
        }

    @staticmethod
    def get_submission_detail(submission_id: int) -> dict:
        submission = ProblemSubmission.query.get(submission_id)
        if not submission:
            raise ValueError(f'提交记录 {submission_id} 不存在')
        return submission.to_dict(include_code=True)

    @staticmethod
    def list_tags() -> dict:
        tags = ProblemTag.query.order_by(ProblemTag.tag_type, ProblemTag.sort_order, ProblemTag.code).all()
        grouped: dict[str, list[dict]] = {}
        for t in tags:
            grouped.setdefault(t.tag_type, []).append(t.to_dict())
        return {'items': [t.to_dict() for t in tags], 'by_type': grouped}

    @staticmethod
    def get_problem_stats(problem_id: int, legacy_group_id: int | None = None) -> dict:
        """增强 #5：标题右侧统计条（提交数/通过数/时间限制）。

        `problem_submissions.legacy_group_id/legacy_group_name` 来自旧系统真实
        的班级/群组（`group` 表，8 个班级），这批导入的提交记录的
        `legacy_user_id` 并不对应当前 PLEX 账号体系（详见 problem_bank.py
        路由文档），因此无法通过现有 `Class`/`User.class_id` 关系反查出"这些
        旧提交属于当前 PLEX 的哪个班级"——那样做需要凭空捏造一份不存在的
        身份映射。为了不伪造数据，这里如实使用数据里真实存在的"旧系统班级"
        维度作为统计口径，并提供班级下拉供教师切换查看，而不是编造出一个假
        的"当前用户班级"过滤。完整取舍说明见 REPORT.md 增强篇 5。
        """
        problem = Problem.query.get(problem_id)
        if not problem:
            raise ValueError(f'题目 {problem_id} 不存在')

        group_rows = (
            ProblemSubmission.query
            .filter_by(problem_id=problem_id)
            .with_entities(ProblemSubmission.legacy_group_id, ProblemSubmission.legacy_group_name)
            .distinct()
            .all()
        )
        groups = sorted(
            [{'legacy_group_id': gid, 'legacy_group_name': name} for gid, name in group_rows if gid is not None],
            key=lambda g: g['legacy_group_id'],
        )

        target_group_id = legacy_group_id
        if target_group_id is None and groups:
            target_group_id = groups[0]['legacy_group_id']

        query = ProblemSubmission.query.filter_by(problem_id=problem_id)
        if target_group_id is not None:
            query = query.filter_by(legacy_group_id=target_group_id)

        submission_count = query.count()
        accepted_count = query.filter_by(is_accepted=True).count()

        return {
            'problem_id': problem_id,
            'legacy_group_id': target_group_id,
            'groups': groups,
            'submission_count': submission_count,
            'accepted_count': accepted_count,
            'time_limit_ms': problem.time_limit_ms or Problem.DEFAULT_TIME_LIMIT_MS,
            'time_limit_is_default': problem.time_limit_ms is None,
        }
