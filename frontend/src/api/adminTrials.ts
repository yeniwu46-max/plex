import { http, type ApiEnvelope } from './http'
import type { TeacherTrial } from './teacherTrials'

export interface AdminTrialRow extends TeacherTrial {
  class_name: string
  teacher_name: string
  question_count: number
  avg_score: number
}

export interface AdminTrialsResult {
  trials: AdminTrialRow[]
  total: number
}

export async function fetchAdminTrials(classId?: number) {
  const { data } = await http.get<ApiEnvelope<AdminTrialsResult>>('/v1/admin/trials', {
    params: classId ? { class_id: classId } : undefined,
  })
  if (data.code !== 0) throw new Error(data.message || '试炼列表加载失败')
  return data.data
}
