import { http, type ApiEnvelope } from './http'

export interface LearnerConcept {
  concept_id: string
  label?: string
  estimate: number | null
  uncertainty: number
  independent_count: number
  independent_success: number
  assisted_count: number
  assisted_success: number
  counterexample_count?: number
  counterexample_success?: number
  counterexample_review_due_at?: string | null
  hints_seen: number
  review_count: number
  review_due_at: string | null
  last_evidence_at: string | null
  stale: boolean
}
export interface LearnerMisconception {
  id: number
  concept_id: string
  kind: string
  label: string
  status: 'candidate' | 'confirmed' | 'mitigated' | 'dismissed'
  revision: number
  distinct_questions: number
  evidence: Array<{ event_id: number; observation: string; question_id: number; occurred_at: string }>
  review_note: string | null
  explanation: string
}
export interface LearningChange {
  event_id: number; version: number; kind: string; reason: string; policy_version: string
  concept_id: string | null; question_title: string | null; question_id: number | null
  evidence_scope: string | null; occurred_at: string; processed_at: string
}
export interface LearningEvidencePage {
  course: string; snapshot_version: number; latest_version: number; limit: number
  items: LearningChange[]; has_more: boolean; next_cursor: string | null
}
export interface LearnerStateSnapshot {
  course: string
  state_version: number
  policy_version: string
  estimate_disclaimer: string
  pending_events: number
  failed_events: number
  concepts: LearnerConcept[]
  misconceptions: LearnerMisconception[]
  changes: LearningChange[]
}
export type MisconceptionReviewAction = 'confirm' | 'dismiss' | 'reopen'
export async function reviewMisconception(studentId: number, misconceptionId: number, body: {
  action: MisconceptionReviewAction; expected_revision: number; request_id: string; note: string
}) {
  const { data } = await http.post<ApiEnvelope<LearnerStateSnapshot>>(
    `/v1/teacher/students/${studentId}/misconceptions/${misconceptionId}/review`, body)
  if (data.code !== 0) throw new Error(data.message || '审核保存失败')
  return data.data
}
export async function fetchLearnerState(studentId?: number): Promise<LearnerStateSnapshot> {
  const path = studentId === undefined ? '/v1/student/learner-state' : `/v1/teacher/students/${studentId}/learner-state`
  const { data } = await http.get<ApiEnvelope<LearnerStateSnapshot>>(path)
  if (data.code !== 0) throw new Error(data.message || '学习证据加载失败')
  return data.data
}
export async function fetchLearningEvidence(studentId: number | undefined, params: {
  cursor?: string; snapshot_version?: number; limit?: number
} = {}): Promise<LearningEvidencePage> {
  const path = studentId === undefined ? '/v1/student/learning-evidence' : `/v1/teacher/students/${studentId}/learning-evidence`
  const { data } = await http.get<ApiEnvelope<LearningEvidencePage>>(path, { params })
  if (data.code !== 0) throw new Error(data.message || '学习历史加载失败')
  return data.data
}
export async function acknowledgeTutorDisplay(receiptId: string) {
  const { data } = await http.post<ApiEnvelope<{ acknowledged: boolean }>>(
    `/v1/student/tutor-responses/${encodeURIComponent(receiptId)}/displayed`, {}, { timeout: 10_000 })
  if (data.code !== 0) throw new Error(data.message || '提示记录同步失败')
  return data.data
}
