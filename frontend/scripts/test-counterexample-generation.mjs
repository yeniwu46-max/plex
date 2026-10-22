import { loadBrowserCrypto } from './helpers/browser-crypto.mjs'
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import ts from 'typescript'
import * as vue from 'vue'

function compiled(path, modules, globals = {}) {
  const code = ts.transpileModule(readFileSync(new URL(path, import.meta.url), 'utf8'), { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText
  const exports = {}
  vm.runInNewContext(code, { exports, console, AbortController, ...globals, require: name => {
      if (name.endsWith('/browserCrypto')) return loadBrowserCrypto(globals.crypto)
 assert.ok(name in modules, name); return modules[name] } })
  return exports
}
const clone = value => JSON.parse(JSON.stringify(value))
const page = { items: [], total: 0, page: 1, page_size: 20 }
const task = { id: 'task-1', spec_id: 'spec-1', class_id: 1, status: 'queued', stage: 'generation', bug_kind: 'loop_boundary', attempts: 0 }
const basis = { title: '求和', tests: [{ input: [], expected: 0 }], reference_code: 'private source' }
function deferred() { let resolve; const promise = new Promise(r => { resolve = r }); return { promise, resolve } }
async function settle() { for (let i = 0; i < 20; i++) await Promise.resolve(); await vue.nextTick() }
function harness(overrides = {}, cache = new Map()) {
  const user = vue.ref(1), cohort = vue.ref(1), unmount = [], calls = [], timers = new Map()
  let serial = 0
  const methods = {
    listCounterexampleGenerationTasks: async () => clone(page),
    getCounterexampleGenerationTask: async () => clone(task),
    getCounterexampleSpecification: async () => ({ id: 'spec-1', class_id: 1, specification: clone(basis) }),
    saveCounterexampleSpecification: async b => ({ id: b.request_id }),
    createCounterexampleGenerationTask: async b => ({ ...clone(task), id: b.request_id, spec_id: b.spec_id }),
    cancelCounterexampleGenerationTask: async () => ({ ...clone(task), status: 'cancelled' }),
    retryCounterexampleGenerationTask: async () => clone(task), ...overrides,
  }
  const api = Object.fromEntries(Object.entries(methods).map(([name, method]) => [name, (...args) => {
    calls.push({ name, args: args.map(arg => arg instanceof AbortSignal ? arg : clone(arg ?? null)) }); return method(...args)
  }]))
  const { useCounterexampleGeneration } = compiled('../src/composables/useCounterexampleGeneration.ts', {
    vue: { ...vue, onBeforeUnmount: fn => unmount.push(fn) }, axios: { isAxiosError: e => e?.isAxiosError === true },
    '../api/teacherCounterexamples': api,
  }, { crypto: { randomUUID: () => `uuid-${++serial}` }, localStorage: { getItem: key => cache.get(key),
    setItem: (key, value) => cache.set(key, value), removeItem: key => cache.delete(key) },
    setTimeout: fn => { const id = ++serial; timers.set(id, fn); return id }, clearTimeout: id => timers.delete(id) })
  const scope = vue.effectScope(), state = scope.run(() => useCounterexampleGeneration(user, cohort))
  return { state, user, cohort, calls, cache, timers, close() { unmount.forEach(fn => fn()); scope.stop() } }
}

test('queue stores only identifiers and retries the frozen basis and request after response loss', async () => {
  let count = 0
  const h = harness({ createCounterexampleGenerationTask: async body => {
    if (++count === 1) throw new Error('response lost')
    return { ...clone(task), id: body.request_id }
  } })
  try {
    await settle(); const source = clone(basis)
    assert.equal(await h.state.queue(source, 'loop_boundary'), false)
    assert.ok(h.state.pending.value)
    assert.ok([...h.cache.values()].every(raw => !raw.includes('tests') && !raw.includes('private source')))
    source.title = 'changed after uncertain submission'
    assert.equal(await h.state.queue(source, 'empty_input'), true)
    const sends = h.calls.filter(call => call.name === 'createCounterexampleGenerationTask')
    assert.deepEqual(sends[0].args[0], sends[1].args[0])
    const specs = h.calls.filter(call => call.name === 'saveCounterexampleSpecification')
    assert.deepEqual(specs[0].args[0], specs[1].args[0]); assert.equal(h.state.pending.value, null)
    assert.equal(h.timers.size, 1)
  } finally { h.close() }
  assert.equal(h.timers.size, 0)
})

test('refresh recovers existing task without sending another generation request', async () => {
  const cache = new Map([['plex:counterexample-generation:1:1', JSON.stringify({ taskId:'task-1',specId:'spec-1',bugKind:'loop_boundary' })]])
  const h = harness({}, cache)
  try {
    await settle(); assert.equal(h.state.selected.value.id, 'task-1'); assert.equal(h.state.pending.value, null)
    assert.equal(h.calls.some(call => call.name === 'createCounterexampleGenerationTask'), false)
  } finally { h.close() }
})

test('refresh can resume a saved basis when creation never reached server', async () => {
  const cache = new Map([['plex:counterexample-generation:1:1', JSON.stringify({ taskId:'task-1',specId:'spec-1',bugKind:'loop_boundary' })]])
  const h = harness({ getCounterexampleGenerationTask: async () => { throw { isAxiosError:true,response:{status:404} } } }, cache)
  try {
    await settle(); assert.ok(h.state.pending.value); assert.equal(await h.state.queue(), true)
    assert.equal(h.calls.some(call => call.name === 'saveCounterexampleSpecification'), false)
    assert.equal(h.calls.filter(call => call.name === 'createCounterexampleGenerationTask').length, 1)
  } finally { h.close() }
})

test('class change after basis save cannot enqueue a task or cache data in the next class', async () => {
  const held = deferred(), h = harness({ saveCounterexampleSpecification: () => held.promise })
  try {
    await settle(); const queued = h.state.queue(basis, 'loop_boundary')
    const saving = h.calls.find(call => call.name === 'saveCounterexampleSpecification')
    h.cohort.value = 2; await settle(); assert.equal(saving.args.at(-1).aborted, true)
    held.resolve({ id:'old-spec' }); assert.equal(await queued, false)
    assert.equal(h.calls.some(call => call.name === 'createCounterexampleGenerationTask'), false)
    assert.equal(h.cache.has('plex:counterexample-generation:1:2'), false)
  } finally { h.close() }
})

test('late response after logout is discarded and polling is stopped', async () => {
  const held = deferred(), h = harness({ getCounterexampleGenerationTask: () => held.promise })
  try {
    await settle(); const read = h.state.select('task-1')
    h.user.value = undefined; await settle(); held.resolve(clone(task)); await read
    assert.equal(h.state.selected.value, null); assert.equal(h.timers.size, 0)
  } finally { h.close() }
})

test('cancellation calls the server and terminal tasks no longer schedule polling', async () => {
  const h = harness()
  try {
    await settle(); await h.state.select('task-1'); assert.equal(h.timers.size, 1)
    await h.state.action('cancel')
    assert.equal(h.state.selected.value.status, 'cancelled'); assert.equal(h.timers.size, 0)
    assert.equal(h.calls.filter(call => call.name === 'cancelCounterexampleGenerationTask').length, 1)
  } finally { h.close() }
})

test('list refresh failure after accepted creation does not leave a duplicate creation action', async () => {
  let count = 0
  const h = harness({ listCounterexampleGenerationTasks: async () => {
    if (++count > 1) throw new Error('offline'); return clone(page)
  } })
  try {
    await settle(); assert.equal(await h.state.queue(basis, 'loop_boundary'), true)
    assert.ok(h.state.selected.value); assert.equal(h.state.pending.value, null)
    assert.match(h.state.error.value, /任务已保存/)
  } finally { h.close() }
})

test('pending new request takes priority over an older selected task during recovery', async () => {
  const h = harness({ createCounterexampleGenerationTask: async () => { throw new Error('lost response') },
    getCounterexampleGenerationTask: async id => ({ ...clone(task), id }) })
  try {
    await settle(); await h.state.select('old-task'); await h.state.queue(basis, 'loop_boundary')
    const pendingId = h.state.pending.value.taskId
    await h.state.refresh()
    assert.equal(h.state.selected.value.id, pendingId); assert.equal(h.state.pending.value, null)
  } finally { h.close() }
})

test('a definite basis contract rejection unlocks editing without queuing a task', async () => {
  const h=harness({saveCounterexampleSpecification:async()=>{throw {isAxiosError:true,response:{status:400,data:{message:'所选性质没有可执行关系'}}}}})
  try {
    await settle();assert.equal(await h.state.queue(basis,'loop_boundary'),false)
    assert.equal(h.state.pending.value,null);assert.equal(h.cache.size,0)
    assert.match(h.state.error.value,/性质/)
    assert.equal(h.calls.some(call=>call.name==='createCounterexampleGenerationTask'),false)
  } finally {h.close()}
})
