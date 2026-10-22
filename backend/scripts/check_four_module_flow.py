"""Synthetic four-module HTTP acceptance with real Docker and a real tutor model.

Uses a disposable SQLite database. Teacher publication is explicitly simulated;
this is engineering integration evidence, never classroom or teacher review data.
"""
import argparse
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import time
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--real-model', action='store_true')
    args = parser.parse_args()
    if not args.real_model:
        parser.error('--real-model is required; only synthetic course/code data is sent.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Never replace earlier evidence, including a failed run.
    with args.output.open('x', encoding='utf-8') as handle:
        handle.write('{}\n')
    report = {'scenario': 'synthetic_four_module_http_docker_model', 'verified': False,
              'human_review': 'simulated_fixture_only', 'business_records_changed': False,
              'browser_verified': False, 'stages': [], 'model_calls': [], 'snapshots': []}
    started = time.perf_counter()

    def save():
        report['elapsed_seconds'] = round(time.perf_counter() - started, 3)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def stage(name, **data):
        report['stages'].append({'name': name, **data})
        save()
        print(json.dumps({'stage': name, 'completed': True}), flush=True)

    try:
        with TemporaryDirectory(prefix='plex-four-module-') as directory:
            folder = Path(directory).resolve()
            os.environ.update(EMBEDDING_PROVIDER='local', VECTOR_BACKEND='local',
                              VECTOR_STORE_PATH=str(folder / 'vectors'))
            import requests
            from flask_jwt_extended import create_access_token
            from werkzeug.serving import make_server
            from app import create_app
            from app.config import TestingConfig
            from app.models import db, User, Class, Trial, TrialQuestion, TrialQuestionProgress
            from app.models.learner_state import LearningEvent
            from app.services.learner_state import LearnerStateService as State
            from app.services.learning_path import LearningPathService
            from app.services.knowledge import KnowledgeService
            from app.services.knowledge.index_service import IndexService
            from app.services.knowledge.access_service import KnowledgeAccessService
            from app.services.knowledge.learner_context_service import LearnerContextService
            from app.services.knowledge.providers.llm import get_llm_provider, LLMProvider
            from app.utils.time import utc_now
            from scripts.check_counterexample_sandbox import fixtures

            TestingConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///' + (folder / 'flow.db').as_posix()
            TestingConfig.SQLALCHEMY_ECHO = False
            app = create_app('testing')
            app.instance_path = str(folder / 'instance')
            app.config.update(CODE_EXECUTION_BACKEND='docker', LEARNER_STATE_READ_MODE='evidence',
                              TUTOR_MODELS_ENABLED=False, LLM_ALLOW_IN_TESTS=False)
            with app.app_context():
                assert Path(db.engine.url.database).resolve() == folder / 'flow.db'
                teacher = User.query.filter_by(username='teacher001').one()
                student = User.query.filter_by(username='student001').one()
                cohort = Class(name='四模块工程联调（合成）', teacher_id=teacher.id, grade_level=1)
                db.session.add(cohort); db.session.flush(); student.class_id = cohort.id
                trial = Trial(class_id=cohort.id, teacher_id=teacher.id, title='边界迁移合成验收',
                              status='running', starts_at=utc_now() - timedelta(minutes=2))
                db.session.add(trial); db.session.flush()
                tasks = [
                    ('读取一行整数，输出所有数的和。', [('1 2 3', '6'), ('7', '7')]),
                    ('读取一行整数，输出正数的个数。', [('1 -2 3', '2'), ('4', '1')]),
                    ('读取一行整数，第 i 个数的权重为 i（从 1 开始），输出加权和。', [('2 3', '8'), ('5', '5')]),
                ]
                question_ids = []
                for title, tests in tasks:
                    q = TrialQuestion(trial_id=trial.id, stem=title, question_type='coding',
                                      knowledge_key='loop-for', options=[], correct_index=0)
                    q.set_coding_meta({'run_mode': 'stdout', 'test_cases': [
                        {'id': str(i), 'input': stdin, 'expected': expected}
                        for i, (stdin, expected) in enumerate(tests)]})
                    db.session.add(q); db.session.flush(); question_ids.append(q.id)
                    db.session.add(TrialQuestionProgress(user_id=student.id, question_id=q.id, status='pending'))
                db.session.commit()
                student_id, class_id = student.id, cohort.id
                headers = {role: {'Authorization': 'Bearer ' + create_access_token(identity=str(user.id))}
                           for role, user in [('student', student), ('teacher', teacher)]}
                KnowledgeService.ensure_ready(seed_graph=True, index_builtin=False)
                document = IndexService.register_text(title='循环边界：合成课程验收材料', user_id=teacher.id,
                    chapter='for 循环', concept_hints=['loop-for'], auto_index=True, text=(
                        '# for 循环与边界核对\n\nrange(start, stop) 包含 start，不包含 stop。'
                        '列表的合法索引从 0 到长度减一，使用循环时应逐个核对会访问哪些索引。'
                        '例如 range(1, 4) 生成 1、2、3。检查程序可先手工列出索引，再比较题意是否要求处理末项。'
                        '空序列不会进入循环体，累加器应在循环前初始化。单元素输入有助于检查末项是否遗漏。'))
                assert document.status == 'READY'
                document_id = document.id
                KnowledgeAccessService.update(teacher.id, document.id,
                    {'visibility': 'class', 'class_id': class_id, 'published': True})
                delegate = get_llm_provider()

            class ObservedProvider(LLMProvider):
                def available(self):
                    return delegate.available()

                def generate(self, **kwargs):
                    if len(report['model_calls']) >= 2:
                        raise RuntimeError('acceptance_model_call_limit')
                    entry = {'completed': False}
                    report['model_calls'].append(entry)
                    # Match the production structured-JSON provider exactly;
                    # formatting cleanup must not alter punctuation in code.
                    result = delegate.generate(**kwargs, preserve_text=True)
                    if result:
                        from agents.llm_client import _extract_json
                        entry.update(completed=True, provider=result.provider, model=result.model,
                                     token_usage=result.token_usage, response=_extract_json(result.text))
                    save()
                    return result

            server = make_server('127.0.0.1', 0, app, threaded=True)
            worker = Thread(target=server.serve_forever, daemon=True); worker.start()
            base = f'http://127.0.0.1:{server.server_port}/api/v1'

            def http(method, path, body=None, *, role='student', expected=200):
                response = requests.request(method, base + path, headers=headers[role], json=body, timeout=125)
                assert response.status_code == expected, (path, response.status_code, response.json().get('message'))
                return response.json().get('data')

            def snapshot(label):
                with app.app_context():
                    State.drain()
                current = http('GET', '/student/learner-state')
                report['snapshots'].append({'stage': label, 'state': current})
                save()
                return current

            def concept(state):
                return next(c for c in state['concepts'] if c['concept_id'] == 'loop-for')

            try:
                wrong_sum = 'data = list(map(int, input().split()))\ntotal = 0\nfor i in range(len(data) - 1):\n    total += data[i]\nprint(total)'
                wrong_count = 'data = list(map(int, input().split()))\ntotal = 0\nfor i in range(len(data) - 1):\n    if data[i] > 0:\n        total += 1\nprint(total)'
                report['formal_results'] = []
                for qid, code, expected_actual in zip(question_ids[:2], (wrong_sum, wrong_count), (['3', '0'], ['1', '0'])):
                    result = http('POST', f'/student/assignments/{qid}/code-submit', {'code': code})
                    report['formal_results'].append({'question_id': qid, 'code': code, 'result': result})
                    save()
                    assert result['code_passed'] is False
                    # Reject a fixture that fails only because input was missing
                    # or execution crashed: these must be actual boundary errors.
                    assert [r['actual'] for r in result['results']] == expected_actual
                    assert all(r['status']['id'] == 3 and not r['passed'] for r in result['results'])
                initial = snapshot('two_failed_formal_submissions')
                c0 = concept(initial)
                assert c0['independent_count'] == 2 and c0['independent_success'] == 0
                misconception = next(m for m in initial['misconceptions'] if m['kind'] == 'loop_end_excluded')
                assert misconception['status'] == 'candidate' and misconception['distinct_questions'] == 2
                with app.app_context():
                    grades = LearningEvent.query.filter_by(user_id=student_id, kind='submission_graded').all()
                    assert len(grades) == 2 and all(e.payload['backend'] == 'docker' for e in grades)
                    path = LearningPathService.plan(student_id, state_snapshot=initial)
                    learner = LearnerContextService.build(student_id, state_snapshot=initial)
                    assert path['learning_decision'] == learner.learning_decision
                    assert path['state_version'] == learner.state_version == initial['state_version']
                decision = path['learning_decision']
                assert decision['basis'] == 'repeated_candidate'
                assert all(decision[k]['state_version'] == initial['state_version'] for k in ('hint', 'next_exercise', 'review'))
                stage('formal_execution_and_shared_state', question_ids=question_ids[:2], decision=decision)

                prompt = {'request_id': str(uuid.uuid4()), 'mode': 'next_step', 'hint_level': 2,
                          'formal_question_id': question_ids[1], 'code': wrong_count,
                          'question': 'for循环 range 的停止边界怎样核对？'}
                # Verify the intended positive retrieval fixture before spending
                # model tokens. The earlier generic-query run remains separate
                # evidence of insufficient_evidence handling, not a quality score.
                with app.app_context():
                    preflight = KnowledgeService.prepare(prompt['question'], user_id=student_id, scene='trial',
                        context={'task_type': 'practice', 'concept_hint': 'loop-for'}, state_snapshot=initial)
                    report['retrieval_preflight'] = {'grounded': preflight.knowledge_grounded,
                        'blocked_reason': preflight.blocked_reason, 'confidence_level': preflight.confidence_level,
                        'confidence': preflight.confidence,
                        'concept_ids': preflight.retrieval.understanding.concept_ids,
                        'embedding': 'local_hash',
                        'chunks': [c.to_debug_dict() for c in preflight.chunks]}
                    save()
                    assert preflight.knowledge_grounded and not preflight.blocked_reason
                app.config.update(TUTOR_MODELS_ENABLED=True, LLM_ALLOW_IN_TESTS=True)
                try:
                    with patch('app.services.tutoring.get_llm_provider', return_value=ObservedProvider()):
                        answer = http('POST', '/student/tutor/ask', prompt)
                        report['tutor_response'] = answer; save()
                        assert answer['status'] == 'ok', answer['policy_result']
                        assert answer['generation_mode'] == 'llm_reviewed'
                        assert answer['state_version'] == initial['state_version']
                        assert answer['teaching_plan']['decision'] == decision
                        assert answer['evidence_status'] == 'grounded' and answer['citations']
                        for citation in answer['citations']:
                            assert citation['document_id'] == document_id
                            source_url = citation['url']
                            assert source_url.startswith('/api/v1/rag/sources/')
                            http('GET', source_url.removeprefix('/api/v1'))
                        assert http('POST', '/student/tutor/ask', prompt) == answer
                finally:
                    app.config.update(TUTOR_MODELS_ENABLED=False, LLM_ALLOW_IN_TESTS=False)
                assert len(report['model_calls']) == 2 and all(c['completed'] for c in report['model_calls'])
                receipt = answer['display_receipt_id']; assert receipt
                before_display = snapshot('answer_generated_not_displayed')
                assert concept(before_display)['hints_seen'] == 0
                # Simulates the UI acknowledgement; does not claim a human read the answer.
                display_path = f'/student/tutor-responses/{receipt}/displayed'
                assert http('POST', display_path) == http('POST', display_path)
                after_hint = snapshot('simulated_display_acknowledgement')
                assert concept(after_hint)['hints_seen'] == 1
                assert concept(after_hint)['estimate'] == c0['estimate']
                stage('retrieval_reviewed_tutor_and_receipt', receipt=receipt, request_id=prompt['request_id'])

                specification, candidate = next(fixtures()); specification.pop('contract_version')
                spec = http('POST', '/teacher/counterexample-specifications',
                    {'request_id': str(uuid.uuid4()), 'class_id': class_id, 'specification': specification}, role='teacher')
                challenge = http('POST', '/teacher/counterexample-challenges',
                    {'request_id': str(uuid.uuid4()), 'spec_id': spec['id'], 'candidate': candidate}, role='teacher')
                challenge_path = '/teacher/counterexample-challenges/' + challenge['id']
                validation = http('POST', challenge_path + '/validate',
                    {'request_id': str(uuid.uuid4()), 'manifest_hash': challenge['manifest_hash']}, role='teacher')
                assert validation['status'] == 'passed'
                http('POST', challenge_path + '/review', {'action': 'publish',
                    'manifest_hash': challenge['manifest_hash'], 'validation_id': validation['id'],
                    'note': '工程验收模拟审核；用户暂缓真实教师评审，不代表真人审阅。',
                    'checks': {k: True for k in ('single_clear_bug', 'statement_consistent', 'explanation_correct', 'difficulty_appropriate')}},
                    role='teacher')
                attempt_body = {'request_id': str(uuid.uuid4()), 'revision': challenge['current_revision'],
                    'version': challenge['manifest_hash'], 'input': [2, 3], 'expected_output': 5,
                    'explanation': '错误程序遗漏末项 3，只得到 2；所有元素相加应为 5。'}
                attempt_path = f'/student/counterexample-challenges/{challenge["id"]}/attempts'
                attempt = http('POST', attempt_path, attempt_body)
                assert attempt['status'] == 'complete' and attempt['counterexample_found'] and attempt['expected_output_correct']
                assert http('POST', attempt_path, attempt_body) == attempt
                assert http('GET', '/student/counterexample-attempts/' + attempt_body['request_id']) == attempt
                teacher_attempt = http('GET', '/teacher/counterexample-attempts/' + attempt_body['request_id'], role='teacher')
                assert all(r['backend'] == 'docker' for r in teacher_attempt['execution_report']['runtimes'])
                after_counterexample = snapshot('counterexample_with_idempotent_retry')
                c1 = concept(after_counterexample)
                assert c1['counterexample_count'] == c1['counterexample_success'] == 1
                assert c1['independent_count'] == 2 and c1['estimate'] == c0['estimate']
                assert c1['counterexample_review_due_at']
                stage('counterexample_and_followup_schedule', challenge_id=challenge['id'],
                      revision=challenge['current_revision'], validation_id=validation['id'],
                      attempt=attempt, runtimes=teacher_attempt['execution_report']['runtimes'])

                correct = 'data = list(map(int, input().split()))\ntotal = 0\nfor i in range(len(data)):\n    total += (i + 1) * data[i]\nprint(total)'
                independent = http('POST', f'/student/assignments/{question_ids[2]}/code-submit', {'code': correct})
                report['formal_results'].append({'question_id': question_ids[2], 'code': correct, 'result': independent})
                save()
                assert independent['code_passed'] is True
                assert [r['actual'] for r in independent['results']] == ['8', '5']
                final = snapshot('later_independent_formal_success')
                c2 = concept(final)
                assert c2['independent_count'] == 3 and c2['independent_success'] == 1
                assert c2['assisted_count'] == 0 and c2['counterexample_count'] == 1
                assert c2['counterexample_review_due_at'] is None
                assert initial['state_version'] < after_hint['state_version'] < after_counterexample['state_version'] < final['state_version']
                teacher_state = http('GET', f'/teacher/students/{student_id}/learner-state', role='teacher')
                assert teacher_state['state_version'] == final['state_version']
                evidence = http('GET', '/student/learning-evidence')
                report['student_evidence'] = evidence
                with app.app_context():
                    events = LearningEvent.query.filter_by(user_id=student_id).order_by(LearningEvent.id).all()
                    report['event_links'] = [{'id': e.id, 'kind': e.kind, 'source_type': e.source_type,
                        'source_id': e.source_id, 'source_version': e.source_version, 'status': e.status,
                        'payload': e.payload} for e in events]
                    final_grade = next(e for e in events if e.kind == 'submission_graded' and e.payload['question_id'] == question_ids[2])
                    assert final_grade.payload['assisted'] is False and final_grade.payload['backend'] == 'docker'
                stage('independent_transfer_and_teacher_traceability', question_id=question_ids[2])
                report['implementation_hashes'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in [Path(__file__), ROOT/'app/services/learner_state.py', ROOT/'app/services/tutoring.py',
                              ROOT/'app/services/counterexample_attempt.py', ROOT/'app/services/docker_execution.py']}
                report['verified'] = True
            finally:
                server.shutdown(); server.server_close(); worker.join(timeout=5)
                with app.app_context():
                    db.session.remove(); db.engine.dispose()
    except Exception as exc:
        report['verified'] = False
        report['failure'] = {'type': type(exc).__name__, 'message': str(exc)[:500]}
        raise
    finally:
        save()
        print(json.dumps({'verified': report['verified'], 'completed_stages': len(report['stages']),
                          'model_calls': len(report['model_calls'])}), flush=True)


if __name__ == '__main__':
    main()
