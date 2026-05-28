import { http, type ApiEnvelope } from './http'

export interface TeacherTrial {
  id: number
  class_id: number
  teacher_id: number
  title: string
  trial_type: string
  knowledge_key: string | null
  knowledge_keys?: string[]
  difficulty: number
  notify_students?: boolean
  student_count?: number
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
  knowledge_keys?: string[]
  difficulty?: number
  duration_minutes?: number
  reward_points?: number
  status?: string
  publish_mode?: 'draft' | 'now' | 'scheduled'
  starts_at?: string
  start_delay_minutes?: number
  notify_students?: boolean
}

export interface PublishTrialResult {
  trial: TeacherTrial
  notify_students: boolean
  student_count: number
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

export async function publishTeacherTrial(trialId: number, notifyStudents = true) {
  const { data } = await http.post<ApiEnvelope<PublishTrialResult>>(
    `/v1/teacher/trials/${trialId}/publish`,
    { notify_students: notifyStudents },
  )
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

export interface TrialQuestionStat {
  question_id: number
  sort_order: number
  stem: string
  knowledge_key: string | null
  knowledge_label: string
  answered_count: number
  correct_count: number
  correct_rate: number
  avg_time_spent_sec?: number
}

export interface TrialStudentAnswerRecord {
  question_id: number
  sort_order: number
  stem: string
  knowledge_key: string | null
  knowledge_label: string
  status: string
  selected_index: number | null
  selected_label: string | null
  selected_text: string | null
  correct_index: number
  correct_label: string | null
  is_correct: boolean | null
  started_at: string | null
  answered_at: string | null
  time_spent_sec: number | null
}

export interface TrialStudentProgressRow {
  user_id: number
  username: string
  real_name: string
  participation_status: string | null
  score: number
  answered_count: number
  correct_count: number
  question_total: number
  total_time_spent_sec: number
  joined_at: string | null
  completed_at: string | null
  answers: TrialStudentAnswerRecord[]
}

export interface TeacherTrialDetailResult {
  trial: TeacherTrial
  class_name: string
  teacher_name: string
  questions: Array<{
    id: number
    trial_id: number
    sort_order: number
    stem: string
    options: string[]
    knowledge_key: string | null
    correct_index: number
  }>
  students: TrialStudentProgressRow[]
  summary: {
    question_count: number
    avg_score: number
    completion_rate: number
    question_stats: TrialQuestionStat[]
  }
}

export async function fetchTeacherTrialDetail(trialId: number) {
  const { data } = await http.get<ApiEnvelope<TeacherTrialDetailResult>>(`/v1/teacher/trials/${trialId}`)
  if (data.code !== 0) throw new Error(data.message || '试炼详情加载失败')
  return data.data
}

export interface ClassTrialAnswerBoardTrial {
  trial: TeacherTrial
  summary: TeacherTrialDetailResult['summary']
  students: TrialStudentProgressRow[]
  has_activity: boolean
}

export interface ClassTrialAnswerBoardResult {
  class_id: number
  class_name: string
  student_count: number
  trial_count: number
  active_trial_count: number
  submitted_total: number
  sync_note: string
  trials: ClassTrialAnswerBoardTrial[]
}

export interface StudentTrialAnswerBoardItem {
  trial: TeacherTrial
  participation_status: string | null
  score: number
  answered_count: number
  correct_count: number
  question_total: number
  total_time_spent_sec: number
  joined_at: string | null
  completed_at: string | null
  answers: TrialStudentAnswerRecord[]
}

export interface StudentTrialAnswerBoardResult {
  student_id: number
  username: string
  real_name: string
  class_id: number
  trials: StudentTrialAnswerBoardItem[]
}

export async function fetchClassTrialAnswerBoard(classId: number) {
  const { data } = await http.get<ApiEnvelope<ClassTrialAnswerBoardResult>>(
    `/v1/teacher/classes/${classId}/trial-answers`,
  )
  if (data.code !== 0) throw new Error(data.message || '班级作答数据加载失败')
  return data.data
}

export async function fetchStudentTrialAnswerBoard(studentId: number) {
  const { data } = await http.get<ApiEnvelope<StudentTrialAnswerBoardResult>>(
    `/v1/teacher/students/${studentId}/trial-answers`,
  )
  if (data.code !== 0) throw new Error(data.message || '学生作答数据加载失败')
  return data.data
}
