<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NIcon, NModal, NTag, useMessage } from 'naive-ui'
import type { TrialAttemptRecord } from '../../utils/trialMistakeLog'
import PlexCodeEditor from './PlexCodeEditor.vue'
import {
  ArrowBackOutline,
  ChatbubbleEllipsesOutline,
  CheckmarkCircleOutline,
  CloseCircleOutline,
  CloudUploadOutline,
  DocumentTextOutline,
  PlayOutline,
  RefreshOutline,
  ShuffleOutline,
  TimeOutline,
} from '@vicons/ionicons5'
import type { PythonTrialQuestion } from '../../data/pythonTrialQuestions'
import { useAuthStore } from '../../stores/auth'
import { useNotificationStore } from '../../stores/notifications'
import { getTrialAttemptHistory, recordTrialRun, resolveAttemptScore, resolveAttemptVerdict } from '../../utils/trialMistakeLog'
import { submitTrialCodeAnswer } from '../../api/studentAssignments'
import { advanceDailyQuest } from '../../api/studentOverview'
import { requestTrialFeedback, type StudentDiagnoseResult } from '../../api/agentService'
import { submitCode } from '../../api/codeRunner'
import { concisePythonError, normalizePythonSource } from '../../utils/pythonSourceNormalization'
import PlexDiagnosisPanel from '../agent/PlexDiagnosisPanel.vue'
import TrialCommentPanel from './TrialCommentPanel.vue'
import TrialAiFloatingBall from './TrialAiFloatingBall.vue'
import QuestionSlotGems from './QuestionSlotGems.vue'
import { xiaoESubmitCheckSummary, xiaoEThinkingMessage, xiaoETimeoutMessage } from '../../utils/xiaoEPersona'
// recordTrialRun 会写入 localStorage 并异步同步 POST /student/code-trial/runs

const props = withDefaults(
  defineProps<{
    question: PythonTrialQuestion
    embedded?: boolean
    backLabel?: string
    trialQuestionId?: number
    slotIds?: string[]
    activeSlot?: number
  }>(),
  {
    embedded: false,
    backLabel: '返回星轨',
    trialQuestionId: undefined,
    slotIds: () => [],
    activeSlot: 0,
  },
)

const emit = defineEmits<{
  back: []
  passed: []
  changeQuestion: []
  selectSlot: [slot: number]
}>()

const router = useRouter()
const message = useMessage()
const auth = useAuthStore()
const notifications = useNotificationStore()

const EMPTY_STARTER = ''

const code = ref(EMPTY_STARTER)
const running = ref(false)
const submittingManual = ref(false)
const leftPanel = ref<'problem' | 'history' | 'comments'>('problem')
const pyodideReady = ref(false)
const pyodideLoading = ref(false)
const pyodideError = ref('')
const isMounted = ref(true)
let aborted = false

type CaseResult = {
  id: string
  label: string
  expected: string
  actual: string
  passed: boolean
  error?: string
  time?: string
  memory?: number
}

const caseResults = ref<CaseResult[]>([])
const executionBackend = ref<'api' | 'pyodide' | null>(null)
const agentLoading = ref(false)
const agentResult = ref<StudentDiagnoseResult | null>(null)
const agentError = ref('')
const submitAgentTrace = ref('')
let agentRequestId = 0
const passedCount = computed(() => caseResults.value.filter((item) => item.passed).length)
const allPassed = computed(
  () => caseResults.value.length > 0 && passedCount.value === caseResults.value.length,
)

const answerHistory = computed(() => {
  const userId = auth.profile?.id ?? 'guest'
  return getTrialAttemptHistory(userId, props.question.id)
})

const codeModalVisible = ref(false)
const activeAttempt = ref<TrialAttemptRecord | null>(null)

function openAttemptCode(record: TrialAttemptRecord) {
  activeAttempt.value = record
  codeModalVisible.value = true
}

async function copyAttemptCode() {
  const text = activeAttempt.value?.code
  if (!text) {
    message.warning('该记录未保存代码，请重新运行后查看')
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    message.success('代码已复制')
  } catch {
    message.error('复制失败，请手动选择')
  }
}

const floatingBallContext = computed(() => ({
  exerciseId: props.question.id,
  questionTitle: props.question.title,
  questionPrompt: props.question.description,
  topic: props.question.topic,
  constraints: props.question.constraints,
  code: code.value,
  stderr: caseResults.value
    .map((item) => item.error)
    .filter(Boolean)
    .join('\n'),
  stdout: caseResults.value.find((item) => !item.passed)?.actual,
  expectedOutput: caseResults.value.find((item) => !item.passed)?.expected,
  failedCases: caseResults.value
    .filter((item) => !item.passed)
    .map((item) => ({
      label: item.label,
      expected: item.expected,
      actual: item.actual,
      error: item.error,
    })),
  caseResults: caseResults.value.map((item) => ({ passed: item.passed })),
  allPassed: allPassed.value,
}))

let runStartedAt = 0

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let pyodideInstance: any = null

declare global {
  interface Window {
    loadPyodide?: (config: { indexURL: string }) => Promise<unknown>
  }
}

