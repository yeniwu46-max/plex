<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NIcon, NSelect, NSpin, type SelectOption } from 'naive-ui'
import { CompassOutline, InformationCircleOutline, SparklesOutline } from '@vicons/ionicons5'
import TeacherDashboardShell from '../components/layout/TeacherDashboardShell.vue'
import KnowledgeOrbitMap from '../components/teacher/KnowledgeOrbitMap.vue'
import PlexKnowledgeGraph from '../components/shared/PlexKnowledgeGraph.vue'
import PlexTeacherSuggestionPanel from '../components/agent/PlexTeacherSuggestionPanel.vue'
import SparklineCard from '../components/teacher/SparklineCard.vue'
import StarfieldDomainDrawer from '../components/teacher/StarfieldDomainDrawer.vue'
import { fetchTeacherClassStats } from '../api/teacherOverview'
import { formatHttpError } from '../api/http'
import { fetchClassDiagnosis, type ClassDiagnosisResult } from '../api/teacherAgents'
import { useTeacherOverviewInjected } from '../composables/useTeacherOverview'
import { STAR_PATH_TABS } from '../data/starPathDomains'
import {
  buildClassStarfieldNodes,
  buildRiskCopy,
  buildRiskTrend,
  buildStarfieldKpis,
  polylineFromPoints,
  type OrbitNode,
} from '../data/teacherStarfield'
import { fetchClassKnowledgeGraph, type KnowledgeGraphSummary } from '../api/knowledgeGraph'
import { KG_NODES, KG_EDGES, type KgEdge, type KgNode } from '../data/knowledgeGraphData'

const router = useRouter()
const route = useRoute()
const domainFilter = ref<string | null>(null)
const drawerOpen = ref(false)
const selectedNode = ref<OrbitNode | null>(null)

const { overview, loading, errorMessage, hasSelectedClass, attentionStudents, loadOverview, selectedClassId } =
  useTeacherOverviewInjected()

const classStats = ref<Awaited<ReturnType<typeof fetchTeacherClassStats>> | null>(null)
const kgNodes = ref<KgNode[]>(KG_NODES)
const kgEdges = ref<KgEdge[]>(KG_EDGES)
const kgSummary = ref<KnowledgeGraphSummary | null>(null)
const kgLoading = ref(false)

const diagnosis = ref<ClassDiagnosisResult | null>(null)
const diagnosisLoading = ref(false)
const diagnosisError = ref('')

async function runClassDiagnosis() {
  if (!selectedClassId.value || diagnosisLoading.value) return
  diagnosisLoading.value = true
  diagnosisError.value = ''
  try {
    diagnosis.value = await fetchClassDiagnosis(selectedClassId.value)
  } catch (error) {
    diagnosis.value = null
    diagnosisError.value = formatHttpError(error, '班级诊断失败')
  } finally {
    diagnosisLoading.value = false
  }
}

function goExplorer(studentId: number) {
  void router.push({ path: '/teacher/starfield', query: { studentId: String(studentId) } })
}

const focusedStudentId = computed(() => {
  const raw = route.query.studentId
  const id = raw ? Number(raw) : NaN
  return Number.isFinite(id) ? id : null
})

