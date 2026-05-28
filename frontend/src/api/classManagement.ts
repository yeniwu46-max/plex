import { http, type ApiEnvelope } from './http'
import type { ClassSummary } from './studentManagement'

export interface UpdateClassPayload {
  name?: string
  description?: string
  grade_level?: number | null
}

export async function updateClass(classId: number, payload: UpdateClassPayload) {
  const { data } = await http.put<ApiEnvelope<ClassSummary>>(`/v1/classes/${classId}`, payload)
  if (data.code !== 0) throw new Error(data.message || '班级更新失败')
  return data.data
}

export async function createClassAsAdmin(payload: {
  name: string
  teacher_id: number
  description?: string
  grade_level?: number | null
}) {
  const { data } = await http.post<ApiEnvelope<ClassSummary>>('/v1/classes', payload)
  if (data.code !== 0) throw new Error(data.message || '班级创建失败')
  return data.data
}

export async function deleteClassAsAdmin(classId: number) {
  const { data } = await http.delete<ApiEnvelope<null>>(`/v1/classes/${classId}`)
  if (data.code !== 0) throw new Error(data.message || '班级删除失败')
  return data.data
}