const PYODIDE_INDEX = 'https://cdn.jsdelivr.net/pyodide/v0.26.4/full/'

async function ensurePyodide() {
  if (pyodideInstance) return pyodideInstance
  pyodideLoading.value = true
  pyodideError.value = ''
  try {
    if (!window.loadPyodide) {
      await new Promise<void>((resolve, reject) => {
        const script = document.createElement('script')
        script.src = `${PYODIDE_INDEX}pyodide.js`
        script.async = true
        script.onload = () => resolve()
        script.onerror = () => reject(new Error('Pyodide 脚本加载失败'))
        document.head.appendChild(script)
      })
    }
    if (!window.loadPyodide) throw new Error('Pyodide 不可用')
    pyodideInstance = await window.loadPyodide({ indexURL: PYODIDE_INDEX })
    pyodideReady.value = true
    return pyodideInstance
  } catch (error) {
    pyodideError.value = error instanceof Error ? error.message : 'Python 运行环境加载失败'
    throw error
  } finally {
    pyodideLoading.value = false
  }
}

function normalizeOutput(value: unknown) {
  return String(value ?? '')
    .replace(/\r\n/g, '\n')
    .trim()
}

async function runSingleCase(testCase: PythonTrialQuestion['testCases'][number], source: string) {
  const py = await ensurePyodide()
  const setup = testCase.setup ? `${testCase.setup}\n` : ''

  await py.runPythonAsync(`
import sys
from io import StringIO
sys.stdout = StringIO()
`)

  try {
    if (props.question.runMode === 'expression' && testCase.invoke) {
      await py.runPythonAsync(`${setup}\n${source}`)
      const actual = normalizeOutput(await py.runPythonAsync(testCase.invoke))
      return { actual, error: undefined }
    }

    await py.runPythonAsync(`${setup}\n${source}`)
    const actual = normalizeOutput(await py.runPythonAsync('sys.stdout.getvalue()'))
    return { actual, error: undefined }
  } catch (error) {
    return {
      actual: '',
      error: concisePythonError(error instanceof Error ? error.message : '运行出错'),
    }
  }
}

function applyRunResults(results: CaseResult[], backend: 'api' | 'pyodide') {
  if (aborted || !isMounted.value) return
  caseResults.value = results
  executionBackend.value = backend
  const userId = auth.profile?.id ?? 'guest'
  const allPass = results.every((item) => item.passed)
  const durationMs = runStartedAt > 0 ? Date.now() - runStartedAt : 0
  const snapshots = results.map((item) => ({ label: item.label, passed: item.passed, error: item.error }))

  recordTrialRun(userId, props.question, snapshots, durationMs, code.value)

  if (props.trialQuestionId) {
    void submitTrialCodeAnswer(props.trialQuestionId, code.value)
      .then((result) => {
        if (aborted || !isMounted.value) return
        if (allPass) {
          message.success('编程题已提交并通过')
          emit('passed')
        } else {
          message.warning('代码已提交，但未通过全部测试')
        }
        if (result.trial_complete) {
          message.success(`试炼已完成，得分 ${result.trial_complete.participation.score}`)
        }
      })
      .catch((error) => {
        if (!aborted && isMounted.value) {
          message.error(error instanceof Error ? error.message : '试炼提交失败')
        }
      })
    return
  }

  if (results.every((item) => item.passed)) {
    message.success('全部测试通过！')
    emit('passed')
    const uid = auth.profile?.id
    if (uid && auth.profile?.role === 'student') {
      notifications.push(uid, 'first_coding_solved')
      advanceDailyQuest('trial-challenge').catch(() => undefined)
    }
  } else {
    message.warning(`${results.filter((item) => item.passed).length}/${results.length} 个测试通过`)
  }
}

async function runViaApi(source: string): Promise<CaseResult[]> {
  const payload = await submitCode({
    language: 'python',
    code: source,
    run_mode: props.question.runMode,
    test_cases: props.question.testCases.map((tc) => ({
      id: tc.id,
      label: tc.label,
      input: '',
      expected: tc.expected,
      setup: tc.setup,
      invoke: tc.invoke,
    })),
  })
  return payload.results.map((item) => ({
    id: item.case_id || item.label,
    label: item.label,
    expected: item.expected,
    actual: item.actual,
    passed: item.passed,
    error: concisePythonError(item.error),
    time: item.time,
    memory: item.memory,
  }))
}

async function runViaPyodide(source: string): Promise<CaseResult[]> {
  const results: CaseResult[] = []
  for (const testCase of props.question.testCases) {
    const { actual, error } = await runSingleCase(testCase, source)
    results.push({
      id: testCase.id,
      label: testCase.label,
      expected: testCase.expected,
      actual: error ? '' : actual,
      passed: !error && normalizeOutput(actual) === normalizeOutput(testCase.expected),
      error,
    })
  }
  return results
}

