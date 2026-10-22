import { loadBrowserCrypto } from './helpers/browser-crypto.mjs'
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import ts from 'typescript'
import * as vue from 'vue'

function mount(teacher=false) {
  const source = readFileSync(new URL('../src/components/student/LearnerEvidencePanel.vue', import.meta.url),'utf8')
    .match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1]
    +'\nexport const api={state,loading,error,reviewing,notes,history,historyReady,historyLoading,historyError,nextCursor,latestVersion,changes,load,loadMore,review};'
  const code=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText
  const exports={}, stateCalls=[], historyCalls=[], reviewCalls=[]
  const auth=vue.reactive({profile:{id:1,role:teacher?'teacher':'student'}}),props=vue.reactive({studentId:teacher?5:undefined})
  const pending=(list,args)=>new Promise((resolve,reject)=>list.push({args,resolve,reject}))
  let unmount=()=>{},sequence=0
  const scope=vue.effectScope()
  scope.run(()=>vm.runInNewContext(code,{exports,Date,Map,Set,crypto:{randomUUID:()=>`request-${++sequence}`},
    defineProps:()=>props, require:name=>{
      if (name.endsWith('/browserCrypto')) return loadBrowserCrypto({randomUUID:()=>`request-${++sequence}`})

      if(name==='vue')return {...vue,onBeforeUnmount:fn=>{unmount=fn}}
      if(name==='naive-ui')return {}
      if(name==='../../stores/auth')return {useAuthStore:()=>auth}
      if(name==='../../api/learnerState')return {
        fetchLearnerState:(...args)=>pending(stateCalls,args),
        fetchLearningEvidence:(...args)=>pending(historyCalls,args),
        reviewMisconception:(...args)=>pending(reviewCalls,args),
      }
      throw new Error('Unexpected dependency '+name)
    }}))
  return {...exports.api,auth,props,stateCalls,historyCalls,reviewCalls,dispose(){unmount();scope.stop()}}
}
const tick=async()=>{await Promise.resolve();await vue.nextTick();await Promise.resolve()}
const change=v=>({event_id:v,version:v,reason:'server evidence'})
const snapshot=v=>({state_version:v,changes:[change(v)],concepts:[],misconceptions:[]})
const historyPage=(version,versions,cursor=null,latest=version)=>({snapshot_version:version,latest_version:latest,items:versions.map(change),next_cursor:cursor,has_more:!!cursor})
async function ready(s,version=3,versions=[3,2],cursor='cursor-1'){
  s.stateCalls.at(-1).resolve(snapshot(version));await tick()
  s.historyCalls.at(-1).resolve(historyPage(version,versions,cursor));await tick();await tick()
}

test('history uses the visible state version, loads older pages and keeps newer evidence separate',async()=>{
  const s=mount()
  try{
    assert.equal(s.stateCalls.length,1)
    await ready(s)
    assert.equal(s.historyCalls[0].args[1].snapshot_version,3)
    assert.equal(s.changes.value.length,2)
    const more=s.loadMore()
    assert.equal(s.historyCalls[1].args[1].cursor,'cursor-1')
    s.historyCalls[1].resolve(historyPage(3,[1],null,4));await more
    assert.deepEqual(Array.from(s.changes.value,x=>x.version),[3,2,1])
    assert.equal(s.state.value.state_version,3);assert.equal(s.latestVersion.value,4)
    await s.loadMore();assert.equal(s.historyCalls.length,2)
  }finally{s.dispose()}
})

test('failed page retains earlier records and cursor; retries and double clicks cannot duplicate rows',async()=>{
  const s=mount()
  try{
    await ready(s)
    const more=s.loadMore();await s.loadMore();assert.equal(s.historyCalls.length,2)
    s.historyCalls[1].reject(new Error('offline'));await more
    assert.equal(s.historyError.value,'offline');assert.equal(s.nextCursor.value,'cursor-1')
    assert.equal(s.changes.value.length,2)
    const retry=s.loadMore();assert.equal(s.historyCalls[2].args[1].cursor,'cursor-1')
    s.historyCalls[2].resolve(historyPage(3,[2,1]));await retry
    assert.deepEqual(Array.from(s.changes.value,x=>x.version),[3,2,1])
  }finally{s.dispose()}
})