async function focusStudentFromQuery() {
  const studentId = focusedStudentId.value
  if (!studentId) return
  if (!diagnosis.value && !diagnosisLoading.value) {
    await runClassDiagnosis()
  }
  await nextTick()
  document
    .querySelector(`[data-student-id="${studentId}"]`)
    ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

async function loadClassKnowledgeGraph() {
  if (!selectedClassId.value) return
  kgLoading.value = true
  try {
    const data = await fetchClassKnowledgeGraph(selectedClassId.value)
    kgNodes.value = data.nodes
    kgEdges.value = data.edges
    kgSummary.value = data.summary ?? null
  } catch {
    kgNodes.value = KG_NODES
    kgEdges.value = KG_EDGES
    kgSummary.value = null
  } finally {
    kgLoading.value = false
  }
}

async function loadClassStats() {
  if (!selectedClassId.value) {
    classStats.value = null
    return
  }
  try {
    classStats.value = await fetchTeacherClassStats(selectedClassId.value)
  } catch {
    classStats.value = null
  }
}

onMounted(() => {
  void loadClassStats()
  void loadClassKnowledgeGraph()
  void runClassDiagnosis()
  void focusStudentFromQuery()
})

watch(focusedStudentId, () => {
  void focusStudentFromQuery()
})

watch(selectedClassId, () => {
  diagnosis.value = null
  diagnosisError.value = ''
  void loadClassStats()
  void loadClassKnowledgeGraph()
  void runClassDiagnosis()
})

const regionOptions: SelectOption[] = [
  { label: '全部星域', value: 'all' },
  ...STAR_PATH_TABS.filter((tab) => tab.key !== 'all').map((tab) => ({
    label: tab.label,
    value: tab.key,
  })),
]

const allNodes = computed(() => buildClassStarfieldNodes(overview.value, classStats.value))
const orbitNodes = computed(() => {
  if (!domainFilter.value || domainFilter.value === 'all') return allNodes.value
  return allNodes.value.filter((node) => node.domainKey === domainFilter.value)
})
const kpis = computed(() => buildStarfieldKpis(overview.value))
const riskPoints = computed(() => buildRiskTrend(overview.value))
const riskPolyline = computed(() => polylineFromPoints(riskPoints.value, 280, 90))
const riskCopy = computed(() => buildRiskCopy(overview.value, riskPoints.value))
const topWeakNodes = computed(() => kgSummary.value?.top_weak_nodes.slice(0, 3) ?? [])
const heatRankNodes = computed(() => kgSummary.value?.top_weak_nodes ?? [])

const classAvgScore = computed(() => {
  const nodes = allNodes.value
  if (!nodes.length) return overview.value?.metrics?.avg_today_completion ?? 0
  return Math.round(nodes.reduce((sum, n) => sum + n.score, 0) / nodes.length)
})

function onNodeSelect(node: OrbitNode) {
  selectedNode.value = node
  drawerOpen.value = true
}

</script>

<template>
  <TeacherDashboardShell
    active-nav="starfield"
    page-title="星域诊断"
    page-subtitle="STARFIELD DIAGNOSIS · 知识图谱掌握度与班级一键学情诊断"
    toolbar-label="星域诊断筛选"
    show-period
    hide-search
  >
    <template #toolbar-filters>
      <n-select
        :value="domainFilter ?? 'all'"
        :options="regionOptions"
        class="teacher-toolbar__filter"
        @update:value="domainFilter = $event === 'all' ? null : String($event)"
      />
    </template>

    <section class="starfield-page teacher-page teacher-quad-layout" aria-label="星域观测">
      <div v-if="loading" class="teacher-state-panel starfield-page__state">正在同步星域数据…</div>
      <div v-else-if="errorMessage" class="teacher-state-panel teacher-state-panel--error starfield-page__state">
        <span>{{ errorMessage }}</span>
        <n-button secondary @click="loadOverview()">重试</n-button>
      </div>
      <div v-else-if="!hasSelectedClass" class="teacher-state-panel starfield-page__state">
        <n-icon :component="CompassOutline" />
        <span>当前教师账号还没有负责的班级。</span>
      </div>
      <template v-else>
        <section class="starfield-page__map teacher-panel teacher-quad-layout__primary" data-tour="teacher-student-profile">
          <header class="teacher-panel__head starfield-page__map-head">
            <h2 class="teacher-panel__title">知识星域全景</h2>
            <n-icon :component="InformationCircleOutline" />
          </header>
          <knowledge-orbit-map :nodes="orbitNodes" title="" @select="onNodeSelect" />
        </section>

        <section
          class="starfield-page__diagnosis teacher-panel teacher-quad-layout__side-top"
          aria-label="班级一键学情诊断"
          data-tour="teacher-ai-suggestion"
        >
          <header class="teacher-panel__head starfield-page__diagnosis-head">
            <h2 class="teacher-panel__title">班级一键学情诊断</h2>
            <n-button
              size="tiny"
              type="warning"
              :loading="diagnosisLoading"
              :disabled="!selectedClassId"
              @click="runClassDiagnosis"
            >
              <template #icon><n-icon :component="SparklesOutline" /></template>
              重新诊断
            </n-button>
          </header>

          <div v-if="diagnosisLoading && !diagnosis" class="starfield-page__diagnosis-loading">
            <n-spin size="small" />
            <span>正在聚合班级错题与知识图谱…</span>
          </div>
          <p v-else-if="diagnosisError" class="starfield-page__diagnosis-error">{{ diagnosisError }}</p>
          <template v-else-if="diagnosis">
            <div class="starfield-page__diagnosis-meta">
              <span>{{ diagnosis.studentCount }} 名学生</span>
              <span v-if="diagnosis.weakNodes.length">{{ diagnosis.weakNodes.length }} 个薄弱知识点</span>
              <span class="starfield-page__diagnosis-backend">{{ diagnosis.backend || 'agent' }}</span>
            </div>

            <div v-if="diagnosis.attentionStudents.length" class="starfield-page__attention">
              <h3>重点关注</h3>
              <div class="starfield-page__attention-chips">
                <button
                  v-for="stu in diagnosis.attentionStudents"
                  :key="stu.id"
                  type="button"
                  class="starfield-page__attention-chip"
                  :class="{ 'starfield-page__attention-chip--focus': focusedStudentId === stu.id }"
                  :data-student-id="stu.id"
                  @click="goExplorer(stu.id)"
                >
                  <strong>{{ stu.name }}</strong>
                  <small>{{ stu.activeCount }} 错题</small>
                </button>
              </div>
            </div>

            <plex-teacher-suggestion-panel
              class="starfield-page__diagnosis-panel"
              :result="diagnosis.suggestion"
              :loading="false"
              :error="''"
            />
          </template>
          <p v-else class="starfield-page__diagnosis-empty">点击「重新诊断」生成班级学情诊断。</p>
        </section>

        <section class="starfield-page__risk teacher-panel teacher-quad-layout__side-bottom">
          <header class="teacher-panel__head">
            <h2 class="teacher-panel__title">风险波动</h2>
          </header>
          <p class="starfield-page__risk-copy">{{ riskCopy }}</p>
          <svg class="starfield-page__risk-chart" viewBox="0 0 280 90" role="img" aria-label="风险波动趋势">
            <line v-for="line in 3" :key="line" x1="0" x2="278" :y1="line * 28" :y2="line * 28" />
            <polyline :points="riskPolyline" />
          </svg>
        </section>

        <section class="starfield-page__kg teacher-panel teacher-quad-layout__full-row">
          <header class="teacher-panel__head">
            <h2 class="teacher-panel__title">班级知识图谱</h2>
            <span v-if="kgLoading" class="starfield-page__kg-loading">同步中…</span>
          </header>
          <div v-if="topWeakNodes.length" class="starfield-page__kg-summary">
            <div>
              <span>高风险知识点 Top 3</span>
              <strong>{{ topWeakNodes.map((node) => node.label).join(' / ') }}</strong>
            </div>
            <div>
              <span>覆盖学生</span>
              <strong>{{ kgSummary?.student_count ?? 0 }} 人</strong>
            </div>
            <div>
              <span>建议复盘方向</span>
              <strong>{{ topWeakNodes[0]?.label }} 相关错题讲评与补救练习</strong>
            </div>
          </div>
          <plex-knowledge-graph :nodes="kgNodes" :edges="kgEdges" mode="teacher" height="420px" />
          <div v-if="heatRankNodes.length" class="starfield-page__kg-rank" aria-label="班级薄弱知识点排行">
            <article v-for="node in heatRankNodes" :key="node.id" class="starfield-page__kg-rank-item">
              <div>
                <strong>{{ node.label }}</strong>
                <span>{{ node.fail_count }} 次失败 / {{ node.affected_student_count }} 人受影响</span>
              </div>
              <b>{{ node.weak_score }}</b>
            </article>
          </div>
        </section>

        <div class="starfield-page__kpis teacher-quad-layout__full-row">
          <sparkline-card
            v-for="item in kpis"
            :key="item.key"
            :label="item.label"
            :value="item.value"
            :delta="item.delta"
            :points="item.points"
          />
        </div>
      </template>
    </section>

    <starfield-domain-drawer
      v-model:show="drawerOpen"
      :node="selectedNode"
      :class-avg-score="classAvgScore"
      :attention-students="attentionStudents"
    />
  </TeacherDashboardShell>
</template>

<style scoped>
.starfield-page {
  grid-template-rows: minmax(480px, 1fr) minmax(280px, auto) auto auto;
}

.starfield-page__state {
  grid-column: 1 / -1;
}

.starfield-page__diagnosis {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  padding: 1.25rem;
  min-height: 0;
  overflow: auto;
}

.starfield-page__diagnosis-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
}

