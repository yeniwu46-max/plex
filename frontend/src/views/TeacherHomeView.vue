<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NIcon, NSelect } from 'naive-ui'
import {
  CompassOutline,
  CubeOutline,
  InformationCircleOutline,
  PeopleOutline,
  ShieldCheckmarkOutline,
  SparklesOutline,
} from '@vicons/ionicons5'
import TeacherDashboardShell from '../components/layout/TeacherDashboardShell.vue'
import ClassHeatmapPanel from '../components/teacher/ClassHeatmapPanel.vue'
import ClassRankingBoard from '../components/teacher/ClassRankingBoard.vue'
import KnowledgeOrbitMap from '../components/teacher/KnowledgeOrbitMap.vue'
import PlexBarChart from '../components/charts/PlexBarChart.vue'
import PlexPieChart from '../components/charts/PlexPieChart.vue'
import { useTeacherOverviewInjected } from '../composables/useTeacherOverview'
import { buildClassStarfieldNodes, polylineFromPoints } from '../data/teacherStarfield'
import { fetchTeacherClassStats, type TeacherClassStatsResult } from '../api/teacherOverview'
import { downloadClassEvaluationExport, fetchClassEvaluation } from '../api/learningReport'
import type { ClassEvaluationStudent } from '../api/learningReport'

const router = useRouter()

const {
  overview,
  loading,
  errorMessage,
  period,
  metrics,
  students,
  selectedClassId,
  attentionStudents,
  activityScore,
  hasSelectedClass,
  periodOptions,
  loadOverview,
  changePeriod,
} = useTeacherOverviewInjected()

function goExplorer(studentId: number) {
  void router.push({ path: '/teacher/starfield', query: { studentId: String(studentId) } })
}

const classStats = ref<TeacherClassStatsResult | null>(null)
const classEvaluation = ref<Awaited<ReturnType<typeof fetchClassEvaluation>> | null>(null)
const exportingCsv = ref(false)

async function loadClassStats() {
  if (!selectedClassId.value) {
    classStats.value = null
    classEvaluation.value = null
    return
  }
  try {
    const [stats, evaluation] = await Promise.all([
      fetchTeacherClassStats(selectedClassId.value),
      fetchClassEvaluation(selectedClassId.value, period.value === 'month' ? '30d' : '7d').catch(() => null),
    ])
    classStats.value = stats
    classEvaluation.value = evaluation
  } catch {
    classStats.value = null
    classEvaluation.value = null
  }
}

async function onExportCsv() {
  if (!selectedClassId.value || exportingCsv.value) return
  exportingCsv.value = true
  try {
    await downloadClassEvaluationExport(selectedClassId.value)
  } catch (error) {
    window.alert(error instanceof Error ? error.message : '导出失败')
  } finally {
    exportingCsv.value = false
  }
}

onMounted(() => {
  void loadClassStats()
})

watch([selectedClassId, period], () => {
  void loadClassStats()
})

const domainChartData = computed(() => {
  const items = classStats.value?.domain_mastery ?? []
  if (!items.length) {
    return {
      xData: ['暂无数据'],
      series: [{ name: '班级掌握度', data: [0], color: '#f97316' }],
    }
  }
  return {
    xData: items.map((item) => item.label),
    series: [{ name: '班级掌握度', data: items.map((item) => item.mastery_rate), color: '#f97316' }],
  }
})

const mistakeChartData = computed(() => {
  const items = classStats.value?.mistake_types ?? []
  if (!items.length) {
    return [{ name: '暂无错题', value: 1, color: '#64748b' }]
  }
  return items
})

const DAILY_QUEST_LABELS = ['晨间启动', '修复知识碎片', '试炼挑战', '夜间总结'] as const

const heatmap = computed(() => overview.value?.heatmap ?? { days: [], rows: [] })
const ranking = computed(() => overview.value?.ranking ?? [])

