import { loadBrowserCrypto } from './helpers/browser-crypto.mjs'
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import ts from 'typescript'
import * as vue from 'vue'

function compiled(path, modules, globals = {}) {
  const source = readFileSync(new URL(path, import.meta.url), 'utf8')
  const code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText
  const exports = {}
  vm.runInNewContext(code, { exports, console, AbortController, ...globals, require: name => {
      if (name.endsWith('/browserCrypto')) return loadBrowserCrypto(globals.crypto)
 assert.ok(name in modules, name); return modules[name] } })
  return exports
}
const values = compiled('../src/api/counterexamples.ts', { './http': {} })
const authoring = compiled('../src/utils/counterexampleAuthoring.ts', { '../api/counterexamples': values })
const spec = { title: '求和', statement: '求整数数组之和，空数组为 0。', concept_id: 'loop-for',
  input_contract: { type: 'integer_array', minimum: -10, maximum: 10, min_items: 0, max_items: 10 },
  output_contract: { type: 'integer', minimum: -100, maximum: 100 }, reference_code: 'def solve(data):\n    return sum(data)',
  tests: [{ input: [], expected: 0 }, { input: [1], expected: 1 }, { input: [1,2], expected: 3 }], reference_note: '逐项人工推算', allowed_bug_exceptions: [], contract_version: 'counterexample-v1' }
const candidate = { buggy_code: 'def solve(data):\n    return sum(data[:-1])', fixed_code: spec.reference_code, bug_kind: 'loop_boundary', explanation: '遗漏最后一项' }
const row = { id: 'challenge-1', class_id: 1, revision: 1, current_revision: 1, published_revision: null,
  spec_id: 'spec-1', manifest_hash: 'hash-1', specification: spec, candidate, validation: null, blocked_reason: null, material_issues: [] }
const page = { items: [], page: 1, page_size: 20, total: 0 }
const template = { id: 'L01', content_hash: 'frozen-hash', revision: 1, specification: spec, candidate,
  title: spec.title, bug_kind: 'loop_boundary', human_review_status: 'pending', provenance: 'ai_assisted_draft' }
const clone = value => JSON.parse(JSON.stringify(value))
function deferred() { let resolve, reject; const promise = new Promise((r,j) => { resolve=r; reject=j }); return { promise, resolve, reject } }
function harness(overrides = {}, saved = new Map()) {
  const user = vue.ref(1), cohort = vue.ref(1), unmount = [], calls = []
  let serial = 0
  const methods = {
    listTeacherCounterexamples: async () => page,
    getTeacherCounterexample: async () => clone(row),
    getCounterexampleSpecification: async () => ({ id: 'spec-1', class_id: 1, specification: clone(spec) }),
    getCounterexampleVersions: async () => page, listTeacherCounterexampleAttempts: async () => page,
    saveCounterexampleSpecification: async body => ({ id: body.request_id }),
    createCounterexample: async () => clone(row), reviseCounterexample: async () => ({ ...clone(row), revision: 2, current_revision: 2 }),
    validateCounterexample: async () => ({ id: 'validation-1', status: 'passed' }),
    publishCounterexample: async () => ({ ...clone(row), published_revision: 1 }),
    getTeacherCounterexampleAttempt: async () => ({}), reviewCounterexampleExplanation: async () => ({}),
    listCounterexampleTemplates: async () => ({ version: 'counterexample-catalog-v1', items: [clone(template)] }),
    getCounterexampleTemplate: async () => clone(template),
    ...overrides,
  }
  const api = Object.fromEntries(Object.entries(methods).map(([name, method]) => [name, (...args) => {
    calls.push({ name, args: args.map(arg => arg instanceof AbortSignal ? arg : clone(arg ?? null)) }); return method(...args)
  }]))
  const mod = compiled('../src/composables/useCounterexampleWorkbench.ts', {
    vue: { ...vue, onBeforeUnmount: fn => unmount.push(fn) }, axios: { isAxiosError: error => error?.isAxiosError === true },
    '../api/teacherCounterexamples': api, '../utils/counterexampleAuthoring': authoring,
  }, { crypto: { randomUUID: () => `uuid-${++serial}` }, localStorage: {
    getItem: key => saved.get(key), setItem: (key, value) => saved.set(key,value), removeItem: key => saved.delete(key),
  } })
  const scope = vue.effectScope(), state = scope.run(() => mod.useCounterexampleWorkbench(user, cohort))
  return { state, user, cohort, calls, saved, close() { unmount.forEach(fn => fn()); scope.stop() } }
}
async function settle() { for (let i=0;i<16;i++) await Promise.resolve(); await vue.nextTick() }
function fill(state) { state.form.value = authoring.formFromCounterexample(spec, candidate); state.approvedBasis.value = true }

