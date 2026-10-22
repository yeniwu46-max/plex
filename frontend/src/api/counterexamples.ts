import { http, type ApiEnvelope } from './http'

export type CounterexampleValue = number | number[] | boolean
export type ValueContract = { type: 'integer' | 'integer_array' | 'boolean'; minimum?: number; maximum?: number; min_items?: number; max_items?: number }
export interface CounterexampleChallenge {
  id: string
  title: string
  statement: string
  concept_id: string
  revision: number
  version: string
  signature: string
  buggy_code: string
  input_contract: ValueContract
  output_contract: ValueContract
  allowed_bug_exceptions: string[]
}
export interface CounterexampleRequest {
  request_id: string
  revision: number
  version: string
  input: CounterexampleValue
  expected_output: CounterexampleValue
  explanation: string
}
export type CounterexampleOutcome = { kind: 'value'; value: CounterexampleValue } | { kind: 'exception'; exception: string }
export interface CounterexampleAttempt extends CounterexampleRequest {
  challenge_id: string
  status: 'processing' | 'complete' | 'material_issue' | 'unavailable' | 'stale'
  created_at: string
  completed_at: string | null
  retryable: boolean
  graded: boolean
  message?: string
  notice?: string
  counterexample_found?: boolean
  expected_output_correct?: boolean
  correct_result?: CounterexampleOutcome
  buggy_result?: CounterexampleOutcome
  evidence_event_id?: number
  explanation_review?: {
    source: 'model' | 'teacher' | 'rules'
    status: 'supported' | 'needs_revision' | 'needs_teacher' | 'not_evaluated'
    feedback: string
    revision: number
    notice: string
  }
}
export type AttemptSummary = Pick<CounterexampleAttempt, 'request_id' | 'status' | 'created_at'>
function unpack<T>(envelope: ApiEnvelope<T>) {
  if (envelope.code !== 0) throw new Error(envelope.message || '无法读取反例挑战')
  return envelope.data
}
export async function fetchCounterexamples(signal?: AbortSignal) {
  return unpack((await http.get<ApiEnvelope<{ items: CounterexampleChallenge[] }>>('/v1/student/counterexample-challenges', { signal })).data).items
}
export async function fetchCounterexample(id: string, signal?: AbortSignal) {
  return unpack((await http.get<ApiEnvelope<CounterexampleChallenge>>(`/v1/student/counterexample-challenges/${encodeURIComponent(id)}`, { signal })).data)
}
export async function fetchCounterexampleAttempts(id: string, signal?: AbortSignal) {
  return unpack((await http.get<ApiEnvelope<{ items: AttemptSummary[] }>>(`/v1/student/counterexample-challenges/${encodeURIComponent(id)}/attempts`, { signal })).data).items
}
export async function fetchCounterexampleAttempt(id: string, signal?: AbortSignal) {
  return unpack((await http.get<ApiEnvelope<CounterexampleAttempt>>(`/v1/student/counterexample-attempts/${encodeURIComponent(id)}`, { signal })).data)
}
export async function submitCounterexample(id: string, body: CounterexampleRequest, signal?: AbortSignal) {
  return unpack((await http.post<ApiEnvelope<CounterexampleAttempt>>(`/v1/student/counterexample-challenges/${encodeURIComponent(id)}/attempts`, body, { signal, timeout: 110000 })).data)
}

export function describeValueContract(contract: ValueContract) {
  if (contract.type === 'boolean') return 'JSON 布尔值 true 或 false'
  const bounds = `每个整数在 ${contract.minimum} 至 ${contract.maximum} 之间`
  return contract.type === 'integer' ? `一个整数，范围 ${contract.minimum} 至 ${contract.maximum}` : `整数数组，长度 ${contract.min_items}–${contract.max_items}，${bounds}`
}
export function parseCounterexampleValue(raw: string, contract: ValueContract): CounterexampleValue {
  if (raw.length > 10000) throw new Error('输入过长，请检查题目允许的范围。')
  let value: unknown
  try { value = JSON.parse(raw) } catch { throw new Error('请使用 JSON 格式，例如整数 3、数组 [1, 2] 或布尔值 true。') }
  const integer = (item: unknown) => typeof item === 'number' && Number.isSafeInteger(item) && item >= contract.minimum! && item <= contract.maximum!
  const valid = contract.type === 'boolean' ? typeof value === 'boolean' : contract.type === 'integer' ? integer(value)
    : Array.isArray(value) && value.length >= contract.min_items! && value.length <= contract.max_items! && value.every(integer)
  if (!valid) throw new Error(`格式不符：${describeValueContract(contract)}。`)
  return value as CounterexampleValue
}
