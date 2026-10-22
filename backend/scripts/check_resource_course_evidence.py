"""Actual HTTP, indexing and model generation in an isolated synthetic database."""
import argparse
import json
import os
import re
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real-model', action='store_true')
    parser.add_argument('--verify-accounting', action='store_true')
    parser.add_argument('--verify-admission', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT.parent / 'output/plex-p2-course-live.json')
    args = parser.parse_args()
    if not args.real_model:
        parser.error('Pass --real-model to call the configured provider using synthetic data only.')
    import requests
    from flask_jwt_extended import create_access_token
    from werkzeug.serving import make_server
    from app import create_app
    from app.config import TestingConfig
    from app.models import db, User, Class, ResourceGenerationTask, KnowledgeDocument
    from app.services.knowledge.knowledge_service import KnowledgeService
    from app.services.knowledge.index_service import IndexService
    from app.services.knowledge.access_service import KnowledgeAccessService
    from app.services.resource_learning_context import ResourceLearningContext
    from app.services.resource_course_evidence import ResourceCourseEvidence
    from app.services.personalized_resource import PersonalizedResourceService

    output_root = (ROOT.parent / 'output').resolve()
    with TemporaryDirectory(prefix='plex-course-acceptance-', dir=output_root) as temporary:
        folder = Path(temporary).resolve()
        assert folder.parent == output_root and folder.name.startswith('plex-course-acceptance-')
        TestingConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///' + (folder / 'acceptance.db').as_posix()
        TestingConfig.SQLALCHEMY_ECHO = False
        if args.verify_accounting: os.environ['RAG_LLM_ENABLED']='true'
        os.environ.update(EMBEDDING_PROVIDER='local', VECTOR_BACKEND='local', VECTOR_STORE_PATH=str(folder / 'vectors'))
        app = create_app('testing')
        app.instance_path = str(folder / 'instance')
        app.config.update(LLM_ALLOW_IN_TESTS=True, LEARNER_STATE_READ_MODE='evidence', CODE_EXECUTION_BACKEND='disabled')
        if args.verify_admission:app.config.update(RESOURCE_USER_DAILY_LIMIT=1,RESOURCE_CLASS_DAILY_LIMIT=1)
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
            student_id, teacher_id, class_id = student.id, teacher.id, classroom.id
            teacher_headers = {'Authorization':'Bearer '+create_access_token(identity=str(teacher.id))}
            headers = {'Authorization':'Bearer '+create_access_token(identity=str(student.id))}
            # Confirm actual local index/BM25/graph retrieval before spending model tokens.
            manifest, _ = ResourceCourseEvidence.retrieve(ResourceLearningContext.capture(student.id,'loop-for'),
                'for循环', PersonalizedResourceService._citation('loop-for'))
            assert manifest['status'] == 'retrieved', 'Synthetic document was not retrieved'
        server = make_server('127.0.0.1', 0, app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        base = f'http://127.0.0.1:{server.server_port}/api/v1'
        started = time.perf_counter()
        evidence = {'synthetic_fixture':True, 'business_records_changed':False, 'human_review':False,
                    'embedding':'local_hash', 'vector_backend':'local', 'code_execution':'disabled'}
        try:
            response = requests.post(base+'/student/resource-generation/tasks', headers=headers, json={
                'knowledge_key':'loop-for','resource_types':['learning_bundle'], 'force_regenerate':True,
                'require_real_api':True,'idempotency_key':'real-admission-check'}, timeout=240)
            assert response.status_code == 201, f'create status {response.status_code}'
            task = response.json()['data']
            evidence.update(task_status=task['status'], backend=task['backend'], fallback_reason=task.get('fallback_reason'),
                failure_reason=re.sub(r'(sk-[\w-]+|Bearer \S+|https?://\S+)', '[redacted]', str(task.get('error') or ''))[:500],
                course_evidence=task['course_evidence'], resource_count=len(task['resources']),
                steps=[{'agent':s['agent'],'status':s['status'],'backend':s.get('backend'),'model':s.get('model')}
                       for s in task['steps']], wall_ms=round((time.perf_counter()-started)*1000))
            assert task['status'] == 'completed', 'Resource model generation did not complete'
            assert task['backend'] != 'local_rules'
            assert task['course_evidence']['status'] == 'retrieved'
            if args.verify_admission:
                body={'knowledge_key':'loop-for','resource_types':['learning_bundle'],'force_regenerate':True,
                    'require_real_api':True,'idempotency_key':'real-admission-check'}
                from app.models.ai_runtime import AiModelCall
                with app.app_context():before=AiModelCall.query.count()
                repeated=requests.post(base+'/student/resource-generation/tasks',headers=headers,json=body,timeout=30)
                limited=requests.post(base+'/student/resource-generation/tasks',headers=headers,json={**body,'idempotency_key':'new-over-limit'},timeout=30)
                quota=requests.get(base+'/student/resource-generation/usage',headers=headers,timeout=20)
                assert repeated.status_code==201 and repeated.json()['data']['task_id']==task['task_id']
                assert limited.status_code==429 and quota.status_code==200
                assert quota.json()['data']['requests_used']==1 and quota.json()['data']['requests_remaining']==0
                with app.app_context():assert AiModelCall.query.count()==before and ResourceGenerationTask.query.count()==1
                evidence['admission']={'replay_same_task':True,'replay_no_model_calls':True,'new_request_status':429,'quota':quota.json()['data']}
            if args.verify_accounting:
                from app.models.ai_runtime import AiModelCall
                from app.services.model_accounting import summary
                rag = requests.post(base+'/rag/query',headers=teacher_headers,json={
                    'query':'for循环的 range(1,4) 为什么不包含停止值，如何用追踪表核对循环边界？',
                    'context':{'concept_hint':'loop-for'}},timeout=100)
                assert rag.status_code==200, f'RAG status {rag.status_code}'
                rag_data=rag.json()['data']
                with app.app_context():
                    calls=AiModelCall.query.order_by(AiModelCall.started_at).all()
                    resource_calls=[r for r in calls if r.workflow=='resource']
                    rag_calls=[r for r in calls if r.workflow=='rag']
                    evidence['accounting_diagnostic']={'resource_calls':len(resource_calls),'rag_calls':len(rag_calls),
                        'rag':{key:rag_data.get(key) for key in ('generation_mode','status','request_id','knowledge_grounded')},
                        'calls':[{key:getattr(r,key) for key in ('workflow','stage','status','error_code','model','total_tokens')} for r in calls]}
                    assert resource_calls and rag_calls, 'Both workflows must perform a real model call'
                    assert all(r.user_id==student_id and r.class_id==class_id and r.request_id==task['task_id'] for r in resource_calls)
                    assert all(r.user_id==teacher_id and r.class_id is None and r.request_id==rag_data['request_id'] for r in rag_calls)
                    assert all(r.finished_at and len(r.prompt_hash)==64 for r in calls)
                    assert any(r.total_tokens is not None and r.status=='succeeded' for r in resource_calls)
                    assert any(r.total_tokens is not None and r.status=='succeeded' for r in rag_calls)
                    evidence['model_accounting']={
                        'calls':[{key:getattr(r,key) for key in ('workflow','stage','provider','model','status','error_code','prompt_tokens','completion_tokens','total_tokens','elapsed_ms')} for r in calls],
                        'student':summary(student_id),'teacher':summary(teacher_id),'class':summary(teacher_id,class_id=class_id),
                        'rag_generation_mode':rag_data['generation_mode']}
                own=requests.get(base+'/ai/usage',headers=headers,timeout=20)
                cohort=requests.get(base+f'/teacher/classes/{class_id}/ai-usage',headers=teacher_headers,timeout=20)
                denied=requests.get(base+f'/teacher/classes/{class_id}/ai-usage',headers=headers,timeout=20)
                assert own.status_code==cohort.status_code==200 and denied.status_code==403
                assert own.json()['data']['totals']==evidence['model_accounting']['student']['totals']
                assert cohort.json()['data']['totals']==evidence['model_accounting']['class']['totals']
                evidence['model_accounting']['http_acl_checked']=True
            with app.app_context():
                row = ResourceGenerationTask.query.filter_by(task_id=task['task_id']).one()
                assert any(s['document_id'] == document_id for s in row.evidence_manifest['sources'])
                KnowledgeDocument.query.filter_by(id=document_id).update({'published':False}); db.session.commit()
            revoked = requests.get(base+'/student/resource-generation/tasks/'+task['task_id'],headers=headers,timeout=30).json()['data']
            evidence['revoked_status'] = revoked['course_evidence']['status']
            evidence['revoked_payload_hidden'] = not revoked['resources'] and not revoked['steps'] and revoked['audit_report'] is None
            assert evidence['revoked_status']=='unavailable' and evidence['revoked_payload_hidden']
        finally:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(json.dumps(evidence,ensure_ascii=False,indent=2).encode())
            server.shutdown(); thread.join(timeout=10)
            with app.app_context(): db.session.remove(); db.engine.dispose()
        print(json.dumps({'status':'passed','backend':evidence['backend'],'sources':evidence['course_evidence']['source_count'],
                          'revocation_checked':evidence['revoked_payload_hidden']}))


if __name__ == '__main__':
    main()
