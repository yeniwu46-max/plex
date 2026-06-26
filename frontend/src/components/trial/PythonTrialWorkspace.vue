<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NIcon, NTag, useMessage } from 'naive-ui'
import PlexCodeEditor from './PlexCodeEditor.vue'
import {
  ArrowBackOutline,
  BulbOutline,
  ChatbubbleEllipsesOutline,
  CheckmarkCircleOutline,
  CloseCircleOutline,
  CloudUploadOutline,
  PlayOutline,
  RefreshOutline,
  ShuffleOutline,
  TimeOutline,
} from '@vicons/ionicons5'
import type { PythonTrialQuestion } from '../../data/pythonTrialQuestions'
import { useAuthStore } from '../../stores/auth'
import { useNotificationStore } from '../../stores/notifications'
import { getTrialMistakeRecords, recordTrialRun } from '../../utils/trialMistakeLog'
import { submitTrialCodeAnswer } from '../../api/studentAssignments'
import { advanceDailyQuest } from '../../api/studentOverview'
import { codeHint, runCodeLearningCycle, studentDiagnose, type LearningCycleResult, type StudentDiagnoseResult } from '../../api/agentService'
import PlexDiagnosisPanel from '../agent/PlexDiagnosisPanel.vue'
import PlexLearningAdvicePanel from '../agent/PlexLearningAdvicePanel.vue'
import PlexAgentTracePanel from '../agent/PlexAgentTracePanel.vue'
import PlexLearningCyclePanel from '../agent/PlexLearningCyclePanel.vue'
// recordTrialRun 会写入 localStorage 并异步同步 POST /student/code-trial/runs

const props = withDefaults(
  defineProps<{
    question: PythonTrialQuestion
    embedded?: boolean
    backLabel?: string
    trialQuestionId?: number
  }>(),
  {
    embedded: false,
    backLabel: '返回星轨',
    trialQuestionId: undefined,
  },
)

const emit = defineEmits<{
  back: []
  passed: []
  changeQuestion: []
}>()

const router = useRouter()
const message = useMessage()
const auth = useAuthStore()
const notifications = useNotificationStore()

const code = ref(props.question.starterCode || 'print("Hello, PLEX!")')
const running = ref(false)
const submittingManual = ref(false)
const showHint = ref(false)
const showHistory = ref(false)
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
const learningCycle = ref<LearningCycleResult | null>(null)
const agentError = ref('')
const aiHintLoading = ref(false)
let agentRequestId = 0
const passedCount = computed(() => caseResults.value.filter((item) => item.passed).length)
const allPassed = computed(
  () => caseResults.value.length > 0 && passedCount.value === caseResults.value.length,
)

const agentPreview = computed<StudentDiagnoseResult>(() => ({
  diagnosis: {
    weakPoints: [props.question.topic],
    errorType: 'unknown',
    diagnosis: '正在分析你的代码与学习记录…',
    confidence: 0,
  },
  codeAnalysis: {
    codeIssueSummary: '分析中',
    possibleCause: '',
    fixDirection: '',
    relatedConcepts: props.question.tags,
  },
  graphInsight: {
    relatedNodes: [props.question.topic],
    prerequisiteNodes: [],
    recommendedReviewNodes: [],
    graphReason: '',
  },
  recommendation: {
    nextKnowledgePoint: props.question.topic,
    recommendedExercises: [],
    reviewPlan: [],
    estimatedDifficulty: 'easy',
  },
  feedback: {
    shortFeedback: '',
    stepHints: [],
    encouragement: '',
    nextAction: '',
  },
}))

const answerHistory = computed(() => {
  const userId = auth.profile?.id ?? 'guest'
  return getTrialMistakeRecords(userId).filter((r) => r.questionId === props.question.id)
})

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

async function runSingleCase(testCase: PythonTrialQuestion['testCases'][number]) {
  const py = await ensurePyodide()
  const setup = testCase.setup ? `${testCase.setup}\n` : ''

  await py.runPythonAsync(`
import sys
from io import StringIO
sys.stdout = StringIO()
`)

  try {
    if (props.question.runMode === 'expression' && testCase.invoke) {
      await py.runPythonAsync(`${setup}\n${code.value}`)
      const actual = normalizeOutput(await py.runPythonAsync(testCase.invoke))
      return { actual, error: undefined }
    }

    await py.runPythonAsync(`${setup}\n${code.value}`)
    const actual = normalizeOutput(await py.runPythonAsync('sys.stdout.getvalue()'))
    return { actual, error: undefined }
  } catch (error) {
    return {
      actual: '',
      error: error instanceof Error ? error.message : '运行出错',
    }
  }
}

