import type { PythonTrialQuestion } from './pythonTrialQuestions'
import { getPythonTrialQuestion } from './pythonTrialQuestions'

export interface MockExamSet {
  id: string
  title: string
  subtitle: string
  description: string
  difficulty: '基础' | '进阶' | '挑战'
  questionIds: string[]
}

export const MOCK_EXAM_SETS: MockExamSet[] = [
  {
    id: 'set-a',
    title: '套卷 A · 语法基础',
    subtitle: 'Syntax Foundations',
    description: '变量、分支与循环的综合运用，适合巩固 Python 入门语法。',
    difficulty: '基础',
    questionIds: [
      'if-parity',
      'for-sum',
      'if-max-two',
      'for-count-evens',
      'list-max',
      'capstone-positive-count',
    ],
  },
  {
    id: 'set-b',
    title: '套卷 B · 逻辑进阶',
    subtitle: 'Logic & Loops',
    description: '多分支判断、循环控制与列表操作，难度适中。',
    difficulty: '进阶',
    questionIds: [
      'if-sign',
      'for-mult-table',
      'for-factorial',
      'list-sum-loop',
      'list-ends',
      'capstone-range-sum',
    ],
  },
  {
    id: 'set-c',
    title: '套卷 C · 函数综合',
    subtitle: 'Functions & Algorithms',
    description: '函数封装与简单算法思维，适合模拟考试冲刺。',
    difficulty: '挑战',
    questionIds: [
      'def-rect-area',
      'def-max-two',
      'list-total',
      'algo-bubble-sort',
      'algo-binary-search',
      'capstone-fizz',
    ],
  },
]

function resolveQuestions(ids: string[]): PythonTrialQuestion[] {
  return ids
    .map((id) => getPythonTrialQuestion(id))
    .filter((item): item is PythonTrialQuestion => item !== null)
}

export function getMockExamSet(setId: string): MockExamSet | undefined {
  return MOCK_EXAM_SETS.find((item) => item.id === setId)
}

export function getMockExamQuestionsForSet(setId: string): PythonTrialQuestion[] {
  const set = getMockExamSet(setId)
  if (!set) return resolveQuestions(MOCK_EXAM_SETS[0].questionIds)
  return resolveQuestions(set.questionIds)
}

export const DEFAULT_MOCK_EXAM_SET_ID = MOCK_EXAM_SETS[0].id

let cachedDefaultMockExamQuestions: PythonTrialQuestion[] | undefined

/** 延迟加载默认套卷，避免模块初始化时的循环依赖 */
export function getDefaultMockExamQuestions(): PythonTrialQuestion[] {
  if (!cachedDefaultMockExamQuestions) {
    cachedDefaultMockExamQuestions = getMockExamQuestionsForSet(DEFAULT_MOCK_EXAM_SET_ID)
  }
  return cachedDefaultMockExamQuestions
}
