"""学习评估报告 API 测试"""
import unittest
from datetime import timedelta

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import (
    Class,
    ResourceGenerationTask,
    Role,
    Trial,
    TrialParticipation,
    TrialQuestion,
    TrialQuestionProgress,
    User,
    db,
)
from app.utils.time import utc_now


class EvaluationTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            student_role = Role.query.filter_by(name='student').first()
            teacher = User.query.filter_by(username='teacher001').first()
            self.student = User(
                username='eval-student',
                email='eval@example.com',
                password_hash=generate_password_hash('student123'),
                real_name='评估学生',
                role_id=student_role.id,
            )
            db.session.add(self.student)
            db.session.flush()
            cls = Class(name='评估班', description='e', grade_level=1, teacher_id=teacher.id)
            db.session.add(cls)
            db.session.flush()
            self.student.class_id = cls.id
            self.class_id = cls.id
            trial = Trial(
                class_id=cls.id,
                teacher_id=teacher.id,
                title='评估试炼',
                trial_type='solo',
                knowledge_key='algo',
                status='ended',
            )
            db.session.add(trial)
            db.session.flush()
            db.session.add(
                TrialParticipation(
                    trial_id=trial.id,
                    user_id=self.student.id,
                    status='completed',
                    score=80,
                )
            )
            db.session.commit()
            self.student_token = create_access_token(identity=str(self.student.id))
            self.teacher_token = create_access_token(identity=str(teacher.id))
            self.student_id = self.student.id

    def auth(self, token):
        return {'Authorization': f'Bearer {token}'}

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_student_learning_report(self):
        resp = self.client.get(
            '/api/v1/student/learning-report?period=7d',
            headers=self.auth(self.student_token),
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()['data']
        self.assertIn('summary', body)
        self.assertIn('domain_mastery', body)
        self.assertIn('recommendations', body)

    def test_teacher_class_evaluation(self):
        resp = self.client.get(
            f'/api/v1/teacher/class-evaluation?class_id={self.class_id}&period=7d',
            headers=self.auth(self.teacher_token),
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()['data']
        self.assertEqual(body['class_id'], self.class_id)
        self.assertIn('students', body)

    def _create_effect_evidence(self, before_count=3, after_count=3):
        with self.app.app_context():
            trial = Trial.query.filter_by(class_id=self.class_id).first()
            intervention_at = utc_now()
            task = ResourceGenerationTask(
                task_id=f'effect-{before_count}-{after_count}',
                user_id=self.student_id,
                knowledge_key='loop',
                requested_types=['lesson_document', 'exercise_set'],
                status='completed',
                progress=100,
                profile_version=2,
                backend='local_rules',
                completed_at=intervention_at + timedelta(seconds=1),
            )
            task.created_at = intervention_at
            db.session.add(task)
            db.session.flush()
            for index in range(before_count + after_count):
                question = TrialQuestion(
                    trial_id=trial.id,
                    sort_order=index,
                    stem=f'loop effect {index}',
                    options=['A', 'B'],
                    correct_index=0,
                    knowledge_key='loop',
                )
                db.session.add(question)
                db.session.flush()
                is_after = index >= before_count
                db.session.add(
                    TrialQuestionProgress(
                        user_id=self.student_id,
                        question_id=question.id,
                        status='completed',
                        selected_index=0 if is_after else 1,
                        is_correct=is_after,
                        answered_at=intervention_at
                        + (timedelta(minutes=index + 1) if is_after else -timedelta(minutes=index + 1)),
                    )
                )
            db.session.commit()
            return task.task_id

    def test_learning_effect_is_identical_for_student_and_teacher(self):
        task_id = self._create_effect_evidence()
        student_resp = self.client.get(
            f'/api/v1/student/learning-effect?task_id={task_id}',
            headers=self.auth(self.student_token),
        )
        teacher_resp = self.client.get(
            f'/api/v1/teacher/students/{self.student_id}/learning-effect?task_id={task_id}',
            headers=self.auth(self.teacher_token),
        )
        self.assertEqual(student_resp.status_code, 200)
        self.assertEqual(teacher_resp.status_code, 200)
        student_data = student_resp.get_json()['data']
        teacher_data = teacher_resp.get_json()['data']
        self.assertEqual(student_data['status'], 'sufficient')
        self.assertEqual(student_data['before']['correct_rate'], 0.0)
        self.assertEqual(student_data['after']['correct_rate'], 100.0)
        self.assertEqual(student_data['delta']['mistake_count'], -3)
        self.assertEqual(student_data, {k: v for k, v in teacher_data.items() if k != 'student'})

    def test_learning_effect_does_not_invent_improvement_for_small_sample(self):
        task_id = self._create_effect_evidence(before_count=1, after_count=1)
        resp = self.client.get(
            f'/api/v1/student/learning-effect?task_id={task_id}',
            headers=self.auth(self.student_token),
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()['data']
        self.assertEqual(data['status'], 'insufficient_evidence')
        self.assertIsNone(data['delta']['correct_rate'])
        self.assertIsNone(data['delta']['mastery_rate'])


if __name__ == '__main__':
    unittest.main()
