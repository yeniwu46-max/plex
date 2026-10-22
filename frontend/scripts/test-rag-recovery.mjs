import { loadBrowserCrypto } from './helpers/browser-crypto.mjs'
import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {webcrypto} from 'node:crypto'
import vm from 'node:vm'
import ts from 'typescript'

function module(path, dependencies={}, globals={}) {
  const source=readFileSync(new URL(path,import.meta.url),'utf8')
  const code=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText
  const exports={}
  vm.runInNewContext(code,{exports,crypto:webcrypto,TextEncoder,...globals,require:name=>{
      if (name.endsWith('/browserCrypto')) return loadBrowserCrypto()

    assert.ok(name in dependencies,'Unexpected dependency '+name);return dependencies[name]
  }})
  return exports
}
function setup(blocked=false) {
  const values=new Map(),requests=[],auth={profile:{id:1,role:'admin'}}
  const storage={getItem:k=>{if(blocked)throw Error('blocked');return values.get(k)||null},setItem:(k,v)=>{if(blocked)throw Error('blocked');values.set(k,v)},removeItem:k=>values.delete(k)}
  const load=()=>module('../src/api/rag.ts',{
    './http':{formatHttpError:(e,f)=>e.message||f,http:{
      post:(url,body)=>new Promise((resolve,reject)=>requests.push({url,body,resolve,reject})),
      get:url=>new Promise((resolve,reject)=>requests.push({url,resolve,reject})),
    }},'../stores/auth':{useAuthStore:()=>auth},
    '../utils/ragRequestIdentity':module('../src/utils/ragRequestIdentity.ts',{}, {localStorage:storage}),
  })
  return {api:load(),load,values,requests,auth}
}
async function ready(s,n) {
  for(let i=0;i<100 && s.requests.length<n;i++)await new Promise(r=>setTimeout(r,2))
  assert.equal(s.requests.length,n)
}
const ok=data=>({data:{code:0,data}})
const question={query:'private question',debug:true,context:{title:'private title',concept_hint:'loop'}}

test('network loss, reload and processing conflict retain the same request without storing private text',async()=>{
  const s=setup();let pending=s.api.ragQuery(question),failure=assert.rejects(pending)
  await ready(s,1);const id=s.requests[0].body.request_id;s.requests[0].reject(new Error('network'));await failure
  assert.ok([...s.values].every(([k,v])=>!k.includes('private')&&!v.includes('private')))
  assert.equal(s.api.latestRagRequest(1),id)
  const reloaded=s.load()
  pending=reloaded.ragQuery({context:{concept_hint:'loop',title:'private title'},debug:true,query:'private question'});failure=assert.rejects(pending)
  await ready(s,2);assert.equal(s.requests[1].body.request_id,id)
  s.requests[1].reject({response:{status:409,data:{data:{reason:'request_in_progress'}}}});await failure
  pending=s.api.ragQuery(question);await ready(s,3);assert.equal(s.requests[2].body.request_id,id)
  s.requests[2].resolve(ok({request_id:id,answer:'accepted'}));assert.equal((await pending).answer,'accepted')
  pending=reloaded.ragQuery(question);await ready(s,4);assert.notEqual(s.requests[3].body.request_id,id)
  s.requests[3].resolve(ok({answer:'new'}));await pending
})

test('recovery only reads and account changes cannot expose old answers',async()=>{
  const s=setup(),rid=webcrypto.randomUUID(),pending=s.api.fetchRagRequest(rid)
  await ready(s,1);assert.equal(s.requests[0].url,`/v1/rag/requests/${rid}`);assert.equal(s.requests[0].body,undefined)
  const failure=assert.rejects(pending,/账号已切换/);s.auth.profile={id:2,role:'admin'}
  s.requests[0].resolve(ok({status:'complete',answer:{answer:'private answer'}}));await failure
  const query=s.api.ragQuery(question),reject=assert.rejects(query,/账号已切换/)
  await ready(s,2);s.auth.profile={id:2,role:'student'};s.requests[1].resolve(ok({answer:'old role'}));await reject
})

test('quota uncertainty retains failed chain, revoked sources clear identity, explicit IDs are respected',async()=>{
  const s=setup();let pending=s.api.ragQuery(question),failure=assert.rejects(pending)
  await ready(s,1);const id=s.requests[0].body.request_id
  s.requests[0].reject({response:{status:429,data:{data:{reason:'daily_limit'}}}});await failure
  pending=s.api.ragQuery(question);failure=assert.rejects(pending);await ready(s,2);assert.equal(s.requests[1].body.request_id,id)
  s.requests[1].reject({response:{status:409,data:{data:{reason:'sources_changed'}}}});await failure
  pending=s.api.ragQuery(question);await ready(s,3);assert.notEqual(s.requests[2].body.request_id,id)
  s.requests[2].resolve(ok({answer:'new'}));await pending
  const explicit=webcrypto.randomUUID();pending=s.api.ragQuery({...question,request_id:explicit});await ready(s,4)
  assert.equal(s.requests[3].body.request_id,explicit);s.requests[3].resolve(ok({request_id:explicit}));await pending
})

test('blocked local storage still protects same-page retry and concurrent calls',async()=>{
  const s=setup(true),a=s.api.ragQuery(question),b=s.api.ragQuery(question)
  const failures=[assert.rejects(a),assert.rejects(b)]
  await ready(s,2);assert.equal(s.requests[0].body.request_id,s.requests[1].body.request_id)
  s.requests.forEach(r=>r.reject(new Error('network')));await Promise.all(failures)
  const retry=s.api.ragQuery(question);await ready(s,3);assert.equal(s.requests[2].body.request_id,s.requests[0].body.request_id)
  s.requests[2].resolve(ok({answer:'done'}));await retry
})