.starfield-page__diagnosis-loading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--teacher-muted);
  font-size: 0.84rem;
}

.starfield-page__diagnosis-error {
  margin: 0;
  color: #fca5a5;
  font-size: 0.84rem;
}

.starfield-page__diagnosis-empty {
  margin: 0;
  color: var(--teacher-muted);
  font-size: 0.84rem;
}

.starfield-page__diagnosis-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  font-size: 0.72rem;
  color: var(--teacher-muted);
}

.starfield-page__diagnosis-meta span {
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  background: rgba(8, 14, 22, 0.55);
  border: 1px solid rgba(130, 212, 255, 0.12);
}

.starfield-page__diagnosis-backend {
  color: #fdba74;
}

.starfield-page__attention h3 {
  margin: 0 0 0.4rem;
  color: #fdba74;
  font-size: 0.82rem;
  font-weight: 650;
}

.starfield-page__attention-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.starfield-page__attention-chip {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 0.3rem 0.6rem;
  border: 1px solid rgba(255, 85, 77, 0.3);
  border-radius: 12px;
  background: rgba(40, 12, 12, 0.4);
  color: var(--teacher-text);
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease;
}

.starfield-page__attention-chip:hover,
.starfield-page__attention-chip--focus {
  border-color: rgba(255, 85, 77, 0.6);
  background: rgba(60, 16, 16, 0.6);
  box-shadow: 0 0 0 2px rgba(251, 146, 60, 0.25);
}

