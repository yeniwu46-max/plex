from scripts import evaluate_iflytek_live as live


def test_live_benchmark_uses_generic_spark_credential(monkeypatch):
    calls = []

    class FakeSpark:
        @staticmethod
        def configured():
            return True

        @staticmethod
        def chat_json(*args, **kwargs):
            calls.append(kwargs)
            return {'response': 'ok', 'grounded': True, 'knowledge_key': 'python-list'}

        @staticmethod
        def status():
            return {'model': 'generalv3'}

    monkeypatch.setattr(live, 'IflytekSparkService', FakeSpark)
    report = live.run(1)

    assert report['status'] == 'completed'
    assert report['success_count'] == 1
    assert calls == [{'timeout': 20}]
