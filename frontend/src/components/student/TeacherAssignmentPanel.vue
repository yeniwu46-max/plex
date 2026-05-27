<script setup lang="ts">
import { ref, watch } from 'vue'
import { NButton, NTag, useMessage } from 'naive-ui'
import {
  submitAssignmentAnswer,
  type TeacherAssignmentItem,
  type TeacherAssignmentsResult,
} from '../../api/studentAssignments'
import type { DailyQuestTodayResult } from '../../api/studentOverview'
import { showIncentiveFeedback } from '../../utils/incentiveFeedback'

const props = defineProps<{
  assignments: TeacherAssignmentsResult
  loading?: boolean
}>()

const emit = defineEmits<{
  updated: [payload: { assignments: TeacherAssignmentsResult; daily: DailyQuestTodayResult | null }]
}>()

const message = useMessage()
const selections = ref<Record<number, number | null>>({})
const submittingId = ref<number | null>(null)
const feedback = ref<Record<number, { correct: boolean; correctIndex: number }>>({})

function initSelection(item: TeacherAssignmentItem) {
  if (selections.value[item.id] === undefined) {
    selections.value[item.id] = item.selected_index ?? null
  }
}

function selectOption(questionId: number, index: number) {
  if (submittingId.value || feedback.value[questionId]) return
  selections.value[questionId] = index
}

async function submit(item: TeacherAssignmentItem) {
  const selected = selections.value[item.id]
  if (selected === null || selected === undefined || submittingId.value) return
  submittingId.value = item.id
  try {
    const result = await submitAssignmentAnswer(item.id, selected)
    feedback.value[item.id] = { correct: result.correct, correctIndex: result.correct_index }
    showIncentiveFeedback(message, result.incentive)
    emit('updated', { assignments: result.assignments, daily: result.daily })
    message.success(result.correct ? '回答正确，已计入知识碎片修复' : '回答有误，可继续尝试其他题目')
  } catch (error) {
    message.error(error instanceof Error ? error.message : '提交失败')
  } finally {
    submittingId.value = null
  }
}

watch(
  () => props.assignments.items,
  (items) => {
    items.forEach(initSelection)
  },
  { immediate: true, deep: true },
)
</script>

<template>
  <section class="teacher-assign" aria-label="教师布置题目">
    <header class="teacher-assign__head">
      <div>
        <h2>教师布置 · 知识碎片</h2>
        <p>完成试炼配套题目，同步推进「修复知识碎片」委托</p>
      </div>
      <n-tag v-if="assignments.pending_count" type="warning" round :bordered="false">
        待完成 {{ assignments.pending_count }}
      </n-tag>
    </header>

    <p v-if="loading" class="teacher-assign__empty">加载题目中…</p>
    <p v-else-if="!assignments.items.length" class="teacher-assign__empty">
      暂无待完成题目。教师发布试炼后，题目会出现在这里。
    </p>

    <article
      v-for="item in assignments.items"
      :key="item.id"
      class="assign-card"
      :class="{ 'assign-card--done': item.status === 'completed' || feedback[item.id] }"
    >
      <div class="assign-card__meta">
        <n-tag size="small" :bordered="false">{{ item.knowledge_label }}</n-tag>
        <span>{{ item.trial_title }} · {{ item.teacher_name }}</span>
      </div>
      <h3>{{ item.stem }}</h3>
      <ul class="assign-card__options" role="list">
        <li v-for="(option, index) in item.options" :key="index">
          <button
            type="button"
            class="option-btn"
            :class="{
              'option-btn--selected': selections[item.id] === index,
              'option-btn--correct':
                feedback[item.id] && index === feedback[item.id].correctIndex,
              'option-btn--wrong':
                feedback[item.id] &&
                !feedback[item.id].correct &&
                selections[item.id] === index &&
                index !== feedback[item.id].correctIndex,
            }"
            :disabled="Boolean(submittingId) || Boolean(feedback[item.id])"
            @click="selectOption(item.id, index)"
          >
            <span class="option-btn__label">{{ String.fromCharCode(65 + index) }}</span>
            <span>{{ option }}</span>
          </button>
        </li>
      </ul>
      <footer class="assign-card__foot">
        <n-button
          type="primary"
          size="small"
          :loading="submittingId === item.id"
          :disabled="selections[item.id] === null || selections[item.id] === undefined || Boolean(feedback[item.id])"
          @click="submit(item)"
        >
          {{ feedback[item.id] ? (feedback[item.id].correct ? '已完成' : '已提交') : '提交答案' }}
        </n-button>
      </footer>
    </article>
  </section>
</template>

<style scoped>
.teacher-assign {
  margin-bottom: 1.25rem;
  padding: 1.1rem 1.15rem;
  border-radius: 16px;
  border: 1px solid rgba(16, 240, 192, 0.22);
  background: linear-gradient(145deg, rgba(11, 22, 40, 0.92), rgba(8, 14, 28, 0.88));
}

.teacher-assign__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.85rem;
}

.teacher-assign__head h2 {
  margin: 0;
  font-size: 1.05rem;
  color: #e8fff8;
}

.teacher-assign__head p {
  margin: 0.25rem 0 0;
  font-size: 0.82rem;
  color: rgba(142, 163, 184, 0.95);
}

.teacher-assign__empty {
  margin: 0;
  font-size: 0.86rem;
  color: rgba(142, 163, 184, 0.9);
}

.assign-card {
  padding: 0.9rem 0;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.assign-card:first-of-type {
  border-top: none;
  padding-top: 0;
}

.assign-card h3 {
  margin: 0.55rem 0 0.65rem;
  font-size: 0.95rem;
  line-height: 1.45;
  color: rgba(255, 255, 255, 0.92);
  font-weight: 600;
}

.assign-card__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.78rem;
  color: rgba(142, 163, 184, 0.95);
}

.assign-card__options {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.option-btn {
  width: 100%;
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  text-align: left;
  padding: 0.55rem 0.65rem;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(13, 26, 45, 0.75);
  color: rgba(255, 255, 255, 0.88);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.option-btn:hover:not(:disabled) {
  border-color: rgba(16, 240, 192, 0.45);
}

.option-btn--selected {
  border-color: rgba(16, 240, 192, 0.65);
  background: rgba(16, 240, 192, 0.1);
}

.option-btn--correct {
  border-color: rgba(16, 240, 192, 0.85);
  background: rgba(16, 240, 192, 0.16);
}

.option-btn--wrong {
  border-color: rgba(232, 128, 128, 0.75);
  background: rgba(232, 128, 128, 0.12);
}

.option-btn__label {
  flex-shrink: 0;
  width: 1.35rem;
  height: 1.35rem;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.08);
}

.assign-card__foot {
  margin-top: 0.65rem;
  display: flex;
  justify-content: flex-end;
}
</style>
