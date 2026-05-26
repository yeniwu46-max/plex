<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NButton, NIcon, NSelect, type SelectOption } from 'naive-ui'
import {
  AlertCircleOutline,
  ChevronDownOutline,
  CompassOutline,
  CubeOutline,
  InformationCircleOutline,
  PeopleOutline,
  RefreshOutline,
  ScanOutline,
  ShieldCheckmarkOutline,
  SparklesOutline,
} from '@vicons/ionicons5'
import DashboardShell from '../components/layout/DashboardShell.vue'
import { fetchTeacherOverview, type TeacherOverview, type TeacherStudentRow } from '../api/teacherOverview'

const overview = ref<TeacherOverview | null>(null)
const loading = ref(true)
const errorMessage = ref('')
const selectedClassId = ref<number | null>(null)
const period = ref<'week' | 'month'>('week')

const classOptions = computed<SelectOption[]>(() =>
  (overview.value?.classes ?? []).map((item) => ({
    label: `${item.name} ${new Date().getFullYear()}`,
    value: item.id,
  })),
)

const metrics = computed(() => overview.value?.metrics)
const students = computed(() => overview.value?.students ?? [])
const attentionStudents = computed(() => overview.value?.attention_students ?? [])
const activityScore = computed(() => metrics.value?.avg_today_completion ?? 0)
const activeLineWidth = computed(() => `${Math.max(12, Math.min(100, activityScore.value))}%`)
const missionTotal = computed(() => Math.max(5, students.value.length ? 5 : 0))
const missionDone = computed(() => Math.min(5, Math.max(0, Math.round((activityScore.value / 100) * 5))))

const periodOptions: SelectOption[] = [
  { label: '本周', value: 'week' },
  { label: '本月', value: 'month' },
]

const explorationStats = computed(() => [
  {
    key: 'trials',
    icon: SparklesOutline,
    value: Math.max(0, metrics.value?.avg_points ?? 0),
    label: '平均 XP',
  },
  {
    key: 'active',
    icon: PeopleOutline,
    value: metrics.value?.active_count ?? 0,
    label: '活跃 Explorer',
  },
  {
    key: 'repair',
    icon: ShieldCheckmarkOutline,
    value: `${activityScore.value}%`,
    label: '今日修复率',
  },
  {
    key: 'risk',
    icon: CubeOutline,
    value: metrics.value?.attention_count ?? 0,
    label: '需跟进学生',
  },
])

const orbitNodes = computed(() => {
  const base = [
    { label: '算法基础', tone: 'amber', x: 43, y: 16, score: 78, delta: '上升' },
    { label: '前端开发', tone: 'gold', x: 72, y: 26, score: 85, delta: '上升' },
    { label: '后端开发', tone: 'red', x: 73, y: 70, score: 69, delta: '下降' },
    { label: '计算机基础', tone: 'teal', x: 50, y: 78, score: 90, delta: '上升' },
    { label: '数据库', tone: 'amber', x: 21, y: 66, score: 74, delta: '稳定' },
    { label: '数据结构', tone: 'red', x: 12, y: 39, score: 63, delta: '下降' },
  ]
  const avg = activityScore.value || 72
  return base.map((item, index) => ({
    ...item,
    score: Math.max(42, Math.min(98, Math.round((item.score + avg + index * 2) / 2))),
  }))
})

const trendPoints = computed(() => {
  const rows = overview.value?.heatmap.rows ?? []
  if (!rows.length) return [24, 34, 22, 48, 36, 68, 50, 76, 66]
  const dayCount = overview.value?.heatmap.days.length ?? 0
  return Array.from({ length: Math.min(dayCount, 9) }, (_, idx) => {
    const rates = rows.map((row) => row.cells[idx]?.rate ?? 0)
    return Math.round(rates.reduce((sum, value) => sum + value, 0) / Math.max(1, rates.length))
  })
})

const trendPolyline = computed(() => {
  const points = trendPoints.value
  const max = Math.max(100, ...points)
  return points.map((value, idx) => `${idx * 36},${100 - Math.round((value / max) * 82)}`).join(' ')
})