test('authoring strips server-only contract version and checks independent input/output pairs', () => {
  const form = authoring.formFromCounterexample(spec, candidate)
  const draft = authoring.buildCounterexampleDraft(form)
  assert.equal('contract_version' in draft.specification, false)
  form.tests[2].input = '[1]'; assert.throws(() => authoring.buildCounterexampleDraft(form), /不能重复/)
  form.tests[2].input = '[true]'; assert.throws(() => authoring.buildCounterexampleDraft(form), /格式不符/)
})

test('legacy edits preserve their original contract while new supplementary checks need teacher rationale', () => {
  const form = authoring.formFromCounterexample(spec, candidate)
  assert.equal(form.supplementary, false)
  assert.equal('verification' in authoring.buildCounterexampleDraft(form).specification, false)
  form.supplementary = true
  assert.throws(() => authoring.buildCounterexampleDraft(form), /补充验证依据/)
  form.verification.rationale = '求和与排列顺序无关，加入零不改变结果。'
  form.verification.properties = ['permutation_invariant', 'append_zero_invariant']
  const saved = authoring.buildCounterexampleDraft(form).specification
  assert.equal(saved.verification.policy_version, 'bounded-properties-v1')
  const restored = authoring.formFromCounterexample(saved, candidate)
  restored.verification.properties.push('result_is_member')
  assert.equal(saved.verification.properties.length, 2)
  assert.equal(restored.supplementary, true)
})

test('boundary checks require an independently stated empty result and compatible property output type', () => {
  const form = authoring.formFromCounterexample(spec, candidate)
  form.supplementary = true; form.verification.rationale = '核对空输入和最大合法长度。'
  form.tests[0] = { input:'[3]',expected:'3' }
  assert.throws(() => authoring.buildCounterexampleSpecification(form), /\[\]/)
  form.tests[0] = { input:'[]',expected:'0' }
  form.output.type = 'boolean'; form.tests.forEach(test => { test.expected='true' })
  form.verification.properties = ['result_is_member']
  assert.throws(() => authoring.buildCounterexampleSpecification(form), /整数输出/)
})