.starfield-page__attention-chip strong {
  font-size: 0.78rem;
}

.starfield-page__attention-chip small {
  color: #fca5a5;
  font-size: 0.68rem;
}

.starfield-page__map {
  padding: 1.25rem 1.5rem 1rem;
}

.starfield-page__map-head {
  margin-bottom: 0.25rem;
}

.starfield-page__risk {
  display: flex;
  min-height: 280px;
  flex-direction: column;
  padding: 1.25rem;
  overflow: visible;
}

.starfield-page__risk.teacher-panel {
  overflow: visible;
}

.starfield-page__risk .teacher-panel__head {
  flex-shrink: 0;
  overflow: visible;
  margin-bottom: 0.35rem;
}

.starfield-page__risk .teacher-panel__title {
  white-space: nowrap;
  overflow: visible;
  line-height: 1.35;
}

.starfield-page__kg {
  grid-row: 3;
  padding: 1rem 1.25rem 1.25rem;
  overflow: visible;
}

.starfield-page__kg.teacher-panel {
  overflow: visible;
}

.starfield-page__kg .teacher-panel__head {
  overflow: visible;
  margin-bottom: 0.75rem;
}

.starfield-page__kg .teacher-panel__title {
  white-space: nowrap;
  overflow: visible;
  line-height: 1.35;
}

.starfield-page__kg-loading {
  color: var(--teacher-muted);
  font-size: 0.78rem;
}

.starfield-page__kg-summary {
  display: grid;
  grid-template-columns: 1.1fr 0.55fr 1.35fr;
  gap: 0.6rem;
  margin: 0 0 0.8rem;
}

.starfield-page__kg-summary div {
  padding: 0.65rem 0.75rem;
  border-radius: 12px;
  border: 1px solid rgba(249, 115, 22, 0.18);
  background: linear-gradient(135deg, rgba(67, 20, 7, 0.42), rgba(15, 23, 42, 0.45));
}

.starfield-page__kg-summary span,
.starfield-page__kg-rank-item span {
  display: block;
  color: var(--teacher-muted);
  font-size: 0.72rem;
}

.starfield-page__kg-summary strong {
  display: block;
  margin-top: 0.24rem;
  color: #fed7aa;
  font-size: 0.86rem;
  line-height: 1.35;
}

.starfield-page__kg-rank {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.55rem;
  margin-top: 0.8rem;
}

.starfield-page__kg-rank-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.6rem 0.7rem;
  border-radius: 12px;
  border: 1px solid rgba(248, 113, 113, 0.22);
  background: rgba(127, 29, 29, 0.18);
}

.starfield-page__kg-rank-item strong {
  display: block;
  color: #fecaca;
  font-size: 0.82rem;
}

.starfield-page__kg-rank-item b {
  color: #fb923c;
  font-size: 1rem;
}

.starfield-page__risk-copy {
  margin: 0 0 0.75rem;
  color: var(--teacher-muted);
  font-size: 0.88rem;
  line-height: 1.6;
  flex: 1 1 auto;
  min-height: 0;
}

.starfield-page__risk-chart {
  display: block;
  width: 100%;
  height: 96px;
  flex-shrink: 0;
  margin-top: auto;
}

.starfield-page__risk-chart line {
  stroke: rgba(221, 230, 239, 0.07);
}

.starfield-page__risk-chart polyline {
  fill: none;
  stroke: #ff554d;
  stroke-width: 2.5;
  filter: drop-shadow(0 0 8px rgba(255, 85, 77, 0.35));
}

.starfield-page__kpis {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--teacher-quad-gap, 1.1rem);
  grid-row: 4;
}

@media (max-width: 1100px) {
  .starfield-page {
    grid-template-rows: auto;
  }

  .starfield-page__kg {
    grid-row: auto;
  }

  .starfield-page__kg-summary,
  .starfield-page__kg-rank {
    grid-template-columns: 1fr;
  }

  .starfield-page__risk {
    min-height: 240px;
  }

  .starfield-page__kpis {
    grid-template-columns: 1fr;
    grid-row: auto;
  }
}
</style>
