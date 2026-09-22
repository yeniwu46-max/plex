from scripts.audit_iflytek990_completion import audit


def test_completion_audit_keeps_local_and_external_gates_separate():
    report = audit()
    assert report['local_passed'] is True
    assert report['submission_ready'] is False
    assert report['missing'] == []
    assert {'spark_live', 'experiment', 'mp4'}.issubset(set(report['blocked_external']))
    assert report['verified_local_count'] >= 10

