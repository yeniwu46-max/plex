<script setup lang="ts">
import { ref, watch } from 'vue'
import { NButton, NTag } from 'naive-ui'
import { fetchTeacherTrialDetail, type TeacherTrialDetailResult } from '../../api/teacherTrials'
import { formatDateTimeText, formatDurationSec } from '../../utils/trialAnswerFormat'

const props = defineProps<{
  trialId: number | null
}>()

const emit = defineEmits<{
  close: []
}>()

const loading = ref(false)
const errorMessage = ref('')
const detail = ref<TeacherTrialDetailResult | null>(null)
const expandedStudentId = ref<number | null>(null)

const statusLabels: Record<string, string> = {
  joined: '进行中',
  completed: '已完成',
  abandoned: '已放弃',
}

function toggleStudent(userId: number) {
  expandedStudentId.value = expandedStudentId.value === userId ? null : userId
}

async function loadDetail() {
  if (!props.trialId) {
    detail.value = null
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    detail.value = await fetchTeacherTrialDetail(props.trialId)
    if (detail.value.students.length && expandedStudentId.value === null) {
      expandedStudentId.value = detail.value.students[0].user_id
    }
  } catch (error) {
    detail.value = null
    errorMessage.value = error instanceof Error ? error.message : '加载失败'
  } finally {
    loading.value = false
  }
}

watch(
  () => props.trialId,
  () => {
    expandedStudentId.value = null
    void loadDetail()
  },
  { immediate: true },
)
</script>