test('model candidates require a matching completed teaching audit even with all manual checks', async () => {
  const current={...clone(row),origin:'model_generated',validation:{id:'validation',status:'passed',manifest_hash:row.manifest_hash,report:{passed:true}},
    generation:{status:'running',pedagogy_review:null}}
  const h=harness({getTeacherCounterexample:async()=>clone(current)})
  try {
    await settle();await h.state.select(row.id)
    for(const key in h.state.checks.value) h.state.checks.value[key]=true
    h.state.reviewNote.value='人工核对完成'
    assert.equal(h.state.canPublish.value,false)
    h.state.detail.value.generation={status:'ready',pedagogy_review:{verdict:'pass',manifest_hash:row.manifest_hash,validation_id:'different'}}
    assert.equal(h.state.canPublish.value,false)
    h.state.detail.value.generation.pedagogy_review.validation_id='validation'
    assert.equal(h.state.canPublish.value,true)
  } finally {h.close()}
})
test('save requires explicit basis review and sends nothing for an invalid draft', async () => {
  const h=harness()
  try {
    await settle(); h.state.newDraft(); await h.state.save()
    assert.ok(h.state.error.value); assert.equal(h.calls.filter(c=>c.name==='saveCounterexampleSpecification').length,0)
    h.state.approvedBasis.value=true; await h.state.save()
    assert.equal(h.calls.filter(c=>c.name==='saveCounterexampleSpecification').length,0)
  } finally { h.close() }
})
test('uncertain create retries exactly the original UUIDs and payload, without publishing', async () => {
  let count=0
  const h=harness({ createCounterexample: async () => { if (++count===1) throw new Error('lost response'); return clone(row) } })
  try {
    await settle(); h.state.newDraft(); fill(h.state); await h.state.save()
    assert.ok(h.state.pendingSave.value)
    h.state.form.value.candidate.buggy_code='changed while offline'; await h.state.save()
    const sends=h.calls.filter(c=>c.name==='createCounterexample')
    assert.deepEqual(sends[0].args[0],sends[1].args[0])
    const bases=h.calls.filter(c=>c.name==='saveCounterexampleSpecification')
    assert.deepEqual(bases[0].args[0],bases[1].args[0]); assert.equal(h.state.editing.value,false)
    assert.equal(h.calls.some(c=>c.name==='publishCounterexample'),false)
    assert.ok([...h.saved.values()].every(value=>!value.includes('solve')&&!value.includes('tests')))
  } finally { h.close() }
})
test('changing class during basis save aborts the pending action before candidate creation', async () => {
  const held=deferred(), h=harness({ saveCounterexampleSpecification:()=>held.promise })
  try {
    await settle(); h.state.newDraft(); fill(h.state); const saved=h.state.save()
    const call=h.calls.find(c=>c.name==='saveCounterexampleSpecification')
    h.cohort.value=2; await settle(); assert.equal(call.args.at(-1).aborted,true)
    held.resolve({id:'old-spec'}); await saved
    assert.equal(h.calls.some(c=>c.name==='createCounterexample'),false); assert.equal(h.state.detail.value,null)
    assert.equal(h.saved.has('plex:counterexample-author:1:2'),false)
  } finally { h.close() }
})
test('known completed verification can be rerun, but publishing still needs all checks', async () => {
  const current={...clone(row),validation:{id:'old-validation',status:'passed',manifest_hash:row.manifest_hash,report:{passed:true}}}
  const h=harness({getTeacherCounterexample:async()=>clone(current)},new Map([['plex:counterexample-author:1:1',JSON.stringify({challengeId:row.id,validationHash:row.manifest_hash,validationId:'old-validation'})]]))
  try {
    await settle(); assert.equal(h.state.canPublish.value,false)
    await h.state.validate(); const sent=h.calls.find(c=>c.name==='validateCounterexample')
    assert.notEqual(sent.args[1].request_id,'old-validation')
    Object.keys(h.state.checks.value).forEach(key=>h.state.checks.value[key]=true); h.state.reviewNote.value='全部核对'
    assert.equal(h.state.canPublish.value,true); h.state.edit(); assert.equal(h.state.canPublish.value,false)
    await h.state.publish('publish'); assert.equal(h.calls.some(c=>c.name==='publishCounterexample'),false)
  } finally { h.close() }
})
test('historical versions cannot be edited, validated or published', async () => {
  const h=harness({getTeacherCounterexample:async()=>({...clone(row),current_revision:2})})
  try {
    await settle(); await h.state.select(row.id,1); h.state.edit(); await h.state.validate(); await h.state.publish('withdraw')
    assert.equal(h.state.editing.value,false); assert.equal(h.calls.some(c=>['validateCounterexample','publishCounterexample'].includes(c.name)),false)
  } finally { h.close() }
})
test('refresh can recover an approved basis when candidate creation never finished', async () => {
  const h=harness({getTeacherCounterexample:async()=>{throw {isAxiosError:true,response:{status:404}}}},
    new Map([['plex:counterexample-author:1:1',JSON.stringify({challengeId:'unfinished-id',specId:'saved-spec'})]]))
  try {
    await settle(); assert.equal(h.state.editing.value,true); assert.equal(h.state.form.value.reference_code,spec.reference_code)
    assert.equal(h.state.form.value.candidate.buggy_code,''); fill(h.state); await h.state.save()
    assert.equal(h.calls.find(c=>c.name==='createCounterexample').args[0].request_id,'unfinished-id')
  } finally { h.close() }
})
test('explanation review retries its own request and an account switch discards late results', async () => {
  const attempt={request_id:'attempt-1',challenge_id:row.id,status:'complete',explanation_review:{revision:0}}
  let count=0; const held=deferred()
  const h=harness({getTeacherCounterexampleAttempt:async()=>clone(attempt),reviewCounterexampleExplanation:async()=>{
    if (++count===1) throw new Error('lost'); return held.promise
  }})
  try {
    await settle(); await h.state.select(row.id); await h.state.readAttempt('attempt-1'); h.state.explanationNote.value='遗漏末尾元素，依据明确。'
    await h.state.reviewExplanation('supported'); const retry=h.state.reviewExplanation('supported')
    const sends=h.calls.filter(c=>c.name==='reviewCounterexampleExplanation'); assert.deepEqual(sends[0].args[1],sends[1].args[1])
    h.user.value=2; await settle(); held.resolve({...attempt,explanation_review:{revision:1}}); await retry
    assert.equal(h.state.selectedAttempt.value,null)
  } finally { h.close() }
})


