<script setup lang="ts">
import { createRequestId } from '../../utils/browserCrypto'
import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import { NButton, NIcon, NInput, NSpin, useMessage } from 'naive-ui'
import { ChatbubbleEllipsesOutline, CloseOutline, MicOutline, SendOutline } from '@vicons/ionicons5'
import { acknowledgeTutorDisplay } from '../../api/learnerState'
import { askTutor, cancelTutorTurn, tutorModes, type TutorMode, type TutorRequest, type TutorResponse } from '../../api/tutoring'
import TutorResponseCard from '../student/TutorResponseCard.vue'
import MarkdownRenderer from '../common/MarkdownRenderer.vue'
import MessengerKnowledgeCard from '../student/MessengerKnowledgeCard.vue'
import type { MessengerKnowledge } from '../../api/rag'
import { useSpeechRecognitionInput } from '../../composables/useSpeechRecognitionInput'
import { xiaoEThinkingMessage, XIAO_E_PERSONA_INTRO } from '../../utils/xiaoEPersona'
import { useAuthStore } from '../../stores/auth'
import { fetchTutorContext, type TutorContextView } from '../../api/tutorContext'

export type TrialCoachContext = {
  runId?: string
  questionVersion?: string
  runIsStale?: boolean
  formalQuestionId?: number
  exerciseId: string
  questionTitle: string
  questionPrompt?: string
  topic?: string
  constraints?: string[]
  code: string
  stderr?: string
  stdout?: string
  expectedOutput?: string
  failedCases?: Array<{ label: string; expected: string; actual: string; error?: string }>
  caseResults: Array<{ passed: boolean }>
  allPassed: boolean
}

type ChatMessage = {
  tutor?: TutorResponse
  retry?: TutorRequest
  codeSnapshot?: string
  id: string
  role: 'user' | 'assistant'
  content: string
  agentName?: string
  questionPick?: { code: string; id: string; title: string }
  knowledge?: MessengerKnowledge | null
}

const props = defineProps<{
  context: TrialCoachContext
}>()

const messageApi = useMessage()
const auth = useAuthStore()

const { listening: voiceListening, toggle: toggleVoiceInput } = useSpeechRecognitionInput({
  getText: () => inputText.value,
  setText: (value) => {
    inputText.value = value
  },
  message: messageApi,
})

const BALL_SIZE = 52
const MARGIN = 20
const DIALOG_GAP = 14
const DEFAULT_DIALOG_WIDTH = 500
const DEFAULT_DIALOG_HEIGHT = 600
const MIN_DIALOG_WIDTH = 360
const MIN_DIALOG_HEIGHT = 420

const pageActive = ref(true)
const dialogOpen = ref(false)
const loading = ref(false)
const cancelling = ref(false)
const pendingTutorId = ref<string>()
const contextLoading = ref(false)
const contextLoaded = ref(false)
const contextError = ref('')
const verifiedContext = ref<TutorContextView | null>(null)
const includeCode = ref(true)
let coachRequestId = 0
const inputText = ref('')
const messages = ref<ChatMessage[]>([])
const messagesEl = ref<HTMLElement | null>(null)
const activeIntent = ref<TutorMode>('next_step')
const tutorSessionId = ref<string>()
const hintLevel = ref(2)
const hintLevelOptions = [
  { label: 'L1 思路', value: 1 },
  { label: 'L2 定位', value: 2 },
]

const dialogWidth = ref(DEFAULT_DIALOG_WIDTH)
const dialogHeight = ref(DEFAULT_DIALOG_HEIGHT)
const viewportWidth = ref(window.innerWidth)
const viewportHeight = ref(window.innerHeight)
const resizing = ref(false)
const resizeStart = { x: 0, y: 0, width: 0, height: 0 }

const posX = ref(0)
const posY = ref(0)
const dragging = ref(false)
const dragMoved = ref(false)
const dragOffset = { x: 0, y: 0 }

