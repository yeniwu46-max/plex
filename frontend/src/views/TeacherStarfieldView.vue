<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { NButton, NIcon, NSelect, type SelectOption } from 'naive-ui'
import { CompassOutline, InformationCircleOutline } from '@vicons/ionicons5'
import TeacherDashboardShell from '../components/layout/TeacherDashboardShell.vue'
import KnowledgeOrbitMap from '../components/teacher/KnowledgeOrbitMap.vue'
import PlexKnowledgeGraph from '../components/shared/PlexKnowledgeGraph.vue'
import SparklineCard from '../components/teacher/SparklineCard.vue'
import StarfieldDomainDrawer from '../components/teacher/StarfieldDomainDrawer.vue'
import TeacherInsightCard from '../components/teacher/TeacherInsightCard.vue'
import { fetchTeacherClassStats } from '../api/teacherOverview'
import { useTeacherOverviewInjected } from '../composables/useTeacherOverview'
import { STAR_PATH_TABS } from '../data/starPathDomains'
import {
  buildClassStarfieldNodes,
  buildRiskCopy,
  buildRiskTrend,
  buildStarfieldInsight,
  buildStarfieldKpis,
  polylineFromPoints,
  type OrbitNode,
} from '../data/teacherStarfield'
import { fetchClassKnowledgeGraph } from '../api/knowledgeGraph'
import { KG_NODES, KG_EDGES, type KgEdge, type KgNode } from '../data/knowledgeGraphData'

const domainFilter = ref<string | null>(null)
const drawerOpen = ref(false)
const selectedNode = ref<OrbitNode | null>(null)

const { overview, loading, errorMessage, hasSelectedClass, attentionStudents, loadOverview, selectedClassId } =
  useTeacherOverviewInjected()

const classStats = ref<Awaited<ReturnType<typeof fetchTeacherClassStats>> | null>(null)
const kgNodes = ref<KgNode[]>(KG_NODES)
const kgEdges = ref<KgEdge[]>(KG_EDGES)
const kgLoading = ref(false)

async function loadClassKnowledgeGraph() {
  if (!selectedClassId.value) return
  kgLoading.value = true
  try {
    const data = await fetchClassKnowledgeGraph(selectedClassId.value)
    kgNodes.value = data.nodes
    kgEdges.value = data.edges
  } catch {
    kgNodes.value = KG_NODES
    kgEdges.value = KG_EDGES
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
})

watch(selectedClassId, () => {
  void loadClassStats()
  void loadClassKnowledgeGraph()
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
const insight = computed(() => buildStarfieldInsight(overview.value, allNodes.value))
const kpis = computed(() => buildStarfieldKpis(overview.value))
const riskPoints = computed(() => buildRiskTrend(overview.value))
const riskPolyline = computed(() => polylineFromPoints(riskPoints.value, 280, 90))
const riskCopy = computed(() => buildRiskCopy(overview.value, riskPoints.value))

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
    page-title="星域观测"
    page-subtitle="STARFIELD ANALYTICS · 观测班级知识星域掌握与风险波动"
    toolbar-label="星域观测筛选"
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
        <section class="starfield-page__map teacher-panel teacher-quad-layout__primary">
          <header class="teacher-panel__head starfield-page__map-head">
            <h2 class="teacher-panel__title">知识星域全景</h2>
            <n-icon :component="InformationCircleOutline" />
          </header>
          <knowledge-orbit-map :nodes="orbitNodes" title="" @select="onNodeSelect" />
        </section>

        <teacher-insight-card
          class="starfield-page__insight teacher-quad-layout__side-top"
          title="AI 洞察"
          :rate="insight.rate"
          :subject="insight.subject"
          :copy="insight.copy"
        />

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
          <plex-knowledge-graph :nodes="kgNodes" :edges="kgEdges" mode="teacher" height="420px" />
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

  .starfield-page__risk {
    min-height: 240px;
  }

  .starfield-page__kpis {
    grid-template-columns: 1fr;
    grid-row: auto;
  }
}
</style>
