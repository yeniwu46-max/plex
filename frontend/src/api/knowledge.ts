/**
 * Knowledge Intelligence Layer：知识库文档 / 知识图谱 / 索引状态 / 使用分析。
 * 对应后端 /api/v1/knowledge/*。
 */
import { formatHttpError, http, type ApiEnvelope } from './http'

export type IndexStatus = 'PENDING' | 'PARSING' | 'CHUNKING' | 'EMBEDDING' | 'INDEXING' | 'READY' | 'FAILED'
export const RUNNING_INDEX_STATUSES: IndexStatus[] = ['PENDING', 'PARSING', 'CHUNKING', 'EMBEDDING', 'INDEXING']

export type KnowledgeType =
  | 'concept_explanation'
  | 'example'
  | 'exercise'
  | 'solution'
  | 'misconception'
  | 'summary'
  | 'extension'
  | 'teacher_note'

export type ResourceType =
  | 'textbook'
  | 'slides'
  | 'markdown'
  | 'exercise'
  | 'mistake_analysis'
  | 'teacher_resource'
  | 'ai_generated'
  | 'other'

export const KNOWLEDGE_TYPE_LABELS: Record<KnowledgeType, string> = {
  concept_explanation: '概念讲解',
  example: '示例',
  exercise: '练习',
  solution: '解答',
  misconception: '误区',
  summary: '小结',
  extension: '拓展',
  teacher_note: '教师笔记',
}

export const RESOURCE_TYPE_LABELS: Record<ResourceType, string> = {
  textbook: '教材',
  slides: '课件',
  markdown: 'Markdown',
  exercise: '练习题',
  mistake_analysis: '错题解析',
  teacher_resource: '教师资源',
  ai_generated: 'AI 生成',
  other: '其他',
}

export const INDEX_STATUS_LABELS: Record<IndexStatus, string> = {
  PENDING: '排队中',
  PARSING: '解析中',
  CHUNKING: '切块中',
  EMBEDDING: '向量化中',
  INDEXING: '写入索引',
  READY: '已就绪',
  FAILED: '失败',
}

export interface KnowledgeIndexJob {
  id: string
  document_id: string
  version: number
  status: IndexStatus
  stage: string
  progress: number
  chunk_count: number
  embedded_count: number
  error_message: string | null
  embedding_provider?: string | null
  vector_backend?: string | null
  started_at?: string | null
  finished_at?: string | null
  created_at?: string
}

export interface KnowledgeDocument {
  id: string
  title: string
  file_name: string
  file_type: string
  file_size: number
  course_id: string | null
  chapter: string
  resource_type: ResourceType
  source: string
  audience_level: string
  uploaded_by: number | null
  version: number
  status: IndexStatus
  stage_progress: number
  error_message: string | null
  chunk_count: number
  concept_ids: string[]
  teacher_verified: boolean
  verified_by: number | null
  verified_at: string | null
  quality_score: number | null
  indexed_at: string | null
  created_at: string
  updated_at: string
  job?: KnowledgeIndexJob | null
}

export interface KnowledgeChunk {
  chunk_id: string
  document_id: string
  version: number
  sequence: number
  title: string
  content?: string
  preview?: string
  knowledge_type: KnowledgeType
  concept_ids: string[]
  primary_concept_id: string | null
  chapter: string
  difficulty: number
  resource_type: ResourceType
  source: string
  source_page: number | null
  teacher_verified: boolean
  token_count: number
  embedding_status: string
  embedding_model: string | null
}

export interface KnowledgeIndexStatus {
  ready: boolean
  course_id?: string
  documents: Record<IndexStatus, number>
  document_total: number
  chunk_total: number
  chunk_embedded: number
  concept_total: number
  vector: { backend: string; count: number; embedding?: { provider: string; model: string; dimensions: number } }
  running_jobs: KnowledgeIndexJob[]
  recent_failed: KnowledgeIndexJob[]
  async_mode: boolean
}

export type ConceptNodeType = 'concept' | 'skill' | 'example' | 'exercise' | 'misconception' | 'resource' | 'objective'
export type RelationType =
  | 'PREREQUISITE_OF'
  | 'RELATED_TO'
  | 'PART_OF'
  | 'EXAMPLE_OF'
  | 'EXERCISE_FOR'
  | 'MISCONCEPTION_OF'
  | 'REMEDIATES'
  | 'NEXT_RECOMMENDED'

export const RELATION_TYPE_LABELS: Record<RelationType, string> = {
  PREREQUISITE_OF: '前置于',
  RELATED_TO: '相关',
  PART_OF: '属于',
  EXAMPLE_OF: '示例',
  EXERCISE_FOR: '练习',
  MISCONCEPTION_OF: '误区',
  REMEDIATES: '补救',
  NEXT_RECOMMENDED: '推荐后续',
}