function applyRunResults(results: CaseResult[], backend: 'api' | 'pyodide') {
  if (aborted || !isMounted.value) return
  caseResults.value = results
  executionBackend.value = backend
  const userId = auth.profile?.id ?? 'guest'
  const allPass = results.every((item) => item.passed)

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

  recordTrialRun(
    userId,
    props.question,
    results.map((item) => ({ label: item.label, passed: item.passed, error: item.error })),
  )
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

async function runViaApi(): Promise<CaseResult[]> {
  const payload = await runCodeLearningCycle({
    language: 'python',
    code: code.value,
    run_mode: props.question.runMode,
    test_cases: props.question.testCases.map((tc) => ({
      id: tc.id,
      label: tc.label,
      input: '',
      expected: tc.expected,
      setup: tc.setup,
      invoke: tc.invoke,
    })),
    exerciseId: props.question.id,
    questionTitle: props.question.title,
    questionPrompt: props.question.description,
    topic: props.question.topic,
    knowledgePoints: [props.question.topic, ...props.question.tags],
    attemptCount: answerHistory.value.length + 1,
  })
  learningCycle.value = payload
  agentResult.value = payload
  agentError.value = ''
  return payload.execution.results.map((item) => ({
    id: item.case_id || item.label,
    label: item.label,
    expected: item.expected,
    actual: item.actual,
    passed: item.passed,
    error: item.error ?? undefined,
    time: item.time,
    memory: item.memory,
  }))
}

async function runViaPyodide(): Promise<CaseResult[]> {
  const results: CaseResult[] = []
  for (const testCase of props.question.testCases) {
    const { actual, error } = await runSingleCase(testCase)
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
  caseResults.value = []
  executionBackend.value = null
  try {
    try {
      const results = await runViaApi()
      if (aborted || !isMounted.value) return
      applyRunResults(results, 'api')
      return
    } catch {
      /* fall back to Pyodide */
    }
    const results = await runViaPyodide()
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
  code.value = props.question.starterCode || 'print("Hello, PLEX!")'
  caseResults.value = []
  showHint.value = false
  agentResult.value = null
  learningCycle.value = null
  agentError.value = ''
}

function revealHint() {
  showHint.value = true
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
  void router.push('/student/trials')
}

onBeforeUnmount(() => {
  aborted = true
  isMounted.value = false
  running.value = false
})

watch(
  () => props.question.id,
  () => {
    code.value = props.question.starterCode || 'print("Hello, PLEX!")'
    caseResults.value = []
    showHint.value = false
    agentResult.value = null
    learningCycle.value = null
    agentError.value = ''
  },
)

async function askAiForHint() {
  if (!code.value.trim() || aiHintLoading.value) return
  aiHintLoading.value = true
  const failedCases = caseResults.value
    .filter((item) => !item.passed)
    .map((item) => ({
      label: item.label,
      expected: item.expected,
      actual: item.actual,
      error: item.error,
    }))
  const failedCase = failedCases[0]
  try {
    const result = await codeHint({
      exerciseId: props.question.id,
      questionTitle: props.question.title,
      topic: props.question.topic,
      code: code.value,
      stdout: failedCase?.actual,
      stderr: failedCase?.error,
      expectedOutput: failedCase?.expected,
      failedCases,
    })
    code.value = result.annotated_code
    message.success('AI 已把提示写入代码注释')
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'AI 提示生成失败')
  } finally {
    aiHintLoading.value = false
  }
}

async function fetchAiFeedback() {
  if (!code.value.trim() || agentLoading.value) return
  const requestId = ++agentRequestId
  agentLoading.value = true
  agentError.value = ''
  agentResult.value = null

  const failedCase = caseResults.value.find((item) => !item.passed)
  const attemptCount = answerHistory.value.length + 1

  try {
    const result = await studentDiagnose({
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
    agentError.value = msg.includes('timeout') ? '智能体响应超时（15s），请稍后重试' : msg
  } finally {
    if (requestId === agentRequestId && isMounted.value) {
      agentLoading.value = false
    }
  }
}
</script>

<template>
  <div class="py-workspace">
    <header class="py-workspace__bar">
      <button type="button" class="py-workspace__back" @click="goBack">
        <n-icon :component="ArrowBackOutline" />
        {{ embedded ? backLabel : '返回题目列表' }}
      </button>
      <div class="py-workspace__meta">
        <span class="py-workspace__topic">{{ question.topic }}</span>
        <span class="py-workspace__diff" :data-level="question.difficulty">{{ question.difficulty }}</span>
        <span class="py-workspace__xp">+{{ question.rewardXp }} XP</span>
      </div>
      <div class="py-workspace__actions">
        <n-button v-if="embedded" quaternary :disabled="running" @click="emit('changeQuestion')">
          <template #icon><n-icon :component="ShuffleOutline" /></template>
          换一题
        </n-button>
        <n-button quaternary :disabled="running" @click="onReset">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          重置代码
        </n-button>
        <n-button
          secondary
          :loading="aiHintLoading"
          :disabled="running || !code.trim()"
          @click="askAiForHint"
        >
          <template #icon><n-icon :component="ChatbubbleEllipsesOutline" /></template>
          询问AI
        </n-button>
        <n-button type="primary" :loading="running || pyodideLoading" @click="onRun">
          <template #icon><n-icon :component="PlayOutline" /></template>
          运行测试
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
    </header>

    <div class="py-workspace__body">
      <aside class="py-workspace__panel py-workspace__panel--brief">
        <h1>{{ question.title }}</h1>
        <p class="py-workspace__desc">{{ question.description }}</p>

        <section v-if="question.constraints.length" class="py-block">
          <h2>要求</h2>
          <ul>
            <li v-for="item in question.constraints" :key="item">{{ item }}</li>
          </ul>
        </section>

        <section class="py-block">
          <h2>示例</h2>
          <article v-for="(ex, index) in question.examples" :key="index" class="py-example">
            <div><small>输入</small><code>{{ ex.input }}</code></div>
            <div><small>输出</small><code>{{ ex.output }}</code></div>
          </article>
        </section>

        <section class="py-block">
          <h2>测试数据</h2>
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

          <p v-if="!caseResults.length" class="py-results__empty">点击右上角「运行测试」后，这里会显示每个测试点的实际输出与判定。</p>

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
                <code>{{ item.error ? '（无输出）' : item.actual || '（空）' }}</code>
              </div>
              <p v-if="item.time || item.memory" class="py-result-card__meta">
                <span v-if="item.time">耗时 {{ item.time }}s</span>
                <span v-if="item.memory">内存 {{ item.memory }}KB</span>
              </p>
              <p v-if="item.error" class="py-result-card__error">{{ item.error }}</p>
            </article>
          </div>
        </section>

        <section class="py-hint-block">
          <button v-if="!showHint" type="button" class="py-hint-toggle" @click="revealHint">
            <n-icon :component="BulbOutline" />
            查看提示
          </button>
          <div v-else class="py-hint">
            <n-icon :component="BulbOutline" />
            <p>{{ question.hint }}</p>
          </div>
        </section>

        <section class="py-ai-block" aria-label="AI 学习反馈">
          <header class="py-ai-block__head">
            <h2>AI 学习反馈</h2>
            <n-button
              size="small"
              type="primary"
              ghost
              :loading="agentLoading"
              :disabled="!code.trim() || (!caseResults.length && !agentLoading)"
              @click="fetchAiFeedback"
            >
              获取 AI 反馈
            </n-button>
          </header>
          <p v-if="!caseResults.length && !agentResult" class="py-ai-block__tip">
            请先运行测试，再获取针对当前代码的学习反馈。
          </p>
          <p v-else-if="agentError" class="py-ai-block__error">{{ agentError }}</p>
          <template v-else-if="agentResult || agentLoading">
            <plex-agent-trace-panel
              :trace="agentResult?.pipelineTrace"
              :loading="agentLoading && !agentResult"
            />
            <plex-diagnosis-panel
              :result="agentResult ?? agentPreview"
              :loading="agentLoading && !agentResult"
            />
            <plex-learning-advice-panel
              v-if="agentResult"
              :result="agentResult"
              :loading="false"
            />
            <plex-learning-cycle-panel
              v-if="learningCycle"
              :result="learningCycle"
            />
          </template>
        </section>

        <p v-if="executionBackend === 'api'" class="py-workspace__ok">已通过 PLEX 沙箱服务运行（Judge0/Mock）</p>
        <p v-else-if="executionBackend === 'pyodide'" class="py-workspace__ok">已通过浏览器 Pyodide 离线运行</p>
        <p v-else-if="pyodideError" class="py-workspace__warn">{{ pyodideError }}</p>
        <p v-else-if="pyodideReady" class="py-workspace__ok">Pyodide 离线环境已就绪（API 不可用时自动启用）</p>

        <section class="py-block py-history">
          <button type="button" class="py-history__toggle" @click="showHistory = !showHistory">
            <n-icon :component="TimeOutline" />
            <span>答题记录</span>
            <span v-if="answerHistory.length" class="py-history__count">{{ answerHistory.length }}</span>
            <span class="py-history__arrow">{{ showHistory ? '▲' : '▼' }}</span>
          </button>
          <div v-if="showHistory" class="py-history__list">
            <p v-if="!answerHistory.length" class="py-history__empty">暂无提交记录，运行测试后会记录在这里。</p>
            <template v-else>
              <article v-for="record in answerHistory" :key="record.lastFailedAt" class="py-history__item">
                <div class="py-history__row">
                  <n-tag v-if="record.lastPassedAt && new Date(record.lastPassedAt) > new Date(record.lastFailedAt)" type="success" size="small">AC</n-tag>
                  <n-tag v-else type="error" size="small">WA × {{ record.failCount }}</n-tag>
                  <span class="py-history__time">{{ new Date(record.lastFailedAt).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) }}</span>
                </div>
                <div v-if="record.failedCaseLabels.length" class="py-history__cases">
                  未通过：{{ record.failedCaseLabels.join('、') }}
                </div>
              </article>
            </template>
          </div>
        </section>
      </aside>

      <section class="py-workspace__panel py-workspace__panel--editor">
        <header class="py-editor__head">
          <h2>代码编辑区</h2>
          <span>main.py</span>
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
          <p v-else class="py-editor__hint">编写代码后点击「运行测试」，左侧会展示详细运行结果。</p>
        </footer>
      </section>
    </div>
  </div>
</template>

<style scoped>
.py-workspace {
  display: flex;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  padding: 0 var(--plex-page-gutter-x, 1.25rem) 1.25rem;
}

.py-workspace__bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem 1rem;
  margin-bottom: 1rem;
  padding: 0.65rem 0;
  border-bottom: 1px solid rgba(130, 212, 255, 0.1);
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
  grid-template-columns: minmax(300px, 0.92fr) minmax(360px, 1.08fr);
  gap: 1rem;
}

.py-workspace__panel {
  min-height: 0;
  overflow: hidden;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 16px;
  background: linear-gradient(145deg, rgba(5, 18, 30, 0.94), rgba(3, 12, 20, 0.82));
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.03), 0 18px 50px rgba(0, 0, 0, 0.22);
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

.py-hint-block {
  margin-top: 0.25rem;
}

.py-hint-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.55rem 0.85rem;
  border: 1px solid rgba(251, 146, 60, 0.28);
  border-radius: 999px;
  background: rgba(251, 146, 60, 0.08);
  color: #fdba74;
  cursor: pointer;
  font-size: 0.84rem;
}

.py-hint-toggle .n-icon {
  font-size: 1rem;
}

.py-hint {
  display: flex;
  gap: 0.55rem;
  align-items: flex-start;
  padding: 0.75rem 0.85rem;
  border: 1px solid rgba(251, 146, 60, 0.22);
  border-radius: 10px;
  background: rgba(251, 146, 60, 0.08);
  color: rgba(255, 237, 213, 0.82);
  font-size: 0.84rem;
  line-height: 1.55;
}

.py-hint .n-icon {
  margin-top: 0.1rem;
  color: #fb923c;
  font-size: 1.1rem;
  flex-shrink: 0;
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
  padding: 0.75rem 1rem;
  border-bottom: 1px solid rgba(130, 212, 255, 0.1);
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
  min-height: 320px;
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

.py-history__toggle {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  width: 100%;
  padding: 0.55rem 0;
  border: none;
  background: none;
  color: rgba(221, 230, 239, 0.8);
  font-size: 0.86rem;
  cursor: pointer;
  text-align: left;
}

.py-history__toggle:hover {
  color: #edf7ff;
}

.py-history__count {
  background: rgba(16, 240, 192, 0.15);
  color: #10f0c0;
  border-radius: 999px;
  padding: 0 0.45em;
  font-size: 0.75rem;
  font-weight: 700;
}

.py-history__arrow {
  margin-left: auto;
  font-size: 0.7rem;
  opacity: 0.6;
}

.py-history__list {
  margin-top: 0.5rem;
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

.py-history__row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.py-history__time {
  color: rgba(180, 200, 220, 0.6);
  font-size: 0.75rem;
}

.py-history__cases {
  color: rgba(252, 165, 165, 0.8);
  font-size: 0.78rem;
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