const floatStyle = computed(() => ({
  left: `${posX.value}px`,
  top: `${posY.value}px`,
}))

const maxDialogWidth = computed(() => viewportWidth.value - MARGIN * 2)
const maxDialogHeight = computed(() => viewportHeight.value - MARGIN * 2)

const dialogStyle = computed(() => {
  const width = Math.min(dialogWidth.value, maxDialogWidth.value)
  const height = Math.min(dialogHeight.value, maxDialogHeight.value)
  const preferAbove = posY.value > window.innerHeight * 0.42
  const left = Math.max(MARGIN, Math.min(posX.value + BALL_SIZE - width, window.innerWidth - width - MARGIN))
  const preferredTop = preferAbove ? posY.value - DIALOG_GAP - height : posY.value + BALL_SIZE + DIALOG_GAP
  const top = Math.max(MARGIN, Math.min(preferredTop, window.innerHeight - height - MARGIN))

  return {
    width: `${width}px`,
    height: `${height}px`,
    position: 'fixed' as const,
    left: `${left}px`,
    top: `${top}px`,
  }
})

const runStatusLabel = computed(() => {
  if (props.context.runIsStale) return '代码已修改，旧运行结果仅供回看'
  if (!props.context.caseResults.length) return '尚未运行测试'
  if (props.context.allPassed) return '全部通过'
  const passed = props.context.caseResults.filter((item) => item.passed).length
  return `${passed}/${props.context.caseResults.length} 通过`
})

const shortcuts = tutorModes.map(item => ({ intent: item.mode, label: item.label }))

function clampPosition(x: number, y: number) {
  const maxX = window.innerWidth - BALL_SIZE - MARGIN
  const maxY = window.innerHeight - BALL_SIZE - MARGIN
  return {
    x: Math.min(Math.max(MARGIN, x), maxX),
    y: Math.min(Math.max(MARGIN, y), maxY),
  }
}

function clampDialogSize(width: number, height: number) {
  return {
    width: Math.min(Math.max(MIN_DIALOG_WIDTH, width), maxDialogWidth.value),
    height: Math.min(Math.max(MIN_DIALOG_HEIGHT, height), maxDialogHeight.value),
  }
}

function defaultPosition() {
  return clampPosition(window.innerWidth - BALL_SIZE - MARGIN, window.innerHeight - BALL_SIZE - MARGIN)
}

function syncDefaultPosition() {
  const next = defaultPosition()
  posX.value = next.x
  posY.value = next.y
}

function onWindowResize() {
  viewportWidth.value = window.innerWidth
  viewportHeight.value = window.innerHeight
  const clamped = clampPosition(posX.value, posY.value)
  posX.value = clamped.x
  posY.value = clamped.y
  const size = clampDialogSize(dialogWidth.value, dialogHeight.value)
  dialogWidth.value = size.width
  dialogHeight.value = size.height
}

function onPointerDown(event: PointerEvent) {
  if (event.button !== 0) return
  dragOffset.x = event.clientX - posX.value
  dragOffset.y = event.clientY - posY.value
  dragging.value = true
  dragMoved.value = false
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
}

function onPointerMove(event: PointerEvent) {
  if (!dragging.value) return
  const nextX = event.clientX - dragOffset.x
  const nextY = event.clientY - dragOffset.y
  if (Math.abs(nextX - posX.value) > 4 || Math.abs(nextY - posY.value) > 4) {
    dragMoved.value = true
  }
  const clamped = clampPosition(nextX, nextY)
  posX.value = clamped.x
  posY.value = clamped.y
}

function onPointerUp(event: PointerEvent) {
  if (!dragging.value) return
  dragging.value = false
  try {
    ;(event.currentTarget as HTMLElement).releasePointerCapture(event.pointerId)
  } catch {
    /* ignore */
  }
  if (!dragMoved.value) {
    dialogOpen.value = !dialogOpen.value
  }
}

