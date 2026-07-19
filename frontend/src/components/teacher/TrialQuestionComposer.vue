<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NButton, NInput, NInputNumber, NSelect, NSlider, useMessage } from 'naive-ui'
import {
  fetchCodingQuestionBank,
  type CodingBankItem,
} from '../../api/teacherTrials'
import type { KnowledgeDomainDef } from '../../data/teacherKnowledgeCatalog'
import {
  createComposerQuestion,
  nextComposerUid,
  QUESTION_TYPE_LABELS,
  type ComposerQuestion,
  type ComposerQuestionType,
  type ComposerTestCase,
} from '../../utils/trialQuestionComposerModel'

const props = defineProps<{
  modelValue: ComposerQuestion[]
  domains: KnowledgeDomainDef[]
  defaultKnowledgeKey?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: ComposerQuestion[]]
}>()

const message = useMessage()
const bankItems = ref<CodingBankItem[]>([])
const showBank = ref(false)
const editingUid = ref<string | null>(null)

const questions = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const knowledgeOptions = computed(() =>
  props.domains.flatMap((domain) =>
    domain.points.map((point) => ({
      label: `${domain.label} · ${point.label}`,
      value: point.key,
    })),
  ),
)

const addTypes: ComposerQuestionType[] = [
  'single',
  'multiple',
  'true_false',
  'fill_blank',
  'short_answer',
  'coding',
]

function addQuestion(type: ComposerQuestionType) {
  const q = createComposerQuestion(type, props.defaultKnowledgeKey)
  questions.value = [...questions.value, q]
  editingUid.value = q.uid
}

function duplicateQuestion(index: number) {
  const source = questions.value[index]
  const copy: ComposerQuestion = {
    ...JSON.parse(JSON.stringify(source)),
    uid: nextComposerUid(),
  }
  const next = [...questions.value]
  next.splice(index + 1, 0, copy)
  questions.value = next
  editingUid.value = copy.uid
}

function removeQuestion(index: number) {
  const removed = questions.value[index]
  questions.value = questions.value.filter((_, i) => i !== index)
  if (editingUid.value === removed?.uid) editingUid.value = null
}

function moveQuestion(index: number, delta: number) {
  const target = index + delta
  if (target < 0 || target >= questions.value.length) return
  const next = [...questions.value]
  ;[next[index], next[target]] = [next[target], next[index]]
  questions.value = next
}

function patchQuestion(index: number, patch: Partial<ComposerQuestion>) {
  const next = [...questions.value]
  next[index] = { ...next[index], ...patch }
  questions.value = next
}

function updateOption(index: number, optIdx: number, value: string) {
  const options = [...questions.value[index].options]
  options[optIdx] = value
  patchQuestion(index, { options })
}

function addOption(index: number) {
  const options = [...questions.value[index].options, '']
  patchQuestion(index, { options })
}

function removeOption(index: number, optIdx: number) {
  const q = questions.value[index]
  if (q.options.length <= 2) return
  const options = q.options.filter((_, i) => i !== optIdx)
  let correctIndex = q.correctIndex
  if (correctIndex >= options.length) correctIndex = options.length - 1
  const correctIndexes = q.correctIndexes
    .filter((i) => i !== optIdx)
    .map((i) => (i > optIdx ? i - 1 : i))
  patchQuestion(index, { options, correctIndex, correctIndexes })
}

function toggleMultiCorrect(index: number, optIdx: number) {
  const q = questions.value[index]
  const set = new Set(q.correctIndexes)
  if (set.has(optIdx)) set.delete(optIdx)
  else set.add(optIdx)
  patchQuestion(index, { correctIndexes: [...set] })
}

function updateBlank(index: number, blankIdx: number, value: string) {
  const blankAnswers = [...questions.value[index].blankAnswers]
  blankAnswers[blankIdx] = value
  patchQuestion(index, { blankAnswers })
}

function addBlank(index: number) {
  patchQuestion(index, { blankAnswers: [...questions.value[index].blankAnswers, ''] })
}

function removeBlank(index: number, blankIdx: number) {
  const q = questions.value[index]
  if (q.blankAnswers.length <= 1) return
  patchQuestion(index, { blankAnswers: q.blankAnswers.filter((_, i) => i !== blankIdx) })
}

function addTestCase(index: number) {
  const q = questions.value[index]
  const cases = [
    ...q.testCases,
    { id: `t${q.testCases.length + 1}`, label: `用例 ${q.testCases.length + 1}`, expected: '' },
  ]
  patchQuestion(index, { testCases: cases })
}