const missionTotal = computed(() => {
  const total = students.value.reduce((sum, s) => sum + (s.today_total ?? 0), 0)
  return total > 0 ? total : students.value.length * DAILY_QUEST_LABELS.length
})

const missionDone = computed(() => students.value.reduce((sum, s) => sum + (s.today_completed ?? 0), 0))

const explorationStats = computed(() => [
  { key: 'trials', icon: SparklesOutline, value: Math.max(0, metrics.value?.avg_points ?? 0), label: '平均 XP' },
  { key: 'active', icon: PeopleOutline, value: metrics.value?.active_count ?? 0, label: '活跃 Explorer' },
  { key: 'repair', icon: ShieldCheckmarkOutline, value: `${activityScore.value}%`, label: '今日修复率' },
  { key: 'risk', icon: CubeOutline, value: metrics.value?.attention_count ?? 0, label: '需跟进学生' },
])

const orbitNodes = computed(() => buildClassStarfieldNodes(overview.value, classStats.value))

const trendPoints = computed(() => {
  const rows = overview.value?.heatmap.rows ?? []
  if (!rows.length) return [24, 34, 22, 48, 36, 68, 50, 76, 66]
  const dayCount = overview.value?.heatmap.days.length ?? 0
  return Array.from({ length: Math.min(dayCount, 9) }, (_, idx) => {
    const rates = rows.map((row) => row.cells[idx]?.rate ?? 0)
    return Math.round(rates.reduce((sum, value) => sum + value, 0) / Math.max(1, rates.length))
  })
})

const trendPolyline = computed(() => polylineFromPoints(trendPoints.value, 290, 100))

function studentsCompletedQuestThreshold(threshold: number) {
  return students.value.filter((s) => {
    const completed = s.today_completed ?? 0
    const total = s.today_total ?? DAILY_QUEST_LABELS.length
    return completed >= Math.min(threshold, total)
  }).length
}

const evaluationAttention = computed(() => {
  const items = classEvaluation.value?.attention_students ?? []
  return items.map((student: ClassEvaluationStudent) => ({
    id: student.student_id,
    username: student.username,
    real_name: student.real_name,
    reasons: student.risk_tags,
    learning_index: student.learning_index,
    level_label: student.level_label,
  }))
})

const mergedAttentionStudents = computed(() => {
  if (evaluationAttention.value.length) return evaluationAttention.value
  return attentionStudents.value
})

const focusedExplorers = computed(() => {
  const source = mergedAttentionStudents.value.length
    ? mergedAttentionStudents.value
    : students.value.slice(0, 5)
  return source.slice(0, 5).map((student, index) => ({
    ...student,
    risk: riskText(student, index),
    avatarTone: ['orange', 'red', 'yellow', 'amber', 'teal'][index] ?? 'orange',
  }))
})

const missionItems = computed(() => {
  const classSize = Math.max(1, students.value.length)
  return DAILY_QUEST_LABELS.map((label, index) => {
    const threshold = index + 1
    const doneCount = studentsCompletedQuestThreshold(threshold)
    const progress = Math.round((doneCount / classSize) * 100)
    return {
      label,
      progress,
      status: `${doneCount}/${classSize} 人`,
    }
  })
})

function riskText(student: { reasons?: string[] }, index: number) {
  if (student.reasons?.some((reason) => reason.includes('冻结') || reason.includes('无积分'))) return '高风险'
  if (student.reasons?.length || index < 4) return index < 2 ? '高风险' : '中风险'
  return '低风险'
}

</script>