async function onRun() {
  if (aborted || !isMounted.value) return
  running.value = true
  runStartedAt = Date.now()
  caseResults.value = []
  executionBackend.value = null
  try {
    const normalized = normalizePythonSource(code.value)
    const source = normalized.code
    if (normalized.replacements > 0) {
      code.value = source
      message.info(`已自动将 ${normalized.replacements} 个全角代码符号转换为英文半角符号`)
    }
    try {
      const results = await runViaApi(source)
      if (aborted || !isMounted.value) return
      applyRunResults(results, 'api')
      return
    } catch {
      /* fall back to Pyodide */
    }
    const results = await runViaPyodide(source)
    if (aborted || !isMounted.value) return
    applyRunResults(results, 'pyodide')
  } catch {
    if (!aborted && isMounted.value) {
      message.error(pyodideError.value || '运行失败，请检查网络后重试')
    }
  } finally {
    if (isMounted.value) running.value = false
  }
}

async function onManualSubmit() {
  if (!props.trialQuestionId || submittingManual.value) return
  submittingManual.value = true
  try {
    const result = await submitTrialCodeAnswer(props.trialQuestionId, code.value)
    if (result.agent_trace?.items?.length) {
      submitAgentTrace.value = xiaoESubmitCheckSummary(
        result.agent_trace.items
          .slice(0, 2)
          .map((row) => row.summary)
          .join(' · '),
      )
    }
    if (result.trial_complete) {
      message.success(`代码已提交，试炼得分 ${result.trial_complete.participation.score}`)
    } else {
      message.success('代码已提交')
    }
    emit('passed')
  } catch {
    message.error('提交失败，请重试')
  } finally {
    submittingManual.value = false
  }
}

function onReset() {
  code.value = EMPTY_STARTER
  caseResults.value = []
  agentResult.value = null
  agentError.value = ''
  submitAgentTrace.value = ''
}

function goBack() {
  if (running.value || pyodideLoading.value) {
    message.info('正在运行或加载，请稍候…')
    return
  }
  if (props.embedded) {
    emit('back')
    return
  }
  if (window.history.length > 1) {
    void router.back()
    return
  }
  void router.push('/student/star-path')
}

onBeforeUnmount(() => {
  aborted = true
  isMounted.value = false
  running.value = false
})

const showSlotNav = computed(() => props.slotIds.length > 1)

watch(
  () => props.question.id,
  () => {
    code.value = EMPTY_STARTER
    caseResults.value = []
    agentResult.value = null
    agentError.value = ''
    leftPanel.value = 'problem'
  },
)

async function fetchAiFeedback() {
  if (!code.value.trim() || agentLoading.value) return
  const requestId = ++agentRequestId
  agentLoading.value = true
  agentError.value = ''
  agentResult.value = null

  const failedCase = caseResults.value.find((item) => !item.passed)
  const attemptCount = answerHistory.value.length + 1

  try {
    const result = await requestTrialFeedback({
      exerciseId: props.question.id,
      code: code.value,
      stderr: failedCase?.error || caseResults.value.map((item) => item.error).filter(Boolean).join('\n'),
      stdout: failedCase?.actual,
      expectedOutput: failedCase?.expected,
      knowledgePoints: [props.question.topic, ...props.question.tags],
      attemptCount,
      answerStatus: allPassed.value ? 'correct' : failedCase ? 'wrong' : 'partial',
      questionTitle: props.question.title,
      questionPrompt: props.question.description,
    })
    if (requestId !== agentRequestId || !isMounted.value) return
    agentResult.value = result
  } catch (error) {
    if (requestId !== agentRequestId || !isMounted.value) return
    const msg = error instanceof Error ? error.message : 'AI 反馈获取失败'
    agentError.value = msg.includes('timeout') ? xiaoETimeoutMessage() : msg
  } finally {
    if (requestId === agentRequestId && isMounted.value) {
      agentLoading.value = false
    }
  }
}
function formatDuration(ms: number) {
  if (ms < 1000) return `${ms}ms`
  const sec = Math.round(ms / 1000)
  if (sec < 60) return `${sec}s`
  const min = Math.floor(sec / 60)
  const rest = sec % 60
  return `${min}m ${rest}s`
}
</script>

