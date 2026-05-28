<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NButton, NTag, useMessage } from 'naive-ui'
import {
  fetchStudentTrialQuestions,
  type StudentTrialQuestionsResult,
} from '../../api/studentTrials'
import { submitAssignmentAnswer, type TeacherAssignmentItem } from '../../api/studentAssignments'
import { showIncentiveFeedback } from '../../utils/incentiveFeedback'

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
      if (item.status === 'completed' && item.selected_index !== null) {
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

async function submit(item: TeacherAssignmentItem) {
  const selected = selections.value[item.id]
  if (selected === null || selected === undefined || submittingId.value) return
  submittingId.value = item.id
  try {
    const result = await submitAssignmentAnswer(item.id, selected, elapsedSec(item.id))
    feedback.value[item.id] = { correct: result.correct, correctIndex: result.correct_index }
    showIncentiveFeedback(message, result.incentive ?? result.trial_complete?.incentive)
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

onMounted(() => {
  void loadQuestions()
})
</script>

<template>
  <section class="trial-mcq" aria-label="试炼题目">
    <header class="trial-mcq__head">
      <div>
        <button type="button" class="trial-mcq__back" @click="emit('back')">← 返回</button>
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

    <p v-if="loading" class="trial-mcq__empty">加载题目中…</p>
    <p v-else-if="errorMessage" class="trial-mcq__empty trial-mcq__empty--error">
      {{ errorMessage }}
      <n-button secondary size="small" @click="loadQuestions()">重试</n-button>
    </p>
    <p v-else-if="!payload?.items.length" class="trial-mcq__empty">该试炼暂无题目，请稍后再试。</p>

    <article
      v-for="item in payload?.items ?? []"
      :key="item.id"
      class="trial-mcq__card"
      :class="{ 'trial-mcq__card--done': item.status === 'completed' || feedback[item.id] }"
    >
      <div class="trial-mcq__meta">
        <n-tag size="small" :bordered="false">{{ item.knowledge_label }}</n-tag>
        <span>第 {{ item.sort_order + 1 }} 题</span>
      </div>
      <h3>{{ item.stem }}</h3>
      <ul class="trial-mcq__options">
        <li v-for="(option, index) in item.options" :key="index">
          <button
            type="button"
            class="option-btn"
            :class="{
              'option-btn--selected': selections[item.id] === index,
              'option-btn--correct': feedback[item.id] && index === feedback[item.id].correctIndex,
              'option-btn--wrong':
                feedback[item.id] &&
                !feedback[item.id].correct &&
                selections[item.id] === index &&
                index !== feedback[item.id].correctIndex,
            }"
            :disabled="Boolean(submittingId) || Boolean(feedback[item.id]) || isDone"
            @click="selectOption(item.id, index)"
          >
            <span>{{ String.fromCharCode(65 + index) }}</span>
            <span>{{ option }}</span>
          </button>
        </li>
      </ul>
      <footer v-if="!isDone">
        <n-button
          type="primary"
          size="small"
          :loading="submittingId === item.id"
          :disabled="selections[item.id] === null || selections[item.id] === undefined || Boolean(feedback[item.id])"
          @click="submit(item)"
        >
          提交本题
        </n-button>
      </footer>
    </article>
  </section>
</template>

<style scoped>
.trial-mcq {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-height: 0;
}

.trial-mcq__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.trial-mcq__back {
  border: none;
  background: none;
  color: var(--plex-accent, #10f0c0);
  cursor: pointer;
  padding: 0;
  margin-bottom: 0.35rem;
  font-size: 0.85rem;
}

.trial-mcq__head h2 {
  margin: 0;
  font-size: 1.15rem;
}

.trial-mcq__head p {
  margin: 0.25rem 0 0;
  color: var(--plex-text-muted, #8ea3b8);
  font-size: 0.85rem;
}

.trial-mcq__empty {
  color: var(--plex-text-muted, #8ea3b8);
  text-align: center;
  padding: 2rem 1rem;
}

.trial-mcq__empty--error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.trial-mcq__card {
  border: 1px solid rgba(16, 240, 192, 0.15);
  border-radius: 12px;
  padding: 1rem 1.1rem;
  background: rgba(11, 22, 40, 0.72);
}

.trial-mcq__card--done {
  opacity: 0.92;
}

.trial-mcq__meta {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin-bottom: 0.5rem;
  font-size: 0.8rem;
  color: var(--plex-text-muted, #8ea3b8);
}

.trial-mcq__card h3 {
  margin: 0 0 0.75rem;
  font-size: 1rem;
  line-height: 1.5;
}

.trial-mcq__options {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.option-btn {
  width: 100%;
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  text-align: left;
  border: 1px solid rgba(16, 240, 192, 0.12);
  border-radius: 10px;
  padding: 0.65rem 0.75rem;
  background: rgba(13, 26, 45, 0.8);
  color: inherit;
  cursor: pointer;
}

.option-btn--selected {
  border-color: rgba(16, 240, 192, 0.45);
}

.option-btn--correct {
  border-color: rgba(16, 240, 192, 0.65);
  background: rgba(16, 240, 192, 0.08);
}

.option-btn--wrong {
  border-color: rgba(232, 128, 128, 0.65);
  background: rgba(232, 128, 128, 0.08);
}

.option-btn:disabled {
  cursor: default;
}

.option-btn span:first-child {
  font-weight: 700;
  color: var(--plex-accent, #10f0c0);
  min-width: 1.25rem;
}

.trial-mcq__card footer {
  margin-top: 0.75rem;
}
</style>
