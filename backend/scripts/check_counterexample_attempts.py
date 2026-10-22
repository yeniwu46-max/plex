"""Real HTTP/Docker acceptance in a disposable SQLite database, never business data."""
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
from app.services.learner_state import LearnerStateService
from scripts.check_counterexample_sandbox import fixtures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT.parent/'output/plex-p3-attempts-live.json')
    parser.add_argument('--real-model', action='store_true', help='Use the configured model for explanation review.')
    args = parser.parse_args()
    with TemporaryDirectory(prefix='plex-counterexample-') as temporary:
        TestingConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///' + (Path(temporary)/'acceptance.db').as_posix()
        TestingConfig.SQLALCHEMY_ECHO = False
        app = create_app('testing')
        app.config.update(CODE_EXECUTION_BACKEND='docker', TUTOR_MODELS_ENABLED=args.real_model, LLM_ALLOW_IN_TESTS=args.real_model)
        with app.app_context():
            teacher = User.query.filter_by(username='teacher001').one()
            student = User.query.filter_by(username='student001').one()
            cohort = Class(name='反例开发验收（合成数据）', teacher_id=teacher.id, grade_level=1)
            db.session.add(cohort); db.session.flush(); student.class_id = cohort.id; db.session.commit()
            student_id, class_id = student.id, cohort.id
            headers = {role: {'Authorization': 'Bearer '+create_access_token(identity=str(user.id))}
                for role, user in [('teacher', teacher), ('student', student)]}
        server = make_server('127.0.0.1', 0, app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        base = f'http://127.0.0.1:{server.server_port}/api/v1'
        def request(method, path, role, body=None, status=200):
            response = requests.request(method, base+path, headers=headers[role], json=body, timeout=125)
            assert response.status_code == status, (response.status_code, response.text[:300])
            return response.json()['data']
        def publish(candidate_override=None):
            specification, candidate = next(fixtures()); specification.pop('contract_version')
            candidate.update(candidate_override or {})
            spec = request('POST', '/teacher/counterexample-specifications', 'teacher',
                {'request_id': str(uuid.uuid4()), 'class_id': class_id, 'specification': specification})
            saved_spec = request('GET', '/teacher/counterexample-specifications/'+spec['id'], 'teacher')
            assert saved_spec['specification']['reference_code']==specification['reference_code']
            row = request('POST', '/teacher/counterexample-challenges', 'teacher',
                {'request_id': str(uuid.uuid4()), 'spec_id': spec['id'], 'candidate': candidate})
            path = '/teacher/counterexample-challenges/'+row['id']
            report = request('POST', path+'/validate', 'teacher',
                {'request_id': str(uuid.uuid4()), 'manifest_hash': row['manifest_hash']})
            assert report['status'] == 'passed', report
            request('POST', path+'/review', 'teacher', {'action': 'publish', 'manifest_hash': row['manifest_hash'],
                'validation_id': report['id'], 'note': '开发验收脚本模拟审核，不代表真实教师审阅。',
                'checks': {k: True for k in ('single_clear_bug','statement_consistent','explanation_correct','difficulty_appropriate')}})
            teacher_list=request('GET', '/teacher/counterexample-challenges?class_id='+str(class_id), 'teacher')
            assert row['id'] in [item['id'] for item in teacher_list['items']]
            return row
        try:
            row = publish()
            body = {'request_id': str(uuid.uuid4()), 'revision': row['current_revision'], 'version': row['manifest_hash'],
                'input': [2,3], 'expected_output': 5, 'explanation': '切片 data[:-1] 遗漏最后一个元素，所以输入 [2,3] 实际只加了 2，正确应是 2+3=5。'}
            path = '/student/counterexample-challenges/'+row['id']+'/attempts'
            started = time.perf_counter()
            result = request('POST', path, 'student', body)
            assert result['status']=='complete' and result['counterexample_found'] and result['expected_output_correct']
            assert result['buggy_result']=={'kind':'value','value':2} and result['correct_result']=={'kind':'value','value':5}
            assert request('POST', path, 'student', body)==result
            record_path='/student/counterexample-attempts/'+body['request_id']
            assert request('GET', record_path, 'student')==result
            assert request('GET', path, 'student')['items'][0]['request_id']==body['request_id']
            teacher_record=request('GET', '/teacher/counterexample-attempts/'+body['request_id'], 'teacher')
            teacher_history=request('GET', '/teacher/counterexample-challenges/'+row['id']+'/attempts','teacher')
            assert teacher_history['items'][0]['request_id']==body['request_id']
            assert teacher_record['task_snapshot']['buggy_code']==row['candidate']['buggy_code']
            audit=teacher_record['execution_report']['initial_explanation_review']
            if args.real_model:
                assert audit['provider'] and audit['model'], 'Model did not produce a recorded response'
            review_body={'request_id':str(uuid.uuid4()),'expected_revision':0,'verdict':'supported',
                'note':'开发验收模拟教师：说明已联系末尾元素与这次输出差异。'}
            review_path='/teacher/counterexample-attempts/'+body['request_id']+'/review'
            reviewed=request('POST',review_path,'teacher',review_body)
            assert request('POST',review_path,'teacher',review_body)==reviewed
            assert reviewed['review_history'][0]['note']==review_body['note']
            restored=request('GET',record_path,'student')
            assert restored['explanation_review']['source']=='teacher' and restored['evidence_event_id']==result['evidence_event_id']
            for key in ('counterexample_found','expected_output_correct','correct_result','buggy_result'):
                assert restored[key]==result[key]
            request('POST','/teacher/counterexample-challenges/'+row['id']+'/versions','teacher',
                {'request_id':str(uuid.uuid4()),'expected_revision':1,'spec_id':row['spec_id'],
                    'candidate':{**row['candidate'],'explanation':'新的教学说明，不覆盖旧版本。'}})
            old=request('GET','/teacher/counterexample-challenges/'+row['id']+'/versions/1','teacher')
            assert old['revision']==1 and old['current_revision']==2 and old['candidate']==row['candidate']
            history=request('GET','/teacher/counterexample-challenges/'+row['id']+'/versions','teacher')
            assert [v['revision'] for v in history['items']]==[2,1]
            request('GET','/student/counterexample-challenges/'+row['id'],'student',status=404)
            # A new legal input exposes a defect missed by the finite baseline suite.
            defective=publish({'fixed_code':'def solve(data):\n    return 99 if len(data) == 3 else sum(data)'})
            issue=request('POST','/student/counterexample-challenges/'+defective['id']+'/attempts','student',
                {**body,'request_id':str(uuid.uuid4()),'version':defective['manifest_hash'],
                    'input':[1,2,3],'expected_output':6})
            assert issue['status']=='material_issue' and not issue['graded'] and 'correct_result' not in issue
            request('GET','/student/counterexample-challenges/'+defective['id'],'student',status=404)
            with app.app_context():
                LearnerStateService.drain()
                concept=LearnerStateService.snapshot(student_id)['concepts'][0]
                assert concept['counterexample_count']==concept['counterexample_success']==1
                assert concept['estimate'] is None and concept['independent_count']==0
            summary={'scenario':'synthetic_http_acceptance', 'counterexample_found':True, 'expected_output_correct':True,
                'retry_equal':True,'restored':True,'teacher_review_preserved_facts':True,'material_issue_withdrawn_ungraded':True,
                'teacher_list_and_spec_recovery':True,'teacher_attempt_list_and_review_history':True,'historical_version_frozen':True,
                'counterexample_count':concept['counterexample_count'],'ability_estimate':concept['estimate'],
                'explanation_review':audit,'runtimes':teacher_record['execution_report']['runtimes'],
                'execution_ms':result['execution_ms'],'total_observed_seconds':round(time.perf_counter()-started,3)}
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(json.dumps(summary,ensure_ascii=False,indent=2).encode('utf-8'))
            print(json.dumps(summary,ensure_ascii=False),flush=True)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)
            with app.app_context(): db.session.remove(); db.engine.dispose()


if __name__=='__main__':
    main()
