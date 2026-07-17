import { http, type ApiEnvelope } from './http'
import type { KgEdge, KgNode } from '../data/knowledgeGraphData'

export interface KnowledgeGraphWeakNode {
  id: string
  label: string
  status?: string
  weak_score: number
  fail_count: number
  wrong_count: number
  accuracy?: number | null
  affected_student_count: number
}

export interface KnowledgeGraphSummary {
  top_weak_nodes: KnowledgeGraphWeakNode[]
  student_count: number
  total_mistakes: number
  max_weak_score: number
}

export interface KnowledgeGraphPayload {
  nodes: KgNode[]
  edges: KgEdge[]
  scope: 'student' | 'class' | 'admin'
  user_id?: number
  class_id?: number
  student_count?: number
  graph_backend?: string
  summary?: KnowledgeGraphSummary
  recommended_node_ids?: string[]
}

export async function fetchStudentKnowledgeGraph() {
  const { data } = await http.get<ApiEnvelope<KnowledgeGraphPayload>>('/v1/knowledge-graph/student')
  if (data.code !== 0) throw new Error(data.message || '知识图谱加载失败')
  return data.data
}

export async function fetchStudentKnowledgeGraphById(studentId: number) {
  const { data } = await http.get<ApiEnvelope<KnowledgeGraphPayload>>(
    `/v1/knowledge-graph/student/${studentId}`,
  )
  if (data.code !== 0) throw new Error(data.message || '知识图谱加载失败')
  return data.data
}

export async function fetchClassKnowledgeGraph(classId: number) {
  const { data } = await http.get<ApiEnvelope<KnowledgeGraphPayload>>(
    `/v1/knowledge-graph/class/${classId}`,
  )
  if (data.code !== 0) throw new Error(data.message || '班级知识图谱加载失败')
  return data.data
}

export async function fetchAdminKnowledgeGraph() {
  const { data } = await http.get<ApiEnvelope<KnowledgeGraphPayload>>('/v1/knowledge-graph/admin')
  if (data.code !== 0) throw new Error(data.message || '知识图谱加载失败')
  return data.data
}
