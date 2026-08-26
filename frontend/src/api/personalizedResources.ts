import { http, type ApiEnvelope } from './http'

export type PersonalizedResourceType =
  | 'learning_bundle'
  | 'lesson_document'
  | 'mind_map'
  | 'exercise_set'
  | 'extended_reading'
  | 'coding_lab'
  | 'audio_explanation'
  | 'video_lesson'

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
  is_anomaly?: boolean
  student_warning?: string | null
  ai_review?: Record<string, unknown>
}

export interface ResourceTask {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  current_agent?: string | null
  steps: AgentTraceStep[]
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

export interface AgentTraceStep {
  agent: string
  name?: string
  contract_version?: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  latency_ms?: number | null
  backend?: string | null
  model?: string | null
  depends_on?: string | null
  input_summary?: Record<string, unknown>
  output_summary?: Record<string, unknown>
  started_at?: string | null
  completed_at?: string | null
  error?: string | null
}

export async function createResourceTask(
  knowledgeKey: string,
  resourceTypes?: PersonalizedResourceType[],
  idempotencyKey?: string,
  options?: {
    target?: string
    learning_stage?: string
    learning_style?: string[]
    force_regenerate?: boolean
    require_real_api?: boolean
  },
) {
  const { data } = await http.post<ApiEnvelope<ResourceTask>>('/v1/student/resource-generation/tasks', {
    knowledge_key: knowledgeKey,
    resource_types: resourceTypes,
    idempotency_key: idempotencyKey,
    target: options?.target,
    learning_stage: options?.learning_stage,
    learning_style: options?.learning_style,
    force_regenerate: options?.force_regenerate ?? true,
    require_real_api: options?.require_real_api ?? true,
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

export async function fetchReviewResources(
  reviewStatus = 'pending_review',
  options?: { anomalyOnly?: boolean },
) {
  const { data } = await http.get<ApiEnvelope<{ items: PersonalizedResource[]; total: number }>>(
    '/v1/teacher/personalized-resources/review',
    {
      params: {
        review_status: reviewStatus,
        ...(options?.anomalyOnly === undefined
          ? {}
          : { anomaly_only: options.anomalyOnly ? 'true' : 'false' }),
      },
    },
  )
  if (data.code !== 0) throw new Error(data.message || '待审核资源加载失败')
  return data.data
}

export interface ResourceReviewMetrics {
  total_resources: number
  status_counts: Record<'pending_review' | 'approved' | 'rejected', number>
  pending_review_count: number
  anomaly_pending_count?: number
  average_review_minutes: number | null
  risk_reason_distribution: Array<{ reason: string; count: number }>
  verdict_distribution?: Array<{ verdict: AuditVerdict; count: number }>
  avg_dimension_scores?: Partial<Record<keyof DimensionScores, number>>
}

export type AuditVerdict = 'PASS' | 'NEED_MODIFY' | 'REJECT'
export type CheckLevel = 'PASS' | 'WARNING' | 'FAIL'

export interface AuditCheckItem {
  id: string
  label: string
  level: CheckLevel
  detail: string
}

export interface AuditStepResult {
  step: number
  name: string
  checks: AuditCheckItem[]
  score: number
  summary: string
}

export interface DimensionScores {
  knowledge_accuracy: number
  teaching_quality: number
  case_quality: number
  exercise_quality: number
  code_quality: number
  ai_trustworthiness: number
}

export interface AuditReport {
  verdict: AuditVerdict
  suggested_publish: boolean
  summary: string
  steps: AuditStepResult[]
  dimensions: DimensionScores
  knowledge_key: string
  backend: string
  metadata?: Record<string, unknown>
}

export interface ResourceAuditResponse {
  resource_id: number
  generation_task_id: string
  audit_report: AuditReport
}

const DIMENSION_LABELS: Record<keyof DimensionScores, string> = {
  knowledge_accuracy: '知识准确性',
  teaching_quality: '教学质量',
  case_quality: '案例质量',
  exercise_quality: '练习质量',
  code_quality: '代码质量',
  ai_trustworthiness: 'AI 可信度',
}

export { DIMENSION_LABELS }

export async function fetchResourceAudit(resourceId: number) {
  const { data } = await http.get<ApiEnvelope<ResourceAuditResponse>>(
    `/v1/teacher/personalized-resources/${resourceId}/audit`,
  )
  if (data.code !== 0) throw new Error(data.message || '审核报告加载失败')
  return data.data
}

export async function rerunResourceAudit(resourceId: number) {
  const { data } = await http.post<ApiEnvelope<ResourceAuditResponse>>(
    `/v1/teacher/personalized-resources/${resourceId}/audit/rerun`,
  )
  if (data.code !== 0) throw new Error(data.message || '重新审核失败')
  return data.data
}

export async function fetchResourceReviewMetrics() {
  const { data } = await http.get<ApiEnvelope<ResourceReviewMetrics>>(
    '/v1/teacher/personalized-resources/metrics',
  )
  if (data.code !== 0) throw new Error(data.message || '审核指标加载失败')
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

export interface SmartReviewResult {
  approved_count: number
  flagged_count: number
  total: number
  items: Array<{ id: number; decision: string; is_anomaly?: boolean }>
}

export async function runTeacherSmartReview() {
  const { data } = await http.post<ApiEnvelope<SmartReviewResult>>(
    '/v1/teacher/personalized-resources/smart-review',
  )
  if (data.code !== 0) throw new Error(data.message || '智能审核失败')
  return data.data
}

export async function releasePendingResources(releaseAll = true) {
  const { data } = await http.post<ApiEnvelope<{
    approved_count: number
    kept_anomaly_count: number
    total: number
  }>>('/v1/teacher/personalized-resources/release-pending', {
    release_all: releaseAll,
  })
  if (data.code !== 0) throw new Error(data.message || '资源放行失败')
  return data.data
}

/** 下载已生成资源内容为 Markdown/JSON 文件（前端导出，不落密钥）。 */
export function downloadPersonalizedResource(item: PersonalizedResource) {
  const content = item.content || {}
  const hasStructuredText =
    typeof content === 'object' &&
    (typeof (content as { markdown?: unknown }).markdown === 'string' ||
      typeof (content as { body?: unknown }).body === 'string' ||
      typeof (content as { summary?: unknown }).summary === 'string')
  let blob: Blob
  let filename: string
  if (item.content_url && /\.(pdf|mp3|mp4|wav|png|jpg)$/i.test(item.content_url)) {
    const anchor = document.createElement('a')
    anchor.href = item.content_url
    anchor.download = ''
    anchor.target = '_blank'
    anchor.rel = 'noopener'
    anchor.click()
    return
  }
  if (hasStructuredText) {
    const parts = [
      `# ${item.title}`,
      '',
      `知识点：${item.knowledge_label}`,
      `类型：${item.resource_type}`,
      '',
      String(
        (content as { markdown?: string }).markdown ||
          (content as { body?: string }).body ||
          (content as { summary?: string }).summary ||
          '',
      ),
    ]
    const exercises = (content as { exercises?: unknown[] }).exercises
    if (Array.isArray(exercises) && exercises.length) {
      parts.push('', '## 练习题', '')
      exercises.forEach((ex, index) => {
        const row = ex as Record<string, unknown>
        parts.push(`### ${index + 1}. ${row.stem || row.question || '题目'}`)
        if (Array.isArray(row.options)) {
          row.options.forEach((opt, oi) => {
            parts.push(`${String.fromCharCode(65 + oi)}. ${opt}`)
          })
        }
        if (row.answer != null || row.correct_index != null) {
          parts.push(`答案：${row.answer ?? row.correct_index}`)
        }
        parts.push('')
      })
    }
    blob = new Blob([parts.join('\n')], { type: 'text/markdown;charset=utf-8' })
    filename = `${item.title || 'resource'}-${item.id}.md`
  } else {
    blob = new Blob([JSON.stringify({ id: item.id, title: item.title, content }, null, 2)], {
      type: 'application/json;charset=utf-8',
    })
    filename = `${item.title || 'resource'}-${item.id}.json`
  }
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename.replace(/[\\/:*?"<>|]/g, '_')
  anchor.click()
  URL.revokeObjectURL(url)
}
