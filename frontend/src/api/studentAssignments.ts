import { http, type ApiEnvelope } from './http'
import type { AgentTraceSummary } from './agentOrchestration'
import type { CompleteTrialResult, IncentiveFeedbackPayload } from './studentTrials'

export interface CodingMeta {
  starter_code: string
  run_mode: 'stdout' | 'expression'
  hint?: string
  test_cases: Array<{
    id: string
    label: string
    setup?: string
    invoke?: string
    expected: string
  }>
  constraints?: string[]
  examples?: Array<{ input: string; output: string; explain?: string }>
}

export interface TeacherAssignmentItem {
  id: number
  trial_id: number
  trial_title: string
  teacher_name: string
  question_type?: 'mcq' | 'coding'
  knowledge_key: string | null
  knowledge_label: string
  stem: string
  options: string[]
  coding_meta?: CodingMeta | null
  status: 'pending' | 'completed'
  is_correct: boolean | null
  code_passed?: boolean | null
  selected_index: number | null
  submitted_code?: string | null
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
  time_spent_sec?: number
  answered_at?: string | null
  assignments: TeacherAssignmentsResult
  daily: import('./studentOverview').DailyQuestTodayResult | null
  incentive?: IncentiveFeedbackPayload
  trial_complete?: CompleteTrialResult | null
  agent_trace?: AgentTraceSummary
}

export interface SubmitCodeAssignmentResult {
  code_passed: boolean
  passed_count: number
  total: number
  results: Array<{
    case_id?: string
    label: string
    expected: string
    actual: string
    passed: boolean
    error?: string | null
  }>
  time_spent_sec?: number
  answered_at?: string | null
  trial_complete?: CompleteTrialResult | null
  agent_trace?: AgentTraceSummary
}

export async function submitTrialCodeAnswer(questionId: number, code: string, timeSpentSec?: number) {
  const { data } = await http.post<ApiEnvelope<SubmitCodeAssignmentResult>>(
    `/v1/student/assignments/${questionId}/code-submit`,
    { code, time_spent_sec: timeSpentSec },
  )
  if (data.code !== 0) {
    throw new Error(data.message || '代码提交失败')
  }
  return data.data
}

export async function fetchStudentAssignments() {
  const { data } = await http.get<ApiEnvelope<TeacherAssignmentsResult>>('/v1/student/assignments')
  if (data.code !== 0) {
    throw new Error(data.message || '获取教师布置题目失败')
  }
  return data.data
}

export async function submitAssignmentAnswer(
  questionId: number,
  selectedIndex: number,
  timeSpentSec?: number,
) {
  const { data } = await http.post<ApiEnvelope<SubmitAssignmentResult>>(
    `/v1/student/assignments/${questionId}/answer`,
    {
      selected_index: selectedIndex,
      time_spent_sec: timeSpentSec,
    },
  )
  if (data.code !== 0) {
    throw new Error(data.message || '提交答案失败')
  }
  return data.data
}
