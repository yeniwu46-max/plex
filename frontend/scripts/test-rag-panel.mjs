import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import vm from 'node:vm'
import ts from 'typescript'
import * as vue from 'vue'

function mount() {
  const source=readFileSync(new URL('../src/components/admin/AdminRagDebugPanel.vue',import.meta.url),'utf8')
    .match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1]+
    '\nexport const state={run,recover,query,answerResult,retrieveResult,running,recovering,recoveryStatus,lastRequest,loadLogs,logs,logLoading};'
  const code=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText
  const exports={},requests=[],messages=[],auth=vue.reactive({profile:{id:1,role:'admin'}})
  const call=kind=>(body)=>new Promise((resolve,reject)=>requests.push({kind,body,resolve,reject}))
  let unmount=()=>{}
  const scope=vue.effectScope()
  scope.run(()=>vm.runInNewContext(code,{exports,require:name=>{
    if(name==='vue')return {...vue,onBeforeUnmount:fn=>{unmount=fn}}
    if(name==='../../stores/auth')return {useAuthStore:()=>auth}
    if(name==='naive-ui')return {useMessage:()=>({warning:m=>messages.push(m),error:m=>messages.push(m)})}
    if(name==='../../api/knowledge')return {KNOWLEDGE_TYPE_LABELS:{}}
    if(name==='../../api/rag')return {ragQuery:call('query'),ragRetrieve:call('retrieve'),fetchRagRequest:call('recover'),
      fetchRagLog:call('log'),fetchRagLogs:call('logs'),latestRagRequest:owner=>'request-'+owner}
    if(name.startsWith('@vicons/')||name.endsWith('.vue'))return {}
    throw Error('Unexpected dependency '+name)
  }}))
  return {...exports.state,requests,messages,auth,dispose(){unmount();scope.stop()}}
}

test('panel recovery makes a read only call, reports processing, then displays the saved answer',async()=>{
  const s=mount()
  try {
    let pending=s.recover();assert.equal(s.requests[0].kind,'recover')
    s.requests[0].resolve({status:'processing',answer:null,attempts_remaining:2});await pending
    assert.equal(s.answerResult.value,null);assert.match(s.recoveryStatus.value,/仍在处理/)
    pending=s.recover();s.requests[1].resolve({status:'complete',answer:{answer:'saved'}});await pending
    assert.equal(s.answerResult.value.answer,'saved');assert.equal(s.requests.length,2)
  } finally {s.dispose()}
})

test('running query ignores double clicks and old answers/errors after account change or unmount',async()=>{
  const s=mount();s.query.value='loop'
  const pending=s.run();await s.run();assert.equal(s.requests.length,1)
  s.auth.profile={id:2,role:'admin'};s.requests[0].resolve({answer:'private old answer'});await pending
  assert.equal(s.answerResult.value,null);assert.equal(s.query.value,'');assert.equal(s.lastRequest.value,'request-2')
  const recovery=s.recover();s.dispose();s.requests[1].reject(Error('private old failure'));await recovery
  assert.equal(s.recoveryStatus.value,'');assert.equal(s.messages.length,0)
})

test('question submission does not invalidate independent log loading',async()=>{
  const s=mount()
  try {
    const logs=s.loadLogs();s.query.value='loop';const answer=s.run()
    s.requests[0].resolve({items:[{id:1}],total:1});await logs
    assert.equal(s.logs.value.length,1);assert.equal(s.logLoading.value,false)
    s.requests[1].resolve({answer:'new'});await answer
    assert.equal(s.answerResult.value.answer,'new')
  } finally {s.dispose()}
})
