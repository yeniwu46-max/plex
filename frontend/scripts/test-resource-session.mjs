import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import ts from 'typescript'
import * as vue from 'vue'

function mount() {
  const source = readFileSync(new URL('../src/composables/useResourceTaskSession.ts', import.meta.url), 'utf8')
  const code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText
  const exports = {}, calls = [], timers = new Map(), hooks = {}
  const auth = vue.reactive({ profile: { id: 1, role: 'student' } })
  const api = Object.fromEntries(['createResourceTask', 'fetchPersonalizedResources', 'fetchResourceTask', 'fetchResourceTasks', 'retryResourceTask']
    .map(name => [name, (...args) => new Promise((resolve, reject) => calls.push({ name, args, resolve, reject }))]))
  const scope = vue.effectScope()
  let sequence = 0, state
  vm.runInNewContext(code, { exports, console,
    window: { setTimeout(fn) { const id = ++sequence; timers.set(id, fn); return id }, clearTimeout(id) { timers.delete(id) } },
    require(name) {
      if (name === 'vue') return { ...vue, onMounted: fn => { hooks.mount = fn }, onActivated: fn => { hooks.activate = fn },
        onDeactivated: fn => { hooks.deactivate = fn }, onBeforeUnmount: fn => { hooks.unmount = fn } }
      if (name === '../stores/auth') return { useAuthStore: () => auth }
      if (name === '../api/http') return { formatHttpError: e => e.message }
      assert.equal(name, '../api/personalizedResources'); return api
    },
  })
  scope.run(() => { state = exports.useResourceTaskSession() })
  return { state, calls, timers, hooks, auth,
    dispose() { hooks.unmount(); scope.stop() },
    snapshot(resources = [], tasks = []) {
      calls.filter(c => !c.settled && ['fetchPersonalizedResources', 'fetchResourceTasks'].includes(c.name)).forEach(c => {
        c.settled = true; c.resolve({ items: c.name === 'fetchPersonalizedResources' ? resources : tasks })
      })
    },
  }
}
const tick = async () => { for (let i = 0; i < 5; i++) await Promise.resolve(); await vue.nextTick() }
const task = (id, status = 'completed') => ({ task_id: id, status, resources: [], progress: status === 'completed' ? 100 : 50, steps: [] })
async function ready(s, resources = [], tasks = []) { s.hooks.mount(); s.snapshot(resources, tasks); await tick() }

test('initial KeepAlive activation reads once and restores the latest authorized task', async () => {
  const s = mount()
  try {
    s.hooks.mount(); s.hooks.activate(); assert.equal(s.calls.length, 2)
    s.snapshot([{ id: 1 }], [task('latest')]); await tick()
    assert.equal(s.state.task.value.task_id, 'latest'); assert.equal(s.state.resources.value.length, 1)
  } finally { s.dispose() }
})

test('account change clears content and rejects a previous account snapshot', async () => {
  const s = mount()
  try {
    s.hooks.mount(); const old = s.calls.slice(); s.auth.profile = { id: 2, role: 'student' }
    old.forEach(c => { c.settled = true; c.resolve({ items: c.name === 'fetchResourceTasks' ? [task('old')] : [{ id: 1 }] }) })
    await tick(); assert.equal(s.state.task.value, null); assert.equal(s.state.resources.value.length, 0)
    s.snapshot([{ id: 2 }], [task('new')]); await tick(); assert.equal(s.state.task.value.task_id, 'new')
  } finally { s.dispose() }
})

test('failed revalidation hides previously readable material instead of retaining a cached copy', async () => {
  const s = mount()
  try {
    await ready(s, [{ id: 1 }], [task('old')]); const load = s.state.load()
    assert.equal(s.state.resources.value.length, 0); assert.equal(s.state.task.value, null)
    s.calls.at(-1).reject(new Error('access unavailable')); s.calls.at(-2).resolve({ items: [] }); await load
    assert.equal(s.state.resources.value.length, 0); assert.equal(s.state.loadError.value, 'access unavailable')
  } finally { s.dispose() }
})

