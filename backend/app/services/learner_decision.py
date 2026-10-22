"""A single versioned decision shared by tutoring, exercise choice and review."""
from datetime import datetime, timezone
from app.data.knowledge_node_registry import resolve_node_id
from app.services.misconception_policy import KINDS
from app.utils.time import utc_now


def _concept(value):
    return resolve_node_id(value) or value


class LearnerDecisionService:
    @staticmethod
    def from_snapshot(snapshot, *, focus_concept=None, now=None):
        now = now or utc_now()
        focus = _concept(focus_concept) if focus_concept else None
        relevant = lambda item: not focus or _concept(item['concept_id']) == focus
        candidates = [m for m in snapshot.get('misconceptions', []) if relevant(m)
                      and (m['status'] == 'confirmed' or (m['status'] == 'candidate' and m['distinct_questions'] >= 2))]
        candidates.sort(key=lambda m: (m['status'] != 'confirmed', -m['distinct_questions'], m['id']))
        selected = candidates[0] if candidates else None
        evidence, avoid = [], []
        if selected:
            focus = _concept(selected['concept_id'])
            rule = KINDS[selected['kind']]
            reason = ('教师已确认，需要针对性复核。' if selected['status'] == 'confirmed'
                      else '同一现象出现在至少两道正式题中，先验证是否存在理解偏差。')
            hint, exercise, review = rule['hint'], rule['exercise'], rule['review']
            evidence = [e['event_id'] for e in selected['evidence']]
            avoid = list(dict.fromkeys(e['question_id'] for e in selected['evidence']))
            basis = 'confirmed_misconception' if selected['status'] == 'confirmed' else 'repeated_candidate'
        else:
            due = []
            for item in snapshot['concepts']:
                if not relevant(item):
                    continue
                for field in ('review_due_at','counterexample_review_due_at'):
                    if not item.get(field):
                        continue
                    try:
                        at = datetime.fromisoformat(item[field].replace('Z', '+00:00'))
                        if at.tzinfo:
                            at = at.astimezone(timezone.utc).replace(tzinfo=None)
                        if at <= now:
                            due.append((at, item, field))
                    except ValueError:
                        continue
            weak = [c for c in snapshot['concepts'] if relevant(c) and c['estimate'] is not None
                    and c['independent_count'] + c['assisted_count'] >= 2 and c['estimate'] < .5]
            weak.sort(key=lambda c: (c['estimate'], c['concept_id']))
            if due:
                selected_due = min(due, key=lambda pair: pair[0])
                focus = _concept(selected_due[1]['concept_id'])
                basis, reason = (('counterexample_review', '反例实践后的独立迁移练习已到期；找到反例不等于算法已掌握。')
                    if selected_due[2]=='counterexample_review_due_at' else ('review_due', '已有复习计划到期；这不是一次新的测验判断。'))
            elif weak:
                focus = _concept(weak[0]['concept_id'])
                basis, reason = 'formal_evidence', '近期正式作答仍有未通过项，建议用一道不同题目核对。'
            else:
                basis, reason = 'baseline', '现有证据不足以作出专项诊断，先了解当前思路。'
            hint = '先说明你预计程序会做什么，再选一个小输入手工核对。'
            exercise = '选择一道当前知识点的基础练习，先独立尝试'
            review = '回顾这次练习的关键条件；未作答前不提前认定掌握程度'
            evidence = [c['event_id'] for c in snapshot.get('changes', [])
                        if focus and _concept(c.get('concept_id')) == focus][:10]
        common = {'state_version': snapshot['state_version'], 'concept_id': focus,
                  'evidence_ids': evidence, 'reason': reason}
        return {**common, 'basis': basis, 'misconception_kind': selected['kind'] if selected else None, 'hint': {**common, 'action': hint},
                'next_exercise': {**common, 'action': exercise, 'avoid_question_ids': avoid},
                'review': {**common, 'action': review}}
