import { http, formatHttpError, type ApiEnvelope } from './http'

export interface ModelUsageGroup {
  calls: number
  reported_total_tokens: number
  unknown_usage_calls: number
  failed_calls: number
  unfinished_calls: number
}
export interface CostCurrency {
  currency: string
  min: string
  max: string
  calls: number
  range_calls: number
}
export interface CostEstimate {
  status: 'no_calls' | 'unpriced' | 'partial' | 'estimated'
  basis: 'published_rates_estimate'
  invoice_verified: false
  estimated_calls: number
  unpriced_calls: number
  by_currency: CostCurrency[]
  unpriced_reasons: Record<string, number>
  by_workflow: Record<string, { estimated_calls: number; unpriced_calls: number; by_currency: CostCurrency[] }>
}
export interface ModelUsage {
  scope: 'connected_text_models'
  audience: 'self' | 'class'
  class_id: number | null
  period_start: string
  reset_at: string
  totals: ModelUsageGroup
  workflows: Record<'tutor' | 'resource' | 'rag' | 'counterexample', ModelUsageGroup>
  excluded: string[]
  cost: null
  cost_status: 'not_priced' | 'estimate_available'
  cost_estimate?: CostEstimate
}

export async function fetchModelUsage(classId?: number | null): Promise<ModelUsage> {
  try {
    const path = classId == null ? '/v1/ai/usage' : `/v1/teacher/classes/${classId}/ai-usage`
    const { data } = await http.get<ApiEnvelope<ModelUsage>>(path)
    if (data.code !== 0) throw new Error(data.message || '暂时无法读取用量')
    return data.data
  } catch (error) { throw new Error(formatHttpError(error, '暂时无法读取用量')) }
}

export interface RagQuota {
  scope: 'rag'
  request_limit: number
  requests_used: number
  requests_remaining: number
  active_requests: number
  concurrency_limit: number
  attempt_limit: number
  reset_at: string
}
export async function fetchRagQuota(): Promise<RagQuota> {
  const { data } = await http.get<ApiEnvelope<RagQuota>>('/v1/rag/usage')
  if (data.code !== 0) throw new Error(data.message || '课程问答额度读取失败')
  return data.data
}

export interface ResourceQuota {
  scope: 'resource'
  request_limit: number
  requests_used: number
  requests_remaining: number
  active_tasks: number
  active_limit: number
  attempt_limit: number
  reset_at: string
}
export async function fetchResourceQuota(classId?: number | null): Promise<ResourceQuota> {
  try {
    const path = classId == null ? '/v1/student/resource-generation/usage' : `/v1/teacher/classes/${classId}/resource-generation/usage`
    const {data} = await http.get<ApiEnvelope<ResourceQuota>>(path)
    if (data.code !== 0) throw new Error(data.message || '暂时无法读取资源额度')
    return data.data
  } catch (error) { throw new Error(formatHttpError(error, '暂时无法读取资源额度')) }
}
