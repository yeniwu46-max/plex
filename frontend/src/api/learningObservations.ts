import { http, type ApiEnvelope } from './http'

export interface LatencySamples { samples: number; missing: number; p50: number | null; p95: number | null }
export interface LearningObservations {
  policy_version: string
  scope: string
  class_id: number
  window: { days: number; start: string; as_of: string }
  current_students: number
  tutoring_students: number
  flow: {
    requests: number; states: Record<string, number>; published_help: number
    display_confirmed: number; not_display_confirmed: number
  }
  formal_practice: {
    total: number; independent: number; independent_correct: number; assisted: number; assisted_correct: number
  }
  followup: {
    unit: string; days: number; exposures: number; observed: number
    first_correct: number; first_incorrect: number; window_open: number; window_closed_without_observation: number
  }
  latency_ms: {
    method: string; completed_request: LatencySamples; finished_attempt: LatencySamples
    finished_model_call: LatencySamples; model_by_status: Record<string, LatencySamples>
    attempts: number; unfinished_attempts: number; model_calls: number; unfinished_model_calls: number
  }
  limitations: string[]
}

export async function fetchLearningObservations(classId: number, days: 7 | 14 | 30) {
  const { data } = await http.get<ApiEnvelope<LearningObservations>>(
    `/v1/teacher/classes/${classId}/learning-observations`, { params: { days } })
  if (data.code !== 0) throw new Error(data.message || '暂时无法读取学习观察')
  return data.data
}
