import { http, type ApiEnvelope } from './http'

export interface Appearance { visual_style: 'space' | 'comic'; color_mode: 'dark' | 'light' | 'auto' }
export interface ArrivalSummary {
  status: 'pending' | 'completed' | 'skipped' | 'exempt'
  adventurer_number: number | null
  welcome_pending: boolean
  required: boolean
}
export interface SurveyAnswers { age_range?: string; programming_level?: string; field?: string; field_detail?: string }
export interface ArrivalState {
  onboarding: ArrivalSummary
  preferences: Appearance | null
  answers: SurveyAnswers
  draft: SurveyAnswers
  step: number
  survey_version: number
  options: Record<'age_range' | 'programming_level' | 'field', Record<string, string>>
}
async function unwrap<T>(request: Promise<{ data: ApiEnvelope<T> }>) {
  const { data } = await request
  if (data.code !== 0) throw new Error(data.message || '保存失败，请重试')
  return data.data
}
export const fetchArrival = () => unwrap(http.get<ApiEnvelope<ArrivalState>>('/v1/student/onboarding'))
export const saveArrival = (answers: SurveyAnswers, step = 1, preferences?: Appearance, draftOnly = false) => unwrap(http.patch<ApiEnvelope<ArrivalState>>('/v1/student/onboarding', { answers, step, draft_only: draftOnly, ...(preferences ? { preferences } : {}) }))
export const completeArrival = (action: 'submit' | 'skip', answers: SurveyAnswers, preferences: Appearance) => unwrap(http.post<ApiEnvelope<ArrivalState>>('/v1/student/onboarding/complete', { action, answers, preferences }))
export const acknowledgeArrival = () => unwrap(http.post<ApiEnvelope<ArrivalState>>('/v1/student/onboarding/acknowledge', {}))
export const saveAppearance = (appearance: Appearance) => unwrap(http.patch<ApiEnvelope<Appearance>>('/v1/users/me/preferences', appearance))
