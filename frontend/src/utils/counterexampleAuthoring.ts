import { parseCounterexampleValue, type ValueContract } from '../api/counterexamples'
import type { CounterexampleCandidate, CounterexampleSpecification, CounterexampleVerification } from '../api/teacherCounterexamples'

export interface AuthoringForm {
  title: string; statement: string; concept_id: string
  input: { type: 'integer' | 'integer_array'; minimum: number; maximum: number; min_items: number; max_items: number }
  output: { type: 'integer' | 'integer_array' | 'boolean'; minimum: number; maximum: number; min_items: number; max_items: number }
  reference_code: string; reference_note: string; allowed_bug_exceptions: string[]
  tests: { input: string; expected: string }[]
  candidate: CounterexampleCandidate
  supplementary: boolean; verification: CounterexampleVerification
}
export function blankCounterexampleForm(): AuthoringForm {
  return { title: '', statement: '', concept_id: '',
    input: { type: 'integer_array', minimum: -10, maximum: 10, min_items: 0, max_items: 10 },
    output: { type: 'integer', minimum: -100, maximum: 100, min_items: 0, max_items: 10 },
    reference_code: '', reference_note: '', allowed_bug_exceptions: [], supplementary: true,
    verification: { policy_version: 'bounded-properties-v1', boundary_checks: true, properties: [], rationale: '' },
    tests: Array.from({ length: 3 }, () => ({ input: '', expected: '' })),
    candidate: { buggy_code: '', fixed_code: '', bug_kind: 'loop_boundary', explanation: '' } }
}
export function formFromCounterexample(specification: CounterexampleSpecification, candidate?: CounterexampleCandidate): AuthoringForm {
  const form = blankCounterexampleForm()
  return { ...form, title: specification.title, statement: specification.statement, concept_id: specification.concept_id,
    input: { ...form.input, ...specification.input_contract } as AuthoringForm['input'],
    output: { ...form.output, ...specification.output_contract }, reference_code: specification.reference_code,
    reference_note: specification.reference_note, allowed_bug_exceptions: [...specification.allowed_bug_exceptions],
    tests: specification.tests.map(test => ({ input: JSON.stringify(test.input), expected: JSON.stringify(test.expected) })),
    supplementary: !!specification.verification,
    verification: specification.verification ? { ...specification.verification, properties: [...specification.verification.properties] } : form.verification,
    candidate: candidate ? { ...candidate } : form.candidate }
}
function text(value: string, label: string, limit: number) {
    if (!value.trim() || value.length > limit) throw new Error(`${label}需填写 1–${limit} 字。`)
    return value.trim()
}
export function buildCounterexampleSpecification(form: AuthoringForm) {
  function contract(raw: AuthoringForm['output'], output: boolean): ValueContract {
    if (raw.type === 'boolean') return { type: 'boolean' }
    const bound = output ? 1e12 : 1e6
    if (![raw.minimum, raw.maximum].every(Number.isSafeInteger) || raw.minimum < -bound || raw.maximum > bound || raw.maximum < raw.minimum)
      throw new Error(`${output ? '输出' : '输入'}数值范围不合法。`)
    const value: ValueContract = { type: raw.type, minimum: raw.minimum, maximum: raw.maximum }
    if (raw.type === 'integer_array') {
      if (![raw.min_items, raw.max_items].every(Number.isSafeInteger) || raw.min_items < 0 || raw.max_items > 128 || raw.max_items < raw.min_items)
        throw new Error('数组长度须为 0–128 范围内的有效区间。')
      value.min_items = raw.min_items; value.max_items = raw.max_items
    }
    return value
  }
  const input = contract(form.input, false), output = contract(form.output, true)
  if (form.tests.length < 3 || form.tests.length > 24) throw new Error('需填写 3–24 个独立测试。')
  const tests = form.tests.map((test, index) => {
    try { return { input: parseCounterexampleValue(test.input, input), expected: parseCounterexampleValue(test.expected, output) } }
    catch (cause) { throw new Error(`测试 ${index+1}：${cause instanceof Error ? cause.message : '格式不符'}`) }
  })
  if (new Set(tests.map(test => JSON.stringify(test.input))).size !== tests.length) throw new Error('独立测试的输入不能重复。')
  const specification: CounterexampleSpecification = { title: text(form.title, '标题', 120), statement: text(form.statement, '题意', 4000),
    concept_id: text(form.concept_id, '知识点', 80), input_contract: input, output_contract: output,
    reference_code: text(form.reference_code, '参考实现', 16000), reference_note: text(form.reference_note, '独立核对说明', 1500),
    allowed_bug_exceptions: [...form.allowed_bug_exceptions], tests }
  if (form.supplementary) {
    const verify = form.verification
    if (!verify.boundary_checks && !verify.properties.length) throw new Error('补充验证至少启用边界检查或一项适用性质。')
    if (verify.properties.length && input.type !== 'integer_array') throw new Error('当前性质检查适用于整数数组输入。')
    if (verify.properties.some(key => ['result_is_member','concatenation_additive'].includes(key)) && output.type !== 'integer')
      throw new Error('结果来自输入和拼接可加性要求整数输出。')
    if (verify.boundary_checks && input.type === 'integer_array' && input.min_items === 0 && !tests.some(test => Array.isArray(test.input) && test.input.length === 0))
      throw new Error('允许空数组时，请先为 [] 填写独立预期测试。')
    specification.verification = { policy_version: 'bounded-properties-v1', boundary_checks: verify.boundary_checks,
      properties: [...verify.properties], rationale: text(verify.rationale, '补充验证依据', 1000) }
  }
  return specification
}
export function buildCounterexampleDraft(form: AuthoringForm) {
  const specification = buildCounterexampleSpecification(form)
  const candidate: CounterexampleCandidate = { bug_kind: form.candidate.bug_kind,
    buggy_code: text(form.candidate.buggy_code, '错误程序', 16000), fixed_code: text(form.candidate.fixed_code, '修正程序', 16000),
    explanation: text(form.candidate.explanation, '错误说明', 3000) }
  return { specification, candidate }
}
