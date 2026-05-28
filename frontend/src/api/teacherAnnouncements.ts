import { http, type ApiEnvelope } from './http'

export interface SystemAnnouncement {
  id: number
  title: string
  body: string
  target_role: string
  created_by: number | null
  is_active: boolean
  created_at: string | null
}

export async function fetchTeacherAnnouncements() {
  const { data } = await http.get<ApiEnvelope<SystemAnnouncement[]>>('/v1/teacher/announcements')
  if (data.code !== 0) throw new Error(data.message || '公告加载失败')
  return data.data
}
