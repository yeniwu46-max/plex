"""Serve an isolated, clearly synthetic database for PLEX browser acceptance."""
import argparse
from datetime import timedelta
import json
import os
from pathlib import Path
import secrets
import sqlite3
import sys
from threading import Event, Thread
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--port', type=int, default=5101)
    parser.add_argument('--real-model', action='store_true')
    parser.add_argument('--resume', action='store_true', help="Resume only this script's marked synthetic database, without reseeding.")
    args = parser.parse_args()
    folder = args.directory.resolve()
    database = folder / 'browser-acceptance.db'
    resumed = None
    if args.resume:
        resumed = json.loads((folder / 'ready.json').read_text(encoding='utf-8'))
        if (resumed.get('environment') != 'synthetic-browser-acceptance'
                or Path(resumed.get('database', '')).resolve() != database
                or not database.is_file()):
            parser.error('--resume requires the original marked synthetic database')
        backup = folder / ('before-resume-' + uuid.uuid4().hex + '.sqlite')
        with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as source:
            with sqlite3.connect(backup) as target:
                source.backup(target)
    else:
        folder.mkdir(parents=True, exist_ok=False)
    os.environ.update(EMBEDDING_PROVIDER='local', VECTOR_BACKEND='local',
                      VECTOR_STORE_PATH=str(folder / 'vectors'), AGENT_BACKEND='mock')
    from flask_jwt_extended import create_access_token
    from werkzeug.serving import make_server
    from app import create_app
    from app.config import TestingConfig
    from app.models import db, User, Class, Trial, TrialQuestion
    from app.services.learner_state import LearnerStateService
    from app.services.assignment import AssignmentService
    from app.services.knowledge import KnowledgeService
    from app.services.knowledge.index_service import IndexService
    from app.services.knowledge.access_service import KnowledgeAccessService
    from app.utils.time import utc_now
    from scripts.check_counterexample_sandbox import fixtures

    TestingConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///' + database.as_posix()
    TestingConfig.SQLALCHEMY_ECHO = False
    TestingConfig.JWT_SECRET_KEY = secrets.token_hex(32)
    TestingConfig.SECRET_KEY = secrets.token_hex(32)
    app = create_app('testing')
    app.instance_path = str(folder / 'instance')
    app.config.update(CODE_EXECUTION_BACKEND='docker', CODE_TRACE_ENABLED=True, RESOURCE_TASK_SYNC=False,
        TUTOR_MODELS_ENABLED=False, LLM_ALLOW_IN_TESTS=False, LEARNER_STATE_READ_MODE='evidence',
        COUNTEREXAMPLE_GENERATION_WORKER_ENABLED=False, TUTOR_DAILY_REQUEST_LIMIT=4)

    @app.after_request
    def identify_fixture(response):
        response.headers['X-Plex-Environment'] = 'synthetic-browser-acceptance'
        return response

    if not args.resume:
        with app.app_context():
            assert Path(db.engine.url.database).resolve() == database
            student = User.query.filter_by(username='student001').one()
            teacher = User.query.filter_by(username='teacher001').one()
            student.real_name = '界面验收学生（合成）'
            teacher.real_name = '界面验收教师（合成）'
            cohort = Class(name='四模块界面验收班（合成）', teacher_id=teacher.id, grade_level=1)
            db.session.add(cohort); db.session.flush(); student.class_id = cohort.id
            trial = Trial(class_id=cohort.id, teacher_id=teacher.id, title='循环边界与迁移 · 界面验收',
                          status='running', starts_at=utc_now() - timedelta(minutes=2))
            db.session.add(trial); db.session.flush()
            question_ids = []
            for title, expected in [('循环求和：包括最后一个元素', '6'), ('重复练习：核对循环结束边界', '6'),
                                    ('独立探索：为循环建立逐行追踪表', '6')]:
                question = TrialQuestion(trial_id=trial.id, stem=title + '。读取一行整数，输出所有整数的和。',
                    question_type='coding', options=[], correct_index=0, knowledge_key='loop-for')
                question.set_coding_meta({'run_mode': 'stdout', 'test_cases': [{'id':'sum', 'input':'1 2 3', 'expected':expected}]})
                db.session.add(question); db.session.flush(); question_ids.append(question.id)
            db.session.commit()
            wrong = 'data = list(map(int, input().split()))\ntotal = 0\nfor i in range(len(data) - 1):\n    total += data[i]\nprint(total)'
            for qid in question_ids[:2]:
                result = AssignmentService.submit_code_answer(student.id, qid, wrong)
                assert result['code_passed'] is False and result['results'][0]['actual'] == '3'
            LearnerStateService.drain()
            KnowledgeService.ensure_ready(seed_graph=True, index_builtin=False)
            doc = IndexService.register_text(title='界面验收材料：for 循环边界', user_id=teacher.id,
                chapter='循环与序列', concept_hints=['loop-for'], auto_index=True,
                text='# for 循环与边界核对\n\nrange(start, stop) 包含 start，不包含 stop。列表的合法索引从 0 到长度减一。'
                     '例如 range(1, 4) 提供 1、2、3。先手工列出循环访问的索引，再核对是否处理最后一个元素。'
                     '空序列不会执行循环体，累加器应在循环前初始化。单元素输入适合检查末项遗漏。')
            assert doc.status == 'READY'
            KnowledgeAccessService.update(teacher.id, doc.id,
                {'visibility':'class', 'class_id':cohort.id, 'published':True})
            teacher_headers = {'Authorization':'Bearer '+create_access_token(identity=str(teacher.id))}
            student_id, teacher_id, class_id = student.id, teacher.id, cohort.id
            document_id = doc.id

        client = app.test_client()
        def seed(path, body):
            response = client.post('/api/v1'+path, headers=teacher_headers, json=body)
            assert response.status_code == 200, (path, response.status_code)
            return response.json['data']

        spec, candidate = next(fixtures()); spec.pop('contract_version')
        spec_row = seed('/teacher/counterexample-specifications',
            {'request_id':str(uuid.uuid4()), 'class_id':class_id, 'specification':spec})
        challenge = seed('/teacher/counterexample-challenges',
            {'request_id':str(uuid.uuid4()), 'spec_id':spec_row['id'], 'candidate':candidate})
        prefix = '/teacher/counterexample-challenges/'+challenge['id']
        validation = seed(prefix+'/validate', {'request_id':str(uuid.uuid4()), 'manifest_hash':challenge['manifest_hash']})
        assert validation['status'] == 'passed'
        seed(prefix+'/review', {'action':'publish', 'manifest_hash':challenge['manifest_hash'], 'validation_id':validation['id'],
            'note':'仅供独立浏览器环境，脚本模拟审核，不是真实教师结论。',
            'checks':{k:True for k in ('single_clear_bug','statement_consistent','explanation_correct','difficulty_appropriate')}})
    else:
        student_id, teacher_id, class_id = (resumed[key] for key in ('student_id', 'teacher_id', 'class_id'))
        question_ids, document_id = resumed['question_ids'], resumed['document_id']
        challenge = {'id': resumed['challenge_id']}
        with app.app_context():
            assert Path(db.engine.url.database).resolve() == database
            KnowledgeService.ensure_ready(seed_graph=False, index_builtin=False)
    app.config.update(TUTOR_MODELS_ENABLED=args.real_model, LLM_ALLOW_IN_TESTS=args.real_model)
    stopped = Event()
    def consume():
        while not stopped.wait(0.5):
            with app.app_context():
                try:
                    LearnerStateService.drain()
                finally:
                    db.session.remove()
    consumer = Thread(target=consume, daemon=True); consumer.start()
    server = make_server('127.0.0.1', args.port, app, threaded=True)
    ready = {'environment':'synthetic-browser-acceptance','port':args.port,'database':str(database),
             'student_id':student_id,'teacher_id':teacher_id,'class_id':class_id,'question_ids':question_ids,
             'document_id':document_id,'challenge_id':challenge['id'],'real_model_enabled':args.real_model,
             'main_database_modified':False,'trace_enabled_only_in_fixture':True,'resource_tasks_async':True}
    (folder/'ready.json').write_text(json.dumps(ready,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'ready':True,'port':args.port,'environment':ready['environment']}),flush=True)
    try:
        server.serve_forever()
    finally:
        stopped.set(); consumer.join(timeout=3); server.server_close()
        with app.app_context():
            db.session.remove(); db.engine.dispose()


if __name__ == '__main__':
    main()