export interface KnowledgeConceptNode {
  concept_id: string
  name: string
  description: string
  course_id: string | null
  chapter: string
  node_type: ConceptNodeType
  difficulty: number
  importance: number
  learning_objectives: string[]
  common_misconceptions: string[]
  tags: string[]
  mastery_threshold: number
  status: string
  kg_node_id?: string | null
}

export interface KnowledgeRelationEdge {
  id: number
  source: string
  target: string
  relation_type: RelationType
  weight: number
  origin: string
  teacher_verified: boolean
  verified_by: number | null
  note: string | null
}

export interface KnowledgeGraphResult {
  nodes: KnowledgeConceptNode[]
  edges: KnowledgeRelationEdge[]
  stats: { node_count: number; edge_count: number; by_type: Record<string, number> }
  chapters: Array<{ key: string; title: string; order: number; description: string }>
}

export interface ConceptBrief {
  concept_id: string
  name: string
  node_type: ConceptNodeType
  difficulty: number
  description?: string
}

export interface KnowledgeConceptDetail extends KnowledgeConceptNode {
  prerequisites: string[]
  related_concepts: string[]
  example_ids: string[]
  exercise_ids: string[]
  misconception_ids: string[]
  resource_ids: string[]
  next_recommended: string[]
  prerequisite_nodes: ConceptBrief[]
  related_nodes: ConceptBrief[]
  misconception_nodes: ConceptBrief[]
  example_nodes: ConceptBrief[]
  exercise_nodes: ConceptBrief[]
  next_nodes: ConceptBrief[]
  usage?: { queries: number; students: number; low_confidence: number; strategies: Record<string, number> }
}

export interface ConceptKnowledgeResult {
  concept_ids: string[]
  concepts: ConceptBrief[]
  graph: { focus_ids: string[]; nodes: Array<{ concept_id: string; name: string; role: string; node_type: string }>; edges: unknown[] }
  strategy: { strategies: Array<{ code: string; label: string }>; mastery_band: string }
  chunks: Array<{
    chunk_id: string
    document_id: string
    title: string
    document_title: string
    knowledge_type: KnowledgeType
    concept_ids: string[]
    teacher_verified: boolean
    content: string
    difficulty: number
  }>
  grounded: boolean
}

export interface KnowledgeAnalyticsOverview {
  days: number
  total_queries: number
  unique_students: number
  avg_latency_ms: number
  grounded_rate: number
  hot_queries: Array<{ preview: string; count: number; students: number; concepts: string[] }>
  weak_concepts: Array<{ concept_id: string; name: string; queries: number; students: number; low_confidence: number }>
  intents: Record<string, number>
  strategies: Record<string, number>
  confidence_levels: Record<string, number>
}

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  limit: number
}

function unwrap<T>(data: ApiEnvelope<T>, fallback: string): T {
  if (data.code !== 0) throw new Error(data.message || fallback)
  return data.data
}

async function guard<T>(promise: Promise<{ data: ApiEnvelope<T> }>, fallback: string): Promise<T> {
  try {
    const { data } = await promise
    return unwrap(data, fallback)
  } catch (error) {
    throw new Error(formatHttpError(error, fallback))
  }
}

// ---------------------------------------------------------------- documents
export interface UploadDocumentOptions {
  title?: string
  course_id?: string
  chapter?: string
  resource_type?: ResourceType
  audience_level?: 'beginner' | 'intermediate' | 'advanced'
  teacher_verified?: boolean
  concept_ids?: string[]
  auto_index?: boolean
}

export function uploadKnowledgeDocument(file: File, options: UploadDocumentOptions = {}) {
  const form = new FormData()
  form.append('file', file)
  Object.entries(options).forEach(([key, value]) => {
    if (value === undefined || value === null) return
    form.append(key, Array.isArray(value) ? value.join(',') : String(value))
  })
  return guard(
    http.post<ApiEnvelope<KnowledgeDocument>>('/v1/knowledge/documents', form, { timeout: 120000 }),
    '文档上传失败',
  )
}

export function createKnowledgeTextDocument(payload: { title: string; text: string } & UploadDocumentOptions) {
  return guard(http.post<ApiEnvelope<KnowledgeDocument>>('/v1/knowledge/documents', payload), '文档创建失败')
}

export function fetchKnowledgeDocuments(params: { page?: number; per_page?: number; status?: string; source?: string; keyword?: string } = {}) {
  return guard(http.get<ApiEnvelope<Paginated<KnowledgeDocument>>>('/v1/knowledge/documents', { params }), '文档列表加载失败')
}

export function fetchKnowledgeDocument(id: string) {
  return guard(http.get<ApiEnvelope<KnowledgeDocument>>(`/v1/knowledge/documents/${id}`), '文档加载失败')
}