const focusedExplorers = computed(() => {
  const source = attentionStudents.value.length ? attentionStudents.value : students.value.slice(0, 5)
  return source.slice(0, 5).map((student, index) => ({
    ...student,
    risk: riskText(student, index),
    avatarTone: ['orange', 'red', 'yellow', 'amber', 'teal'][index] ?? 'orange',
  }))
})

const aiInsight = computed(() => {
  const rate = Math.max(0, Math.min(100, 100 - (metrics.value?.attention_count ?? 0) * 11))
  const subject = orbitNodes.value.find((node) => node.tone === 'red')?.label ?? '动态规划状态转移'
  return {
    rate,
    subject,
    copy: `${rate}% 的 Explorer 在「${subject}」相关路径保持稳定，仍建议对低活跃学生追加可视化训练。`,
  }
})

const missionItems = computed(() => [
  { label: '动态规划基础巩固', progress: Math.min(100, activityScore.value + 8), status: `${Math.min(3, missionDone.value)}/3` },
  { label: '图论专项训练', progress: Math.max(18, activityScore.value - 18), status: `${Math.min(3, Math.max(1, missionDone.value - 1))}/3` },
  { label: 'AI 对抗赛 · 预选', progress: activityScore.value, status: missionDone.value >= 3 ? '进行中' : '待启动' },
  { label: '深渊试炼挑战', progress: Math.max(8, activityScore.value - 36), status: '待开始' },
  { label: '知识修复计划', progress: Math.max(6, activityScore.value - 48), status: '待开始' },
])

async function loadOverview(classId = selectedClassId.value) {
  loading.value = true
  errorMessage.value = ''
  try {
    const data = await fetchTeacherOverview({ classId, period: period.value })
    overview.value = data
    selectedClassId.value = data.selected_class?.id ?? null
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '教师端数据加载失败'
  } finally {
    loading.value = false
  }
}

function changeClass(value: string | number | null) {
  const nextValue = value === null ? null : Number(value)
  selectedClassId.value = nextValue
  void loadOverview(nextValue)
}

function changePeriod(value: string | number) {
  period.value = value === 'month' ? 'month' : 'week'
  void loadOverview()
}

function riskText(student: TeacherStudentRow, index: number) {
  if (student.reasons?.some((reason) => reason.includes('冻结') || reason.includes('无积分'))) return '高风险'
  if (student.reasons?.length || index < 4) return index < 2 ? '高风险' : '中风险'
  return '低风险'
}

function activityDescription() {
  if (activityScore.value >= 80) return '班级探索状态活跃，适合推进挑战任务。'
  if (activityScore.value >= 50) return '班级处于稳定推进，需要关注少数掉队学生。'
  return '班级活跃度偏低，建议先启动基础修复训练。'
}

onMounted(() => {
  void loadOverview()
})
</script>

