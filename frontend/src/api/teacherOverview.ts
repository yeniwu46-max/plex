import { http, type ApiEnvelope } from './http'

export interface TeacherProfile {
  id: number
  username: string
  real_name: string | null
  role: string | null
}

export interface TeacherClass {
  id: number
  name: string
  description: string | null
  grade_level: number | null
  teacher_id: number
  teacher_name: string | null
  student_count: number
  created_at: string | null
  updated_at: string | null
}

export interface TeacherMetrics {
  student_count: number
  active_count: number
  frozen_count: number
  avg_points: number
  avg_today_completion: number
  attention_count: number
  review_due_students?: number
  reviewed_today_students?: number
  intervention_count?: number
  intervention_resolved_count?: number
  intervention_completion_rate?: number
}

export interface HeatmapCell {
  date: string
  completed: number
  total: number
  rate: number
}

export interface HeatmapRow {
  user_id: number
  student_name: string
  avg_rate: number
  cells: HeatmapCell[]
}

export interface TeacherRankingItem {
  user_id: number
  student_name: string
  username: string
  rank: number
  points: number
  level: number
  week: string
  achievements_count: number
  status: string
}

export interface TeacherStudentRow {
  id: number
  username: string
  real_name: string | null
  status: string
  level: number
  total_points: number
  consecutive_days: number
  achievements_count: number
  rank: number | null
  today_completed: number
  today_total: number
  today_completion_rate: number
  last_activity_at: string | null
  inactive_days: number | null
  is_inactive_7d: boolean
  review_due_count?: number
  reviewed_today?: number
  reasons?: string[]
  weak_domain?: string | null
}

export interface TeacherActivity {
  id: number
  user_id: number
  student_name: string
  points: number
  reason: string | null
  created_at: string | null
}

export interface TeacherOverview {
  teacher: TeacherProfile
  classes: TeacherClass[]
  selected_class: TeacherClass | null
  period: 'week' | 'month'
  metrics: TeacherMetrics
  heatmap: {
    days: Array<{ date: string; label: string }>
    rows: HeatmapRow[]
  }
  ranking: TeacherRankingItem[]
  attention_students: TeacherStudentRow[]
  students: TeacherStudentRow[]
  recent_activity: TeacherActivity[]
}

export async function fetchTeacherOverview(params: { classId?: number | null; period?: 'week' | 'month' }) {
  const { data } = await http.get<ApiEnvelope<TeacherOverview>>('/v1/teacher/overview', {
    params: {
      class_id: params.classId || undefined,
      period: params.period || 'week',
    },
  })
  if (data.code !== 0) {
    throw new Error(data.message || '教师端数据加载失败')
  }
  return data.data
}

export interface TeacherAdaptationTicket {
  adaptation_id: number
  student_id: number
  knowledge_key: string
  status: 'open' | 'in_progress' | 'resolved'
  priority: string
  owner_role: string
  sla_hours: number
  trigger_evidence: Record<string, unknown>
  action_plan: Record<string, unknown>
}

export interface TeacherAdaptationSummary {
  active_interventions: Array<Record<string, unknown>>
  tickets: TeacherAdaptationTicket[]
  risk_level: 'needs_support' | 'stable'
}

export async function fetchStudentAdaptations(studentId: number) {
  const { data } = await http.get<ApiEnvelope<TeacherAdaptationSummary>>(`/v1/teacher/students/${studentId}/learning-adaptations`)
  if (data.code !== 0) throw new Error(data.message || '干预工单加载失败')
  return data.data
}

export async function updateStudentAdaptationTicket(studentId: number, adaptationId: number, status: TeacherAdaptationTicket['status'], note = '') {
  const { data } = await http.patch<ApiEnvelope<Record<string, unknown>>>(
    `/v1/teacher/students/${studentId}/learning-adaptations/${adaptationId}/ticket`,
    { status, note },
  )
  if (data.code !== 0) throw new Error(data.message || '干预工单更新失败')
  return data.data
}

export interface TeacherClassStatsResult {
  domain_mastery: Array<{ label: string; mastery_rate: number }>
  mistake_types: Array<{ name: string; value: number; color: string }>
}

export async function fetchTeacherClassStats(classId?: number | null) {
  const { data } = await http.get<ApiEnvelope<TeacherClassStatsResult>>('/v1/teacher/class-stats', {
    params: { class_id: classId || undefined },
  })
  if (data.code !== 0) throw new Error(data.message || '班级统计加载失败')
  return data.data
}
