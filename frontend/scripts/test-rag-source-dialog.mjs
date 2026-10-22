import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import ts from 'typescript'
import * as vue from 'vue'

function mount() {
  const source = readFileSync(new URL('../src/composables/useRagSourceDialog.ts', import.meta.url), 'utf8')
  const code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText
  const exports = {}, calls = [], hooks = {}
  const auth = vue.reactive({ profile: { id: 1, role: 'student' } }), owner = vue.ref({ request_id: 'a' })
  const scope = vue.effectScope()
  vm.runInNewContext(code, { exports, Error, require(name) {
    if (name === 'vue') return { ...vue, onActivated: fn => { hooks.activate = fn }, onDeactivated: fn => { hooks.deactivate = fn }, onBeforeUnmount: fn => { hooks.unmount = fn } }
    if (name === '../stores/auth') return { useAuthStore: () => auth }
    assert.equal(name, '../api/rag')
    return { fetchRagSource: (...args) => new Promise((resolve, reject) => calls.push({ args, resolve, reject })) }
  } })
  const state = scope.run(() => exports.useRagSourceDialog(() => owner.value))
  return { state, calls, auth, owner, hooks, dispose() { hooks.unmount(); scope.stop() } }
}
const citation = (id = 'one') => ({ chunk_id: id, version: 1 })

test('the last selected citation owns the dialog, including loading and failure state', async () => {
  const s = mount()
  try {
    const first = s.state.show(citation()), second = s.state.show(citation('two'))
    s.calls[0].resolve({ content: 'old' }); await first
    assert.equal(s.state.detail.value, null); assert.equal(s.state.loading.value, true)
    s.calls[1].resolve({ content: 'current' }); await second
    assert.equal(s.state.detail.value.content, 'current')
  } finally { s.dispose() }
})

test('closing, changing owner/account and leaving the cached page discard pending source contents', async () => {
  for (const action of ['close', 'owner', 'account', 'leave', 'unmount']) {
    const s = mount()
    try {
      const pending = s.state.show(citation())
      if (action === 'close') s.state.open.value = false
      if (action === 'owner') s.owner.value = { request_id: 'b' }
      if (action === 'account') s.auth.profile.id = 2
      if (action === 'leave') s.hooks.deactivate()
      if (action === 'unmount') s.hooks.unmount()
      s.calls[0].resolve({ content: 'PRIVATE-OLD' }); await pending
      assert.equal(s.state.open.value, false); assert.equal(s.state.detail.value, null)
      assert.equal(s.state.loading.value, false)
    } finally { s.dispose() }
  }
})

test('failure never displays cached source text and retry re-reads the same version', async () => {
  const s = mount()
  try {
    const first = s.state.show(citation()); s.calls[0].resolve({ content: 'old source' }); await first
    const next = s.state.show(citation()); assert.equal(s.state.detail.value, null)
    s.calls[1].reject(new Error('permission unavailable')); await next
    assert.equal(s.state.error.value, 'permission unavailable'); assert.equal(s.state.open.value, true)
    s.state.retry(); assert.deepEqual(s.calls[2].args, ['one', 1])
    s.calls[2].resolve({ content: 'fresh' }); await new Promise(resolve => setImmediate(resolve))
    assert.equal(s.state.detail.value.content, 'fresh'); assert.equal(s.state.error.value, '')
  } finally { s.dispose() }
})

test('reactivation keeps the source closed until an explicit fresh read', async () => {
  const s = mount()
  try {
    s.hooks.deactivate(); await s.state.show(citation()); assert.equal(s.calls.length, 0)
    s.hooks.activate(); assert.equal(s.state.open.value, false)
    const pending = s.state.show(citation()); assert.equal(s.calls.length, 1)
    s.calls[0].resolve({ content: 'fresh' }); await pending
    assert.equal(s.state.detail.value.content, 'fresh')
  } finally { s.dispose() }
})
