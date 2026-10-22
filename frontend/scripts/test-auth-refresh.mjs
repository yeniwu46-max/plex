// Exercise the real interceptor with controlled network responses and storage.
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import ts from 'typescript'

function setup() {
  const saved = new Map([['a3_access_token', 'old-access'], ['a3_refresh_token', 'old-refresh'], ['a3_user_profile', '{}']])
  const pending = []
  const redirects = []
  let rejectResponse
  class Headers { set(k, v) { this[k] = v } }
  const http = async config => config
  http.interceptors = { request: { use() {} }, response: { use(_success, reject) { rejectResponse = reject } } }
  const axios = { create: () => http, post: () => new Promise((resolve, reject) => pending.push({ resolve, reject })) }
  const exports = {}
  const source = readFileSync(new URL('../src/api/http.ts', import.meta.url), 'utf8').replaceAll('import.meta.env', '({})')
  const code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, esModuleInterop: true } }).outputText
  vm.runInNewContext(code, {
    exports,
    require: name => { assert.equal(name, 'axios'); return { __esModule: true, default: axios, AxiosHeaders: Headers, isAxiosError: e => e?.isAxiosError === true } },
    localStorage: { getItem: k => saved.get(k) ?? null, setItem: (k, v) => saved.set(k, v), removeItem: k => saved.delete(k) },
    window: { dispatchEvent() {}, location: { pathname: '/student', search: '', hash: '', assign: v => redirects.push(v) } },
    Event: class {}, FormData: class {},
  })
  const error = (status, url = '/v1/users/me') => ({ isAxiosError: true, config: { url, headers: new Headers() }, response: { status } })
  const request = () => rejectResponse(error(401))
  const success = (i, token) => pending[i].resolve({ data: { code: 0, data: { access_token: token } } })
  return { saved, pending, redirects, error, request, success, rejectResponse }
}

test('parallel protected requests share one refresh', async () => {
  const s = setup(); const a = s.request(); const b = s.request()
  assert.equal(s.pending.length, 1)
  s.success(0, 'new-access')
  const replies = await Promise.all([a, b])
  assert.ok(replies.every(r => r.headers.Authorization === 'Bearer new-access'))
})

test('a new session has its own refresh and cannot be overwritten by an older one', async () => {
  const s = setup(); const old = s.request(); const rejected = assert.rejects(old, /登录状态已变化/)
  s.saved.set('a3_refresh_token', 'new-refresh')
  const newer = s.request(); assert.equal(s.pending.length, 2)
  s.success(0, 'stale-access'); await rejected
  s.success(1, 'current-access'); await newer
  assert.equal(s.saved.get('a3_access_token'), 'current-access')
  assert.equal(s.saved.get('a3_refresh_token'), 'new-refresh')
  assert.equal(s.redirects.length, 0)
})

test('network failure preserves the saved session', async () => {
  const s = setup(); const p = s.request(); const rejected = assert.rejects(p)
  s.pending[0].reject({ isAxiosError: true, code: 'ERR_NETWORK' }); await rejected
  assert.equal(s.saved.get('a3_refresh_token'), 'old-refresh')
  assert.equal(s.redirects.length, 0)
})

test('revoked refresh clears credentials and redirects to login', async () => {
  const s = setup(); const p = s.request(); const rejected = assert.rejects(p)
  s.pending[0].reject(s.error(401)); await rejected
  assert.equal(s.saved.size, 0)
  assert.deepEqual(s.redirects, ['/login?redirect=%2Fstudent'])
})

test('incorrect login does not attempt token refresh', async () => {
  const s = setup()
  await assert.rejects(s.rejectResponse(s.error(401, '/v1/auth/login')))
  assert.equal(s.pending.length, 0)
  assert.equal(s.saved.get('a3_refresh_token'), 'old-refresh')
})
