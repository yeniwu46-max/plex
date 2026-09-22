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
  review_schedule?: {
    algorithm: 'SM-2'
    ease_factor: number
    interval_days: number
    repetitions: number
    review_count: number
    last_quality: number | null
    last_reviewed_at: string | null
    due_at: string
  } | null
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

export interface DueMistakeReviewsResult {
  items: StudentMistakeItem[]
  total: number
  limit: number
}

export interface MistakeReviewResult {
  record: StudentMistakeItem
  student_profile_update: {
    version: number
    completion_rate: number
    reason: 'sm2_review'
  }
  knowledge_graph_update: {
    node_id: string | null
    status: string | null
    review_count: number
    review_repetitions: number
    last_review_quality: number | null
    next_review_due_at: string | null
  }
  learning_path_update: {
    active_node_id: string | null
    next_best_action: { node_id: string | null; reason: string; action: string }
    replanned: boolean
    trigger: 'sm2_review'
    path_diff?: {
      previous_active_node_id?: string | null
      current_active_node_id?: string | null
      changed: boolean
      previous_top_node_ids?: string[]
      current_top_node_ids?: string[]
    }
  }
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

export async function fetchDueMistakeReviews(limit = 20) {
  const { data } = await http.get<ApiEnvelope<DueMistakeReviewsResult>>(
    '/v1/student/mistakes/reviews/due',
    { params: { limit } },
  )
  if (data.code !== 0) throw new Error(data.message || '复习任务加载失败')
  return data.data
}

export async function submitMistakeReview(mistakeId: number, quality: number) {
  const { data } = await http.post<ApiEnvelope<MistakeReviewResult>>(
    `/v1/student/mistakes/${mistakeId}/review`,
    { quality },
  )
  if (data.code !== 0) throw new Error(data.message || '复习结果提交失败')
  return data.data
}