test('ambiguous create failure refreshes history without creating another task or claiming success', async () => {
  const s = mount()
  try {
    await ready(s); const pending = s.state.generate('loop-for')
    s.calls.at(-1).reject(new Error('response lost')); await tick()
    s.snapshot([], [task('accepted-in-background', 'running')]); assert.equal(await pending, null)
    assert.equal(s.state.task.value.task_id, 'accepted-in-background')
    assert.equal(s.state.taskError.value, 'response lost')
    assert.equal(s.calls.filter(c => c.name === 'createResourceTask').length, 1)
  } finally { s.dispose() }
})

test('deactivation ignores a late creation response and restores by fresh reads on return', async () => {
  const s = mount()
  try {
    await ready(s); const pending = s.state.generate('loop-for'), request = s.calls.at(-1)
    s.hooks.deactivate(); request.resolve(task('old')); assert.equal(await pending, null)
    assert.equal(s.state.task.value, null); assert.equal(s.state.generating.value, false)
    s.hooks.activate(); s.snapshot([], [task('old')]); await tick()
    assert.equal(s.state.task.value.task_id, 'old')
  } finally { s.dispose() }
})

test('duplicate clicks submit once and completion uses the fresh resource list', async () => {
  const s = mount()
  try {
    await ready(s); const pending = s.state.generate('loop-for')
    assert.equal(await s.state.generate('loop-for'), null)
    s.calls.at(-1).resolve({ ...task('new'), resources: [{ id: 999, content: 'cached' }] }); await tick()
    s.snapshot([{ id: 2 }], [task('new')]); await pending
    assert.equal(s.state.resources.value[0].id, 2)
    assert.equal(s.calls.filter(c => c.name === 'createResourceTask').length, 1)
  } finally { s.dispose() }
})

test('the bounded observation timeout leaves a running task, never a completed resource result', async () => {
  const s = mount()
  try {
    await ready(s); const pending = s.state.generate('loop-for')
    s.calls.at(-1).resolve(task('slow', 'running')); await tick()
    for (let i = 0; i < 120; i++) {
      const fn = [...s.timers.values()][0]; assert.equal(typeof fn, 'function'); fn(); await tick()
      assert.equal(s.calls.at(-1).name, 'fetchResourceTask')
      s.calls.at(-1).resolve(task('slow', 'running')); await tick()
    }
    const result = await pending
    assert.equal(result.status, 'running'); assert.equal(s.state.pollingTimedOut.value, true)
    assert.equal(s.state.generating.value, false); assert.equal(s.state.resources.value.length, 0)
  } finally { s.dispose() }
})

test('leaving during polling releases its timer without further reads or cancelling the server job', async () => {
  const s = mount()
  try {
    await ready(s); const pending = s.state.inspect('job')
    s.calls.at(-1).resolve(task('job', 'running')); await tick()
    assert.equal(s.timers.size, 1); const count = s.calls.length
    s.hooks.deactivate(); assert.equal(await pending, null)
    assert.equal(s.timers.size, 0); assert.equal(s.calls.length, count)
  } finally { s.dispose() }
})

test('retry failure remains visible and history inspection fetches current status', async () => {
  const s = mount()
  try {
    await ready(s); const pending = s.state.retry('failed')
    s.calls.at(-1).resolve({ ...task('retry', 'failed'), error: 'model unavailable' }); await pending
    assert.equal(s.state.taskError.value, 'model unavailable')
    const inspect = s.state.inspect('retry'); assert.equal(s.calls.at(-1).name, 'fetchResourceTask')
    s.calls.at(-1).resolve(task('retry')); await tick(); s.snapshot([], [task('retry')]); await inspect
    assert.equal(s.state.task.value.status, 'completed'); assert.equal(s.state.taskError.value, '')
  } finally { s.dispose() }
})


test('returning to a running task resumes observation without submitting a second generation', async () => {
  const s = mount()
  try {
    await ready(s)
    s.hooks.deactivate(); s.hooks.activate()
    s.snapshot([], [task('background', 'running')]); await tick()
    assert.equal(s.calls.at(-1).name, 'fetchResourceTask')
    assert.equal(s.calls.at(-1).args[0], 'background')
    s.calls.at(-1).resolve(task('background')); await tick()
    s.snapshot([{ id: 3 }], [task('background')]); await tick()
    assert.equal(s.state.task.value.status, 'completed')
    assert.equal(s.state.resources.value[0].id, 3)
    assert.equal(s.calls.filter(c => c.name === 'createResourceTask').length, 0)
  } finally { s.dispose() }
})
