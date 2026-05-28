import { http, type ApiEnvelope } from './http'

export interface StudentInboxNotification {
  id: number
  kind: string
  title: string
  body: string
  trial_id: number | null
  is_read: boolean
  created_at: string | null
}

export interface StudentInboxResult {
  items: StudentInboxNotification[]
  unread_count: number
}

export async function fetchStudentInbox(unreadOnly = true) {
  const { data } = await http.get<ApiEnvelope<StudentInboxResult>>('/v1/student/notifications', {
    params: { unread_only: unreadOnly ? 1 : 0, limit: 30 },
  })
  if (data.code !== 0) throw new Error(data.message || '通知加载失败')
  return data.data
}

export async function markStudentInboxRead(notificationId: number) {
  const { data } = await http.post<ApiEnvelope<StudentInboxNotification>>(
    `/v1/student/notifications/${notificationId}/read`,
  )
  if (data.code !== 0) throw new Error(data.message || '操作失败')
  return data.data
}

export async function markAllStudentInboxRead() {
  const { data } = await http.post<ApiEnvelope<null>>('/v1/student/notifications/read-all')
  if (data.code !== 0) throw new Error(data.message || '操作失败')
}