<template>
  <DashboardShell
    active-nav="cabin"
    page-title="领航总览"
    page-subtitle="观察整个知识宇宙的成长轨迹"
    search-placeholder="搜索班级、学生…"
    hide-search
  >
    <template #toolbar>
      <section class="navigator-toolbar" aria-label="教师端筛选与状态">
        <n-select
          :value="selectedClassId"
          :options="classOptions"
          :disabled="loading || !classOptions.length"
          placeholder="选择班级"
          class="class-select"
          @update:value="changeClass"
        >
          <template #arrow>
            <n-icon :component="ChevronDownOutline" />
          </template>
        </n-select>
        <div class="activity-chip">
          <span>班级活跃度</span>
          <strong>{{ activityScore }}%</strong>
          <i :style="{ width: activeLineWidth }" />
        </div>
        <div class="keeper-chip">
          <span class="keeper-avatar" aria-hidden="true"><span /></span>
          <div>
            <strong>Waystation Keeper</strong>
            <small>在线</small>
          </div>
        </div>
        <n-button circle quaternary class="toolbar-icon" aria-label="刷新" :loading="loading" @click="loadOverview()">
          <template #icon>
            <n-icon :component="RefreshOutline" />
          </template>
        </n-button>
      </section>
    </template>

    <section class="navigator-home" aria-label="教师端领航总览">
      <div v-if="loading" class="state-panel">正在同步领航数据…</div>
      <div v-else-if="errorMessage" class="state-panel state-panel--error">
        <span>{{ errorMessage }}</span>
        <n-button secondary @click="loadOverview()">重试</n-button>
      </div>
      <div v-else-if="!overview?.selected_class" class="state-panel">
        <n-icon :component="CompassOutline" />
        <span>当前教师账号还没有负责的班级，请先初始化或分配班级。</span>
      </div>
      <template v-else>
        <section class="cosmos-panel">
          <header class="panel-title">
            <h2>知识宇宙全景</h2>
            <n-icon :component="InformationCircleOutline" />
          </header>
          <div class="orbit-map">
            <span class="orbit-center">
              <n-icon :component="SparklesOutline" />
            </span>
            <span v-for="ring in 7" :key="ring" class="orbit-ring" :style="{ '--ring': ring }" />
            <article
              v-for="node in orbitNodes"
              :key="node.label"
              class="orbit-node"
              :class="`orbit-node--${node.tone}`"
              :style="{ left: `${node.x}%`, top: `${node.y}%` }"
            >
              <span class="orbit-node__planet">
                <n-icon :component="node.tone === 'teal' ? ScanOutline : node.tone === 'red' ? AlertCircleOutline : CubeOutline" />
              </span>
              <strong>{{ node.label }}</strong>
              <em>{{ node.score }}%</em>
              <small :class="{ 'is-down': node.delta === '下降' }">{{ node.delta }}</small>
            </article>
            <div class="orbit-legend">
              <span><i class="good" />掌握良好</span>
              <span><i class="mid" />中等水平</span>
              <span><i class="bad" />高风险</span>
              <span><i class="none" />数据不足</span>
            </div>
          </div>
        </section>

        <aside class="overview-card stats-card">
          <header class="panel-title">
            <h2>今日探索概览</h2>
          </header>
          <div class="stat-row">
            <article v-for="item in explorationStats" :key="item.key">
              <span><n-icon :component="item.icon" /></span>
              <strong>{{ item.value }}</strong>
              <small>{{ item.label }}</small>
            </article>
          </div>
        </aside>

        <aside class="overview-card insight-card">
          <header class="panel-title">
            <h2>AI 教学洞察</h2>
            <button type="button">查看详情</button>
          </header>
          <div class="insight-body">
            <div class="mini-orbit" aria-hidden="true">
              <span v-for="ring in 4" :key="ring" :style="{ '--ring': ring }" />
              <i />
            </div>
            <p><strong>{{ aiInsight.rate }}%</strong> 的 Explorer<br />在「{{ aiInsight.subject }}」出现理解断层。</p>
            <small>{{ activityDescription() }}</small>
          </div>
        </aside>

        <article class="overview-card trend-card">
          <header class="panel-title">
            <h2>成长趋势</h2>
            <n-select
              :value="period"
              :options="periodOptions"
              size="small"
              class="period-select"
              @update:value="changePeriod"
            />
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

        <article class="overview-card focus-card">
          <header class="panel-title">
            <h2>需要关注的 Explorer</h2>
          </header>
          <div class="explorer-row">
            <article v-for="student in focusedExplorers" :key="student.id" class="explorer-chip">
              <span class="student-avatar" :class="`student-avatar--${student.avatarTone}`">
                {{ (student.real_name || student.username || '?').slice(0, 1) }}
              </span>
              <strong>{{ student.real_name || student.username }}</strong>
              <small>{{ student.risk }}</small>
            </article>
            <span v-if="attentionStudents.length > 5" class="more-chip">+{{ attentionStudents.length - 5 }}</span>
          </div>
        </article>

        <article class="overview-card mission-card">
          <header class="panel-title">
            <h2>今日委托进度</h2>
          </header>
          <div class="mission-body">
            <div class="progress-ring" :style="{ '--progress': `${Math.round((missionDone / Math.max(1, missionTotal)) * 100)}%` }">
              <strong>{{ missionDone }}</strong>
              <span>/{{ missionTotal }}</span>
              <small>进行中</small>
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
      </template>
    </section>
  </DashboardShell>
