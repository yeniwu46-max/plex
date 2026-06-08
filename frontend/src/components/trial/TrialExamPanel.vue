<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NButton, NTag, useMessage } from 'naive-ui'
import {
  completeStudentTrial,
  fetchStudentTrialQuestions,
  type StudentTrialQuestionsResult,
} from '../../api/studentTrials'
import {
  submitAssignmentAnswer,
  type TeacherAssignmentItem,
} from '../../api/studentAssignments'
import PythonTrialWorkspace from './PythonTrialWorkspace.vue'
import type { PythonTrialQuestion } from '../../data/pythonTrialQuestions'
import { showIncentiveFeedback } from '../../utils/incentiveFeedback'
import { advanceDailyQuest } from '../../api/studentOverview'

const props = defineProps<{
  trialId: number
  trialTitle?: string
}>()

const emit = defineEmits<{
  completed: []
  back: []
}>()

const message = useMessage()
const loading = ref(true)
const errorMessage = ref('')
const payload = ref<StudentTrialQuestionsResult | null>(null)
const selections = ref<Record<number, number | null>>({})
const submittingId = ref<number | null>(null)
const feedback = ref<Record<number, { correct: boolean; correctIndex: number }>>({})
const questionStartedAt = ref<Record<number, number>>({})
const activeCodingId = ref<number | null>(null)

function markQuestionStart(questionId: number) {
  if (!questionStartedAt.value[questionId]) {
    questionStartedAt.value[questionId] = Date.now()
  }
}

function elapsedSec(questionId: number): number {
  const started = questionStartedAt.value[questionId]
  if (!started) return 0
  return Math.max(1, Math.round((Date.now() - started) / 1000))
}

const title = computed(() => props.trialTitle || payload.value?.trial_title || '班级试炼')
const isDone = computed(() => payload.value?.my_status === 'completed')
const canSubmitTrial = computed(() => {
  const p = payload.value
  if (!p || isDone.value) return false
  return p.answered_count >= p.question_count && p.question_count > 0
})
const submittingTrial = ref(false)

const activeCodingItem = computed(() =>
  payload.value?.items.find((item) => item.id === activeCodingId.value) ?? null,
)

function isCoding(item: TeacherAssignmentItem) {
  return item.question_type === 'coding'
}

function toPythonQuestion(item: TeacherAssignmentItem): PythonTrialQuestion {
  const meta = item.coding_meta ?? {
    starter_code: '# 在此编写代码\n',
    test_cases: [],
    run_mode: 'stdout' as const,
    hint: '',
    constraints: [],
    examples: [],
  }
  return {
    id: String(item.id),
    title: item.stem.slice(0, 40),
    topic: item.knowledge_label,
    difficulty: '基础',
    rewardXp: 20,
    durationMin: 10,
    tags: [],
    description: item.stem,
    constraints: meta.constraints || [],
    examples: meta.examples || [],
    testCases: (meta.test_cases || []).map((tc) => ({
      id: tc.id,
      label: tc.label,
      setup: tc.setup,
      invoke: tc.invoke,
      expected: tc.expected,
    })),
    starterCode: meta.starter_code || '# 在此编写代码\n',
    runMode: meta.run_mode || 'stdout',
    hint: meta.hint || '',
  }
}

async function loadQuestions() {
  loading.value = true
  errorMessage.value = ''
  try {
    payload.value = await fetchStudentTrialQuestions(props.trialId)
    payload.value.items.forEach((item) => {
      if (selections.value[item.id] === undefined) {
        selections.value[item.id] = item.selected_index ?? null
      }
      if (item.status === 'pending') {
        markQuestionStart(item.id)
      }
      if (item.status === 'completed' && !isCoding(item) && item.selected_index !== null) {
        feedback.value[item.id] = {
          correct: Boolean(item.is_correct),
          correctIndex: item.is_correct ? item.selected_index : item.selected_index,
        }
      }
    })
  } catch (error) {
    payload.value = null
    errorMessage.value = error instanceof Error ? error.message : '加载题目失败'
  } finally {
    loading.value = false
  }
}

function selectOption(questionId: number, index: number) {
  if (submittingId.value || feedback.value[questionId] || isDone.value) return
  selections.value[questionId] = index
}