function onResizeDown(event: PointerEvent) {
  event.stopPropagation()
  if (event.button !== 0) return
  resizing.value = true
  resizeStart.x = event.clientX
  resizeStart.y = event.clientY
  resizeStart.width = dialogWidth.value
  resizeStart.height = dialogHeight.value
  window.addEventListener('pointermove', onResizeMove)
  window.addEventListener('pointerup', onResizeUp)
}

function onResizeMove(event: PointerEvent) {
  if (!resizing.value) return
  const deltaX = event.clientX - resizeStart.x
  const deltaY = event.clientY - resizeStart.y
  const size = clampDialogSize(resizeStart.width + deltaX, resizeStart.height + deltaY)
  dialogWidth.value = size.width
  dialogHeight.value = size.height
}

function onResizeUp() {
  resizing.value = false
  window.removeEventListener('pointermove', onResizeMove)
  window.removeEventListener('pointerup', onResizeUp)
}

function buildPayload(intent: TutorMode, userQuestion: string) {
  return {
    request_id: createRequestId(),
    session_id: tutorSessionId.value,
    mode: intent,
    question_ref: props.context.exerciseId,
    formal_question_id: props.context.formalQuestionId,
    question_version: verifiedContext.value?.task?.version,
    run_id: includeCode.value && !props.context.runIsStale ? props.context.runId : undefined,
    code: includeCode.value ? props.context.code : '',
    question: userQuestion,
    hint_level: hintLevel.value,
  } satisfies TutorRequest
}

function buildLocalIntro() {
  const title = verifiedContext.value?.task?.title || '自主代码讨论'
  return `${XIAO_E_PERSONA_INTRO} 当前题目「${title}」。\n${props.context.runId && !props.context.runIsStale ? '发送时会校验当前自测引用；自测不等同正式成绩。' : '目前没有对应当前代码的运行记录；我会先看你的代码和描述。'} 你也可以移除不相关代码再提问。`
}

async function loadPracticeContext() {
  if (contextLoading.value || contextLoaded.value) return
  const requestId = coachRequestId
  contextLoading.value = true
  contextError.value = ''
  try {
    const context = await fetchTutorContext({
      question_ref: props.context.exerciseId,
      formal_question_id: props.context.formalQuestionId,
      code: includeCode.value ? props.context.code : '',
    })
    if (requestId !== coachRequestId) return
    verifiedContext.value = context
    pushMessage('assistant', buildLocalIntro(), '小E')
    contextLoaded.value = true
  } catch (error) {
    if (requestId === coachRequestId) contextError.value = error instanceof Error ? error.message : '无法核对题目，请重试'
  } finally {
    if (requestId === coachRequestId) contextLoading.value = false
    await scrollToBottom()
  }
}

function pushMessage(
  role: ChatMessage['role'],
  content: string,
  agentName?: string,
  questionPick?: ChatMessage['questionPick'],
  knowledge?: MessengerKnowledge | null,
) {
  messages.value.push({
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    role,
    content,
    agentName,
    questionPick,
    knowledge,
  })
}

async function scrollToBottom() {
  await nextTick()
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  }
}

const displayAcks = new Set<string>()
function acknowledgeVisibleTutors() {
  if (!pageActive.value || !dialogOpen.value || document.visibilityState !== 'visible') return
  for (const msg of messages.value) {
    const id = msg.tutor?.display_receipt_id
    if (!id || displayAcks.has(id)) continue
    displayAcks.add(id)
    void acknowledgeTutorDisplay(id).catch(() => {
      displayAcks.delete(id)
      messageApi.warning('提示已显示，但学习记录尚未同步。')
    })
  }
}

async function cancelCurrentTutor() {
  const id=pendingTutorId.value, epoch=coachRequestId
  if(!id || cancelling.value) return
  cancelling.value=true
  try {
    const result=await cancelTutorTurn(id)
    if(epoch!==coachRequestId || pendingTutorId.value!==id) return
    if(!result.cancelled) { messageApi.info('回答已经完成，可以继续查看。'); return }
    ++coachRequestId;loading.value=false;pendingTutorId.value=undefined
    pushMessage('assistant','本次请求已取消。','小E')
  } catch(error) { if(epoch===coachRequestId) messageApi.error(error instanceof Error?error.message:'取消未确认') }
  finally { if(pendingTutorId.value===id || !pendingTutorId.value) cancelling.value=false }
}