<template>
  <aside v-if="trialId" class="trial-detail" aria-label="试炼数据详情">
    <header class="trial-detail__head">
      <div>
        <h2>{{ detail?.trial.title ?? '试炼详情' }}</h2>
        <p v-if="detail">
          {{ detail.class_name }} · {{ detail.teacher_name }}
          · {{ detail.summary.question_count }} 题 · 数据已同步数据库
        </p>
      </div>
      <n-button quaternary size="small" @click="emit('close')">关闭</n-button>
    </header>

    <div v-if="loading" class="trial-detail__state">加载中…</div>
    <div v-else-if="errorMessage" class="trial-detail__state trial-detail__state--error">
      <span>{{ errorMessage }}</span>
      <n-button secondary size="small" @click="loadDetail()">重试</n-button>
    </div>
    <template v-else-if="detail">
      <section class="trial-detail__stats">
        <article>
          <span>参与人数</span>
          <strong>{{ detail.trial.participant_count ?? 0 }}</strong>
        </article>
        <article>
          <span>完成率</span>
          <strong>{{ detail.summary.completion_rate }}%</strong>
        </article>
        <article>
          <span>平均分</span>
          <strong>{{ detail.summary.avg_score }}</strong>
        </article>
      </section>

      <section class="trial-detail__section">
        <h3>题目统计</h3>
        <div v-if="detail.summary.question_stats.length" class="trial-detail__table-wrap">
          <table class="trial-detail__table">
            <thead>
              <tr>
                <th>题号</th>
                <th>知识点</th>
                <th>正确率</th>
                <th>平均用时</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in detail.summary.question_stats" :key="item.question_id">
                <td>第 {{ item.sort_order + 1 }} 题</td>
                <td>{{ item.knowledge_label }}</td>
                <td>{{ item.correct_count }}/{{ item.answered_count }}（{{ item.correct_rate }}%）</td>
                <td>{{ formatDurationSec(item.avg_time_spent_sec) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="trial-detail__empty">暂无题目数据</p>
      </section>

      <section class="trial-detail__section">
        <h3>学生作答明细</h3>
        <ul v-if="detail.students.length" class="trial-detail__students">
          <li v-for="student in detail.students" :key="student.user_id">
            <button type="button" class="trial-detail__student-head" @click="toggleStudent(student.user_id)">
              <div>
                <strong>{{ student.real_name }}（{{ student.username }}）</strong>
                <p>
                  <template v-if="student.participation_status">
                    {{ statusLabels[student.participation_status] ?? student.participation_status }}
                  </template>
                  <template v-else>未参与</template>
                  · 答题 {{ student.answered_count }}/{{ student.question_total }}
                  · 正确 {{ student.correct_count }}
                  · 总用时 {{ formatDurationSec(student.total_time_spent_sec) }}
                  <template v-if="student.participation_status === 'completed'">
                    · 得分 {{ student.score }}
                  </template>
                </p>
                <p v-if="student.joined_at" class="trial-detail__meta-line">
                  参与 {{ formatDateTimeText(student.joined_at) }}
                  <template v-if="student.completed_at">
                    · 完成 {{ formatDateTimeText(student.completed_at) }}
                  </template>
                </p>
              </div>
              <span>{{ expandedStudentId === student.user_id ? '收起 ▲' : '展开 ▼' }}</span>
            </button>

            <div v-if="expandedStudentId === student.user_id" class="trial-detail__table-wrap">
              <table class="trial-detail__table">
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
                        {{ answer.selected_label ?? '—' }}
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
                      <span v-else class="trial-detail__pending">待作答</span>
                    </td>
                    <td>{{ formatDurationSec(answer.time_spent_sec) }}</td>
                    <td>{{ formatDateTimeText(answer.answered_at) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </li>
        </ul>
        <p v-else class="trial-detail__empty">暂无学生数据</p>
      </section>
    </template>
  </aside>
</template>

<style scoped>
.trial-detail {
  border: 1px solid rgba(16, 240, 192, 0.18);
  border-radius: 14px;
  background: rgba(11, 22, 40, 0.92);
  padding: 1rem 1.1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-height: min(78vh, 860px);
  overflow: auto;
}

.trial-detail__head {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
}

.trial-detail__head h2 {
  margin: 0;
  font-size: 1.05rem;
}

.trial-detail__head p {
  margin: 0.25rem 0 0;
  color: var(--plex-text-muted, #8ea3b8);
  font-size: 0.82rem;
}

.trial-detail__state {
  text-align: center;
  color: var(--plex-text-muted, #8ea3b8);
  padding: 1.5rem 0;
}

.trial-detail__state--error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.65rem;
}

.trial-detail__stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.65rem;
}

.trial-detail__stats article {
  border: 1px solid rgba(16, 240, 192, 0.12);
  border-radius: 10px;
  padding: 0.65rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.trial-detail__stats span {
  font-size: 0.78rem;
  color: var(--plex-text-muted, #8ea3b8);
}

.trial-detail__stats strong {
  font-size: 1.1rem;
}

.trial-detail__section h3 {
  margin: 0 0 0.65rem;
  font-size: 0.92rem;
}

.trial-detail__students {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.trial-detail__students > li {
  border: 1px solid rgba(16, 240, 192, 0.1);
  border-radius: 10px;
  overflow: hidden;
}

.trial-detail__student-head {
  width: 100%;
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: flex-start;
  padding: 0.75rem 0.85rem;
  border: none;
  background: rgba(13, 26, 45, 0.55);
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.trial-detail__student-head p {
  margin: 0.25rem 0 0;
  font-size: 0.82rem;
  color: var(--plex-text-muted, #8ea3b8);
}

.trial-detail__meta-line {
  font-size: 0.78rem !important;
  opacity: 0.9;
}

.trial-detail__table-wrap {
  overflow: auto;
  padding: 0 0.75rem 0.75rem;
}

.trial-detail__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}

.trial-detail__table th,
.trial-detail__table td {
  border-bottom: 1px solid rgba(16, 240, 192, 0.08);
  padding: 0.45rem 0.5rem;
  text-align: left;
  vertical-align: top;
}

.trial-detail__table th {
  color: var(--plex-text-muted, #8ea3b8);
  font-weight: 600;
}

.trial-detail__table small {
  color: var(--plex-text-muted, #8ea3b8);
}

.trial-detail__pending {
  color: var(--plex-text-muted, #8ea3b8);
}

.trial-detail__empty {
  margin: 0;
  color: var(--plex-text-muted, #8ea3b8);
  font-size: 0.85rem;
}
</style>
