"""Live tutoring cancellation and accounting using synthetic course data only."""
import argparse
import json
import os
import re
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Thread, Event
from concurrent.futures import ThreadPoolExecutor
import time
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real-model', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT.parent / 'output/plex-p4-runtime-live.json')
    args = parser.parse_args()
    if not args.real_model:
        parser.error('Pass --real-model to call the configured provider using synthetic data only.')
    import requests
    from flask_jwt_extended import create_access_token
    from werkzeug.serving import make_server
    from app import create_app
    from app.config import TestingConfig
    from app.models import db, User, Class, KnowledgeDocument
    from app.services.knowledge.knowledge_service import KnowledgeService
    from app.services.knowledge.index_service import IndexService
    from app.services.knowledge.access_service import KnowledgeAccessService
    from app.services.resource_learning_context import ResourceLearningContext
    from app.services.resource_course_evidence import ResourceCourseEvidence
    from app.services.personalized_resource import PersonalizedResourceService

    from app.services.knowledge.providers.llm import get_llm_provider, LLMProvider
    delegate = get_llm_provider()
    calls = []
    model_started = Event()
    class ObservedProvider(LLMProvider):
        def available(self): return delegate.available()
        def generate(self, **kwargs):
            model_started.set()
            result = delegate.generate(**kwargs, preserve_text=True)
            calls.append({'ok':result is not None, 'model':getattr(result,'model',None), 'provider':getattr(result,'provider',None)})
            if result:
                from agents.llm_client import _extract_json
                parsed=_extract_json(result.text) or {}
                calls[-1]['citation_ids']=[r.get('chunk_id') for r in parsed.get('citations',[]) if isinstance(r,dict)]
            return result
    output_root = (ROOT.parent / 'output').resolve()
    with TemporaryDirectory(prefix='plex-runtime-acceptance-', dir=output_root) as temporary:
        folder = Path(temporary).resolve()
        assert folder.parent == output_root and folder.name.startswith('plex-runtime-acceptance-')
        TestingConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///' + (folder / 'acceptance.db').as_posix()
        TestingConfig.SQLALCHEMY_ECHO = False
        os.environ.update(EMBEDDING_PROVIDER='local', VECTOR_BACKEND='local', VECTOR_STORE_PATH=str(folder / 'vectors'))
        app = create_app('testing')
        app.instance_path = str(folder / 'instance')
        app.config.update(LLM_ALLOW_IN_TESTS=True, TUTOR_MODELS_ENABLED=True, LEARNER_STATE_READ_MODE='evidence', CODE_EXECUTION_BACKEND='disabled')
        with app.app_context():
            teacher = User.query.filter_by(username='teacher001').one()
            student = User.query.filter_by(username='student001').one()
            classroom = Class(name='课程资源开发验收', teacher_id=teacher.id, grade_level=1)
            db.session.add(classroom); db.session.flush(); student.class_id = classroom.id; db.session.commit()
            KnowledgeService.ensure_ready(seed_graph=True, index_builtin=False)
            document = IndexService.register_text(title='for循环：端点与执行次序', user_id=teacher.id,
                chapter='循环', concept_hints=['loop-for'], text=(
                    '# for循环：端点与执行次序\n\n'
                    'for循环用于遍历序列。for循环的循环变量依次获得每个元素，再执行循环体。'
                    'range(start, stop) 包含 start，不包含 stop，步长默认是 1。'
                    '例如 range(1, 4) 依次提供 1、2、3，循环体执行三次。'
                    '通过追踪表逐轮记录循环变量及累加变量，可以核对边界条件。'
                    '空序列不会执行循环体，所以累加器应在循环之前初始化。'
                    '常见错误是误认为停止值也会被遍历，或把初始化放在循环内部。'), auto_index=True)
            assert document.status == 'READY'
            document_id = document.id
            KnowledgeAccessService.update(teacher.id, document_id, {'visibility':'class','class_id':classroom.id,'published':True})
            student_id = student.id
            headers = {'Authorization':'Bearer '+create_access_token(identity=str(student.id))}
            # Confirm actual local index/BM25/graph retrieval before spending model tokens.
            manifest, _ = ResourceCourseEvidence.retrieve(ResourceLearningContext.capture(student.id,'loop-for'),
                'for循环', PersonalizedResourceService._citation('loop-for'))
            assert manifest['status'] == 'retrieved', 'Synthetic document was not retrieved'
        server = make_server('127.0.0.1', 0, app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        base = f'http://127.0.0.1:{server.server_port}/api/v1'
        evidence={'synthetic_fixture':True,'business_records_changed':False,'embedding':'local_hash','vector_backend':'local','model_calls':calls}
        try:
            with patch('app.services.tutoring.get_llm_provider',return_value=ObservedProvider()):
                body={'topic':'Python for循环的range停止值和空序列边界','request_id':str(uuid.uuid4())}
                complete=requests.post(base+'/student/messenger/tools/learning-document',headers=headers,json=body,timeout=100)
                evidence['completed_http']=complete.status_code
                evidence['completed_status']=complete.json().get('data',{}).get('status')
                assert complete.status_code==200 and evidence['completed_status']=='ok'
                body={**body,'request_id':str(uuid.uuid4())};model_started.clear()
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future=pool.submit(requests.post,base+'/student/messenger/tools/learning-document',headers=headers,json=body,timeout=100)
                    assert model_started.wait(15),'Model did not begin within acceptance wait'
                    stopped=requests.post(base+'/student/tutor/turns/'+body['request_id']+'/cancel',headers=headers,timeout=20)
                    evidence['cancel_http']=stopped.status_code;evidence['cancelled']=stopped.json().get('data',{}).get('cancelled')
                    assert evidence['cancelled'] is True
                    evidence['cancelled_generation_http']=future.result(timeout=100).status_code
                    assert evidence['cancelled_generation_http']==409
                retry=requests.post(base+'/student/messenger/tools/learning-document',headers=headers,json=body,timeout=20)
                evidence['cancelled_retry_http']=retry.status_code
                assert retry.status_code==409
                use=requests.get(base+'/student/tutor/usage',headers=headers,timeout=20).json()['data']
                evidence['usage']=use
                assert use['requests_used']==2 and use['model_calls']==3 and use['active_requests']==0 and use['cancelled_requests']==1
                from app.models.ai_runtime import AiModelCall,TutorRequestAttempt
                from app.models.tutor_session import TutorTurn
                from app.models.learner_state import LearningEvent,TutorDisplayReceipt
                with app.app_context():
                    stopped_turn=db.session.get(TutorTurn,body['request_id'])
                    evidence['cancelled_output_absent']=stopped_turn.response is None and stopped_turn.receipt_id is None
                    evidence['learning_events']=LearningEvent.query.count();evidence['display_receipts']=TutorDisplayReceipt.query.count()
                    evidence['ledger']=[{'stage':row.stage,'provider':row.provider,'model':row.model,'status':row.status,
                        'total_tokens':row.total_tokens,'elapsed_ms':row.elapsed_ms} for row in AiModelCall.query.order_by(AiModelCall.started_at).all()]
                assert evidence['cancelled_output_absent'] and evidence['learning_events']==evidence['display_receipts']==0
                assert len(evidence['ledger'])==3 and all(row['provider']=='deepseek' for row in evidence['ledger'])
        finally:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_bytes(json.dumps(evidence,ensure_ascii=False,indent=2).encode())
            server.shutdown();thread.join(timeout=10)
            with app.app_context():db.session.remove();db.engine.dispose()
        print(json.dumps({'status':'passed','cancelled':evidence['cancelled'],'model_calls':len(evidence['ledger']),'learning_events':evidence['learning_events']}))



if __name__ == '__main__':
    main()
