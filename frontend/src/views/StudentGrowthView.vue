<script setup lang="ts">
import { computed, onActivated, onMounted, ref } from 'vue'
import { NButton } from 'naive-ui'
import DashboardShell from '../components/layout/DashboardShell.vue'
import PlexSyncState from '../components/common/PlexSyncState.vue'
import ClassFileExchangePanel from '../components/student/ClassFileExchangePanel.vue'
import PlexRadarChart from '../components/charts/PlexRadarChart.vue'
import PlexPieChart from '../components/charts/PlexPieChart.vue'
import PlexLineChart from '../components/charts/PlexLineChart.vue'
import PlexBarChart from '../components/charts/PlexBarChart.vue'
import EmergencyMissionGrowthModal from '../components/growth/EmergencyMissionGrowthModal.vue'
import { useStudentWorkspaceStore } from '../stores/studentWorkspace'
import type { StudentOverview } from '../api/studentOverview'
import { fetchArchiveInsights } from '../api/studentProgress'
import type { EmergencyMissionArchiveRecord } from '../api/emergencyMission'
import type { LearningReportResult } from '../api/learningReport'
import { fetchStudentKnowledgeGraph } from '../api/knowledgeGraph'
import type { KgNode } from '../data/knowledgeGraphData'
import { formatGrowthEvent } from '../utils/growthEventLabels'
import { buildKnowledgeRadarFromGraph } from '../utils/knowledgeRadar'

const ERROR_TYPE_LABELS: Record<string, string> = {
  wrong_output: '输出错误',
  runtime_error: '运行错误',
  wrong_answer: '答案错误',
}

const workspace = useStudentWorkspaceStore()

const overview = ref<StudentOverview | null>(null)
const learningReport = ref<LearningReportResult | null>(null)
const knowledgeGraphNodes = ref<KgNode[]>([])
const skillItems = ref<Array<{ key: string; label: string; percent: number }>>([])
const emergencyMissions = ref<EmergencyMissionArchiveRecord[]>([])
const expandedEmergencyIds = ref<Set<number>>(new Set())
const detailRecord = ref<EmergencyMissionArchiveRecord | null>(null)
const detailOpen = ref(false)
const loading = ref(true)
const errorMessage = ref('')

const displayName = computed(
  () => overview.value?.profile.real_name || overview.value?.profile.username || 'Explorer',
)
const explorerId = computed(() => {
  const id = overview.value?.profile.id
  return id ? `PX-${String(id).padStart(4, '0')}` : 'PX-0000'
})
const classInfo = computed(() => overview.value?.profile.class)
const classLabel = computed(() => {
  const cls = classInfo.value
  if (!cls) return '暂未加入班级'
  const code = cls.join_code ? ` · 编号 ${cls.join_code}` : ''
  return `${cls.name || `班级 #${cls.id}`}${code}`
})

const growthEvents = computed(() => {
  const logs = overview.value?.pointsLog?.logs ?? []
  const tones = ['teal', 'gold', 'blue', 'purple'] as const
  const pointEvents = logs.slice(0, 8).map((log, index) => {
    const formatted = formatGrowthEvent(log)
    return {
      id: `points-${log.id}`,
      kind: 'points' as const,
      title: formatted.title,
      date: log.created_at?.slice(0, 10) || '今日',
      description: formatted.description,
      tone: tones[index % tones.length],
    }
  })

  const emergencyEvents = emergencyMissions.value.slice(0, 6).map((record, index) => ({
    id: `emergency-${record.id}`,
    kind: 'emergency' as const,
    record,
    title: '边界条件补给站 · 紧急任务',
    date: record.date?.slice(0, 10) || '今日',
    description: `${record.focus_label} · 答对 ${record.correct_count}/${record.total_count}${
      record.reward_points ? ` · +${record.reward_points} XP` : ''
    }`,
    tone: tones[(pointEvents.length + index) % tones.length],
  }))

  return [...emergencyEvents, ...pointEvents]
    .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0))
    .slice(0, 10)
})

function toggleEmergencyEntry(record: EmergencyMissionArchiveRecord) {
  const next = new Set(expandedEmergencyIds.value)
  if (next.has(record.id)) next.delete(record.id)
  else next.add(record.id)
  expandedEmergencyIds.value = next
}

