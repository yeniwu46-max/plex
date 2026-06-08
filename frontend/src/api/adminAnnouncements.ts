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

export async function updateAdminAnnouncement(
  announcementId: number,
  payload: {
    title?: string
    body?: string
    target_role?: 'teacher' | 'student' | 'all'
  },
) {
  const { data } = await http.patch<ApiEnvelope<SystemAnnouncement>>(
    `/v1/admin/announcements/${announcementId}`,
    payload,
  )
  if (data.code !== 0) throw new Error(data.message || '更新公告失败')
  return data.data
}

export async function deleteAdminAnnouncement(announcementId: number) {
  const { data } = await http.delete<ApiEnvelope<{ deleted: boolean; id: number }>>(
    `/v1/admin/announcements/${announcementId}`,
  )
  if (data.code !== 0) throw new Error(data.message || '删除公告失败')
  return data.data
}
