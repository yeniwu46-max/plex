<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NButton, NModal, NSpin } from 'naive-ui'
import {
  fetchEmergencyMissionExplanation,
  type EmergencyMissionArchiveRecord,
} from '../../api/emergencyMission'

const props = defineProps<{
  show: boolean
  record: EmergencyMissionArchiveRecord | null
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
}>()

const loading = ref(false)
const errorMessage = ref('')
const explanation = ref('')

const visible = computed({
  get: () => props.show,
  set: (value: boolean) => emit('update:show', value),
})

function formatOptionLabel(index: number | null | undefined) {
  if (index === null || index === undefined || index < 0) return '未作答'
  return String.fromCharCode(65 + index)
}

async function loadExplanation() {
  if (!props.record) return
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await fetchEmergencyMissionExplanation(props.record.id)
    explanation.value = result.summary
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'AI 解析加载失败'
    explanation.value = ''
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.show, props.record?.id],
  ([open]) => {
    if (open && props.record) {
      explanation.value = ''
      void loadExplanation()
    }
  },
)
</script>

<template>
  <n-modal
    v-model:show="visible"
    preset="card"
    class="emergency-growth-modal"
    :style="{ width: 'min(560px, 92vw)' }"
    title="补给站紧急任务 · 详情"
    :mask-closable="true"
  >
    <template v-if="record">
      <header class="emergency-growth-modal__meta">
        <span>{{ record.focus_label }}</span>
        <span>{{ record.date?.slice(0, 10) || '今日' }}</span>
        <span>{{ record.all_correct ? '全对' : `答对 ${record.correct_count}/${record.total_count}` }}</span>
      </header>

      <section class="emergency-growth-modal__questions" aria-label="作答记录">
        <article v-for="q in record.questions" :key="q.id" class="emergency-growth-modal__q">
          <h4>{{ q.sort_order }}. {{ q.stem }}</h4>
          <ul>
            <li v-for="(opt, idx) in q.options" :key="idx">
              <span
                :class="{
                  'is-picked': q.selected_index === idx,
                  'is-right': q.correct_index === idx,
                  'is-wrong': q.selected_index === idx && q.correct_index !== idx,
                }"
              >
                {{ String.fromCharCode(65 + idx) }}. {{ opt }}
              </span>
            </li>
          </ul>
          <p class="emergency-growth-modal__verdict">
            你的选择：{{ formatOptionLabel(q.selected_index) }}
            · 正确答案：{{ formatOptionLabel(q.correct_index) }}
            · {{ q.is_correct ? '回答正确' : '回答错误' }}
          </p>
        </article>
      </section>

      <section class="emergency-growth-modal__ai" aria-label="AI 解析">
        <h3>AI 解析</h3>
        <n-spin v-if="loading" size="small" />
        <p v-else-if="errorMessage" class="emergency-growth-modal__error">
          {{ errorMessage }}
          <n-button size="tiny" quaternary @click="loadExplanation">重试</n-button>
        </p>
        <p v-else class="emergency-growth-modal__summary">{{ explanation }}</p>
      </section>
    </template>
  </n-modal>
</template>

<style scoped>
.emergency-growth-modal__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 0.85rem;
  margin-bottom: 0.85rem;
  color: rgba(142, 163, 184, 0.95);
  font-size: 0.82rem;
}

.emergency-growth-modal__q {
  margin-bottom: 0.85rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.emergency-growth-modal__q h4 {
  margin: 0 0 0.45rem;
  font-size: 0.9rem;
  line-height: 1.45;
  color: rgba(255, 255, 255, 0.92);
}

.emergency-growth-modal__q ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.emergency-growth-modal__q li span {
  display: block;
  padding: 0.35rem 0.45rem;
  margin-bottom: 0.25rem;
  border-radius: 6px;
  font-size: 0.84rem;
  color: rgba(255, 255, 255, 0.86);
}

.emergency-growth-modal__q li span.is-picked {
  border: 1px solid rgba(16, 240, 192, 0.45);
  background: rgba(16, 240, 192, 0.08);
}

.emergency-growth-modal__q li span.is-right {
  border-color: rgba(16, 240, 192, 0.75);
}

.emergency-growth-modal__q li span.is-wrong {
  border-color: rgba(232, 128, 128, 0.75);
  background: rgba(232, 128, 128, 0.08);
}

.emergency-growth-modal__verdict {
  margin: 0.4rem 0 0;
  font-size: 0.78rem;
  color: rgba(142, 163, 184, 0.95);
}

.emergency-growth-modal__ai {
  margin-top: 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid rgba(16, 240, 192, 0.15);
}

.emergency-growth-modal__ai h3 {
  margin: 0 0 0.55rem;
  color: #39e6c7;
  font-size: 0.88rem;
}

.emergency-growth-modal__summary {
  margin: 0;
  color: rgba(237, 247, 255, 0.9);
  font-size: 0.86rem;
  line-height: 1.6;
  white-space: pre-wrap;
}

.emergency-growth-modal__error {
  margin: 0;
  color: #ffb4b4;
  font-size: 0.84rem;
}
</style>

<style>
.emergency-growth-modal.n-modal {
  --n-color: #0b1628;
  --n-text-color: #e8fff8;
  --n-title-text-color: #e8fff8;
  --n-border-color: rgba(16, 240, 192, 0.25);
}
</style>
