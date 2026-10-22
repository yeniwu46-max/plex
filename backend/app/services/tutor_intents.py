"""Bounded free-question routing and factual, owner-scoped learning queries."""
import re
from datetime import timedelta

from app.models import db, TrialQuestionProgress
from app.services.learner_decision import LearnerDecisionService
from app.utils.time import utc_now

AUTO_MODES = {'concept_explain', 'algorithm_validation', 'algorithm_trace', 'learning_overview', 'clarify'}


def infer_mode(question, code=''):
    # No model classifier/retry loop. Uncertain routing cannot relax task policy.
    text = question.strip()
    if re.search(r'薄弱|成长|近[期周]|最近.*学习|下一[道题]|推荐.*练|修复路线|学习路径|复习计划', text):
        return 'learning_overview'
    if re.search(r'伪代码', text):
        return 'pseudocode'
    if re.search(r'下一步|给.*提示|直接.*答案|完整.*答案|帮我写.*程序', text):
        return 'next_step'
    if re.search(r'推演|跟踪|每[轮步]|执行过程|运行过程|逐步.*执行|变量.*变化', text):
        return 'algorithm_trace'
    if re.search(r'验证|正确吗|可行吗|对不对|复杂度|检查.*思路|我的思路', text):
        return 'algorithm_validation'
    if re.search(r'什么是|是什么意思|含义|原理|用法|区别|举例|示例|定义|介绍', text):
        return 'concept_explain'
    if re.search(r'报错|异常|[A-Z]\w*Error\b', text):
        return 'explain_error'
    if code:
        return 'review_approach'
    if re.fullmatch(r'[你好您好小Ee，,！!。.\s]+|(?:我)?(?:不会|不懂|卡住了|帮帮我)[！!。.？?\s]*', text):
        return 'clarify'
    return 'concept_explain'


def learning_overview(user_id, snapshot, question, *, decision=None, allow_counterexample=True):
    """Summarize facts without asking a model to infer learning improvement."""
    now = utc_now()
    rows = TrialQuestionProgress.query.filter(
        TrialQuestionProgress.user_id == user_id, TrialQuestionProgress.status == 'completed',
        TrialQuestionProgress.answered_at >= now - timedelta(days=7),
        TrialQuestionProgress.answered_at <= now,
    ).all()
    decision = decision or LearnerDecisionService.from_snapshot(snapshot)
    if rows:
        correct = sum(bool(row.is_correct) for row in rows)
        summary = f'最近 7 天完成了 {len(rows)} 道正式题，其中 {correct} 道通过。'
    else:
        summary = '最近 7 天还没有已完成的正式作答记录，目前不能据此判断进步或薄弱程度。'
    summary += '\n' + decision['reason']
    next_action = decision['hint']['action']
    pick = counterexample_pick = None
    if re.search(r'下一[道题]|推荐.*练', question):
        from app.services.counterexample_recommendation import recommend
        counterexample_pick = recommend(user_id, decision) if allow_counterexample else None
        if counterexample_pick:
            next_action = '可以先尝试下方反例挑战，用一个合法输入核对边界。'
        else:
            from app.services.practice_question import PracticeQuestionService
            row = PracticeQuestionService.recommend_for_student(user_id, state_snapshot=snapshot)
            if row:
                pick = {k: row.get(k) for k in ('id', 'code', 'title', 'topic', 'knowledge_key')}
                pick.update(practice_path=f'/student/trials/practice/{row["id"]}', state_version=snapshot['state_version'])
                next_action = f'先独立尝试「{row["title"]}」，再核对自己的思路。'
            else:
                next_action = '当前没有可推荐的已开放题目，可以先到星轨查看课程知识点。'
    elif re.search(r'路线|路径|计划|复习', question):
        next_action = decision['review']['action']
        summary += '\n建议顺序：先核对当前条件，再做一道对应练习，最后记录需要复习的地方。'
    return {'counterexample_pick': counterexample_pick, 'summary': summary, 'next_step': next_action, 'follow_up': '', 'citations': [],
            'question_pick': pick, 'records_at': now.isoformat() + 'Z'}
