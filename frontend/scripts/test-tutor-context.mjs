import { httpCrypto, loadBrowserCrypto } from './helpers/browser-crypto.mjs'
// Exercise the actual async workspace script against controlled execution I/O.
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import ts from 'typescript'
import * as vue from 'vue'

function deferred() {
  let resolve, reject
  const promise = new Promise((r, j) => { resolve = r; reject = j })
  return { promise, resolve, reject }
}

function component(path, bindings, props, modules, globals = {}) {
  const source = readFileSync(new URL(path, import.meta.url), 'utf8').match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1]
    + `\nexport const testApi = { ${bindings} };`
  const code = ts.transpileModule(source, {compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText
  const exports = {}
  const scope = vue.effectScope()
  scope.run(() => vm.runInNewContext(code, {
    exports, console, Date, Error, ...globals,
    defineOptions(){}, defineProps:() => props, withDefaults:p => p, defineEmits:() => (...args) => globals.emit?.(...args),
    require: name => {
      if (name.endsWith('/browserCrypto')) return loadBrowserCrypto(globals.crypto)

      if (name === 'vue') return {...vue,onMounted(){},onBeforeUnmount(){},onActivated(){},onDeactivated(){}}
      if (name.endsWith('.vue')) return {default:{}}
      assert.ok(name in modules, `Unexpected dependency: ${name}`)
      return modules[name]
    },
  }))
  return {...exports.testApi, dispose:() => scope.stop()}
}

function workspace(gradeResult = {code_passed:false,passed_count:0,total:1}) {
  const runs = [], grades = [], records = [], feedbacks = [], acks = [], cancels = [], events = [], notices = []
  const auth = vue.reactive({profile:{id:1,role:'student'}})
  const document = {visibilityState:'visible'}
  const props = vue.reactive({question:{id:'bank-1',title:'Test task',testCases:[{id:'1',label:'sample',expected:'1'}],runMode:'stdout',topic:'loop',tags:[]},trialQuestionId:1,slotIds:[]})
  const store = component('../src/components/trial/PythonTrialWorkspace.vue',
    'code, onRun, onManualSubmit, onReset, lastRun, runIsStale, caseResults, running, fetchAiFeedback, agentResult, agentLoading, agentError, feedbackIsStale, leftPanel, acknowledgeVisibleFeedback, cancelAiFeedback, agentLoading', props, {
      'vue-router':{useRoute:() => ({query:{},params:{}}),useRouter:() => ({})},
      'naive-ui':{useMessage:() => Object.fromEntries(['info','warning','success','error'].map(level => [level,text => notices.push({level,text})]))},
      '../../stores/auth':{useAuthStore:() => auth},
      '../../stores/notifications':{useNotificationStore:() => ({push(){}})},
      '../../utils/trialMistakeLog':{getTrialAttemptHistory:() => [],recordTrialRun:(...args) => records.push(args)},
      '../../api/studentPractice':{submitPractice:async()=>({result:{all_passed:false}})},
      '../../api/studentAssignments':{submitTrialCodeAnswer:async (...args) => {grades.push(args); return typeof gradeResult === 'function' ? gradeResult() : gradeResult}},
      '../../api/studentOverview':{advanceDailyQuest:async () => {}},
      '../../api/tutoring':{cancelTutorTurn:id => {const pending=deferred();cancels.push({id,...pending});return pending.promise},askTutor:body => {const pending = deferred(); feedbacks.push({body,...pending}); return pending.promise}},
      '../../api/learnerState':{acknowledgeTutorDisplay:async id => acks.push(id)},
      '../../api/codeRunner':{submitCode:body => {const pending = deferred(); runs.push({body,...pending}); return pending.promise}},
      '../../utils/pythonSourceNormalization':{normalizePythonSource:code => ({code,replacements:0}),concisePythonError:s => s},
      '../../utils/xiaoEPersona':{},
    }, {document,emit:(...args) => events.push(args),crypto:{randomUUID:() => `request-${feedbacks.length}`}})
  return {store, props, runs, grades, records, feedbacks, acks, auth, document, cancels, events, notices}
}
const response = {run_id:'run-1',question_version:'v1',results:[{case_id:'1',label:'sample',passed:false,expected:'1',actual:'',error:'NameError'}]}

test('editing while execution is pending never submits or records the edited code as executed', async () => {
  const {store,runs,grades,records} = workspace()
  try {
    store.code.value = 'print(old_value)'
    const pending = store.onRun()
    store.code.value = 'print(new_value)'
    runs[0].resolve(response); await pending
    assert.equal(runs[0].body.code,'print(old_value)')
    assert.equal(grades[0][1],'print(old_value)')
    assert.equal(records[0].at(-1),'print(old_value)')
    assert.equal(store.lastRun.value.code,'print(old_value)')
    assert.equal(store.runIsStale.value,true)
  } finally {store.dispose()}
})

test('switching questions discards a late run and cannot submit it to the new formal question', async () => {
  const {store,props,runs,grades,records} = workspace()
  try {
    store.code.value = 'print(old_value)'
    const pending = store.onRun()
    props.question = {...props.question,id:'bank-2'}; props.trialQuestionId = 2
    await vue.nextTick()
    runs[0].resolve(response); await pending
    assert.equal(grades.length,0); assert.equal(records.length,0)
    assert.equal(store.lastRun.value,null); assert.equal(store.caseResults.value.length,0)
  } finally {store.dispose()}
})

test('reset invalidates the pending run and a newer run owns the displayed results', async () => {
  const {store,runs,grades} = workspace()
  try {
    store.code.value = 'print(1)'; const old = store.onRun()
    store.onReset(); store.code.value = 'print(2)'; const next = store.onRun()
    runs[0].resolve(response); await old
    assert.equal(store.running.value,true); assert.equal(grades.length,0)
    runs[1].resolve({...response,run_id:'run-2'}); await next
    assert.equal(store.lastRun.value.id,'run-2'); assert.equal(grades[0][1],'print(2)')
  } finally {store.dispose()}
})

test('a direct practice link recomputes its question after the async non-reactive cache loads', async () => {
  const ready = deferred(), cache = new Map()
  const route = vue.reactive({params:{questionId:'bank-1'},query:{}})
  const q = {id:'bank-1',description:'Public task',title:'Test task',tags:[],testCases:[]}
  const store = component('../src/views/StudentTrialPracticeView.vue', 'question, loadQuestion', {}, {
    'vue-router':{useRoute:() => route,useRouter:() => ({})}, 'naive-ui':{useMessage:() => ({})},
    '../data/pythonTrialQuestions':{getPythonTrialQuestion:() => null},
    '../data/starPathTrail':{getStarPathNodeByQuestionId:() => null},
    '../data/starPathDomains':{getStarPathKnowledgePoint:() => null},
    '../utils/starPathQuestionGenerator':{resolveQuestionById:() => null},
    '../data/starPathKnowledgeTracks':{MIN_QUESTIONS_PER_KP:5},
    '../utils/practiceQuestionCache':{ensurePracticeQuestionsLoaded:() => ready.promise,getCachedPracticeQuestion:id => cache.get(id)},
    '../api/practiceQuestions':{fetchPracticeQuestionByRef:() => {throw new Error('cache should resolve task')}},
    '../api/studentStore':{}, '../utils/questionNaming':{normalizeQuestion:q => q},
    '../utils/explorationNarrative':{}, '../utils/questionStemSanitizer':{sanitizeQuestionContent:q => q},
    '../utils/practiceQuestionNav':{},
  })
  try {
    assert.equal(store.question.value,null)
    const pending = store.loadQuestion('bank-1')
    cache.set('bank-1',q); ready.resolve(); await pending
    assert.equal(store.question.value.id,'bank-1')
  } finally {store.dispose()}
})

test('coach keeps the conversation when code changes, resets on question change and fits a resized viewport', async () => {
  const props = vue.reactive({context:{exerciseId:'bank-1',code:'old',caseResults:[],allPassed:false,questionTitle:'Task'}})
  const window = {innerWidth:1440,innerHeight:1000}
  const store = component('../src/components/trial/TrialAiFloatingBall.vue',
    'messages, dialogStyle, onWindowResize, includeCode', props, {
      'naive-ui':{useMessage:() => ({})}, '../../api/learnerState':{}, '../../api/tutoring':{cancelTutorTurn:id => {const pending=deferred();cancels.push({id,...pending});return pending.promise},askTutor:body => {const pending = deferred(); feedbacks.push({body,...pending}); return pending.promise}},
      '../../api/learnerState':{acknowledgeTutorDisplay:async id => acks.push(id)},
      '../../composables/useSpeechRecognitionInput':{useSpeechRecognitionInput:() => ({listening:vue.ref(false),toggle(){}})},
      '../../stores/auth':{useAuthStore:()=>({profile:{id:1}})},
      '../../utils/xiaoEPersona':{}, '../../utils/trialCoachPresentation':{}, '../../api/tutorContext':{},
      '../../api/tutoring':{tutorModes:[]},
    }, {window})
  try {
    store.messages.value.push({id:'1',role:'assistant',content:'Check the name',codeSnapshot:'old'})
    props.context = {...props.context,code:'new'}; await vue.nextTick()
    assert.equal(store.messages.value.length,1)
    assert.notEqual(store.messages.value[0].codeSnapshot,props.context.code)
    window.innerWidth = 390; window.innerHeight = 600; store.onWindowResize()
    const style = store.dialogStyle.value
    assert.ok(parseFloat(style.width) <= 350)
    assert.ok(parseFloat(style.top) >= 20)
    assert.ok(parseFloat(style.height) + parseFloat(style.top) <= 580)
    props.context = {...props.context,exerciseId:'bank-2'}; await vue.nextTick()
    assert.equal(store.messages.value.length,0)
  } finally {store.dispose()}
})

test('mode tutoring retries the identical request and labels a response against the submitted code snapshot', async () => {
  const requests = [], acknowledgements = []
  const auth=vue.reactive({profile:{id:1}})
  const props = vue.reactive({context:{exerciseId:'bank-1',code:'old',runId:'run-1',caseResults:[],allPassed:false,questionTitle:'Task'}})
  const store = component('../src/components/trial/TrialAiFloatingBall.vue',
    'messages, contextLoaded, verifiedContext, dialogOpen, sendQuestion', props, {
      'naive-ui':{useMessage:() => ({warning(){},error(){},success(){},info(){}})},
      '../../api/learnerState':{acknowledgeTutorDisplay:id => {acknowledgements.push(id); return Promise.resolve()}},
      '../../api/tutoring':{tutorModes:[],askTutor:body => {const task=deferred(); requests.push({body,...task}); return task.promise}},
      '../../composables/useSpeechRecognitionInput':{useSpeechRecognitionInput:() => ({listening:vue.ref(false),toggle(){}})},
      '../../stores/auth':{useAuthStore:()=>auth},
      '../../utils/xiaoEPersona':{}, '../../api/tutorContext':{fetchTutorContext:async()=>({task:{version:'v1'}})},
    }, {window:{innerWidth:1440,innerHeight:900},document:{visibilityState:'visible'},crypto:httpCrypto})
  try {
    store.contextLoaded.value = true; store.dialogOpen.value = true
    store.verifiedContext.value = {task:{version:'v1'}}
    const pending = store.sendQuestion('检查我的思路', 'review_approach')
    await new Promise(resolve => setImmediate(resolve)); requests[0].reject(new Error('connection lost')); await pending
    const retry = store.messages.value.at(-1).retry
    props.context.code = 'new'
    const again = store.sendQuestion(retry.question, retry.mode, retry)
    await new Promise(resolve => setImmediate(resolve))
    assert.deepEqual(requests[1].body, requests[0].body)
    assert.equal(requests[1].body.code,'old'); assert.equal(requests[1].body.run_id,'run-1')
    requests[1].resolve({session_id:'s1',summary:'已核对',display_receipt_id:'receipt-1',teaching_plan:{hint_level:2}})
    await again
    assert.equal(store.messages.value.at(-1).codeSnapshot,'old')
    assert.deepEqual(acknowledgements,['receipt-1'])
    const switching=store.sendQuestion('下一步','next_step');await new Promise(resolve=>setImmediate(resolve))
    store.dialogOpen.value=false;auth.profile.id=2;await vue.nextTick()
    requests[2].resolve({session_id:'old',summary:'OLD-ACCOUNT',display_receipt_id:'old',teaching_plan:{hint_level:2}});await switching
    assert.equal(store.messages.value.length,0);assert.deepEqual(acknowledgements,['receipt-1'])
  } finally {store.dispose()}
})

test('messenger mode responses cannot cross into another chat or account while pending', async () => {
  const requests = [], acknowledgements = []
  const restores = []
  const sessions = vue.ref([{id:'a',messages:[]},{id:'b',messages:[]}]), active = vue.ref('a')
  const auth = vue.reactive({profile:{id:1}})
  const store = component('../src/views/MessengerView.vue',
    'tutorMode, tutorCode, tutorRestoring, chatMessages, chatLoading, sendTutorQuestion', {}, {
      'vue-router':{useRoute:() => ({query:{},params:{}}),useRouter:() => ({})},'naive-ui':{useMessage:() => ({warning(){},error(){},success(){},info(){}})},
      '@vicons/ionicons5':{},
      '../api/messenger':{}, '../api/agentService':{}, '../stores/theme':{useThemeStore:() => ({isComic:false})},
      '../api/tutoring':{tutorModes:[],askTutor:body => {const task=deferred();requests.push({body,...task});return task.promise},
        fetchTutorTurn:id => {const task=deferred();restores.push({id,...task});return task.promise}},
      '../api/codeRunner':{}, '../api/http':{formatHttpError:e => e.message}, '../stores/auth':{useAuthStore:() => auth},
      '../api/learnerState':{acknowledgeTutorDisplay:id => {acknowledgements.push(id);return Promise.resolve()}},
      '../utils/xiaoEPersona':{}, '../utils/practiceQuestionNav':{},
      '../composables/useSpeechRecognitionInput':{useSpeechRecognitionInput:() => ({listening:vue.ref(false),toggle(){}})},
      '../composables/useMessengerChatSessions':{useMessengerChatSessions:() => ({sessions,activeSessionId:active,
        activeSession:vue.computed(() => sessions.value.find(s=>s.id===active.value)),setSessionMessages(){}})},
    }, {window:{requestAnimationFrame:() => 1},document:{visibilityState:'visible'},crypto:{randomUUID:()=> 'request-1'}})
  try {
    store.tutorMode.value = 'next_step'; store.tutorCode.value = 'first-code'
    const pending = store.sendTutorQuestion('下一步')
    active.value = 'b'; await vue.nextTick()
    requests[0].resolve({session_id:'server-a',summary:'belongs to a',display_receipt_id:'receipt-a'})
    await pending
    assert.equal(store.chatMessages.value.length,0)
    assert.deepEqual(acknowledgements,[])
    assert.equal(store.tutorMode.value,null)
    store.tutorMode.value='next_step'
    const next = store.sendTutorQuestion('另一个问题')
    assert.equal(requests[1].body.session_id,undefined)
    auth.profile.id = 2; await vue.nextTick()
    requests[1].resolve({session_id:'server-b',summary:'belongs to old account',display_receipt_id:'receipt-b'})
    await next
    assert.ok(!store.chatMessages.value.some(m => m.role === 'assistant'))
    assert.deepEqual(acknowledgements,[])
    sessions.value[0].messages = [{role:'assistant',text:'正在核对',tutorRequestId:'saved-request'}]
    active.value = 'a'; await vue.nextTick()
    assert.equal(store.tutorRestoring.value,true)
    await store.sendTutorQuestion('等待恢复时不另建会话')
    assert.equal(requests.length,2)
    restores[0].resolve({request_id:'saved-request',session_id:'restored-session',summary:'服务端核对后的记录',display_receipt_id:null})
    await new Promise(resolve => setImmediate(resolve))
    assert.equal(store.tutorRestoring.value,false)
    assert.equal(store.chatMessages.value[0].tutor.summary,'服务端核对后的记录')
    store.tutorMode.value='next_step'
    const resumed = store.sendTutorQuestion('继续这个会话')
    assert.equal(requests[2].body.session_id,'restored-session')
    requests[2].resolve({session_id:'restored-session',summary:'新回复',display_receipt_id:null})
    await resumed
  } finally {store.dispose()}
})


test('workspace feedback binds owned runs and retries the original request after edits', async () => {
  const {store,feedbacks,acks} = workspace()
  try {
    store.code.value = 'print(old_value)'
    store.lastRun.value = {id:'run-1',code:'print(old_value)',version:'v1'}
    const pending = store.fetchAiFeedback()
    assert.equal(feedbacks[0].body.run_id,'run-1')
    store.code.value = 'print(new_value)'
    feedbacks[0].reject(new Error('network unavailable')); await pending
    const retry = store.fetchAiFeedback(true)
    assert.deepEqual(feedbacks[1].body,feedbacks[0].body)
    feedbacks[1].resolve({session_id:'session-1',display_receipt_id:'receipt-1'}); await retry; await vue.nextTick(); await vue.nextTick()
    assert.equal(store.feedbackIsStale.value,true)
    assert.deepEqual(acks,['receipt-1'])
    const next = store.fetchAiFeedback()
    assert.equal(feedbacks[2].body.run_id,undefined)
    assert.equal(feedbacks[2].body.session_id,'session-1')
    feedbacks[2].resolve({session_id:'session-1',display_receipt_id:null}); await next
  } finally {store.dispose()}
})

test('workspace drops feedback on task/account change or reset; hidden panels do not acknowledge', async () => {
  for (const change of ['task','account','reset']) {
    const {store,feedbacks,props,auth,acks} = workspace()
    try {
      store.code.value = 'print(1)'; const pending = store.fetchAiFeedback()
      if (change === 'task') props.trialQuestionId = 2
      if (change === 'account') auth.profile.id = 2
      if (change === 'reset') store.onReset()
      await vue.nextTick()
      feedbacks[0].resolve({session_id:'old',display_receipt_id:'old'}); await pending; await vue.nextTick()
      assert.equal(store.agentResult.value,null); assert.equal(store.agentLoading.value,false)
      assert.deepEqual(acks,[])
    } finally {store.dispose()}
  }
  const {store,feedbacks,acks,document} = workspace()
  try {
    store.code.value = 'print(1)'; document.visibilityState = 'hidden'
    const pending = store.fetchAiFeedback()
    store.leftPanel.value = 'history'
    feedbacks[0].resolve({session_id:'s',display_receipt_id:'r'}); await pending; await vue.nextTick()
    document.visibilityState = 'visible'; store.acknowledgeVisibleFeedback()
    assert.deepEqual(acks,[])
    store.leftPanel.value = 'problem'; await vue.nextTick(); await vue.nextTick()
    assert.deepEqual(acks,['r'])
  } finally {store.dispose()}
})


function freeMessenger(cryptoOverride) {
  const streams = [], acks = [], persisted = [], artifacts = [], reads = [], downloads = [], cancels = [], uses = [], turnReads = [], modeRequests = []
  const sessions = vue.ref([{id:'a',messages:[]},{id:'b',messages:[]}]), active = vue.ref('a')
  const auth = vue.reactive({profile:{id:1}})
  const store = component('../src/views/MessengerView.vue',
    'conversationMode, linkedContext, updateLinked, setConversationMode, tutorCode, tutorRun, chatMessages, chatLoading, sendChat, sendChatText, tutorSessionIds, prompt, runToolAction, restoreArtifactMessages, downloadMessageMarkdown, onVisible, cancelCurrentRequest, loadTutorUsage, tutorUsage, deactivateChat, activateChat, tutorMode, sendTutorQuestion, acknowledgeVisibleTutors', {}, {
      'vue-router':{useRoute:() => ({query:{},params:{}}),useRouter:() => ({})},'naive-ui':{useMessage:() => ({warning(){},error(){},success(){},info(){}})},
      '@vicons/ionicons5':{},
      '../api/messenger':{
        postMessengerLearningDocument:(topic,id,signal) => {const pending=deferred();artifacts.push({topic,id,signal,...pending});return pending.promise},
        postMessengerKnowledgeGraph:(topic,id,signal) => {const pending=deferred();artifacts.push({topic,id,signal,...pending});return pending.promise},
        fetchMessengerArtifact:id => {const pending=deferred();reads.push({id,...pending});return pending.promise},
        streamMessengerChat:(body,history,handlers) => {
        const pending=deferred(); streams.push({body,history,handlers,...pending}); return pending.promise
      }},
      '../api/agentService':{}, '../stores/theme':{useThemeStore:() => ({isComic:false})},
      '../api/tutoring':{tutorModes:[],fetchTutorTurn:id => {const pending=deferred();turnReads.push({id,...pending});return pending.promise},
        askTutor:body => {const pending=deferred();modeRequests.push({body,...pending});return pending.promise},
        cancelTutorTurn:id => {const pending=deferred();cancels.push({id,...pending});return pending.promise},
        fetchTutorUsage:() => {const pending=deferred();uses.push(pending);return pending.promise}},
      '../api/codeRunner':{}, '../api/http':{formatHttpError:e => e.message}, '../stores/auth':{useAuthStore:() => auth},
      '../api/learnerState':{acknowledgeTutorDisplay:async id => acks.push(id)},
      '../utils/xiaoEPersona':{}, '../utils/practiceQuestionNav':{},
      '../composables/useSpeechRecognitionInput':{useSpeechRecognitionInput:() => ({listening:vue.ref(false),toggle(){}})},
      '../composables/useMessengerChatSessions':{useMessengerChatSessions:() => ({sessions,activeSessionId:active,
        activeSession:vue.computed(() => sessions.value.find(s=>s.id===active.value)),
        setSessionMessages:(id,rows) => persisted.push({id,rows:JSON.parse(JSON.stringify(rows))})})},
    }, {AbortController,Blob,URL:{createObjectURL:blob => {downloads.push(blob);return 'blob:test'},revokeObjectURL(){}},
      window:{requestAnimationFrame:() => 1},document:{visibilityState:'visible',createElement:() => ({click(){}})},
      crypto:cryptoOverride || {randomUUID:()=> `request-${streams.length+artifacts.length}`}})
  return {store,streams,acks,persisted,active,auth,artifacts,reads,downloads,cancels,uses,turnReads,modeRequests}
}

test('HTTP messenger send button reaches the stream and renders the answer', async () => {
  const {store,streams} = freeMessenger(httpCrypto)
  try {
    store.prompt.value = '小E，请解释循环'
    const pending = store.sendChat()
    assert.equal(streams.length, 1)
    assert.equal(streams[0].body.message, '小E，请解释循环')
    assert.match(streams[0].body.request_id, /^[0-9a-f-]{36}$/)
    assert.equal(store.prompt.value, '')
    streams[0].resolve({reply:'循环用于重复执行一段代码。'})
    await pending
    assert.equal(store.chatMessages.value.at(-1).text, '循环用于重复执行一段代码。')
    assert.equal(store.chatLoading.value, false)
  } finally {store.dispose()}
})

test('free chat retries the same turn, caches only references and resumes the shared server session', async () => {
  const {store,streams,acks,persisted} = freeMessenger()
  try {
    store.tutorCode.value='old-code'; store.tutorRun.value={code:'old-code',result:{run_id:'owned-run'}}
    const pending=store.sendChatText('解释这个概念')
    streams[0].handlers.onDelta('PRIVATE-MATERIAL-TEXT'); await vue.nextTick()
    assert.ok(!JSON.stringify(persisted).includes('PRIVATE-MATERIAL-TEXT'))
    store.tutorCode.value='new-code'; streams[0].reject(new Error('connection interrupted')); await pending
    assert.ok(!store.chatMessages.value.at(-1).text.includes('PRIVATE-MATERIAL-TEXT'))
    store.chatMessages.value.at(-1).retry(); await new Promise(r=>setImmediate(r))
    assert.deepEqual(streams[1].body,streams[0].body)
    assert.equal(streams[1].body.run_id,'owned-run'); assert.equal(streams[1].history.length,0)
    const tutor={request_id:'request-0',session_id:'owned-session',summary:'已核对',display_receipt_id:'receipt'}
    streams[1].resolve({reply:'已核对',tutor}); await new Promise(r=>setImmediate(r))
    assert.deepEqual(acks,['receipt'])
    assert.equal(store.chatMessages.value.at(-1).tutorCode,'old-code')
    assert.equal(store.tutorSessionIds.get('a'),'owned-session')
    const next=store.sendChatText('再解释一下')
    assert.equal(streams[2].body.session_id,'owned-session'); assert.equal(streams[2].body.run_id,undefined)
    streams[2].resolve({reply:'新回复',tutor:{...tutor,request_id:'request-2',display_receipt_id:null}}); await next
  } finally {store.dispose()}
})

test('free chat aborts on conversation/account changes and late SSE cannot enter the new chat', async () => {
  for (const change of ['conversation','account']) {
    const {store,streams,acks,active,auth}=freeMessenger()
    try {
      const pending=store.sendChatText('Python 列表是什么？')
      if (change==='conversation') active.value='b'; else auth.profile.id=2
      await vue.nextTick()
      assert.equal(streams[0].handlers.signal.aborted,true)
      const response={reply:'OLD-ACCOUNT',tutor:{request_id:'old',session_id:'old',display_receipt_id:'old'}}
      streams[0].handlers.onDelta('OLD-ACCOUNT'); streams[0].handlers.onDone(response)
      streams[0].resolve(response); await pending
      assert.equal(store.chatMessages.value.length,0); assert.deepEqual(acks,[])
      assert.equal(store.tutorSessionIds.size,0)
    } finally {store.dispose()}
  }
})


const artifactResult = {artifact_id:'request-0',session_id:'server-session',status:'ok',kind:'document',
  title:'学习笔记',markdown:'PRIVATE-COURSE-MATERIAL',knowledge:{sources:[{chunk_id:'own'}]}}

test('artifact retry keeps its original topic and request and does not acknowledge a hint', async () => {
  const {store,artifacts,acks}=freeMessenger()
  try {
    store.prompt.value='Python 循环';const pending=store.runToolAction('learning-document')
    artifacts[0].reject(new Error('network interrupted'));await pending
    store.prompt.value='Python 函数';store.chatMessages.value.at(-1).retry()
    assert.equal(artifacts[1].id,artifacts[0].id);assert.equal(artifacts[1].topic,'Python 循环')
    artifacts[1].resolve(artifactResult);await new Promise(r=>setImmediate(r))
    assert.equal(store.chatMessages.value.at(-1).artifactReady,true)
    assert.equal(store.chatMessages.value.at(-1).text,artifactResult.markdown)
    assert.deepEqual(acks,[])
  } finally {store.dispose()}
})

test('artifact generation aborts on conversation/account changes and ignores late results', async () => {
  for (const change of ['conversation','account']) {
    const {store,artifacts,active,auth}=freeMessenger()
    try {
      store.prompt.value='Python 循环';const pending=store.runToolAction('knowledge-graph')
      if(change==='conversation')active.value='b';else auth.profile.id=2
      await vue.nextTick();assert.equal(artifacts[0].signal.aborted,true)
      artifacts[0].resolve({...artifactResult,kind:'graph'});await pending
      assert.equal(store.chatMessages.value.length,0)
    } finally {store.dispose()}
  }
})

test('artifact download rechecks sources, never downloads a denied or previous account result', async () => {
  for (const change of ['revoked','account','authorized']) {
    const {store,reads,downloads,auth}=freeMessenger()
    try {
      store.chatMessages.value=[{role:'assistant',artifactRequestId:'request-0',artifact:'document',artifactReady:true,text:'OLD-COPY'}]
      const pending=store.downloadMessageMarkdown(store.chatMessages.value[0])
      assert.equal(downloads.length,0);assert.equal(reads[0].id,'request-0')
      if(change==='revoked')reads[0].reject(new Error('source revoked'))
      else {if(change==='account'){auth.profile.id=2;await vue.nextTick()}reads[0].resolve(artifactResult)}
      await pending
      assert.equal(downloads.length,change==='authorized'?1:0)
      if(change==='authorized')assert.equal(await downloads[0].text(),artifactResult.markdown)
      if(change==='revoked')assert.equal(store.chatMessages.value[0].artifactReady,false)
    } finally {store.dispose()}
  }
})

test('fresh artifact restore clears stale text and an older success cannot undo a newer denial', async () => {
  const {store,reads}=freeMessenger()
  try {
    store.chatMessages.value=[{role:'assistant',artifactRequestId:'request-0',artifactReady:true,text:'OLD-COPY',knowledge:{sources:['old']}}]
    store.onVisible();assert.equal(reads.length,1)
    assert.equal(store.chatMessages.value[0].text,'正在核对学习材料…');assert.equal(store.chatMessages.value[0].knowledge,undefined)
    store.onVisible();assert.equal(reads.length,2)
    reads[1].reject(new Error('source revoked'));await new Promise(r=>setImmediate(r))
    reads[0].resolve(artifactResult);await new Promise(r=>setImmediate(r))
    assert.equal(store.chatMessages.value[0].text,'source revoked');assert.equal(store.chatMessages.value[0].artifactReady,false)
  } finally {store.dispose()}
})

test('session storage strips artifact body and sources on save and rehydration across accounts', async () => {
  const source=readFileSync(new URL('../src/composables/useMessengerChatSessions.ts',import.meta.url),'utf8')
  const code=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText
  const exports={},auth=vue.reactive({profile:{id:1}}),cache=new Map(),scope=vue.effectScope()
  const message={role:'assistant',text:'PRIVATE-COPY',artifact:'document',artifactRequestId:'owned-id',knowledge:{sources:['PRIVATE-SOURCE']}}
  cache.set('a3_messenger_sessions_1',JSON.stringify([{id:'a',messages:[message]}]))
  let store
  scope.run(()=>{
    vm.runInNewContext(code,{exports,localStorage:{getItem:k=>cache.get(k),setItem:(k,v)=>cache.set(k,v)},
      require:name=>name==='vue'?vue:{useAuthStore:()=>auth}})
    store=exports.useMessengerChatSessions()
  })
  try {
    assert.equal(store.sessions.value[0].messages[0].text,'正在核对学习材料…')
    assert.ok(!cache.get('a3_messenger_sessions_1').includes('PRIVATE'))
    store.setSessionMessages('a',[message]);assert.ok(!cache.get('a3_messenger_sessions_1').includes('PRIVATE'))
    auth.profile.id=2;await vue.nextTick()
    assert.equal(store.sessions.value[0].messages.length,0)
    assert.ok(!cache.get('a3_messenger_sessions_2').includes('owned-id'))
  } finally {scope.stop()}
})


test('confirmed chat cancellation discards late deltas and does not acknowledge the cancelled reply', async () => {
  const {store,streams,acks,cancels}=freeMessenger()
  try {
    const pending=store.sendChatText('Python 循环');const stopping=store.cancelCurrentRequest()
    assert.equal(cancels[0].id,streams[0].body.request_id)
    cancels[0].resolve({cancelled:true});await stopping
    assert.equal(streams[0].handlers.signal.aborted,true);assert.equal(store.chatLoading.value,false)
    const result={reply:'LATE-PRIVATE',tutor:{request_id:cancels[0].id,session_id:'s',display_receipt_id:'receipt'}}
    streams[0].handlers.onDelta('LATE-PRIVATE');streams[0].handlers.onDone(result);streams[0].resolve(result);await pending
    assert.equal(store.chatMessages.value.at(-1).text,'本次请求已取消。');assert.equal(store.chatMessages.value.at(-1).tutorRequestId,undefined)
    assert.deepEqual(acks,[])
  } finally {store.dispose()}
})

test('failed cancellation never claims success and completed requests can still display their answer', async () => {
  for(const outcome of ['failed','complete']) {
    const {store,streams,cancels}=freeMessenger()
    try {
      const pending=store.sendChatText('Python 循环');const stopping=store.cancelCurrentRequest()
      if(outcome==='failed')cancels[0].reject(new Error('offline'));else cancels[0].resolve({cancelled:false,status:'complete'})
      await stopping;assert.equal(store.chatLoading.value,true);assert.equal(streams[0].handlers.signal.aborted,false)
      streams[0].resolve({reply:'已完成',tutor:{request_id:'r',session_id:'s'}});await pending
      assert.equal(store.chatMessages.value.at(-1).text,'已完成')
    } finally {store.dispose()}
  }
})

test('document cancellation discards a late success and clears the recoverable reference', async () => {
  const {store,artifacts,cancels}=freeMessenger()
  try {
    store.prompt.value='Python 循环';const pending=store.runToolAction('learning-document')
    const stopping=store.cancelCurrentRequest();cancels[0].resolve({cancelled:true});await stopping
    artifacts[0].resolve(artifactResult);await pending
    assert.equal(store.chatMessages.value.at(-1).artifactRequestId,undefined)
    assert.equal(store.chatMessages.value.at(-1).text,'本次请求已取消。')
  } finally {store.dispose()}
})

test('account change ignores late cancellation and quota responses', async () => {
  const {store,streams,cancels,uses,auth}=freeMessenger()
  try {
    const pending=store.sendChatText('Python 循环'),stopping=store.cancelCurrentRequest(),usage=store.loadTutorUsage()
    auth.profile.id=2;await vue.nextTick()
    cancels[0].resolve({cancelled:true});uses[0].resolve({requests_used:72});await stopping;await usage
    streams[0].resolve({reply:'old'});await pending
    assert.equal(store.tutorUsage.value,null);assert.equal(store.chatMessages.value.length,0)
  } finally {store.dispose()}
})

test('workspace cancellation ignores a late reviewed answer and preserves grades', async () => {
  const {store,feedbacks,cancels,acks,grades}=workspace()
  try {
    store.code.value='print(1)';const pending=store.fetchAiFeedback()
    const stopping=store.cancelAiFeedback();assert.equal(cancels[0].id,feedbacks[0].body.request_id)
    cancels[0].resolve({cancelled:true});await stopping
    feedbacks[0].resolve({session_id:'s',summary:'late',display_receipt_id:'receipt'});await pending;await vue.nextTick()
    assert.equal(store.agentResult.value,null);assert.equal(store.agentLoading.value,false)
    assert.deepEqual(acks,[]);assert.deepEqual(grades,[])
  } finally {store.dispose()}
})


test('manual formal failure refreshes the paper without emitting a pass or success notice', async () => {
  const {store,events,notices,grades} = workspace()
  try {
    store.code.value = 'print(3)'
    await store.onManualSubmit()
    assert.equal(grades[0][1],'print(3)')
    assert.deepEqual(events,[['submitted']])
    assert.ok(notices.some(n => n.level === 'warning' && n.text.includes('0/1')))
    assert.equal(notices.some(n => n.level === 'success'),false)
  } finally {store.dispose()}
})

test('manual formal success reports the server verdict and refreshes the paper', async () => {
  const {store,events,notices} = workspace({code_passed:true,passed_count:1,total:1})
  try {
    store.code.value = 'print(6)'
    await store.onManualSubmit()
    assert.deepEqual(events,[['submitted']])
    assert.ok(notices.some(n => n.level === 'success' && n.text.includes('通过')))
    assert.equal(notices.some(n => n.level === 'warning'),false)
  } finally {store.dispose()}
})


for (const change of ['question','account','code']) {
  test(`manual submission ignores a late verdict after changing ${change}`, async () => {
    const grade = deferred()
    const {store,props,auth,events,notices,grades} = workspace(() => grade.promise)
    try {
      store.code.value = 'print(3)'
      const pending = store.onManualSubmit()
      if (change === 'question') props.trialQuestionId = 2
      if (change === 'account') auth.profile.id = 2
      if (change === 'code') store.code.value = 'print(6)'
      grade.resolve({code_passed:false,passed_count:0,total:1})
      await pending
      assert.equal(grades[0][0],1)
      assert.equal(grades[0][1],'print(3)')
      assert.equal(events.length,0)
      assert.equal(notices.length,0)
    } finally {store.dispose()}
  })
}

test('manual submit and run cannot start competing formal submissions', async () => {
  const grade = deferred()
  const {store,runs,grades} = workspace(() => grade.promise)
  try {
    store.code.value = 'print(3)'
    const pending = store.onManualSubmit()
    await store.onManualSubmit()
    await store.onRun()
    assert.equal(grades.length,1)
    assert.equal(runs.length,0)
    grade.resolve({code_passed:false,passed_count:0,total:1})
    await pending
  } finally {store.dispose()}
})


test('completed-code review uses the persisted submission and cannot reopen a pending question', () => {
  const mutations = []
  const store = component('../src/components/trial/TrialExamPanel.vue',
    'payload, activeReviewId, activeReviewItem, reviewContext', {trialId:1}, {
      'naive-ui':{useMessage:()=>({})},
      '../../api/studentTrials':{completeStudentTrial:()=>mutations.push('complete')},
      '../../api/studentPractice':{submitPractice:async()=>({result:{all_passed:false}})},
      '../../api/studentAssignments':{submitAssignmentAnswer:()=>mutations.push('grade')},
      '../../utils/incentiveFeedback':{}, '../../api/studentOverview':{},
    })
  try {
    store.payload.value = {items:[
      {id:1,question_type:'coding',status:'completed',stem:'Sum values',knowledge_label:'for',submitted_code:'print(3)',code_passed:false},
      {id:2,question_type:'coding',status:'pending',stem:'Next task'},
      {id:3,question_type:'mcq',status:'completed',stem:'Choice'},
    ]}
    store.activeReviewId.value = 1
    assert.equal(store.reviewContext.value.formalQuestionId,1)
    assert.equal(store.reviewContext.value.exerciseId,'lc-1')
    assert.equal(store.reviewContext.value.code,'print(3)')
    assert.equal(store.reviewContext.value.runId,undefined)
    assert.equal(store.reviewContext.value.caseResults.length,0)
    assert.equal(store.activeReviewItem.value.code_passed,false)
    for (const id of [2,3,999,null]) {
      store.activeReviewId.value = id
      assert.equal(store.activeReviewItem.value,null)
      assert.equal(store.reviewContext.value,null)
    }
    assert.deepEqual(mutations,[])
  } finally {store.dispose()}
})


test('cached inactive coach hides its dialog and does not acknowledge unseen feedback', () => {
  const acks=[]
  const store=component('../src/components/trial/TrialAiFloatingBall.vue',
    'pageActive, dialogOpen, messages, suspendCoach, acknowledgeVisibleTutors',
    {context:{exerciseId:'lc-2',code:'old',caseResults:[],questionTitle:'Review'}}, {
      'naive-ui':{useMessage:()=>({})},
      '../../api/learnerState':{acknowledgeTutorDisplay:async id=>acks.push(id)},
      '../../api/tutoring':{tutorModes:[]},
      '../../composables/useSpeechRecognitionInput':{useSpeechRecognitionInput:()=>({listening:vue.ref(false),toggle(){}})},
      '../../stores/auth':{useAuthStore:()=>({profile:{id:1}})},
      '../../utils/xiaoEPersona':{}, '../../api/tutorContext':{},
    }, {window:{innerWidth:1440,innerHeight:900,removeEventListener(){}},document:{visibilityState:'visible'}})
  try {
    store.messages.value=[{id:'answer',tutor:{display_receipt_id:'receipt'}}]
    store.dialogOpen.value=true
    store.suspendCoach()
    assert.equal(store.pageActive.value,false)
    assert.equal(store.dialogOpen.value,false)
    store.acknowledgeVisibleTutors()
    assert.deepEqual(acks,[])
    store.pageActive.value=true
    store.acknowledgeVisibleTutors()
    assert.deepEqual(acks,[])
    store.dialogOpen.value=true
    store.acknowledgeVisibleTutors()
    assert.deepEqual(acks,['receipt'])
  } finally {store.dispose()}
})


test('challenge recommendations pin the displayed version across route and data changes', async () => {
  const route = vue.reactive({params:{challengeId:'task-a'},query:{version:'old-version'}})
  const challenge = vue.ref({id:'task-a',version:'new-version'})
  const state = component('../src/views/StudentCounterexampleView.vue', 'versionMismatch', {}, {
    'vue-router': {useRoute:() => route,useRouter:() => ({})},
    'naive-ui': {},
    '../stores/auth': {useAuthStore:() => ({profile:{id:1,role:'student'}})},
    '../composables/useCounterexampleAttempt': {useCounterexampleAttempt:() => ({challenge})},
    '../api/counterexamples': {},
  })
  try {
    assert.equal(state.versionMismatch.value,true)
    challenge.value={id:'task-a',version:'old-version'}
    assert.equal(state.versionMismatch.value,false)
    challenge.value={id:'task-a',version:'new-version'}
    assert.equal(state.versionMismatch.value,true)
    route.query={}
    assert.equal(state.versionMismatch.value,false)
    route.query={version:'old-version'};challenge.value=null
    assert.equal(state.versionMismatch.value,false) // load/access error owns the empty state
  } finally {state.dispose()}
})


test('leaving a cached chat aborts local observation and never acknowledges a late answer; return rechecks permissions', async () => {
  const {store,streams,acks,turnReads}=freeMessenger()
  try {
    const pending=store.sendChatText('只提示下一步')
    store.deactivateChat()
    assert.equal(streams[0].handlers.signal.aborted,true)
    streams[0].resolve({reply:'HIDDEN',tutor:{request_id:'request-0',summary:'HIDDEN',session_id:'s',display_receipt_id:'hidden-receipt'}})
    await pending; store.onVisible()
    assert.deepEqual(acks,[])
    assert.ok(!JSON.stringify(store.chatMessages.value).includes('HIDDEN'))
    store.activateChat(); assert.equal(turnReads.length,1)
    assert.equal(turnReads[0].id,'request-0')
    turnReads[0].resolve({request_id:'request-0',summary:'Fresh authorized answer',session_id:'s',display_receipt_id:'visible-receipt'})
    await new Promise(resolve=>setImmediate(resolve))
    assert.deepEqual(acks,['visible-receipt'])
    store.deactivateChat(); store.activateChat()
    assert.equal(store.chatMessages.value.at(-1).tutor,undefined)
    turnReads[1].reject(new Error('source revoked'))
    await new Promise(resolve=>setImmediate(resolve))
    assert.equal(store.chatMessages.value.at(-1).text,'source revoked')
    assert.equal(store.chatMessages.value.at(-1).tutor,undefined)
    assert.equal(typeof store.chatMessages.value.at(-1).retry,'function')
  } finally {store.dispose()}
})

test('mode requests persist a recoverable reference before completion and survive page deactivation without a false display', async () => {
  const {store,modeRequests,turnReads,acks,persisted}=freeMessenger()
  try {
    store.tutorMode.value='next_step'
    const pending=store.sendTutorQuestion('下一步')
    await vue.nextTick()
    assert.ok(persisted.some(x=>x.rows.some(row=>row.tutorRequestId==='request-0')))
    store.deactivateChat()
    modeRequests[0].resolve({request_id:'request-0',session_id:'s',summary:'HIDDEN-MODE',display_receipt_id:'r'})
    await pending; assert.deepEqual(acks,[])
    store.activateChat(); assert.equal(turnReads[0].id,'request-0')
    turnReads[0].resolve({request_id:'request-0',session_id:'s',summary:'Restored mode',display_receipt_id:'r'})
    await new Promise(resolve=>setImmediate(resolve))
    assert.equal(store.chatMessages.value.at(-1).tutor.summary,'Restored mode')
    assert.deepEqual(acks,['r'])
  } finally {store.dispose()}
})

test('hidden cached messenger drops late usage and cannot start another background request', async () => {
  const {store,uses,streams,artifacts}=freeMessenger()
  try {
    const pending=store.loadTutorUsage();store.deactivateChat()
    uses[0].resolve({requests_used:99});await pending
    assert.equal(store.tutorUsage.value,null)
    await store.sendChatText('hidden');store.prompt.value='hidden';await store.runToolAction('learning-document')
    assert.equal(streams.length,0);assert.equal(artifacts.length,0)
    store.onVisible();assert.equal(uses.length,1)
  } finally {store.dispose()}
})


test('linked chat requires verified context and free mode clears question and server session', async () => {
  const {store,streams} = freeMessenger()
  try {
    store.setConversationMode('linked')
    await store.sendChatText('解释本题')
    assert.equal(streams.length,0)
    store.updateLinked({question_ref:'bank-1',question_version:'v1',submission_id:'owned-attempt',code:'print(1)'})
    const pending=store.sendChatText('检查我的思路')
    assert.equal(streams[0].body.question_ref,'bank-1')
    assert.equal(streams[0].body.submission_id,'owned-attempt')
    streams[0].resolve({reply:'核对边界条件'})
    await pending
    store.setConversationMode('free')
    assert.equal(store.linkedContext.value,null)
    const free=store.sendChatText('什么是循环')
    assert.equal(streams[1].body.question_ref,undefined)
    assert.equal(streams[1].body.submission_id,undefined)
    assert.equal(streams[1].body.session_id,undefined)
    streams[1].resolve({reply:'循环重复执行代码'});await free
  } finally {store.dispose()}
})
