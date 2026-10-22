import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import ts from 'typescript'
import * as vue from 'vue'

function mount() {
  const source = readFileSync(new URL('../src/components/shared/AiUsageSummary.vue', import.meta.url), 'utf8')
    .match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1] + '\nexport const state = {open,usage,error,loading,refresh,toggle,ragQuota,resourceQuota};'
  const code = ts.transpileModule(source, {compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText
  const exports = {}, requests = [], props = vue.reactive({classId:null}), auth = vue.reactive({profile:{id:1}})
  let unmount = () => {}, activate = () => {}, deactivate = () => {}
  const scope = vue.effectScope()
  scope.run(() => vm.runInNewContext(code, {exports, Date, defineProps:() => props, require:name => {
    if (name === 'vue') return {...vue, onBeforeUnmount:fn => {unmount=fn}, onActivated:fn => {activate=fn}, onDeactivated:fn => {deactivate=fn}}
    if (name === '../../stores/auth') return {useAuthStore:() => auth}
    if (name === '../../api/aiUsage') return {fetchModelUsage:classId => new Promise((resolve,reject) => requests.push({classId,resolve,reject})), fetchResourceQuota:async () => ({requests_remaining:3}), fetchRagQuota:async () => ({requests_remaining:7})}
    throw new Error('Unexpected dependency '+name)
  }}))
  return {...exports.state,props,auth,requests,activate:()=>activate(),deactivate:()=>deactivate(),dispose(){unmount();scope.stop()}}
}
const tick = async () => {await Promise.resolve();await vue.nextTick()}

test('usage is loaded on demand and switching accounts discards late totals', async () => {
  const s=mount()
  try {
    assert.equal(s.requests.length,0)
    s.toggle();assert.equal(s.requests.length,1)
    s.auth.profile={id:2};assert.equal(s.requests.length,2)
    s.requests[0].resolve({owner:1});await tick()
    assert.equal(s.usage.value,null);assert.equal(s.loading.value,true)
    s.requests[1].resolve({owner:2});await tick()
    assert.equal(s.usage.value.owner,2)
    s.auth.profile=null;assert.equal(s.usage.value,null);assert.equal(s.loading.value,false)
  } finally {s.dispose()}
})

test('class switches isolate data and errors, and retry does not pretend unknown usage is zero', async () => {
  const s=mount()
  try {
    s.props.classId=10;s.toggle()
    assert.equal(s.requests[0].classId,10)
    s.props.classId=20
    s.requests[0].reject(new Error('old class denied'));await tick()
    assert.equal(s.error.value,'');assert.equal(s.loading.value,true)
    s.requests[1].reject(new Error('temporarily unavailable'));await tick()
    assert.equal(s.usage.value,null);assert.equal(s.error.value,'temporarily unavailable')
    const pending=s.refresh();assert.equal(s.error.value,'')
    s.requests[2].resolve({totals:{unknown_usage_calls:3,reported_total_tokens:0}});await pending
    assert.equal(s.usage.value.totals.unknown_usage_calls,3)
  } finally {s.dispose()}
})

test('a stale refresh or unmounted request cannot replace the newest displayed result', async () => {
  const s=mount()
  s.toggle();const pending=s.refresh()
  s.requests[1].resolve({version:2});await pending
  s.requests[0].resolve({version:1});await tick();assert.equal(s.usage.value.version,2)
  const late=s.refresh();s.dispose();s.requests[2].resolve({version:3});await late
  assert.equal(s.usage.value,null)
})


test('teacher self quota is visible but class and student views never inherit it',async()=>{
  const s=mount()
  try {
    s.auth.profile={id:1,role:'teacher'}
    s.toggle();s.requests[0].resolve({totals:{}});await tick();await tick()
    assert.equal(s.ragQuota.value.requests_remaining,7);assert.equal(s.resourceQuota.value,null)
    s.props.classId=4;s.requests[1].resolve({totals:{}});await tick();await tick()
    assert.equal(s.ragQuota.value,null);assert.equal(s.resourceQuota.value.requests_remaining,3)
    s.props.classId=null;s.auth.profile={id:1,role:'student'}
    s.requests[2].resolve({totals:{}});s.requests[3].resolve({totals:{}});await tick();await tick()
    assert.equal(s.ragQuota.value,null)
  } finally {s.dispose()}
})

test('cached page deactivation drops late usage and reloads the expanded panel on return',async()=>{
  const s=mount()
  try {
    s.toggle();s.deactivate()
    s.requests[0].resolve({owner:1});await tick()
    assert.equal(s.usage.value,null);assert.equal(s.loading.value,false)
    s.auth.profile={id:2,role:'student'};assert.equal(s.requests.length,1)
    s.activate();assert.equal(s.requests.length,2)
    s.requests[1].resolve({owner:2});await tick();await tick()
    assert.equal(s.usage.value.owner,2)
  } finally {s.dispose()}
})