test('loading a frozen draft resets approval and writes no server state or program cache', async () => {
  const h=harness()
  try {
    await settle(); await h.state.loadTemplates()
    assert.equal(h.state.templates.value.items.length,1)
    h.state.approvedBasis.value=true; await h.state.loadTemplate(template)
    assert.equal(h.state.editing.value,true); assert.equal(h.state.approvedBasis.value,false)
    assert.equal(h.state.sourceTemplate.value.id,'L01'); assert.equal(h.state.canPublish.value,false)
    assert.equal(h.state.form.value.candidate.buggy_code,candidate.buggy_code)
    assert.equal(h.calls.some(c=>/^(save|create|revise|validate|publish)/.test(c.name)),false)
    assert.equal(h.saved.size,0)
    h.state.discardEdit(); assert.equal(h.state.sourceTemplate.value,null)
    h.state.newDraft(); assert.equal(h.state.sourceTemplate.value,null)
  } finally {h.close()}
})

test('catalog loading ignores a late response after class switch', async () => {
  const held=deferred(), h=harness({getCounterexampleTemplate:()=>held.promise})
  try {
    await settle(); const load=h.state.loadTemplate(template)
    const sent=h.calls.find(c=>c.name==='getCounterexampleTemplate')
    h.cohort.value=2; await settle(); assert.equal(sent.args.at(-1).aborted,true)
    held.resolve(clone(template)); await load
    assert.equal(h.state.sourceTemplate.value,null); assert.equal(h.state.editing.value,false)
    assert.equal(h.state.templates.value,null)
  } finally {h.close()}
})

test('a newly selected task never inherits another task history when related reads fail', async () => {
  const held = deferred()
  const second = { ...clone(row), id: 'challenge-2', spec_id: 'spec-2' }
  const h = harness({
    getTeacherCounterexample: async id => clone(id === second.id ? second : row),
    getCounterexampleVersions: async id => id === second.id ? held.promise : { ...page, items: [{ revision: 1 }], total: 1 },
    listTeacherCounterexampleAttempts: async id => ({ ...page, items: [{ request_id: `attempt-${id}` }], total: 1 }),
  })
  try {
    await settle(); await h.state.select(row.id)
    assert.equal(h.state.attempts.value.items.length, 1)
    const switching = h.state.select(second.id)
    await settle()
    assert.equal(h.state.detail.value.id, second.id)
    assert.equal(h.state.versions.value.items.length, 0)
    assert.equal(h.state.attempts.value.items.length, 0)
    held.reject(new Error('history unavailable')); await switching
    assert.equal(h.state.attempts.value.total, 0)
    assert.equal(h.state.error.value, '请求未完成，请重试。')
  } finally { h.close() }
})

