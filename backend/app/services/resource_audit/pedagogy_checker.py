"""Step 2: teaching quality checks."""
from __future__ import annotations

from app.data.course_knowledge import catalog_points
from app.services.pedagogical_resource import STAGE_BLOOM, VALID_STAGES, build_knowledge_node

from .schema import CheckItem, StepResult


def _score_from_checks(checks: list[CheckItem]) -> int:
    score = 100
    for check in checks:
        if check.level == 'FAIL':
            score -= 25
        elif check.level == 'WARNING':
            score -= 8
    return max(0, min(100, score))


def check_pedagogy(bundle: dict, knowledge_key: str, profile: dict | None = None) -> StepResult:
    checks: list[CheckItem] = []
    profile = profile or {}
    analysis = bundle.get('analysis') or {}
    node = build_knowledge_node(knowledge_key)
    label = catalog_points().get(knowledge_key, knowledge_key)

    positioning = str(analysis.get('positioning') or '')
    if 'Python程序设计基础' in positioning or node.get('chapter'):
        checks.append(CheckItem('curriculum', '课程标准', 'PASS', '定位符合课程章节'))
    else:
        checks.append(CheckItem('curriculum', '课程标准', 'WARNING', '教学定位未明确课程来源'))

    bloom = str(analysis.get('bloom_level') or '')
    stage = str(analysis.get('learning_stage') or '学习')
    expected = STAGE_BLOOM.get(stage, STAGE_BLOOM['学习'])
    if bloom and bloom == expected:
        checks.append(CheckItem('bloom', 'Bloom 层级', 'PASS', f'{stage} → {bloom}'))
    elif bloom:
        checks.append(CheckItem('bloom', 'Bloom 层级', 'WARNING', f'期望 {expected}，实际 {bloom}'))
    else:
        checks.append(CheckItem('bloom', 'Bloom 层级', 'WARNING', '缺少 Bloom 层级标注'))

    if stage in VALID_STAGES:
        checks.append(CheckItem('learning_stage', '学习阶段', 'PASS', f'阶段：{stage}'))
    else:
        checks.append(CheckItem('learning_stage', '学习阶段', 'WARNING', f'非常规阶段：{stage}'))

    objectives = bundle.get('objective') or analysis.get('learning_objectives') or []
    if objectives:
        checks.append(CheckItem('objectives', '学习目标', 'PASS', f'{len(objectives)} 条目标'))
    else:
        checks.append(CheckItem('objectives', '学习目标', 'FAIL', '缺少学习目标'))

    difficulty = int(node.get('difficulty') or 1)
    foundation = str(profile.get('knowledge_foundation') or '')
    beginner = '零基础' in foundation
    if beginner and difficulty >= 3:
        checks.append(CheckItem('difficulty_jump', '难度跳跃', 'WARNING', '零基础学习者面对较高难度知识点'))
    else:
        checks.append(CheckItem('difficulty_jump', '难度跳跃', 'PASS', f'{label} 难度与画像匹配'))

    explain = str(bundle.get('explain') or '')
    if len(explain) >= 50:
        checks.append(CheckItem('explain_length', '讲解完整性', 'PASS', '讲解篇幅充足'))
    else:
        checks.append(CheckItem('explain_length', '讲解完整性', 'WARNING', '讲解过短，可能不符合认知规律'))

    styles = analysis.get('recommended_styles') or []
    if styles:
        checks.append(CheckItem('styles', '学习方式', 'PASS', f'推荐：{"、".join(styles[:3])}'))
    else:
        checks.append(CheckItem('styles', '学习方式', 'WARNING', '未推荐呈现方式'))

    score = _score_from_checks(checks)
    summary = '教学质量良好' if score >= 80 else '教学设计需改进'
    return StepResult(step=2, name='教育质量', checks=checks, score=score, summary=summary)