<template>
  <TeacherDashboardShell
    active-nav="navigator"
    page-title="领航总览"
    page-subtitle="观察整个知识宇宙的成长轨迹"
    toolbar-label="教师端筛选与状态"
    hide-search
  >
    <section class="navigator-home teacher-page teacher-quad-layout" aria-label="教师端领航总览">
      <div v-if="loading" class="teacher-state-panel navigator-home__state">正在同步领航数据…</div>
      <div v-else-if="errorMessage" class="teacher-state-panel teacher-state-panel--error navigator-home__state">
        <span>{{ errorMessage }}</span>
        <n-button secondary @click="loadOverview()">重试</n-button>
      </div>
      <div v-else-if="!hasSelectedClass" class="teacher-state-panel navigator-home__state">
        <n-icon :component="CompassOutline" />
        <span>当前教师账号还没有负责的班级，请先初始化或分配班级。</span>
      </div>
      <template v-else>
        <section class="cosmos-panel teacher-panel teacher-quad-layout__primary">
          <header class="teacher-panel__head">
            <h2 class="teacher-panel__title">知识宇宙全景</h2>
            <n-icon :component="InformationCircleOutline" />
          </header>
          <knowledge-orbit-map :nodes="orbitNodes" title="" />
        </section>

        <aside class="overview-card stats-card teacher-panel teacher-quad-layout__side-top" data-tour="teacher-class-dashboard">
          <header class="teacher-panel__head">
            <h2 class="teacher-panel__title">今日探索概览</h2>
          </header>
          <div class="stat-row">
            <article v-for="item in explorationStats" :key="item.key">
              <span><n-icon :component="item.icon" /></span>
              <strong>{{ item.value }}</strong>
              <small>{{ item.label }}</small>
            </article>
          </div>
        </aside>

        <div class="navigator-home__row3 teacher-quad-layout__full-row teacher-quad-layout__cols-3">
          <article class="overview-card trend-card teacher-panel">
            <header class="teacher-panel__head">
              <h2 class="teacher-panel__title">成长趋势</h2>
              <n-select :value="period" :options="periodOptions" size="small" class="period-select" @update:value="changePeriod" />
            </header>
            <svg class="trend-chart" viewBox="0 0 290 120" role="img" aria-label="班级成长趋势">
              <line v-for="line in 3" :key="line" x1="0" x2="288" :y1="line * 32" :y2="line * 32" />
              <polyline :points="trendPolyline" />
            </svg>
            <div class="trend-legend">
              <span><i />探索活跃度</span>
              <span><i />知识修复率</span>
              <span><i />试炼完成率</span>
            </div>
          </article>

          <article class="overview-card focus-card teacher-panel">
            <header class="teacher-panel__head">
              <h2 class="teacher-panel__title">需要关注的 Explorer</h2>
            </header>
            <div class="explorer-row">
              <button
                v-for="student in focusedExplorers"
                :key="student.id"
                type="button"
                class="explorer-chip"
                @click="goExplorer(student.id)"
              >
                <span class="student-avatar" :class="`student-avatar--${student.avatarTone}`">
                  {{ (student.real_name || student.username || '?').slice(0, 1) }}
                </span>
                <strong>{{ student.real_name || student.username }}</strong>
                <small>{{ student.risk }}</small>
              </button>
              <span v-if="mergedAttentionStudents.length > 5" class="more-chip">+{{ mergedAttentionStudents.length - 5 }}</span>
            </div>
          </article>

          <article class="overview-card mission-card teacher-panel" data-tour="teacher-assignment-analysis">
            <header class="teacher-panel__head">
              <h2 class="teacher-panel__title">今日委托进度</h2>
            </header>
            <div class="mission-body">
              <div class="progress-ring" :style="{ '--progress': `${Math.round((missionDone / Math.max(1, missionTotal)) * 100)}%` }">
                <div class="progress-ring__value">
                  <strong>{{ missionDone }}</strong>
                  <span>/{{ missionTotal }}</span>
                </div>
                <small>已完成</small>
              </div>
              <div class="mission-list">
                <article v-for="item in missionItems" :key="item.label">
                  <span>{{ item.label }}</span>
                  <i><b :style="{ width: `${item.progress}%` }" /></i>
                  <em>{{ item.status }}</em>
                </article>
              </div>
            </div>
          </article>
        </div>

        <div class="navigator-home__row4 teacher-quad-layout__full-row teacher-quad-layout__cols-2">
          <class-heatmap-panel class="overview-card heatmap-card" :heatmap="heatmap" />
          <class-ranking-board class="overview-card ranking-card" :ranking="ranking" />
        </div>

        <div class="navigator-home__charts teacher-quad-layout__full-row teacher-quad-layout__cols-2">
          <div v-if="selectedClassId" class="navigator-home__export-row teacher-quad-layout__full-row">
            <n-button
              class="navigator-home__export-btn"
              :loading="exportingCsv"
              @click="onExportCsv"
            >
              导出班级学情 CSV
            </n-button>
          </div>
          <article class="overview-card teacher-panel" data-tour="teacher-weak-points">
            <header class="teacher-panel__head">
              <h2 class="teacher-panel__title">班级知识域掌握度</h2>
            </header>
            <div class="navigator-home__chart-wrap">
              <plex-bar-chart
                :x-data="domainChartData.xData"
                :series="domainChartData.series"
              />
            </div>
          </article>

          <article class="overview-card teacher-panel">
            <header class="teacher-panel__head">
              <h2 class="teacher-panel__title">错题类型分布</h2>
            </header>
            <div class="navigator-home__chart-wrap">
              <plex-pie-chart :data="mistakeChartData" />
            </div>
          </article>
        </div>

      </template>
    </section>
  </TeacherDashboardShell>
