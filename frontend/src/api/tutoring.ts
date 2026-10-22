import { formatHttpError, http, type ApiEnvelope } from './http'
import type { TutorContextRequest, TutorContextView } from './tutorContext'
import type { RagSourceView } from './rag'

export type TutorMode = 'explain_error' | 'review_approach' | 'next_step' | 'pseudocode'
export const tutorModes: Array<{ mode: TutorMode; label: string }> = [
  { mode: 'explain_error', label: '解释这个报错' },
  { mode: 'review_approach', label: '检查我的思路' },
  { mode: 'next_step', label: '只提示下一步' },
  { mode: 'pseudocode', label: '用伪代码说明' },
]
export interface TutorRequest extends TutorContextRequest {
  request_id: string
  session_id?: string
  mode: TutorMode
  hint_level?: number
  question: string
}
export type AutoTutorMode = 'concept_explain' | 'algorithm_validation' | 'algorithm_trace' | 'learning_overview' | 'clarify'
export type ArtifactTutorMode = 'learning_document' | 'knowledge_graph'
export interface CounterexamplePick {
  id: string
  title: string
  revision: number
  version: string
  concept_id: string
  state_version: number
  evidence_ids: number[]
  reason: string
  practice_path: string
}
export interface TutorResponse {
  counterexample_pick?: CounterexamplePick | null
  recommendation_notice?: string
  request_id: string
  session_id: string
  display_receipt_id: string | null
  mode: TutorMode | AutoTutorMode | ArtifactTutorMode
  title?: string
  sections?: Array<{ heading: string; text: string }>
  nodes?: Array<{ id: string; label: string }>
  edges?: Array<{ from: string; to: string }>
  example?: { code: string; explanation: string } | null
  trace_input?: string
  trace_steps?: string[]
  trace_notice?: string
  execution_trace?: import('./pythonTrace').PythonTrace
  records_at?: string
  question_pick?: import('./agentService').MessengerQuickActionResult['question_pick']
  status: 'ok' | 'needs_context' | 'safe_fallback'
  summary: string
  next_step: string
  follow_up: string
  annotations?: Array<{ line: number; message: string }>
  pseudocode_lines?: Array<{ step: string; explanation: string }>
  scope?: 'partial'
  citations: Array<RagSourceView & { supports: string }>
  evidence_status: 'grounded' | 'insufficient_evidence' | 'retrieval_unavailable' | 'not_requested' | 'learning_records'
  evidence_notice: string
  state_version: number
  context: TutorContextView
  teaching_plan: { mode: TutorMode | AutoTutorMode | ArtifactTutorMode; hint_level: number; task_policy: string; state_version: number }
  generation_mode: 'llm_reviewed' | 'rules' | 'none' | 'learning_records'
  policy_result: {
    version: string; status: string; reason: string | null; checks: string[]
    review_failures?: Array<'answer_leakage' | 'unsupported_claims' | 'citation_mismatch' | 'repeats_hint' | 'policy_violation' | 'invalid_review'>
  }
}
export async function askTutor(body: TutorRequest): Promise<TutorResponse> {
  try {
    const { data } = await http.post<ApiEnvelope<TutorResponse>>('/v1/student/tutor/ask', body, { timeout: 90000 })
    if (data.code !== 0) throw new Error(data.message || '这次辅导尚未完成')
    return data.data
  } catch (error) { throw new Error(formatHttpError(error, '这次辅导尚未完成')) }
}

export async function fetchTutorTurn(requestId: string): Promise<TutorResponse> {
  try {
    const { data } = await http.get<ApiEnvelope<TutorResponse>>(`/v1/student/tutor/turns/${encodeURIComponent(requestId)}`)
    if (data.code !== 0) throw new Error(data.message || '无法恢复辅导记录')
    return data.data
  } catch (error) { throw new Error(formatHttpError(error, '无法恢复辅导记录')) }
}

export interface TutorUsage {
  scope: 'tutor'
  request_limit: number
  requests_used: number
  requests_remaining: number
  active_requests: number
  concurrency_limit: number
  model_calls: number
  reported_total_tokens: number
  unknown_usage_calls: number
  failed_calls: number
  cancelled_requests: number
  reset_at: string
  cost: null
  cost_status: 'not_priced'
}
export async function cancelTutorTurn(requestId: string): Promise<{request_id:string;status:'complete'|'cancelled';cancelled:boolean}> {
  try {
    const { data } = await http.post<ApiEnvelope<{request_id:string;status:'complete'|'cancelled';cancelled:boolean}>>(`/v1/student/tutor/turns/${encodeURIComponent(requestId)}/cancel`)
    if(data.code!==0) throw new Error(data.message || '取消请求未完成')
    return data.data
  } catch(error) { throw new Error(formatHttpError(error, '取消请求未完成，原请求可能仍在处理')) }
}
export async function fetchTutorUsage(): Promise<TutorUsage> {
  try {
    const { data } = await http.get<ApiEnvelope<TutorUsage>>('/v1/student/tutor/usage')
    if(data.code!==0) throw new Error(data.message || '暂时无法读取用量')
    return data.data
  } catch(error) { throw new Error(formatHttpError(error, '暂时无法读取用量')) }
}