function updateTestCase(index: number, caseIdx: number, patch: Partial<ComposerTestCase>) {
  const testCases = questions.value[index].testCases.map((c, i) =>
    i === caseIdx ? { ...c, ...patch } : c,
  )
  patchQuestion(index, { testCases })
}

function removeTestCase(index: number, caseIdx: number) {
  const q = questions.value[index]
  if (q.testCases.length <= 1) return
  patchQuestion(index, { testCases: q.testCases.filter((_, i) => i !== caseIdx) })
}

function importFromBank(item: CodingBankItem) {
  const q = createComposerQuestion('coding', item.knowledge_key || props.defaultKnowledgeKey)
  q.stem = item.stem
  q.starterCode = item.starter_code
  q.runMode = (item.run_mode as 'stdout' | 'expression') || 'stdout'
  q.hint = item.hint || ''
  q.testCases = (item.test_cases ?? []).map((tc) => ({ ...tc })) as ComposerTestCase[]
  if (!q.testCases.length) q.testCases = [{ id: 't1', label: '样例 1', expected: '' }]
  questions.value = [...questions.value, q]
  showBank.value = false
  editingUid.value = q.uid
  message.success(`已添加编程题「${item.id}」`)
}

function previewText(q: ComposerQuestion) {
  return q.stem?.trim() || '（未填写题干）'
}

onMounted(async () => {
  try {
    bankItems.value = await fetchCodingQuestionBank()
  } catch {
    bankItems.value = []
  }
})
</script>

