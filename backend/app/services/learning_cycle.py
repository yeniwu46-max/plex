"""Legacy code cycle: isolated self-test followed by the reviewed tutor.

Self-test success is not a grade, mastery update or proof of correctness.
"""
from copy import deepcopy

from app.services.code_execution import CodeExecutionService
from app.services.legacy_student_tutoring import prepare, feedback_view
from app.services.tutor_context import TutorContextService, TutorContextError
from app.services.tutoring import TutorService


def execute_self_test(user_id, context, specification):
    """Only TutorService invokes this after claiming an owner-scoped request."""
    result = CodeExecutionService.submit(specification['language'], context.code,
        specification['test_cases'], specification['run_mode'])
    reference = TutorContextService.record_run(user_id, context, result, kind='test_cases')
    # Persist bounded results for retry/recovery, never source code, stdin,
    # setup/invoke scripts, hidden tests or a host traceback.
    cases = []
    for item in result['results']:
        row = {key: item.get(key) for key in ('passed', 'status', 'time', 'memory')}
        row['truncated'] = False
        for key, limit in [('case_id', 80), ('label', 120), ('expected', 4096), ('actual', 4096), ('error', 1000)]:
            value = str(item.get(key) or '')
            row[key] = value[:limit]
            row['truncated'] |= len(value) > limit
        cases.append(row)
    return {**reference, 'all_passed': result['all_passed'], 'passed_count': result['passed_count'],
        'total': result['total'], 'backend': result.get('backend'), 'results': cases,
        'submitted_at': result.get('submitted_at'), 'evidence_scope': 'self_test'}


class LearningCycleService:
    @staticmethod
    def execute(user_id, payload):
        request = prepare(user_id, payload, 'code-learning-cycle',
            default_question='请结合本次自测检查我的代码思路，指出一个需要核对的地方。', mode='review_approach')
        if request.get('run_id'):
            raise TutorContextError('运行闭环会生成新运行记录；已有运行请使用四模式辅导入口')
        specification = {'language': payload.get('language', 'python'),
            'test_cases': deepcopy(payload.get('test_cases')), 'run_mode': payload.get('run_mode', 'stdout')}
        CodeExecutionService.validate_submission(specification['language'], request['code'],
            specification['test_cases'], specification['run_mode'])
        tutor = TutorService.ask(user_id, request, self_test=specification)
        result = feedback_view(tutor)
        execution = tutor['self_test_execution']
        decision = tutor['teaching_plan']['decision']
        concept = decision['concept_id']
        result.update(
            execution=execution, tutorResponse=tutor,
            learningProfile={'stateVersion': tutor['state_version'], 'focusConcept': concept,
                'explanationPreference': '', 'visualPreferenceConfirmed': None,
                'interventionPresentation': '已审核的文字反馈与课程引用',
                'loopMastery': 'unknown', 'loopMasteryScore': None,
                'evidence': ['当前代码与本人自测记录；没有据此更新正式掌握状态。']},
            learningPath={**result['recommendation'], 'nextKnowledgePoint': concept or '', 'reason': decision['reason']},
            resources={'executionDiagram': None, 'microFix': None, 'sources': tutor['citations'], 'backend': tutor['generation_mode']},
            tutor={'mode': 'reflection' if execution['all_passed'] else 'socratic',
                'question': tutor['follow_up'] or tutor['next_step'], 'nextAction': tutor['next_step']},
            knowledgeGraphUpdate={'nodeId': concept, 'nodeLabel': concept or '', 'status': 'unchanged',
                'action': 'unchanged', 'evidence': '自测不会修改成绩、掌握度或清除正式错题。'},
            learningReport={'headline': '本次代码自测与辅导报告',
                'outcome': 'self_test_passed' if execution['all_passed'] else 'self_test_mismatch',
                'evidenceScope': 'self_test', 'diagnosis': tutor['summary'],
                'nextActions': [tutor['next_step'], '有限自测通过不等于所有输入正确；正式提交后记录学习证据。'], 'riskTags': []},
            pipelineTrace=[{'agentId':'code_sandbox', 'name':'隔离自测', 'status':'success',
                'latencyMs':execution['latency_ms'], 'summary':'记录本次自测，不作为正式成绩。', 'backend':execution['backend']},
                {'agentId':'reviewed_tutor', 'name':'小 E 辅导与审核',
                 'status':'success' if tutor['status']=='ok' else 'fallback',
                 'latencyMs':tutor['timing']['tutoring_ms'], 'summary':tutor['evidence_notice'], 'backend':tutor['generation_mode']}],
            completedAt=result['completed_at'])
        return result
