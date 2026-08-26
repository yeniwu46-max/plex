<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { NButton, NInput, NSelect, useMessage } from 'naive-ui'
import {
  fetchCodingQuestionBank,
  type CodingBankItem,
  type TrialPaperQuestion,
} from '../../api/teacherTrials'

const props = defineProps<{
  modelValue: TrialPaperQuestion[]
  knowledgeKey?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: TrialPaperQuestion[]]
}>()

const message = useMessage()
const bankItems = ref<CodingBankItem[]>([])
const showBank = ref(false)
const editingIndex = ref<number | null>(null)

const questions = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

function newMcq(): TrialPaperQuestion {
  return {
    question_type: 'mcq',
    stem: '',
    options: ['', '', '', ''],
    correct_index: 0,
    knowledge_key: props.knowledgeKey,
  }
}

function newCoding(): TrialPaperQuestion {
  return {
    question_type: 'coding',
    stem: '',
    starter_code: '# 在此编写代码\n',
    run_mode: 'stdout',
    hint: '',
    test_cases: [{ id: 't1', label: '样例 1', expected: '' }],
    knowledge_key: props.knowledgeKey,
  }
}

function addMcq() {
  questions.value = [...questions.value, newMcq()]
  editingIndex.value = questions.value.length - 1
}

function addCoding() {
  questions.value = [...questions.value, newCoding()]
  editingIndex.value = questions.value.length - 1
}

function removeQuestion(index: number) {
  questions.value = questions.value.filter((_, i) => i !== index)
  if (editingIndex.value === index) editingIndex.value = null
}

function moveQuestion(index: number, delta: number) {
  const next = [...questions.value]
  const target = index + delta
  if (target < 0 || target >= next.length) return
  ;[next[index], next[target]] = [next[target], next[index]]
  questions.value = next
  editingIndex.value = target
}

function updateQuestion(index: number, patch: Partial<TrialPaperQuestion>) {
  const next = [...questions.value]
  next[index] = { ...next[index], ...patch } as TrialPaperQuestion
  questions.value = next
}

function addTestCase(index: number) {
  const q = questions.value[index]
  if (q.question_type !== 'coding') return
  const cases = [...q.test_cases, { id: `t${q.test_cases.length + 1}`, label: `用例 ${q.test_cases.length + 1}`, expected: '' }]
  updateQuestion(index, { test_cases: cases })
}

function removeTestCase(qIndex: number, caseIndex: number) {
  const q = questions.value[qIndex]
  if (q.question_type !== 'coding' || q.test_cases.length <= 1) return
  updateQuestion(qIndex, { test_cases: q.test_cases.filter((_, i) => i !== caseIndex) })
}

function importFromBank(item: CodingBankItem) {
  questions.value = [
    ...questions.value,
    {
      question_type: 'coding',
      stem: item.stem,
      starter_code: item.starter_code,
      run_mode: item.run_mode as 'stdout' | 'expression',
      hint: item.hint || '',
      test_cases: (item.test_cases ?? []).map((tc) => ({ ...tc })),
      knowledge_key: item.knowledge_key || props.knowledgeKey,
    },
  ]
  showBank.value = false
  message.success(`已添加编程题「${item.id}」`)
}

onMounted(async () => {
  try {
    bankItems.value = await fetchCodingQuestionBank()
  } catch {
    bankItems.value = []
  }
})

watch(
  () => props.knowledgeKey,
  (key) => {
    if (!key) return
    questions.value = questions.value.map((q) => ({ ...q, knowledge_key: q.knowledge_key || key }))
  },
)
</script>

