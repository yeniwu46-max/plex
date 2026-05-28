import { http } from './http'

export interface CodeRunRequest {
  language: string
  code: string
  stdin?: string
}

export interface CodeRunStatus {
  id: number
  description: string
}

export interface CodeRunResult {
  token: string
  status: CodeRunStatus
  stdout: string | null
  stderr: string | null
  compile_output: string | null
  time: string
  memory: number
  language: string
}

export interface TestCaseInput {
  id: string
  label: string
  input?: string
  expected?: string
}

export interface TestCaseResult {
  case_id: string
  label: string
  passed: boolean
  expected: string
  actual: string
  status: CodeRunStatus
  time: string
  memory: number
}

export interface CodeSubmitResult {
  all_passed: boolean
  passed_count: number
  total: number
  results: TestCaseResult[]
  submitted_at: string
}

export interface SupportedLanguage {
  id: number
  name: string
  key: string
}

type ApiEnvelope<T> = { code: number; data: T; msg?: string }

export async function runCode(params: CodeRunRequest): Promise<CodeRunResult> {
  const { data } = await http.post<ApiEnvelope<CodeRunResult>>('/v1/code/run', params)
  if (data.code !== 0) throw new Error(data.msg ?? '代码运行失败')
  return data.data
}

export async function submitCode(params: {
  language: string
  code: string
  test_cases: TestCaseInput[]
}): Promise<CodeSubmitResult> {
  const { data } = await http.post<ApiEnvelope<CodeSubmitResult>>('/v1/code/submit', params)
  if (data.code !== 0) throw new Error(data.msg ?? '代码提交失败')
  return data.data
}

export async function getSubmissionResult(submissionId: string): Promise<CodeRunResult & { submission_id: string }> {
  const { data } = await http.get<ApiEnvelope<CodeRunResult & { submission_id: string }>>(
    `/v1/code/result/${submissionId}`,
  )
  if (data.code !== 0) throw new Error(data.msg ?? '获取提交结果失败')
  return data.data
}

export async function getSupportedLanguages(): Promise<SupportedLanguage[]> {
  const { data } = await http.get<ApiEnvelope<{ languages: SupportedLanguage[] }>>('/v1/code/languages')
  if (data.code !== 0) return []
  return data.data.languages
}

export const CODE_STATUS_LABEL: Record<number, string> = {
  1: '排队中',
  2: '处理中',
  3: '通过',
  4: '答案错误',
  5: '超时',
  6: '编译错误',
  7: '内存超限',
  8: '输出超限',
  9: '运行时错误',
  10: '内部错误',
  11: '运行时错误 (NZEC)',
  13: '禁止操作',
  14: '壁垒超时',
}

export function isAccepted(status: CodeRunStatus) {
  return status.id === 3
}

export function isRuntimeError(status: CodeRunStatus) {
  return [9, 11].includes(status.id)
}

export function isCompileError(status: CodeRunStatus) {
  return status.id === 6
}
