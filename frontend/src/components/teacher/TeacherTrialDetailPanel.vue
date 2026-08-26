<script setup lang="ts">
import { ref, watch } from 'vue'
import { NButton, NIcon, NTag, NCollapse, NCollapseItem, NModal, useMessage } from 'naive-ui'
import { SparklesOutline } from '@vicons/ionicons5'
import {
  analyzeTeacherTrial,
  fetchTeacherTrialDetail,
  type TeacherTrialDetailResult,
  type TrialAiAnalyzeResult,
} from '../../api/teacherTrials'
import { formatHttpError } from '../../api/http'
import { formatDateTimeText, formatDurationSec } from '../../utils/trialAnswerFormat'

const props = defineProps<{
  trialId: number | null
}>()

const emit = defineEmits<{
  close: []
}>()

type DetailTab = 'stats' | 'preview' | 'answers'

const message = useMessage()
const loading = ref(false)
const analyzing = ref(false)
const errorMessage = ref('')
const detail = ref<TeacherTrialDetailResult | null>(null)
const expandedStudentId = ref<number | null>(null)
const aiAnalysis = ref<TrialAiAnalyzeResult | null>(null)
const activeTab = ref<DetailTab>('stats')
const fullReportShow = ref(false)

const tabs: Array<{ key: DetailTab; label: string }> = [
  { key: 'stats', label: '题目统计' },
  { key: 'preview', label: '题目预览' },
  { key: 'answers', label: '学生作答明细' },
]

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
    aiAnalysis.value = null
    return
  }
  loading.value = true
  errorMessage.value = ''
  aiAnalysis.value = null
  activeTab.value = 'stats'
  try {
    detail.value = await fetchTeacherTrialDetail(props.trialId)
    if (detail.value.students.length && expandedStudentId.value === null) {
      expandedStudentId.value = detail.value.students[0].user_id
    }
  } catch (error) {
    detail.value = null
    errorMessage.value = formatHttpError(error, '加载失败')
  } finally {
    loading.value = false
  }
}

