import { http, type ApiEnvelope } from './http'

export interface LearningResourceItem {
  id: number
  knowledge_key: string
  type: string
  title: string
  content_ref: string
  difficulty: number
  is_active?: boolean
}

export interface LearningResourcesResult {
  knowledge_key?: string | null
  knowledge_label?: string
  items: LearningResourceItem[]
  total?: number
}

export async function fetchStudentLearningResources(knowledgeKey?: string) {
  const { data } = await http.get<ApiEnvelope<LearningResourcesResult>>('/v1/student/learning-resources', {
    params: knowledgeKey ? { knowledge_key: knowledgeKey } : undefined,
  })
  if (data.code !== 0) throw new Error(data.message || '资源加载失败')
  return data.data
}

export async function fetchAdminLearningResources() {
  const { data } = await http.get<ApiEnvelope<LearningResourcesResult>>('/v1/admin/learning-resources')
  if (data.code !== 0) throw new Error(data.message || '资源列表加载失败')
  return data.data
}