<template>
  <div class="py-workspace">
    <header class="py-workspace__bar">
      <button type="button" class="py-workspace__back" @click="goBack">
        <n-icon :component="ArrowBackOutline" />
        {{ embedded ? backLabel : '返回星轨学习' }}
      </button>
      <div class="py-workspace__meta">
        <span class="py-workspace__topic">{{ question.topic }}</span>
        <span class="py-workspace__diff" :data-level="question.difficulty">{{ question.difficulty }}</span>
        <span class="py-workspace__xp">+{{ question.rewardXp }} XP</span>
      </div>
      <QuestionSlotGems
        v-if="showSlotNav"
        class="py-workspace__slots py-workspace__slots--inline"
        :slots="slotIds"
        :active-index="activeSlot"
        @select="emit('selectSlot', $event)"
      />
      <div class="py-workspace__actions">
        <n-button v-if="embedded" quaternary :disabled="running" @click="emit('changeQuestion')">
          <template #icon><n-icon :component="ShuffleOutline" /></template>
          换一题
        </n-button>
        <n-button
          v-if="embedded && props.trialQuestionId"
          type="success"
          :loading="submittingManual"
          :disabled="running"
          @click="onManualSubmit"
        >
          <template #icon><n-icon :component="CloudUploadOutline" /></template>
          提交代码
        </n-button>
      </div>
      <p v-if="submitAgentTrace" class="py-workspace__submit-trace">{{ submitAgentTrace }}</p>
    </header>

    <div class="py-workspace__body">
      <aside class="py-workspace__panel py-workspace__panel--side">
        <nav class="py-side-panel__tabs" aria-label="题目、记录与讨论">
          <button
            type="button"
            class="py-side-panel__tab"
            :class="{ 'is-active': leftPanel === 'problem' }"
            @click="leftPanel = 'problem'"
          >
            <n-icon :component="DocumentTextOutline" />
            <span>题目</span>
          </button>
          <button
            type="button"
            class="py-side-panel__tab"
            :class="{ 'is-active': leftPanel === 'history' }"
            @click="leftPanel = 'history'"
          >
            <n-icon :component="TimeOutline" />
            <span>答题记录</span>
            <em v-if="answerHistory.length">{{ answerHistory.length }}</em>
          </button>
          <button
            type="button"
            class="py-side-panel__tab"
            :class="{ 'is-active': leftPanel === 'comments' }"
            @click="leftPanel = 'comments'"
          >
            <n-icon :component="ChatbubbleEllipsesOutline" />
            <span>讨论</span>
          </button>
        </nav>

        <div class="py-side-panel__content py-side-panel__content--fade">
          <template v-if="leftPanel === 'problem'">
            <h1 class="py-workspace__title">{{ question.title }}</h1>
            <p class="py-workspace__desc">{{ question.description }}</p>

            <section v-if="question.constraints.length" class="py-block">
              <h2>要求</h2>
              <ul>
                <li v-for="item in question.constraints" :key="item">{{ item }}</li>
              </ul>
            </section>

            <section class="py-block">
              <h2>示例</h2>
              <p v-if="!question.examples.length" class="py-block__empty">暂无示例，可直接查看下方判题用例。</p>
              <article v-for="(ex, index) in question.examples" :key="index" class="py-example">
                <div><small>输入</small><code>{{ ex.input }}</code></div>
                <div><small>输出</small><code>{{ ex.output }}</code></div>
              </article>
            </section>

            <section class="py-block">
              <h2>判题用例</h2>
              <p v-if="!question.testCases.length" class="py-block__empty">暂未提供结构化判题用例。</p>
              <div class="py-tests">
                <article v-for="tc in question.testCases" :key="tc.id" class="py-test">
                  <strong>{{ tc.label }}</strong>
                  <div v-if="tc.setup" class="py-test__row">
                    <span>前置</span>
                    <code>{{ tc.setup.replace(/\n/g, '; ') }}</code>
                  </div>
                  <div v-if="tc.invoke" class="py-test__row">
                    <span>调用</span>
                    <code>{{ tc.invoke }}</code>
                  </div>
                </article>
              </div>
            </section>

            <section class="py-block py-results">
              <header class="py-results__head">
                <h2>运行结果</h2>
                <span v-if="caseResults.length" :class="{ 'is-success': allPassed }">
                  {{ passedCount }} / {{ caseResults.length }} 通过
                </span>
              </header>

              <p v-if="!caseResults.length" class="py-results__empty">点击代码区右上角「运行测试」后，这里会显示每个测试点的实际输出与判定。</p>

              <div v-else class="py-results__list">
                <article
                  v-for="item in caseResults"
                  :key="item.id"
                  class="py-result-card"
                  :class="item.passed ? 'is-pass' : 'is-fail'"
                >
                  <header>
                    <strong>{{ item.label }}</strong>
                    <span>{{ item.passed ? '通过' : '未通过' }}</span>
                  </header>
                  <div class="py-result-card__row">
                    <small>预期输出</small>
                    <code>{{ item.expected }}</code>
                  </div>
                  <div class="py-result-card__row">
                    <small>实际输出</small>
                    <code>{{ item.error ? '无输出' : item.actual || '空' }}</code>
                  </div>
                  <p v-if="item.time || item.memory" class="py-result-card__meta">
                    <span v-if="item.time">耗时 {{ item.time }}s</span>
                    <span v-if="item.memory">内存 {{ item.memory }}KB</span>
                  </p>
                  <p v-if="item.error" class="py-result-card__error">{{ item.error }}</p>
                </article>
              </div>
            </section>

            <section class="py-ai-block" aria-label="小E 学习反馈">
              <header class="py-ai-block__head">
                <h2>小E · 学习反馈</h2>
                <n-button
                  size="small"
                  type="primary"
                  ghost
                  :loading="agentLoading"
                  :disabled="!code.trim()"
                  @click="fetchAiFeedback"
                >
                  请小E 看看
                </n-button>
              </header>
              <p v-if="!agentResult && !agentLoading && !agentError" class="py-ai-block__tip">
                运行测试后，可点击「请小E 看看」获取针对性反馈。
              </p>
              <p v-else-if="agentLoading && !agentResult" class="py-ai-block__tip">{{ xiaoEThinkingMessage('diagnosis') }}</p>
              <p v-else-if="agentError" class="py-ai-block__error">{{ agentError }}</p>
              <plex-diagnosis-panel
                v-else-if="agentResult"
                :result="agentResult"
                :loading="false"
              />
            </section>

            <p v-if="executionBackend === 'api'" class="py-workspace__ok">代码已由 PLEX 在线判题服务执行</p>
            <p v-else-if="executionBackend === 'pyodide'" class="py-workspace__ok">已通过浏览器 Pyodide 离线运行</p>
            <p v-else-if="pyodideError" class="py-workspace__warn">{{ pyodideError }}</p>
            <p v-else-if="pyodideReady" class="py-workspace__ok">浏览器离线运行环境已就绪</p>
          </template>

          <div v-else-if="leftPanel === 'history'" class="py-history__list">
            <p v-if="!answerHistory.length" class="py-history__empty">暂无提交记录，运行测试后会记录在这里。</p>
            <template v-else>
              <article
                v-for="(record, index) in answerHistory"
                :key="`${record.submittedAt}-${index}`"
                class="py-history__item py-history__item--clickable"
                role="button"
                tabindex="0"
                @click="openAttemptCode(record)"
                @keydown.enter.prevent="openAttemptCode(record)"
              >
                <div class="py-history__row">
                  <n-tag :type="record.passed ? 'success' : 'error'" size="small">
                    {{ resolveAttemptVerdict(record) }}
                  </n-tag>
                  <span class="py-history__score">
                    {{ resolveAttemptScore(record).passed }}/{{ resolveAttemptScore(record).total }}
                  </span>
                  <span class="py-history__time">
                    {{ new Date(record.submittedAt).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) }}
                  </span>
                  <span class="py-history__duration">用时 {{ formatDuration(record.durationMs) }}</span>
                </div>
                <div v-if="!record.passed && record.errorReason" class="py-history__cases">
                  错误原因：{{ record.errorReason }}
                </div>
                <div v-else-if="!record.passed && record.failedCaseLabels.length" class="py-history__cases">
                  未通过：{{ record.failedCaseLabels.join('、') }}
                </div>
                <p class="py-history__hint">点击查看当时代码</p>
              </article>
            </template>
          </div>

          <trial-comment-panel v-else-if="leftPanel === 'comments'" :key="question.id" :question-ref="question.id" />
        </div>
      </aside>

      <section class="py-workspace__panel py-workspace__panel--editor">
        <header class="py-editor__head">
          <h2>代码编辑区</h2>
          <div class="py-editor__head-actions">
            <span class="py-editor__filename">main.py</span>
            <n-button quaternary size="small" :disabled="running" @click="onReset">
              <template #icon><n-icon :component="RefreshOutline" /></template>
              重置代码
            </n-button>
            <n-button type="primary" size="small" :loading="running || pyodideLoading" @click="onRun">
              <template #icon><n-icon :component="PlayOutline" /></template>
              运行测试
            </n-button>
          </div>
        </header>
        <div class="py-editor__wrap">
          <plex-code-editor
            v-model="code"
            language="python"
            filename="main.py"
            height="100%"
          />
        </div>

        <footer class="py-editor__footer">
          <div v-if="caseResults.length" class="py-editor__summary" :class="{ 'is-success': allPassed }">
            <n-icon :component="allPassed ? CheckmarkCircleOutline : CloseCircleOutline" />
            <span>{{ passedCount }} / {{ caseResults.length }} 测试通过</span>
          </div>
          <p v-else class="py-editor__hint">编写代码后点击右上角「运行测试」，左侧面板会展示详细运行结果。</p>
        </footer>
      </section>
    </div>

    <trial-ai-floating-ball :context="floatingBallContext" />

    <n-modal
      v-model:show="codeModalVisible"
      preset="card"
      title="答题代码快照"
      class="py-attempt-code-modal"
      :style="{ width: 'min(720px, 94vw)' }"
    >
      <div v-if="activeAttempt" class="py-attempt-code">
        <div class="py-attempt-code__meta">
          <n-tag :type="activeAttempt.passed ? 'success' : 'error'" size="small">
            {{ resolveAttemptVerdict(activeAttempt) }}
          </n-tag>
          <span>
            {{ new Date(activeAttempt.submittedAt).toLocaleString('zh-CN') }}
          </span>
          <span>
            {{ resolveAttemptScore(activeAttempt).passed }}/{{ resolveAttemptScore(activeAttempt).total }} 通过
          </span>
          <n-button size="small" type="primary" ghost @click="copyAttemptCode">复制代码</n-button>
        </div>
        <pre v-if="activeAttempt.code" class="py-attempt-code__body"><code>{{ activeAttempt.code }}</code></pre>
        <p v-else class="py-attempt-code__empty">该记录未保存代码。重新运行后即可回看。</p>
      </div>
    </n-modal>
  </div>
