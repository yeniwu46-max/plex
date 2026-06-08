import { http, type ApiEnvelope } from './http'

export interface StudentMistakeItem {
  id: number
  source: string
  knowledge_key: string
  knowledge_label?: string
  question_ref: string
  question_id: string
  question_title: string
  topic: string
  tags: string[]
  star_path_node_id: string | null
  star_path_node_title: string | null
  failed_case_labels: string[]
  error_types: string[]
  error_type?: string
  fail_count: number
  last_failed_at: string
  last_passed_at: string | null
}

export interface WeakKnowledgeItem {
  knowledge_key: string
  knowledge_label: string
  fail_count: number
  weight?: number
}

export interface StudentMistakesResult {
  items: StudentMistakeItem[]
  weak_knowledge: WeakKnowledgeItem[]
  total: number
}

export interface CodeTrialRunPayload {
  question_id: string
  question_title?: string
  knowledge_key?: string
  topic?: string
  tags?: string[]
  star_path_node_id?: string | null
  star_path_node_title?: string | null
  cases: Array<{ label: string; passed: boolean; error?: string }>
}

export async function fetchStudentMistakes(params?: {
  knowledge_key?: string
  active_only?: boolean
}) {
  const { data } = await http.get<ApiEnvelope<StudentMistakesResult>>('/v1/student/mistakes', {
    params: {
      knowledge_key: params?.knowledge_key,
      active_only: params?.active_only === false ? 'false' : 'true',
    },
  })
  if (data.code !== 0) throw new Error(data.message || '错题加载失败')
  return data.data
}

export async function submitCodeTrialRun(payload: CodeTrialRunPayload) {
  const { data } = await http.post<ApiEnvelope<{ record: StudentMistakeItem | null }>>(
    '/v1/student/code-trial/runs',
    payload,
  )
  if (data.code !== 0) throw new Error(data.message || '错题同步失败')
  return data.data
}