<template>
  <section class="paper-editor" aria-label="试卷编辑器">
    <header class="paper-editor__head">
      <strong>试卷题目 · {{ questions.length }} 题</strong>
      <div class="paper-editor__actions">
        <n-button size="small" secondary @click="addMcq">+ 选择题</n-button>
        <n-button size="small" secondary @click="addCoding">+ 编程题</n-button>
        <n-button size="small" quaternary @click="showBank = !showBank">从题库添加</n-button>
      </div>
    </header>

    <div v-if="showBank" class="paper-editor__bank">
      <p v-if="!bankItems.length">题库加载中或暂无题目</p>
      <button
        v-for="item in bankItems"
        :key="item.id"
        type="button"
        class="paper-editor__bank-item"
        @click="importFromBank(item)"
      >
        <strong>{{ item.id }}</strong>
        <span>{{ item.stem.slice(0, 48) }}…</span>
      </button>
    </div>

    <p v-if="!questions.length" class="paper-editor__empty">尚未添加题目。可 AI 生成选择题，或手动添加选择/编程题。</p>

    <article v-for="(q, index) in questions" :key="index" class="paper-editor__item">
      <header class="paper-editor__item-head">
        <span>Q{{ index + 1 }} · {{ q.question_type === 'coding' ? '编程题' : '选择题' }}</span>
        <div>
          <n-button quaternary size="tiny" :disabled="index === 0" @click="moveQuestion(index, -1)">↑</n-button>
          <n-button quaternary size="tiny" :disabled="index === questions.length - 1" @click="moveQuestion(index, 1)">↓</n-button>
          <n-button quaternary size="tiny" @click="editingIndex = editingIndex === index ? null : index">
            {{ editingIndex === index ? '收起' : '编辑' }}
          </n-button>
          <n-button quaternary size="tiny" type="error" @click="removeQuestion(index)">删除</n-button>
        </div>
      </header>

      <p class="paper-editor__preview">{{ q.stem || '未填写题干' }}</p>

      <div v-if="editingIndex === index" class="paper-editor__form">
        <label>
          <span>题干</span>
          <n-input
            :value="q.stem"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 6 }"
            @update:value="(v) => updateQuestion(index, { stem: v })"
          />
        </label>

        <template v-if="q.question_type === 'mcq'">
          <label v-for="(_, optIdx) in q.options" :key="optIdx">
            <span>选项 {{ String.fromCharCode(65 + optIdx) }}</span>
            <n-input
              :value="q.options[optIdx]"
              @update:value="(v) => {
                const options = [...q.options]
                options[optIdx] = v
                updateQuestion(index, { options })
              }"
            />
          </label>
          <label>
            <span>正确答案</span>
            <n-select
              :value="q.correct_index"
              :options="q.options.map((_, i) => ({ label: String.fromCharCode(65 + i), value: i }))"
              @update:value="(v) => updateQuestion(index, { correct_index: Number(v) })"
            />
          </label>
        </template>

        <template v-else>
          <label>
            <span>Starter Code</span>
            <n-input
              :value="q.starter_code"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 10 }"
              @update:value="(v) => updateQuestion(index, { starter_code: v })"
            />
          </label>
          <label>
            <span>运行模式</span>
            <n-select
              :value="q.run_mode"
              :options="[
                { label: '标准输出 stdout', value: 'stdout' },
                { label: '表达式 expression', value: 'expression' },
              ]"
              @update:value="(v) => updateQuestion(index, { run_mode: v as 'stdout' | 'expression' })"
            />
          </label>
          <label>
            <span>提示</span>
            <n-input :value="q.hint" @update:value="(v) => updateQuestion(index, { hint: v })" />
          </label>
          <div class="paper-editor__cases">
            <strong>测试用例</strong>
            <article v-for="(tc, caseIdx) in q.test_cases" :key="tc.id" class="paper-editor__case">
              <n-input
                :value="tc.label"
                placeholder="标签"
                @update:value="(v) => {
                  const test_cases = q.test_cases.map((c, i) => i === caseIdx ? { ...c, label: v } : c)
                  updateQuestion(index, { test_cases })
                }"
              />
              <n-input
                :value="tc.setup || ''"
                placeholder="初始化代码，可选"
                @update:value="(v) => {
                  const test_cases = q.test_cases.map((c, i) => i === caseIdx ? { ...c, setup: v || undefined } : c)
                  updateQuestion(index, { test_cases })
                }"
              />
              <n-input
                :value="tc.expected"
                placeholder="期望输出"
                @update:value="(v) => {
                  const test_cases = q.test_cases.map((c, i) => i === caseIdx ? { ...c, expected: v } : c)
                  updateQuestion(index, { test_cases })
                }"
              />
              <n-button quaternary size="tiny" @click="removeTestCase(index, caseIdx)">删</n-button>
            </article>
            <n-button size="tiny" secondary @click="addTestCase(index)">+ 添加用例</n-button>
          </div>
        </template>
      </div>
    </article>
  </section>
</template>

<style scoped>
.paper-editor {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.paper-editor__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  flex-wrap: wrap;
  color: rgba(255, 247, 237, 0.9);
  font-size: 0.88rem;
}

.paper-editor__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.paper-editor__empty {
  margin: 0;
  color: rgba(221, 230, 239, 0.55);
  font-size: 0.82rem;
}

.paper-editor__bank {
  display: grid;
  gap: 0.35rem;
  padding: 0.65rem;
  border-radius: 10px;
  border: 1px solid rgba(130, 212, 255, 0.14);
  background: rgba(5, 18, 30, 0.55);
}

.paper-editor__bank-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.15rem;
  padding: 0.45rem 0.55rem;
  border: 1px solid rgba(130, 212, 255, 0.1);
  border-radius: 8px;
  background: rgba(3, 12, 20, 0.65);
  color: rgba(226, 232, 240, 0.82);
  cursor: pointer;
  text-align: left;
}

.paper-editor__bank-item strong {
  color: #fb923c;
  font-size: 0.78rem;
}

.paper-editor__item {
  padding: 0.65rem 0.75rem;
  border-radius: 10px;
  border: 1px solid rgba(130, 212, 255, 0.12);
  background: rgba(5, 18, 30, 0.45);
}

.paper-editor__item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
  color: rgba(255, 247, 237, 0.75);
  font-size: 0.78rem;
}

.paper-editor__preview {
  margin: 0;
  color: rgba(226, 232, 240, 0.88);
  font-size: 0.84rem;
  line-height: 1.5;
}

.paper-editor__form {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  margin-top: 0.65rem;
}

.paper-editor__form label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  color: rgba(221, 230, 239, 0.65);
  font-size: 0.76rem;
}

.paper-editor__cases {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.paper-editor__case {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr auto;
  gap: 0.35rem;
  align-items: center;
}
</style>
