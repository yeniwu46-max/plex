import { http, type ApiEnvelope } from './http'

export interface TutorContextRequest {
  submission_id?: string
  question_ref?: string
  formal_question_id?: number
  question_version?: string
  code?: string
  run_id?: string
}

export interface TutorContextView {
  task_source: 'server' | 'browser_only' | 'none'
  local_ref: string | null
  task: {
    ref: string
    title: string
    prompt: string
    version: string
    formal_question_id: number | null
    concept_id: string | null
    tutoring_policy: 'disabled' | 'concept_only' | 'guided'
    max_hint_level: number
  } | null
  code_hash: string
  code_lines: number
  run: { id: string; kind: string; evidence_scope: 'self_test'; created_at: string; code_normalized: boolean } | null
  formal_result: { evidence_scope: 'server_graded'; passed: boolean; at: string | null } | null
  execution_note: string
}

export async function fetchTutorContext(body: TutorContextRequest) {
  const { data } = await http.post<ApiEnvelope<TutorContextView>>('/v1/student/tutor/context', body)
  if (data.code !== 0) throw new Error(data.message || '无法核对辅导上下文')
  return data.data
}
