import { formatHttpError, http, type ApiEnvelope } from './http'
import type { TutorContextRequest } from './tutorContext'

export interface VariableSnapshot { values: Record<string, string>; omitted: number }
export interface PythonTrace {
  policy: string
  source_sha256: string
  original_code_sha256: string
  code_normalized: boolean
  python_version: string
  image_id: string
  backend: 'docker'
  evidence_scope: 'self_test'
  timing: 'variables_before_line'
  outcome: 'completed' | 'runtime_error' | 'step_limit' | 'output_limit'
  completed: boolean
  steps: Array<{ line: number; variables: VariableSnapshot }>
  final_variables: VariableSnapshot
  last_line: number
  stdin: string
  stdin_sha256: string
  stdout: string
  error_type: string
  error_message: string
}
export interface PythonTraceResult {
  run_id: string
  code_hash: string
  question_version?: string
  trace: PythonTrace | null
  trace_status: 'recorded' | 'sandbox_limit'
  graded: false
  evidence_scope: 'self_test'
}
export interface TraceCapabilities { enabled: boolean; backend_supported: boolean; max_steps: number }
export type TraceRequest = Omit<TutorContextRequest, 'run_id' | 'code'> & { code: string; stdin: string }

export async function fetchTraceCapabilities(): Promise<TraceCapabilities> {
  const { data } = await http.get<ApiEnvelope<{ execution: { trace?: TraceCapabilities } }>>('/v1/code/languages')
  if (data.code !== 0) throw new Error(data.message || '无法读取执行轨迹状态')
  return data.data.execution?.trace || { enabled: false, backend_supported: false, max_steps: 80 }
}
export async function tracePython(body: TraceRequest): Promise<PythonTraceResult> {
  try {
    const { data } = await http.post<ApiEnvelope<PythonTraceResult>>('/v1/code/trace', body, { timeout: 20000 })
    if (data.code !== 0) throw new Error(data.message || '本次轨迹未完成')
    return data.data
  } catch (error) { throw new Error(formatHttpError(error, '执行轨迹暂不可用，请稍后重试')) }
}