async function submitMcq(item: TeacherAssignmentItem) {
  const selected = selections.value[item.id]
  if (selected === null || selected === undefined || submittingId.value) return
  submittingId.value = item.id
  try {
    const result = await submitAssignmentAnswer(item.id, selected, elapsedSec(item.id))
    feedback.value[item.id] = { correct: result.correct, correctIndex: result.correct_index }
    showIncentiveFeedback(message, result.incentive ?? result.trial_complete?.incentive)
    advanceDailyQuest('fragment-repair').catch(() => undefined)
    if (result.trial_complete) {
      message.success(`试炼已完成，得分 ${result.trial_complete.participation.score}`)
      emit('completed')
    } else {
      message.success(result.correct ? '回答正确' : '回答有误，请继续完成其他题目')
    }
    await loadQuestions()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '提交失败')
  } finally {
    submittingId.value = null
  }
}

async function onCodingPassed() {
  message.success('编程题已通过')
  activeCodingId.value = null
  await loadQuestions()
  if (payload.value?.my_status === 'completed') {
    emit('completed')
  }
}

async function submitTrial() {
  if (!canSubmitTrial.value || submittingTrial.value) return
  submittingTrial.value = true
  try {
    const result = await completeStudentTrial(props.trialId, payload.value?.score)
    showIncentiveFeedback(message, result.incentive)
    message.success(`试炼「${result.trial.title}」已完成，得分 ${result.participation.score}`)
    emit('completed')
  } catch (error) {
    message.error(error instanceof Error ? error.message : '提交试炼失败')
    await loadQuestions()
  } finally {
    submittingTrial.value = false
  }
}

onMounted(() => {
  void loadQuestions()
})
</script>

<template>
  <section class="trial-exam" aria-label="试炼试卷">
    <template v-if="activeCodingItem">
      <PythonTrialWorkspace
        :question="toPythonQuestion(activeCodingItem)"
        embedded
        back-label="返回试卷"
        :trial-question-id="activeCodingItem.id"
        @back="activeCodingId = null"
        @passed="onCodingPassed"
      />
    </template>

    <template v-else>
      <header class="trial-exam__head">
        <div>
          <button type="button" class="trial-exam__back" @click="emit('back')">← 返回</button>
          <h2>{{ title }}</h2>
          <p v-if="payload">
            已答 {{ payload.answered_count }}/{{ payload.question_count }} 题
            <template v-if="payload.my_status === 'completed'"> · 得分 {{ payload.score }}</template>
          </p>
        </div>
        <n-tag v-if="payload?.pending_count" type="warning" round :bordered="false">
          待完成 {{ payload.pending_count }}
        </n-tag>
        <n-tag v-else-if="isDone" type="success" round :bordered="false">已完成</n-tag>
      </header>

      <p v-if="loading" class="trial-exam__empty">加载题目中…</p>
      <p v-else-if="errorMessage" class="trial-exam__empty trial-exam__empty--error">
        {{ errorMessage }}
        <n-button secondary size="small" @click="loadQuestions()">重试</n-button>
      </p>
      <p v-else-if="!payload?.items.length" class="trial-exam__empty">该试炼暂无题目，请稍后再试。</p>

      <ol v-else class="trial-exam__list">
        <li v-for="item in payload.items" :key="item.id" class="trial-exam__item">
          <header>
            <span>Q{{ item.sort_order }}</span>
            <n-tag size="small" :bordered="false">{{ isCoding(item) ? '编程题' : '选择题' }}</n-tag>
            <n-tag v-if="item.status === 'completed'" size="small" type="success" :bordered="false">已完成</n-tag>
          </header>
          <p class="trial-exam__stem">{{ item.stem }}</p>

          <template v-if="isCoding(item)">
            <p v-if="item.code_passed" class="trial-exam__result trial-exam__result--ok">已通过全部测试</p>
            <p v-else-if="item.status === 'completed'" class="trial-exam__result trial-exam__result--fail">未通过</p>
            <n-button
              v-if="item.status !== 'completed' && !isDone"
              type="primary"
              size="small"
              @click="activeCodingId = item.id"
            >
              打开代码编辑器
            </n-button>
          </template>

          <template v-else>
            <div class="trial-exam__options">
              <button
                v-for="(opt, idx) in item.options"
                :key="idx"
                type="button"
                class="trial-exam__option"
                :class="{
                  'trial-exam__option--selected': selections[item.id] === idx,
                  'trial-exam__option--correct': feedback[item.id]?.correct && feedback[item.id]?.correctIndex === idx,
                  'trial-exam__option--wrong':
                    feedback[item.id] && !feedback[item.id]?.correct && selections[item.id] === idx,
                }"
                :disabled="Boolean(feedback[item.id]) || isDone || item.status === 'completed'"
                @click="selectOption(item.id, idx)"
              >
                <span>{{ String.fromCharCode(65 + idx) }}</span>
                {{ opt }}
              </button>
            </div>
            <n-button
              v-if="!feedback[item.id] && item.status !== 'completed' && !isDone"
              type="primary"
              size="small"
              :loading="submittingId === item.id"
              :disabled="selections[item.id] === null || selections[item.id] === undefined"
              @click="submitMcq(item)"
            >
              提交本题
            </n-button>
            <p v-else-if="feedback[item.id]" class="trial-exam__result" :class="feedback[item.id]?.correct ? 'trial-exam__result--ok' : 'trial-exam__result--fail'">
              {{ feedback[item.id]?.correct ? '回答正确' : '回答错误' }}
            </p>
          </template>
        </li>
      </ol>

      <footer v-if="canSubmitTrial" class="trial-exam__footer">
        <n-button type="primary" :loading="submittingTrial" @click="submitTrial">提交试炼并结算</n-button>
      </footer>
    </template>
  </section>