test('initial history failure keeps compact evidence and can retry without losing the pinned version',async()=>{
  const s=mount()
  try{
    s.stateCalls[0].resolve(snapshot(8));await tick()
    s.historyCalls[0].reject(new Error('history unavailable'));await tick();await tick()
    assert.equal(s.historyReady.value,false);assert.equal(s.changes.value[0].version,8)
    const retry=s.loadMore();assert.equal(s.historyCalls[1].args[1].snapshot_version,8)
    s.historyCalls[1].resolve(historyPage(8,[8,7]));await retry
    assert.equal(s.historyReady.value,true);assert.equal(s.historyError.value,'')
  }finally{s.dispose()}
})

test('switching students and accounts clears notes and never shows late state or history',async()=>{
  const s=mount(true)
  try{
    s.notes.value[1]='old student note'
    s.props.studentId=6
    assert.equal(s.stateCalls[1].args[0],6);assert.equal(s.notes.value[1],undefined)
    s.stateCalls[0].resolve(snapshot(5));await tick();assert.equal(s.state.value,null)
    s.stateCalls[1].resolve(snapshot(6));await tick();assert.equal(s.historyCalls[0].args[0],6)
    s.auth.profile={id:2,role:'teacher'};assert.equal(s.state.value,null)
    s.historyCalls[0].resolve(historyPage(6,[6]));await tick();assert.equal(s.changes.value.length,0)
    s.auth.profile={id:2,role:'student'}
    s.stateCalls[2].resolve(snapshot(9));await tick();assert.equal(s.state.value,null)
    assert.equal(s.loading.value,false);assert.equal(s.stateCalls.length,3)
  }finally{s.dispose()}
})

test('refresh invalidates an in-flight old page and a mismatched history version is not merged',async()=>{
  const s=mount()
  try{
    await ready(s)
    const more=s.loadMore();const refresh=s.load()
    s.historyCalls[1].resolve(historyPage(3,[1]));await more;assert.equal(s.state.value,null)
    s.stateCalls[1].resolve(snapshot(5));await tick()
    s.historyCalls[2].resolve(historyPage(6,[6]));await refresh
    assert.equal(s.historyReady.value,false);assert.equal(s.changes.value[0].version,5)
    assert.match(s.historyError.value,/版本已变化/)
  }finally{s.dispose()}
})

test('review retry retains its request ID and successful review resets history to the new state',async()=>{
  const s=mount(true),item={id:7,revision:2}
  try{
    await ready(s);s.notes.value[7]='Reviewed against observed attempts.'
    const first=s.review(item,'confirm');s.reviewCalls[0].reject(new Error('network'));await first
    const retry=s.review(item,'confirm')
    assert.equal(s.reviewCalls[1].args[2].request_id,s.reviewCalls[0].args[2].request_id)
    s.reviewCalls[1].resolve(snapshot(4));await tick()
    assert.equal(s.historyCalls[1].args[1].snapshot_version,4)
    s.historyCalls[1].resolve(historyPage(4,[4,3]));await retry
    assert.equal(s.state.value.state_version,4);assert.equal(s.notes.value[7],'')
  }finally{s.dispose()}
})

test('a review result from a previous student cannot overwrite the current student',async()=>{
  const s=mount(true),item={id:7,revision:2}
  try{
    await ready(s);s.notes.value[7]='Teacher explanation'
    const oldReview=s.review(item,'dismiss')
    s.props.studentId=6
    s.stateCalls[1].resolve(snapshot(10));await tick()
    s.historyCalls[1].resolve(historyPage(10,[10]));await tick();await tick()
    s.reviewCalls[0].resolve(snapshot(4));await oldReview
    assert.equal(s.state.value.state_version,10);assert.equal(s.reviewing.value,null)
  }finally{s.dispose()}
})

test('logout or unmount cannot publish a pending history result',async()=>{
  const s=mount()
  s.stateCalls[0].resolve(snapshot(3));await tick()
  s.auth.profile=null;s.historyCalls[0].resolve(historyPage(3,[3]));await tick()
  assert.equal(s.state.value,null)
  s.auth.profile={id:2,role:'student'}
  s.stateCalls[1].resolve(snapshot(2));await tick()
  s.dispose();s.historyCalls[1].resolve(historyPage(2,[2]));await tick()
  assert.equal(s.historyReady.value,false)
})
