import { http, type ApiEnvelope } from './http'

export interface OnlineStudentItem {
  id: number
  username: string | null
  real_name: string | null
  student_no?: string | null
  avatar_url?: string | null
  last_seen_at?: string | null
}

export interface OnlineStudentsResult {
  class_id: number | null
  online_count: number
  ttl_seconds: number
  updated_at: string
  source?: string
  students: OnlineStudentItem[]
}

export interface TeacherPersonalProfile {
  id: number
  username: string
  real_name: string | null
  gender: string
  email: string | null
  phone: string | null
  avatar_url: string | null
  bio?: string | null
  status: string
  online: boolean
  classes: Array<{
    id: number
    name: string
    student_count: number
    join_code?: string | null
  }>
}

export async function fetchOnlineStudents(classId?: number | null) {
  const { data } = await http.get<ApiEnvelope<OnlineStudentsResult>>('/v1/teacher/online-students', {
    params: classId ? { class_id: classId } : undefined,
  })
  if (data.code !== 0) throw new Error(data.message || '在线名单加载失败')
  return data.data
}

export async function fetchTeacherPersonalProfile() {
  const { data } = await http.get<ApiEnvelope<TeacherPersonalProfile>>('/v1/teacher/profile')
  if (data.code !== 0) throw new Error(data.message || '教师信息加载失败')
  return data.data
}