test('a failed explanation read clears the previous student and review text', async () => {
  const held = deferred()
  const h = harness({ getTeacherCounterexampleAttempt: id => id === 'attempt-2' ? held.promise
    : Promise.resolve({ request_id: id, challenge_id: row.id, status: 'complete' }) })
  try {
    await settle(); await h.state.select(row.id); await h.state.readAttempt('attempt-1')
    h.state.explanationNote.value = 'This note belongs to the first student.'
    const switching = h.state.readAttempt('attempt-2')
    assert.equal(h.state.selectedAttempt.value, null)
    assert.equal(h.state.explanationNote.value, '')
    held.reject(new Error('record unavailable')); await switching
    assert.equal(h.state.selectedAttempt.value, null)
    assert.equal(h.state.error.value, '请求未完成，请重试。')
  } finally { h.close() }
})

test('discarding a rejected edit restores the saved task and clears obsolete feedback', async () => {
  const h = harness()
  try {
    await settle(); await h.state.select(row.id); h.state.edit()
    h.state.form.value.title = ''; h.state.approvedBasis.value = true
    await h.state.save(); assert.ok(h.state.error.value)
    h.state.discardEdit()
    assert.equal(h.state.editing.value, false)
    assert.equal(h.state.approvedBasis.value, false)
    assert.equal(h.state.form.value.title, spec.title)
    assert.equal(h.state.error.value, '')
    assert.equal(h.state.notice.value, '')
    assert.equal(h.calls.some(c => /^(save|create|revise|publish)/.test(c.name)), false)
  } finally { h.close() }
})

test('adapted template retries frozen content and source after uncertain save', async () => {
  let count=0
  const h=harness({createCounterexample:async()=>{if(++count===1) throw new Error('response lost');return {...clone(row),source_template:{id:'L01',content_hash:'frozen-hash',revision:1},origin:'catalog_adapted'}}})
  try {
    await settle();await h.state.loadTemplate(template)
    h.state.form.value.candidate.explanation='teacher edit';h.state.approvedBasis.value=true
    await h.state.save();assert.ok(h.state.pendingSave.value)
    const source=h.state.pendingSave.value.source_template
    assert.equal(source.id,'L01')
    h.state.sourceTemplate.value.id='D01';h.state.form.value.candidate.explanation='later edit'
    await h.state.save()
    const sends=h.calls.filter(c=>c.name==='createCounterexample')
    assert.deepEqual(sends[0].args[0],sends[1].args[0])
    assert.equal(sends[0].args[0].candidate.explanation,'teacher edit')
    assert.equal(sends[0].args[0].source_template.id,'L01')
    assert.equal(h.state.sourceTemplate.value.id,'L01')
    assert.ok([...h.saved.values()].every(value=>!value.includes('solve')&&!value.includes('tests')))
  } finally {h.close()}
})

test('recovering a saved template basis preserves provenance without restoring approval', async () => {
  const source={id:'L01',content_hash:'frozen-hash'}
  const h=harness({getTeacherCounterexample:async()=>{throw {isAxiosError:true,response:{status:404}}}},
    new Map([['plex:counterexample-author:1:1',JSON.stringify({challengeId:'unfinished',specId:'saved',sourceTemplate:source})]]))
  try {
    await settle();assert.equal(h.state.sourceTemplate.value.id,'L01')
    assert.equal(h.state.approvedBasis.value,false)
    assert.equal(h.state.form.value.candidate.buggy_code,'')
    h.state.form.value.candidate=clone(candidate);h.state.approvedBasis.value=true;await h.state.save()
    assert.deepEqual(h.calls.find(c=>c.name==='createCounterexample').args[0].source_template,source)
  } finally {h.close()}
})
