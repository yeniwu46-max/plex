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