</template>

<style scoped>
.navigator-toolbar {
  position: relative;
  z-index: 4;
  top: auto;
  right: auto;
  display: flex;
  align-items: center;
  gap: 1.5rem;
  width: fit-content;
  margin: -3.95rem var(--plex-page-gutter-x) 1.7rem auto;
}

.class-select {
  width: 230px;
}

.class-select :deep(.n-base-selection) {
  --n-height: 58px !important;
  --n-color: rgba(4, 15, 25, 0.72) !important;
  --n-border: 1px solid rgba(130, 212, 255, 0.12) !important;
  --n-border-hover: 1px solid rgba(255, 145, 31, 0.45) !important;
  --n-text-color: #fff7ed !important;
  border-radius: 14px !important;
  font-size: 0.96rem;
}

.activity-chip {
  display: grid;
  grid-template-columns: auto 5rem;
  align-items: center;
  min-width: 230px;
  gap: 0.3rem 1rem;
  padding-left: 1.5rem;
  border-left: 1px solid rgba(219, 235, 249, 0.1);
}

.activity-chip span,
.keeper-chip small {
  color: rgba(221, 230, 239, 0.62);
  font-size: 0.82rem;
}

.activity-chip strong {
  color: #fb923c;
  font-size: 1.3rem;
}

.activity-chip i {
  grid-column: 2;
  display: block;
  height: 3px;
  border-radius: 99px;
  background: linear-gradient(90deg, #fb923c, #fbbf24);
  box-shadow: 0 0 18px rgba(251, 146, 60, 0.52);
}

.keeper-chip {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  padding-left: 1.35rem;
  border-left: 1px solid rgba(219, 235, 249, 0.1);
}

.keeper-chip strong {
  color: rgba(255, 247, 237, 0.88);
  font-size: 0.9rem;
}

.keeper-chip small::before {
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 0.35rem;
  border-radius: 50%;
  background: #22cfa4;
  content: '';
}

.keeper-avatar {
  position: relative;
  display: grid;
  width: 48px;
  height: 48px;
  place-items: center;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.18);
  background:
    radial-gradient(circle at center, rgba(59, 130, 246, 0.28), transparent 62%),
    #061827;
}

.keeper-avatar span {
  width: 30px;
  height: 22px;
  border-radius: 10px;
  background: #e9f3fb;
  box-shadow: inset 0 -8px #111926;
}

.toolbar-icon {
  color: #fed7aa !important;
}

.navigator-home {
  --orange: #fb923c;
  --gold: #fbbf24;
  --teal: #2efff1;
  display: grid;
  grid-template-columns: minmax(310px, 0.9fr) minmax(360px, 1fr) minmax(420px, 1.18fr);
  grid-template-rows: 250px 280px 225px;
  gap: 1.1rem;
  height: 100%;
  overflow: auto;
  padding: 0 var(--plex-page-gutter-x) 2rem;
}

.state-panel {
  grid-column: 1 / -1;
  display: flex;
  min-height: 320px;
  align-items: center;
  justify-content: center;
  gap: 0.8rem;
  border: 1px solid rgba(255, 145, 31, 0.18);
  border-radius: 16px;
  background: rgba(5, 17, 29, 0.72);
  color: rgba(255, 237, 213, 0.86);
}

.state-panel--error {
  color: #fecaca;
}

.cosmos-panel,
.overview-card {
  position: relative;
  min-width: 0;
  overflow: hidden;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 18px;
  background:
    radial-gradient(circle at 50% 38%, rgba(251, 146, 60, 0.09), transparent 32%),
    linear-gradient(145deg, rgba(5, 18, 30, 0.91), rgba(3, 12, 20, 0.78));
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.04), 0 22px 70px rgba(0, 0, 0, 0.22);
}

.cosmos-panel {
  grid-column: 1 / span 2;
  grid-row: span 2;
  padding: 1.5rem;
}

.stats-card {
  grid-column: 3;
  grid-row: 1;
}

.insight-card {
  grid-column: 3;
  grid-row: 2;
}

