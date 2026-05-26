<script setup lang="ts">
import { ref, watch } from 'vue'
import { NButton } from 'naive-ui'
import { fetchStudentTrialHistory, type StudentTrialHistoryResult } from '../../api/teacherTrials'

const props = defineProps<{
  studentId: number
}>()

const loading = ref(false)
const errorMessage = ref('')
const history = ref<StudentTrialHistoryResult | null>(null)

const statusLabels: Record<string, string> = {
  joined: '进行中',
  completed: '已完成',
  abandoned: '已放弃',
}

async function loadHistory() {
  loading.value = true
  errorMessage.value = ''
  try {
    history.value = await fetchStudentTrialHistory(props.studentId)
  } catch (error) {
    history.value = null
    errorMessage.value = error instanceof Error ? error.message : '加载失败'
  } finally {
    loading.value = false
  }
}

watch(
  () => props.studentId,
  (id) => {
    if (id) void loadHistory()
  },
  { immediate: true },
)
</script>

<template>
  <section class="explorer-trial-panel" aria-label="试炼记录">
    <header v-if="history" class="explorer-trial-panel__summary">
      <div>
        <span>参与试炼</span>
        <strong>{{ history.summary.total }}</strong>
      </div>
      <div>
        <span>已完成</span>
        <strong>{{ history.summary.completed }}</strong>
      </div>
      <div>
        <span>平均分</span>
        <strong>{{ history.summary.avg_score }}</strong>
      </div>
    </header>

    <div v-if="loading" class="teacher-state-panel">正在加载试炼记录…</div>
    <div v-else-if="errorMessage" class="teacher-state-panel teacher-state-panel--error">
      <span>{{ errorMessage }}</span>
      <n-button secondary size="small" @click="loadHistory()">重试</n-button>
    </div>
    <p v-else-if="!history?.participations.length" class="explorer-trial-panel__empty">该 Explorer 尚无试炼参与记录。</p>

    <ul v-else class="explorer-trial-panel__list">
      <li v-for="item in history.participations" :key="item.id">
        <div>
          <h3>{{ item.trial.title }}</h3>
          <p>
            {{ statusLabels[item.status] ?? item.status }}
            · 难度 {{ item.trial.difficulty }}
            <template v-if="item.status === 'completed'"> · 得分 {{ item.score }}</template>
          </p>
        </div>
        <span class="explorer-trial-panel__badge">{{ item.trial.reward_points }} XP</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.explorer-trial-panel {
  display: grid;
  gap: 1rem;
}

.explorer-trial-panel__summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
}

.explorer-trial-panel__summary div {
  padding: 0.75rem 0.9rem;
  border-radius: 12px;
  border: 1px solid rgba(130, 212, 255, 0.12);
  background: rgba(4, 12, 20, 0.55);
}

.explorer-trial-panel__summary span {
  display: block;
  font-size: 0.78rem;
  color: var(--teacher-muted);
}

.explorer-trial-panel__summary strong {
  font-size: 1.25rem;
  color: var(--teacher-text);
}

.explorer-trial-panel__empty {
  margin: 0;
  color: var(--teacher-muted);
  font-size: 0.9rem;
}

.explorer-trial-panel__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.65rem;
}

.explorer-trial-panel__list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.85rem 1rem;
  border-radius: 14px;
  border: 1px solid rgba(130, 212, 255, 0.1);
  background: rgba(4, 12, 20, 0.45);
}

.explorer-trial-panel__list h3 {
  margin: 0 0 0.25rem;
  font-size: 0.95rem;
  color: var(--teacher-text);
}

.explorer-trial-panel__list p {
  margin: 0;
  font-size: 0.82rem;
  color: var(--teacher-muted);
}

.explorer-trial-panel__badge {
  flex-shrink: 0;
  padding: 0.25rem 0.65rem;
  border-radius: 999px;
  background: rgba(251, 146, 60, 0.14);
  color: var(--teacher-orange);
  font-size: 0.78rem;
  font-weight: 650;
}
</style>
