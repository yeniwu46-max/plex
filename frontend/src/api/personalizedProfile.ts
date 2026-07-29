import { http, type ApiEnvelope } from './http'
import { postSseStream } from './sse'

export type ProfileDimensionKey =
  | 'major_background'
  | 'knowledge_foundation'
  | 'learning_goal'
  | 'explanation_preference'
  | 'mistake_pattern'
  | 'learning_pace'
  | 'interest_direction'
  | 'cognitive_state'

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

export interface LearningAdaptation {
  id: number
  knowledge_key: string
  status: 'active' | 'recovered'
  trigger_evidence: { rule?: string }
  action_plan: { action: string; difficulty: string; resources: string[]; micro_practice_count: number; recovery_rule: string }
}

export type OnboardingQuestionType = 'single_choice' | 'scenario' | 'code_reading' | 'true_false' | 'fill_blank'
export interface OnboardingDiagnosticQuestion { id: string; knowledge_key: string; question_type?: OnboardingQuestionType; stem: string; options: string[]; code_preview?: string | null }

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

/** SSE 流式画像对话：阶段回调 + 逐 token 回复，返回完整抽取结果。 */
export async function streamProfileChat(
  message: string,
  confirmChanges: boolean,
  onDelta: (text: string) => void,
  onStage?: (stage: string, label: string) => void,
  signal?: AbortSignal,
): Promise<ProfileChatResult> {
  const controller = new AbortController()
  const onExternalAbort = () => controller.abort()
  signal?.addEventListener('abort', onExternalAbort)
  const timer = window.setTimeout(() => controller.abort(), 30_000)
  try {
    const done = await postSseStream(
      '/v1/student/profile/chat/stream',
      { message, confirm_changes: confirmChanges },
      { onDelta, onStage, signal: controller.signal },
    )
    const result = done?.result as ProfileChatResult | undefined
    if (!result) throw new Error('画像分析流意外结束，请重试')
    return result
  } catch (error) {
    if (controller.signal.aborted && !signal?.aborted) {
      throw new Error('画像对话超时，请重试')
    }
    throw error
  } finally {
    window.clearTimeout(timer)
    signal?.removeEventListener('abort', onExternalAbort)
  }
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

export async function fetchProfileDiagnostic() {
  const { data } = await http.get<ApiEnvelope<{ questions: OnboardingDiagnosticQuestion[]; diagnostic: { status: string } }>>('/v1/student/profile/diagnostic')
  if (data.code !== 0) throw new Error(data.message || '入门测验加载失败')
  return data.data
}

export async function submitProfileDiagnostic(answers: Record<string, number>, skip = false) {
  const { data } = await http.post<ApiEnvelope<{ profile: DynamicStudentProfile }>>('/v1/student/profile/diagnostic', { answers, skip })
  if (data.code !== 0) throw new Error(data.message || '入门测验提交失败')
  return data.data
}

export async function fetchLearningAdaptations() {
  const { data } = await http.get<ApiEnvelope<{ items: LearningAdaptation[] }>>('/v1/student/profile/adaptations')
  if (data.code !== 0) throw new Error(data.message || '自适应方案加载失败')
  return data.data.items
}
