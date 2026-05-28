import { http, type ApiEnvelope } from './http'
import type { SystemAnnouncement } from './teacherAnnouncements'

export async function fetchAdminAnnouncements() {
  const { data } = await http.get<ApiEnvelope<SystemAnnouncement[]>>('/v1/admin/announcements')
  if (data.code !== 0) throw new Error(data.message || '公告列表加载失败')
  return data.data
}

export async function createAdminAnnouncement(payload: {
  title: string
  body: string
  target_role?: 'teacher' | 'student' | 'all'
}) {
  const { data } = await http.post<ApiEnvelope<SystemAnnouncement>>('/v1/admin/announcements', payload)
  if (data.code !== 0) throw new Error(data.message || '发布公告失败')
  return data.data
}
