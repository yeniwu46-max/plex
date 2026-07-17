import { http, type ApiEnvelope } from './http'
import type { PythonRunMode, PythonTestCase, PythonTrialDifficulty } from '../data/pythonTrialQuestions'

export interface PracticeQuestionPayload {
  id: string
  code?: string
  title: string
  topic: string
  difficulty: PythonTrialDifficulty
  reward_xp: number
  duration_min: number
  tags: string[]
  description: string
  constraints: string[]
  examples: { input: string; output: string; explain?: string }[]
  test_cases: PythonTestCase[]
  starter_code: string
  run_mode: PythonRunMode
  hint: string
  knowledge_key?: string
  source?: string
  db_question_id?: number
}

export interface PracticeQuestionsResult {
  items: PracticeQuestionPayload[]
  total: number
}

export async function fetchPracticeQuestions(knowledgeKey?: string, search?: string) {
  const { data } = await http.get<ApiEnvelope<PracticeQuestionsResult>>('/v1/student/practice-questions', {
    params: {
      ...(knowledgeKey ? { knowledge_key: knowledgeKey } : {}),
      ...(search?.trim() ? { q: search.trim() } : {}),
    },
  })
  if (data.code !== 0) throw new Error(data.message || '练习题加载失败')
  return data.data
}

export async function fetchPracticeQuestionByRef(questionRef: string) {
  const ref = encodeURIComponent(questionRef.trim())
  const { data } = await http.get<ApiEnvelope<PracticeQuestionPayload>>(`/v1/student/practice-questions/${ref}`)
  if (data.code !== 0) throw new Error(data.message || '题目不存在')
  return data.data
}
