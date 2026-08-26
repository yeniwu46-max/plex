import { http, type ApiEnvelope } from './http'

export type EnrollmentStatus = 'pending' | 'approved' | 'rejected'

export interface ClassLookupResult {
  class_id: number
  class_name: string
  teacher_name: string | null
  student_count: number
  join_code: string
  teacher?: {
    id: number
    real_name: string | null
    username: string
    gender: string
    email: string | null
    phone: string | null
    avatar_url: string | null
    status: string
    online: boolean
  } | null
}

export interface ClassEnrollmentRequest {
  id: number
  student_id: number
  student_name: string | null
  student_username: string | null
  class_id: number
  class_name: string | null
  join_code: string | null
  teacher_name: string | null
  status: EnrollmentStatus
  message: string | null
  reviewer_id: number | null
  reviewer_name: string | null
  review_note: string | null
  created_at: string | null
  reviewed_at: string | null
}

export async function lookupClassByCode(joinCode: string) {
  const { data } = await http.post<ApiEnvelope<ClassLookupResult>>('/v1/class-enrollments/lookup', {
    join_code: joinCode,
  })
  if (data.code !== 0) throw new Error(data.message || '班级编号无效')
  return data.data
}

export async function applyToClass(joinCode: string, message?: string) {
  const { data } = await http.post<ApiEnvelope<ClassEnrollmentRequest>>('/v1/class-enrollments/apply', {
    join_code: joinCode,
    message,
  })
  if (data.code !== 0) throw new Error(data.message || '提交申请失败')
  return data.data
}

export async function fetchMyEnrollmentRequests(status?: EnrollmentStatus) {
  const { data } = await http.get<ApiEnvelope<ClassEnrollmentRequest[]>>('/v1/class-enrollments/mine', {
    params: status ? { status } : undefined,
  })
  if (data.code !== 0) throw new Error(data.message || '加载申请记录失败')
  return data.data
}

export async function fetchEnrollmentRequests(params?: { status?: EnrollmentStatus; class_id?: number }) {
  const { data } = await http.get<ApiEnvelope<ClassEnrollmentRequest[]>>('/v1/class-enrollments', {
    params,
  })
  if (data.code !== 0) throw new Error(data.message || '加载入班申请失败')
  return data.data
}

export async function reviewEnrollmentRequest(requestId: number, approve: boolean, note?: string) {
  const { data } = await http.post<ApiEnvelope<ClassEnrollmentRequest>>(
    `/v1/class-enrollments/${requestId}/review`,
    { approve, note },
  )
  if (data.code !== 0) throw new Error(data.message || '审核失败')
  return data.data
}