</template>

<style scoped>
.py-workspace {
  display: flex;
  height: 100%;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  padding: 0 0.45rem 0.45rem;
}

.py-workspace__bar {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 0.4rem 0.65rem;
  margin-bottom: 0.35rem;
  padding: 0.2rem 0;
  border-bottom: 1px solid rgba(130, 212, 255, 0.1);
}

.py-workspace__slots {
  grid-column: 1 / -1;
  justify-content: center;
  margin: 0.15rem 0 0.2rem;
}

.py-workspace__slots--inline {
  grid-column: auto;
  justify-content: flex-end;
  margin: 0;
  flex: 1 1 auto;
  min-width: 0;
}

@media (min-width: 900px) {
  .py-workspace__bar {
    grid-template-columns: auto minmax(0, 1fr) auto auto;
  }

  .py-workspace__slots--inline {
    grid-column: 3;
    justify-content: center;
  }

  .py-workspace__actions {
    grid-column: 4;
  }
}

.py-side-panel__content--fade {
  animation: py-panel-fade 0.28s ease;
}

.py-block__empty {
  margin: 0;
  color: rgba(190, 208, 224, 0.68);
  font-size: 0.84rem;
}

@keyframes py-panel-fade {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.py-workspace__submit-trace {
  flex-basis: 100%;
  margin: 0;
  padding: 0.55rem 0.75rem;
  border-radius: 8px;
  background: rgba(129, 140, 248, 0.1);
  border: 1px solid rgba(129, 140, 248, 0.18);
  color: rgba(226, 232, 240, 0.78);
  font-size: 0.82rem;
  line-height: 1.45;
}

.py-workspace__back {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border: 0;
  background: transparent;
  color: rgba(221, 230, 239, 0.72);
  cursor: pointer;
  font-size: 0.88rem;
}

.py-workspace__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  align-items: center;
}