async function runAiAnalyze() {
  if (!props.trialId || analyzing.value) return
  analyzing.value = true
  try {
    aiAnalysis.value = await analyzeTeacherTrial(props.trialId)
    const backend = aiAnalysis.value.backend || ''
    if (backend.startsWith('local_fallback')) {
      message.warning('星火暂不可用，已使用本地规则生成分析')
    } else {
      message.success('小E 已完成试炼分析')
    }
  } catch (error) {
    message.error(formatHttpError(error, '小E 分析失败，请稍后重试'))
  } finally {
    analyzing.value = false
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
        <div class="trial-detail__head-actions">
        <n-button
          size="small"
          secondary
          :disabled="loading || !detail"
          @click="fullReportShow = true"
        >
          查看全部
        </n-button>
        <n-button
          type="warning"
          size="small"
          :loading="analyzing"
          :disabled="loading || !detail"
          @click="runAiAnalyze"
        >
          <template #icon><n-icon :component="SparklesOutline" /></template>
          小E帮分析
        </n-button>
        <n-button quaternary size="small" @click="emit('close')">关闭</n-button>
      </div>
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

      <section v-if="aiAnalysis" class="trial-detail__ai" aria-label="小E 分析结果">
        <header>
          <h3>小E 帮分析</h3>
          <span>{{ aiAnalysis.backend.startsWith('iflytek') ? '星火' : '本地回退' }}</span>
        </header>
        <p>{{ aiAnalysis.overview }}</p>
        <div v-if="aiAnalysis.weak_points.length" class="trial-detail__ai-block">
          <strong>薄弱点</strong>
          <ul>
            <li v-for="(item, idx) in aiAnalysis.weak_points" :key="`w-${idx}`">{{ item }}</li>
          </ul>
        </div>
        <div v-if="aiAnalysis.strong_points.length" class="trial-detail__ai-block">
          <strong>优势</strong>
          <ul>
            <li v-for="(item, idx) in aiAnalysis.strong_points" :key="`s-${idx}`">{{ item }}</li>
          </ul>
        </div>
        <div v-if="aiAnalysis.suggestions.length" class="trial-detail__ai-block">
          <strong>教学建议</strong>
          <ul>
            <li v-for="(item, idx) in aiAnalysis.suggestions" :key="`g-${idx}`">{{ item }}</li>
          </ul>
        </div>
        <div v-if="aiAnalysis.question_notes?.length" class="trial-detail__ai-block">
          <strong>逐题点评</strong>
          <ul>
            <li v-for="(item, idx) in aiAnalysis.question_notes" :key="`q-${idx}`">
              <template v-if="item.sort_order != null">第 {{ Number(item.sort_order) + 1 }} 题 · </template>
              {{ item.note }}
            </li>
          </ul>
        </div>
      </section>

      <nav class="trial-detail__tabs" aria-label="试炼详情导航">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          class="trial-detail__tab"
          :class="{ 'trial-detail__tab--active': activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </nav>

      <section v-if="activeTab === 'stats'" class="trial-detail__section">
        <div v-if="detail.summary.question_stats.length" class="trial-detail__table-wrap trial-detail__table-wrap--flush">
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
                <td>{{ item.correct_count }}/{{ item.answered_count }} · {{ item.correct_rate }}%</td>
                <td>{{ formatDurationSec(item.avg_time_spent_sec) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="trial-detail__empty">暂无题目数据</p>
      </section>

      <section v-else-if="activeTab === 'preview'" class="trial-detail__section">
        <template v-if="detail.questions && detail.questions.length">
          <n-collapse>
            <n-collapse-item
              v-for="(q, idx) in detail.questions"
              :key="q.id"
              :name="String(q.id)"
            >
              <template #header>
                <span class="trial-detail__q-header">
                  第 {{ idx + 1 }} 题
                  <span class="trial-detail__q-kp">{{ q.knowledge_key ?? '' }}</span>
                </span>
              </template>
              <div class="trial-detail__q-body">
                <p class="trial-detail__q-stem">{{ q.stem }}</p>
                <ul class="trial-detail__q-options">
                  <li
                    v-for="(opt, oi) in q.options"
                    :key="oi"
                    :class="{ 'trial-detail__q-opt--correct': oi === q.correct_index }"
                  >
                    <span class="trial-detail__q-opt-label">{{ String.fromCharCode(65 + oi) }}</span>
                    {{ opt }}
                  </li>
                </ul>
              </div>
            </n-collapse-item>
          </n-collapse>
        </template>
        <p v-else class="trial-detail__empty">暂无题目预览</p>
      </section>

      <section v-else class="trial-detail__section">
        <ul v-if="detail.students.length" class="trial-detail__students">
          <li v-for="student in detail.students" :key="student.user_id">
            <button type="button" class="trial-detail__student-head" @click="toggleStudent(student.user_id)">
              <div>
                <strong>{{ student.real_name }} · {{ student.username }}</strong>
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
                    <th>智能体检查</th>
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
                    <td>
                      <details v-if="answer.agent_trace?.length" class="trial-detail__trace">
                        <summary>{{ answer.agent_trace.length }} 条记录</summary>
                        <ul>
                          <li v-for="(trace, idx) in answer.agent_trace" :key="`${trace.agentId}-${idx}`">
                            <strong>{{ trace.name ?? trace.agentId }}</strong>
                            <span>{{ trace.summary }}</span>
                          </li>
                        </ul>
                      </details>
                      <span v-else class="trial-detail__pending">—</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </li>
        </ul>
        <p v-else class="trial-detail__empty">暂无学生数据</p>
      </section>
    </template>

    <n-modal
      v-model:show="fullReportShow"
      preset="card"
      :title="`${detail?.trial.title || '试炼'} · 完整报告`"
      :bordered="false"
      style="width: min(920px, calc(100vw - 32px))"
      :z-index="5600"
    >
      <template v-if="detail">
        <section class="trial-detail__section">
          <h3>题目正确率</h3>
          <div class="trial-detail__table-wrap">
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
                <tr v-for="item in detail.summary.question_stats" :key="`full-q-${item.question_id}`">
                  <td>第 {{ item.sort_order + 1 }} 题</td>
                  <td>{{ item.knowledge_label }}</td>
                  <td>{{ item.correct_count }}/{{ item.answered_count }} · {{ item.correct_rate }}%</td>
                  <td>{{ formatDurationSec(item.avg_time_spent_sec) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
        <section class="trial-detail__section">
          <h3>学生进度</h3>
          <ul class="trial-detail__students">
            <li v-for="student in detail.students" :key="`full-s-${student.user_id}`">
              <strong>{{ student.real_name || student.username }}</strong>
              <span>
                {{ statusLabels[student.participation_status || ''] || student.participation_status || '进行中' }}
                · {{ student.correct_count }}/{{ student.answered_count }} 题正确
                · 得分 {{ student.score ?? '—' }}
              </span>
            </li>
          </ul>
        </section>
      </template>
    </n-modal>
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

.trial-detail__head-actions {
  display: flex;
  align-items: flex-start;
  gap: 0.45rem;
  flex-shrink: 0;
}

.trial-detail__ai {
  padding: 0.85rem 0.95rem;
  border: 1px solid rgba(251, 146, 60, 0.28);
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(67, 20, 7, 0.35), rgba(15, 23, 42, 0.55));
}

.trial-detail__ai > header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.45rem;
}

.trial-detail__ai h3 {
  margin: 0;
  font-size: 0.92rem;
  color: #fed7aa;
}

.trial-detail__ai > header span {
  color: rgba(254, 215, 170, 0.55);
  font-size: 0.75rem;
}

.trial-detail__ai > p {
  margin: 0 0 0.55rem;
  color: rgba(255, 247, 237, 0.88);
  line-height: 1.55;
  font-size: 0.88rem;
}

.trial-detail__ai-block {
  margin-top: 0.55rem;
}

.trial-detail__ai-block strong {
  display: block;
  margin-bottom: 0.25rem;
  color: #fdba74;
  font-size: 0.8rem;
}

.trial-detail__ai-block ul {
  margin: 0;
  padding-left: 1.1rem;
  color: rgba(235, 215, 194, 0.78);
  font-size: 0.84rem;
  line-height: 1.45;
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

.trial-detail__tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  padding: 0.2rem;
  border: 1px solid rgba(16, 240, 192, 0.12);
  border-radius: 12px;
  background: rgba(8, 18, 32, 0.65);
}

.trial-detail__tab {
  border: none;
  border-radius: 9px;
  padding: 0.45rem 0.85rem;
  background: transparent;
  color: rgba(190, 208, 224, 0.72);
  cursor: pointer;
  font-size: 0.84rem;
}

.trial-detail__tab--active {
  color: #0b1422;
  background: linear-gradient(135deg, #34e6c5, #10f0c0);
  font-weight: 700;
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

.trial-detail__table-wrap--flush {
  padding: 0;
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

.trial-detail__trace {
  font-size: 0.78rem;
  color: rgba(226, 232, 240, 0.78);
}

.trial-detail__trace summary {
  cursor: pointer;
  color: #a78bfa;
}

.trial-detail__trace ul {
  margin: 0.35rem 0 0;
  padding-left: 1rem;
  display: grid;
  gap: 0.25rem;
}

.trial-detail__trace li span {
  display: block;
  color: rgba(226, 232, 240, 0.62);
}

.trial-detail__empty {
  margin: 0;
  color: var(--plex-text-muted, #8ea3b8);
  font-size: 0.85rem;
}

.trial-detail__q-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.88rem;
}

.trial-detail__q-kp {
  font-size: 0.75rem;
  color: var(--plex-text-muted, #8ea3b8);
  background: rgba(16, 240, 192, 0.07);
  border-radius: 4px;
  padding: 0 0.35rem;
}

.trial-detail__q-body {
  padding: 0.25rem 0 0.5rem;
}

.trial-detail__q-stem {
  margin: 0 0 0.65rem;
  font-size: 0.88rem;
  line-height: 1.6;
}

.trial-detail__q-options {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.trial-detail__q-options li {
  display: flex;
  align-items: flex-start;
  gap: 0.4rem;
  font-size: 0.84rem;
  color: var(--plex-text-muted, #8ea3b8);
  padding: 0.3rem 0.5rem;
  border-radius: 6px;
  transition: background 0.15s;
}

.trial-detail__q-opt--correct {
  color: #10f0c0 !important;
  background: rgba(16, 240, 192, 0.08);
  font-weight: 600;
}

.trial-detail__q-opt-label {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.2rem;
  height: 1.2rem;
  border-radius: 3px;
  border: 1px solid currentColor;
  font-size: 0.75rem;
  flex-shrink: 0;
  margin-top: 0.05rem;
}
</style>