async function sendQuestion(question: string, intent: TutorMode = activeIntent.value, retryPayload?: TutorRequest) {
  const text = question.trim()
  if (!pageActive.value || !text || loading.value || !contextLoaded.value) return
  const requestId = coachRequestId
  const payloadSnapshot = retryPayload || buildPayload(intent, text)

  activeIntent.value = intent
  loading.value = true
  pendingTutorId.value = payloadSnapshot.request_id
  if (!retryPayload) pushMessage('user', text)
  inputText.value = ''
  await scrollToBottom()

  try {
    const result = await askTutor(payloadSnapshot)
    if (requestId !== coachRequestId) return
    if (result.context) verifiedContext.value = result.context
    tutorSessionId.value = result.session_id
    hintLevel.value = result.teaching_plan.hint_level
    pushMessage('assistant', result.summary, '小E')
    const added = messages.value[messages.value.length - 1]!
    added.tutor = result
    if (payloadSnapshot.code) added.codeSnapshot = payloadSnapshot.code
    await nextTick()
    acknowledgeVisibleTutors()
  } catch (error) {
    if (requestId !== coachRequestId) return
    const msg = error instanceof Error ? error.message : 'AI 辅导请求失败'
    pushMessage('assistant', msg.includes('404') ? '辅导服务未就绪，请确认后端已重启。' : msg)
    messages.value[messages.value.length - 1]!.retry = payloadSnapshot
  } finally {
    if (requestId === coachRequestId) { loading.value = false; pendingTutorId.value = undefined }
    await scrollToBottom()
  }
}

function onShortcut(intent: TutorMode, label: string) {
  void sendQuestion(inputText.value.trim() || label, intent)
}

function onSend() {
  void sendQuestion(inputText.value, activeIntent.value)
}

function onInputKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    onSend()
  }
}

function closeDialog() {
  dialogOpen.value = false
}

watch(dialogOpen, async (open) => {
  if (open && !messages.value.length) {
    void loadPracticeContext()
  }
  await nextTick()
  if (open) acknowledgeVisibleTutors()
})

watch([() => props.context.exerciseId, () => props.context.formalQuestionId, () => auth.profile?.id], () => {
  ++coachRequestId
  messages.value = []
  tutorSessionId.value = undefined
  verifiedContext.value = null
  contextLoaded.value = contextLoading.value = loading.value = false
  pendingTutorId.value=undefined;cancelling.value=false
  includeCode.value = true
  if (dialogOpen.value) void loadPracticeContext()
})

onMounted(() => {
  syncDefaultPosition()
  const size = clampDialogSize(DEFAULT_DIALOG_WIDTH, DEFAULT_DIALOG_HEIGHT)
  dialogWidth.value = size.width
  dialogHeight.value = size.height
  window.addEventListener('resize', onWindowResize)
  document.addEventListener('visibilitychange', acknowledgeVisibleTutors)
})

function suspendCoach() {
  pageActive.value = false
  dialogOpen.value = false
  dragging.value = false
  onResizeUp()
  if (voiceListening.value) toggleVoiceInput()
}
onActivated(() => { pageActive.value = true })
onDeactivated(suspendCoach)

onBeforeUnmount(() => {
  ++coachRequestId
  dragging.value = false
  resizing.value = false
  window.removeEventListener('resize', onWindowResize)
  document.removeEventListener('visibilitychange', acknowledgeVisibleTutors)
  window.removeEventListener('pointermove', onResizeMove)
  window.removeEventListener('pointerup', onResizeUp)
})
</script>