.py-workspace__topic,
.py-workspace__diff,
.py-workspace__xp {
  padding: 0.18rem 0.55rem;
  border-radius: 999px;
  font-size: 0.76rem;
  font-weight: 650;
}

.py-workspace__topic {
  background: rgba(46, 255, 241, 0.12);
  color: #5fffe8;
}

.py-workspace__diff {
  background: rgba(130, 212, 255, 0.12);
  color: #93c5fd;
}

.py-workspace__diff:where([data-level='挑战']) {
  background: rgba(244, 63, 94, 0.16);
  color: #fb7185;
}

.py-workspace__xp {
  background: rgba(251, 146, 60, 0.16);
  color: #fb923c;
}

.py-workspace__actions {
  display: flex;
  gap: 0.5rem;
  margin-left: auto;
  align-items: center;
}

.py-lang-selector {
  width: 7.5rem;
}

.py-workspace__body {
  display: grid;
  flex: 1;
  min-height: 0;
  /* 缩小侧栏占比，放大题目区与编程区可用空间 */
  grid-template-columns: minmax(300px, 0.92fr) minmax(480px, 1.65fr);
  gap: 0.55rem;
}

.py-workspace__panel {
  min-height: 0;
  overflow: hidden;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 16px;
  background: linear-gradient(145deg, rgba(5, 18, 30, 0.94), rgba(3, 12, 20, 0.82));
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.03), 0 18px 50px rgba(0, 0, 0, 0.22);
}

.py-workspace__panel--side {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.py-workspace__title {
  margin: 0;
  color: #fff7ed;
  font-size: 1.25rem;
  font-weight: 720;
}

.py-workspace__panel--brief {
  overflow: auto;
  padding: 1.15rem 1.25rem 1.35rem;
}

.py-workspace__panel--brief h1 {
  margin: 0;
  color: #fff7ed;
  font-size: 1.35rem;
  font-weight: 720;
}

.py-workspace__desc {
  margin: 0.65rem 0 1rem;
  color: rgba(226, 232, 240, 0.78);
  font-size: 0.92rem;
  line-height: 1.65;
}

.py-block {
  margin-bottom: 1rem;
}

.py-block h2 {
  margin: 0 0 0.55rem;
  color: rgba(255, 247, 237, 0.92);
  font-size: 0.92rem;
  font-weight: 700;
}

.py-block ul {
  margin: 0;
  padding-left: 1.1rem;
  color: rgba(221, 230, 239, 0.68);
  font-size: 0.84rem;
  line-height: 1.55;
}

.py-example {
  display: grid;
  gap: 0.45rem;
  margin-bottom: 0.65rem;
  padding: 0.65rem 0.75rem;
  border: 1px solid rgba(130, 212, 255, 0.1);
  border-radius: 10px;
  background: rgba(4, 12, 20, 0.55);
}

.py-example small {
  display: block;
  margin-bottom: 0.2rem;
  color: rgba(221, 230, 239, 0.52);
  font-size: 0.72rem;
}

.py-example code,
.py-test code {
  display: block;
  color: #7dd3fc;
  font-family: 'Consolas', 'Fira Code', monospace;
  font-size: 0.82rem;
  white-space: pre-wrap;
  word-break: break-word;
}

.py-example p {
  margin: 0.2rem 0 0;
  color: rgba(221, 230, 239, 0.55);
  font-size: 0.78rem;
}

.py-tests {
  display: grid;
  gap: 0.55rem;
}

.py-test {
  padding: 0.65rem 0.75rem;
  border: 1px solid rgba(130, 212, 255, 0.1);
  border-radius: 10px;
  background: rgba(4, 12, 20, 0.5);
}

.py-test strong {
  display: block;
  margin-bottom: 0.4rem;
  color: rgba(255, 247, 237, 0.88);
  font-size: 0.82rem;
}

.py-test__row {
  display: grid;
  grid-template-columns: 2.5rem minmax(0, 1fr);
  gap: 0.45rem;
  align-items: start;
  margin-top: 0.35rem;
  font-size: 0.78rem;
}

.py-test__row span {
  color: rgba(221, 230, 239, 0.48);
}

.py-results__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.55rem;
}

