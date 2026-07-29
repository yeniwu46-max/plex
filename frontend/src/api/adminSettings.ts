import { http, type ApiEnvelope } from './http'

export interface AdminRulesSettings {
  open_time: string
  daily_limit: string
  difficulty: number
  punish: string
}

export interface AdminToggleItem {
  key: string
  enabled: boolean
}

export interface AdminSettingsPayload {
  rules: AdminRulesSettings
  data_scope: string
  ai_strategies: AdminToggleItem[]
  notices: AdminToggleItem[]
  channels?: Record<string, boolean>
}

export interface AdminSettingsResult {
  class_id: number | null
  scope_class_id: number | null
  settings: AdminSettingsPayload
  updated_at: string | null
}

export async function fetchAdminSettings(classId?: number) {
  const { data } = await http.get<ApiEnvelope<AdminSettingsResult>>('/v1/admin/settings', {
    params: classId ? { class_id: classId } : undefined,
  })
  if (data.code !== 0) throw new Error(data.message || '加载配置失败')
  return data.data
}

export async function saveAdminSettings(settings: Partial<AdminSettingsPayload>, classId?: number) {
  const { data } = await http.put<ApiEnvelope<AdminSettingsResult>>('/v1/admin/settings', {
    class_id: classId,
    settings,
  })
  if (data.code !== 0) throw new Error(data.message || '保存配置失败')
  return data.data
}

export interface WeakKnowledgeTopItem {
  knowledge_key: string
  knowledge_label: string
  fail_count: number
}

export interface AdminDashboardResult {
  metrics: {
    active_students: number
    total_students: number
    active_teachers: number
    running_trials: number
    total_trials: number
    trial_completion_rate: number
    health_score: number
  }
  progress: {
    task_completion_rate: number
    trial_participation_rate: number
    knowledge_mastery_rate: number
    activity_rate: number
  }
  period?: string
  weak_knowledge_top?: WeakKnowledgeTopItem[]
  storage?: {
    total_tb: number
    used_tb: number
    free_tb: number
    used_ratio: number
    unit: string
    breakdown: Array<{ label: string; value_tb: number; count: number }>
    detail: {
      approved_resources: number
      pending_review: number
      resource_tasks: number
      completed_tasks: number
      failed_tasks: number
      participations: number
      progress_answers: number
    }
  }
  alerts?: Array<{
    title: string
    desc: string
    level: string
    tone: string
    time: string
  }>
  resource_operations?: {
    task_count: number
    completed_count: number
    failed_count: number
    success_rate: number
    average_latency_ms: number | null
    fallback_rate: number
    pending_review_count: number
    backend_distribution: Array<{ backend: string; count: number }>
  }
  charts?: {
    activity_trend: {
      x_data: string[]
      submissions: number[]
      passed: number[]
    }
    health_trend?: {
      x_data: string[]
      scores: number[]
    }
    class_completion: Array<{ label: string; rate: number }>
  }
}

export async function fetchAdminDashboard(period: 'today' | 'week' | 'month' = 'month') {
  const { data } = await http.get<ApiEnvelope<AdminDashboardResult>>('/v1/admin/dashboard', {
    params: { period },
  })
  if (data.code !== 0) throw new Error(data.message || '大盘数据加载失败')
  return data.data
}

export interface AdminTrialTeacherItem {
  id: number
  name: string
  username: string
  class_count: number
  running_trials: number
  total_trials: number
}

export interface AdminTrialClassItem {
  id: number
  name: string
  student_count: number
  trial_count: number
  running_trials: number
  completion_rate: number
  avg_score: number
}

export interface AdminClassTrialStats {
  class_id: number
  class_name: string
  trials: Array<{
    id: number
    title: string
    status: string
    participant_count: number
    completion_rate: number
    avg_score: number
    question_stats: Array<{
      question_id: number
      label: string
      correct_rate: number
      correct: number
      total: number
    }>
    student_progress: Array<{
      user_id: number
      name: string
      answered: number
      score: number
      status: string
    }>
  }>
}

export async function fetchAdminTrialTeachers() {
  const { data } = await http.get<ApiEnvelope<{ items: AdminTrialTeacherItem[] }>>(
    '/v1/admin/trials/teachers',
  )
  if (data.code !== 0) throw new Error(data.message || '加载教师列表失败')
  return data.data.items
}

export async function fetchAdminTeacherClasses(teacherId: number) {
  const { data } = await http.get<ApiEnvelope<{ items: AdminTrialClassItem[] }>>(
    `/v1/admin/trials/teachers/${teacherId}/classes`,
  )
  if (data.code !== 0) throw new Error(data.message || '加载班级列表失败')
  return data.data.items
}

export async function fetchAdminClassTrialStats(classId: number) {
  const { data } = await http.get<ApiEnvelope<AdminClassTrialStats>>(
    `/v1/admin/trials/classes/${classId}/stats`,
  )
  if (data.code !== 0) throw new Error(data.message || '加载试炼统计失败')
  return data.data
}
