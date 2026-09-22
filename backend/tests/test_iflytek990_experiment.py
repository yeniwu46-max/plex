import csv

from scripts.analyze_iflytek990_experiment import analyze


def _write(path, rows):
    fields = [
        'participant_id', 'stage', 'event_type', 'knowledge_key', 'question_id',
        'is_correct', 'study_minutes', 'recommendation_shown',
        'recommendation_accepted', 'due_reviews', 'completed_reviews',
        'teacher_review_minutes', 'ticket_status', 'timestamp',
    ]
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_experiment_analyzer_reports_paired_effect_and_validation(tmp_path):
    path = tmp_path / 'events.csv'
    _write(path, [
        {'participant_id': 'anon-001', 'stage': 'pre', 'event_type': 'quiz', 'knowledge_key': 'loop', 'question_id': 'q1', 'is_correct': '0', 'timestamp': '2026-08-28T10:00:00Z'},
        {'participant_id': 'anon-001', 'stage': 'post', 'event_type': 'quiz', 'knowledge_key': 'loop', 'question_id': 'q2', 'is_correct': '1', 'timestamp': '2026-08-29T10:00:00Z'},
    ])
    result = analyze(path)
    assert result['validation_passed'] is True
    assert result['paired_pre_post_count'] == 1
    assert result['metrics']['delta_mean'] == 1.0
    assert result['metrics']['delta_median'] == 1.0


def test_experiment_analyzer_flags_pii_like_identifier(tmp_path):
    path = tmp_path / 'events.csv'
    _write(path, [
        {'participant_id': '13800138000', 'stage': 'pre', 'event_type': 'quiz', 'knowledge_key': 'loop', 'question_id': 'q1', 'is_correct': '1', 'timestamp': '2026-08-28T10:00:00Z'},
    ])
    result = analyze(path)
    assert result['validation_passed'] is False
    assert result['validation']['pii_like_participant_ids'] == [2]
