<script setup lang="ts">
import LinkedQuestionPicker from '../components/student/LinkedQuestionPicker.vue'
import type { TutorContextRequest } from '../api/tutorContext'
import { createRequestId } from '../utils/browserCrypto'
import { nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NDropdown, NIcon, NInput, NButton, NModal, NPopover, useMessage } from 'naive-ui'
import { postMessengerKnowledgeGraph, postMessengerLearningDocument, fetchMessengerArtifact, streamMessengerChat, type MessengerArtifactResult, type MessengerChatRequest } from '../api/messenger'
import type { AgentTraceStep, MessengerQuickActionResult } from '../api/agentService'
import {
  AddOutline,
  BarbellOutline,
  GitNetworkOutline,
  MicOutline,
  PaperPlaneOutline,
  TelescopeOutline,
  TrendingUpOutline,
} from '@vicons/ionicons5'
import DashboardShell from '../components/layout/DashboardShell.vue'
import xiaoEComic from '../assets/xiao-e-comic.svg'
import { useThemeStore } from '../stores/theme'
import MarkdownRenderer from '../components/common/MarkdownRenderer.vue'
import PlexAgentTracePanel from '../components/agent/PlexAgentTracePanel.vue'
import MessengerKnowledgeCard from '../components/student/MessengerKnowledgeCard.vue'
import type { MessengerKnowledge } from '../api/rag'
import { askTutor, cancelTutorTurn, fetchTutorUsage, type TutorUsage, fetchTutorTurn, tutorModes, type TutorMode, type TutorRequest, type TutorResponse } from '../api/tutoring'
import { runCode, type CodeRunResult } from '../api/codeRunner'
import { acknowledgeTutorDisplay } from '../api/learnerState'
import { formatHttpError } from '../api/http'
import { useAuthStore } from '../stores/auth'
import TutorResponseCard from '../components/student/TutorResponseCard.vue'
import { xiaoEThinkingMessage } from '../utils/xiaoEPersona'
import { openPracticeQuestionByRef } from '../utils/practiceQuestionNav'
import { useSpeechRecognitionInput } from '../composables/useSpeechRecognitionInput'
import {
  useMessengerChatSessions,
  type PersistedChatMessage,
} from '../composables/useMessengerChatSessions'

const router = useRouter()
const route = useRoute()
const themeStore = useThemeStore()
const message = useMessage()
const auth = useAuthStore()

type ChatMessage = {
  tutorRequestId?: string
  artifactRequestId?: string
  artifactReady?: boolean
  artifactCheckVersion?: number
  tutorRestored?: boolean
  tutor?: TutorResponse
  tutorCode?: string
  role: 'user' | 'assistant'
  text: string
  streaming?: boolean
  stageLabel?: string
  thinking?: AgentTraceStep[]
  illustration?: { url: string; caption?: string }
  /** Graph-enhanced RAG 参考知识（学生安全视图） */
  knowledge?: MessengerKnowledge | null
  questionPick?: MessengerQuickActionResult['question_pick']
  retry?: () => void
  /** 工具产物：学习文档可下载 MD */
  artifact?: 'document' | 'graph'
  downloadName?: string
}

