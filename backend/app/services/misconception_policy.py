"""Conservative, versioned signals and teacher review for programming misconceptions."""
import ast
from sqlalchemy import select, or_
from app.models.learner_misconception import LearnerMisconception, LearnerMisconceptionEvidence
from app.models.learner_state import LearningEvent
from app.utils.time import utc_now

RULE_VERSION = 'python-observation-v1'
KINDS = {
    'loop_end_excluded': {'label': '循环结束边界', 'hint': '手工列出循环访问的索引，核对最后一个元素是否需要处理。',
                         'exercise': '选择包含末项和单元素输入的循环练习', 'review': '复习 range 结束位置不包含在序列中的规则'},
    'recursion_missing_guard': {'label': '递归终止条件', 'hint': '先找出最小输入，检查它能否不再递归而直接返回。',
                                'exercise': '选择要求明确最小输入与终止条件的递归练习', 'review': '复习递归终止条件与问题规模缩小'},
}


def detect_signals(code, grade_result):
    """Static observation + failed server execution => candidate only, not diagnosis."""
    if grade_result.get('code_passed') is not False or not code:
        return []
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError):
        return []
    signals = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'range' and node.args:
            stop = node.args[0] if len(node.args) == 1 else node.args[1]
            if (isinstance(stop, ast.BinOp) and isinstance(stop.op, ast.Sub)
                and isinstance(stop.right, ast.Constant) and stop.right.value == 1
                and isinstance(stop.left, ast.Call) and isinstance(stop.left.func, ast.Name)
                and stop.left.func.id == 'len'):
                signals['loop_end_excluded'] = {'kind': 'loop_end_excluded', 'rule_version': RULE_VERSION,
                    'observation': f'第 {node.lineno} 行的 range 结束位置使用 len(...) - 1，且正式测试未全部通过；是否为错误仍待核对。'}
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nodes = list(ast.walk(node))
            recursive = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == node.name for n in nodes)
            guarded = any(isinstance(n, (ast.If, ast.IfExp, ast.Match, ast.While)) for n in nodes)
            recursion_error = any('RecursionError' in str(result.get('stderr') or result.get('error') or '')
                                  for result in grade_result.get('results', []))
            if recursive and not guarded and recursion_error:
                signals['recursion_missing_guard'] = {'kind': 'recursion_missing_guard', 'rule_version': RULE_VERSION,
                    'observation': f'第 {node.lineno} 行函数调用自身、未发现显式条件分支，正式执行报告 RecursionError；需核对终止条件。'}
    return list(signals.values())


class MisconceptionPolicy:
    @staticmethod
    def apply(session, state, event, version):
        if event.kind == 'misconception_reviewed':
            row = session.get(LearnerMisconception, event.payload['misconception_id'], with_for_update=True)
            if not row or row.state_id != state.id or row.revision != event.payload['expected_revision']:
                raise ValueError('misconception_version_conflict')
            action = event.payload['action']
            if action not in ('confirm', 'dismiss', 'reopen'):
                raise ValueError('invalid_review')
            row.manual_status = {'confirm': 'confirmed', 'dismiss': 'dismissed', 'reopen': None}[action]
            row.status = row.manual_status or 'candidate'
            row.reviewer_id = event.payload['reviewer_id']
            row.review_note = event.payload['note']
            row.reviewed_at = event.occurred_at
            row.revision += 1
            row.updated_version, row.updated_at = version, utc_now()
            return
        if event.kind != 'submission_graded':
            return
        payload = event.payload
        concept = payload.get('concept_id')
        signals = payload.get('diagnostic_signals') or []
        if not isinstance(signals, list) or len(signals) > len(KINDS):
            raise ValueError('invalid_diagnostic_signals')
        seen = set()
        if signals and (payload.get('correct') or type(payload.get('question_id')) is not int):
            raise ValueError('invalid_diagnostic_signal')
        for signal in signals:
            if (not isinstance(signal, dict) or signal.get('kind') not in KINDS
                or signal.get('rule_version') != RULE_VERSION or not isinstance(signal.get('observation'), str)
                or not 1 <= len(signal['observation']) <= 240 or signal['kind'] in seen):
                raise ValueError('unknown_diagnostic_rule')
            seen.add(signal['kind'])
            row = session.scalar(select(LearnerMisconception).where(
                LearnerMisconception.state_id == state.id, LearnerMisconception.concept_id == concept,
                LearnerMisconception.kind == signal['kind']))
            if row is None:
                row = LearnerMisconception(state_id=state.id, concept_id=concept, kind=signal['kind'],
                    status='candidate', revision=0, updated_version=version, last_signal_at=event.occurred_at)
                session.add(row); session.flush()
            row.last_signal_at = max(row.last_signal_at, event.occurred_at)
            session.add(LearnerMisconceptionEvidence(misconception_id=row.id, event_id=event.id,
                question_id=payload['question_id'], observation=signal['observation'][:240]))
        session.flush()
        rows = session.scalars(select(LearnerMisconception).where(
            LearnerMisconception.state_id == state.id, LearnerMisconception.concept_id == concept)).all()
        # Derive mitigation from distinct later independent successes. Recompute
        # after out-of-order events rather than trusting processing sequence.
        for row in rows:
            later = session.scalars(select(LearningEvent).where(
                LearningEvent.user_id == event.user_id, LearningEvent.course == event.course,
                LearningEvent.kind == 'submission_graded', LearningEvent.occurred_at > row.last_signal_at,
                or_(LearningEvent.status == 'done', LearningEvent.id == event.id))).all()
            successful_questions = {e.payload.get('question_id') for e in later
                if e.payload.get('concept_id') == concept and e.payload.get('correct') is True
                and e.payload.get('assisted') is False and e.payload.get('question_id') is not None}
            if row.manual_status == 'dismissed':
                row.status = 'dismissed'  # New model/rule signals cannot override the teacher.
            elif len(successful_questions) >= 2:
                row.status = 'mitigated'
            else:
                row.status = row.manual_status or 'candidate'
            row.revision += 1
            row.updated_version, row.updated_at = version, utc_now()

    @staticmethod
    def serialize(session, state_id):
        rows = session.scalars(select(LearnerMisconception).where(
            LearnerMisconception.state_id == state_id).order_by(LearnerMisconception.updated_at.desc())).all()
        result = []
        for row in rows:
            evidence = session.execute(select(LearnerMisconceptionEvidence, LearningEvent.occurred_at).join(
                LearningEvent, LearningEvent.id == LearnerMisconceptionEvidence.event_id).where(
                LearnerMisconceptionEvidence.misconception_id == row.id).order_by(LearningEvent.occurred_at.desc())).all()
            result.append({'id': row.id, 'concept_id': row.concept_id, 'kind': row.kind, 'label': KINDS[row.kind]['label'],
                'status': row.status, 'revision': row.revision, 'rule_version': RULE_VERSION,
                'distinct_questions': len({e.question_id for e, _ in evidence}),
                'evidence': [{'event_id': e.event_id, 'observation': e.observation, 'question_id': e.question_id,
                              'occurred_at': at.isoformat()} for e, at in evidence[:10]],
                'reviewer_id': row.reviewer_id, 'review_note': row.review_note, 'updated_version': row.updated_version,
                'explanation': '由规则提出，需核对代码意图；重复出现不等于已确认。' if row.status == 'candidate'
                    else '后续两道独立练习通过，暂记为已缓解，仍需观察。' if row.status == 'mitigated'
                    else '由任课教师核对并处理。'})
        return result
