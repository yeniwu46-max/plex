"""Step 4: exercise quality checks."""
from __future__ import annotations

from .schema import CheckItem, StepResult


def _score_from_checks(checks: list[CheckItem]) -> int:
    score = 100
    for check in checks:
        if check.level == 'FAIL':
            score -= 25
        elif check.level == 'WARNING':
            score -= 8
    return max(0, min(100, score))


def check_exercises(bundle: dict, knowledge_key: str) -> StepResult:
    checks: list[CheckItem] = []
    exercises = [e for e in (bundle.get('exercises') or []) if isinstance(e, dict)]
    type_counts = {'choice': 0, 'fill': 0, 'coding': 0}
    for ex in exercises:
        t = ex.get('type')
        if t in type_counts:
            type_counts[t] += 1

    for t, count in type_counts.items():
        if count >= 2:
            checks.append(CheckItem(f'ex_{t}', f'{t} 题量', 'PASS', f'{count} 题'))
        else:
            checks.append(CheckItem(f'ex_{t}', f'{t} 题量', 'FAIL', f'{t} 题型不足 2 题'))

    missing_answers = [
        ex for ex in exercises
        if not str(ex.get('answer') or '').strip() or not str(ex.get('explanation') or '').strip()
    ]
    if not missing_answers:
        checks.append(CheckItem('ex_answers', '答案完整性', 'PASS', '均含答案与解析'))
    else:
        checks.append(CheckItem('ex_answers', '答案完整性', 'FAIL', f'{len(missing_answers)} 题缺少答案或解析'))

    choice_errors = 0
    for ex in exercises:
        if ex.get('type') != 'choice':
            continue
        options = ex.get('options') or []
        answer = str(ex.get('answer') or '')
        if options and answer and answer not in options:
            choice_errors += 1
    if choice_errors == 0:
        checks.append(CheckItem('ex_choice_valid', '选择题答案', 'PASS', '答案均在选项内'))
    else:
        checks.append(CheckItem('ex_choice_valid', '选择题答案', 'FAIL', f'{choice_errors} 题答案不在选项中'))

    tagged = sum(
        1 for ex in exercises
        if knowledge_key in (ex.get('tags') or [])
    )
    if tagged >= len(exercises) // 2:
        checks.append(CheckItem('ex_coverage', '知识点覆盖', 'PASS', f'{tagged} 题标注 {knowledge_key}'))
    else:
        checks.append(CheckItem('ex_coverage', '知识点覆盖', 'WARNING', '部分练习未标注知识点'))

    coding = [ex for ex in exercises if ex.get('type') == 'coding']
    fill = [ex for ex in exercises if ex.get('type') == 'fill']
    if coding and fill:
        checks.append(CheckItem('ex_gradient', '难度梯度', 'PASS', '含填空与编程梯度'))
    else:
        checks.append(CheckItem('ex_gradient', '难度梯度', 'WARNING', '题型梯度不够丰富'))

    score = _score_from_checks(checks)
    summary = '练习设计合理' if score >= 80 else '练习需补充或修正'
    return StepResult(step=4, name='练习质量', checks=checks, score=score, summary=summary)
