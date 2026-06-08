import { http, type ApiEnvelope } from './http'

export type PersonalizedResourceType =
  | 'lesson_document'
  | 'mind_map'
  | 'exercise_set'
  | 'extended_reading'
  | 'coding_lab'
  | 'audio_explanation'

export interface PersonalizedResource {
  id: number
  user_id: number
  knowledge_key: string
  knowledge_label: string
  resource_type: PersonalizedResourceType
  title: string
  content: Record<string, unknown>
  content_url?: string | null
  difficulty: number
  estimated_minutes: number
  profile_snapshot: Record<string, string>
  recommendation_reason: string
  citations: Array<{ document_id: string; title: string; section: string; snippet: string }>
  confidence: number
  review_status: 'pending_review' | 'approved' | 'rejected'
  review_reason?: string | null
  risk_reasons: string[]
  generator_agent: string
  generation_task_id: string
  backend: string
}

export interface ResourceTask {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  current_agent?: string | null
  steps: Array<{ agent: string; status: string; latency_ms?: number | null }>
  resources: PersonalizedResource[]
  error?: string | null
  backend: string
  fallback_reason?: string | null
  retry_of?: string | null
  profile_version: number
  request_fingerprint: string
  recoverable: boolean
  created_at?: string | null
  completed_at?: string | null
}

export async function createResourceTask(
  knowledgeKey: string,
  resourceTypes?: PersonalizedResourceType[],
  idempotencyKey?: string,
) {
  const { data } = await http.post<ApiEnvelope<ResourceTask>>('/v1/student/resource-generation/tasks', {
    knowledge_key: knowledgeKey,
    resource_types: resourceTypes,
    idempotency_key: idempotencyKey,
  })
  if (data.code !== 0) throw new Error(data.message || '创建生成任务失败')
  return data.data
}

export async function fetchResourceTasks() {
  const { data } = await http.get<ApiEnvelope<{ items: ResourceTask[]; total: number }>>(
    '/v1/student/resource-generation/tasks',
  )
  if (data.code !== 0) throw new Error(data.message || '任务历史加载失败')
  return data.data
}

export async function retryResourceTask(taskId: string) {
  const { data } = await http.post<ApiEnvelope<ResourceTask>>(
    `/v1/student/resource-generation/tasks/${taskId}/retry`,
  )
  if (data.code !== 0) throw new Error(data.message || '任务重试失败')
  return data.data
}

export async function fetchResourceTask(taskId: string) {
  const { data } = await http.get<ApiEnvelope<ResourceTask>>(`/v1/student/resource-generation/tasks/${taskId}`)
  if (data.code !== 0) throw new Error(data.message || '任务状态加载失败')
  return data.data
}

export async function fetchPersonalizedResources() {
  const { data } = await http.get<ApiEnvelope<{ items: PersonalizedResource[]; total: number }>>(
    '/v1/student/personalized-resources',
  )
  if (data.code !== 0) throw new Error(data.message || '资源加载失败')
  return data.data
}

export async function fetchReviewResources(reviewStatus = 'pending_review') {
  const { data } = await http.get<ApiEnvelope<{ items: PersonalizedResource[]; total: number }>>(
    '/v1/teacher/personalized-resources/review',
    { params: { review_status: reviewStatus } },
  )
  if (data.code !== 0) throw new Error(data.message || '待审核资源加载失败')
  return data.data
}

export async function reviewPersonalizedResource(
  resourceId: number,
  reviewStatus: 'approved' | 'rejected',
  reason = '',
) {
  const { data } = await http.put<ApiEnvelope<PersonalizedResource>>(
    `/v1/teacher/personalized-resources/${resourceId}/review`,
    { review_status: reviewStatus, reason },
  )
  if (data.code !== 0) throw new Error(data.message || '审核失败')
  return data.data
}
