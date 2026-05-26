import { http, type ApiEnvelope } from './http'

export interface TeacherTrial {
  id: number
  class_id: number
  teacher_id: number
  title: string
  trial_type: string
  knowledge_key: string | null
  difficulty: number
  duration_minutes: number
  status: 'draft' | 'scheduled' | 'running' | 'ended'
  effective_status?: 'draft' | 'scheduled' | 'running' | 'ended'
  reward_points: number
  starts_at: string | null
  ends_at: string | null
  participant_count?: number
  completed_count?: number
  completion_rate?: number
  progress?: number
}

export interface TeacherTrialSummary {
  running_count: number
  scheduled_count?: number
  draft_count?: number
  participant_count: number
  class_student_count: number
  avg_completion_rate: number
  template_count: number
}

export interface TeacherTrialsResult {
  trials: TeacherTrial[]
  summary: TeacherTrialSummary
}

export interface CreateTrialPayload {
  class_id: number
  title?: string
  trial_type?: string
  knowledge_key?: string | null
  difficulty?: number
  duration_minutes?: number
  reward_points?: number
  status?: string
  publish_mode?: 'draft' | 'now' | 'scheduled'
  starts_at?: string
  start_delay_minutes?: number
}

export async function fetchTeacherTrials(classId: number) {
  const { data } = await http.get<ApiEnvelope<TeacherTrialsResult>>('/v1/teacher/trials', {
    params: { class_id: classId },
  })
  if (data.code !== 0) throw new Error(data.message || '试炼列表加载失败')
  return data.data
}

export async function createTeacherTrial(payload: CreateTrialPayload) {
  const { data } = await http.post<ApiEnvelope<TeacherTrial>>('/v1/teacher/trials', payload)
  if (data.code !== 0) throw new Error(data.message || '创建试炼失败')
  return data.data
}

export async function publishTeacherTrial(trialId: number) {
  const { data } = await http.post<ApiEnvelope<TeacherTrial>>(`/v1/teacher/trials/${trialId}/publish`)
  if (data.code !== 0) throw new Error(data.message || '发布试炼失败')
  return data.data
}

export async function updateTeacherTrial(trialId: number, payload: { status?: string; title?: string }) {
  const { data } = await http.patch<ApiEnvelope<TeacherTrial>>(`/v1/teacher/trials/${trialId}`, payload)
  if (data.code !== 0) throw new Error(data.message || '更新试炼失败')
  return data.data
}

export interface StudentTrialParticipation {
  id: number
  trial_id: number
  user_id: number
  status: string
  score: number
  joined_at: string | null
  completed_at: string | null
  trial: TeacherTrial
}

export interface StudentTrialHistoryResult {
  student_id: number
  participations: StudentTrialParticipation[]
  summary: {
    total: number
    completed: number
    joined: number
    avg_score: number
  }
}

export async function fetchStudentTrialHistory(studentId: number) {
  const { data } = await http.get<ApiEnvelope<StudentTrialHistoryResult>>(
    `/v1/teacher/students/${studentId}/trials`,
  )
  if (data.code !== 0) throw new Error(data.message || '试炼记录加载失败')
  return data.data
}
