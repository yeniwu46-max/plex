import { http, type ApiEnvelope } from './http'
import type { CounterexampleAttempt, CounterexampleOutcome, CounterexampleValue, ValueContract } from './counterexamples'

export interface CounterexampleSpecification {
  title: string; statement: string; concept_id: string; input_contract: ValueContract; output_contract: ValueContract
  reference_code: string; tests: { input: CounterexampleValue; expected: CounterexampleValue }[]
  reference_note: string; allowed_bug_exceptions: string[]; contract_version?: string
  verification?: CounterexampleVerification
}
export type CounterexampleProperty = 'permutation_invariant' | 'duplicate_invariant' | 'append_zero_invariant' | 'concatenation_additive' | 'result_is_member'
export interface CounterexampleVerification {
  policy_version: 'bounded-properties-v1'; boundary_checks: boolean; properties: CounterexampleProperty[]; rationale: string
}
export interface CounterexampleCandidate {
  buggy_code: string; fixed_code: string; bug_kind: 'loop_boundary' | 'empty_input' | 'duplicate_elements'; explanation: string
}
export interface Page<T> { items: T[]; page: number; page_size: number; total: number }
export interface CounterexampleSummary {
  id: string; class_id: number; title: string; revision: number; published_revision: number | null
  blocked_reason: string | null; validation_status: string | null; created_at: string
}
export interface ValidationView {
  id: string; version_id: string; manifest_hash: string; status: 'processing' | 'passed' | 'failed' | 'unavailable' | 'superseded'
  completed_at: string | null
  report: { passed: boolean; reason?: string | null; elapsed_ms?: number; scope?: string
    artifact_hashes?: Record<string, string>
    runtimes?: { program: string; backend: string; python: string; image_id: string | null; harness_hash: string }[]
    witnesses?: { input: CounterexampleValue; buggy: CounterexampleOutcome; reference: CounterexampleOutcome; test_index: number; input_origin?: string }[]
    witness_count?: number; execution_batches?: number
    failure_detail?: { program: string; input: CounterexampleValue; input_origin: string; observed: CounterexampleOutcome; expected: CounterexampleOutcome | null }
    coverage?: { policy_version: string; plan_hash: string; declared_inputs: number; total_inputs: number; boundary_inputs: number; metamorphic_inputs: number
      properties: { property: CounterexampleProperty; program: string; checked: number; failed: number }[]
      failures: { property: CounterexampleProperty; program: string; transform: string; base_input: CounterexampleValue; derived_input: CounterexampleValue | null; base_output: CounterexampleValue; derived_output: CounterexampleValue | null }[] }
  } | null
}
export interface TeacherCounterexample {
  id: string; class_id: number; revision: number; current_revision: number; published_revision: number | null
  version_id: string; manifest_hash: string; spec_id: string; specification: CounterexampleSpecification
  candidate: CounterexampleCandidate; origin: string; validation: ValidationView | null
  source_template?: TemplateReference & { revision: number } | null
  blocked_reason: string | null; material_issues: { attempt_id: string; input: CounterexampleValue; reason: string }[]
  reviewed_report_id: string | null; review_note: string | null
  generation?: { id: string; status: string; stage: string; error_code: string | null; pedagogy_review: GenerationAudit | null } | null
}
export interface TemplateReference { id: string; content_hash: string }
export interface CounterexampleTemplateSummary extends TemplateReference {
  revision: number; title: string; concept_id: string; bug_kind: CounterexampleCandidate['bug_kind']; difficulty: string; objective: string
  human_review_status: 'pending'; provenance: 'ai_assisted_draft'
  development_validation: { passed: boolean; reason: string | null; verified_at: string; report_hash: string; validator_version: string } | null
}
export interface CounterexampleTemplate extends CounterexampleTemplateSummary {
  specification: CounterexampleSpecification; candidate: CounterexampleCandidate
}
export interface CounterexampleCatalog { version: string; catalog_hash: string; items: CounterexampleTemplateSummary[] }
export interface GenerationAudit {
  policy_version: string; provider: string | null; model: string | null; elapsed_ms: number
  token_usage: Record<string, number>; error_code: string | null; raw_output?: string
  verdict?: 'pass' | 'revise' | 'uncertain'; checks?: PublicationChecks; note?: string; quotes?: string[]
  manifest_hash?: string; validation_id?: string
}
export interface CounterexampleGenerationTask {
  id: string; class_id: number; spec_id: string; spec_hash: string; bug_kind: CounterexampleCandidate['bug_kind']
  challenge_id: string; version_id: string | null; validation_id: string
  status: 'queued' | 'running' | 'ready' | 'rejected' | 'failed' | 'cancelled'
  stage: 'generation' | 'validation' | 'pedagogy'; attempts: number; error_code: string | null; retryable: boolean
  created_at: string; completed_at: string | null; generation_audit?: GenerationAudit | null; pedagogy_review?: GenerationAudit | null
  calls?: { id: string; attempt: number; stage: string; audit: GenerationAudit | null; created_at: string; completed_at: string | null }[]
}
export interface VersionSummary { revision: number; created_at: string; origin: string; manifest_hash: string; blocked_reason: string | null; reviewed_report_id: string | null; review_note: string | null }
export interface TeacherAttemptSummary {
  request_id: string; student_id: number; student_name: string; revision: number; status: CounterexampleAttempt['status']
  explanation_status: string | null; explanation_source: string | null; created_at: string
}
export interface TeacherCounterexampleAttempt extends CounterexampleAttempt {
  student_id: number; student_name: string
  task_snapshot: { title: string; statement: string; buggy_code: string; input_contract: ValueContract; output_contract: ValueContract }
  execution_report: Record<string, unknown> | null
  review_history: { revision: number; verdict: string; note: string; reviewer_id: number; created_at: string }[]
}
export type PublicationChecks = Record<'single_clear_bug' | 'statement_consistent' | 'explanation_correct' | 'difficulty_appropriate', boolean>
function unpack<T>(data: ApiEnvelope<T>) { if (data.code !== 0) throw new Error(data.message || '反例工作台请求失败'); return data.data }
async function get<T>(path: string, signal?: AbortSignal) { return unpack((await http.get<ApiEnvelope<T>>('/v1/teacher/'+path, { signal })).data) }
async function post<T>(path: string, body: unknown, signal?: AbortSignal) {
  return unpack((await http.post<ApiEnvelope<T>>('/v1/teacher/'+path, body, { signal, timeout: 110000 })).data)
}
const challengePath = (id: string) => 'counterexample-challenges/'+encodeURIComponent(id)
export const listTeacherCounterexamples = (classId: number, page = 1, signal?: AbortSignal) =>
  get<Page<CounterexampleSummary>>(`counterexample-challenges?class_id=${classId}&page=${page}`, signal)
