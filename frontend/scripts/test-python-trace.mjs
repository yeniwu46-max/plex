// Exercise actual panel request/session handling, with execution HTTP mocked.
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import ts from 'typescript'
import * as vue from 'vue'

function deferred() { let resolve, reject; const promise = new Promise((r,j) => { resolve=r;reject=j }); return {promise,resolve,reject} }
function panel() {
  const props = vue.reactive({code:'x = 1',questionRef:'loop-1',accountId:1,disabled:false})
  const requests=[], reads=[], emitted=[], cleanup=[]
  const source=readFileSync(new URL('../src/components/trial/PythonTracePanel.vue',import.meta.url),'utf8')
    .match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1] + '\nexport const testApi={caps,loading,capabilityError,pending,error,stdin,result,runTrace,loadCapabilities};'
  const code=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText
  const exports={}, scope=vue.effectScope()
  scope.run(() => vm.runInNewContext(code,{exports,console,TextEncoder,
    defineProps:() => props, defineEmits:() => (...args) => emitted.push(args),
    require(name) {
      if(name==='vue') return {...vue,onMounted(){},onBeforeUnmount(fn){cleanup.push(fn)}}
      if(name.endsWith('.vue')) return {default:{}}
      assert.equal(name,'../../api/pythonTrace')
      return {fetchTraceCapabilities(){const req=deferred();reads.push(req);return req.promise},
        tracePython(body){const req=deferred();requests.push({body,...req});return req.promise}}
    },
  }))
  const state=exports.testApi
  state.caps.value={enabled:true,backend_supported:true,max_steps:80}
  return {state,props,requests,reads,emitted,dispose(){cleanup.forEach(fn=>fn());scope.stop()}}
}
const result={run_id:'r1',question_version:'v1',trace_status:'recorded',trace:{steps:[{line:1}]},graded:false}

test('explicit trace runs only current code/stdin; emits owned reference without grades',async()=>{
  const p=panel()
  try {
    p.state.stdin.value='4\n'
    const request=p.state.runTrace()
    assert.equal(p.requests[0].body.code,'x = 1'); assert.equal(p.requests[0].body.stdin,'4\n')
    assert.equal(p.requests[0].body.question_ref,'loop-1')
    assert.equal('test_cases' in p.requests[0].body,false)
    p.requests[0].resolve(result); await request
    assert.equal(p.emitted.length,1); assert.equal(p.emitted[0][0],'recorded')
    assert.equal(p.emitted[0][1].id,'r1'); assert.equal(p.state.pending.value,false)
  } finally {p.dispose()}
})

for (const change of ['code','stdin','account','question','unmount']) {
  test(`late trace response after ${change} cannot display or attach to new context`,async()=>{
    const p=panel()
    try {
      const request=p.state.runTrace()
      if(change==='code') p.props.code='x = 2'
      if(change==='stdin') p.state.stdin.value='different input'
      if(change==='account') p.props.accountId=2
      if(change==='question') p.props.questionRef='loop-2'
      if(change==='unmount') p.dispose()
      p.requests[0].resolve(result); await request
      assert.equal(p.state.result.value,null); assert.equal(p.emitted.length,0)
    } finally {p.dispose()}
  })
}

test('new request survives an obsolete request failure',async()=>{
  const p=panel()
  try {
    const old=p.state.runTrace(); p.props.code='x = 2'
    const current=p.state.runTrace()
    p.requests[0].reject(new Error('obsolete'));await old
    assert.equal(p.state.pending.value,true); assert.equal(p.state.error.value,'')
    p.requests[1].resolve(result);await current
    assert.equal(p.emitted[0][1].code,'x = 2')
  } finally {p.dispose()}
})

test('quota/environment failure and incomplete sandbox output never emit record',async()=>{
  const p=panel()
  try {
    let request=p.state.runTrace();p.requests[0].reject(new Error('unavailable'));await request
    assert.ok(p.state.error.value);assert.equal(p.emitted.length,0)
    request=p.state.runTrace();p.requests[1].resolve({...result,trace_status:'sandbox_limit',trace:null});await request
    assert.match(p.state.error.value,/未获得逐行记录/);assert.equal(p.emitted.length,0)
  } finally {p.dispose()}
})

test('feature flag, isolation, logged out and input size checks avoid execution',async()=>{
  const p=panel()
  try {
    p.state.caps.value.enabled=false;await p.state.runTrace()
    p.state.caps.value={enabled:true,backend_supported:false};await p.state.runTrace()
    p.state.caps.value={enabled:true,backend_supported:true};p.state.stdin.value='中'.repeat(1400);await p.state.runTrace()
    p.state.stdin.value='';p.props.accountId=undefined;await p.state.runTrace()
    assert.equal(p.requests.length,0)
  } finally {p.dispose()}
})

test('late capability response cannot enable previous account settings',async()=>{
  const p=panel()
  try {
    const first=p.state.loadCapabilities();p.props.accountId=2
    p.reads[1].resolve({enabled:false,backend_supported:true});await vue.nextTick()
    p.reads[0].resolve({enabled:true,backend_supported:true});await first
    assert.equal(p.state.caps.value.enabled,false)
  } finally {p.dispose()}
})

test('capability endpoint consumes the execution contract',async()=>{
  const source=readFileSync(new URL('../src/api/pythonTrace.ts',import.meta.url),'utf8')
  const code=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText
  const exports={}
  vm.runInNewContext(code,{exports,require(){return{http:{get:async()=>({data:{code:0,data:{execution:{trace:{enabled:true,backend_supported:true,max_steps:80}}}}})}}}})
  const result=await exports.fetchTraceCapabilities()
  assert.equal(result.enabled,true);assert.equal(result.max_steps,80)
})
