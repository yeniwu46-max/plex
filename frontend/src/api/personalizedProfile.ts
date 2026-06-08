import { http, type ApiEnvelope } from './http'

export type ProfileDimensionKey =
  | 'major_background'
  | 'knowledge_foundation'
  | 'learning_goal'
  | 'explanation_preference'
  | 'mistake_pattern'
  | 'learning_pace'
  | 'interest_direction'

export interface ProfileDimension {
  value: string | null
  confidence: number
  evidence: string[]
  source: 'conversation' | 'behavior' | 'mixed' | 'confirmed'
}

export interface DynamicStudentProfile {
  user_id: number
  dimensions: Record<ProfileDimensionKey, ProfileDimension>
  completion_rate: number
  version: number
  updated_at?: string | null
}

export interface ProfileChatResult {
  conversation_id: string
  assistant_reply: string
  proposed_changes: Array<{
    dimension: ProfileDimensionKey
    label: string
    old_value?: string | null
    new_value: string
    confidence: number
    evidence: string[]
    requires_confirmation: boolean
  }>
  profile: DynamicStudentProfile
  backend: string
}

export interface ProfileSuggestion {
  id: number
  dimension: ProfileDimensionKey
  proposed_value: string
  evidence: string[]
  source: string
  status: 'pending' | 'accepted' | 'rejected'
  profile_version: number
  created_at?: string | null
}

export async function fetchDynamicProfile() {
  const { data } = await http.get<ApiEnvelope<DynamicStudentProfile>>('/v1/student/profile')
  if (data.code !== 0) throw new Error(data.message || '画像加载失败')
  return data.data
}

export async function chatDynamicProfile(message: string, confirmChanges = false) {
  const { data } = await http.post<ApiEnvelope<ProfileChatResult>>('/v1/student/profile/chat', {
    message,
    confirm_changes: confirmChanges,
  })
  if (data.code !== 0) throw new Error(data.message || '画像分析失败')
  return data.data
}

export async function updateDynamicProfile(changes: Partial<Record<ProfileDimensionKey, string>>) {
  const { data } = await http.put<ApiEnvelope<DynamicStudentProfile>>('/v1/student/profile', {
    changes,
    reason: 'student_correction',
  })
  if (data.code !== 0) throw new Error(data.message || '画像更新失败')
  return data.data
}

export async function fetchProfileSuggestions() {
  const { data } = await http.get<ApiEnvelope<{ items: ProfileSuggestion[]; total: number }>>(
    '/v1/student/profile/suggestions',
  )
  if (data.code !== 0) throw new Error(data.message || '画像建议加载失败')
  return data.data
}

export async function resolveProfileSuggestion(id: number, action: 'accepted' | 'rejected') {
  const { data } = await http.put<
    ApiEnvelope<{ suggestion: ProfileSuggestion; profile: DynamicStudentProfile | null }>
  >(`/v1/student/profile/suggestions/${id}`, { action })
  if (data.code !== 0) throw new Error(data.message || '画像建议处理失败')
  return data.data
}