<template>
  <section class="composer" aria-label="题目编辑器">
    <header class="composer__head">
      <strong>试卷题目（{{ questions.length }} 题）</strong>
      <div class="composer__add">
        <n-button
          v-for="type in addTypes"
          :key="type"
          size="small"
          secondary
          @click="addQuestion(type)"
        >
          + {{ QUESTION_TYPE_LABELS[type] }}
        </n-button>
        <n-button size="small" quaternary @click="showBank = !showBank">从题库添加</n-button>
      </div>
    </header>

    <div v-if="showBank" class="composer__bank">
      <p v-if="!bankItems.length">题库加载中或暂无题目</p>
      <button
        v-for="item in bankItems"
        :key="item.id"
        type="button"
        class="composer__bank-item"
        @click="importFromBank(item)"
      >
        <strong>{{ item.id }}</strong>
        <span>{{ item.stem.slice(0, 48) }}…</span>
      </button>
    </div>

    <p v-if="!questions.length" class="composer__empty">
      尚未添加题目。可在上方按题型添加，或使用左侧「AI 批量生成」。
    </p>

    <article v-for="(q, index) in questions" :key="q.uid" class="composer__item">
      <header class="composer__item-head">
        <span class="composer__badge" :class="`composer__badge--${q.type}`">
          Q{{ index + 1 }} · {{ QUESTION_TYPE_LABELS[q.type] }} · {{ q.score }} 分
        </span>
        <div class="composer__ops">
          <n-button quaternary size="tiny" :disabled="index === 0" @click="moveQuestion(index, -1)">↑</n-button>
          <n-button
            quaternary
            size="tiny"
            :disabled="index === questions.length - 1"
            @click="moveQuestion(index, 1)"
          >
            ↓
          </n-button>
          <n-button quaternary size="tiny" @click="duplicateQuestion(index)">复制</n-button>
          <n-button quaternary size="tiny" @click="editingUid = editingUid === q.uid ? null : q.uid">
            {{ editingUid === q.uid ? '收起' : '编辑' }}
          </n-button>
          <n-button quaternary size="tiny" type="error" @click="removeQuestion(index)">删除</n-button>
        </div>
      </header>

      <p class="composer__preview">{{ previewText(q) }}</p>

      <div v-if="editingUid === q.uid" class="composer__form">
        <label class="composer__field">
          <span>题干</span>
          <n-input
            :value="q.stem"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 6 }"
            placeholder="请输入题干内容"
            @update:value="(v) => patchQuestion(index, { stem: v })"
          />
        </label>

        <div class="composer__meta-grid">
          <label class="composer__field">
            <span>关联知识点</span>
            <n-select
              :value="q.knowledgeKey ?? null"
              :options="knowledgeOptions"
              clearable
              filterable
              placeholder="选择知识点"
              @update:value="(v) => patchQuestion(index, { knowledgeKey: v ?? undefined })"
            />
          </label>
          <label class="composer__field composer__field--narrow">
            <span>分值</span>
            <n-input-number
              :value="q.score"
              :min="0"
              :max="100"
              @update:value="(v) => patchQuestion(index, { score: Number(v ?? 0) })"
            />
          </label>
        </div>

        <label class="composer__field">
          <span>难度：{{ q.difficulty }}</span>
          <n-slider
            :value="q.difficulty"
            :min="0"
            :max="100"
            :step="1"
            @update:value="(v) => patchQuestion(index, { difficulty: Number(v) })"
          />
        </label>

        <!-- 选择类题型 -->
        <template v-if="q.type === 'single' || q.type === 'multiple' || q.type === 'true_false'">
          <div class="composer__options">
            <div
              v-for="(_, optIdx) in q.options"
              :key="optIdx"
              class="composer__option"
            >
              <button
                type="button"
                class="composer__mark"
                :class="{
                  'composer__mark--on':
                    q.type === 'multiple'
                      ? q.correctIndexes.includes(optIdx)
                      : q.correctIndex === optIdx,
                  'composer__mark--round': q.type !== 'multiple',
                }"
                :title="q.type === 'multiple' ? '标记为正确项' : '标记为正确答案'"
                @click="
                  q.type === 'multiple'
                    ? toggleMultiCorrect(index, optIdx)
                    : patchQuestion(index, { correctIndex: optIdx })
                "
              >
                {{ String.fromCharCode(65 + optIdx) }}
              </button>
              <n-input
                :value="q.options[optIdx]"
                :placeholder="`选项 ${String.fromCharCode(65 + optIdx)}`"
                :disabled="q.type === 'true_false'"
                @update:value="(v) => updateOption(index, optIdx, v)"
              />
              <n-button
                v-if="q.type !== 'true_false'"
                quaternary
                size="tiny"
                :disabled="q.options.length <= 2"
                @click="removeOption(index, optIdx)"
              >
                删
              </n-button>
            </div>
            <n-button
              v-if="q.type !== 'true_false'"
              size="tiny"
              secondary
              class="composer__add-option"
              @click="addOption(index)"
            >
              + 添加选项
            </n-button>
            <p class="composer__hint">
              {{ q.type === 'multiple' ? '点击左侧字母标记多个正确项' : '点击左侧字母标记唯一正确答案' }}
            </p>
          </div>
        </template>

        <!-- 填空题 -->
        <template v-else-if="q.type === 'fill_blank'">
          <div class="composer__blanks">
            <span class="composer__sub">空位答案（按顺序）</span>
            <div v-for="(_, blankIdx) in q.blankAnswers" :key="blankIdx" class="composer__blank">
              <span class="composer__blank-no">空 {{ blankIdx + 1 }}</span>
              <n-input
                :value="q.blankAnswers[blankIdx]"
                placeholder="该空位的标准答案"
                @update:value="(v) => updateBlank(index, blankIdx, v)"
              />
              <n-button
                quaternary
                size="tiny"
                :disabled="q.blankAnswers.length <= 1"
                @click="removeBlank(index, blankIdx)"
              >
                删
              </n-button>
            </div>
            <n-button size="tiny" secondary @click="addBlank(index)">+ 添加空位</n-button>
          </div>
        </template>

        <!-- 简答题 -->
        <template v-else-if="q.type === 'short_answer'">
          <label class="composer__field">
            <span>参考答案</span>
            <n-input
              :value="q.referenceAnswer"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 6 }"
              placeholder="用于教师评阅的参考答案"
              @update:value="(v) => patchQuestion(index, { referenceAnswer: v })"
            />
          </label>
        </template>

        <!-- 编程题 -->
        <template v-else-if="q.type === 'coding'">
          <label class="composer__field">
            <span>Starter Code</span>
            <n-input
              :value="q.starterCode"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 12 }"
              @update:value="(v) => patchQuestion(index, { starterCode: v })"
            />
          </label>
          <div class="composer__meta-grid">
            <label class="composer__field">
              <span>运行模式</span>
              <n-select
                :value="q.runMode"
                :options="[
                  { label: '标准输出 stdout', value: 'stdout' },
                  { label: '表达式 expression', value: 'expression' },
                ]"
                @update:value="(v) => patchQuestion(index, { runMode: v as 'stdout' | 'expression' })"
              />
            </label>
            <label class="composer__field">
              <span>提示</span>
              <n-input
                :value="q.hint"
                placeholder="可选提示"
                @update:value="(v) => patchQuestion(index, { hint: v })"
              />
            </label>
          </div>
          <div class="composer__cases">
            <span class="composer__sub">测试用例</span>
            <article v-for="(tc, caseIdx) in q.testCases" :key="tc.id" class="composer__case">
              <n-input
                :value="tc.label"
                placeholder="标签"
                @update:value="(v) => updateTestCase(index, caseIdx, { label: v })"
              />
              <n-input
                :value="tc.setup || ''"
                placeholder="setup（可选）"
                @update:value="(v) => updateTestCase(index, caseIdx, { setup: v || undefined })"
              />
              <n-input
                :value="tc.expected"
                placeholder="期望输出"
                @update:value="(v) => updateTestCase(index, caseIdx, { expected: v })"
              />
              <n-button
                quaternary
                size="tiny"
                :disabled="q.testCases.length <= 1"
                @click="removeTestCase(index, caseIdx)"
              >
                删
              </n-button>
            </article>
            <n-button size="tiny" secondary @click="addTestCase(index)">+ 添加用例</n-button>
          </div>
        </template>

        <label class="composer__field">
          <span>解析（可选）</span>
          <n-input
            :value="q.analysis"
            type="textarea"
            :autosize="{ minRows: 1, maxRows: 4 }"
            placeholder="答案解析，学生作答后可见"
            @update:value="(v) => patchQuestion(index, { analysis: v })"
          />
        </label>
      </div>
    </article>
  </section>
