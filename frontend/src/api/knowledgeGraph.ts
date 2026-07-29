import { formatHttpError, http, type ApiEnvelope } from './http'
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

export interface KnowledgeGraphAffectedStudent {
  id: number
  username: string
  real_name: string
  class_id: number
  class_name: string | null
  fail_count: number
  wrong_count: number
  error_types: Array<{ error_type: string; count: number }>
}

export interface KnowledgeGraphAffectedStudentsResult {
  class_id: number
  class_name: string | null
  node_id: string
  items: KnowledgeGraphAffectedStudent[]
  total: number
}

export async function fetchNodeAffectedStudents(classId: number, nodeId: string) {
  try {
    const { data } = await http.get<ApiEnvelope<KnowledgeGraphAffectedStudentsResult>>(
      `/v1/knowledge-graph/class/${classId}/affected-students`,
      { params: { node_id: nodeId } },
    )
    if (data.code !== 0) throw new Error(data.message || '影响学生列表加载失败')
    return data.data
  } catch (error) {
    throw new Error(formatHttpError(error, '影响学生列表加载失败'))
  }
}

export async function fetchAdminKnowledgeGraph() {
  const { data } = await http.get<ApiEnvelope<KnowledgeGraphPayload>>('/v1/knowledge-graph/admin')
  if (data.code !== 0) throw new Error(data.message || '知识图谱加载失败')
  return data.data
}
