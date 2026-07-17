"""Step 3: case quality checks."""
from __future__ import annotations

from app.data.course_knowledge import catalog_points

from .schema import CheckItem, StepResult


def _score_from_checks(checks: list[CheckItem]) -> int:
    score = 100
    for check in checks:
        if check.level == 'FAIL':
            score -= 25
        elif check.level == 'WARNING':
            score -= 8
    return max(0, min(100, score))


def check_cases(bundle: dict, knowledge_key: str) -> StepResult:
    checks: list[CheckItem] = []
    cases = [c for c in (bundle.get('cases') or []) if isinstance(c, dict)]
    label = catalog_points().get(knowledge_key, knowledge_key)

    if len(cases) >= 2:
        checks.append(CheckItem('case_count', '案例数量', 'PASS', f'{len(cases)} 个案例'))
    else:
        checks.append(CheckItem('case_count', '案例数量', 'FAIL', '至少需要 2 个案例'))

    titles = [str(c.get('title') or '') for c in cases]
    if len(titles) == len(set(titles)):
        checks.append(CheckItem('case_unique', '案例去重', 'PASS', '标题无重复'))
    else:
        checks.append(CheckItem('case_unique', '案例去重', 'FAIL', '存在重复案例标题'))

    real_count = sum(1 for c in cases if str(c.get('why_real') or c.get('scenario') or '').strip())
    if real_count >= len(cases):
        checks.append(CheckItem('case_realism', '案例真实性', 'PASS', '案例包含真实场景描述'))
    else:
        checks.append(CheckItem('case_realism', '案例真实性', 'WARNING', '部分案例缺少真实性说明'))

    aligned = 0
    for case in cases:
        text = ' '.join([
            str(case.get('title') or ''),
            str(case.get('scenario') or ''),
            str(case.get('key_idea') or ''),
        ]).lower()
        if label.lower() in text or knowledge_key in text or any(
            token in text for token in label.replace('与', ' ').split() if len(token) >= 2
        ):
            aligned += 1
    if aligned >= max(1, len(cases) - 1):
        checks.append(CheckItem('case_topic', '知识点匹配', 'PASS', f'{aligned}/{len(cases)} 与 {label} 相关'))
    else:
        checks.append(CheckItem('case_topic', '知识点匹配', 'WARNING', '部分案例与知识点关联弱'))

    life_like = sum(
        1 for c in cases
        if any(word in str(c.get('scenario') or '') for word in ('脚本', '工具', '游戏', '数据', '团队', '运维', '教务'))
    )
    if life_like >= 1:
        checks.append(CheckItem('case_life', '生活贴近度', 'PASS', '包含贴近生活的场景'))
    else:
        checks.append(CheckItem('case_life', '生活贴近度', 'WARNING', '案例场景偏抽象'))

    score = _score_from_checks(checks)
    summary = '案例质量良好' if score >= 80 else '案例需补充或调整'
    return StepResult(step=3, name='案例质量', checks=checks, score=score, summary=summary)