export const getTeacherCounterexample = (id: string, signal?: AbortSignal, revision?: number) =>
  get<TeacherCounterexample>(challengePath(id)+(revision ? `/versions/${revision}` : ''), signal)
export const getCounterexampleSpecification = (id: string, signal?: AbortSignal) =>
  get<{ id: string; class_id: number; specification: CounterexampleSpecification }>('counterexample-specifications/'+encodeURIComponent(id), signal)
export const getCounterexampleVersions = (id: string, page = 1, signal?: AbortSignal) =>
  get<Page<VersionSummary>>(challengePath(id)+`/versions?page=${page}`, signal)
export const listTeacherCounterexampleAttempts = (id: string, page = 1, signal?: AbortSignal) =>
  get<Page<TeacherAttemptSummary>>(challengePath(id)+`/attempts?page=${page}`, signal)
export const getTeacherCounterexampleAttempt = (id: string, signal?: AbortSignal) =>
  get<TeacherCounterexampleAttempt>('counterexample-attempts/'+encodeURIComponent(id), signal)
export const saveCounterexampleSpecification = (body: { request_id: string; class_id: number; specification: CounterexampleSpecification }, signal?: AbortSignal) =>
  post<{ id: string; content_hash: string }>('counterexample-specifications', body, signal)
export const createCounterexample = (body: { request_id: string; spec_id: string; candidate: CounterexampleCandidate; source_template?: TemplateReference }, signal?: AbortSignal) =>
  post<TeacherCounterexample>('counterexample-challenges', body, signal)
export const reviseCounterexample = (id: string, body: { request_id: string; expected_revision: number; spec_id: string; candidate: CounterexampleCandidate; source_template?: TemplateReference }, signal?: AbortSignal) =>
  post<TeacherCounterexample>(challengePath(id)+'/versions', body, signal)
export const validateCounterexample = (id: string, body: { request_id: string; manifest_hash: string }, signal?: AbortSignal) =>
  post<ValidationView>(challengePath(id)+'/validate', body, signal)
export const publishCounterexample = (id: string, body: { action: 'publish' | 'withdraw'; manifest_hash: string; validation_id?: string; note?: string; checks?: PublicationChecks }, signal?: AbortSignal) =>
  post<TeacherCounterexample>(challengePath(id)+'/review', body, signal)
export const reviewCounterexampleExplanation = (id: string, body: { request_id: string; expected_revision: number; verdict: 'supported' | 'needs_revision'; note: string }, signal?: AbortSignal) =>
  post<TeacherCounterexampleAttempt>('counterexample-attempts/'+encodeURIComponent(id)+'/review', body, signal)

const generationPath = (id: string) => 'counterexample-generation-tasks/'+encodeURIComponent(id)
export const listCounterexampleGenerationTasks = (classId: number, page = 1, signal?: AbortSignal) =>
  get<Page<CounterexampleGenerationTask>>(`counterexample-generation-tasks?class_id=${classId}&page=${page}`, signal)
export const getCounterexampleGenerationTask = (id: string, signal?: AbortSignal) => get<CounterexampleGenerationTask>(generationPath(id), signal)
export const createCounterexampleGenerationTask = (body: { request_id: string; spec_id: string; bug_kind: CounterexampleCandidate['bug_kind'] }, signal?: AbortSignal) =>
  post<CounterexampleGenerationTask>('counterexample-generation-tasks', body, signal)
export const cancelCounterexampleGenerationTask = (id: string, signal?: AbortSignal) => post<CounterexampleGenerationTask>(generationPath(id)+'/cancel', {}, signal)
export const retryCounterexampleGenerationTask = (id: string, expected_attempts: number, signal?: AbortSignal) =>
  post<CounterexampleGenerationTask>(generationPath(id)+'/retry', { expected_attempts }, signal)
export const listCounterexampleTemplates = (classId: number, signal?: AbortSignal) =>
  get<CounterexampleCatalog>(`counterexample-templates?class_id=${classId}`, signal)
export const getCounterexampleTemplate = (classId: number, source: TemplateReference, signal?: AbortSignal) =>
  get<CounterexampleTemplate>(`counterexample-templates/${encodeURIComponent(source.id)}?class_id=${classId}&content_hash=${encodeURIComponent(source.content_hash)}`, signal)
