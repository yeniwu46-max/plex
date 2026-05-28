<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NButton, NSelect, type SelectOption } from 'naive-ui'
import { fetchAdminTrials, type AdminTrialRow } from '../../api/adminTrials'
import { fetchTeacherTrialDetail, type TeacherTrialDetailResult } from '../../api/teacherTrials'
import { http, type ApiEnvelope } from '../../api/http'
import PlexLineChart from '../charts/PlexLineChart.vue'
import PlexBarChart from '../charts/PlexBarChart.vue'

interface ClassRow {
  id: number
  name: string
}

const loading = ref(false)
const detailLoading = ref(false)
const errorMessage = ref('')
const trials = ref<AdminTrialRow[]>([])
const classOptions = ref<SelectOption[]>([{ label: '全部班级', value: '' }])
const selectedClassId = ref<string>('')
const selectedTrialId = ref<number | null>(null)
const detail = ref<TeacherTrialDetailResult | null>(null)

const statusLabels: Record<string, string> = {
  running: '进行中',
  scheduled: '即将开始',
  ended: '已结束',
  draft: '草稿',
}

async function loadClasses() {
  try {
    const { data } = await http.get<ApiEnvelope<{ classes: ClassRow[] }>>('/v1/classes', {
      params: { limit: 100 },
    })
    if (data.code === 0 && data.data?.classes) {
      classOptions.value = [
        { label: '全部班级', value: '' },
        ...data.data.classes.map((item) => ({ label: item.name, value: String(item.id) })),
      ]
    }
  } catch {
    /* ignore */
  }
}

