import { loadBrowserCrypto } from './helpers/browser-crypto.mjs'
import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {webcrypto} from 'node:crypto'
import vm from 'node:vm'
import ts from 'typescript'

function module(path,dependencies={},globals={}) {
  const source=readFileSync(new URL(path,import.meta.url),'utf8')
  const compiled=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText
  const exports={}
  vm.runInNewContext(compiled,{exports,console,crypto:webcrypto,TextEncoder,...globals,require:name=>{
      if (name.endsWith('/browserCrypto')) return loadBrowserCrypto()

    assert.ok(name in dependencies,'Unexpected module '+name);return dependencies[name]
  }})
  return exports
}
function setup() {
  const values=new Map(),requests=[],auth={profile:{id:1,role:'student'}}
  const storage={getItem:key=>values.get(key)||null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)}
  const identity=()=>module('../src/utils/resourceRequestIdentity.ts',{}, {localStorage:storage})
  const load=()=>module('../src/api/personalizedResources.ts',{
    './http':{http:{post:(url,body)=>new Promise((resolve,reject)=>requests.push({url,body,resolve,reject}))}},
    '../stores/auth':{useAuthStore:()=>auth},'../utils/resourceRequestIdentity':identity(),
  })
  return {api:load(),load,values,requests,auth}
}
async function requestReady(s,count) {
  for(let i=0;i<100 && s.requests.length<count;i++)await new Promise(resolve=>setTimeout(resolve,2))
  assert.equal(s.requests.length,count)
}
const ok=id=>({data:{code:0,data:{task_id:id}}})

test('ambiguous failure and reload reuse one owner-scoped ID; accepted task clears it',async()=>{
  const s=setup(),first=s.api.createResourceTask('loop-for',['learning_bundle'])
  const rejected=assert.rejects(first,/network lost/)
  await requestReady(s,1);const id=s.requests[0].body.idempotency_key
  s.requests[0].reject(new Error('network lost'));await rejected
  assert.equal(s.values.size,1)
  const second=s.load().createResourceTask('loop-for',['learning_bundle']);await requestReady(s,2)
  assert.equal(s.requests[1].body.idempotency_key,id)
  s.requests[1].resolve(ok('accepted'));assert.equal((await second).task_id,'accepted');assert.equal(s.values.size,0)
  const next=s.api.createResourceTask('loop-for',['learning_bundle']);await requestReady(s,3)
  assert.notEqual(s.requests[2].body.idempotency_key,id);s.requests[2].resolve(ok('next'));await next
})

test('concurrent submissions share identity and late responses cannot cross accounts',async()=>{
  const s=setup(),a=s.api.createResourceTask('loop-for'),b=s.api.createResourceTask('loop-for')
  await requestReady(s,2);assert.equal(s.requests[0].body.idempotency_key,s.requests[1].body.idempotency_key)
  const ra=assert.rejects(a,/账号已切换/),rb=assert.rejects(b,/账号已切换/)
  s.auth.profile={id:2,role:'student'};s.requests.forEach(r=>r.resolve(ok('private-old-task')));await Promise.all([ra,rb])
  const c=s.api.createResourceTask('loop-for');await requestReady(s,3)
  assert.notEqual(s.requests[2].body.idempotency_key,s.requests[0].body.idempotency_key)
  s.requests[2].resolve(ok('new-owner'));assert.equal((await c).task_id,'new-owner')
})

test('quota rejection clears unaccepted identity while server uncertainty preserves it',async()=>{
  const s=setup()
  for(const status of [429,503]) {
    const pending=s.api.createResourceTask('loop-for'),failure=assert.rejects(pending)
    await requestReady(s,status===429?1:2);s.requests.at(-1).reject({response:{status}});await failure
    assert.equal(s.values.size,status===429?0:1)
  }
  assert.notEqual(s.requests[0].body.idempotency_key,s.requests[1].body.idempotency_key)
})
