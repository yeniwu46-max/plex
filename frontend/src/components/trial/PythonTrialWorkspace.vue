<script setup lang="ts">
import { computed, ref, shallowRef, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Codemirror } from 'vue-codemirror'
import { python } from '@codemirror/lang-python'
import { oneDark } from '@codemirror/theme-one-dark'
import { NButton, NIcon, useMessage } from 'naive-ui'
import {
  ArrowBackOutline,
  BulbOutline,
  CheckmarkCircleOutline,
  CloseCircleOutline,
  PlayOutline,
  RefreshOutline,
} from '@vicons/ionicons5'
import type { PythonTrialQuestion } from '../../data/pythonTrialQuestions'
import { useAuthStore } from '../../stores/auth'
import { recordTrialRun } from '../../utils/trialMistakeLog'

const props = defineProps<{
  question: PythonTrialQuestion
}>()

const router = useRouter()
const message = useMessage()
const auth = useAuthStore()

const code = ref(props.question.starterCode)
const running = ref(false)
const showHint = ref(false)
const pyodideReady = ref(false)
const pyodideLoading = ref(false)
const pyodideError = ref('')

type CaseResult = {
  id: string
  label: string
  expected: string
  actual: string
  passed: boolean
  error?: string
}

const caseResults = ref<CaseResult[]>([])
const passedCount = computed(() => caseResults.value.filter((item) => item.passed).length)
const allPassed = computed(
  () => caseResults.value.length > 0 && passedCount.value === caseResults.value.length,
)

const editorExtensions = shallowRef([python(), oneDark])

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

async function onRun() {
  running.value = true
  caseResults.value = []
  try {
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
    caseResults.value = results
    const userId = auth.profile?.id ?? 'guest'
    recordTrialRun(
      userId,
      props.question,
      results.map((item) => ({ label: item.label, passed: item.passed, error: item.error })),
    )
    if (results.every((item) => item.passed)) {
      message.success('全部测试通过！')
    } else {
      message.warning(`${results.filter((item) => item.passed).length}/${results.length} 个测试通过`)
    }
  } catch {
    message.error(pyodideError.value || '运行失败，请检查网络后重试')
  } finally {
    running.value = false
  }
}

function onReset() {
  code.value = props.question.starterCode
  caseResults.value = []
  showHint.value = false
}

function revealHint() {
  showHint.value = true
}

function goBack() {
  void router.push('/student/trials')
}

watch(
  () => props.question.id,
  () => {
    code.value = props.question.starterCode
    caseResults.value = []
    showHint.value = false
  },
)
</script>

<template>
  <div class="py-workspace">
    <header class="py-workspace__bar">
      <button type="button" class="py-workspace__back" @click="goBack">
        <n-icon :component="ArrowBackOutline" />
        返回题目列表
      </button>
      <div class="py-workspace__meta">
        <span class="py-workspace__topic">{{ question.topic }}</span>
        <span class="py-workspace__diff">{{ question.difficulty }}</span>
        <span class="py-workspace__xp">+{{ question.rewardXp }} XP</span>
      </div>
      <div class="py-workspace__actions">
        <n-button quaternary :disabled="running" @click="onReset">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          重置代码
        </n-button>
        <n-button type="primary" :loading="running || pyodideLoading" @click="onRun">
          <template #icon><n-icon :component="PlayOutline" /></template>
          运行测试
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

        <p v-if="pyodideError" class="py-workspace__warn">{{ pyodideError }}</p>
        <p v-else-if="pyodideReady" class="py-workspace__ok">Python 运行环境已就绪</p>
      </aside>

      <section class="py-workspace__panel py-workspace__panel--editor">
        <header class="py-editor__head">
          <h2>代码编辑区</h2>
          <span>main.py</span>
        </header>
        <div class="py-editor__wrap">
          <codemirror
            v-model="code"
            :extensions="editorExtensions"
            :style="{ height: '100%', fontSize: '14px' }"
            :indent-with-tab="true"
            :tab-size="4"
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

.py-workspace__xp {
  background: rgba(251, 146, 60, 0.16);
  color: #fb923c;
}

.py-workspace__actions {
  display: flex;
  gap: 0.5rem;
  margin-left: auto;
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

.py-editor__wrap :deep(.cm-editor) {
  height: 100%;
  background: #0a1628;
}

.py-editor__wrap :deep(.cm-scroller) {
  font-family: 'Consolas', 'Fira Code', 'Microsoft YaHei', monospace;
  line-height: 1.55;
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