function openEmergencyDetail(record: EmergencyMissionArchiveRecord) {
  detailRecord.value = record
  detailOpen.value = true
}

const radarData = computed(() =>
  buildKnowledgeRadarFromGraph(
    knowledgeGraphNodes.value,
    learningReport.value?.domain_mastery,
  ),
)

const radarLabels = computed(() => radarData.value.dimensions)
const radarValues = computed(() => radarData.value.values)

const mistakePieData = computed(() => {
  const colors = ['#38bdf8', '#818cf8', '#fb923c', '#34d399', '#f472b6', '#fbbf24']
  const counts = new Map<string, number>()
  const mistakes = learningReport.value?.mistake_highlights ?? []

  for (const item of mistakes) {
    const types = item.error_types?.length ? item.error_types : [item.error_type || '其他']
    for (const rawType of types) {
      const label = ERROR_TYPE_LABELS[rawType] || rawType || '其他'
      counts.set(label, (counts.get(label) ?? 0) + (item.fail_count ?? 1))
    }
  }

  if (!counts.size) {
    for (const item of learningReport.value?.weak_knowledge ?? []) {
      counts.set(item.knowledge_label, item.fail_count)
    }
  }

  return [...counts.entries()].map(([name, value], index) => ({
    name,
    value,
    color: colors[index % colors.length],
  }))
})

const trendDays = computed(() => learningReport.value?.trend.x_data ?? [])
const trendCorrect = computed(() => learningReport.value?.trend.correct_rate ?? [])
const trendCount = computed(() => learningReport.value?.trend.practice_count ?? [])

const domainBarLabels = computed(
  () => learningReport.value?.domain_mastery.map((item) => item.label) ?? [],
)
const domainBarValues = computed(
  () => learningReport.value?.domain_mastery.map((item) => item.mastery_rate) ?? [],
)