<template>
  <Teleport to="body">
    <div v-if="pageActive" class="trial-ai-float" :style="floatStyle">
      <Transition name="trial-ai-dialog">
        <div
          v-if="dialogOpen"
          class="trial-ai-float__dialog"
          :class="{ 'is-resizing': resizing }"
          role="dialog"
          aria-label="AI 编程辅导"
          :style="dialogStyle"
        >
          <header class="trial-ai-float__head">
            <div class="trial-ai-float__title">
              <span class="trial-ai-float__dot" aria-hidden="true" />
              <div>
                <strong>小E · 编程辅导</strong>
                <p>{{ context.questionTitle }} · {{ runStatusLabel }}</p>
              </div>
            </div>
            <button type="button" class="trial-ai-float__close" aria-label="关闭" @click="closeDialog">
              <n-icon :component="CloseOutline" />
            </button>
          </header>

          <div class="trial-ai-float__context" aria-live="polite">
            <template v-if="verifiedContext">
              <span v-if="verifiedContext.task">已核对题目 · {{ verifiedContext.task.version.slice(0, 8) }}</span>
              <span v-else>未绑定服务器题面，本次仅讨论代码与描述。</span>
              <span>{{ includeCode ? '附带当前代码' : '本次不附带代码' }}{{ context.runId && includeCode ? ' · 附带服务器自测' : '' }}</span>
              <span v-if="context.runId && includeCode">运行引用 {{ context.runId.slice(0, 8) }}</span>
              <span v-if="context.runIsStale">代码已修改，本次不引用旧运行记录。</span>
              <span v-if="verifiedContext.task?.tutoring_policy === 'disabled'">教师已关闭本次任务的辅导。</span>
              <button type="button" :disabled="loading" @click="includeCode = !includeCode">{{ includeCode ? '移除代码' : '附带代码' }}</button>
              <button type="button" :disabled="loading" @click="tutorSessionId = undefined; contextLoaded = false; loadPracticeContext()">开始新的辅导</button>
            </template>
            <template v-if="contextError">
              <span>{{ contextError }}</span>
              <button type="button" @click="loadPracticeContext">重新核对</button>
            </template>
          </div>

          <div class="trial-ai-float__hint-row">
            <span>提示层级</span>
            <button
              v-for="opt in hintLevelOptions"
              :key="opt.value"
              type="button"
              class="trial-ai-float__chip"
              :class="{ 'is-active': hintLevel === opt.value }"
              :disabled="loading || !contextLoaded || verifiedContext?.task?.tutoring_policy === 'disabled'"
              @click="hintLevel = opt.value"
            >
              {{ opt.label }}
            </button>
          </div>
          <div class="trial-ai-float__shortcuts">
            <button
              v-for="item in shortcuts"
              :key="item.intent"
              type="button"
              class="trial-ai-float__chip"
              :aria-pressed="activeIntent === item.intent"
              :class="{ 'is-active': activeIntent === item.intent }"
              :disabled="loading || !contextLoaded || verifiedContext?.task?.tutoring_policy === 'disabled'"
              @click="onShortcut(item.intent, item.label)"
            >
              {{ item.label }}
            </button>
          </div>

          <div ref="messagesEl" class="trial-ai-float__messages">
            <article
              v-for="msg in messages"
              :key="msg.id"
              class="trial-ai-float__msg"
              :class="msg.role === 'user' ? 'is-user' : 'is-assistant'"
            >
              <header v-if="msg.role === 'assistant' && msg.agentName">
                <small>{{ msg.agentName }}</small>
              </header>
              <template v-if="msg.role === 'assistant'">
                <small v-if="msg.codeSnapshot && msg.codeSnapshot !== context.code" class="trial-ai-float__stale">这条反馈对应旧代码，请勿套用其中的位置说明。</small>
                <TutorResponseCard v-if="msg.tutor" :response="msg.tutor" />
                <MarkdownRenderer v-else :content="msg.content" />
                <MessengerKnowledgeCard v-if="msg.knowledge" :knowledge="msg.knowledge" />
                <button v-if="msg.retry" type="button" :disabled="loading" @click="sendQuestion(msg.retry.question, msg.retry.mode, msg.retry)">重试上次提问</button>
              </template>
              <p v-else>{{ msg.content }}</p>
            </article>
            <div v-if="contextLoading || loading" class="trial-ai-float__typing">
              <n-spin size="small" />
              <span>{{ contextLoading ? xiaoEThinkingMessage('diagnosis') : xiaoEThinkingMessage('trial') }}</span>
            </div>
          </div>

          <footer class="trial-ai-float__composer">
            <div class="trial-ai-float__composer-row">
              <button
                type="button"
                class="trial-ai-float__mic"
                :class="{ 'is-active': voiceListening }"
                aria-label="语音输入"
                :disabled="loading"
                @click="toggleVoiceInput"
              >
                <n-icon :component="MicOutline" />
              </button>
              <n-input
                v-model:value="inputText"
                type="textarea"
                placeholder="有问题尽管问我，小E 来帮你～"
                :autosize="{ minRows: 2, maxRows: 5 }"
                :disabled="loading"
                @keydown="onInputKeydown"
              />
            </div>
            <n-button v-if="loading" :disabled="cancelling" @click="cancelCurrentTutor">{{ cancelling ? '正在确认…' : '取消本次请求' }}</n-button>
            <n-button type="primary" :loading="loading" :disabled="!inputText.trim() || !contextLoaded || verifiedContext?.task?.tutoring_policy === 'disabled'" @click="onSend">
              <template #icon><n-icon :component="SendOutline" /></template>
              发送
            </n-button>
          </footer>

          <button
            type="button"
            class="trial-ai-float__resize"
            aria-label="调整窗口大小"
            @pointerdown="onResizeDown"
          />
        </div>
      </Transition>

      <button
        type="button"
        class="trial-ai-float__ball"
        :class="{ 'is-open': dialogOpen, 'is-dragging': dragging }"
        aria-label="小E 编程辅导"
        @pointerdown="onPointerDown"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
        @pointercancel="onPointerUp"
        @click="($event: MouseEvent) => { if ($event.detail === 0) dialogOpen = !dialogOpen }"
      >
        <span class="trial-ai-float__ball-glow" aria-hidden="true" />
        <n-icon :component="ChatbubbleEllipsesOutline" />
      </button>
    </div>
  </Teleport>
