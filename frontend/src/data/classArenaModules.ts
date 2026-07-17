/** 探索舱 · 试炼场模块目录 */

export type ClassArenaModuleKey = 'student_duel' | 'mock_exam'

export interface ClassArenaModuleDef {
  key: ClassArenaModuleKey
  title: string
  subtitle: string
  description: string
  badge?: string
  status: 'live' | 'beta' | 'soon'
  tags: string[]
}

export const CLASS_ARENA_MODULES: ClassArenaModuleDef[] = [
  {
    key: 'student_duel',
    title: '学生对战',
    subtitle: 'Student vs Student',
    description: '随机 3 道编程题，ACM 赛制：先通过全部用例者获胜。',
    badge: 'ACM',
    status: 'live',
    tags: ['随机 3 题', '同班匹配', '先 AC 获胜'],
  },
  {
    key: 'mock_exam',
    title: '模拟考试',
    subtitle: 'Mock Exam',
    description: '6 道编程题套卷，限时完成并统计得分。',
    badge: '套卷',
    status: 'live',
    tags: ['6 题', '限时', '综合测评'],
  },
]

export const STUDENT_DUEL_PROBLEM_COUNT = 3
export const MOCK_EXAM_PROBLEM_COUNT = 6
export const MOCK_EXAM_TIME_SEC = 7200

export const MOCK_EXAM_RULES = [
  '共 6 道编程题，按顺序作答；每题需通过全部测试用例才算 AC。',
  '总时限 120 分钟，可在题目间切换，提交后不可修改该题代码。',
  '得分 = AC 题数 × 100 / 6。',
]