async function loadArchive(force = false) {
  const blocking = !overview.value
  if (blocking) loading.value = true
  errorMessage.value = ''
  try {
    const [overviewResult, insights, report, graph] = await Promise.all([
      workspace.loadOverview(force),
      fetchArchiveInsights(),
      workspace.loadLearningReport('7d', force).catch(() => null),
      fetchStudentKnowledgeGraph().catch(() => null),
    ])
    overview.value = overviewResult
    learningReport.value = report
    knowledgeGraphNodes.value = graph?.nodes ?? []
    skillItems.value = insights.skills
    emergencyMissions.value = insights.emergency_missions ?? []
  } catch (error) {
    if (!overview.value) {
      errorMessage.value = error instanceof Error ? error.message : '成长档案加载失败'
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadArchive(true)
})

onActivated(() => {
  // 切回本页时用缓存先渲染，后台再静默刷新，避免闪烁
  void loadArchive(false)
})
</script>

<template>
  <DashboardShell
    active-nav="me"
    page-title="成长档案"
    page-subtitle="你的成长，被记录在每一段星轨里"
    search-placeholder=""
    hide-search
  >
    <main class="growth-page">
      <PlexSyncState
        v-if="loading && !overview"
        label="正在整理你的探索档案"
        hint="档案会随练习、试炼与委托实时更新"
      />
      <div v-else-if="errorMessage" class="growth-state growth-state--error">
        <span>{{ errorMessage }}</span>
        <n-button size="small" @click="loadArchive(true)">重试</n-button>
      </div>
      <template v-else>
        <section class="growth-hero">
          <div>
            <h2>{{ displayName }}</h2>
            <p class="eyebrow">GROWTH PORTFOLIO</p>
            <p class="growth-meta">
              <span>{{ explorerId }}</span>
              <span>{{ classLabel }}</span>
              <span>Lv.{{ overview?.profile.level ?? 1 }}</span>
              <span>{{ overview?.profile.total_points ?? 0 }} XP</span>
            </p>
          </div>
          <div class="growth-stats">
            <div class="tech-stat-card">
              <span class="tech-stat-card__corner tech-stat-card__corner--tl" aria-hidden="true" />
              <span class="tech-stat-card__corner tech-stat-card__corner--br" aria-hidden="true" />
              <small>连续探索</small>
              <strong>{{ overview?.profile.consecutive_days ?? 0 }} 天</strong>
            </div>
            <div class="tech-stat-card tech-stat-card--rank">
              <span class="tech-stat-card__corner tech-stat-card__corner--tl" aria-hidden="true" />
              <span class="tech-stat-card__corner tech-stat-card__corner--br" aria-hidden="true" />
              <small>班级排名</small>
              <strong>{{ overview?.profile.class_rank ? `第 ${overview.profile.class_rank} 名` : '暂无' }}</strong>
            </div>
            <div class="tech-stat-card tech-stat-card--rate">
              <span class="tech-stat-card__corner tech-stat-card__corner--tl" aria-hidden="true" />
              <span class="tech-stat-card__corner tech-stat-card__corner--br" aria-hidden="true" />
              <small>近 7 日正确率</small>
              <strong>{{ learningReport?.summary.correct_rate ?? 0 }}%</strong>
            </div>
          </div>
        </section>

        <section class="growth-grid" data-tour="student-learning-report">
          <article class="growth-card skill-card">
            <header><span>能力分布</span><h3>技能掌握度</h3></header>
            <div class="skill-hud">
              <span class="skill-hud__corner skill-hud__corner--tl" aria-hidden="true" />
              <span class="skill-hud__corner skill-hud__corner--br" aria-hidden="true" />
              <ul class="skill-grid">
                <li v-for="skill in skillItems" :key="skill.key" class="skill-grid__item">
                  <div class="skill-grid__head">
                    <strong>{{ skill.label }}</strong>
                    <em>{{ skill.percent }}%</em>
                  </div>
                  <div class="skill-grid__track">
                    <span class="skill-grid__fill" :style="{ width: `${skill.percent}%` }" />
                  </div>
                </li>
                <li v-if="!skillItems.length" class="empty">完成练习后，系统会生成八大学域技能分布。</li>
              </ul>
            </div>
          </article>

          <article class="growth-card timeline-card">
            <header><span>成长轨迹</span><h3>近期记录</h3></header>
            <ul class="timeline">
              <li v-for="event in growthEvents" :key="event.id" class="timeline__item">
                <time>{{ event.date }}</time>
                <div>
                  <button
                    v-if="event.kind === 'emergency' && event.record"
                    type="button"
                    class="timeline__toggle"
                    @click="toggleEmergencyEntry(event.record)"
                  >
                    <strong>{{ event.title }}</strong>
                    <span>{{ expandedEmergencyIds.has(event.record.id) ? '收起' : '展开' }}</span>
                  </button>
                  <strong v-else>{{ event.title }}</strong>
                  <p v-if="event.kind !== 'emergency' || (event.record && expandedEmergencyIds.has(event.record.id))">
                    {{ event.description }}
                  </p>
                  <button
                    v-if="event.kind === 'emergency' && event.record && expandedEmergencyIds.has(event.record.id)"
                    type="button"
                    class="timeline__detail"
                    @click="openEmergencyDetail(event.record)"
                  >
                    查看详情
                  </button>
                </div>
              </li>
              <li v-if="!growthEvents.length" class="empty">完成委托或试炼后，成长轨迹会出现在这里。</li>
            </ul>
          </article>

          <article v-if="learningReport" class="growth-card radar-card" data-tour="student-knowledge-graph">
            <header><span>学习报告</span><h3>知识雷达</h3></header>
            <plex-radar-chart :dimensions="radarLabels" :values="radarValues" title="知识点掌握度" color="#34e6c5" />
            <p class="report-summary">
              {{ learningReport.summary.level_label }} · 探索指数 {{ learningReport.summary.index }}
              · 近 7 日正确率 {{ learningReport.summary.correct_rate }}%
            </p>
          </article>

          <article v-if="learningReport" class="growth-card chart-card mistake-card">
            <header><span>学习报告</span><h3>错题分析</h3></header>
            <div v-if="mistakePieData.length" class="chart-wrap chart-wrap--hud">
              <span class="chart-wrap__ring chart-wrap__ring--outer" aria-hidden="true" />
              <span class="chart-wrap__ring chart-wrap__ring--inner" aria-hidden="true" />
              <plex-pie-chart :data="mistakePieData" sci-fi />
            </div>
            <p v-else class="empty">完成试炼并产生错题后，这里会展示错题类型分布。</p>
          </article>

          <div
            v-if="learningReport && (trendDays.length || domainBarLabels.length)"
            class="growth-charts-row"
          >
            <article v-if="trendDays.length" class="growth-card chart-card">
              <header><span>学习趋势</span><h3>近 7 天练习</h3></header>
              <div class="chart-wrap">
                <plex-line-chart
                  :x-data="trendDays"
                  :series="[
                    { name: '正确率(%)', data: trendCorrect, color: '#34e6c5' },
                    { name: '练习次数', data: trendCount, color: '#38bdf8' },
                  ]"
                />
              </div>
            </article>

            <article v-if="domainBarLabels.length" class="growth-card chart-card">
              <header><span>星域掌握</span><h3>知识域进度</h3></header>
              <div class="chart-wrap">
                <plex-bar-chart
                  :x-data="domainBarLabels"
                  :series="[{ name: '掌握度', data: domainBarValues, color: '#34e6c5' }]"
                />
              </div>
            </article>
          </div>
        </section>

        <class-file-exchange-panel role="student" :class-id="classInfo?.id ?? null" />
      </template>
    </main>

    <EmergencyMissionGrowthModal v-model:show="detailOpen" :record="detailRecord" />
  </DashboardShell>
