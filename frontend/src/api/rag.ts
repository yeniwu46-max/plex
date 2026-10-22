/**
 * Graph-enhanced RAG：问答 / 仅检索 / 来源 / 请求日志。
 * 对应后端 /api/v1/rag/*。学生端返回的是安全视图（不含相似度、rerank 分值）。
 */
import { formatHttpError, http, type ApiEnvelope } from './http'
import type { KnowledgeDocument, KnowledgeType, Paginated } from './knowledge'
import type { TutorContextRequest } from './tutorContext'
import type { TutorResponse } from './tutoring'
import { useAuthStore } from '../stores/auth'
import { ragRequestIdentity } from '../utils/ragRequestIdentity'
export { latestRagRequest } from '../utils/ragRequestIdentity'

export type RagScene = 'chat' | 'trial' | 'practice' | 'exercise' | 'emergency' | 'problem' | 'diagnosis' | 'path' | 'resource'
export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW_CONFIDENCE' | 'UNASSESSED'

export interface RagConceptView {
  concept_id: string
  name: string
  node_type: string
  role: 'focus' | 'prerequisite' | 'related'
  mastery_status: string | null
}

export interface RagSourceView {
  chunk_id: string
  document_id: string
  version?: number
  chapter?: string
  url?: string
  title: string
  document_title: string
  knowledge_type: KnowledgeType
  concept_ids: string[]
  resource_type: string
  source: string
  source_page: number | null
  teacher_verified: boolean
  preview: string
}

export interface RagStrategyView {
  strategies: Array<{ code: string; label: string }>
  mastery_band: 'low' | 'medium' | 'high' | 'unknown'
  style: string
  practice_mode: boolean
  hint_level: number | null
  hint_max_level: number | null
  hint_name: string | null
}

export interface RagRecommendedNext {
  type: 'prerequisite' | 'exercise' | 'misconception' | 'next' | 'review'
  concept_id: string
  name: string
  reason: string
}

export interface RagRequestContext {
  task_type?: string
  task_id?: string | number
  trial_id?: string | number
  problem_id?: string | number
  concept_hint?: string
  concept_ids?: string[]
  stage?: string
  title?: string
  hint_level?: number
}

export interface RagQueryPayload extends TutorContextRequest {
  request_id?: string
  session_id?: string
  query: string
  scene?: RagScene
  context?: RagRequestContext
  hint_level?: number
  history?: Array<{ role: string; content: string }>
  /** 仅管理员生效 */
  debug?: boolean
  /** 仅管理员生效 */
  use_llm?: boolean
}

export interface RagDebugChunk {
  chunk_id: string
  document_id: string
  content: string
  title: string
  knowledge_type: KnowledgeType
  concept_ids: string[]
  primary_concept_id: string | null
  difficulty: number
  resource_type: string
  source: string
  teacher_verified: boolean
  document_title: string
  vector_score: number
  lexical_score: number
  hybrid_score: number
  score_breakdown: Record<string, number>
  final_score: number
  rank: number
  retrieval_channels: string[]
}

export interface RagGraphNode {
  concept_id: string
  name: string
  node_type: string
  role: string
  hop: number
  weight: number
  mastery: number | null
  description: string
}

export interface RagGraphContext {
  focus_ids: string[]
  nodes: RagGraphNode[]
  edges: Array<{ source: string; target: string; type: string; weight: number; teacher_verified?: boolean }>
  unmet_prerequisites: string[]
  misconceptions: string[]
  next_recommended: string[]
}

export interface RagUnderstanding {
  query: string
  normalized_query: string
  intent: string
  concept_ids: string[]
  concept_scores: Record<string, number>
  keywords: string[]
  error_type: string | null
  difficulty_hint: number | null
  method: string
}

export interface RagRerankExplain {
  chunk_id: string
  rank: number
  final_score: number
  hybrid_score: number
  vector_score: number
  lexical_score: number
  breakdown: Record<string, number>
  channels: string[]
}

export interface RagStrategyDebug {
  strategies: string[]
  mastery_band: string
  focus_mastery: number | null
  style: string
  hint_level: number | null
  hint_max_level: number | null
  hint_policy: Record<string, unknown>
  practice_mode: boolean
  rationale: string[]
}

export interface RagDebugPayload {
  understanding: RagUnderstanding
  graph: RagGraphContext
  candidates: RagDebugChunk[]
  reranked: RagDebugChunk[]
  rerank_explain: RagRerankExplain[]
  strategy: RagStrategyDebug
  context: {
    learner_context: string
    knowledge_context: string
    retrieved_context: string
    teaching_strategy: string
    hint_instruction: string
    system_prompt: string
    user_prompt: string
  }
  filters: Record<string, unknown>
  channel_stats: Record<string, unknown>
  learner_context: Record<string, unknown>
  blocked_reason: string | null
}

export interface RagAnswer {
  request_id?: string
  tutor?: TutorResponse
  answer: string
  concepts: RagConceptView[]
  sources: RagSourceView[]
  confidence: number | null
  confidence_level: ConfidenceLevel
  knowledge_grounded: boolean
  teaching_strategy: RagStrategyView
  recommended_next: RagRecommendedNext[]
  hint_level: number | null
  intent: string
  generation_mode: 'llm' | 'extractive' | 'refused' | 'llm_reviewed'
  latency_ms: number
  log_id: number | null
  model?: string | null
  provider?: string | null
  token_usage?: Record<string, unknown>
  debug?: RagDebugPayload
}