.py-results__head h2 {
  margin: 0;
}

.py-results__head span {
  color: #fca5a5;
  font-size: 0.78rem;
  font-weight: 700;
}

.py-results__head span.is-success {
  color: #34d399;
}

.py-results__empty {
  margin: 0;
  padding: 0.85rem 0.9rem;
  border: 1px dashed rgba(130, 212, 255, 0.16);
  border-radius: 10px;
  color: rgba(221, 230, 239, 0.52);
  font-size: 0.82rem;
  line-height: 1.55;
}

.py-results__list {
  display: grid;
  gap: 0.55rem;
}

.py-result-card {
  padding: 0.75rem 0.85rem;
  border-radius: 10px;
  border: 1px solid rgba(130, 212, 255, 0.12);
  background: rgba(4, 12, 20, 0.55);
}

.py-result-card.is-pass {
  border-color: rgba(52, 211, 153, 0.28);
  background: rgba(52, 211, 153, 0.06);
}

.py-result-card.is-fail {
  border-color: rgba(248, 113, 113, 0.28);
  background: rgba(248, 113, 113, 0.06);
}

.py-result-card header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.45rem;
}

.py-result-card header strong {
  color: rgba(255, 247, 237, 0.9);
  font-size: 0.84rem;
}

.py-result-card header span {
  font-size: 0.76rem;
  font-weight: 700;
}

.py-result-card.is-pass header span {
  color: #34d399;
}

.py-result-card.is-fail header span {
  color: #fca5a5;
}

.py-result-card__row {
  margin-top: 0.35rem;
}

.py-result-card__row small {
  display: block;
  margin-bottom: 0.18rem;
  color: rgba(221, 230, 239, 0.48);
  font-size: 0.72rem;
}

.py-result-card__row code {
  display: block;
  color: #7dd3fc;
  font-family: 'Consolas', 'Fira Code', monospace;
  font-size: 0.82rem;
  white-space: pre-wrap;
  word-break: break-word;
}

.py-result-card.is-pass .py-result-card__row:last-of-type code {
  color: #34d399;
}

.py-result-card.is-fail .py-result-card__row:last-of-type code {
  color: #fca5a5;
}

.py-result-card__meta {
  display: flex;
  gap: 0.75rem;
  margin: 0.35rem 0 0;
  color: rgba(221, 230, 239, 0.45);
  font-size: 0.72rem;
}

.py-result-card__error {
  margin: 0.45rem 0 0;
  color: #fca5a5;
  font-size: 0.78rem;
  line-height: 1.5;
}

.py-ai-block {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  margin-top: 0.35rem;
}

.py-ai-block__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.py-ai-block__head h2 {
  margin: 0;
  color: #bbf7d0;
  font-size: 0.92rem;
  font-weight: 700;
}

.py-ai-block__tip,
.py-ai-block__error {
  margin: 0;
  font-size: 0.82rem;
  line-height: 1.5;
}

.py-ai-block__tip {
  color: rgba(187, 247, 208, 0.65);
}

.py-ai-block__error {
  color: #fca5a5;
}

.py-workspace__warn {
  margin: 0.75rem 0 0;
  color: #fca5a5;
  font-size: 0.82rem;
}

.py-workspace__ok {
  margin: 0.75rem 0 0;
  color: #34d399;
  font-size: 0.78rem;
}

.py-workspace__panel--editor {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.py-editor__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.65rem 0.85rem;
  border-bottom: 1px solid rgba(130, 212, 255, 0.1);
}

.py-editor__head-actions {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin-left: auto;
}

.py-editor__filename {
  color: rgba(221, 230, 239, 0.45);
  font-family: monospace;
  font-size: 0.78rem;
}

.py-editor__head h2 {
  margin: 0;
  color: rgba(255, 247, 237, 0.9);
  font-size: 0.92rem;
}

.py-editor__head span {
  color: rgba(221, 230, 239, 0.45);
  font-family: monospace;
  font-size: 0.78rem;
}

.py-editor__wrap {
  flex: 1;
  min-height: 420px;
  overflow: hidden;
}

.py-editor__wrap :deep(.plex-code-editor) {
  border-radius: 0;
  border: none;
}

.py-editor__footer {
  padding: 0.65rem 1rem;
  border-top: 1px solid rgba(130, 212, 255, 0.1);
}

