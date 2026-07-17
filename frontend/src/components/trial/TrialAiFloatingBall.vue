<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { NButton, NIcon, NInput, NSpin } from 'naive-ui'
import { ChatbubbleEllipsesOutline, CloseOutline, SendOutline } from '@vicons/ionicons5'
import { trialCoach, type TrialCoachIntent, type TrialCoachPayload, type TrialCoachResult } from '../../api/agentService'

export type TrialCoachContext = {
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
  id: string
  role: 'user' | 'assistant'
  content: string
  agentName?: string
}

const props = defineProps<{
  context: TrialCoachContext
}>()

const BALL_SIZE = 52
const MARGIN = 20
const DIALOG_GAP = 14
const DEFAULT_DIALOG_WIDTH = 500
const DEFAULT_DIALOG_HEIGHT = 600
const MIN_DIALOG_WIDTH = 360
const MIN_DIALOG_HEIGHT = 420

const dialogOpen = ref(false)
const loading = ref(false)
const inputText = ref('')
const messages = ref<ChatMessage[]>([])
const messagesEl = ref<HTMLElement | null>(null)
const activeIntent = ref<TrialCoachIntent>('custom')

const dialogWidth = ref(DEFAULT_DIALOG_WIDTH)
const dialogHeight = ref(DEFAULT_DIALOG_HEIGHT)
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

const maxDialogWidth = computed(() => window.innerWidth - MARGIN * 2)
const maxDialogHeight = computed(() => window.innerHeight - MARGIN * 2)

const dialogStyle = computed(() => {
  const width = Math.min(dialogWidth.value, maxDialogWidth.value)
  const height = Math.min(dialogHeight.value, maxDialogHeight.value)
  const preferAbove = posY.value > window.innerHeight * 0.42
  const alignLeft = posX.value + BALL_SIZE < width + MARGIN

  return {
    width: `${width}px`,
    height: `${height}px`,
    ...(alignLeft ? { left: '0', right: 'auto' } : { right: '0', left: 'auto' }),
    ...(preferAbove
      ? { bottom: `calc(100% + ${DIALOG_GAP}px)`, top: 'auto' }
      : { top: `calc(100% + ${DIALOG_GAP}px)`, bottom: 'auto' }),
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
    conversationHistory: messages.value
      .filter((item) => item.content.trim())
      .slice(-8)
      .map((item) => ({ role: item.role, content: item.content })),
  }
}

function pushMessage(role: ChatMessage['role'], content: string, agentName?: string) {
  messages.value.push({
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    role,
    content,
    agentName,
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
  pushMessage('user', text)
  inputText.value = ''
  await scrollToBottom()

  try {
    const result: TrialCoachResult = await trialCoach(buildPayload(intent, text))
    pushMessage('assistant', result.response, result.agentName)
  } catch (error) {
    const msg = error instanceof Error ? error.message : 'AI 辅导请求失败'
    pushMessage('assistant', msg.includes('404') ? '辅导服务未就绪，请确认后端已重启。' : msg)
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

function onShortcut(intent: TrialCoachIntent, label: string) {
  void sendQuestion(label, intent)
}

function onSend() {
  void sendQuestion(inputText.value, 'custom')
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
    pushMessage(
      'assistant',
      `你好，我是小E。当前题目是「${props.context.questionTitle}」，状态：${runStatusLabel.value}。有什么疑惑都可以问我。`,
      '小E',
    )
    void scrollToBottom()
  }
})

onMounted(() => {
  syncDefaultPosition()
  const size = clampDialogSize(DEFAULT_DIALOG_WIDTH, DEFAULT_DIALOG_HEIGHT)
  dialogWidth.value = size.width
  dialogHeight.value = size.height
  window.addEventListener('resize', onWindowResize)
})

onBeforeUnmount(() => {
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
              <p>{{ msg.content }}</p>
            </article>
            <div v-if="loading" class="trial-ai-float__typing">
              <n-spin size="small" />
              <span>小E 正在思考…</span>
            </div>
          </div>

          <footer class="trial-ai-float__composer">
            <n-input
              v-model:value="inputText"
              type="textarea"
              placeholder="请输入你的疑惑，小E会帮您解决:"
              :autosize="{ minRows: 2, maxRows: 5 }"
              :disabled="loading"
              @keydown="onInputKeydown"
            />
            <n-button type="primary" :loading="loading" :disabled="!inputText.trim()" @click="onSend">
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
      >
        <span class="trial-ai-float__ball-glow" aria-hidden="true" />
        <n-icon :component="ChatbubbleEllipsesOutline" />
      </button>
    </div>
  </Teleport>
</template>

<style scoped>
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
