import { http, type ApiEnvelope } from './http'

export type StudentStatus = 'active' | 'frozen' | 'deleted'

export interface Student {
  id: number
  username: string
  real_name: string
  email: string
  phone: string | null
  avatar_url: string | null
  role: string | null
  level: number
  total_points: number
  class_id: number | null
  class_name?: string | null
  status: StudentStatus
  created_at: string | null
}

export interface ClassSummary {
  id: number
  name: string
  description: string | null
  grade_level: number | null
  teacher_id: number
  teacher_name: string | null
  student_count: number
}

export interface StudentListParams {
  page: number
  limit: number
  search?: string
  status?: string
  class_id?: number | null
}

export interface StudentListResult {
  total: number
  page: number
  limit: number
  users: Student[]
}

export interface ClassListResult {
  total: number
  page: number
  limit: number
  classes: ClassSummary[]
}

export interface CreateStudentPayload {
  username: string
  email: string
  password: string
  real_name: string
  phone?: string
  gender?: string
  bio?: string
  class_id?: number | null
}

export interface UpdateStudentPayload {
  username: string
  email: string
  real_name: string
  phone?: string
  gender?: string
  bio?: string
  class_id?: number | null
  status?: StudentStatus
}

export async function fetchStudents(params: StudentListParams) {
  const { data } = await http.get<ApiEnvelope<StudentListResult>>('/v1/users', {
    params: {
      page: params.page,
      limit: params.limit,
      role: 'student',
      status: params.status || 'active,frozen',
      search: params.search || undefined,
      class_id: params.class_id || undefined,
    },
  })
  return data
}

export async function createStudent(payload: CreateStudentPayload) {
  const { data } = await http.post<ApiEnvelope<Student>>('/v1/users', payload)
  return data
}

export async function updateStudent(id: number, payload: UpdateStudentPayload) {
  const { data } = await http.put<ApiEnvelope<Student>>(`/v1/users/${id}`, payload)
  return data
}

export async function deleteStudent(id: number) {
  const { data } = await http.delete<ApiEnvelope<null>>(`/v1/users/${id}`)
  return data
}

export async function updateStudentStatus(id: number, status: 'active' | 'frozen') {
  const { data } = await http.patch<ApiEnvelope<null>>(`/v1/users/${id}/status`, { status })
  return data
}

export async function fetchClasses() {
  const { data } = await http.get<ApiEnvelope<ClassListResult>>('/v1/classes', {
    params: { page: 1, limit: 100 },
  })
  return data
}
