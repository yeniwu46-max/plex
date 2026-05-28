<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NButton, NSelect, NTag, type SelectOption } from 'naive-ui'
import {
  fetchClassTrialAnswerBoard,
  type ClassTrialAnswerBoardResult,
  type ClassTrialAnswerBoardTrial,
} from '../../api/teacherTrials'
import { formatDateTimeText, formatDurationSec } from '../../utils/trialAnswerFormat'

const props = defineProps<{
  classId: number | null
  compact?: boolean
}>()

const loading = ref(false)
const errorMessage = ref('')
const board = ref<ClassTrialAnswerBoardResult | null>(null)
const selectedTrialId = ref<number | null>(null)
const expandedStudentId = ref<number | null>(null)

const trialOptions = computed<SelectOption[]>(() =>
  (board.value?.trials ?? []).map((item) => ({
    label: `${item.trial.title}（${statusText(item.trial.effective_status ?? item.trial.status)}）`,
    value: item.trial.id,
  })),
)

const selectedTrial = computed<ClassTrialAnswerBoardTrial | null>(() => {
  if (!board.value || selectedTrialId.value === null) return null
  return board.value.trials.find((item) => item.trial.id === selectedTrialId.value) ?? null
})

function statusText(status: string) {
  const map: Record<string, string> = {
    running: '进行中',
    scheduled: '即将开始',
    ended: '已结束',
    draft: '草稿',
  }
  return map[status] ?? status
}

async function loadBoard() {
  if (!props.classId) {
    board.value = null
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    board.value = await fetchClassTrialAnswerBoard(props.classId)
    const preferred =
      board.value.trials.find((item) => item.trial.effective_status === 'running') ?? board.value.trials[0]
    selectedTrialId.value = preferred?.trial.id ?? null
    expandedStudentId.value = null
  } catch (error) {
    board.value = null
    errorMessage.value = error instanceof Error ? error.message : '加载失败'
  } finally {
    loading.value = false
  }
}

function toggleStudent(userId: number) {
  expandedStudentId.value = expandedStudentId.value === userId ? null : userId
}

watch(
  () => props.classId,
  () => {
    void loadBoard()
  },
  { immediate: true },
)
</script>

