<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { NButton, NIcon, NInput, NSpin, useMessage } from 'naive-ui'
import { ChatbubbleEllipsesOutline, CloseOutline, MicOutline, SendOutline } from '@vicons/ionicons5'
import { trialCoach, type TrialCoachIntent, type TrialCoachPayload, type TrialCoachResult } from '../../api/agentService'
import MarkdownRenderer from '../common/MarkdownRenderer.vue'
import MessengerKnowledgeCard from '../student/MessengerKnowledgeCard.vue'
import type { MessengerKnowledge } from '../../api/rag'
import { useSpeechRecognitionInput } from '../../composables/useSpeechRecognitionInput'
import { xiaoECleanProse, xiaoEThinkingMessage, XIAO_E_PERSONA_INTRO } from '../../utils/xiaoEPersona'
import { trimTrialCoachKnowledge } from '../../utils/trialCoachPresentation'
import { askTutorGuidance, planTutorGuidance, acknowledgeTutorGuidance, type TutorMode, type TutorRecommendation, type TutorGuidanceResult } from '../../api/agentService'
import { TutorGuidanceSession } from '../../utils/tutorGuidanceSession'
import { readTutorGuidance } from '../../api/agentService'
import TutorEvidenceCard from './TutorEvidenceCard.vue'
import { useAuthStore } from '../../stores/auth'

export type TrialCoachContext = {
  exerciseId: string
  trialQuestionId?: number
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
  id: string
  role: 'user' | 'assistant'
  content: string
  agentName?: string
  questionPick?: { code: string; id: string; title: string }
  knowledge?: MessengerKnowledge | null
  stale?: boolean
  guidance?: TutorGuidanceResult
}

const props = defineProps<{
  context: TrialCoachContext
}>()

const messageApi = useMessage()
const auth = useAuthStore()
const guidance = new TutorGuidanceSession()
const selectedMode = ref<TutorMode | 'auto'>('auto')
const recommendation = ref<TutorRecommendation | null>(null)
const recommendationError = ref('')
const guidanceResult = ref<TutorGuidanceResult | null>(null)
const retryAvailable = ref(false)
const acknowledgementPending = ref(false)
const displayConfirmed = ref(false)
const helpModes: Array<{ mode: TutorMode; label: string }> = [
  { mode: 'error_explanation', label: '报错解释' },
  { mode: 'thought_check', label: '思路检查' },
  { mode: 'next_step', label: '只提示下一步' },
  { mode: 'local_pseudocode', label: '局部伪代码' },
]
const helpModeRequests: Record<TutorMode | 'auto', string> = {
  auto: '请根据我当前的情况，选择合适的方式帮助我。',
  error_explanation: '请帮我解释报错原因。',
  thought_check: '请帮我检查解题思路。',
  next_step: '请只提示我下一步该做什么。',
  local_pseudocode: '请用局部伪代码帮我梳理这一步。',
}
let planTimer: ReturnType<typeof setTimeout> | undefined
let planSequence = 0
let legacySequence = 0

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

const dialogOpen = ref(false)
const loading = ref(false)
const contextLoading = ref(false)
const contextLoaded = ref(false)
const inputText = ref('')
const messages = ref<ChatMessage[]>([])
const messagesEl = ref<HTMLElement | null>(null)
const activeIntent = ref<TrialCoachIntent>('custom')
const hintLevel = ref(2)

const dialogWidth = ref(DEFAULT_DIALOG_WIDTH)
const dialogHeight = ref(DEFAULT_DIALOG_HEIGHT)
const resizing = ref(false)
const resizeStart = { x: 0, y: 0, width: 0, height: 0 }

const posX = ref(0)
const posY = ref(0)
const viewportWidth = ref(window.innerWidth)
const viewportHeight = ref(window.innerHeight)
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
  const panelX = Math.max(MARGIN, Math.min(posX.value + BALL_SIZE - width, viewportWidth.value - width - MARGIN))
  const below = posY.value + BALL_SIZE + DIALOG_GAP
  const preferredY = below + height <= viewportHeight.value - MARGIN ? below : posY.value - DIALOG_GAP - height
  const panelY = Math.max(MARGIN, Math.min(preferredY, viewportHeight.value - height - MARGIN))

  return {
    width: `${width}px`,
    height: `${height}px`,
    left: `${panelX - posX.value}px`,
    top: `${panelY - posY.value}px`,
  }
})

