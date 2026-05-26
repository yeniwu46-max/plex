import { http, type ApiEnvelope } from './http'

export interface StudentTrial {
  id: number
  title: string
  trial_type: string
  knowledge_key: string | null
  difficulty: number
  duration_minutes: number
  status: string
  effective_status?: string
  reward_points: number
  participant_count?: number
  completion_rate?: number
  my_status: string | null
  my_score: number
}

export interface StudentTrialsResult {
  trials: StudentTrial[]
}

export interface IncentiveFeedbackPayload {
  level_up?: boolean
  level?: number
  title?: string
  points_gained?: number
  class_rank?: number | null
  unlocked_achievements?: Array<{ name: string; rarity?: string }>
}

export interface CompleteTrialResult {
  participation: { status: string; score: number }
  trial: { title: string; reward_points: number }
  total_points: number
  incentive?: IncentiveFeedbackPayload
}

export async function fetchStudentTrials() {
  const { data } = await http.get<ApiEnvelope<StudentTrialsResult>>('/v1/student/trials')
  if (data.code !== 0) throw new Error(data.message || '试炼列表加载失败')
  return data.data
}

export async function fetchStudentArenaTrials() {
  const { data } = await http.get<ApiEnvelope<StudentTrialsResult>>('/v1/student/trials/arena')
  if (data.code !== 0) throw new Error(data.message || '试炼场数据加载失败')
  return data.data
}

export async function joinStudentTrial(trialId: number) {
  const { data } = await http.post<ApiEnvelope<unknown>>(`/v1/student/trials/${trialId}/join`)
  if (data.code !== 0) throw new Error(data.message || '参与试炼失败')
  return data.data
}

export async function completeStudentTrial(trialId: number, score?: number) {
  const { data } = await http.post<ApiEnvelope<CompleteTrialResult>>(`/v1/student/trials/${trialId}/complete`, {
    score,
  })
  if (data.code !== 0) throw new Error(data.message || '完成试炼失败')
  return data.data
}
