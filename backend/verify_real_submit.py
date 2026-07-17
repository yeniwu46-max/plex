"""验证：学生端真实提交 API 写入的数据，教师端能读到；智能体编排 trace 非空。"""
import requests

BASE = 'http://127.0.0.1:5100/api/v1'


def login(username: str, password: str) -> str:
    r = requests.post(f'{BASE}/auth/login', json={'username': username, 'password': password}, timeout=5)
    r.raise_for_status()
    return r.json()['data']['access_token']


def main() -> None:
    admin_token = login('admin', 'admin123')
    ah = {'Authorization': f'Bearer {admin_token}'}
    orch = requests.get(f'{BASE}/admin/agent-orchestration', headers=ah, timeout=5).json()
    assert orch['code'] == 0, orch
    assert 'runtime' in orch['data'], 'agent-orchestration 应包含 runtime 块'
    print('编排配置：', orch['data']['config'])
    print('运行态：', orch['data']['runtime'])

    teacher_token = login('teacher001', 'teacher123')
    th = {'Authorization': f'Bearer {teacher_token}'}

    board = requests.get(f'{BASE}/teacher/classes/1/trial-answers', headers=th, timeout=5).json()['data']
    before = sum(1 for t in board['trials'] for s in t['students'] if s['answered_count'] > 0)
    print(f'提交前：有作答记录的学生数 = {before}')

    student_token = login('student001', 'student123')
    sh = {'Authorization': f'Bearer {student_token}'}

    trials = requests.get(f'{BASE}/student/trials', headers=sh, timeout=5).json()['data']['trials']
    running = next((t for t in trials if t.get('status') == 'running'), trials[0] if trials else None)
    if not running:
        print('无可用试炼')
        return

    trial_id = running['id']
    questions = requests.get(f'{BASE}/student/trials/{trial_id}/questions', headers=sh, timeout=5).json()['data']['items']
    pending = next((q for q in questions if q.get('status') != 'completed'), None)
    if not pending:
        print('试炼无待作答题')
        return

    q = pending
    payload = {'selected_index': 0, 'time_spent_sec': 42}
    sub = requests.post(f'{BASE}/student/assignments/{q["id"]}/answer', headers=sh, json=payload, timeout=30).json()
    print(f'学生提交：题目 {q["id"]} → code={sub["code"]} correct={sub["data"]["correct"]} at={sub["data"]["answered_at"]}')
    agent_trace = sub['data'].get('agent_trace') or {}
    print(f'智能体 trace：count={agent_trace.get("count", 0)} has_error={agent_trace.get("has_error")}')
    assert agent_trace.get('count', 0) > 0, '提交后 agent_trace 应为非空（请确认管理端已启用编排）'
    if agent_trace.get('items'):
        print('  摘要：', agent_trace['items'][0].get('summary', ''))

    board2 = requests.get(f'{BASE}/teacher/classes/1/trial-answers', headers=th, timeout=5).json()['data']
    for item in board2['trials']:
        for s in item['students']:
            if s['username'] == 'student001' and s['answered_count'] > 0:
                ans = next(x for x in s['answers'] if x['status'] == 'completed' and x['question_id'] == q['id'])
                print(
                    '教师端读到：',
                    s['real_name'],
                    item['trial']['title'],
                    f"选 {ans.get('selected_label', '—')}",
                    '对' if ans['is_correct'] else '错',
                    f"{ans['time_spent_sec']}s",
                    ans['answered_at'],
                )
                trace_len = len(ans.get('agent_trace') or [])
                print(f'  智能体记录：{trace_len} 条')
                assert trace_len > 0, '教师端应读到 agent_trace'


if __name__ == '__main__':
    main()
