import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import ts from 'typescript'

const source = await readFile(new URL('../src/utils/tutorGuidanceSession.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } })
const { TutorGuidanceSession } = await import('data:text/javascript;base64,' + Buffer.from(outputText).toString('base64'))
const session = new TutorGuidanceSession()
const payload = { requestId: 'original', code: 'old', mode: 'auto' }
const first = session.start(payload)
payload.code = 'edited'
assert.equal(first.payload.code, 'old', 'request must be a snapshot')
const retry = session.retry()
assert.equal(retry.payload.requestId, 'original', 'retry keeps the same id')
assert.equal(retry.payload.code, 'old', 'retry keeps original code')
assert.equal(session.accept(first.epoch, { requestId: 'original' }), false, 'late request cannot overwrite retry')
assert.equal(session.accept(retry.epoch, { requestId: 'original' }), true)
assert.equal(session.previousRequestId, undefined, 'response alone does not advance progress')
assert.equal(session.latestPayload.code, 'old', 'accepted turn preserves the original student context')
assert.equal(session.confirm(retry.epoch, 'other-id'), false)
assert.equal(session.confirm(retry.epoch, 'original'), true)
assert.equal(session.previousRequestId, 'original')
const next = session.start({ requestId: 'next', code: 'old' })
session.reset()
assert.equal(session.accept(next.epoch, { requestId: 'next' }), false, 'reset discards late response')
assert.equal(session.confirm(retry.epoch, 'original'), false, 'late acknowledgment cannot restore old progress')
assert.equal(session.previousRequestId, undefined)
assert.equal(session.pending, undefined)
assert.equal(session.latest, undefined)
assert.equal(session.latestPayload, undefined)
assert.equal(session.retry(), undefined)
console.log('Tutor guidance lifecycle checks passed: snapshots, retries, confirmation, stale responses and reset.')
