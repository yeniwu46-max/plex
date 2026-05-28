import { http, type ApiEnvelope } from './http'
import type { KnowledgeDomainDef } from '../data/teacherKnowledgeCatalog'

export interface TeacherTrialTemplate {
  id: number
  teacher_id: number
  class_id: number | null
  title: string
  trial_type: string
  knowledge_keys: string[]
  difficulty: number
  duration_minutes: number
  reward_points: number
  created_at: string | null
  updated_at: string | null
}

export interface CreateTemplatePayload {
  title: string
  trial_type?: string
  knowledge_keys: string[]
  class_id?: number | null
  difficulty?: number
  duration_minutes?: number
  reward_points?: number
}

export interface PublishTemplateResult {
  trial: Record<string, unknown>
  notify_students: boolean
  student_count: number
}

export async function fetchKnowledgeCatalog(): Promise<KnowledgeDomainDef[]> {
  const { data } = await http.get<ApiEnvelope<{ domains: KnowledgeDomainDef[] } | KnowledgeDomainDef[]>>(
    '/v1/teacher/knowledge-catalog',
  )
  if (data.code !== 0) throw new Error(data.message || '知识库加载失败')
  const payload = data.data
  if (Array.isArray(payload)) return payload
  return payload?.domains ?? []
}

export async function fetchTeacherTemplates(classId?: number) {
  const { data } = await http.get<ApiEnvelope<TeacherTrialTemplate[]>>('/v1/teacher/templates', {
    params: classId ? { class_id: classId } : undefined,
  })
  if (data.code !== 0) throw new Error(data.message || '模板列表加载失败')
  return data.data
}

export async function createTeacherTemplate(payload: CreateTemplatePayload) {
  const { data } = await http.post<ApiEnvelope<TeacherTrialTemplate>>('/v1/teacher/templates', payload)
  if (data.code !== 0) throw new Error(data.message || '保存模板失败')
  return data.data
}

export async function deleteTeacherTemplate(templateId: number) {
  const { data } = await http.delete<ApiEnvelope<null>>(`/v1/teacher/templates/${templateId}`)
  if (data.code !== 0) throw new Error(data.message || '删除模板失败')
}

export async function publishTeacherTemplate(
  templateId: number,
  classId: number,
  notifyStudents = true,
) {
  const { data } = await http.post<ApiEnvelope<PublishTemplateResult>>(
    `/v1/teacher/templates/${templateId}/publish`,
    { class_id: classId, notify_students: notifyStudents },
  )
  if (data.code !== 0) throw new Error(data.message || '发布作业失败')
  return data.data
}
