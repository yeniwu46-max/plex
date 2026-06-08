import { http, type ApiEnvelope } from './http'
import type { KgEdge, KgNode } from '../data/knowledgeGraphData'

export interface KnowledgeGraphPayload {
  nodes: KgNode[]
  edges: KgEdge[]
  scope: 'student' | 'class' | 'admin'
  user_id?: number
  class_id?: number
  student_count?: number
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