function sanitizeDownloadName(name: string) {
  const cleaned = name.replace(/[\\/:*?"<>|]/g, '_').trim()
  return cleaned || '学习文档.md'
}

async function downloadMessageMarkdown(msg: ChatMessage) {
  const epoch = tutorEpoch, check = msg.artifactCheckVersion = (msg.artifactCheckVersion || 0) + 1
  try {
    let body = (msg.text || '').trim()
    let name = msg.downloadName || '学习文档.md'
    if (msg.artifactRequestId) {
      const fresh = await fetchMessengerArtifact(msg.artifactRequestId)
      if (epoch !== tutorEpoch || msg.artifactCheckVersion !== check) return
      applyArtifact(msg, fresh)
      if (fresh.status !== 'ok') throw new Error('学习材料尚未通过检查，请重新生成')
      body = fresh.markdown; name = `${fresh.title}.md`
    }
    if (!body) throw new Error('文档内容为空，暂无法下载')
    const blob = new Blob([body], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url; link.download = sanitizeDownloadName(name); link.click()
    URL.revokeObjectURL(url)
    message.success('已开始下载 Markdown')
  } catch (error) {
    if (epoch !== tutorEpoch || msg.artifactCheckVersion !== check) return
    msg.text = formatHttpError(error, '材料来源已变化或暂时不可用'); msg.knowledge = undefined; msg.artifactReady = false
    message.error(msg.text)
  }
}

const prompt = ref(typeof route.query.prompt==='string'?route.query.prompt:'')
const chatLoading = ref(false)
const pendingRequestId = ref<string>()
const cancelling = ref(false)
const usageLoading = ref(false)
const usageOpen = ref(false)
const usageError = ref('')
const tutorUsage = ref<TutorUsage | null>(null)
const chatMessages = ref<ChatMessage[]>([])
const chatThreadEl = ref<HTMLElement | null>(null)
const tutorMode = ref<TutorMode | null>(null)
const conversationMode = ref<'free'|'linked'>('free')
const linkedContext = ref<TutorContextRequest|null>(null)
function updateLinked(value:TutorContextRequest|null){tutorSessionIds.delete(activeSessionId.value);linkedContext.value=value;if(value?.code!==undefined)tutorCode.value=value.code;tutorRun.value=null}
function setConversationMode(value:'free'|'linked'){tutorSessionIds.delete(activeSessionId.value);conversationMode.value=value;tutorMode.value=null;linkedContext.value=null;tutorCode.value='';tutorRun.value=null}
watch(()=>route.query,()=>{if(route.query.submission||route.query.question_ref||route.query.linked)conversationMode.value='linked'},{immediate:true})

const tutorCode = ref('')
const tutorRun = ref<{ code: string; result: CodeRunResult } | null>(null)
const tutorRunning = ref(false)
const tutorRestoring = ref(false)
const tutorSessionIds = new Map<string, string>()
let tutorEpoch = 0
let pageActive = true
let chatAbort: AbortController | null = null
let scrollRaf = 0

const {
  sessions: messengerSessions,
  activeSessionId,
  activeSession,
  canCreateSession,
  switchSession,
  createSession,
  renameSession,
  setSessionMessages,
  touchSession,
} = useMessengerChatSessions()

let syncingSessionMessages = false

function formatSessionTime(ts: number) {
  const d = new Date(ts)
  return d.toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function persistActiveSessionMessages() {
  if (syncingSessionMessages || !activeSessionId.value) return
  // Store only the reference. Restore through the server's fresh access/version check.
  const persisted: PersistedChatMessage[] = chatMessages.value.map(
    ({ retry: _retry, thinking: _thinking, tutor, tutorCode: _code, tutorRestored: _restored, artifactReady: _artifactReady, artifactCheckVersion: _artifactCheck, ...rest }) => ({
      ...rest, ...((tutor || rest.tutorRequestId) ? { tutorRequestId: tutor?.request_id || rest.tutorRequestId, text: '正在核对辅导记录…' } : {}),
      streaming: false,
      stageLabel: undefined,
    }),
  )
  setSessionMessages(activeSessionId.value, persisted)
}

watch(
  [activeSessionId, () => auth.profile?.id],
  ([id, account], previous) => {
    ++tutorEpoch
    pendingRequestId.value = undefined; cancelling.value = false; tutorUsage.value = null; usageLoading.value = false; usageOpen.value = false; usageError.value = ''
    chatAbort?.abort()
    if (account !== previous?.[1]) {tutorSessionIds.clear(); linkedContext.value=null}
    if(previous && id!==previous[0]){linkedContext.value=null;conversationMode.value='free';tutorMode.value=null}
    tutorCode.value = ''
    tutorRun.value = null
    tutorRunning.value = false
    tutorRestoring.value = false
    chatLoading.value = false
    syncingSessionMessages = true
    const stored = id && account ? messengerSessions.value.find((s) => s.id === id)?.messages ?? [] : []
    chatMessages.value = stored.map((m) => ({ ...m })) as ChatMessage[]
    syncingSessionMessages = false
    scrollThreadToBottom()
    if (pageActive && id && account) {
      void restoreTutorMessages(id, tutorEpoch)
      void restoreArtifactMessages(id, tutorEpoch)
    }
  },
  { immediate: true },
)

watch(chatMessages, () => persistActiveSessionMessages(), { deep: true })

const renamingSessionId = ref('')
const renameDraft = ref('')
const messengerBoxOpen = ref(false)

const displayAcks = new Set<string>()
function acknowledgeVisibleTutors() {
  if (!pageActive || document.visibilityState !== 'visible') return
  for (const msg of chatMessages.value) {
    const id = msg.tutor?.display_receipt_id
    if (!id || displayAcks.has(id)) continue
    displayAcks.add(id)
    void acknowledgeTutorDisplay(id).catch(() => { displayAcks.delete(id); message.warning('提示已显示，学习记录尚未同步。') })
  }
}
function onVisible() {
  if (!pageActive) return
  acknowledgeVisibleTutors()
  if (document.visibilityState === 'visible') void restoreArtifactMessages(activeSessionId.value, tutorEpoch)
}
onMounted(() => document.addEventListener('visibilitychange', onVisible))
function deactivateChat() {
  pageActive = false; ++tutorEpoch
  chatAbort?.abort(); chatAbort = null
  if (scrollRaf) window.cancelAnimationFrame?.(scrollRaf)
  scrollRaf = 0
  pendingRequestId.value = undefined; cancelling.value = false
  chatLoading.value = false; tutorRunning.value = false; tutorRestoring.value = false
  tutorUsage.value = null; usageLoading.value = false; usageOpen.value = false; usageError.value = ''; messengerBoxOpen.value = false
  for (const row of chatMessages.value) {
    if (row.tutor || row.tutorRequestId || row.artifactRequestId) {
      row.tutorRequestId = row.tutor?.request_id || row.tutorRequestId
      row.text = '返回时将重新核对这条记录…'
      row.tutor = undefined; row.tutorCode = undefined; row.knowledge = undefined; row.questionPick = undefined
      row.artifactReady = false; row.streaming = false; row.stageLabel = undefined; row.retry = undefined
    }
  }
}
function activateChat() {
  if (pageActive) return
  pageActive = true
  void restoreTutorMessages(activeSessionId.value, tutorEpoch)
  void restoreArtifactMessages(activeSessionId.value, tutorEpoch)
}
onDeactivated(deactivateChat)
onActivated(activateChat)
onBeforeUnmount(() => { deactivateChat(); document.removeEventListener('visibilitychange', onVisible) })

async function restoreTutorMessages(session: string, epoch: number) {
  if (!pageActive || epoch !== tutorEpoch) return
  const rows = chatMessages.value.filter(msg => msg.tutorRequestId)
  if (!rows.length) return
  tutorRestoring.value = true
  for (const row of rows) {
    row.tutor = undefined; row.questionPick = undefined; row.retry = undefined
    row.text = '正在核对辅导记录…'
    try {
      const result = await fetchTutorTurn(row.tutorRequestId!)
      if (epoch !== tutorEpoch || session !== activeSessionId.value) return
      // Proxy identity is retained, so restoration updates the current DOM row.
      row.tutor = result; row.text = result.summary; row.tutorRestored = true; row.questionPick = result.question_pick
      tutorSessionIds.set(session, result.session_id)
    } catch (error) {
      if (epoch !== tutorEpoch) return
      row.text = error instanceof Error ? error.message : '这条辅导记录暂不可用'
      row.retry = () => { void restoreTutorMessages(session, epoch) }
    }
  }
  if (epoch === tutorEpoch) tutorRestoring.value = false
  await nextTick()
  if (epoch === tutorEpoch) acknowledgeVisibleTutors()
}

async function loadTutorUsage() {
  if (!pageActive || usageLoading.value) return
  const epoch = tutorEpoch
  usageLoading.value = true
  usageError.value = ''
  try { const result = await fetchTutorUsage(); if (epoch === tutorEpoch) tutorUsage.value = result }
  catch(error) { if(epoch===tutorEpoch) usageError.value = formatHttpError(error,'暂时无法读取用量') }
  finally { if(epoch===tutorEpoch) usageLoading.value = false }
}

function openUsage() { usageOpen.value = true; messengerBoxOpen.value = false; void loadTutorUsage() }

async function cancelCurrentRequest() {
  const id = pendingRequestId.value, epoch = tutorEpoch
  if (!id || cancelling.value) return
  cancelling.value = true
  try {
    const result = await cancelTutorTurn(id)
    if(epoch!==tutorEpoch || pendingRequestId.value!==id) return
    if(!result.cancelled) { message.info('回答已经完成，可以继续查看。'); return }
    ++tutorEpoch
    chatAbort?.abort();chatAbort=null;chatLoading.value=false;pendingRequestId.value=undefined;usageLoading.value=false
    const row = chatMessages.value.find(item=>item.tutorRequestId===id || item.artifactRequestId===id)
    if(row) {
      row.text='本次请求已取消。';row.streaming=false;row.stageLabel=undefined;row.retry=undefined
      row.tutor=undefined;row.tutorRequestId=undefined;row.artifactRequestId=undefined;row.artifact=undefined;row.artifactReady=false;row.knowledge=undefined
    } else chatMessages.value.push({role:'assistant',text:'本次请求已取消。'})
    void loadTutorUsage()
  } catch(error) { if(epoch===tutorEpoch) message.error(formatHttpError(error,'取消未确认，原请求可能仍在处理')) }
  finally { if(pendingRequestId.value===id || !pendingRequestId.value) cancelling.value=false }
}

async function runTutorCode() {
  if (!pageActive || tutorRunning.value || !tutorCode.value.trim()) return
  const epoch = tutorEpoch, code = tutorCode.value
  tutorRunning.value = true
  try {
    const result = await runCode({ ...(conversationMode.value==='linked'?linkedContext.value:{}), language: 'python', code })
    if (epoch === tutorEpoch) tutorRun.value = { code, result }
  } catch (error) {
    if (epoch === tutorEpoch) message.error(formatHttpError(error, '代码执行暂不可用'))
  } finally { if (epoch === tutorEpoch) tutorRunning.value = false }
}

async function sendTutorQuestion(text: string, retryPayload?: TutorRequest) {
  if (!pageActive || chatLoading.value || tutorRestoring.value || (!tutorMode.value && !retryPayload)) return
  if(conversationMode.value==='linked'&&!linkedContext.value){message.warning('请先关联一道可用题目');return}
  const epoch = tutorEpoch, session = activeSessionId.value
  const payload: TutorRequest = retryPayload || {
    request_id: createRequestId(), session_id: tutorSessionIds.get(session), mode: tutorMode.value!,
    ...(conversationMode.value==='linked'?linkedContext.value:{}),
    question: text, code: tutorCode.value,
    run_id: tutorRun.value?.code === tutorCode.value ? tutorRun.value.result.run_id : undefined,
  }
  if (!retryPayload) chatMessages.value.push({ role: 'user', text })
  chatLoading.value = true
  pendingRequestId.value = payload.request_id
  chatMessages.value.push({ role: 'assistant', text: '', tutorRequestId: payload.request_id, streaming: true, stageLabel: '小E 正在核对上下文' })
  const row = chatMessages.value[chatMessages.value.length - 1]!
  try {
    const result = await askTutor(payload)
    if (epoch !== tutorEpoch) return
    tutorSessionIds.set(session, result.session_id)
    row.text = result.summary; row.tutor = result; row.tutorCode = payload.code
    row.streaming = false; row.stageLabel = undefined
    await nextTick()
    if (epoch === tutorEpoch) acknowledgeVisibleTutors()
  } catch (error) {
    if (epoch === tutorEpoch) {
      row.text = error instanceof Error ? error.message : '辅导暂不可用'
      row.streaming = false; row.stageLabel = undefined
      row.retry = () => { void sendTutorQuestion(text, payload) }
    }
  } finally {
    if (epoch === tutorEpoch) { chatLoading.value = false; pendingRequestId.value = undefined; scrollThreadToBottom() }
  }
}

function startRenameSession(id: string, currentName: string) {
  renamingSessionId.value = id
  renameDraft.value = currentName
}

function commitRenameSession() {
  if (!renamingSessionId.value) return
  renameSession(renamingSessionId.value, renameDraft.value)
  renamingSessionId.value = ''
  renameDraft.value = ''
}

function cancelRenameSession() {
  renamingSessionId.value = ''
  renameDraft.value = ''
}

function onNewMessengerSession() {
  if (!canCreateSession.value) {
    message.warning('最多保留 5 个对话窗口')
    return
  }
  const session = createSession()
  if (session) {
    prompt.value = ''
    message.success(`已新建「${session.name}」`)
  }
}

function onSelectMessengerSession(id: string) {
  if (id === activeSessionId.value) {
    messengerBoxOpen.value = false
    return
  }
  switchSession(id)
  touchSession(id)
  messengerBoxOpen.value = false
}

const { listening: voiceListening, toggle: toggleVoiceInput } = useSpeechRecognitionInput({
  getText: () => prompt.value,
  setText: (value) => {
    prompt.value = value
  },
  message,
})

function scrollThreadToBottom() {
  if (scrollRaf) return
  scrollRaf = window.requestAnimationFrame(() => {
    scrollRaf = 0
    const el = chatThreadEl.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

async function openQuestionPick(pick: NonNullable<MessengerQuickActionResult['question_pick']>) {
  const ok = await openPracticeQuestionByRef(router, pick.id)
  if (!ok) {
    chatMessages.value.push({
      role: 'assistant',
      text: '这道题的入口暂时打不开，请稍后在星轨学习或顶部搜索里再试一次。',
    })
  }
}

/** 快捷按钮与自由提问统一走流式对话，避免整包等待「正在思考」。 */
async function runQuickAction(_action: string, userText: string) {
  await sendChatText(userText)
}

async function runWeakPointsAction() {
  await runQuickAction('weak_points', '小E，帮我诊断一下薄弱点。')
}

async function runNextTrialAction() {
  await runQuickAction('next_trial', '小E，下一道试炼该练什么？')
}

async function runPathPlanningAgent() {
  await runQuickAction('repair_path', '小E，帮我规划一下修复路线。')
}

async function runGrowthAction() {
  await runQuickAction('recent_growth', '小E，看看我最近成长怎么样？')
}

const actions = [
  { label: '诊断薄弱点', icon: TelescopeOutline, handler: runWeakPointsAction },
  { label: '推荐下一试炼', icon: BarbellOutline, handler: runNextTrialAction },
  { label: '规划修复路线', icon: GitNetworkOutline, handler: runPathPlanningAgent },
  { label: '查看最近成长', icon: TrendingUpOutline, handler: runGrowthAction },
] as const

async function sendChatText(text: string, appendUserMessage = true, retryPayload?: MessengerChatRequest) {
  if (!pageActive || !text || chatLoading.value || tutorRestoring.value) return
  if(conversationMode.value==='linked'&&!linkedContext.value){message.warning('请先关联一道可用题目');return}
  const epoch = tutorEpoch, session = activeSessionId.value
  const payload: MessengerChatRequest = retryPayload || {
    message: text, request_id: createRequestId(), session_id: tutorSessionIds.get(session),
    ...(conversationMode.value==='linked'?linkedContext.value:{}),
    code: tutorCode.value,
    run_id: tutorRun.value?.code === tutorCode.value ? tutorRun.value.result.run_id : undefined,
  }
  if (appendUserMessage) chatMessages.value.push({ role: 'user', text })
  chatLoading.value = true
  pendingRequestId.value = payload.request_id
  const controller = new AbortController()
  chatAbort = controller
  const retry = () => { void sendChatText(text, false, payload) }
  chatMessages.value.push({ role: 'assistant', text: '', streaming: true,
    tutorRequestId: payload.request_id, stageLabel: '小E 正在核对上下文' })
  const index = chatMessages.value.length - 1
  const live = () => epoch === tutorEpoch ? chatMessages.value[index] : undefined
  try {
    const result = await streamMessengerChat(payload, [], {
      signal: controller.signal,
      onStage: (_stage, label) => { const row = live(); if (row) row.stageLabel = label },
      onDelta: delta => { const row = live(); if (row) { row.text += delta; scrollThreadToBottom() } },
      onDone: result => {
        const row = live()
        if (!row) return
        row.text = result.reply; row.tutor = result.tutor; row.tutorCode = payload.code
        row.questionPick = result.question_pick; row.streaming = false; row.stageLabel = undefined
        if (result.tutor) tutorSessionIds.set(session, result.tutor.session_id)
      },
    })
    const row = live()
    if (!row) return
    row.text = result.reply; row.tutor = result.tutor; row.tutorCode = payload.code
    row.questionPick = result.question_pick; row.streaming = false; row.stageLabel = undefined
    if (result.tutor) tutorSessionIds.set(session, result.tutor.session_id)
    await nextTick(); if (epoch === tutorEpoch) acknowledgeVisibleTutors()
  } catch (error) {
    const row = live()
    if (!row) return
    // Discard incomplete transport output. A retry uses the same server turn;
    // never launch a second untracked synchronous generation after a timeout.
    row.text = error instanceof Error ? error.message : '这次回答未完成，请重试。'
    row.streaming = false; row.stageLabel = undefined; row.tutor = undefined; row.retry = retry
  } finally {
    if (epoch === tutorEpoch) { chatLoading.value = false; pendingRequestId.value = undefined; chatAbort = null; scrollThreadToBottom() }
  }
}

async function sendChat() {
  if (tutorRestoring.value) { message.info('正在核对之前的辅导记录，请稍等。'); return }
  const text = prompt.value.trim()
  if (!text) return
  prompt.value = ''
  if (tutorMode.value) await sendTutorQuestion(text)
  else await sendChatText(text)
}

const toolMenuOptions = [
  { label: '生成知识图', key: 'knowledge-graph' },
  { label: '生成文档', key: 'learning-document' },
]

function applyArtifact(msg: ChatMessage, result: MessengerArtifactResult) {
  msg.text = result.markdown
  msg.artifactRequestId = result.artifact_id
  msg.artifact = result.kind
  msg.artifactReady = result.status === 'ok'
  msg.downloadName = `${result.title}.md`
  msg.knowledge = result.knowledge
  msg.illustration = undefined
  msg.streaming = false; msg.stageLabel = undefined; msg.thinking = undefined
}

async function restoreArtifactMessages(session: string, epoch: number) {
  if (!pageActive || epoch !== tutorEpoch) return
  const rows = chatMessages.value.filter(msg => msg.artifactRequestId && !msg.streaming)
  for (const row of rows) {
    const check = row.artifactCheckVersion = (row.artifactCheckVersion || 0) + 1
    row.text = '正在核对学习材料…'; row.knowledge = undefined; row.artifactReady = false
    try {
      const result = await fetchMessengerArtifact(row.artifactRequestId!)
      if (epoch !== tutorEpoch || session !== activeSessionId.value || row.artifactCheckVersion !== check) return
      applyArtifact(row, result)
      row.retry = undefined
    } catch (error) {
      if (epoch !== tutorEpoch || session !== activeSessionId.value || row.artifactCheckVersion !== check) return
      row.text = formatHttpError(error, '这份学习材料尚未完成或当前不可访问')
      row.retry = () => { void restoreArtifactMessages(session, epoch) }
    }
  }
}

async function runToolAction(key: string) {
  if (!pageActive || chatLoading.value || tutorRestoring.value) return
  const topic = prompt.value.trim()
  if (!topic) { message.warning('请先在输入框描述主题，再选择工具'); return }
  if (!['knowledge-graph', 'learning-document'].includes(key)) return
  const epoch = tutorEpoch, session = activeSessionId.value, requestId = createRequestId()
  const isGraph = key === 'knowledge-graph'
  prompt.value = ''
  chatMessages.value.push({role:'user', text: isGraph ? `请帮我生成知识图：${topic}` : `请帮我生成学习文档：${topic}`})
  chatMessages.value.push({role:'assistant', text:'', artifactRequestId:requestId, artifact:isGraph?'graph':'document'})
  const row = chatMessages.value[chatMessages.value.length - 1]!
  const perform = async () => {
    if (epoch !== tutorEpoch || session !== activeSessionId.value || chatLoading.value) return
    row.artifactCheckVersion = (row.artifactCheckVersion || 0) + 1
    pendingRequestId.value = requestId
    chatLoading.value = true; row.streaming = true; row.retry = undefined
    row.stageLabel = '检索课程材料并核对内容'
    const controller = new AbortController(); chatAbort = controller
    try {
      const result = isGraph ? await postMessengerKnowledgeGraph(topic, requestId, controller.signal)
        : await postMessengerLearningDocument(topic, requestId, controller.signal)
      if (epoch !== tutorEpoch || session !== activeSessionId.value) return
      applyArtifact(row, result)
    } catch (error) {
      if (epoch !== tutorEpoch || session !== activeSessionId.value) return
      row.text = formatHttpError(error, '工具调用未完成，可使用原请求重试')
      row.retry = () => { void perform() }
    } finally {
      if (epoch === tutorEpoch && session === activeSessionId.value) {
        row.streaming = false; row.stageLabel = undefined; chatLoading.value = false; pendingRequestId.value = undefined
        if (chatAbort === controller) chatAbort = null
        scrollThreadToBottom()
      }
    }
  }
  await perform()
}

</script>

<template>
  <DashboardShell
    active-nav="messenger"
    page-title="驿站助手"
    page-subtitle="结合错题、画像与推荐结果提供学习建议"
    search-placeholder=""
    hide-search
  >
    <n-modal v-model:show="usageOpen" preset="card" title="我的辅导用量" class="plex-reading-modal tutor-usage-modal" :style="{ width: 'min(460px, 94vw)' }">
      <p v-if="usageLoading" role="status">正在读取用量…</p>
      <p v-else-if="usageError" role="alert">{{ usageError }}</p>
      <dl v-if="tutorUsage && !usageLoading && !usageError" class="tutor-usage-details">
        <div><dt>本周期辅导</dt><dd>{{ tutorUsage.requests_used }} / {{ tutorUsage.request_limit }} 次</dd></div>
        <div><dt>剩余额度</dt><dd>{{ tutorUsage.requests_remaining }} 次</dd></div>
        <div><dt>模型调用</dt><dd>{{ tutorUsage.model_calls }} 次</dd></div>
        <div><dt>已报告 Token</dt><dd>{{ tutorUsage.reported_total_tokens }}</dd></div>
        <div v-if="tutorUsage.unknown_usage_calls"><dt>用量未知的调用</dt><dd>{{ tutorUsage.unknown_usage_calls }} 次</dd></div>
        <div><dt>额度恢复时间</dt><dd>{{ new Date(tutorUsage.reset_at).toLocaleString('zh-CN') }}</dd></div>
      </dl>
      <template #footer><n-button :loading="usageLoading" @click="loadTutorUsage">{{ usageError ? '重试' : '刷新用量' }}</n-button></template>
    </n-modal>
    <main class="messenger-main" :class="{ 'plex-comic-chat': themeStore.isComic }">
      <section class="messenger-stage" aria-label="驿站使者">
        <div class="station-bg" aria-hidden="true">
          <span class="station-bg__planet" />
          <span class="station-bg__ring station-bg__ring--top" />
          <span class="station-bg__ring station-bg__ring--floor" />
          <span class="station-bg__light station-bg__light--one" />
          <span class="station-bg__light station-bg__light--two" />
          <span class="station-bg__crystal station-bg__crystal--one" />
          <span class="station-bg__crystal station-bg__crystal--two" />
        </div>

        <aside class="analysis-panel" aria-label="与小E对话反馈">
          <header class="analysis-panel__head" data-tour="student-messenger">
          <div class="conversation-modes" role="group" aria-label="提问模式">
            <button :aria-pressed="conversationMode==='free'" :disabled="chatLoading" @click="setConversationMode('free')">随心问</button>
            <button :aria-pressed="conversationMode==='linked'" :disabled="chatLoading" @click="setConversationMode('linked')">关联题目</button>
          </div>
            <div class="messenger-header-tools">
              <n-button class="messenger-usage-toggle plex-action-button" @click="openUsage">查看用量</n-button>
              <div class="messenger-box">
              <n-popover :show="messengerBoxOpen" trigger="manual" placement="bottom-end" raw @clickoutside="messengerBoxOpen = false">
              <template #trigger><button
                type="button"
                class="messenger-box__toggle"
                :aria-expanded="messengerBoxOpen"
                aria-controls="messenger-box-panel"
                @click="messengerBoxOpen = !messengerBoxOpen"
                @keydown.esc="messengerBoxOpen = false"
              >
                <span class="messenger-box__label">BOX</span>
                <span class="messenger-box__current">{{ activeSession?.name || '对话' }}</span>
                <span class="messenger-box__chevron" aria-hidden="true">{{ messengerBoxOpen ? '▴' : '▾' }}</span>
              </button></template>
              <div
                id="messenger-box-panel"
                class="messenger-box__panel"
                @keydown.esc="messengerBoxOpen = false"
                role="tablist"
                aria-label="对话窗口"
              >
                <div class="messenger-box__panel-head">
                  <span>切换对话窗口 · 最多 5 个</span>
                  <button
                    type="button"
                    class="messenger-session-add"
                    :disabled="!canCreateSession"
                    aria-label="新建对话窗口"
                    @click="onNewMessengerSession"
                  >
                    +
                  </button>
                </div>
                <div
                  v-for="session in messengerSessions"
                  :key="session.id"
                  class="messenger-session-tab"
                  :class="{ 'is-active': session.id === activeSessionId }"
                  role="tab"
                  :aria-selected="session.id === activeSessionId"
                >
                  <template v-if="renamingSessionId === session.id">
                    <input
                      v-model="renameDraft"
                      class="messenger-session-rename"
                      maxlength="40"
                      @keydown.enter.prevent="commitRenameSession"
                      @keydown.esc.prevent="cancelRenameSession"
                      @blur="commitRenameSession"
                    />
                  </template>
                  <button
                    v-else
                    type="button"
                    class="messenger-session-tab__btn"
                    @click="onSelectMessengerSession(session.id)"
                    @dblclick.stop="startRenameSession(session.id, session.name)"
                  >
                    {{ session.name }}
                  </button>
                  <small>最近使用 {{ formatSessionTime(session.lastActiveAt) }}</small>
                </div>
              </div>
            </n-popover>
              </div>
            </div>
          </header>
          <div ref="chatThreadEl" class="chat-thread" aria-label="与小E对话">
            <div v-if="!chatMessages.length" class="chat-thread__empty">
              <template v-if="themeStore.isComic">
                <img class="comic-chat-mascot" :src="xiaoEComic" alt="小E" />
                <div class="comic-welcome-bubble">
                  <strong>向小E提一个 Python 或学习问题</strong>
                  <p>探索之路固然艰难，有什么疑惑我帮你解决！</p>
                </div>
              </template>
              <template v-else>
                <strong>向小E提一个 Python 或学习问题</strong>
                <p>探索之路固然艰难，有什么疑惑我帮你解决！</p>
              </template>
            </div>
            <article v-for="(msg, idx) in chatMessages" :key="idx" :class="`chat-thread__item chat-thread__item--${msg.role}`">
              <template v-if="msg.role === 'assistant'">
                <img v-if="themeStore.isComic" class="comic-message-avatar" :src="xiaoEComic" alt="小E" />
                <PlexAgentTracePanel
                  v-if="msg.thinking?.length || msg.streaming"
                  mode="freeform"
                  :trace="msg.thinking"
                  :loading="Boolean(msg.streaming)"
                />
                <p v-if="msg.streaming && !msg.text" class="chat-thread__stage">
                  {{ msg.stageLabel || '小E 正在组织回答' }}…
                </p>
                <template v-if="msg.tutor">
                  <small v-if="(msg.tutorRestored && msg.tutor.context?.code_lines) || (msg.tutorCode && msg.tutorCode !== tutorCode)" class="tutor-code-stale">这条反馈对应之前附带的代码。</small>
                  <TutorResponseCard :response="msg.tutor" />
                </template>
                <MarkdownRenderer v-else-if="msg.text" :content="msg.text" :streaming="msg.streaming" />
                <span v-if="msg.streaming" class="chat-thread__cursor" aria-hidden="true" />
                <MessengerKnowledgeCard v-if="msg.knowledge && !msg.streaming" :knowledge="msg.knowledge" />
                <figure v-if="msg.illustration?.url" class="chat-thread__illustration">
                  <img :src="msg.illustration.url" :alt="msg.illustration.caption || '图解说明'" loading="lazy" />
                  <figcaption>{{ msg.illustration.caption || '图解说明' }}</figcaption>
                </figure>
                <div
                  v-if="msg.artifact === 'document' && !msg.streaming && msg.text && (!msg.artifactRequestId || msg.artifactReady)"
                  class="chat-thread__actions"
                >
                  <button
                    type="button"
                    class="chat-thread__download-md"
                    @click="downloadMessageMarkdown(msg)"
                  >
                    下载 MD
                  </button>
                </div>
              </template>
              <p v-else>{{ msg.text }}</p>
              <button
                v-if="msg.questionPick"
                type="button"
                class="chat-thread__pick"
                @click="openQuestionPick(msg.questionPick)"
              >
                去练 {{ msg.questionPick.code }} · {{ msg.questionPick.title }}
              </button>
              <button
                v-if="msg.retry"
                type="button"
                class="chat-thread__retry"
                :disabled="chatLoading"
                @click="msg.retry?.()"
              >
                重试
              </button>
            </article>
            <p
              v-if="chatLoading && !chatMessages[chatMessages.length - 1]?.streaming"
              class="chat-thread__loading"
            >
              {{ xiaoEThinkingMessage('chat') }}
            </p>
          </div>
        </aside>

        <section class="prompt-dock prompt-dock--tech" aria-label="向小E提问">
          <LinkedQuestionPicker v-if="conversationMode==='linked'" @change="updateLinked" />
          <details v-if="conversationMode==='linked'"><summary>选择帮助方式</summary><div class="tutor-mode-picker">
            <button :aria-pressed="tutorMode===null" @click="tutorMode=null">按问题回答</button>
            <button v-for="item in tutorModes" :key="item.mode" :aria-pressed="tutorMode===item.mode" :disabled="chatLoading" @click="tutorMode=item.mode">{{item.label}}</button>
          </div></details>
          <div class="tutor-mode-picker">
            <button v-if="chatLoading && pendingRequestId" type="button" :disabled="cancelling" @click="cancelCurrentRequest">{{ cancelling ? '正在确认取消…' : '取消本次请求' }}</button>
          </div>
          <small v-if="tutorRestoring" role="status">正在核对并恢复辅导记录…</small>
          <details class="tutor-attachment">
            <summary>附带代码与运行记录</summary>
            <p>可编辑附带代码；修改后需重新运行自测。</p>
            <n-input v-model:value="tutorCode" type="textarea" :autosize="{ minRows: 3, maxRows: 8 }" :disabled="chatLoading" placeholder="粘贴需要讨论的 Python 代码，可随时清空移除" :input-props="{ 'aria-label': '辅导附带代码' }" />
            <button type="button" :disabled="chatLoading || tutorRunning || !tutorCode.trim()" @click="runTutorCode">{{ tutorRunning ? '运行中…' : '运行这段代码' }}</button>
            <span v-if="tutorRun">{{ tutorRun.code === tutorCode ? '已附带本次服务器自测' : '代码已修改，请重新运行' }}</span>
            <pre v-if="tutorRun">{{ tutorRun.result.stderr || tutorRun.result.stdout || '运行结束，无输出。' }}</pre>
          </details>
          <div class="prompt-line">
            <n-dropdown
              trigger="click"
              :options="toolMenuOptions"
              @select="runToolAction"
            >
              <button type="button" class="prompt-tool" aria-label="更多工具" :disabled="chatLoading">
                <n-icon :component="AddOutline" />
              </button>
            </n-dropdown>
            <button
              type="button"
              class="prompt-tool"
              :class="{ 'prompt-tool--active': voiceListening }"
              aria-label="语音输入"
              :disabled="chatLoading"
              @click="toggleVoiceInput"
            >
              <n-icon :component="MicOutline" />
            </button>
            <n-input
              v-model:value="prompt"
              placeholder="向小E提问，或让小E帮你分析学习情况..."
              class="prompt-input"
              :bordered="false"
              @keydown.enter.prevent="sendChat"
            />
            <button type="button" class="prompt-send" aria-label="发送" :disabled="chatLoading" @click="sendChat">
              <n-icon :component="PaperPlaneOutline" />
            </button>
          </div>
          <div class="prompt-actions">
            <button v-for="item in actions" :key="item.label" type="button" :disabled="chatLoading" @click="item.handler">
              <n-icon :component="item.icon" />
              {{ item.label }}
            </button>
          </div>
        </section>

      </section>
    </main>
  </DashboardShell>
</template>

<style scoped>
.tutor-mode-picker { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.tutor-mode-picker button, .tutor-attachment button { font: inherit; color: inherit; background: transparent; border: 1px solid rgb(128 150 160 / 45%); border-radius: 7px; padding: 5px 9px; cursor: pointer; }
.tutor-mode-picker button[aria-pressed="true"] { border-color: #22afa9; background: rgb(34 175 169 / 12%); }
.tutor-mode-picker button:focus-visible, .tutor-attachment button:focus-visible { outline: 2px solid #22afa9; outline-offset: 2px; }
.tutor-mode-picker button:disabled, .tutor-attachment button:disabled { opacity: .5; cursor: default; }
.tutor-attachment { margin-bottom: 12px; font-size: 13px; }
.tutor-attachment summary { cursor: pointer; }
.tutor-attachment button { margin-top: 8px; margin-right: 10px; }
.tutor-attachment pre { max-height: 140px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; }
.tutor-code-stale { display: block; margin: 6px 0; }
:global(html[data-plex-style="comic"] .tutor-mode-picker button) { border-width: 2px; border-radius: 4px 10px 4px 10px; }
.messenger-shell {
  display: flex;
  height: 100dvh;
  min-height: 100dvh;
  overflow: hidden;
  background: #020a12;
  color: #edf7ff;
  font-family:
    'Outfit',
    'Noto Sans SC',
    'Microsoft YaHei',
    system-ui,
    sans-serif;
}

.messenger-shell--collapsed .messenger-sidebar {
  width: 84px;
}

.messenger-sidebar {
  position: relative;
  z-index: 4;
  width: 230px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 2.25rem 0 1.5rem;
  background:
    radial-gradient(circle at 22% 8%, rgba(20, 241, 226, 0.08), transparent 26%),
    linear-gradient(180deg, rgba(3, 15, 25, 0.98), rgba(1, 8, 15, 0.99));
  border-right: 1px solid rgba(110, 228, 255, 0.11);
  transition: width 0.2s ease;
}

.messenger-sidebar__brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0 2.55rem 2.85rem;
  color: #25f5ee;
}

.brand-mark {
  filter: drop-shadow(0 0 12px rgba(37, 245, 238, 0.65));
}

.messenger-sidebar__name {
  color: #ffffff;
  font-size: 1.75rem;
  font-weight: 760;
  letter-spacing: 0.08em;
}

.messenger-sidebar__nav {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 0.55rem;
}

.messenger-nav {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 76px;
  gap: 0.95rem;
  padding: 0.7rem 1.35rem 0.7rem 2.55rem;
  color: rgba(220, 230, 241, 0.74);
  text-decoration: none;
  transition: background 0.18s ease, color 0.18s ease;
}

.messenger-nav:hover {
  color: #ffffff;
  background: rgba(37, 245, 238, 0.045);
}

.messenger-nav--active {
  color: #ffffff;
  background:
    linear-gradient(90deg, rgba(16, 240, 192, 0.25), rgba(16, 240, 192, 0.07) 72%, transparent),
    rgba(6, 182, 212, 0.04);
}

.messenger-nav__bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  opacity: 0;
  background: linear-gradient(180deg, #5ffff3, #12d8c8);
  box-shadow: 0 0 18px rgba(37, 245, 238, 0.76);
}

.messenger-nav--active .messenger-nav__bar {
  opacity: 1;
}

.messenger-nav__icon {
  flex: 0 0 auto;
  font-size: 1.95rem;
}

.messenger-nav__copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.25rem;
  line-height: 1.1;
}

.messenger-nav__label {
  font-size: 1rem;
  font-weight: 670;
  white-space: nowrap;
}

.messenger-nav__sub {
  color: rgba(221, 230, 239, 0.55);
  font-size: 0.72rem;
  font-weight: 680;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.messenger-nav--active .messenger-nav__label,
.messenger-nav--active .messenger-nav__sub {
  color: #52fff1;
  text-shadow: 0 0 14px rgba(37, 245, 238, 0.5);
}

.messenger-sidebar__collapse {
  width: 56px;
  height: 56px;
  align-self: center;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 50%;
  background: rgba(12, 27, 40, 0.68);
  color: #d9f4ff;
  cursor: pointer;
  font-size: 1.5rem;
}

.messenger-main {
  position: relative;
  display: flex;
  flex-direction: column;
  flex: 1 1 0;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 38%, rgba(52, 211, 153, 0.08), transparent 30%),
    radial-gradient(circle at 76% 55%, rgba(22, 78, 99, 0.2), transparent 34%),
    linear-gradient(180deg, #06121f 0%, #020a12 61%, #01070e 100%);
}

.messenger-topbar {
  position: relative;
  z-index: 3;
  display: grid;
  grid-template-columns: minmax(260px, 1fr) minmax(320px, 540px) minmax(260px, 1fr);
  align-items: start;
  gap: 1.5rem;
  padding: 2.15rem 2.8rem 1.15rem 3.7rem;
}

.messenger-heading h1 {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  margin: 0;
  color: #ffffff;
  font-size: clamp(1.7rem, 2.2vw, 2.25rem);
  font-weight: 740;
  line-height: 1.1;
}

.messenger-heading h1 span {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #2efff1;
  box-shadow: 0 0 12px rgba(46, 255, 241, 0.85);
}

.messenger-heading p {
  margin: 0.7rem 0 0;
  color: rgba(221, 230, 239, 0.72);
  font-size: 0.98rem;
}

.messenger-search__input :deep(.n-input) {
  --n-height: 58px !important;
  --n-color: rgba(6, 18, 31, 0.66) !important;
  --n-color-focus: rgba(8, 24, 39, 0.86) !important;
  --n-border: 1px solid rgba(130, 212, 255, 0.12) !important;
  --n-border-hover: 1px solid rgba(37, 245, 238, 0.32) !important;
  --n-text-color: #edf7ff !important;
  --n-placeholder-color: rgba(210, 225, 238, 0.55) !important;
  font-size: 0.96rem;
}

.messenger-search__icon {
  color: #e8f9ff;
  font-size: 1.35rem;
}

.messenger-userbar {
  justify-self: end;
  display: flex;
  align-items: center;
  gap: 1.3rem;
}

.messenger-userbar__divider {
  width: 1px;
  height: 40px;
  background: rgba(219, 235, 249, 0.1);
}

.messenger-icon-btn {
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #edf7ff;
  cursor: pointer;
}

.messenger-user {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  border: 0;
  background: transparent;
  color: #ffffff;
  cursor: pointer;
}

.messenger-user__avatar {
  border: 1px solid rgba(160, 211, 244, 0.26);
  background:
    radial-gradient(circle, rgba(82, 157, 255, 0.22), transparent 62%),
    #061827 !important;
  box-shadow:
    0 0 0 5px rgba(87, 139, 191, 0.1),
    0 0 18px rgba(37, 245, 238, 0.22);
}

.avatar-bot {
  position: relative;
  display: grid;
  width: 31px;
  height: 24px;
  place-items: center;
}

.avatar-bot__head {
  width: 28px;
  height: 20px;
  border-radius: 9px;
  background: #e9f3fb;
  box-shadow: inset 0 -8px 0 #111926;
}

.avatar-bot__head::before,
.avatar-bot__head::after {
  content: '';
  position: absolute;
  top: 13px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #36fff1;
  box-shadow: 0 0 7px rgba(54, 255, 241, 0.9);
}

.avatar-bot__head::before {
  left: 9px;
}

.avatar-bot__head::after {
  right: 9px;
}

.messenger-user__copy {
  display: grid;
  gap: 0.2rem;
  text-align: left;
}

.messenger-user__copy strong {
  font-size: 0.96rem;
}

.messenger-user__copy em {
  width: fit-content;
  padding: 0.04rem 0.34rem;
  border-radius: 0.35rem;
  background: rgba(37, 245, 238, 0.18);
  color: #57fff2;
  font-size: 0.76rem;
  font-style: normal;
}

.messenger-stage {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: minmax(200px, 1fr) auto;
  grid-template-areas:
    'analysis'
    'prompt';
  gap: 0.9rem;
  flex: 1 1 0;
  height: auto;
  min-height: 0;
  overflow-y: auto;
  padding: 0 var(--plex-page-gutter-x) calc(var(--plex-page-gutter-bottom) + 0.25rem);
}

.station-bg {
  position: absolute;
  z-index: 0;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.station-bg::before {
  content: '';
  position: absolute;
  inset: 0;
  opacity: 0.48;
  background-image:
    radial-gradient(1px 1px at 12% 24%, rgba(255, 255, 255, 0.36), transparent),
    radial-gradient(1px 1px at 43% 18%, rgba(93, 214, 255, 0.45), transparent),
    radial-gradient(1px 1px at 63% 40%, rgba(255, 255, 255, 0.2), transparent),
    radial-gradient(1px 1px at 87% 22%, rgba(93, 214, 255, 0.24), transparent);
  background-size: 330px 330px;
}

.station-bg__planet {
  position: absolute;
  left: -12%;
  bottom: 12%;
  width: 31%;
  aspect-ratio: 1;
  border-radius: 50%;
  background:
    radial-gradient(circle at 35% 30%, rgba(203, 232, 255, 0.24), transparent 12%),
    radial-gradient(circle at 55% 58%, rgba(7, 18, 31, 0.96), rgba(3, 12, 22, 0.99) 58%);
  box-shadow:
    inset 36px 24px 84px rgba(129, 207, 255, 0.12),
    -8px -10px 44px rgba(148, 220, 255, 0.18);
}

.station-bg__ring {
  position: absolute;
  left: 50%;
  border: 1px solid rgba(211, 229, 240, 0.09);
  border-radius: 50%;
  transform: translateX(-50%);
}

.station-bg__ring--top {
  top: -190px;
  width: 80%;
  height: 340px;
  border-bottom-color: rgba(230, 241, 249, 0.28);
  box-shadow: inset 0 -10px 40px rgba(198, 218, 230, 0.05);
}

.station-bg__ring--floor {
  bottom: 7%;
  width: 38%;
  height: 120px;
  border-color: rgba(37, 245, 238, 0.2);
  box-shadow: 0 0 42px rgba(37, 245, 238, 0.14);
}

.station-bg__light {
  position: absolute;
  height: 4px;
  border-radius: 99px;
  background: linear-gradient(90deg, transparent, rgba(238, 248, 255, 0.86), transparent);
}

.station-bg__light--one {
  left: 35%;
  top: 7.5%;
  width: 18%;
}

.station-bg__light--two {
  right: -2%;
  top: 8%;
  width: 22%;
  opacity: 0.6;
}

.station-bg__crystal {
  position: absolute;
  width: 20px;
  height: 34px;
  clip-path: polygon(50% 0, 100% 50%, 50% 100%, 0 50%);
  background: linear-gradient(180deg, rgba(97, 247, 255, 0.45), rgba(12, 67, 86, 0.12));
  border: 1px solid rgba(97, 247, 255, 0.18);
}

.station-bg__crystal--one {
  left: 31%;
  top: 38%;
}

.station-bg__crystal--two {
  left: 36%;
  top: 56%;
  transform: scale(0.72);
}

.hero-zone {
  grid-area: hero;
  position: relative;
  z-index: 2;
  display: grid;
  grid-template-columns: minmax(150px, 1fr) minmax(220px, 36%) minmax(150px, 1fr);
  grid-template-rows: minmax(0, 0.42fr) minmax(250px, 40%) minmax(0, 1fr);
  grid-template-areas:
    '. . .'
    'greeting bot trial'
    'fragment . growth';
  gap: 0.5rem 0.85rem;
  min-height: 0;
  overflow: hidden;
}

.float-card {
  position: relative;
  z-index: 2;
  border: 1px solid rgba(105, 219, 255, 0.2);
  border-radius: 0.9rem;
  background:
    linear-gradient(180deg, rgba(13, 31, 49, 0.72), rgba(7, 21, 35, 0.68)),
    rgba(6, 18, 31, 0.7);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.035),
    0 16px 40px rgba(0, 0, 0, 0.16);
  backdrop-filter: blur(14px);
}

/* 四角卡片统一尺寸，避免宽屏/断点下宽高不一致 */
.float-card--greeting,
.float-card--trial,
.float-card--fragment,
.float-card--growth {
  width: 270px;
  max-width: min(270px, 100%);
  min-height: 176px;
  padding: 1.3rem 1.45rem;
  box-sizing: border-box;
}

.float-card h2,
.float-card p {
  margin: 0;
}

/* 与中间行小 E 耳朵齐平：贴 bot 两侧，略偏上对齐耳部 */
.float-card--greeting {
  grid-area: greeting;
  justify-self: end;
  align-self: start;
  margin: 1.15rem 1.25rem 0 6.75rem;
}

.float-card--greeting h2 {
  color: #ffffff;
  font-size: 1.18rem;
}

.float-card--greeting h2 span {
  color: #29fff0;
}

.float-card--greeting p {
  margin-top: 0.7rem;
  color: rgba(230, 240, 247, 0.82);
}

.wave-bars {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 1.55rem;
  color: #31fff2;
}

.wave-bars span {
  width: 2px;
  height: 11px;
  border-radius: 99px;
  background: currentColor;
  box-shadow: 0 0 8px rgba(49, 255, 242, 0.7);
}

.wave-bars span:nth-child(2),
.wave-bars span:nth-child(4) {
  height: 18px;
}

.float-card--fragment {
  grid-area: fragment;
  justify-self: start;
  align-self: start;
  margin: 0.1rem 0 1.85rem 6.75rem;
}

.float-card--fragment p {
  color: #ffffff;
  font-size: 1rem;
}

.float-card--fragment strong {
  display: block;
  margin-top: 1rem;
  color: #ffffff;
  font-size: 2rem;
  font-weight: 650;
}

.float-card--fragment strong span {
  font-size: 1rem;
}

.float-card__action {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  margin-top: 1rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: #25f5ee;
  cursor: pointer;
  font-size: 0.92rem;
  font-weight: 650;
  text-decoration: none;
}

.float-card__watermark {
  position: absolute;
  right: 1.4rem;
  bottom: 1.4rem;
  color: rgba(37, 245, 238, 0.24);
  font-size: 3.5rem;
}

.float-card--trial {
  grid-area: trial;
  justify-self: start;
  align-self: start;
  margin: 1.15rem 6.75rem 0 1.25rem;
}

.float-card--trial h2,
.float-card--growth h2 {
  color: #ffffff;
  font-size: 1.08rem;
  font-weight: 650;
}

.float-card--trial strong {
  display: block;
  margin-top: 1rem;
  color: #ffffff;
  font-size: 1rem;
}

.float-card--trial p {
  margin-top: 0.5rem;
  color: rgba(230, 240, 247, 0.78);
}

.float-card--trial-expanded {
  min-height: auto;
  max-height: min(420px, 52vh);
  overflow-y: auto;
  z-index: 5;
}

.trial-match {
  margin-top: 0.45rem !important;
  font-size: 0.86rem;
}

.trial-summary {
  margin-top: 0.55rem !important;
  color: rgba(221, 230, 239, 0.62) !important;
  font-size: 0.78rem;
  line-height: 1.45;
}

.trial-logic-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  margin-top: 0.65rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: #25f5ee;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 650;
}

.trial-logic-toggle .n-icon {
  font-size: 0.9rem;
  transform: rotate(90deg);
}

.trial-decision-list {
  margin: 0.65rem 0 0;
  padding: 0.65rem 0 0 1.1rem;
  border-top: 1px solid rgba(130, 212, 255, 0.1);
  list-style: none;
}

.trial-decision-list li {
  margin-bottom: 0.55rem;
}

.trial-decision-list li:last-child {
  margin-bottom: 0;
}

.trial-decision-list strong {
  display: block;
  color: #5fffe8;
  font-size: 0.74rem;
  font-weight: 700;
}

.trial-decision-list span {
  display: block;
  margin-top: 0.15rem;
  color: rgba(221, 230, 239, 0.62);
  font-size: 0.72rem;
  line-height: 1.45;
}

.trial-start-link {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  margin-top: 0.75rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: #25f5ee;
  cursor: pointer;
  font: inherit;
  font-weight: 650;
}

.radar {
  position: absolute;
  right: 1.35rem;
  top: 3.4rem;
  display: block;
  width: 70px;
  aspect-ratio: 1;
  border: 1px solid rgba(37, 245, 238, 0.36);
  border-radius: 50%;
  background:
    radial-gradient(circle, rgba(37, 245, 238, 0.3), transparent 12%),
    conic-gradient(from 180deg, rgba(37, 245, 238, 0.22), transparent 35%);
  box-shadow: 0 0 22px rgba(37, 245, 238, 0.12);
}

.radar::before,
.radar::after {
  content: '';
  position: absolute;
  inset: 16px;
  border: 1px solid rgba(37, 245, 238, 0.28);
  border-radius: inherit;
}

.radar::after {
  inset: 31px;
}

.float-card--growth {
  grid-area: growth;
  justify-self: end;
  align-self: start;
  margin: 0.1rem 6.75rem 1.85rem 0;
}

.float-card--growth p {
  margin-top: 0.9rem;
  color: rgba(230, 240, 247, 0.8);
}

.float-card--growth strong,
.float-card--growth span {
  color: #25f5ee;
}

.growth-line {
  position: absolute;
  right: 1.3rem;
  bottom: 1.5rem;
  width: 92px;
  color: #29dff3;
  filter: drop-shadow(0 0 8px rgba(41, 223, 243, 0.5));
}

.assistant-bot {
  grid-area: bot;
  position: relative;
  z-index: 3;
  left: auto;
  top: auto;
  width: 270px;
  height: 290px;
  justify-self: center;
  align-self: center;
  transform: none;
  filter: drop-shadow(0 24px 34px rgba(37, 245, 238, 0.16));
  pointer-events: none;
}

.assistant-bot--corner {
  position: absolute;
  right: var(--plex-page-gutter-x);
  bottom: calc(var(--plex-page-gutter-bottom) + 5.5rem);
  justify-self: end;
  align-self: end;
  opacity: 0.2;
  transform: scale(0.46);
  transform-origin: bottom right;
}

.assistant-bot__crest {
  position: absolute;
  left: 123px;
  top: 0;
  width: 42px;
  height: 66px;
  border-radius: 80% 20% 80% 20%;
  background: linear-gradient(135deg, #4afff2, #14918e);
  transform: rotate(48deg);
}

.assistant-bot__head {
  position: absolute;
  left: 52px;
  top: 38px;
  width: 168px;
  height: 122px;
  border: 13px solid #edf6f8;
  border-radius: 48px;
  background: #101824;
  box-shadow: 0 0 0 8px rgba(141, 210, 230, 0.08);
}

.assistant-bot__head::before,
.assistant-bot__head::after {
  content: '';
  position: absolute;
  top: 47px;
  width: 30px;
  height: 14px;
  border-radius: 999px;
  background: #35fff1;
  box-shadow: 0 0 14px rgba(53, 255, 241, 0.9);
}

.assistant-bot__head::before {
  left: 34px;
  transform: rotate(34deg);
}

.assistant-bot__head::after {
  right: 34px;
  transform: rotate(-34deg);
}

.assistant-bot__ear {
  position: absolute;
  top: 76px;
  width: 44px;
  height: 66px;
  border: 10px solid #dce9ef;
  border-radius: 50%;
  background: #172635;
}

.assistant-bot__ear::after {
  content: '';
  position: absolute;
  inset: 10px;
  border: 4px solid #2edfdc;
  border-radius: inherit;
}

.assistant-bot__ear--left {
  left: 24px;
}

.assistant-bot__ear--right {
  right: 24px;
}

.assistant-bot__body {
  position: absolute;
  left: 88px;
  top: 151px;
  display: grid;
  width: 94px;
  height: 108px;
  place-items: center;
  border-radius: 36px 36px 28px 28px;
  background: #edf6f8;
  color: #27dcd7;
  font-size: 2rem;
}

.assistant-bot__body em {
  font-style: normal;
}

.assistant-bot__arm {
  position: absolute;
  top: 169px;
  width: 74px;
  height: 26px;
  border-radius: 999px;
  background: #edf6f8;
}

.assistant-bot__arm--left {
  left: 36px;
  transform: rotate(-32deg);
}

.assistant-bot__arm--right {
  right: 36px;
  transform: rotate(20deg);
}

.assistant-bot__cape {
  position: absolute;
  right: 24px;
  bottom: 62px;
  width: 150px;
  height: 82px;
  border-radius: 70% 12% 70% 15%;
  background: linear-gradient(135deg, rgba(37, 245, 238, 0.48), rgba(13, 64, 83, 0.12));
  transform: rotate(-6deg);
  z-index: -1;
}

.analysis-panel {
  grid-area: analysis;
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-self: stretch;
  justify-self: center;
  width: min(1180px, 100%);
  min-height: 0;
  max-height: none;
  margin-top: 0;
  overflow: hidden;
  padding: 1.15rem 1.25rem 1.2rem;
  border: 1px solid rgba(90, 208, 255, 0.14);
  border-radius: 1.2rem;
  background:
    linear-gradient(180deg, rgba(8, 25, 39, 0.76), rgba(4, 15, 26, 0.68)),
    rgba(4, 14, 24, 0.68);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.035);
  backdrop-filter: blur(16px);
}

.analysis-panel header h2 {
  margin: 0;
  color: rgba(235, 247, 255, 0.9);
  font-size: 1rem;
  font-weight: 650;
}

.analysis-panel header h2 span {
  color: #26ffee;
  letter-spacing: 0.15em;
}

.analysis-panel__head {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.analysis-panel__title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.messenger-box {
  position: relative;
}

.messenger-box__toggle {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  width: 100%;
  padding: 0.45rem 0.65rem;
  border-radius: 12px;
  border: 1px solid rgba(110, 228, 255, 0.2);
  background:
    linear-gradient(135deg, rgba(37, 245, 238, 0.08), transparent 55%),
    rgba(6, 22, 34, 0.82);
  color: rgba(235, 247, 255, 0.94);
  cursor: pointer;
  text-align: left;
}

.messenger-box__label {
  flex: 0 0 auto;
  padding: 0.12rem 0.45rem;
  border-radius: 6px;
  border: 1px solid rgba(37, 245, 238, 0.35);
  color: #26ffee;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.messenger-box__current {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.82rem;
}

.messenger-box__chevron {
  flex: 0 0 auto;
  color: rgba(148, 163, 184, 0.9);
  font-size: 0.75rem;
}

.messenger-box__panel {
  position: absolute;
  z-index: 12;
  top: calc(100% + 0.35rem);
  left: 0;
  right: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  max-height: min(280px, 42vh);
  overflow-y: auto;
  padding: 0.55rem;
  border-radius: 12px;
  border: 1px solid rgba(110, 228, 255, 0.22);
  background: rgba(4, 16, 26, 0.96);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.35);
}

.messenger-box__panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0 0.15rem 0.25rem;
  font-size: 0.68rem;
  color: rgba(148, 163, 184, 0.92);
}

.messenger-session-add {
  width: 2rem;
  height: 2rem;
  border-radius: 999px;
  border: 1px solid rgba(37, 245, 238, 0.35);
  background: rgba(8, 28, 42, 0.85);
  color: #26ffee;
  font-size: 1.25rem;
  line-height: 1;
  cursor: pointer;
}

.messenger-session-add:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.messenger-session-tab {
  display: flex;
  flex-direction: column;
  gap: 0.12rem;
  width: 100%;
  padding: 0.4rem 0.55rem;
  border-radius: 10px;
  border: 1px solid rgba(110, 228, 255, 0.14);
  background: rgba(6, 22, 34, 0.72);
}

.messenger-session-tab.is-active {
  border-color: rgba(37, 245, 238, 0.45);
  box-shadow: inset 0 0 0 1px rgba(37, 245, 238, 0.12);
}

.messenger-session-tab__btn {
  border: 0;
  padding: 0;
  background: transparent;
  color: rgba(235, 247, 255, 0.92);
  font-size: 0.78rem;
  text-align: left;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.messenger-session-tab small {
  font-size: 0.65rem;
  color: rgba(148, 163, 184, 0.85);
}

.messenger-session-rename {
  width: 100%;
  border: 1px solid rgba(37, 245, 238, 0.35);
  border-radius: 6px;
  background: rgba(4, 14, 24, 0.95);
  color: #edf7ff;
  font-size: 0.78rem;
  padding: 0.15rem 0.35rem;
}

.messenger-session-meta {
  margin: 0;
  font-size: 0.68rem;
  color: rgba(148, 163, 184, 0.88);
}

.chat-thread {
  flex: 1 1 auto;
  min-height: 0;
  max-height: none;
  overflow-y: auto;
  margin: 0.75rem 0 0;
  padding: 1rem 1.05rem;
  border-radius: 12px;
  background: rgba(4, 18, 30, 0.72);
  border: 1px solid rgba(110, 228, 255, 0.12);
}

.chat-thread__empty {
  display: grid;
  min-height: 100%;
  place-content: center;
  gap: 0.45rem;
  text-align: center;
}

.chat-thread__empty strong {
  color: rgba(237, 247, 255, 0.9);
  font-size: 1rem;
}

.chat-thread__empty p {
  margin: 0;
  color: rgba(221, 232, 241, 0.58);
  font-size: 0.86rem;
}

.chat-thread__item {
  width: fit-content;
  max-width: min(760px, 84%);
  margin: 0 0 0.55rem;
  padding: 0.55rem 0.85rem;
  border-radius: 12px;
  font-size: 0.88rem;
  line-height: 1.5;
}

.chat-thread__item--user {
  margin-left: auto;
  background: rgba(37, 245, 238, 0.1);
}

.chat-thread__item--assistant {
  background: rgba(255, 255, 255, 0.04);
}

.chat-thread__item--user p {
  color: #a5f3fc;
}

.chat-thread__item--assistant p {
  color: rgba(237, 247, 255, 0.88);
}

.chat-thread__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-top: 0.7rem;
}

.chat-thread__download-md {
  display: inline-flex;
  align-items: center;
  padding: 0.4rem 0.85rem;
  border: 1px solid rgba(90, 217, 255, 0.4);
  border-radius: 999px;
  background: rgba(90, 217, 255, 0.1);
  color: #7dd3fc;
  font-size: 0.8rem;
  font-weight: 650;
  cursor: pointer;
}

.chat-thread__download-md:hover {
  background: rgba(90, 217, 255, 0.18);
}

.chat-thread__pick {
  display: inline-flex;
  margin-top: 0.65rem;
  padding: 0.45rem 0.85rem;
  border: 1px solid rgba(16, 240, 192, 0.35);
  border-radius: 999px;
  background: rgba(16, 240, 192, 0.1);
  color: #22ffde;
  font-size: 0.82rem;
  cursor: pointer;
}

.chat-thread__pick:hover {
  background: rgba(16, 240, 192, 0.18);
}

.chat-thread__retry {
  display: inline-flex;
  margin-top: 0.55rem;
  margin-left: 0.45rem;
  padding: 0.35rem 0.75rem;
  border: 1px solid rgba(255, 197, 109, 0.45);
  border-radius: 999px;
  background: rgba(255, 197, 109, 0.1);
  color: #ffc56d;
  font-size: 0.78rem;
  font-weight: 650;
  cursor: pointer;
}

.chat-thread__retry:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chat-thread__loading {
  margin: 0;
  color: rgba(237, 247, 255, 0.55);
  font-size: 0.82rem;
}

.chat-thread__stage {
  margin: 0 0 0.35rem;
  color: rgba(125, 211, 252, 0.88);
  font-size: 0.8rem;
}

.chat-thread__cursor {
  display: inline-block;
  width: 8px;
  height: 1em;
  margin-left: 2px;
  vertical-align: text-bottom;
  background: #25f5ee;
  border-radius: 1px;
  animation: chat-cursor-blink 0.9s steps(2, start) infinite;
}

@keyframes chat-cursor-blink {
  to {
    visibility: hidden;
  }
}

.chat-thread__illustration {
  margin: 0.65rem 0 0;
  padding: 0.55rem;
  border-radius: 12px;
  background: rgba(4, 20, 30, 0.72);
  border: 1px solid rgba(110, 228, 255, 0.18);
}

.chat-thread__illustration img {
  display: block;
  width: 100%;
  max-height: 280px;
  object-fit: contain;
  border-radius: 8px;
  background: #fff;
}

.chat-thread__illustration figcaption {
  margin-top: 0.4rem;
  color: rgba(200, 230, 240, 0.7);
  font-size: 0.75rem;
  text-align: center;
}

.prompt-dock {
  grid-area: prompt;
  position: relative;
  z-index: 2;
  align-self: end;
  justify-self: center;
  width: min(1180px, 100%);
  margin-top: 0;
  padding: 0.75rem 1rem 0.85rem;
  border: 1px solid rgba(37, 245, 238, 0.28);
  border-radius: 1.1rem;
  background:
    linear-gradient(180deg, rgba(8, 25, 39, 0.78), rgba(4, 15, 26, 0.72)),
    rgba(4, 14, 24, 0.72);
  backdrop-filter: blur(16px);
  overflow: hidden;
}

.prompt-dock--tech {
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.04),
    0 0 28px rgba(37, 245, 238, 0.08);
}

.prompt-dock__glow {
  position: absolute;
  inset: -1px;
  border-radius: inherit;
  background: linear-gradient(120deg, transparent, rgba(37, 245, 238, 0.18), transparent 65%);
  opacity: 0.35;
  animation: prompt-border-glow 4.5s ease-in-out infinite;
  pointer-events: none;
}

@keyframes prompt-border-glow {
  0%,
  100% {
    transform: translateX(-30%);
    opacity: 0.2;
  }
  50% {
    transform: translateX(30%);
    opacity: 0.55;
  }
}

.prompt-line {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  padding-bottom: 0.55rem;
  border-bottom: 1px solid rgba(224, 237, 247, 0.09);
}

.prompt-tool {
  display: grid;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 50%;
  border: 1px solid rgba(110, 228, 255, 0.18);
  background: rgba(8, 20, 34, 0.85);
  color: #9be7ff;
  cursor: pointer;
}

.prompt-tool--active {
  border-color: rgba(255, 120, 120, 0.65);
  color: #ffb4b4;
  box-shadow: 0 0 0 1px rgba(255, 120, 120, 0.25);
}

.prompt-input {
  flex: 1;
  min-width: 0;
}

.prompt-input :deep(.n-input) {
  --n-color: transparent !important;
  --n-text-color: #edf7ff !important;
  --n-placeholder-color: rgba(210, 225, 238, 0.55) !important;
  font-size: 1rem;
}

.prompt-line button,
.prompt-send {
  display: grid;
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  place-items: center;
  border: 0;
  background: transparent;
  color: #2efff1;
  cursor: pointer;
  font-size: 1.6rem;
}

.prompt-send {
  border-radius: 50%;
  transition: background 0.2s ease, box-shadow 0.2s ease;
}

.prompt-send:hover:not(:disabled) {
  background: rgba(37, 245, 238, 0.1);
  box-shadow: 0 0 18px rgba(37, 245, 238, 0.35);
}

.prompt-send:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.prompt-actions {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.65rem;
  margin-top: 0.65rem;
}

.prompt-actions button {
  position: relative;
  display: inline-flex;
  min-height: 42px;
  align-items: center;
  justify-content: center;
  gap: 0.65rem;
  overflow: hidden;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 0.7rem;
  background: rgba(6, 18, 31, 0.55);
  color: rgba(237, 247, 255, 0.86);
  cursor: pointer;
  font-size: 0.86rem;
  font-weight: 650;
  transition:
    border-color 0.22s ease,
    background 0.22s ease,
    box-shadow 0.22s ease,
    transform 0.22s ease;
}

.prompt-actions button::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(120deg, transparent, rgba(37, 245, 238, 0.12), transparent);
  transform: translateX(-120%);
  transition: transform 0.45s ease;
}

.prompt-actions button:hover:not(:disabled) {
  border-color: rgba(37, 245, 238, 0.35);
  background: rgba(8, 28, 42, 0.78);
  box-shadow: 0 0 20px rgba(37, 245, 238, 0.12);
  transform: translateY(-1px);
}

.prompt-actions button:hover:not(:disabled)::before {
  transform: translateX(120%);
}

.prompt-actions button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.prompt-actions .n-icon {
  color: #25f5ee;
  font-size: 1.25rem;
}

@media (max-width: 1280px) {
  .messenger-topbar {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .messenger-userbar {
    justify-self: start;
  }

  .messenger-stage {
    grid-template-columns: 1fr;
    grid-template-rows: minmax(200px, 1fr) auto;
    grid-template-areas:
      'analysis'
      'prompt';
    height: auto;
    min-height: 0;
    overflow-y: auto;
  }

  .hero-zone {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto minmax(0, 1fr) auto;
    grid-template-areas:
      'bot bot'
      'greeting trial'
      'fragment growth';
    min-height: 520px;
  }

  .float-card--greeting,
  .float-card--trial {
    align-self: center;
    margin: 0.65rem 0.5rem;
  }

  .float-card--greeting {
    justify-self: end;
    margin-left: 0.75rem;
  }

  .float-card--trial {
    justify-self: start;
    margin-right: 0.75rem;
  }

  .float-card--fragment,
  .float-card--growth {
    width: 270px;
    max-width: min(270px, calc(100% - 1rem));
    min-height: 176px;
    align-self: start;
    margin-top: 0.1rem;
    margin-bottom: 1.35rem;
  }

  .float-card--fragment {
    justify-self: end;
    margin-left: 0.75rem;
    margin-right: 0.35rem;
  }

  .float-card--growth {
    justify-self: start;
    margin-right: 0.75rem;
    margin-left: 0.35rem;
  }

  .assistant-bot {
    justify-self: center;
    transform: scale(0.88);
  }

  .assistant-bot--corner {
    display: none;
  }

  .analysis-panel {
    width: min(1180px, 100%);
    margin-top: 0;
    max-height: none;
  }
}

@media (max-width: 900px) {
  .messenger-shell {
    flex-direction: column;
    overflow: auto;
  }

  .messenger-sidebar,
  .messenger-shell--collapsed .messenger-sidebar {
    width: 100%;
    min-height: auto;
    padding: 0.75rem;
  }

  .messenger-sidebar__brand {
    padding: 0.25rem 0.65rem 0.75rem;
  }

  .messenger-sidebar__nav {
    flex-direction: row;
    overflow-x: auto;
    padding-bottom: 0.25rem;
  }

  .messenger-nav {
    min-width: 132px;
    min-height: 64px;
    padding: 0.6rem 0.85rem;
  }

  .messenger-sidebar__collapse {
    display: none;
  }

  .messenger-main {
    overflow: hidden;
  }

  .messenger-topbar,
  .messenger-stage {
    padding-inline: var(--plex-page-gutter-x);
  }

  .messenger-stage {
    grid-template-columns: 1fr;
    grid-template-areas:
      'analysis'
      'prompt';
    min-height: auto;
    padding-inline: var(--plex-page-gutter-x);
  }

  .hero-zone {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto auto auto;
    grid-template-areas:
      'bot'
      'greeting'
      'trial'
      'fragment'
      'growth';
    min-height: auto;
    gap: 0.75rem;
  }

  .float-card--greeting,
  .float-card--fragment,
  .float-card--trial,
  .float-card--growth {
    justify-self: center;
    align-self: stretch;
    width: min(270px, 100%);
    max-width: min(270px, 100%);
    min-height: 176px;
    margin: 0;
  }

  .assistant-bot {
    transform: scale(0.76);
    margin: 0.5rem auto;
  }

  .analysis-panel {
    width: 100%;
    margin-top: 0;
    max-height: none;
  }

  .prompt-dock {
    width: 100%;
  }

  .prompt-actions {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (prefers-reduced-motion: reduce) {
  .chat-thread__cursor,
  .prompt-dock__glow {
    animation: none;
  }
}
</style>

<style scoped>
.analysis-panel__head{display:flex;flex-direction:row;align-items:center;justify-content:space-between;gap:12px;flex:none;min-width:0}
.conversation-modes{display:flex;gap:4px;padding:4px;border:1px solid var(--plex-border);border-radius:12px;flex-shrink:0}
.conversation-modes button{padding:8px 14px;border:0;border-radius:8px;color:var(--plex-text);background:transparent;cursor:pointer;white-space:nowrap}
.conversation-modes button[aria-pressed=true]{background:color-mix(in srgb,var(--plex-primary,#55eee9) 18%,transparent);color:var(--plex-text)}
.conversation-modes button:focus-visible,.messenger-box__toggle:focus-visible{outline:2px solid var(--plex-primary,#55eee9);outline-offset:2px}
.messenger-header-tools{display:flex;align-items:center;gap:10px;min-width:0;margin-left:auto}
.messenger-box{position:relative;min-width:0;width:180px}
.messenger-box__panel{position:static;width:min(320px,90vw);max-height:min(380px,60dvh);overflow-y:auto;background:var(--plex-bg-card,#11263a);color:var(--plex-text);box-shadow:0 10px 28px #0004;scrollbar-width:thin;scrollbar-color:var(--plex-primary,#55eee9) transparent}
.messenger-box__panel small{color:var(--plex-text-muted)}
.messenger-session-tab__btn{color:var(--plex-text)}
.chat-thread{scrollbar-width:none}.chat-thread::-webkit-scrollbar{width:0}.prompt-actions{display:none}
.tutor-usage-details{margin:0}.tutor-usage-details>div{display:flex;justify-content:space-between;gap:16px;padding:12px 0;border-bottom:1px solid var(--plex-border)}.tutor-usage-details dt{color:var(--plex-text-muted)}.tutor-usage-details dd{margin:0;text-align:right;overflow-wrap:anywhere}
@media(max-width:700px){.analysis-panel__head{flex-wrap:wrap}.messenger-header-tools{justify-content:flex-end;flex:1 1 100%}.messenger-box{width:min(190px,55vw)}.conversation-modes{width:100%}.conversation-modes button{flex:1}.analysis-panel{padding:12px}}
</style>
