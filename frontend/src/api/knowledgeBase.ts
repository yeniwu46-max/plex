import { http, type ApiEnvelope } from './http'

export interface KbDocument {
  id: string
  name: string
  size: number
  type: string
  status: string
  chunk_count: number
  uploaded_at: string
  uploader: string
}

export interface KbQueryResult {
  question: string
  answer: string
  sources: Array<{ doc_id: string; score: number; snippet?: string }>
  confidence: number
  backend?: string
  queried_at?: string
}

export interface KbStatus {
  status: string
  backend: string
  total_documents: number
  indexed_documents: number
  processing_documents: number
  total_chunks: number
  last_sync: string
}

export async function queryKnowledgeBase(question: string) {
  const { data } = await http.post<ApiEnvelope<KbQueryResult>>('/v1/kb/query', { question })
  if (data.code !== 0) throw new Error(data.message || '知识库检索失败')
  return data.data
}

export async function fetchKbDocuments() {
  const { data } = await http.get<ApiEnvelope<{ documents: KbDocument[]; total: number }>>('/v1/kb/documents')
  if (data.code !== 0) throw new Error(data.message || '文档列表加载失败')
  return data.data
}

export async function fetchKbStatus() {
  const { data } = await http.get<ApiEnvelope<KbStatus>>('/v1/kb/status')
  if (data.code !== 0) throw new Error(data.message || '知识库状态加载失败')
  return data.data
}