<template>
  <section class="class-answer-board" :class="{ 'class-answer-board--compact': compact }" aria-label="班级试炼作答">
    <header class="class-answer-board__head">
      <div>
        <h2>{{ board?.class_name ?? '班级试炼作答' }}</h2>
        <p v-if="board">
          {{ board.sync_note }} · {{ board.student_count }} 名学生 · {{ board.active_trial_count }} 场进行中
        </p>
        <p v-else-if="!classId">请先在顶部选择班级</p>
      </div>
      <n-button v-if="classId" secondary size="small" :loading="loading" @click="loadBoard()">刷新</n-button>
    </header>

    <div v-if="!classId" class="class-answer-board__empty">选择班级后，这里会显示该班学生在试炼关卡 / 探索舱 / 今日委托的做题记录。</div>
    <div v-else-if="loading" class="class-answer-board__empty">正在同步学生做题数据…</div>
    <div v-else-if="errorMessage" class="class-answer-board__empty class-answer-board__empty--error">
      {{ errorMessage }}
      <n-button secondary size="small" @click="loadBoard()">重试</n-button>
    </div>
    <div v-else-if="!board?.trials.length" class="class-answer-board__empty">该班级暂无试炼，请先在试炼中枢发布。</div>
    <template v-else>
      <div class="class-answer-board__toolbar">
        <label>
          <span>试炼</span>
          <n-select
            v-model:value="selectedTrialId"
            :options="trialOptions"
            placeholder="选择试炼"
            style="min-width: 240px"
          />
        </label>
        <div v-if="selectedTrial" class="class-answer-board__meta">
          <span>完成率 {{ selectedTrial.summary.completion_rate }}%</span>
          <span>均分 {{ selectedTrial.summary.avg_score }}</span>
        </div>
      </div>

      <div v-if="selectedTrial" class="class-answer-board__table-wrap">
        <table class="class-answer-board__table">
          <thead>
            <tr>
              <th>学生</th>
              <th>进度</th>
              <th>正确</th>
              <th>用时</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="student in selectedTrial.students" :key="student.user_id">
              <tr>
                <td>
                  <strong>{{ student.real_name }}</strong>
                  <small>{{ student.username }}</small>
                </td>
                <td>{{ student.answered_count }}/{{ student.question_total }}</td>
                <td>{{ student.correct_count }}</td>
                <td>{{ formatDurationSec(student.total_time_spent_sec) }}</td>
                <td>
                  <n-tag
                    v-if="student.participation_status === 'completed'"
                    size="small"
                    type="success"
                    :bordered="false"
                  >
                    已完成 · {{ student.score }} 分
                  </n-tag>
                  <n-tag
                    v-else-if="student.answered_count > 0"
                    size="small"
                    type="warning"
                    :bordered="false"
                  >
                    答题中
                  </n-tag>
                  <n-tag v-else-if="student.participation_status === 'joined'" size="small" :bordered="false">
                    已参与
                  </n-tag>
                  <span v-else class="class-answer-board__muted">未开始</span>
                </td>
                <td>
                  <n-button
                    v-if="student.answered_count > 0"
                    size="tiny"
                    quaternary
                    @click="toggleStudent(student.user_id)"
                  >
                    {{ expandedStudentId === student.user_id ? '收起' : '明细' }}
                  </n-button>
                </td>
              </tr>
              <tr v-if="expandedStudentId === student.user_id" class="class-answer-board__detail-row">
                <td colspan="6">
                  <table class="class-answer-board__subtable">
                    <thead>
                      <tr>
                        <th>题号</th>
                        <th>学生选项</th>
                        <th>正确答案</th>
                        <th>结果</th>
                        <th>用时</th>
                        <th>提交时间</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="answer in student.answers" :key="answer.question_id">
                        <td>第 {{ answer.sort_order + 1 }} 题</td>
                        <td>
                          <template v-if="answer.status === 'completed'">
                            {{ answer.selected_label }}
                            <small v-if="answer.selected_text"> · {{ answer.selected_text }}</small>
                          </template>
                          <template v-else>—</template>
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
                          <span v-else class="class-answer-board__muted">未提交</span>
                        </td>
                        <td>{{ formatDurationSec(answer.time_spent_sec) }}</td>
                        <td>{{ formatDateTimeText(answer.answered_at) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </template>
  </section>
</template>

<style scoped>
.class-answer-board {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  padding: 1.2rem 1.3rem;
  border-radius: 16px;
  border: 1px solid rgba(130, 212, 255, 0.12);
  background: rgba(4, 12, 20, 0.55);
}

.class-answer-board--compact {
  padding: 0.85rem 1rem;
}

.class-answer-board__head {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: flex-start;
}

.class-answer-board__head h2 {
  margin: 0;
  font-size: 1rem;
}

.class-answer-board__head p {
  margin: 0.25rem 0 0;
  font-size: 0.82rem;
  color: var(--teacher-muted, #8ea3b8);
}

.class-answer-board__toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1rem;
  align-items: center;
}

.class-answer-board__toolbar label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.82rem;
  color: var(--teacher-muted, #8ea3b8);
}

.class-answer-board__meta {
  display: flex;
  gap: 0.85rem;
  font-size: 0.82rem;
  color: var(--teacher-orange, #fb923c);
}

.class-answer-board__table-wrap {
  overflow: auto;
}

.class-answer-board__table,
.class-answer-board__subtable {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}

.class-answer-board__table th,
.class-answer-board__table td,
.class-answer-board__subtable th,
.class-answer-board__subtable td {
  padding: 0.5rem 0.55rem;
  border-bottom: 1px solid rgba(130, 212, 255, 0.08);
  text-align: left;
  vertical-align: top;
}

.class-answer-board__table th,
.class-answer-board__subtable th {
  color: var(--teacher-muted, #8ea3b8);
}

.class-answer-board__table small {
  display: block;
  color: var(--teacher-muted, #8ea3b8);
  font-size: 0.75rem;
}

.class-answer-board__detail-row td {
  background: rgba(4, 12, 20, 0.35);
  padding-top: 0;
}

.class-answer-board__muted {
  color: var(--teacher-muted, #8ea3b8);
}

.class-answer-board__empty {
  color: var(--teacher-muted, #8ea3b8);
  font-size: 0.88rem;
  padding: 1rem 0;
}

.class-answer-board__empty--error {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}
</style>
