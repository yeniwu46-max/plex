import { loadBrowserCrypto } from './helpers/browser-crypto.mjs'
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import ts from 'typescript'
import * as vue from 'vue'

function compiled(file, modules, globals = {}) {
  const source = readFileSync(new URL(file, import.meta.url), 'utf8')
  const code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText
  const exports = {}
  vm.runInNewContext(code, { exports, console, AbortController, ...globals, require: name => {
      if (name.endsWith('/browserCrypto')) return loadBrowserCrypto(globals.crypto)

    assert.ok(name in modules, `Unexpected module ${name}`); return modules[name]
  } })
  return exports
}
const contract = { type: 'integer_array', minimum: -10, maximum: 10, min_items: 0, max_items: 8 }
const api = compiled('../src/api/counterexamples.ts', { './http': {} })
const task = { id: 'task-a', title: 'sum', revision: 1, version: 'v1', input_contract: contract,
  output_contract: { type: 'integer', minimum: -100, maximum: 100 } }
function deferred() {
  let resolve, reject
  const promise = new Promise((r, j) => { resolve = r; reject = j })
  return { promise, resolve, reject }
}
function result(body, extra = {}) {
  return { ...body, challenge_id: 'task-a', status: 'complete', retryable: false, graded: true,
    created_at: '2026-10-16T01:00:00Z', completed_at: '2026-10-16T01:00:01Z', ...extra }
}
function harness(overrides = {}, cache = new Map()) {
  const sends = [], reads = [], unmount = []
  const userId = vue.ref(1), challengeId = vue.ref('task-a')
  const exports = compiled('../src/composables/useCounterexampleAttempt.ts', {
    vue: { ...vue, onBeforeUnmount: fn => unmount.push(fn) },
    axios: { isAxiosError: cause => cause?.isAxiosError === true },
    '../api/counterexamples': { ...api,
      fetchCounterexamples: async () => [task], fetchCounterexample: async id => ({ ...task, id }),
      fetchCounterexampleAttempts: async () => [],
      fetchCounterexampleAttempt: async id => { reads.push(id); throw new Error('offline') },
      submitCounterexample: (id, body, signal) => {
        const call = { id, body: JSON.parse(JSON.stringify(body)), signal, ...deferred() }; sends.push(call); return call.promise
      }, ...overrides,
    },
  }, { crypto: { randomUUID: () => `request-${sends.length + 1}` },
    localStorage: { getItem: key => cache.get(key), setItem: (key, val) => cache.set(key, val), removeItem: key => cache.delete(key) } })
  const scope = vue.effectScope()
  const state = scope.run(() => exports.useCounterexampleAttempt(userId, challengeId))
  const close = () => { unmount.forEach(fn => fn()); scope.stop() }
  return { state, sends, reads, userId, challengeId, cache, close }
}
async function settle() { for (let i = 0; i < 12; i++) await Promise.resolve(); await vue.nextTick() }
function fill(state) { state.input.value = '[2,3]'; state.expected.value = '5'; state.explanation.value = '循环遗漏最后一项。' }

test('JSON contract rejects boolean-as-number, nested values and out of bounds', () => {
  for (const raw of ['[true]', '[11]', '[[1]]', '{}', 'NaN']) assert.throws(() => api.parseCounterexampleValue(raw, contract))
  assert.equal(JSON.stringify(api.parseCounterexampleValue('[2,3]', contract)), '[2,3]')
})
test('failed connection retries the original input and UUID; cache contains only the ID', async () => {
  const h = harness()
  try {
    await settle(); fill(h.state)
    const first = h.state.submit(); h.sends[0].reject(new Error('offline')); await first
    h.state.input.value = '[9]'
    const retry = h.state.submit()
    assert.deepEqual(h.sends[1].body, h.sends[0].body)
    assert.deepEqual([...h.cache.values()], ['request-1'])
    h.sends[1].resolve(result(h.sends[1].body)); await retry
    assert.equal(h.state.attempt.value.status, 'complete')
    assert.equal(h.state.canRetry.value, false)
    h.state.startNew(); assert.equal(h.state.pending.value, null)
  } finally { h.close() }
})
test('refresh restores one owned result and never submits again', async () => {
  const saved = result({ request_id: 'saved-id', revision: 1, version: 'v1', input: [2,3], expected_output: 5, explanation: 'saved' })
  const h = harness({ fetchCounterexampleAttempt: async () => saved }, new Map([['plex:counterexample:1:task-a', 'saved-id']]))
  try {
    await settle(); assert.equal(h.state.attempt.value.request_id, 'saved-id')
    assert.equal(h.state.explanation.value, 'saved'); assert.equal(h.sends.length, 0)
  } finally { h.close() }
})
test('unresolved saved response blocks new requests until recovery succeeds', async () => {
  const h = harness({}, new Map([['plex:counterexample:1:task-a', 'saved-id']]))
  try {
    await settle(); fill(h.state); await h.state.submit()
    assert.equal(h.state.locked.value, true); assert.equal(h.sends.length, 0)
    assert.equal(h.state.unresolvedId.value, 'saved-id')
  } finally { h.close() }
})
test('account switching aborts a request and discards its late reply and cache write', async () => {
  const h = harness()
  try {
    await settle(); fill(h.state); const sent = h.state.submit()
    h.userId.value = 2; await settle()
    assert.equal(h.sends[0].signal.aborted, true)
    h.sends[0].resolve(result(h.sends[0].body)); await sent
    assert.equal(h.state.attempt.value, null)
    assert.equal(h.cache.has('plex:counterexample:2:task-a'), false)
  } finally { h.close() }
})
test('changing task and unmounting both prevent late results from replacing the next task', async () => {
  const h = harness()
  await settle(); fill(h.state); const sent = h.state.submit()
  h.challengeId.value = 'task-b'; await settle()
  h.sends[0].resolve(result(h.sends[0].body)); await sent
  assert.equal(h.state.attempt.value, null); assert.equal(h.state.challenge.value.id, 'task-b')
  fill(h.state); const next = h.state.submit(); h.close()
  assert.equal(h.sends[1].signal.aborted, true)
  h.sends[1].resolve(result(h.sends[1].body)); await next
  assert.equal(h.state.attempt.value, null)
})
test('material defect result is restored even when the challenge is withdrawn', async () => {
  let taskReads = 0
  const saved = result({ request_id: 'saved-id', input: [2], expected_output: 2, explanation: 'edge' }, { status: 'material_issue', graded: false })
  const h = harness({ fetchCounterexampleAttempt: async () => saved, fetchCounterexample: async () => { taskReads++; throw new Error('withdrawn') } },
    new Map([['plex:counterexample:1:task-a', 'saved-id']]))
  try { await settle(); assert.equal(h.state.attempt.value.status, 'material_issue'); assert.equal(taskReads, 0) }
  finally { h.close() }
})

test('withdrawn task and inaccessible saved result cannot trigger a new submission', async () => {
  const unavailable = () => Promise.reject({ isAxiosError: true, response: { status: 404, data: { message: '反例挑战不存在' } } })
  const h = harness({ fetchCounterexampleAttempt: unavailable, fetchCounterexample: unavailable },
    new Map([['plex:counterexample:1:task-a', 'saved-id']]))
  try {
    await settle(); fill(h.state); await h.state.submit()
    assert.equal(h.state.challenge.value, null)
    assert.equal(h.state.attempt.value, null)
    assert.equal(h.state.canStart.value, false)
    assert.equal(h.sends.length, 0)
    assert.ok(h.state.historyError.value)
    assert.equal(h.state.error.value, '反例挑战不存在')
  } finally { h.close() }
})
