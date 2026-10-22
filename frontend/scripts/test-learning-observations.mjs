import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import ts from 'typescript'
import * as vue from 'vue'

function mount() {
  const source = readFileSync(new URL('../src/components/teacher/LearningObservationsPanel.vue', import.meta.url), 'utf8')
    .match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1]
    + '\nexport const state = {open,days,observations,error,loading,refresh,toggle,latencyRows,milliseconds};'
  const code = ts.transpileModule(source, {compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText
  const exports = {}, requests = [], props = vue.reactive({classId:10}), auth = vue.reactive({profile:{id:1,role:'teacher'}})
  let unmount = () => {}
  const scope = vue.effectScope()
  scope.run(() => vm.runInNewContext(code, {exports, Date, defineProps:() => props, require:name => {
    if (name === 'vue') return {...vue,onBeforeUnmount:fn => {unmount=fn}}
    if (name === '../../stores/auth') return {useAuthStore:() => auth}
    if (name === '../../api/learningObservations') return {fetchLearningObservations:(classId,days) => new Promise((resolve,reject) => requests.push({classId,days,resolve,reject}))}
    throw new Error('Unexpected dependency '+name)
  }}))
  return {...exports.state,props,auth,requests,dispose(){unmount();scope.stop()}}
}
const tick = async () => {await Promise.resolve();await vue.nextTick()}

test('observations load on demand with selected window and ignore old class responses',async()=>{
  const s=mount()
  try {
    assert.equal(s.requests.length,0)
    s.toggle();assert.equal(s.requests[0].days,14);assert.equal(s.requests[0].classId,10)
    s.props.classId=20;assert.equal(s.requests.length,2)
    s.requests[0].resolve({class_id:10});await tick();assert.equal(s.observations.value,null)
    s.requests[1].resolve({class_id:20});await tick();assert.equal(s.observations.value.class_id,20)
    s.days.value=7;assert.equal(s.observations.value,null);assert.equal(s.requests[2].days,7)
    s.requests[2].resolve({window:{days:7}});await tick();assert.equal(s.observations.value.window.days,7)
  } finally {s.dispose()}
})

test('account and role changes clear previous class observations and reject late data',async()=>{
  const s=mount()
  try {
    s.toggle();s.auth.profile={id:2,role:'teacher'}
    s.requests[0].reject(new Error('previous account'));await tick();assert.equal(s.error.value,'')
    s.requests[1].resolve({class_id:10});await tick();assert.notEqual(s.observations.value,null)
    s.auth.profile={id:2,role:'student'};assert.equal(s.observations.value,null);assert.equal(s.requests.length,2)
    s.auth.profile={id:3,role:'teacher'};assert.equal(s.requests.length,3)
    s.auth.profile=null;s.requests[2].resolve({class_id:10});await tick()
    assert.equal(s.observations.value,null);assert.equal(s.loading.value,false)
  } finally {s.dispose()}
})

test('a failed fetch stays unknown and retry can show a genuine zero',async()=>{
  const s=mount()
  try {
    s.toggle();s.requests[0].reject(new Error('offline'));await tick()
    assert.equal(s.observations.value,null);assert.equal(s.error.value,'offline')
    const pending=s.refresh();assert.equal(s.error.value,'')
    s.requests[1].resolve({flow:{requests:0},followup:{observed:0}});await pending
    assert.equal(s.observations.value.followup.observed,0)
  } finally {s.dispose()}
})

test('only the latest refresh can publish and unmounted requests cannot publish',async()=>{
  const s=mount()
  s.toggle();const pending=s.refresh()
  s.requests[1].resolve({revision:2});await pending
  s.requests[0].resolve({revision:1});await tick();assert.equal(s.observations.value.revision,2)
  const late=s.refresh();s.dispose();s.requests[2].resolve({revision:3});await late
  assert.equal(s.observations.value,null)
})

test('unknown latency is never formatted as zero and failed model latency is separate',()=>{
  const s=mount()
  try {
    assert.equal(s.milliseconds(null),'暂无样本');assert.equal(s.milliseconds(0),'0 ms')
    const empty={samples:0,missing:0,p50:null,p95:null}, failed={samples:1,missing:0,p50:4000,p95:4000}
    s.observations.value={latency_ms:{completed_request:empty,finished_attempt:empty,finished_model_call:failed,model_by_status:{failed}}}
    assert.equal(s.latencyRows.value.length,4)
    assert.equal(s.latencyRows.value[0].p50,null)
    assert.equal(s.latencyRows.value[3].label,'模型调用失败')
  } finally {s.dispose()}
})