const runStatusLabel = computed(() => {
  if (!props.context.caseResults.length) return '尚未运行测试'
  if (props.context.allPassed) return '全部通过'
  const passed = props.context.caseResults.filter((item) => item.passed).length
  return `${passed}/${props.context.caseResults.length} 通过`
})

const shortcuts: Array<{ intent: TrialCoachIntent; label: string }> = [
  { intent: 'error_diagnosis', label: '询问报错原因' },
  { intent: 'code_quality', label: '分析代码质量' },
  { intent: 'optimization', label: '提出优化建议' },
]

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

function buildPayload(intent: TrialCoachIntent, userQuestion: string) {
  const failedCases = props.context.failedCases ?? []
  const failedCase = failedCases[0]
  const answerStatus: TrialCoachPayload['answerStatus'] = !props.context.caseResults.length
    ? 'not_run'
    : props.context.allPassed
      ? 'correct'
      : failedCase
        ? 'wrong'
        : 'partial'

  return {
    intent,
    exerciseId: props.context.exerciseId,
    questionTitle: props.context.questionTitle,
    questionPrompt: props.context.questionPrompt,
    topic: props.context.topic,
    constraints: props.context.constraints,
    code: props.context.code,
    stderr: props.context.stderr,
    stdout: props.context.stdout,
    expectedOutput: props.context.expectedOutput,
    failedCases,
    caseResults: props.context.caseResults,
    allPassed: props.context.allPassed,
    answerStatus,
    userQuestion,
    hintLevel: hintLevel.value,
    conversationHistory: messages.value
      .filter((item) => !item.stale && item.content.trim())
      .slice(-8)
      .map((item) => ({ role: item.role, content: item.content })),
  }
}

function buildLocalIntro() {
  const status = runStatusLabel.value
  const intro = `${XIAO_E_PERSONA_INTRO} 当前题目「${props.context.questionTitle}」，运行状态：${status}。`
  const stderr = props.context.stderr?.trim()
  const failed = props.context.failedCases?.length ?? 0
  if (stderr) {
    return `${intro}\n我看到编辑器里有报错信息，你可以点「询问报错原因」或直接描述卡在哪一步。`
  }
  if (failed > 0) {
    return `${intro}\n有 ${failed} 个用例未通过，我会结合你当前的代码和输出帮你定位问题。`
  }
  if (props.context.allPassed && props.context.caseResults.length) {
    return `${intro}\n这题已经跑通了，如需优化或检查代码质量，可以用上方快捷按钮。`
  }
  return `${intro}\n先把核心逻辑写完整并运行测试，我会根据最新代码和运行结果来回答。`
}

