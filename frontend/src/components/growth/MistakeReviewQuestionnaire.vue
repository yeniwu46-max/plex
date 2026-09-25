<script setup lang="ts">
import { computed } from 'vue'
import type { StudentMistakeItem } from '../../api/studentMistakes'
import {
  REVIEW_ANSWER_OPTIONS,
  buildSm2ReviewQuestions,
  type ReviewAnswerValue,
} from '../../utils/sm2ReviewQuestionnaire'

const props = defineProps<{
  item: StudentMistakeItem
  modelValue: Record<string, ReviewAnswerValue | undefined>
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, ReviewAnswerValue | undefined>]
}>()

const questions = computed(() => buildSm2ReviewQuestions(props.item))

function setAnswer(questionId: string, value: ReviewAnswerValue) {
  emit('update:modelValue', { ...props.modelValue, [questionId]: value })
}
</script>

<template>
  <div class="review-questionnaire" :aria-label="`${item.knowledge_label || item.knowledge_key} 复习自测`">
    <p class="review-questionnaire__lead">请根据真实回忆作答，系统会据此更新 SM-2 复习计划。</p>
    <fieldset
      v-for="question in questions"
      :key="question.id"
      class="review-questionnaire__item"
    >
      <legend>{{ question.text }}</legend>
      <div class="review-questionnaire__options">
        <button
          v-for="option in REVIEW_ANSWER_OPTIONS"
          :key="`${question.id}-${option.value}`"
          type="button"
          class="review-questionnaire__option"
          :class="{ 'review-questionnaire__option--active': modelValue[question.id] === option.value }"
          :disabled="disabled"
          :aria-pressed="modelValue[question.id] === option.value"
          @click="setAnswer(question.id, option.value)"
        >
          {{ option.label }}
        </button>
      </div>
    </fieldset>
  </div>
</template>

<style scoped>
.review-questionnaire {
  display: grid;
  gap: 0.65rem;
}

.review-questionnaire__lead {
  margin: 0;
  color: #8da7b6;
  font-size: 0.78rem;
}

.review-questionnaire__item {
  margin: 0;
  padding: 0.65rem 0.75rem;
  border: 1px solid rgba(52, 230, 197, 0.12);
  border-radius: 10px;
  background: rgba(2, 10, 18, 0.45);
}

.review-questionnaire__item legend {
  padding: 0 0.15rem;
  color: #dcecf4;
  font-size: 0.82rem;
  line-height: 1.45;
}

.review-questionnaire__options {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-top: 0.45rem;
}

.review-questionnaire__option {
  padding: 0.35rem 0.65rem;
  border: 1px solid rgba(52, 230, 197, 0.22);
  border-radius: 999px;
  background: rgba(52, 230, 197, 0.04);
  color: #b9d4dc;
  font-size: 0.76rem;
  cursor: pointer;
}

.review-questionnaire__option:hover:not(:disabled),
.review-questionnaire__option--active {
  border-color: #34e6c5;
  background: rgba(52, 230, 197, 0.16);
  color: #effffd;
}

.review-questionnaire__option:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
