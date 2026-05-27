import { http, type ApiEnvelope } from './http'
import type { DailyQuestTodayResult, IncentiveFeedbackPayload } from './studentOverview'

export interface TeacherAssignmentItem {
  id: number
  trial_id: number
  trial_title: string
  teacher_name: string
  knowledge_key: string | null
  knowledge_label: string
  stem: string
  options: string[]
  status: 'pending' | 'completed'
  is_correct: boolean | null
  selected_index: number | null
  sort_order: number
  published_at: string | null
}

export interface TeacherAssignmentsResult {
  pending_count: number
  total_count: number
  items: TeacherAssignmentItem[]
}

export interface SubmitAssignmentResult {
  correct: boolean
  correct_index: number
  assignments: TeacherAssignmentsResult
  daily: DailyQuestTodayResult | null
  incentive?: IncentiveFeedbackPayload
}

export async function fetchStudentAssignments() {
  const { data } = await http.get<ApiEnvelope<TeacherAssignmentsResult>>('/v1/student/assignments')
  if (data.code !== 0) {
    throw new Error(data.message || '获取教师布置题目失败')
  }
  return data.data
}

export async function submitAssignmentAnswer(questionId: number, selectedIndex: number) {
  const { data } = await http.post<ApiEnvelope<SubmitAssignmentResult>>(
    `/v1/student/assignments/${questionId}/answer`,
    { selected_index: selectedIndex },
  )
  if (data.code !== 0) {
    throw new Error(data.message || '提交答案失败')
  }
  return data.data
}
