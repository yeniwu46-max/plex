"""Requirement-level audit for the iFlytek 990 submission; never infers external proof."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent


def load(relative: str):
    path = BACKEND_ROOT / relative
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None


def item(key, label, evidence, passed, external=False, note=''):
    return {
        'key': key,
        'label': label,
        'evidence': evidence,
        'status': 'verified_local' if passed else 'blocked_external' if external else 'missing',
        'passed': bool(passed),
        'note': note,
    }


def audit() -> dict:
    kg = load('reports/iflytek-990-kg-validation-20260828.json') or {}
    profile = load('reports/iflytek-990-profile-extraction-20260828.json') or {}
    intent = load('reports/iflytek-990-intent-dispatch-20260828.json') or {}
    agents = load('reports/iflytek-990-agent-orchestration-20260828.json') or {}
    hallucination = load('reports/iflytek-990-hallucination-local-20260828.json') or {}
    path = load('reports/iflytek-990-path-replanning-20260828.json') or {}
    demo = load('reports/iflytek-990-demo-rehearsal-20260828.json') or {}
    risk = load('reports/iflytek-990-risk-explainability-20260828.json') or {}
    live = load('reports/iflytek-990-live-20260828.json') or {}
    experiment = load('reports/iflytek-990-experiment-20260828.json') or {}
    voice = load('reports/iflytek-990-voice-20260828.json') or {}
    clean_environment = load('reports/a3-next-stage/clean-environment.json') or {}
    resource_service = (BACKEND_ROOT / 'app/services/personalized_resource.py').read_text(encoding='utf-8')
    mistake_service = (BACKEND_ROOT / 'app/services/mistake.py').read_text(encoding='utf-8')

    checks = [
        item('profile', '动态多维画像本地评测', 'reports/iflytek-990-profile-extraction-20260828.json', profile.get('case_count', 0) >= 50 and profile.get('summary', {}).get('exact_case_match_rate') == 1.0, note='真实学生画像仍待外部'),
        item('graph', '知识图谱节点与关系', 'reports/iflytek-990-kg-validation-20260828.json', kg.get('node_count', 0) >= 100 and kg.get('edge_count', 0) >= 200),
        item('agents', '多智能体编排契约', 'reports/iflytek-990-agent-orchestration-20260828.json', agents.get('status') == 'passed', note='真实星火后端仍待外部'),
        item('intent', '自然语言意图路由', 'reports/iflytek-990-intent-dispatch-20260828.json', intent.get('natural_language_cases', 0) >= 100 and intent.get('natural_language_accuracy', intent.get('natural_language_classifier_accuracy', 0)) >= 0.9, note='真实学生语料仍待外部'),
        item('grounding', 'RAG/图谱本地幻觉防线', 'reports/iflytek-990-hallucination-local-20260828.json', hallucination.get('sample_count', 0) >= 100 and hallucination.get('clean_hallucination_rate') <= 0.05),
        item('resources', '不少于五类个性化资源', 'app/services/personalized_resource.py', all(name in resource_service for name in ('lesson_document', 'mind_map', 'exercise_set', 'coding_lab', 'extended_reading'))),
        item('replanning', '错题复习触发路径重规划', 'reports/iflytek-990-path-replanning-20260828.json', path.get('passed') is True),
        item('sm2', 'SM-2 错题复习调度', 'app/services/mistake.py', 'SM-2' in mistake_service and path.get('checks', {}).get('sm2_review_saved') is True),
        item('demo', '本地全流程彩排', 'reports/iflytek-990-demo-rehearsal-20260828.json', demo.get('passed') is True),
        item('risk', '风险解释契约', 'reports/iflytek-990-risk-explainability-20260828.json', risk.get('status') == 'passed', note='确定性贡献不冒充 SHAP'),
        item('teacher_dashboard', '教师风险看板与干预完成率', 'frontend/src/views/TeacherHomeView.vue', 'intervention_completion_rate' in (REPO_ROOT / 'frontend/src/views/TeacherHomeView.vue').read_text(encoding='utf-8') and 'intervention_completion_rate' in (BACKEND_ROOT / 'app/services/teacher.py').read_text(encoding='utf-8'), note='浏览器录屏仍待外部'),
        item('spark_live', '真实讯飞 Spark 100 条调用', 'reports/iflytek-990-live-20260828.json', live.get('status') == 'completed' and live.get('success_count') >= 100, external=True, note='当前 not_configured'),
        item('voice', '完整 ASR/LLM/TTS/数字人 30 轮', 'reports/iflytek-990-voice-20260828.json', voice.get('status') == 'passed' and voice.get('rounds_completed', 0) >= 30, external=True, note='当前仅本地 TTS 部分'),
        item('experiment', '真实教学实验 ≥100 人次', 'reports/iflytek-990-experiment-20260828.json', experiment.get('status') == 'ready' and experiment.get('participant_count', 0) >= 100, external=True, note='当前 0 人次'),
        item('mysql8', 'MySQL 8 干净环境', 'reports/a3-next-stage/clean-environment.json', clean_environment.get('checks', {}).get('mysql_8', {}).get('passed') is True, external=True, note='需报告中明确 mysql_8=true'),
        item('pptx', '路演 PPTX', 'docs/submission/artifacts/PLEX-iflytek-990-defense.pptx', (REPO_ROOT / 'docs/submission/artifacts/PLEX-iflytek-990-defense.pptx').is_file()),
        item('mp4', '演示 MP4', 'docs/submission/artifacts/PLEX-A3-demo.mp4', (REPO_ROOT / 'docs/submission/artifacts/PLEX-A3-demo.mp4').is_file(), external=True, note='当前文件不存在'),
    ]
    local_items = [check for check in checks if check['status'] == 'verified_local']
    blocked = [check['key'] for check in checks if check['status'] == 'blocked_external']
    missing = [check['key'] for check in checks if check['status'] == 'missing']
    return {
        'benchmark': 'iflytek-990-requirement-level-audit',
        'run_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'local_passed': not missing,
        'submission_ready': not blocked and not missing,
        'verified_local_count': len(local_items),
        'blocked_external': blocked,
        'missing': missing,
        'checks': checks,
        'policy': 'external requirements require external evidence; local/mock reports never close them',
    }


def main():
    output = BACKEND_ROOT / 'reports/iflytek-990-completion-audit-20260828.json'
    result = audit()
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
