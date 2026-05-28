<script setup lang="ts">
import { ref, watch } from 'vue'
import { NButton, NTag } from 'naive-ui'
import {
  fetchStudentTrialAnswerBoard,
  type StudentTrialAnswerBoardResult,
} from '../../api/teacherTrials'
import { formatDateTimeText, formatDurationSec } from '../../utils/trialAnswerFormat'

const props = defineProps<{
  studentId: number
}>()

const loading = ref(false)
const errorMessage = ref('')
const board = ref<StudentTrialAnswerBoardResult | null>(null)
const expandedTrialId = ref<number | null>(null)

const statusLabels: Record<string, string> = {
  joined: '进行中',
  completed: '已完成',
  abandoned: '已放弃',
}

async function loadBoard() {
  loading.value = true
  errorMessage.value = ''
  try {
    board.value = await fetchStudentTrialAnswerBoard(props.studentId)
    expandedTrialId.value = board.value.trials.find((item) => item.answered_count > 0)?.trial.id ?? null
  } catch (error) {
    board.value = null
    errorMessage.value = error instanceof Error ? error.message : '加载失败'
  } finally {
    loading.value = false
  }
}

function toggleTrial(trialId: number) {
  expandedTrialId.value = expandedTrialId.value === trialId ? null : trialId
}

watch(
  () => props.studentId,
  (id) => {
    if (id) void loadBoard()
  },
  { immediate: true },
)
</script>

<template>
  <section class="explorer-trial-panel" aria-label="试炼作答记录">
    <header v-if="board" class="explorer-trial-panel__summary">
      <div>
        <span>参与试炼</span>
        <strong>{{ board.trials.length }}</strong>
      </div>
      <div>
        <span>已答题次</span>
        <strong>{{ board.trials.reduce((sum, item) => sum + item.answered_count, 0) }}</strong>
      </div>
      <div>
        <span>答对题次</span>
        <strong>{{ board.trials.reduce((sum, item) => sum + item.correct_count, 0) }}</strong>
      </div>
    </header>

    <p class="explorer-trial-panel__hint">与学生端试炼关卡 / 探索舱 / 今日委托提交实时同步</p>

    <div v-if="loading" class="teacher-state-panel">正在加载试炼作答…</div>
    <div v-else-if="errorMessage" class="teacher-state-panel teacher-state-panel--error">
      <span>{{ errorMessage }}</span>
      <n-button secondary size="small" @click="loadBoard()">重试</n-button>
    </div>
    <p v-else-if="!board?.trials.length" class="explorer-trial-panel__empty">该 Explorer 尚无试炼或作答记录。</p>

    <ul v-else class="explorer-trial-panel__list">
      <li v-for="item in board.trials" :key="item.trial.id">
        <button type="button" class="explorer-trial-panel__head" @click="toggleTrial(item.trial.id)">
          <div>
            <h3>{{ item.trial.title }}</h3>
            <p>
              <template v-if="item.participation_status">
                {{ statusLabels[item.participation_status] ?? item.participation_status }}
              </template>
              <template v-else>未参与</template>
              · 答题 {{ item.answered_count }}/{{ item.question_total }}
              · 正确 {{ item.correct_count }}
              · 用时 {{ formatDurationSec(item.total_time_spent_sec) }}
              <template v-if="item.participation_status === 'completed'"> · 得分 {{ item.score }}</template>
            </p>
          </div>
          <span>{{ expandedTrialId === item.trial.id ? '收起 ▲' : '明细 ▼' }}</span>
        </button>

        <div v-if="expandedTrialId === item.trial.id" class="explorer-trial-panel__answers">
          <table>
            <thead>
              <tr>
                <th>题号</th>
                <th>选项</th>
                <th>正确答案</th>
                <th>结果</th>
                <th>用时</th>
                <th>提交时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="answer in item.answers" :key="answer.question_id">
                <td>第 {{ answer.sort_order + 1 }} 题</td>
                <td>
                  <template v-if="answer.status === 'completed'">
                    {{ answer.selected_label }}
                    <small v-if="answer.selected_text"> · {{ answer.selected_text }}</small>
                  </template>
                  <template v-else>未提交</template>
                </td>
                <td>{{ answer.correct_label ?? '—' }}</td>
                <td>
                  <n-tag
                    v-if="answer.status === 'completed'"
                    size="small"
                    :type="answer.is_correct ? 'success' : 'error'"
                    :bordered="false"
                  >
                    {{ answer.is_correct ? '正确' : '错误' }}
                  </n-tag>
                  <span v-else>—</span>
                </td>
                <td>{{ formatDurationSec(answer.time_spent_sec) }}</td>
                <td>{{ formatDateTimeText(answer.answered_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.explorer-trial-panel {
  display: grid;
  gap: 0.85rem;
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

.explorer-trial-panel__hint {
  margin: 0;
  font-size: 0.8rem;
  color: var(--teacher-muted);
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

.explorer-trial-panel__list > li {
  border-radius: 14px;
  border: 1px solid rgba(130, 212, 255, 0.1);
  background: rgba(4, 12, 20, 0.45);
  overflow: hidden;
}

.explorer-trial-panel__head {
  width: 100%;
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.85rem 1rem;
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.explorer-trial-panel__head h3 {
  margin: 0 0 0.25rem;
  font-size: 0.95rem;
  color: var(--teacher-text);
}

.explorer-trial-panel__head p {
  margin: 0;
  font-size: 0.82rem;
  color: var(--teacher-muted);
}

.explorer-trial-panel__answers {
  padding: 0 0.75rem 0.75rem;
  overflow: auto;
}

.explorer-trial-panel__answers table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
}

.explorer-trial-panel__answers th,
.explorer-trial-panel__answers td {
  padding: 0.45rem 0.5rem;
  border-bottom: 1px solid rgba(130, 212, 255, 0.08);
  text-align: left;
  vertical-align: top;
}

.explorer-trial-panel__answers th {
  color: var(--teacher-muted);
}

.explorer-trial-panel__answers small {
  color: var(--teacher-muted);
}
</style>