.py-editor__hint {
  margin: 0;
  color: rgba(221, 230, 239, 0.48);
  font-size: 0.8rem;
}

.py-editor__summary {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: #fca5a5;
  font-size: 0.86rem;
  font-weight: 650;
}

.py-editor__summary.is-success {
  color: #34d399;
}

.py-workspace__panel--side {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.py-side-panel__tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid rgba(130, 212, 255, 0.12);
  background: rgba(4, 12, 20, 0.55);
}

.py-side-panel__tab {
  display: inline-flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  padding: 0.72rem 0.55rem;
  border: 0;
  border-bottom: 2px solid transparent;
  border-radius: 0;
  background: transparent;
  color: rgba(221, 230, 239, 0.62);
  cursor: pointer;
  font-size: 0.82rem;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
}

.py-side-panel__tab.is-active {
  border-bottom-color: #34e6c5;
  background: rgba(52, 230, 197, 0.08);
  color: #34e6c5;
}

.py-side-panel__tab em {
  font-style: normal;
  padding: 0.05rem 0.35rem;
  border-radius: 999px;
  background: rgba(16, 240, 192, 0.15);
  color: #10f0c0;
  font-size: 0.68rem;
}

.py-side-panel__content {
  flex: 1;
  min-height: 0;
  padding: 0.85rem;
  overflow: auto;
}

.py-history__list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.py-history__empty {
  margin: 0;
  color: rgba(180, 200, 220, 0.55);
  font-size: 0.82rem;
}

.py-history__item {
  background: rgba(11, 22, 40, 0.5);
  border: 1px solid rgba(130, 212, 255, 0.1);
  border-radius: 0.5rem;
  padding: 0.5rem 0.65rem;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.py-history__item--clickable {
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.py-history__item--clickable:hover {
  border-color: rgba(46, 255, 241, 0.35);
  background: rgba(46, 255, 241, 0.06);
}

.py-history__hint {
  margin: 0;
  color: rgba(82, 255, 241, 0.72);
  font-size: 0.72rem;
}

.py-attempt-code__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.55rem;
  margin-bottom: 0.75rem;
  color: rgba(210, 230, 240, 0.78);
  font-size: 0.82rem;
}

.py-attempt-code__body {
  margin: 0;
  max-height: min(55vh, 480px);
  overflow: auto;
  padding: 0.85rem 1rem;
  border-radius: 10px;
  border: 1px solid rgba(46, 255, 241, 0.18);
  background: #020b15;
  color: #9be8d6;
  font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
  font-size: 0.82rem;
  line-height: 1.55;
  white-space: pre;
}

.py-attempt-code__empty {
  margin: 0;
  color: rgba(190, 208, 224, 0.7);
  font-size: 0.86rem;
}

.py-history__row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.py-history__score {
  color: rgba(255, 247, 237, 0.88);
  font-size: 0.78rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.py-history__time {
  color: rgba(180, 200, 220, 0.6);
  font-size: 0.75rem;
}

.py-history__duration {
  margin-left: auto;
  color: rgba(180, 200, 220, 0.55);
  font-size: 0.74rem;
}

.py-history__cases {
  color: rgba(252, 165, 165, 0.8);
  font-size: 0.78rem;
}

@media (max-width: 1100px) {
  .py-workspace__body {
    grid-template-columns: 1fr;
    grid-template-rows: minmax(280px, auto) minmax(420px, 1fr);
    overflow: auto;
  }

  .py-workspace__panel--side {
    min-height: 320px;
  }
}

@media (max-width: 960px) {
  .py-workspace__body {
    grid-template-columns: 1fr;
    overflow: auto;
  }

  .py-workspace__panel--editor {
    min-height: 420px;
  }

  .py-workspace__actions {
    width: 100%;
    margin-left: 0;
    justify-content: flex-end;
  }
}
</style>

<style>
/* PythonTrialWorkspace 浅色全局覆盖（非 scoped，依赖 html[data-theme] 选择器） */
html[data-theme='light'] .py-workspace__back {
  color: rgba(71, 85, 105, 0.75) !important;
}

html[data-theme='light'] .py-workspace__bar {
  border-bottom-color: rgba(0, 0, 0, 0.08) !important;
}

html[data-theme='light'] .py-panel {
  background: linear-gradient(145deg, #ffffff, #f8fafc) !important;
  border-color: rgba(0, 0, 0, 0.08) !important;
}

html[data-theme='light'] .py-panel__title {
  color: #0f172a !important;
}

html[data-theme='light'] .py-panel__desc {
  color: rgba(71, 85, 105, 0.78) !important;
}

html[data-theme='light'] .py-output {
  background: #f8fafc !important;
  border-color: rgba(0, 0, 0, 0.08) !important;
}

html[data-theme='light'] .py-output__title {
  color: rgba(71, 85, 105, 0.68) !important;
}

html[data-theme='light'] .py-output__result {
  color: #0f172a !important;
}

html[data-theme='light'] .py-case-pass {
  color: #16a34a !important;
}

html[data-theme='light'] .py-case-fail {
  color: #dc2626 !important;
}
</style>