</template>

<style scoped>
.growth-page{width:100%;padding:0.75rem var(--plex-page-gutter-x) 2rem;overflow:visible}.growth-state{padding:2rem 0;color:rgba(190,208,224,.72)}.growth-state--error{display:flex;align-items:center;gap:.75rem;color:#ffb4b4}.growth-hero{display:flex;justify-content:space-between;gap:1.5rem;padding:1.5rem;margin-bottom:1rem;border:1px solid rgba(52,230,197,.16);border-radius:16px;background:rgba(3,16,28,.86)}.eyebrow{margin:0 0 .35rem;color:#39e6c7;font-size:.72rem;letter-spacing:.12em}.growth-hero h2{margin:0;color:#f5fbff;font-size:1.65rem}.growth-meta{display:flex;flex-wrap:wrap;gap:.65rem 1rem;margin:.55rem 0 0;color:rgba(214,230,244,.72);font-size:.9rem}.growth-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.75rem;min-width:min(100%,320px)}.tech-stat-card{position:relative;overflow:hidden;padding:.85rem 1rem .9rem 1.15rem;border:1px solid rgba(52,230,197,.18);border-radius:12px;background:linear-gradient(135deg,rgba(52,230,197,.06),rgba(3,16,28,.55) 58%),rgba(3,16,28,.72);backdrop-filter:blur(10px);box-shadow:inset 0 1px 0 rgba(255,255,255,.04),0 0 20px rgba(52,230,197,.04);transition:border-color .25s ease,box-shadow .25s ease}.tech-stat-card::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:linear-gradient(180deg,#34e6c5,#0891b2);box-shadow:0 0 14px rgba(52,230,197,.65)}.tech-stat-card::after{content:'';position:absolute;inset:0;background:repeating-linear-gradient(135deg,rgba(52,230,197,.03) 0 1px,transparent 1px 14px);opacity:.45;pointer-events:none}.tech-stat-card:hover{border-color:rgba(52,230,197,.38);box-shadow:inset 0 1px 0 rgba(255,255,255,.06),0 0 28px rgba(52,230,197,.12)}.tech-stat-card--rank::before{background:linear-gradient(180deg,#7bf8ff,#34e6c5)}.tech-stat-card--rate::before{background:linear-gradient(180deg,#818cf8,#38bdf8)}.tech-stat-card__corner{position:absolute;width:10px;height:10px;border-color:rgba(52,230,197,.55);border-style:solid;opacity:.75}.tech-stat-card__corner--tl{top:6px;left:8px;border-width:1px 0 0 1px}.tech-stat-card__corner--br{right:8px;bottom:6px;border-width:0 1px 1px 0}.tech-stat-card small{display:block;color:#88a3b5;font-size:.78rem;letter-spacing:.04em}.tech-stat-card strong{display:block;margin-top:.35rem;color:#edf8fb;font-family:'JetBrains Mono','Consolas',monospace;font-size:1.15rem;font-weight:700;text-shadow:0 0 16px rgba(52,230,197,.35)}.growth-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem;margin-bottom:1rem}.growth-card{padding:1.2rem;border:1px solid rgba(52,230,197,.16);border-radius:16px;background:rgba(3,16,28,.86)}.growth-card header span{color:#39e6c7;font-size:.72rem;letter-spacing:.12em}.growth-card h3{margin:.35rem 0;color:#f5fbff}.growth-card p{color:#a9c2d0;line-height:1.55}.skill-card{min-height:320px;display:flex;flex-direction:column}.skill-hud{position:relative;flex:1;display:flex;flex-direction:column;padding:.85rem;border:1px solid rgba(52,230,197,.14);border-radius:14px;background:linear-gradient(145deg,rgba(52,230,197,.05),rgba(3,16,28,.72)),repeating-linear-gradient(135deg,rgba(52,230,197,.03) 0 1px,transparent 1px 16px);backdrop-filter:blur(8px)}.skill-hud__corner{position:absolute;width:12px;height:12px;border-color:rgba(52,230,197,.55);border-style:solid;opacity:.8}.skill-hud__corner--tl{top:8px;left:8px;border-width:1px 0 0 1px}.skill-hud__corner--br{right:8px;bottom:8px;border-width:0 1px 1px 0}.skill-grid{margin:0;padding:0;list-style:none;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.65rem;flex:1;align-content:start}.skill-grid__item{padding:.65rem .75rem;border:1px solid rgba(52,230,197,.12);border-radius:10px;background:rgba(2,10,18,.55)}.skill-grid__head{display:flex;justify-content:space-between;gap:.5rem;margin-bottom:.45rem}.skill-grid__head strong{color:#edf8fb;font-size:.84rem}.skill-grid__head em{font-style:normal;color:#34e6c5;font-family:'JetBrains Mono','Consolas',monospace;font-size:.78rem;font-weight:700}.skill-grid__track{height:7px;border-radius:999px;background:rgba(148,163,184,.18);overflow:hidden}.skill-grid__fill{display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg,#0891b2,#34e6c5 55%,#5ffff3);box-shadow:0 0 12px rgba(52,230,197,.45)}.timeline li{display:grid;grid-template-columns:5.5rem 1fr;gap:.75rem;padding:.65rem 0;border-bottom:1px solid rgba(142,177,192,.12)}.timeline__toggle{display:flex;align-items:center;justify-content:space-between;gap:.5rem;width:100%;padding:0;border:0;background:transparent;color:inherit;text-align:left;cursor:pointer}.timeline__toggle span{color:#39e6c7;font-size:.76rem;font-weight:600}.timeline__detail{margin-top:.45rem;padding:.35rem .75rem;border:1px solid rgba(52,230,197,.35);border-radius:999px;background:rgba(52,230,197,.08);color:#34e6c5;font-size:.78rem;cursor:pointer}.timeline time{color:#88a3b5;font-size:.78rem}.timeline p{margin:.15rem 0 0;color:#8da7b6;font-size:.82rem}.chart-card{min-height:280px}.chart-wrap{height:220px}.chart-wrap--hud{position:relative;display:grid;place-items:center}.chart-wrap--hud::before{content:'';position:absolute;width:180px;aspect-ratio:1;border-radius:50%;background:radial-gradient(circle,rgba(52,230,197,.12),transparent 68%);filter:blur(8px);pointer-events:none}.chart-wrap__ring{position:absolute;border-radius:50%;border:1px dashed rgba(52,230,197,.18);pointer-events:none}.chart-wrap__ring--outer{width:min(210px,78%);aspect-ratio:1;animation:chart-ring-spin 18s linear infinite}.chart-wrap__ring--inner{width:min(150px,56%);aspect-ratio:1;border-color:rgba(129,140,248,.22);animation:chart-ring-spin 24s linear infinite reverse}.mistake-card{background:linear-gradient(180deg,rgba(52,230,197,.03),rgba(3,16,28,.88))}.report-summary{margin-top:.75rem;color:#8da7b6;font-size:.84rem}.empty{color:#8da7b6;font-size:.85rem}.growth-charts-row{grid-column:span 2;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}@keyframes chart-ring-spin{to{transform:rotate(360deg)}}@media(max-width:900px){.growth-hero,.growth-stats,.growth-grid{grid-template-columns:1fr}.growth-charts-row{grid-column:auto;grid-template-columns:1fr}}
</style>