async function loadPracticeContext() {
  if (contextLoading.value || contextLoaded.value) return
  contextLoading.value = true
  try {
    pushMessage('assistant', buildLocalIntro(), '小E')
    contextLoaded.value = true
  } finally {
    contextLoading.value = false
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

async function sendQuestion(question: string, intent: TrialCoachIntent = activeIntent.value) {
  const text = question.trim()
  if (!text || loading.value) return

  activeIntent.value = intent
  loading.value = true
  const sequence = ++legacySequence
  const payloadSnapshot = buildPayload(intent, text)
  pushMessage('user', text)
  inputText.value = ''
  await scrollToBottom()

  try {
    const result: TrialCoachResult = await trialCoach(payloadSnapshot)
    if (sequence !== legacySequence) return
    if (typeof result.hintLevel === 'number' && result.hintLevel >= 1 && result.hintLevel <= 4) {
      hintLevel.value = result.hintLevel
    }
    const knowledge = trimTrialCoachKnowledge(result.knowledge ?? null, {
      topic: payloadSnapshot.topic,
      stderr: payloadSnapshot.stderr,
      failedCases: payloadSnapshot.failedCases,
      answerStatus: payloadSnapshot.answerStatus,
    })
    pushMessage('assistant', xiaoECleanProse(result.response), result.agentName, undefined, knowledge)
  } catch (error) {
    if (sequence !== legacySequence) return
    const msg = error instanceof Error ? error.message : 'AI 辅导请求失败'
    pushMessage('assistant', msg.includes('404') ? '辅导服务未就绪，请确认后端已重启。' : msg)
  } finally {
    if (sequence === legacySequence) loading.value = false
    await scrollToBottom()
  }
}

function guidanceContext() {
  return {
    exerciseId: props.context.exerciseId,
    trialQuestionId: props.context.trialQuestionId,
    questionTitle: props.context.questionTitle,
    topic: props.context.topic,
    questionPrompt: props.context.questionPrompt,
    code: props.context.code,
    stderr: props.context.stderr,
    userQuestion: inputText.value,
    thought: selectedMode.value === 'thought_check' ? inputText.value : undefined,
    previousRequestId: guidance.previousRequestId,
  }
}

async function refreshRecommendation() {
  const sequence = ++planSequence
  recommendation.value = null
  recommendationError.value = ''
  if (!dialogOpen.value || !auth.isAuthenticated) return
  try {
    const result = await planTutorGuidance(guidanceContext())
    if (sequence === planSequence) recommendation.value = result.recommendation
  } catch {
    if (sequence === planSequence) recommendationError.value = '暂时无法推荐模式，你仍可手动选择。'
  }
}

function queueRecommendation() {
  ++planSequence
  clearTimeout(planTimer)
  planTimer = setTimeout(() => void refreshRecommendation(), 300)
}

async function confirmGuidance() {
  const result = guidance.latest
  const epoch = guidance.epoch
  if (!result || result.needsContext || guidance.previousRequestId === result.requestId ||
      document.visibilityState !== 'visible' || !dialogOpen.value || acknowledgementPending.value) return
  acknowledgementPending.value = true
  try {
    const receipt = await acknowledgeTutorGuidance(result.requestId)
    if (receipt.displayed && guidance.confirm(epoch, result.requestId)) {
      displayConfirmed.value = true
      queueRecommendation()
    }
  } catch {
    if (epoch === guidance.epoch) messageApi.warning('提示已显示，确认失败；可点击“确认展示”重试。')
  } finally {
    if (epoch === guidance.epoch) acknowledgementPending.value = false
  }
}

async function sendGuidance(furtherHelp = false, retry = false) {
  if (loading.value) return
  const currentContext = guidanceContext()
  if (furtherHelp && !currentContext.userQuestion.trim()) {
    currentContext.userQuestion = guidance.latestPayload?.userQuestion || ''
    currentContext.thought = guidance.latestPayload?.thought
  }
  const request = retry ? guidance.retry() : guidance.start({
    ...currentContext, requestId: crypto.randomUUID(), mode: selectedMode.value, furtherHelp,
  })
  if (!request) return
  loading.value = true
  retryAvailable.value = false
  if (!retry) {
    const requestText = helpModeRequests[selectedMode.value]
    const studentText = inputText.value.trim()
    pushMessage('user', furtherHelp ? '我仍卡在这一步，请再具体一点。' : studentText ? `${requestText}\n${studentText}` : requestText)
    inputText.value = ''
  }
  try {
    const result = await askTutorGuidance(request.payload)
    if (!guidance.accept(request.epoch, result)) return
    ++planSequence
    guidanceResult.value = result
    displayConfirmed.value = false
    recommendation.value = result.recommendation
    pushMessage('assistant', `${result.stageLabel} · ${result.modeLabel}\n\n${result.response}\n\n下一步：${result.nextAction}`, '小E')
    messages.value[messages.value.length - 1]!.guidance = result
    await scrollToBottom()
    await confirmGuidance()
  } catch (error) {
    if (request.epoch === guidance.epoch) {
      retryAvailable.value = true
      if (error instanceof Error && error.message.includes('课程依据已更新')) {
        guidance.reset()
        guidanceResult.value = null
        displayConfirmed.value = false
        retryAvailable.value = false
        loading.value = false
      }
      messageApi.error(error instanceof Error ? error.message : '辅导请求失败，可重试原请求；不会增加提示层级。')
    }
  } finally {
    if (request.epoch === guidance.epoch) loading.value = false
  }
}

function chooseHelpMode(mode: TutorMode | 'auto') {
  if (loading.value) return
  selectedMode.value = mode
  void sendGuidance()
}

function invalidateGuidance(msg: ChatMessage) {
  msg.content = '这条辅导的课程依据暂时无法核验，请重新提问。'
  if (msg.guidance) msg.guidance = { ...msg.guidance, citations: [], evidenceStatus: 'unavailable' }
  if (guidance.latest?.requestId === msg.guidance?.requestId) {
    guidance.reset()
    guidanceResult.value = null
    displayConfirmed.value = false
    retryAvailable.value = false
    loading.value = false
  }
}

async function revalidateGuidance() {
  if (!dialogOpen.value || document.visibilityState !== 'visible') return
  const epoch = guidance.epoch
  for (const msg of messages.value.filter(item => item.guidance && !item.stale)) {
    try {
      const result = await readTutorGuidance(msg.guidance!.requestId)
      if (epoch !== guidance.epoch || !messages.value.includes(msg)) return
      msg.guidance = result
      msg.content = `${result.stageLabel} · ${result.modeLabel}\n\n${result.response}\n\n下一步：${result.nextAction}`
    } catch {
      if (epoch === guidance.epoch && messages.value.includes(msg)) invalidateGuidance(msg)
    }
  }
}

function resetGuidance(clearMessages: boolean) {
  guidance.reset()
  ++legacySequence
  loading.value = false
  guidanceResult.value = null
  retryAvailable.value = false
  acknowledgementPending.value = false
  displayConfirmed.value = false
  selectedMode.value = 'auto'
  if (clearMessages) {
    messages.value = []
    inputText.value = ''
    contextLoaded.value = false
    if (dialogOpen.value && auth.isAuthenticated) void loadPracticeContext()
  } else {
    messages.value.forEach((item) => { item.stale = true })
  }
  queueRecommendation()
}

function onShortcut(intent: TrialCoachIntent, label: string) {
  void sendQuestion(label, intent)
}

function onSend() {
  void sendGuidance()
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

watch(dialogOpen, (open) => {
  if (open && !messages.value.length) {
    void loadPracticeContext()
  }
  queueRecommendation()
  if (open) void confirmGuidance()
  if (open) void revalidateGuidance()
})

watch([
  () => auth.profile?.id,
  () => auth.isAuthenticated,
  () => props.context.exerciseId,
  () => props.context.trialQuestionId,
  () => props.context.questionPrompt,
], () => resetGuidance(true))
watch(() => props.context.code, () => resetGuidance(false), { flush: 'sync' })
watch(() => [props.context.stderr, inputText.value], queueRecommendation)

onMounted(() => {
  syncDefaultPosition()
  const size = clampDialogSize(DEFAULT_DIALOG_WIDTH, DEFAULT_DIALOG_HEIGHT)
  dialogWidth.value = size.width
  dialogHeight.value = size.height
  window.addEventListener('resize', onWindowResize)
  document.addEventListener('visibilitychange', confirmGuidance)
  document.addEventListener('visibilitychange', revalidateGuidance)
})

onBeforeUnmount(() => {
  guidance.reset()
  ++legacySequence
  ++planSequence
  clearTimeout(planTimer)
  document.removeEventListener('visibilitychange', confirmGuidance)
  document.removeEventListener('visibilitychange', revalidateGuidance)
  dragging.value = false
  resizing.value = false
  window.removeEventListener('resize', onWindowResize)
  window.removeEventListener('pointermove', onResizeMove)
  window.removeEventListener('pointerup', onResizeUp)
})
</script>

<template>
  <Teleport to="body">
    <div class="trial-ai-float" :style="floatStyle">
      <Transition name="trial-ai-dialog">
        <div
          v-if="dialogOpen"
          role="dialog"
          aria-label="小E编程辅导窗口"
          class="trial-ai-float__dialog"
          :class="{ 'is-resizing': resizing }"
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

          <div class="trial-ai-float__hint-row">
            <span>帮助模式</span>
            <button
              type="button"
              class="trial-ai-float__chip"
              :class="{ 'is-active': selectedMode === 'auto' }"
              :disabled="loading"
              @click="chooseHelpMode('auto')"
            >自动推荐</button>
            <button
              v-for="opt in helpModes"
              :key="opt.mode"
              type="button"
              class="trial-ai-float__chip"
              :class="{ 'is-active': selectedMode === opt.mode }"
              :disabled="loading"
              @click="chooseHelpMode(opt.mode)"
            >
              {{ opt.label }}
            </button>
          </div>
          <div class="trial-ai-float__guidance" aria-live="polite">
            <p v-if="recommendation">建议：{{ recommendation.label }}。{{ recommendation.reason }}</p>
            <p v-else-if="recommendationError">{{ recommendationError }}</p>
            <p v-else>可以手动选择帮助模式。</p>
            <small>先观察，再验证，最后展开局部步骤。修改代码后重新判断；运行信息仅作为自测参考。</small>
            <div v-if="guidanceResult?.canDeepen || (guidanceResult && !guidanceResult.needsContext && !displayConfirmed) || retryAvailable" class="trial-ai-float__guidance-actions">
              <button v-if="guidanceResult?.canDeepen" type="button" class="trial-ai-float__chip"
                :disabled="loading || !displayConfirmed" @click="sendGuidance(true)">再具体一点</button>
              <button v-if="guidanceResult && !guidanceResult.needsContext && !displayConfirmed" type="button"
                class="trial-ai-float__chip" :disabled="loading || acknowledgementPending" @click="confirmGuidance">确认展示</button>
              <button v-if="retryAvailable" type="button" class="trial-ai-float__chip"
                :disabled="loading" @click="sendGuidance(false, true)">重试原请求</button>
            </div>
          </div>
          <details class="trial-ai-float__other-help">
            <summary>其他辅导</summary>
            <div class="trial-ai-float__shortcuts">
            <button
              v-for="item in shortcuts"
              :key="item.intent"
              type="button"
              class="trial-ai-float__chip"
              :disabled="loading"
              @click="onShortcut(item.intent, item.label)"
            >
              {{ item.label }}
            </button>
            </div>
          </details>

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
                <small v-if="msg.stale">对应修改前的代码，仅供回顾</small>
                <MarkdownRenderer :content="msg.content" />
                <TutorEvidenceCard v-if="!msg.stale && msg.guidance?.citations?.length"
                  :request-id="msg.guidance.requestId" :citations="msg.guidance.citations"
                  @invalid="invalidateGuidance(msg)" />
                <small v-else-if="msg.guidance && !msg.guidance.needsContext">通用编程提示 · 未采用可核验的课程引用</small>
                <MessengerKnowledgeCard v-if="msg.knowledge" :knowledge="msg.knowledge" />
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
            <div class="trial-ai-float__composer-actions">
            <n-button type="primary" :loading="loading" :disabled="!inputText.trim()" @click="onSend">
              <template #icon><n-icon :component="SendOutline" /></template>
              发送
            </n-button>
            <n-button :disabled="loading || !inputText.trim()" @click="sendQuestion(inputText, 'custom')">自由问答</n-button>
            </div>
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
        :aria-expanded="dialogOpen"
        @click="(event: MouseEvent) => { if (event.detail === 0) dialogOpen = !dialogOpen }"
        @pointerdown="onPointerDown"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
        @pointercancel="onPointerUp"
      >
        <span class="trial-ai-float__ball-glow" aria-hidden="true" />
        <n-icon :component="ChatbubbleEllipsesOutline" />
      </button>
    </div>
  </Teleport>
</template>

<style scoped>
.trial-ai-float__guidance {
  padding: 0.5rem 1rem;
  font-size: 0.8rem;
  overflow-wrap: anywhere;
}
.trial-ai-float__guidance p { margin: 0 0 0.35rem; }
.trial-ai-float__guidance small { opacity: 0.8; }
.trial-ai-float__guidance-actions, .trial-ai-float__composer-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 0.4rem;
}
.trial-ai-float__composer-actions { justify-content: flex-end; }
.trial-ai-float__other-help { padding: 0.35rem 1rem; font-size: 0.8rem; }
.trial-ai-float__other-help summary { cursor: pointer; }
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
@media (prefers-reduced-motion: reduce) {
  .trial-ai-float__ball { animation: none !important; }
  .trial-ai-dialog-enter-active, .trial-ai-dialog-leave-active { transition: none; }
}
</style>
