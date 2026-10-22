"""Disposable SQLite acceptance with the real Docker grader; no live student writes."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import TestingConfig
from app import create_app
from app.models import db, User, Problem
from app.services.student_practice import MockExams


def main():
    with tempfile.TemporaryDirectory(prefix='plex-exam-') as directory:
        TestingConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///' + str(Path(directory) / 'acceptance.db')
        TestingConfig.SQLALCHEMY_ECHO = False
        TestingConfig.CODE_EXECUTION_BACKEND = 'docker'
        app = create_app('testing')
        with app.app_context():
            uid = User.query.filter_by(username='student001').one().id
            for i in range(6):
                db.session.add(Problem(id=98000+i, problem_no=f'SMOKE{i}', title_cn=f'隔离验收 {i}',
                    kg_node_id='loop-for', question_type='coding', is_active=True, needs_review=False,
                    source_kind='manual', description_cn='输出 1', run_mode='stdout',
                    test_cases_json=[{'id':'one', 'input':'', 'expected':'1', 'hidden':True}]))
            db.session.commit()
            exam = MockExams.create(uid, {'knowledge_keys':['loop-for']})
            answers = {q['id']: 'print(1)' for q in exam['questions']}
            MockExams.save(uid, exam['id'], {'revision':0, 'answers':answers})
            db.session.remove()
            assert MockExams.view(uid, exam['id'])['answers'] == answers
            MockExams.lock(uid, exam['id'])
            MockExams.grade(exam['id'])
            result = MockExams.view(uid, exam['id'])
            assert result['status'] == 'completed' and result['score'] == 100
            assert all(r['backend'] == 'docker' for r in result['results'].values())
            report = {'passed':True, 'database':'temporary SQLite', 'backend':'docker',
                      'questions':len(result['questions']), 'score':result['score'],
                      'draft_restored':True, 'status':result['status']}
            db.session.remove(); db.engine.dispose()
        output = Path(__file__).resolve().parents[2] / 'output/student-experience-real-grading.json'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report))


if __name__ == '__main__':
    main()
