"""One real course RAG call in a disposable synthetic database; verify free recovery."""
import argparse
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real-model', action='store_true')
    parser.add_argument('--verify-pricing', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT.parent / 'output/plex-p4-rag-live.json')
    args = parser.parse_args()
    if not args.real_model:
        parser.error('Pass --real-model to call the configured provider with synthetic course data.')
    import requests
    from flask_jwt_extended import create_access_token
    from werkzeug.serving import make_server
    from app import create_app
    from app.config import TestingConfig
    from app.models import db, User, KnowledgeDocument
    from app.models.ai_runtime import AiModelCall
    from app.models.rag_runtime import RagRequestAttempt
    from app.services.knowledge.knowledge_service import KnowledgeService
    from app.services.knowledge.index_service import IndexService

    root = (ROOT.parent / 'output').resolve()
    with TemporaryDirectory(prefix='plex-rag-acceptance-', dir=root) as temporary:
        folder = Path(temporary).resolve()
        assert folder.parent == root and folder.name.startswith('plex-rag-acceptance-')
        TestingConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///' + (folder / 'acceptance.db').as_posix()
        TestingConfig.SQLALCHEMY_ECHO = False
        os.environ.update(EMBEDDING_PROVIDER='local', VECTOR_BACKEND='local', VECTOR_STORE_PATH=str(folder / 'vectors'), RAG_LLM_ENABLED='true')
        app = create_app('testing'); app.instance_path = str(folder / 'instance')
        app.config.update(LLM_ALLOW_IN_TESTS=True, LEARNER_STATE_READ_MODE='evidence', CODE_EXECUTION_BACKEND='disabled', RAG_DAILY_REQUEST_LIMIT=1)
        with app.app_context():
            teacher = User.query.filter_by(username='teacher001').one()
            admin = User.query.filter_by(username='admin').first() or User.query.filter_by(username='admin001').one()
            teacher_id = teacher.id
            headers = {'Authorization': 'Bearer ' + create_access_token(identity=str(teacher.id))}
            KnowledgeService.ensure_ready(seed_graph=True, index_builtin=False)
            doc = IndexService.register_text(title='for循环：范围与边界', user_id=admin.id, chapter='循环', concept_hints=['loop-for'], auto_index=True,
                text='# for循环：范围与边界\n\nfor循环用于遍历序列，循环变量依次获得每个元素，再执行循环体。'
                     'range(start, stop) 包含 start，不包含 stop，步长默认是 1。range(1, 4) 依次提供 1、2、3。'
                     '通过追踪表逐轮记录循环变量和累加器，可以核对循环次数。空列表不会执行循环体，累加器应在循环之前初始化。'
                     '常见错误是误认为停止值也会被遍历，或把初始化写在循环体内部。')
            assert doc.status == 'READY'
            doc.visibility, doc.published = 'public', True
            db.session.commit(); doc_id = doc.id
            plan = KnowledgeService.prepare('for循环边界 range(1,4)', user_id=teacher_id, role='teacher', context={'concept_hint': 'loop-for'})
            assert plan.knowledge_grounded and plan.context.source_index, 'Synthetic evidence must be retrieved before calling model'
        server = make_server('127.0.0.1', 0, app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        base = f'http://127.0.0.1:{server.server_port}/api/v1/rag'
        evidence = {'status': 'incomplete', 'synthetic_fixture': True, 'business_records_changed': False,
                    'embedding': 'local_hash', 'vector_backend': 'local', 'human_review': False}
        try:
            rid = str(uuid.uuid4())
            body = {'query': 'for循环的 range(1,4) 为什么不包含停止值，如何用追踪表核对循环边界？',
                    'context': {'concept_hint': 'loop-for'}, 'request_id': rid}
            response = requests.post(base + '/query', headers=headers, json=body, timeout=110)
            evidence['create_http'] = response.status_code
            assert response.status_code == 200
            data = response.json()['data']
            evidence['generation_mode'] = data['generation_mode']; evidence['source_count'] = len(data['sources'])
            assert data['request_id'] == rid and data['generation_mode'] == 'llm' and data['sources']
            with app.app_context():
                calls = AiModelCall.query.all(); count = len(calls)
                evidence['calls'] = [{key: getattr(row, key) for key in ('stage', 'provider', 'model', 'status', 'error_code', 'prompt_tokens', 'completion_tokens', 'total_tokens', 'elapsed_ms')} for row in calls]
                assert calls and all(row.workflow == 'rag' and row.user_id == teacher_id and row.request_id == rid for row in calls)
                assert any(row.status == 'succeeded' and row.total_tokens is not None for row in calls)
                if args.verify_pricing:
                    from app.services.model_accounting import summary
                    from decimal import Decimal
                    priced = [row for row in calls if row.cost_status in ('estimated', 'estimated_range')]
                    assert priced, 'Actual provider/model/usage must match a verified active rate'
                    for row in priced:
                        rate = row.price_snapshot
                        assert rate['matched_model'] == row.model and len(rate['card_hash']) == 64
                        p, c, hit = row.prompt_tokens, row.completion_tokens, row.cached_input_tokens
                        low_hit, high_hit = (p, 0) if hit is None else (hit, hit)
                        lo = (Decimal(p-low_hit)*Decimal(rate['input']['min']) + Decimal(low_hit)*Decimal(rate['cached_input']['min']) + Decimal(c)*Decimal(rate['output']['min'])) / Decimal(1000000)
                        hi = (Decimal(p-high_hit)*Decimal(rate['input']['max']) + Decimal(high_hit)*Decimal(rate['cached_input']['max']) + Decimal(c)*Decimal(rate['output']['max'])) / Decimal(1000000)
                        assert row.cost_min <= lo <= hi <= row.cost_max
                    evidence['pricing'] = summary(teacher_id)['cost_estimate']
                    evidence['price_sources'] = [{'provider':r.provider,'model':r.model,'rate_id':r.price_snapshot['id'],
                        'source_url':r.price_snapshot['source_url'],'valid_until':r.price_snapshot['valid_until'],
                        'cache_split':r.price_snapshot['cache_split']} for r in priced]
                    assert not evidence['pricing']['invoice_verified']

            replay = requests.post(base + '/query', headers=headers, json=body, timeout=20)
            restored = requests.get(base + '/requests/' + rid, headers=headers, timeout=20)
            assert replay.status_code == restored.status_code == 200
            assert replay.json()['data'] == data == restored.json()['data']['answer']
            refused = requests.post(base + '/query', headers=headers, json={**body, 'request_id': str(uuid.uuid4())}, timeout=20)
            assert refused.status_code == 429
            quota = requests.get(base + '/usage', headers=headers, timeout=20)
            assert quota.json()['data']['requests_used'] == 1
            if args.verify_pricing:
                cost_response = requests.get(base.removesuffix('/rag')+'/ai/usage', headers=headers, timeout=20)
                assert cost_response.status_code == 200
                assert cost_response.json()['data']['cost_estimate'] == evidence['pricing']

            with app.app_context():
                assert AiModelCall.query.count() == count and RagRequestAttempt.query.count() == 1
                KnowledgeDocument.query.filter_by(id=doc_id).update({'visibility': 'private', 'published': False}); db.session.commit()
            revoked = requests.get(base + '/requests/' + rid, headers=headers, timeout=20)
            repeat_revoked = requests.post(base + '/query', headers=headers, json=body, timeout=20)
            assert revoked.status_code == repeat_revoked.status_code == 409
            assert revoked.json()['data'] == {'reason': 'sources_changed'}
            with app.app_context(): assert AiModelCall.query.count() == count
            evidence.update(status='passed', replay_no_model_calls=True, recovery_no_model_calls=True,
                quota_http=429, revoked_http=409, revoked_content_hidden=True, quota=quota.json()['data'])
        finally:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(json.dumps(evidence, ensure_ascii=False, indent=2).encode())
            server.shutdown(); thread.join(timeout=10)
            with app.app_context(): db.session.remove(); db.engine.dispose()
        print(json.dumps({'status': evidence['status'], 'calls': len(evidence.get('calls', [])), 'revoked_content_hidden': evidence.get('revoked_content_hidden', False)}))


if __name__ == '__main__':
    main()
