import test from 'node:test'
import assert from 'node:assert/strict'
import { createHash, webcrypto } from 'node:crypto'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import ts from 'typescript'
import { httpCrypto, loadBrowserCrypto } from './helpers/browser-crypto.mjs'

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/
const http = loadBrowserCrypto()
function load(path, dependencies, globals = {}) {
  const source = readFileSync(new URL(path, import.meta.url), 'utf8')
  const code = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
  }).outputText
  const exports = {}
  vm.runInNewContext(code, {
    exports, crypto: httpCrypto, TextEncoder, AbortController, ...globals,
    require(name) {
      if (name.endsWith('/browserCrypto')) return http
      assert.ok(name in dependencies, name)
      return dependencies[name]
    },
  })
  return exports
}

test('HTTP generates unique UUID v4 request IDs without randomUUID or subtle', () => {
  assert.equal(httpCrypto.randomUUID, undefined)
  assert.equal(httpCrypto.subtle, undefined)
  const ids = Array.from({ length: 1000 }, () => http.createRequestId())
  assert.equal(new Set(ids).size, ids.length)
  for (const id of ids) assert.match(id, uuid)
})

test('HTTP and native HTTPS SHA-256 yield identical keys for Chinese, Unicode and long payloads', async () => {
  const native = loadBrowserCrypto(webcrypto)
  for (const input of ['', 'abc', '小E，解释循环结构 🌟', JSON.stringify({code:'print("你好")'}), 'x'.repeat(100000)]) {
    const expected = createHash('sha256').update(input).digest('hex')
    assert.equal(await http.sha256Hex(input), expected)
    assert.equal(await native.sha256Hex(input), expected)
  }
})

test('HTTP resource and RAG retries survive reload, isolate owners and retain opaque storage', async () => {
  for (const [file, method] of [
    ['resourceRequestIdentity', 'resourceRequestIdentity'], ['ragRequestIdentity', 'ragRequestIdentity'],
  ]) {
    const values = new Map()
    const localStorage = { getItem:k => values.get(k) || null, setItem:(k,v) => values.set(k,v), removeItem:k => values.delete(k) }
    const reload = () => load(`../src/utils/${file}.ts`, {}, { localStorage })[method]
    const body = { query:'private question 小E', code:'private code' }
    const first = await reload()(1, body)
    const retry = await reload()(1, body)
    assert.match(first.requestId, uuid)
    assert.equal(retry.requestId, first.requestId)
    assert.notEqual((await reload()(2, body)).requestId, first.requestId)
    for (const [key, value] of values) {
      assert.ok(!key.includes('private'))
      assert.match(value, uuid)
    }
    retry.clear()
    assert.notEqual((await reload()(1, body)).requestId, first.requestId)
  }
})

test('HTTP messenger sends chat, streaming chat and learning tools with request IDs', async () => {
  const requests = []
  const api = load('../src/api/messenger.ts', {
    './http': {http:{post:async(url, body) => {
      requests.push({url, body}); return {data:{code:0, data:{reply:'收到问题'}}}
    }}},
    './sse': {postSseStream:async(url, body) => {
      requests.push({url, body}); return {reply:'收到问题', source:'test'}
    }},
  }, { window:{setTimeout, clearTimeout} })
  await api.postMessengerChat('解释循环')
  await api.streamMessengerChat('解释循环')
  await api.postMessengerKnowledgeGraph('循环')
  await api.postMessengerLearningDocument('循环')
  assert.equal(requests.length, 4)
  for (const request of requests) assert.match(request.body.request_id, uuid)
})