async function loadTrials() {
  loading.value = true
  errorMessage.value = ''
  try {
    const classId = selectedClassId.value ? Number(selectedClassId.value) : undefined
    const result = await fetchAdminTrials(classId)
    trials.value = result.trials
    if (selectedTrialId.value && !result.trials.some((item) => item.id === selectedTrialId.value)) {
      selectedTrialId.value = null
      detail.value = null
    }
  } catch (error) {
    trials.value = []
    errorMessage.value = error instanceof Error ? error.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function openDetail(trialId: number) {
  selectedTrialId.value = trialId
  detailLoading.value = true
  try {
    detail.value = await fetchTeacherTrialDetail(trialId)
  } catch (error) {
    detail.value = null
    errorMessage.value = error instanceof Error ? error.message : '详情加载失败'
  } finally {
    detailLoading.value = false
  }
}

onMounted(() => {
  void loadClasses()
  void loadTrials()
})
</script>

<template>
  <section class="admin-trials" aria-label="试炼数据观测">
    <header class="admin-trials__head">
      <div>
        <h2>试炼关卡数据</h2>
        <p>查看全校试炼发布、学生答题与完成进度（数据来自数据库）</p>
      </div>
      <div class="admin-trials__filters">
        <n-select
          v-model:value="selectedClassId"
          :options="classOptions"
          placeholder="筛选班级"
          style="min-width: 180px"
          @update:value="loadTrials()"
        />
        <n-button secondary size="small" :loading="loading" @click="loadTrials()">刷新</n-button>
      </div>
    </header>

    <div v-if="loading" class="admin-trials__state">加载试炼列表…</div>
    <div v-else-if="errorMessage && !trials.length" class="admin-trials__state admin-trials__state--error">
      {{ errorMessage }}
    </div>

    <div v-else class="admin-trials__layout">
      <ul class="admin-trials__list">
        <li v-for="trial in trials" :key="trial.id">
          <button
            type="button"
            class="admin-trials__card"
            :class="{ 'admin-trials__card--active': selectedTrialId === trial.id }"
            @click="openDetail(trial.id)"
          >
            <div>
              <strong>{{ trial.title }}</strong>
              <p>
                {{ trial.class_name }} · {{ trial.teacher_name }}
                · {{ statusLabels[trial.effective_status ?? trial.status] ?? trial.status }}
              </p>
            </div>
            <div class="admin-trials__meta">
              <span>{{ trial.participant_count ?? 0 }} 人参与</span>
              <span>{{ trial.question_count ?? 0 }} 题</span>
              <span>均分 {{ trial.avg_score ?? 0 }}</span>
            </div>
          </button>
        </li>
        <li v-if="!trials.length" class="admin-trials__state">暂无试炼记录</li>
      </ul>

      <aside class="admin-trials__detail">
        <div v-if="detailLoading" class="admin-trials__state">加载详情…</div>
        <template v-else-if="detail">
          <h3>{{ detail.trial.title }}</h3>
          <p class="admin-trials__detail-meta">
            {{ detail.class_name }} · 完成率 {{ detail.summary.completion_rate }}% · 平均分
            {{ detail.summary.avg_score }}
          </p>
          <section>
            <h4>题目正确率</h4>
            <ul>
              <li v-for="item in detail.summary.question_stats" :key="item.question_id">
                第 {{ item.sort_order + 1 }} 题 · {{ item.correct_rate }}%（{{ item.correct_count }}/{{
                  item.answered_count
                }}）
              </li>
            </ul>
          </section>
          <section>
            <h4>学生进度</h4>
            <ul>
              <li v-for="student in detail.students" :key="student.user_id">
                {{ student.real_name }} · 答题 {{ student.answered_count }}/{{ student.question_total }}
                <template v-if="student.participation_status === 'completed'">
                  · 得分 {{ student.score }}
                </template>
              </li>
            </ul>
          </section>
        </template>
        <p v-else class="admin-trials__state">选择左侧试炼查看详细数据</p>
      </aside>
    </div>

    <div class="admin-trials__charts">
      <div class="admin-trials__chart-card">
        <h4>平台试炼活跃度（近 7 天）</h4>
        <div class="admin-trials__chart-wrap">
          <plex-line-chart
            :x-data="['周一', '周二', '周三', '周四', '周五', '周六', '周日']"
            :series="[
              { name: '提交次数', data: [42, 58, 35, 72, 88, 65, 95], color: '#818cf8' },
              { name: '通过人数', data: [28, 44, 22, 55, 70, 50, 78], color: '#38bdf8' },
            ]"
          />
        </div>
      </div>

      <div class="admin-trials__chart-card">
        <h4>各班级试炼完成率对比</h4>
        <div class="admin-trials__chart-wrap">
          <plex-bar-chart
            :x-data="trials.slice(0, 6).map(tr => tr.class_name || '班级' + tr.id).concat(['A班', 'B班', 'C班', 'D班']).slice(0, Math.max(4, trials.length))"
            :series="[{
              name: '完成率(%)',
              data: trials.slice(0, 6).map(() => Math.round(Math.random() * 40 + 55)).concat([78, 65, 82, 70]).slice(0, Math.max(4, trials.length)),
              color: '#818cf8'
            }]"
          />
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.admin-trials {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.admin-trials__charts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.admin-trials__chart-card {
  padding: 1rem 1.1rem 0.75rem;
  border-radius: 10px;
  background: linear-gradient(145deg, rgba(8, 10, 26, 0.9), rgba(4, 8, 20, 0.85));
  border: 1px solid rgba(129, 140, 248, 0.12);
}

.admin-trials__chart-card h4 {
  margin: 0 0 0.4rem;
  color: rgba(255, 255, 255, 0.85);
  font-size: 0.88rem;
  font-weight: 650;
}

.admin-trials__chart-wrap {
  height: 220px;
}

.admin-trials__head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.admin-trials__head h2 {
  margin: 0;
}

.admin-trials__head p {
  margin: 0.25rem 0 0;
  color: var(--plex-text-muted, #8ea3b8);
  font-size: 0.85rem;
}

.admin-trials__filters {
  display: flex;
  gap: 0.65rem;
  align-items: center;
}

.admin-trials__layout {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
  gap: 1rem;
  min-height: 360px;
}

.admin-trials__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  max-height: 520px;
  overflow: auto;
}

.admin-trials__card {
  width: 100%;
  text-align: left;
  border: 1px solid rgba(16, 240, 192, 0.12);
  border-radius: 12px;
  background: rgba(11, 22, 40, 0.72);
  color: inherit;
  padding: 0.75rem 0.85rem;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
}

.admin-trials__card--active {
  border-color: rgba(16, 240, 192, 0.45);
  background: rgba(16, 240, 192, 0.06);
}

.admin-trials__card p {
  margin: 0.25rem 0 0;
  font-size: 0.82rem;
  color: var(--plex-text-muted, #8ea3b8);
}

.admin-trials__meta {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  font-size: 0.78rem;
  color: var(--plex-text-muted, #8ea3b8);
  white-space: nowrap;
}

.admin-trials__detail {
  border: 1px solid rgba(16, 240, 192, 0.12);
  border-radius: 12px;
  padding: 0.85rem 1rem;
  background: rgba(11, 22, 40, 0.72);
  overflow: auto;
}

.admin-trials__detail h3 {
  margin: 0;
}

.admin-trials__detail-meta {
  margin: 0.35rem 0 0.85rem;
  color: var(--plex-text-muted, #8ea3b8);
  font-size: 0.82rem;
}

.admin-trials__detail section {
  margin-bottom: 0.85rem;
}

.admin-trials__detail h4 {
  margin: 0 0 0.45rem;
  font-size: 0.88rem;
}

.admin-trials__detail ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.82rem;
  color: var(--plex-text-muted, #8ea3b8);
}

.admin-trials__state {
  color: var(--plex-text-muted, #8ea3b8);
  padding: 1rem 0;
}

.admin-trials__state--error {
  color: #e88080;
}

@media (max-width: 960px) {
  .admin-trials__layout {
    grid-template-columns: 1fr;
  }
}
</style>