</template>

<style scoped>
.navigator-home__export-row {
  display: flex;
  justify-content: flex-end;
}

.navigator-home__export-btn {
  font-size: 0.82rem;
  color: var(--teacher-orange, #fb923c);
  text-decoration: none;
  padding: 0.35rem 0.75rem;
  border: 1px solid rgba(251, 146, 60, 0.35);
  border-radius: 999px;
}

.navigator-home {
  --orange: var(--teacher-orange, #fb923c);
  --gold: var(--teacher-gold, #fbbf24);
  --teal: var(--teacher-teal, #2efff1);
  grid-template-rows: minmax(480px, 1fr) auto auto auto auto auto;
}

.navigator-home__state {
  grid-column: 1 / -1;
}

.navigator-home__row3 {
  grid-row: 3;
}

.navigator-home__charts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.navigator-home__chart-wrap {
  height: 240px;
  margin-top: 0.5rem;
}

.navigator-home__row4 {
  grid-row: 4;
}

.cosmos-panel {
  padding: 1.5rem;
}

.stats-card {
  padding: 1.45rem;
  height: 100%;
}

.trend-card,
.focus-card,
.mission-card {
  padding: 1.45rem;
  min-height: 225px;
}

.focus-card {
  display: flex;
  flex-direction: column;
}

.stat-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1rem;
  height: calc(100% - 2.5rem);
  align-items: center;
}

.stat-row article {
  display: grid;
  justify-items: center;
  gap: 0.75rem;
  min-width: 0;
  padding: 0 0.75rem;
  border-right: 1px solid rgba(219, 235, 249, 0.08);
}

.stat-row article:last-child {
  border-right: 0;
}

.stat-row article > span {
  display: grid;
  width: 64px;
  height: 64px;
  place-items: center;
  border-radius: 50%;
  border: 1px solid rgba(251, 146, 60, 0.24);
  color: var(--orange);
  font-size: 2rem;
  background: rgba(251, 146, 60, 0.04);
}

.stat-row strong {
  color: #ffffff;
  font-size: 1.72rem;
  font-weight: 650;
}

.stat-row small {
  color: var(--teacher-muted);
  font-size: 0.86rem;
  text-align: center;
}

.trend-chart {
  display: block;
  width: 100%;
  height: 105px;
  margin-top: 0.45rem;
}

.trend-chart line {
  stroke: rgba(221, 230, 239, 0.07);
}

.trend-chart polyline {
  fill: none;
  stroke: var(--orange);
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 3;
  filter: drop-shadow(0 0 8px rgba(251, 146, 60, 0.45));
}

.period-select {
  width: 96px;
}

.trend-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  color: var(--teacher-muted);
  font-size: 0.78rem;
}

.trend-legend span {
  display: inline-flex;
  align-items: center;
  gap: 0.42rem;
}

.trend-legend i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--orange);
}

