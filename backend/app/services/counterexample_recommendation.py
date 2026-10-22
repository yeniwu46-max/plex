"""Evidence-led practice links; never generate or publish a challenge here."""
from sqlalchemy import select
from app.models import db
from app.models.counterexample import CounterexampleAttempt as Attempt, CounterexampleVersion as Version, CounterexampleSpec as Spec
from app.services.counterexample import CounterexampleService, actor, Error, Challenge

# Only mappings backed by both an observation rule and the current task taxonomy.
BUG_KINDS = {'loop_end_excluded': 'loop_boundary'}


def completed_challenges(user_id):
    return set(db.session.scalars(select(Version.challenge_id).join(Attempt, Attempt.version_id == Version.id).where(
        Attempt.user_id == user_id, Attempt.status == 'complete',
        Attempt.result['counterexample_found'].as_boolean().is_(True),
        Attempt.result['expected_output_correct'].as_boolean().is_(True)).distinct()))


def recommend(user_id, decision):
    if decision.get('basis') not in {'repeated_candidate', 'confirmed_misconception'}:
        return None
    bug_kind = BUG_KINDS.get(decision.get('misconception_kind'))
    if not bug_kind or not decision.get('concept_id') or not decision.get('evidence_ids'):
        return None
    user = actor(user_id, {'student'})
    completed = completed_challenges(user_id)
    rows = db.session.query(Challenge).join(Version, (Version.challenge_id == Challenge.id)
        & (Version.revision == Challenge.published_revision)).join(Spec, Spec.id == Version.spec_id).filter(
        Challenge.class_id == user.class_id, Challenge.current_revision == Challenge.published_revision,
        Spec.content['concept_id'].as_string() == decision['concept_id'],
        Version.candidate['bug_kind'].as_string() == bug_kind, Version.blocked_reason.is_(None),
        Challenge.id.not_in(completed)).order_by(Challenge.created_at, Challenge.id).limit(30).all()
    for row in rows:
        try:
            public = CounterexampleService.get_student(user_id, row.id)
        except Error:
            continue
        return {'id': public['id'], 'title': public['title'], 'revision': public['revision'], 'version': public['version'],
            'concept_id': public['concept_id'], 'state_version': decision['state_version'],
            'evidence_ids': list(decision['evidence_ids']), 'reason': decision['reason'],
            'practice_path': f"/student/trials/counterexamples/{public['id']}"}
    return None


def refresh_response(user_id, response):
    """Keep saved explanations, but do not replay revoked/replaced/completed links."""
    pick = response.get('counterexample_pick')
    if not pick:
        return response
    try:
        public = CounterexampleService.get_student(user_id, pick['id'])
        available = public['version'] == pick['version'] and pick['id'] not in completed_challenges(user_id)
    except Error:
        available = False
    if not available:
        response['counterexample_pick'] = None
        response['recommendation_notice'] = '原推荐挑战已完成、变更或暂不可访问，请重新获取练习建议。'
    return response
