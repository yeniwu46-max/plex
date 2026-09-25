/**
 * Graph-enhanced RAG：问答 / 仅检索 / 来源 / 请求日志。
 * 对应后端 /api/v1/rag/*。学生端返回的是安全视图（不含相似度、rerank 分值）。
 */
import { formatHttpError, http, type ApiEnvelope } from './http'
import type { KnowledgeDocument, KnowledgeType, Paginated } from './knowledge'

export type RagScene = 'chat' | 'trial' | 'practice' | 'exercise' | 'emergency' | 'problem' | 'diagnosis' | 'path' | 'resource'
export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW_CONFIDENCE'

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

export interface RagQueryPayload {
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
  answer: string
  concepts: RagConceptView[]
  sources: RagSourceView[]
  confidence: number
  confidence_level: ConfidenceLevel
  knowledge_grounded: boolean
  teaching_strategy: RagStrategyView
  recommended_next: RagRecommendedNext[]
  hint_level: number | null
  intent: string
  generation_mode: 'llm' | 'extractive' | 'refused'
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

export function ragQuery(payload: RagQueryPayload) {
  return guard(http.post<ApiEnvelope<RagAnswer>>('/v1/rag/query', payload, { timeout: 90000 }), '知识问答失败')
}

export function ragRetrieve(payload: RagRetrievePayload) {
  return guard(http.post<ApiEnvelope<RagRetrieveResult>>('/v1/rag/retrieve', payload, { timeout: 60000 }), '检索失败')
}

export function fetchRagSource(chunkId: string) {
  return guard(http.get<ApiEnvelope<RagSourceDetail>>(`/v1/rag/sources/${encodeURIComponent(chunkId)}`), '来源加载失败')
}

export function fetchRagLogs(params: { page?: number; per_page?: number; user_id?: number; scene?: string; status?: string } = {}) {
  return guard(http.get<ApiEnvelope<Paginated<RagQueryLog>>>('/v1/rag/logs', { params }), 'RAG 日志加载失败')
}

export function fetchRagLog(logId: number) {
  return guard(http.get<ApiEnvelope<RagQueryLog>>(`/v1/rag/logs/${logId}`), 'RAG 日志加载失败')
}
