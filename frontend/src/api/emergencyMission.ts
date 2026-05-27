import { http, type ApiEnvelope } from './http'
import type { IncentiveFeedbackPayload } from './studentOverview'

export interface EmergencyQuestion {
  id: number
  sort_order: number
  stem: string
  options: string[]
  knowledge_key: string | null
  selected_index: number | null
  is_correct: boolean | null
  correct_index?: number
}

export interface EmergencyMissionSession {
  id: number
  focus_knowledge_key: string
  focus_label: string | null
  status: 'in_progress' | 'submitted'
  correct_count: number
  all_correct: boolean
  reward_points: number
  reward_granted: boolean
  created_at: string | null
  submitted_at: string | null
  questions: EmergencyQuestion[]
}

export interface SubmitEmergencyResult {
  session: EmergencyMissionSession
  incentive?: IncentiveFeedbackPayload
}

export interface EmergencyMissionArchiveRecord {
  id: number
  title: string
  focus_label: string
  date: string | null
  all_correct: boolean
  correct_count: number
  total_count: number
  reward_points: number
  questions: EmergencyQuestion[]
}

export async function startEmergencyMission() {
  const { data } = await http.post<ApiEnvelope<EmergencyMissionSession>>(
    '/v1/student/emergency-missions/start',
  )
  if (data.code !== 0) {
    throw new Error(data.message || '启动紧急任务失败')
  }
  return data.data
}

export async function submitEmergencyMission(
  sessionId: number,
  answers: Array<{ question_id: number; selected_index: number }>,
) {
  const { data } = await http.post<ApiEnvelope<SubmitEmergencyResult>>(
    `/v1/student/emergency-missions/${sessionId}/submit`,
    { answers },
  )
  if (data.code !== 0) {
    throw new Error(data.message || '提交紧急任务失败')
  }
  return data.data
}