</template>

<style scoped>
.composer {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.composer__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
  color: rgba(255, 247, 237, 0.9);
  font-size: 0.92rem;
}

.composer__add {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.composer__empty {
  margin: 0;
  padding: 1.25rem;
  border: 1px dashed rgba(251, 146, 60, 0.28);
  border-radius: 12px;
  color: rgba(221, 230, 239, 0.6);
  font-size: 0.85rem;
  text-align: center;
}

.composer__bank {
  display: grid;
  gap: 0.35rem;
  padding: 0.65rem;
  border-radius: 10px;
  border: 1px solid rgba(130, 212, 255, 0.14);
  background: rgba(5, 18, 30, 0.55);
}

.composer__bank-item {
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

.composer__bank-item strong {
  color: #fb923c;
  font-size: 0.78rem;
}

.composer__item {
  padding: 0.85rem 0.9rem;
  border-radius: 12px;
  border: 1px solid rgba(130, 212, 255, 0.12);
  background: rgba(5, 18, 30, 0.45);
}

.composer__item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.4rem;
  flex-wrap: wrap;
}

.composer__badge {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  border: 1px solid rgba(251, 146, 60, 0.4);
  color: #fdba74;
  font-size: 0.74rem;
  font-weight: 700;
}

.composer__badge--coding {
  border-color: rgba(56, 189, 248, 0.45);
  color: #7dd3fc;
}

.composer__badge--multiple {
  border-color: rgba(192, 132, 252, 0.45);
  color: #c084fc;
}

.composer__badge--fill_blank,
.composer__badge--short_answer {
  border-color: rgba(251, 191, 36, 0.42);
  color: #fcd34d;
}

.composer__ops {
  display: flex;
  flex-wrap: wrap;
  gap: 0.15rem;
}

.composer__preview {
  margin: 0;
  color: rgba(226, 232, 240, 0.88);
  font-size: 0.86rem;
  line-height: 1.5;
}

.composer__form {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid rgba(130, 212, 255, 0.1);
}

.composer__field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  color: rgba(221, 230, 239, 0.7);
  font-size: 0.78rem;
}

.composer__meta-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 120px;
  gap: 0.65rem;
}

.composer__field--narrow {
  max-width: 160px;
}

.composer__options,
.composer__blanks,
.composer__cases {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.composer__sub {
  color: rgba(255, 237, 213, 0.72);
  font-size: 0.78rem;
}

.composer__option {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.4rem;
}

.composer__mark {
  width: 30px;
  height: 30px;
  border: 1px solid rgba(130, 212, 255, 0.3);
  border-radius: 8px;
  background: rgba(3, 12, 20, 0.6);
  color: rgba(226, 232, 240, 0.75);
  font-weight: 700;
  cursor: pointer;
}

.composer__mark--round {
  border-radius: 50%;
}

.composer__mark--on {
  border-color: #fbbf24;
  background: rgba(251, 191, 36, 0.18);
  color: #fcd34d;
}

.composer__add-option {
  align-self: flex-start;
}

.composer__hint {
  margin: 0;
  color: rgba(221, 230, 239, 0.45);
  font-size: 0.72rem;
}

.composer__blank {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.4rem;
}

.composer__blank-no {
  color: rgba(221, 230, 239, 0.6);
  font-size: 0.74rem;
}

.composer__case {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr auto;
  gap: 0.35rem;
  align-items: center;
}

@media (max-width: 720px) {
  .composer__meta-grid {
    grid-template-columns: 1fr;
  }

  .composer__case {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