export function reindexKnowledgeDocument(id: string) {
  return guard(http.post<ApiEnvelope<KnowledgeIndexJob>>(`/v1/knowledge/documents/${id}/index`), '触发索引失败')
}

export function verifyKnowledgeDocument(id: string, verified: boolean, qualityScore?: number) {
  return guard(
    http.post<ApiEnvelope<KnowledgeDocument>>(`/v1/knowledge/documents/${id}/verify`, { verified, quality_score: qualityScore }),
    '更新审核状态失败',
  )
}

export function updateKnowledgeDocument(id: string, payload: Partial<Pick<KnowledgeDocument, 'title' | 'chapter' | 'resource_type' | 'audience_level' | 'quality_score' | 'course_id'>>) {
  return guard(http.patch<ApiEnvelope<KnowledgeDocument>>(`/v1/knowledge/documents/${id}`, payload), '更新文档失败')
}

export function deleteKnowledgeDocument(id: string) {
  return guard(http.delete<ApiEnvelope<null>>(`/v1/knowledge/documents/${id}`), '删除文档失败')
}

export function fetchKnowledgeChunks(id: string, params: { page?: number; per_page?: number; knowledge_type?: KnowledgeType; include_content?: boolean } = {}) {
  return guard(http.get<ApiEnvelope<Paginated<KnowledgeChunk>>>(`/v1/knowledge/documents/${id}/chunks`, { params }), 'Chunk 列表加载失败')
}

export function fetchKnowledgeIndexStatus() {
  return guard(http.get<ApiEnvelope<KnowledgeIndexStatus>>('/v1/knowledge/index/status'), '索引状态加载失败')
}

export function seedKnowledge(payload: { seed_graph?: boolean; index_builtin?: boolean } = {}) {
  return guard(http.post<ApiEnvelope<Record<string, unknown>>>('/v1/knowledge/seed', payload, { timeout: 120000 }), '初始化失败')
}

// ---------------------------------------------------------------- graph
export function fetchKnowledgeGraph(params: { node_types?: string; relation_types?: string; course_id?: string; include_problems?: boolean } = {}) {
  return guard(http.get<ApiEnvelope<KnowledgeGraphResult>>('/v1/knowledge/graph', { params }), '知识图谱加载失败')
}

export function fetchKnowledgeConcepts(params: { node_types?: string; chapter?: string; q?: string } = {}) {
  return guard(http.get<ApiEnvelope<{ items: KnowledgeConceptNode[]; total: number }>>('/v1/knowledge/concepts', { params }), '知识点列表加载失败')
}

export function fetchKnowledgeConcept(conceptId: string, withUsage = false) {
  return guard(
    http.get<ApiEnvelope<KnowledgeConceptDetail>>(`/v1/knowledge/concepts/${encodeURIComponent(conceptId)}`, { params: withUsage ? { with_usage: 1 } : undefined }),
    '知识点加载失败',
  )
}

export function updateKnowledgeConcept(conceptId: string, payload: Partial<Pick<KnowledgeConceptNode, 'name' | 'description' | 'difficulty' | 'importance' | 'tags' | 'learning_objectives' | 'common_misconceptions' | 'mastery_threshold'>>) {
  return guard(http.patch<ApiEnvelope<KnowledgeConceptDetail>>(`/v1/knowledge/concepts/${encodeURIComponent(conceptId)}`, payload), '更新知识点失败')
}

export function fetchConceptKnowledge(conceptId: string, params: { knowledge_types?: string; top_k?: number } = {}) {
  return guard(
    http.get<ApiEnvelope<ConceptKnowledgeResult>>(`/v1/knowledge/concepts/${encodeURIComponent(conceptId)}/knowledge`, { params }),
    '知识点材料加载失败',
  )
}

export function addKnowledgeRelation(payload: { source_id: string; target_id: string; relation_type: RelationType; weight?: number; note?: string; teacher_verified?: boolean }) {
  return guard(http.post<ApiEnvelope<KnowledgeRelationEdge>>('/v1/knowledge/relations', payload), '新增关系失败')
}

export function verifyKnowledgeRelation(relationId: number, verified: boolean) {
  return guard(http.post<ApiEnvelope<KnowledgeRelationEdge>>(`/v1/knowledge/relations/${relationId}/verify`, { verified }), '更新关系审核失败')
}

export function deleteKnowledgeRelation(relationId: number) {
  return guard(http.delete<ApiEnvelope<null>>(`/v1/knowledge/relations/${relationId}`), '删除关系失败')
}

// ---------------------------------------------------------------- analytics
export function fetchKnowledgeAnalytics(params: { days?: number; class_id?: number; limit?: number } = {}) {
  return guard(http.get<ApiEnvelope<KnowledgeAnalyticsOverview>>('/v1/knowledge/analytics/overview', { params }), '知识使用分析加载失败')
}
