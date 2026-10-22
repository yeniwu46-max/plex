"""Real provider + Docker + HTTP in a disposable database; no business records."""
import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import requests
from flask_jwt_extended import create_access_token
from werkzeug.serving import make_server
from app import create_app
from app.config import TestingConfig
from app.models import db, User, Class
from app.services.counterexample_generation import run_once
from app.services.resource_executor import submit_resource_task
from scripts.check_counterexample_sandbox import fixtures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real-model', action='store_true')
    parser.add_argument('--properties', action='store_true', help='Confirm the sum fixture properties before generating.')
    parser.add_argument('--output', type=Path, default=ROOT.parent/'output/plex-p3-generation-live.json')
    args = parser.parse_args()
    if not args.real_model:
        parser.error('Pass --real-model to run the configured provider and record actual usage.')
    with TemporaryDirectory(prefix='plex-generation-') as temporary:
        TestingConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///' + (Path(temporary)/'acceptance.db').as_posix()
        TestingConfig.SQLALCHEMY_ECHO = False
        app = create_app('testing')
        app.config.update(CODE_EXECUTION_BACKEND='docker', TUTOR_MODELS_ENABLED=True, LLM_ALLOW_IN_TESTS=True)
        with app.app_context():
            teacher = User.query.filter_by(username='teacher001').one()
            student = User.query.filter_by(username='student001').one()
            cohort = Class(name='候选生成开发验收', teacher_id=teacher.id, grade_level=1)
            db.session.add(cohort); db.session.flush(); student.class_id = cohort.id; db.session.commit()
            class_id = cohort.id
            headers = {role: {'Authorization':'Bearer '+create_access_token(identity=str(user.id))}
                for role,user in [('teacher',teacher),('student',student)]}
        server = make_server('127.0.0.1', 0, app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        base = f'http://127.0.0.1:{server.server_port}/api/v1'
        def request(method, path, body=None, role='teacher', status=200):
            result = requests.request(method, base+path, json=body, headers=headers[role], timeout=30)
            assert result.status_code == status, (result.status_code, result.text[:200])
            return result.json()['data']
        started = time.perf_counter()
        try:
            spec, _ = next(fixtures()); spec.pop('contract_version')
            if args.properties:
                spec['verification']={'policy_version':'bounded-properties-v1','boundary_checks':True,
                    'properties':['permutation_invariant','append_zero_invariant','concatenation_additive'],
                    'rationale':'开发验收求和题：排列不变、追加零不变、重复拼接翻倍；不计为真实教师审阅。'}
            basis = request('POST','/teacher/counterexample-specifications',{
                'request_id':str(uuid.uuid4()),'class_id':class_id,'specification':spec})
            body = {'request_id':str(uuid.uuid4()),'spec_id':basis['id'],'bug_kind':'loop_boundary'}
            task = request('POST','/teacher/counterexample-generation-tasks',body)
            assert request('POST','/teacher/counterexample-generation-tasks',body)['id']==task['id']
            future = submit_resource_task(run_once,app)
            assert future.result(timeout=180)
            result = request('GET','/teacher/counterexample-generation-tasks/'+task['id'])
            detail = request('GET','/teacher/counterexample-challenges/'+task['challenge_id']) if result['version_id'] else None
            evidence = {'synthetic_fixture':True, 'human_teacher_review':False, 'task':result,'candidate':detail,
                'wall_ms':round((time.perf_counter()-started)*1000)}
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(json.dumps(evidence,ensure_ascii=False,indent=2).encode('utf-8'))
            assert result['status']=='ready', (result['status'],result['error_code'])
            assert detail and detail['published_revision'] is None and detail['validation']['status']=='passed'
            if args.properties:
                assert detail['validation']['report']['coverage']['properties']
                assert detail['specification']['contract_version']=='counterexample-v2'
            request('GET','/student/counterexample-challenges/'+task['challenge_id'],role='student',status=404)
            request('POST','/teacher/counterexample-challenges/'+task['challenge_id']+'/review',{
                'action':'publish','manifest_hash':detail['manifest_hash'],'validation_id':result['validation_id'],
                'note':'开发脚本模拟教师审核，仅检查发布门槛，不计入真实教师审阅题库。',
                'checks':{key:True for key in ('single_clear_bug','statement_consistent','explanation_correct','difficulty_appropriate')}})
            public = request('GET','/student/counterexample-challenges/'+task['challenge_id'],role='student')
            assert 'fixed_code' not in public and 'generation' not in public
            evidence.update(publication_gate_verified=True, student_view_strips_private_data=True)
            args.output.write_bytes(json.dumps(evidence,ensure_ascii=False,indent=2).encode('utf-8'))
            print(json.dumps({'status':result['status'],'calls':[{
                'stage':call['stage'],'provider':call['audit']['provider'],'model':call['audit']['model'],
                'usage':call['audit']['token_usage'],'elapsed_ms':call['audit']['elapsed_ms']} for call in result['calls']],
                'validation':detail['validation']['status'],'wall_ms':evidence['wall_ms']},ensure_ascii=False))
        finally:
            server.shutdown(); thread.join(timeout=5)
            with app.app_context(): db.session.remove(); db.engine.dispose()


if __name__ == '__main__':
    main()
