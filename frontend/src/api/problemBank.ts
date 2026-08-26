import { http, type ApiEnvelope } from './http'

export interface ProblemSample {
  input: string
  output: string
}

export interface ProblemSummary {
  id: number
  problem_no: string
  concept_group: string
  concept: string | null
  title_en: string
  title_cn: string
  difficulty: number | null
  star_difficulty: number | null
}

export interface ConceptGroupOption {
  group: string
  label: string
}

export interface ProblemListResult {
  items: ProblemSummary[]
  total: number
  concept_groups: ConceptGroupOption[]
  active_tag: string | null
}

export type ProblemTagType = 'concept' | 'topic' | 'difficulty' | 'source'

export interface ProblemTag {
  id: number
  code: string
  label: string
  tag_type: ProblemTagType
  color: string | null
}

export interface ProblemDetail {
  id: number
  problem_no: string
  concept: string | null
  concept_group: string
  title_en: string
  title_cn: string
  background: string | null
  description_en: string | null
  description_cn: string | null
  has_english: boolean
  input_format_en: string | null
  output_format_en: string | null
  input_format_cn: string | null
  output_format_cn: string | null
  samples: ProblemSample[]
  notes: string[]
  difficulty: number | null
  level: number | null
  star_difficulty: number | null
  time_limit_ms: number
  time_limit_is_default: boolean
  is_active: boolean
  created_at: string | null
  tags: ProblemTag[]
  reference_answer?: string
  template?: string | null
}

export interface ProblemStatsGroupOption {
  legacy_group_id: number
  legacy_group_name: string | null
}

export interface ProblemStats {
  problem_id: number
  legacy_group_id: number | null
  groups: ProblemStatsGroupOption[]
  submission_count: number
  accepted_count: number
  time_limit_ms: number
  time_limit_is_default: boolean
}

export interface TagListResult {
  items: ProblemTag[]
  by_type: Record<ProblemTagType, ProblemTag[]>
}

export type SubmissionStatus = 'AC' | 'TE' | 'CE' | 'UE'

export interface SubmissionTestCaseResult {
  seq: number
  label: string | null
  output: string
  passed: boolean
}

export interface ProblemSubmissionSummary {
  id: number
  problem_id: number
  legacy_user_id: number
  legacy_username: string | null
  legacy_student_name: string | null
  legacy_group_name: string | null
  status: SubmissionStatus
  is_accepted: boolean
  compile_success: boolean
  test_success: boolean
  score_points: number | null
  score_total: number | null
  score_percent: number | null
  exec_time_ms: number | null
  exec_memory_kb: number | null
  time_spent_seconds: number | null
  self_confidence: number | null
  submitted_at: string | null
}

export interface ProblemSubmissionDetail extends ProblemSubmissionSummary {
  code_content: string
  test_case_results: SubmissionTestCaseResult[]
  raw_judge_output: string | null
  legacy_error_name: string | null
}

export interface SubmissionListResult {
  problem_id: number
  items: ProblemSubmissionSummary[]
  total: number
}

export async function fetchProblemBankList(params?: { concept_group?: string; keyword?: string; tag?: string }) {
  const { data } = await http.get<ApiEnvelope<ProblemListResult>>('/v1/problem-bank/problems', { params })
  if (data.code !== 0) throw new Error(data.message || '题库列表加载失败')
  return data.data
}

export async function fetchProblemBankTags() {
  const { data } = await http.get<ApiEnvelope<TagListResult>>('/v1/problem-bank/tags')
  if (data.code !== 0) throw new Error(data.message || '标签列表加载失败')
  return data.data
}

export async function fetchProblemStats(problemId: number, legacyGroupId?: number | null) {
  const { data } = await http.get<ApiEnvelope<ProblemStats>>(`/v1/problem-bank/problems/${problemId}/stats`, {
    params: legacyGroupId ? { legacy_group_id: legacyGroupId } : undefined,
  })
  if (data.code !== 0) throw new Error(data.message || '题目统计加载失败')
  return data.data
}

export async function fetchProblemBankDetail(problemId: number) {
  const { data } = await http.get<ApiEnvelope<ProblemDetail>>(`/v1/problem-bank/problems/${problemId}`)
  if (data.code !== 0) throw new Error(data.message || '题目详情加载失败')
  return data.data
}

export async function fetchProblemSubmissions(problemId: number, params?: { legacy_user_id?: number; limit?: number }) {
  const { data } = await http.get<ApiEnvelope<SubmissionListResult>>(
    `/v1/problem-bank/problems/${problemId}/submissions`,
    { params },
  )
  if (data.code !== 0) throw new Error(data.message || '提交记录加载失败')
  return data.data
}

export async function fetchSubmissionDetail(submissionId: number) {
  const { data } = await http.get<ApiEnvelope<ProblemSubmissionDetail>>(`/v1/problem-bank/submissions/${submissionId}`)
  if (data.code !== 0) throw new Error(data.message || '提交详情加载失败')
  return data.data
}
