// Run the actual stores and route guard with Vue/Pinia and controlled HTTP.
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import ts from 'typescript'
import * as vue from 'vue'
import * as pinia from 'pinia'

function execute(path, modules, globals = {}) {
  const exports = {}
  const source = readFileSync(new URL(path, import.meta.url), 'utf8').replaceAll('import.meta.env', '({})')
  const code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, esModuleInterop: true } }).outputText
  vm.runInNewContext(code, { exports, require: name => {
    assert.ok(name in modules, name); return modules[name]
  }, setTimeout, ...globals })
  return exports
}
function storage(initial = []) {
  const values = new Map(initial)
  return { getItem: k => values.get(k) ?? null, setItem: (k,v) => values.set(k,v), removeItem: k => values.delete(k) }
}
function authSetup() {
  pinia.setActivePinia(pinia.createPinia())
  const localStorage = storage([['access','a'],['refresh','r'],['profile',JSON.stringify({ id:1, role:'student' })]])
  const pending = []
  const http = { get: () => new Promise((resolve, reject) => pending.push({ resolve, reject })) }
  const store = execute('../src/stores/auth.ts', {
    pinia, vue, axios: {}, '../api/http': { http, storageKeys:{ access:'access',refresh:'refresh',profile:'profile' } },
  }, { localStorage, window:{addEventListener(){}} }).useAuthStore()
  return { store, pending }
}
const arrival = {status:'pending',required:true,adventurer_number:null,welcome_pending:false}

test('restoring a session waits for the server and coalesces account requests', async () => {
  const {store,pending} = authSetup()
  const a = store.ensureAccount(), b = store.ensureAccount()
  assert.equal(pending.length,1)
  assert.equal(store.accountReady,false)
  pending[0].resolve({data:{code:0,data:{onboarding:arrival}}})
  await Promise.all([a,b])
  assert.equal(store.profile.onboarding.required,true)
  assert.equal(store.accountReady,true)
})
test('offline restore remains retryable and does not bypass onboarding', async () => {
  const {store,pending} = authSetup()
  const first = store.ensureAccount(); const rejected = assert.rejects(first)
  pending[0].reject(new Error('offline')); await rejected
  assert.equal(store.accountReady,false)
  const retry = store.ensureAccount()
  pending[1].resolve({data:{code:0,data:{onboarding:arrival}}}); await retry
  assert.equal(store.accountReady,true)
})
test('stale account response cannot overwrite a switched account', async () => {
  const {store,pending} = authSetup()
  const first = store.ensureAccount(); const rejected = assert.rejects(first,/登录状态已变化/)
  store.acceptSession({id:2,role:'student',access_token:'b',refresh_token:'s',onboarding:arrival})
  pending[0].resolve({data:{code:0,data:{id:1,onboarding:arrival}}}); await rejected
  assert.equal(store.profile.id,2)
})
test('route guard redirects pending and failed loads, while leaving staff and welcome page accessible', async () => {
  let guard
  const auth = {isAuthenticated:true,profile:{role:'student',onboarding:arrival},ensureAccount:async()=>{},homePathForRole:()=>'/student'}
  execute('../src/router/index.ts', {
    'vue-router':{createWebHistory(){},createRouter:()=>({beforeEach:fn=>guard=fn,afterEach(){}})},
    '../stores/auth':{useAuthStore:()=>auth},
  })
  const target = {name:'student-messenger',fullPath:'/student/messenger?conversation=2',meta:{},matched:[{meta:{roles:['student']}}]}
  assert.equal((await guard(target)).query.redirect,target.fullPath)
  assert.equal(await guard({...target,name:'student-onboarding'}),true)
  auth.profile.onboarding = {...arrival,required:false}
  assert.equal(await guard(target),true)
  auth.ensureAccount = async()=>{throw new Error('offline')}
  assert.equal((await guard(target)).name,'student-onboarding')
  auth.profile.role='teacher'
  assert.equal(await guard({...target,matched:[{meta:{roles:['teacher']}}]}),true)
})
test('appearance respects server preferences, restores guest mode and isolates accounts', async () => {
  pinia.setActivePinia(pinia.createPinia())
  const localStorage = storage()
  const writes = []
  const theme = execute('../src/stores/theme.ts', {
    pinia, vue,
    '@vueuse/core':{usePreferredDark:()=>vue.ref(true),useColorMode:()=>vue.ref('dark'),useStorage:(_key,value)=>vue.ref(value)},
    '../api/onboarding':{saveAppearance:async value=>writes.push(value)},
  }, {localStorage,document:{documentElement:{dataset:{},classList:{add(){},remove(){}},setAttribute(){}}}}).useThemeStore()
  theme.bindAccount(null)
  assert.equal(theme.visualStyle,'space')
  theme.bindAccount(1,{visual_style:'comic',color_mode:'light'})
  assert.equal(theme.resolvedTheme,'light')
  theme.bindAccount(2,null)
  assert.equal(theme.visualStyle,'space')
  assert.equal(theme.mode,'dark')
  theme.setVisualStyle('comic'); await new Promise(resolve=>setTimeout(resolve,0))
  assert.equal(writes.length,1)
  theme.bindAccount(null)
  assert.equal(theme.visualStyle,'space')
  theme.bindAccount(2,null)
  assert.equal(theme.visualStyle,'comic')
  theme.bindAccount(2,{visual_style:'space',color_mode:'auto'})
  assert.equal(theme.mode,'auto')
  assert.equal(theme.visualStyle,'space')
})