</template>

<style scoped>
.trial-exam {
  margin: 0 var(--plex-page-gutter-x, 1.25rem);
  padding: 1.25rem;
  border-radius: 16px;
  background: rgba(5, 17, 29, 0.72);
  border: 1px solid rgba(74, 222, 128, 0.12);
}

.trial-exam__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.trial-exam__back {
  border: none;
  background: none;
  color: rgba(226, 232, 240, 0.65);
  cursor: pointer;
  padding: 0;
  margin-bottom: 0.35rem;
}

.trial-exam__head h2 {
  margin: 0;
  color: #f8fafc;
  font-size: 1.15rem;
}

.trial-exam__head p {
  margin: 0.35rem 0 0;
  color: rgba(226, 232, 240, 0.65);
  font-size: 0.85rem;
}

.trial-exam__empty {
  color: rgba(226, 232, 240, 0.65);
  text-align: center;
  padding: 2rem 0;
}

.trial-exam__empty--error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.trial-exam__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.trial-exam__item {
  padding: 1rem;
  border-radius: 12px;
  border: 1px solid rgba(74, 222, 128, 0.1);
  background: rgba(3, 12, 20, 0.55);
}

.trial-exam__item header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  color: rgba(226, 232, 240, 0.55);
  font-size: 0.78rem;
}

.trial-exam__stem {
  margin: 0 0 0.75rem;
  color: rgba(248, 250, 252, 0.92);
  line-height: 1.6;
  white-space: pre-wrap;
}

.trial-exam__options {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-bottom: 0.75rem;
}

.trial-exam__option {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  padding: 0.55rem 0.75rem;
  border-radius: 8px;
  border: 1px solid rgba(74, 222, 128, 0.12);
  background: rgba(5, 17, 29, 0.5);
  color: rgba(226, 232, 240, 0.88);
  cursor: pointer;
  text-align: left;
}

.trial-exam__option span {
  color: #4ade80;
  font-weight: 700;
}

.trial-exam__option--selected {
  border-color: rgba(74, 222, 128, 0.45);
}

.trial-exam__option--correct {
  border-color: rgba(74, 222, 128, 0.65);
  background: rgba(74, 222, 128, 0.08);
}

.trial-exam__option--wrong {
  border-color: rgba(248, 113, 113, 0.55);
  background: rgba(248, 113, 113, 0.08);
}

.trial-exam__result {
  margin: 0.5rem 0 0;
  font-size: 0.85rem;
}

.trial-exam__result--ok {
  color: #4ade80;
}

.trial-exam__result--fail {
  color: #f87171;
}

.trial-exam__footer {
  margin-top: 1.25rem;
  display: flex;
  justify-content: flex-end;
}
</style>
