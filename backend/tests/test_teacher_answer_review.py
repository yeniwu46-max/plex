"""All grades here are synthetic test fixtures, never published as human evaluation."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json

import pytest

from scripts.check_teacher_answers import check, load_run
from scripts.teacher_baseline_contract import ContractError, read_json
from scripts.evaluate_teacher_baseline import run, ARMS
from test_teacher_evaluation import artifact, provider, Response


@pytest.fixture
def comparison(tmp_path):
    directory = tmp_path/'run'
    run(artifact(tmp_path), directory, maximum_cases=1, provider=provider())
    return directory, read_json(directory/'blind-review.json')


def fill(marked):
    value = deepcopy(marked)
    value['reviewers'] = [{'id':'test-only-person', 'declares_python_teaching_experience':True,
                          'declares_personal_review':True}]
    for row in value['items']:
        row.update(reviewer_id='test-only-person', reviewed_at=datetime.now(timezone.utc).isoformat(),
            rationale='Synthetic fixture only, no person has actually reviewed this answer.')
        row['scores'] = {'correctness':2,'evidence_support':'not_applicable','teaching_action':2,
                         'actionable_next_step':1,'answer_leakage':False,'over_refusal':False}
    return value


def test_blank_reviews_never_create_quality_metrics(comparison):
    directory, marked = comparison
    report = check(directory, marked)
    assert report['status'] == 'pending_human_review'
    assert report['reviewed_answers'] == 0 and report['pending_answers'] == 3
    assert report['quality_metrics'] is None


def test_complete_declared_reviews_report_denominators_and_na_separately(comparison):
    directory, marked = comparison
    report = check(directory, fill(marked))
    assert report['status'] == 'reviewed' and report['reviewed_answers'] == 3
    assert set(report['quality_metrics']) == set(ARMS)
    assert report['reviewer_identity_verified_by_tool'] is False
    assert report['complete_split'] is False and report['selected_cases'] == 1
    assert report['learning_gain'] is None and report['causal_state_effect'] is None
    for metrics in report['quality_metrics'].values():
        assert metrics['correctness']['mean_ordinal_0_to_3'] == 2
        assert metrics['evidence_support'] == {'mean_ordinal_0_to_3':None,'scored':0,'not_applicable':1}
        assert metrics['answer_leakage']['denominator'] == 1


@pytest.mark.parametrize('change', ['answer','source','duplicate','score','bool','reviewer','future','before_run','missing_field','invalid_id','invalid_reviewer'])
def test_invalid_or_changed_reviews_are_rejected(comparison, change):
    directory, marked = comparison
    marked = fill(marked)
    row = marked['items'][0]
    if change == 'answer': row['answer']['text'] += 'tampered'
    if change == 'source': row['retrieved_sources'] = [{'forged':'evidence'}]
    if change == 'duplicate': marked['items'][1] = deepcopy(row)
    if change == 'score': row['scores']['correctness'] = 4
    if change == 'bool': row['scores']['correctness'] = True
    if change == 'reviewer': row['reviewer_id'] = 'unknown-person'
    if change == 'future': row['reviewed_at'] = (datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
    if change == 'before_run': row['reviewed_at'] = '2020-01-01T00:00:00+00:00'
    if change == 'missing_field': del row['rationale']
    if change == 'invalid_id': row['review_id'] = []
    if change == 'invalid_reviewer': row['reviewer_id'] = []
    with pytest.raises(ContractError): check(directory, marked)


def test_partial_grades_stay_pending_even_if_user_claims_complete(comparison):
    directory, marked = comparison
    marked = fill(marked)
    marked['items'][0]['scores']['correctness'] = None
    marked['reviewed'] = 3000
    marked['status'] = 'reviewed'
    report = check(directory, marked)
    assert report['reviewed_answers'] == 2 and report['pending_answers'] == 1
    assert report['quality_metrics'] is None


def test_changed_run_or_path_traversal_cannot_be_used_for_grading(comparison):
    directory, _ = comparison
    path = directory/'report.json'
    contents = read_json(path); contents['status'] = 'tampered'
    path.write_text(json.dumps(contents), encoding='utf-8')
    with pytest.raises(ContractError, match='changed'): load_run(directory)
    proof = read_json(directory/'integrity.json')
    proof['files']['../../outside.json'] = 'forged'
    # Put unsafe name first, proving rejection before trying to open it.
    proof['files'] = {'../../outside.json':'forged', **proof['files']}
    (directory/'integrity.json').write_text(json.dumps(proof), encoding='utf-8')
    with pytest.raises(ContractError, match='Unsafe'): load_run(directory)


def test_failed_experiment_cannot_become_a_valid_comparison_by_filling_grades(tmp_path):
    directory = tmp_path/'run'
    run(artifact(tmp_path), directory, maximum_cases=1,
        provider=provider(lambda *a, **kw:Response('Answer', model=None)))
    marked = fill(read_json(directory/'blind-review.json'))
    report = check(directory, marked)
    assert report['status'] == 'incomplete_experiment' and report['quality_metrics'] is None