</template>

<style scoped>
.trial-ai-float__context {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 10px;
  padding: 8px 16px;
  background: var(--plex-bg-card, #11263a);
  color: var(--plex-text, #eef7ff);
  font-size: 12px;
  overflow-wrap: anywhere;
}
.trial-ai-float__context button {
  color: inherit;
  background: transparent;
  border: 1px solid currentColor;
  border-radius: 6px;
  padding: 3px 8px;
  cursor: pointer;
}
.trial-ai-float__context button:focus-visible {
  outline: 2px solid var(--plex-accent, #55eee9);
  outline-offset: 3px;
}
.trial-ai-float__stale {
  display: block;
  margin-bottom: 8px;
  color: #f6cd68;
}
@media (prefers-reduced-motion: reduce) {
  .trial-ai-float__ball { animation: none !important; }
  .trial-ai-dialog-enter-active, .trial-ai-dialog-leave-active { transition: none; }
}
.trial-ai-float {
  position: fixed;
  z-index: 2000;
  width: 3.25rem;
  height: 3.25rem;
  touch-action: none;
}

.trial-ai-float__ball {
  position: relative;
  z-index: 2;
  width: 3.25rem;
  height: 3.25rem;
  border: 1px solid rgba(0, 242, 255, 0.38);
  border-radius: 999px;
  cursor: grab;
  display: grid;
  place-items: center;
  color: #00f2ff;
  background: rgba(8, 20, 32, 0.82);
  backdrop-filter: blur(10px);
  box-shadow:
    0 8px 24px rgba(0, 0, 0, 0.35),
    inset 0 1px rgba(255, 255, 255, 0.06);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.trial-ai-float__ball:not(.is-dragging):not(.is-open) {
  animation: trial-ai-breathe 3.4s ease-in-out infinite;
}

.trial-ai-float__ball.is-open {
  border-color: rgba(0, 242, 255, 0.62);
  box-shadow:
    0 10px 28px rgba(0, 242, 255, 0.18),
    inset 0 0 18px rgba(0, 242, 255, 0.08);
}

.trial-ai-float__ball.is-dragging {
  cursor: grabbing;
  animation: none;
  transform: scale(1.05);
}

.trial-ai-float__ball-glow {
  position: absolute;
  inset: -4px;
  border-radius: inherit;
  background: radial-gradient(circle, rgba(0, 242, 255, 0.22), transparent 68%);
  pointer-events: none;
}

.trial-ai-float__ball :deep(.n-icon) {
  position: relative;
  z-index: 1;
  font-size: 1.35rem;
}

.trial-ai-float__dialog {
  position: absolute;
  z-index: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 16px;
  border: 1px solid rgba(0, 242, 255, 0.16);
  background: linear-gradient(165deg, rgba(7, 18, 30, 0.98), rgba(4, 12, 22, 0.96));
  box-shadow:
    0 22px 56px rgba(0, 0, 0, 0.42),
    0 0 0 1px rgba(255, 255, 255, 0.03) inset;
  color: rgba(226, 232, 240, 0.92);
}

.trial-ai-float__dialog.is-resizing {
  user-select: none;
}

.trial-ai-float__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.95rem 1rem 0.65rem;
  border-bottom: 1px solid rgba(130, 212, 255, 0.1);
}

.trial-ai-float__title {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
}

.trial-ai-float__dot {
  width: 0.55rem;
  height: 0.55rem;
  margin-top: 0.35rem;
  border-radius: 999px;
  background: #00f2ff;
  box-shadow: 0 0 10px rgba(0, 242, 255, 0.65);
}

.trial-ai-float__head strong {
  font-size: 0.98rem;
}

.trial-ai-float__head p {
  margin: 0.18rem 0 0;
  font-size: 0.74rem;
  color: rgba(148, 163, 184, 0.92);
}

.trial-ai-float__close {
  border: 0;
  background: transparent;
  color: rgba(148, 163, 184, 0.9);
  cursor: pointer;
  padding: 0.15rem;
}

.trial-ai-float__hint-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  align-items: center;
  margin-bottom: 0.45rem;
  padding: 0 0.15rem;
}
.trial-ai-float__hint-row > span {
  color: rgba(186, 230, 253, 0.65);
  font-size: 0.72rem;
}
.trial-ai-float__chip.is-active {
  border-color: rgba(37, 245, 238, 0.55);
  background: rgba(37, 245, 238, 0.14);
  color: #ccfbf1;
}
.trial-ai-float__shortcuts {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  padding: 0.75rem 1rem 0.55rem;
}

.trial-ai-float__chip {
  border: 1px solid rgba(0, 242, 255, 0.18);
  border-radius: 999px;
  padding: 0.28rem 0.65rem;
  font-size: 0.74rem;
  color: rgba(226, 232, 240, 0.88);
  background: rgba(15, 23, 42, 0.55);
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.trial-ai-float__chip:hover:not(:disabled) {
  border-color: rgba(0, 242, 255, 0.42);
  background: rgba(0, 242, 255, 0.08);
}

.trial-ai-float__chip:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.trial-ai-float__messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0.35rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.trial-ai-float__msg {
  max-width: 92%;
  padding: 0.55rem 0.7rem;
  border-radius: 12px;
  font-size: 0.82rem;
  line-height: 1.55;
}

.trial-ai-float__msg.is-user {
  align-self: flex-end;
  background: rgba(0, 242, 255, 0.12);
  border: 1px solid rgba(0, 242, 255, 0.18);
}

.trial-ai-float__msg.is-assistant {
  align-self: flex-start;
  background: rgba(15, 23, 42, 0.72);
  border: 1px solid rgba(130, 212, 255, 0.12);
}

.trial-ai-float__msg header small {
  display: block;
  margin-bottom: 0.25rem;
  color: #67e8f9;
  font-size: 0.68rem;
}

.trial-ai-float__msg p {
  margin: 0;
  white-space: pre-wrap;
}

.trial-ai-float__pick {
  display: inline-flex;
  margin-top: 0.55rem;
  padding: 0.4rem 0.75rem;
  border: 1px solid rgba(16, 240, 192, 0.35);
  border-radius: 999px;
  background: rgba(16, 240, 192, 0.1);
  color: #22ffde;
  font-size: 0.78rem;
  cursor: pointer;
}

.trial-ai-float__pick:hover {
  background: rgba(16, 240, 192, 0.18);
}

.trial-ai-float__typing {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.35rem 0.2rem;
  font-size: 0.76rem;
  color: rgba(148, 163, 184, 0.95);
}

.trial-ai-float__composer {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  padding: 0.75rem 1rem 1rem;
  border-top: 1px solid rgba(130, 212, 255, 0.1);
  background: rgba(3, 10, 18, 0.55);
}

.trial-ai-float__composer-row {
  display: flex;
  gap: 0.45rem;
  align-items: flex-start;
}

.trial-ai-float__composer-row :deep(.n-input) {
  flex: 1;
}

.trial-ai-float__mic {
  flex-shrink: 0;
  width: 2.25rem;
  height: 2.25rem;
  margin-top: 0.15rem;
  border-radius: 999px;
  border: 1px solid rgba(0, 242, 255, 0.22);
  background: rgba(8, 20, 32, 0.85);
  color: rgba(148, 163, 184, 0.95);
  cursor: pointer;
  display: grid;
  place-items: center;
}

.trial-ai-float__mic.is-active {
  border-color: rgba(0, 242, 255, 0.55);
  color: #00f2ff;
  box-shadow: 0 0 12px rgba(0, 242, 255, 0.25);
}

.trial-ai-float__mic:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.trial-ai-float__composer :deep(.n-input) {
  --n-border: 1px solid rgba(130, 212, 255, 0.16) !important;
  --n-border-hover: 1px solid rgba(0, 242, 255, 0.32) !important;
  --n-border-focus: 1px solid rgba(0, 242, 255, 0.45) !important;
  --n-color: rgba(8, 18, 30, 0.92) !important;
  --n-text-color: rgba(226, 232, 240, 0.92) !important;
}

.trial-ai-float__composer :deep(.n-button) {
  align-self: flex-end;
}

.trial-ai-float__resize {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 18px;
  height: 18px;
  border: 0;
  padding: 0;
  cursor: nwse-resize;
  background: transparent;
  z-index: 3;
}

.trial-ai-float__resize::before {
  content: '';
  position: absolute;
  right: 4px;
  bottom: 4px;
  width: 10px;
  height: 10px;
  border-right: 2px solid rgba(0, 242, 255, 0.45);
  border-bottom: 2px solid rgba(0, 242, 255, 0.45);
  border-radius: 0 0 3px 0;
  opacity: 0.75;
  transition: opacity 0.15s ease;
}

.trial-ai-float__resize:hover::before {
  opacity: 1;
}

.trial-ai-dialog-enter-active,
.trial-ai-dialog-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.trial-ai-dialog-enter-from,
.trial-ai-dialog-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.98);
}

@keyframes trial-ai-breathe {
  0%,
  100% {
    transform: scale(1);
    box-shadow:
      0 8px 24px rgba(0, 0, 0, 0.35),
      0 0 0 0 rgba(0, 242, 255, 0.28);
  }

  50% {
    transform: scale(1.045);
    box-shadow:
      0 10px 28px rgba(0, 242, 255, 0.12),
      0 0 0 8px rgba(0, 242, 255, 0);
  }
}
</style>