.trend-card {
  grid-column: 1;
  grid-row: 3;
}

.focus-card {
  grid-column: 2;
  grid-row: 3;
}

.mission-card {
  grid-column: 3;
  grid-row: 3;
}

.panel-title {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.panel-title h2 {
  margin: 0;
  color: #fff7ed;
  font-size: 1.28rem;
  font-weight: 720;
}

.panel-title .n-icon,
.panel-title button {
  color: rgba(221, 230, 239, 0.72);
}

.panel-title button {
  border: 0;
  background: transparent;
  cursor: pointer;
  font-size: 0.86rem;
}

.orbit-map {
  position: absolute;
  inset: 3.75rem 1.6rem 1rem;
  overflow: hidden;
}

.orbit-map::before {
  position: absolute;
  inset: 0;
  opacity: 0.55;
  background-image:
    radial-gradient(1px 1px at 14% 34%, rgba(255, 255, 255, 0.5), transparent),
    radial-gradient(1px 1px at 74% 18%, rgba(251, 191, 36, 0.45), transparent),
    radial-gradient(1px 1px at 82% 78%, rgba(46, 255, 241, 0.4), transparent);
  background-size: 160px 160px;
  content: '';
}

.orbit-ring {
  position: absolute;
  left: 50%;
  top: 52%;
  width: calc(var(--ring) * 82px);
  height: calc(var(--ring) * 34px);
  transform: translate(-50%, -50%) rotate(-8deg);
  border: 1px solid rgba(251, 146, 60, 0.16);
  border-radius: 50%;
}

.orbit-center {
  position: absolute;
  left: 50%;
  top: 52%;
  z-index: 2;
  display: grid;
  width: 66px;
  height: 66px;
  place-items: center;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  background:
    radial-gradient(circle, rgba(255, 255, 255, 0.95), rgba(251, 146, 60, 0.86) 21%, transparent 58%),
    rgba(251, 146, 60, 0.18);
  color: #fff7ed;
  font-size: 2.3rem;
  box-shadow: 0 0 38px rgba(251, 146, 60, 0.8);
}

.orbit-node {
  position: absolute;
  z-index: 3;
  display: grid;
  min-width: 126px;
  gap: 0.14rem;
  transform: translate(-50%, -50%);
  color: #fff7ed;
}

.orbit-node::before {
  position: absolute;
  left: 31px;
  top: 31px;
  width: 145px;
  height: 1px;
  transform-origin: left;
  background: linear-gradient(90deg, rgba(251, 146, 60, 0.55), transparent);
  content: '';
}

.orbit-node__planet {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border-radius: 50%;
  color: #fff7ed;
  background: rgba(251, 146, 60, 0.12);
  border: 1px solid rgba(251, 146, 60, 0.8);
  box-shadow: 0 0 28px rgba(251, 146, 60, 0.45), 0 0 0 12px rgba(251, 146, 60, 0.06);
}

.orbit-node strong {
  margin-top: 0.45rem;
  color: rgba(255, 247, 237, 0.82);
  font-weight: 620;
}

.orbit-node em {
  color: #ffffff;
  font-size: 1.14rem;
  font-style: normal;
}

.orbit-node small {
  color: #fb923c;
  font-weight: 800;
}

.orbit-node small::before {
  content: '⬆ ';
}

.orbit-node small.is-down {
  color: #ff554d;
}

.orbit-node small.is-down::before {
  content: '⬇ ';
}

.orbit-node--teal .orbit-node__planet {
  border-color: rgba(46, 255, 241, 0.75);
  background: rgba(46, 255, 241, 0.12);
  box-shadow: 0 0 26px rgba(46, 255, 241, 0.38), 0 0 0 12px rgba(46, 255, 241, 0.05);
}

.orbit-node--red .orbit-node__planet {
  border-color: rgba(255, 85, 77, 0.82);
  background: rgba(255, 85, 77, 0.12);
  box-shadow: 0 0 26px rgba(255, 85, 77, 0.36), 0 0 0 12px rgba(255, 85, 77, 0.05);
}

.orbit-legend {
  position: absolute;
  left: 50%;
  bottom: 0.4rem;
  z-index: 4;
  display: flex;
  gap: 1.5rem;
  transform: translateX(-50%);
  padding: 0.55rem 1rem;
  border: 1px solid rgba(130, 212, 255, 0.08);
  border-radius: 999px;
  background: rgba(2, 11, 18, 0.74);
  color: rgba(221, 230, 239, 0.68);
  white-space: nowrap;
}

.orbit-legend span {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}

.orbit-legend i {
  width: 9px;
  height: 9px;
  border-radius: 50%;
}

.orbit-legend .good {
  background: var(--teal);
}

.orbit-legend .mid {
  background: var(--orange);
}

.orbit-legend .bad {
  background: #ff554d;
}

.orbit-legend .none {
  background: #94a3b8;
}

.overview-card {
  padding: 1.45rem;
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
  color: rgba(221, 230, 239, 0.62);
  font-size: 0.86rem;
  text-align: center;
}

.insight-body {
  display: grid;
  grid-template-columns: 175px minmax(0, 1fr);
  gap: 1.6rem;
  align-items: center;
  height: calc(100% - 2.2rem);
}

.mini-orbit {
  position: relative;
  height: 145px;
}

.mini-orbit span {
  position: absolute;
  left: 50%;
  top: 50%;
  width: calc(var(--ring) * 42px);
  height: calc(var(--ring) * 27px);
  transform: translate(-50%, -50%) rotate(18deg);
  border: 1px solid rgba(251, 146, 60, 0.22);
  border-radius: 50%;
}

.mini-orbit i {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 18px;
  height: 18px;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  background: #fff7ed;
  box-shadow: 0 0 32px rgba(251, 146, 60, 0.85);
}

.insight-body p {
  margin: 0;
  color: #fff7ed;
  font-size: 1.24rem;
  line-height: 1.75;
}

.insight-body p strong {
  color: var(--orange);
}

.insight-body small {
  display: block;
  margin-top: 0.7rem;
  color: rgba(221, 230, 239, 0.62);
  line-height: 1.6;
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
  color: rgba(221, 230, 239, 0.56);
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

.focus-card {
  display: flex;
  flex-direction: column;
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
  color: #fff7ed;
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
  color: #fff7ed;
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
  display: grid;
  width: 106px;
  aspect-ratio: 1;
  place-items: center;
  justify-self: center;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, #06121f 58%, transparent 59%),
    conic-gradient(var(--orange) var(--progress), rgba(255, 255, 255, 0.08) 0);
  box-shadow: 0 0 28px rgba(251, 146, 60, 0.28);
}

.progress-ring strong {
  color: #ffffff;
  font-size: 1.65rem;
  transform: translateY(0.8rem);
}

.progress-ring span {
  color: rgba(255, 237, 213, 0.72);
  transform: translateY(-1.25rem);
}

.progress-ring small {
  color: var(--orange);
  font-weight: 800;
  transform: translateY(-2.55rem);
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

@media (max-width: 1280px) {
  .navigator-toolbar {
    margin: 1rem var(--plex-page-gutter-x) 1rem;
  }

  .navigator-home {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
  }

  .cosmos-panel {
    min-height: 560px;
    grid-row: auto;
  }
}

@media (max-width: 760px) {
  .navigator-toolbar {
    flex-direction: column;
    align-items: stretch;
    margin-inline: 1rem;
  }

  .class-select,
  .activity-chip {
    width: 100%;
  }

  .activity-chip,
  .keeper-chip {
    padding-left: 0;
    border-left: 0;
  }

  .navigator-home {
    grid-template-columns: 1fr;
    padding-inline: 1rem;
  }

  .cosmos-panel {
    min-height: 660px;
  }

  .stat-row,
  .insight-body,
  .mission-body {
    grid-template-columns: 1fr;
  }

  .orbit-node {
    transform: translate(-50%, -50%) scale(0.86);
  }

  .orbit-legend,
  .explorer-row {
    flex-wrap: wrap;
  }

  .mission-list article {
    grid-template-columns: 1fr;
  }
}
</style>