/** 小 E 流式 done 事件里附带的知识卡片（answer 已剔除）。 */
export type MessengerKnowledge = Omit<RagAnswer, 'answer'>

export interface RagRetrieveResult {
  query: string
  understanding: RagUnderstanding
  graph: RagGraphContext
  candidates: RagDebugChunk[]
  reranked: RagDebugChunk[]
  rerank_explain: RagRerankExplain[]
  strategy: RagStrategyDebug
  filters: Record<string, unknown>
  channel_stats: Record<string, unknown>
  confidence: number
  confidence_level: ConfidenceLevel
  knowledge_grounded: boolean
  learner_context: Record<string, unknown>
  latency_ms: number
}

export interface RagRetrievePayload {
  query: string
  top_k?: number
  knowledge_types?: KnowledgeType[]
  document_ids?: string[]
  require_verified?: boolean
  as_user_id?: number
  context?: RagRequestContext
  log?: boolean
}

export interface RagSourceDetail {
  chunk_id: string
  document_id: string
  version?: number
  chapter?: string
  title: string
  document_title?: string
  knowledge_type: KnowledgeType
  concept_ids: string[]
  resource_type: string
  source: string
  source_page: number | null
  teacher_verified: boolean
  content: string
  document?: KnowledgeDocument | null
}

export interface RagQueryLog {
  id: number
  user_id: number | null
  role: string
  scene: string
  query_hash: string
  query_preview: string
  intent: string
  detected_concepts: string[]
  graph_nodes: string[]
  retrieved_chunks: string[]
  retrieval_scores: Record<string, number>
  rerank_scores: Record<string, number>
  teaching_strategy: string[]
  hint_level: number | null
  model: string | null
  provider: string | null
  generation_mode: string
  latency_ms: number
  token_usage: Record<string, unknown>
  confidence: number
  confidence_level: ConfidenceLevel
  knowledge_grounded: boolean
  status: string
  error_message: string | null
  created_at: string
}

async function guard<T>(promise: Promise<{ data: ApiEnvelope<T> }>, fallback: string): Promise<T> {
  try {
    const { data } = await promise
    if (data.code !== 0) throw new Error(data.message || fallback)
    return data.data
  } catch (error) {
    throw new Error(formatHttpError(error, fallback))
  }
}

export async function ragQuery(payload: RagQueryPayload) {
  const auth = useAuthStore(), owner = auth.profile?.id, role = auth.profile?.role
  if (!owner) throw new Error('请先登录')
  const { request_id: explicit, ...body } = payload
  const identity = await ragRequestIdentity(owner, body, explicit)
  const current = () => auth.profile?.id === owner && auth.profile?.role === role
  if (!current()) throw new Error('账号已切换，请重新提问')
  try {
    const { data } = await http.post<ApiEnvelope<RagAnswer>>('/v1/rag/query',
      { ...body, request_id: identity.requestId }, { timeout: 90000 })
    if (!current()) throw new Error('账号已切换，请重新提问')
    if (data.code !== 0) throw new Error(data.message || '知识问答失败')
    identity.clear()
    return data.data
  } catch (error) {
    if (!current()) throw new Error('账号已切换，请重新提问')
    const response = (error as { response?: { status?: number; data?: { data?: { reason?: string } } } }).response
    const reason = response?.data?.data?.reason
    if (response?.status === 400 || ['request_conflict', 'sources_changed', 'not_found', 'access_changed', 'attempt_limit'].includes(reason || '')) identity.clear()
    throw new Error(formatHttpError(error, '知识问答失败；可恢复上次结果，或用相同内容重试'))
  }
}

export interface RagRequestResult {
  request_id: string
  status: 'processing' | 'complete' | 'failed' | 'expired'
  attempts_remaining: number
  answer: RagAnswer | null
}
export async function fetchRagRequest(id: string) {
  const auth = useAuthStore(), owner = auth.profile?.id, role = auth.profile?.role
  const result = await guard(http.get<ApiEnvelope<RagRequestResult>>(`/v1/rag/requests/${encodeURIComponent(id)}`), '问答恢复失败')
  if (!owner || auth.profile?.id !== owner || auth.profile?.role !== role) throw new Error('账号已切换，请重新读取')
  return result
}

export function ragRetrieve(payload: RagRetrievePayload) {
  return guard(http.post<ApiEnvelope<RagRetrieveResult>>('/v1/rag/retrieve', payload, { timeout: 60000 }), '检索失败')
}

export function fetchRagSource(chunkId: string, version?: number) {
  return guard(http.get<ApiEnvelope<RagSourceDetail>>(`/v1/rag/sources/${encodeURIComponent(chunkId)}`, { params: { version } }), '来源已更新、撤回或暂时无法访问，请重新提问')
}

export function fetchRagLogs(params: { page?: number; per_page?: number; user_id?: number; scene?: string; status?: string } = {}) {
  return guard(http.get<ApiEnvelope<Paginated<RagQueryLog>>>('/v1/rag/logs', { params }), 'RAG 日志加载失败')
}

export function fetchRagLog(logId: number) {
  return guard(http.get<ApiEnvelope<RagQueryLog>>(`/v1/rag/logs/${logId}`), 'RAG 日志加载失败')
}