.explorer-row {
  display: flex;
  align-items: center;
  gap: 1.05rem;
  margin-top: auto;
  padding-bottom: 0.35rem;
}

.explorer-chip {
  display: grid;
  justify-items: center;
  gap: 0.35rem;
  min-width: 60px;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  padding: 0;
}

.student-avatar {
  display: grid;
  width: 56px;
  height: 56px;
  place-items: center;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.45);
  background: linear-gradient(145deg, #172034, #f8c59f);
  color: #0b1422;
  font-weight: 900;
}

.student-avatar--teal {
  background: linear-gradient(145deg, #124e4b, #8cffef);
}

.student-avatar--red {
  background: linear-gradient(145deg, #4f1616, #ff8a7d);
}

.student-avatar--yellow,
.student-avatar--amber {
  background: linear-gradient(145deg, #613f10, #ffd68a);
}

.explorer-chip strong {
  max-width: 72px;
  overflow: hidden;
  color: var(--teacher-text);
  font-size: 0.76rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.explorer-chip small {
  color: var(--orange);
  font-size: 0.78rem;
  font-weight: 800;
}

.more-chip {
  display: grid;
  width: 45px;
  height: 45px;
  place-items: center;
  border: 1px solid rgba(221, 230, 239, 0.24);
  border-radius: 50%;
  color: var(--teacher-text);
}

.mission-body {
  display: grid;
  grid-template-columns: 138px minmax(0, 1fr);
  gap: 1rem;
  align-items: center;
  height: calc(100% - 2rem);
}

.progress-ring {
  --progress: 0%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  width: 106px;
  aspect-ratio: 1;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, #06121f 58%, transparent 59%),
    conic-gradient(var(--orange) var(--progress), rgba(255, 255, 255, 0.08) 0);
  box-shadow: 0 0 28px rgba(251, 146, 60, 0.28);
}

.progress-ring__value {
  display: flex;
  align-items: baseline;
  gap: 0.08rem;
  margin-top: 0.15rem;
}

.progress-ring strong {
  color: #ffffff;
  font-size: 1.65rem;
  line-height: 1;
}

.progress-ring span {
  color: rgba(255, 237, 213, 0.72);
  font-size: 0.92rem;
  line-height: 1;
}

.progress-ring small {
  color: var(--orange);
  font-weight: 800;
  font-size: 0.78rem;
  line-height: 1.2;
}

.mission-list {
  display: grid;
  gap: 0.58rem;
  min-width: 0;
}

.mission-list article {
  display: grid;
  grid-template-columns: minmax(92px, 1fr) minmax(54px, 112px) 3.15rem;
  gap: 0.55rem;
  align-items: center;
  color: rgba(255, 247, 237, 0.78);
  font-size: 0.84rem;
}

.mission-list span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mission-list i {
  height: 3px;
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.09);
}

.mission-list b {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--orange), var(--gold));
}

.mission-list em {
  color: var(--orange);
  font-style: normal;
  font-weight: 800;
  text-align: right;
}

@media (max-width: 1100px) {
  .navigator-home {
    grid-template-rows: auto;
  }

  .navigator-home__row3,
  .navigator-home__row4 {
    grid-row: auto;
  }
}

@media (max-width: 760px) {
  .navigator-home.teacher-page {
    padding-inline: 1rem;
  }

  .stat-row,
  .mission-body {
    grid-template-columns: 1fr;
  }

  .explorer-row {
    flex-wrap: wrap;
  }

  .mission-list article {
    grid-template-columns: 1fr;
  }
}
</style>
