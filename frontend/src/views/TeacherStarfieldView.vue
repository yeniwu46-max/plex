<script setup lang="ts">
import { computed, ref } from 'vue'
import { NButton, NIcon, NSelect, type SelectOption } from 'naive-ui'
import { CompassOutline, InformationCircleOutline } from '@vicons/ionicons5'
import TeacherDashboardShell from '../components/layout/TeacherDashboardShell.vue'
import KnowledgeOrbitMap from '../components/teacher/KnowledgeOrbitMap.vue'
import SparklineCard from '../components/teacher/SparklineCard.vue'
import StarfieldDomainDrawer from '../components/teacher/StarfieldDomainDrawer.vue'
import TeacherInsightCard from '../components/teacher/TeacherInsightCard.vue'
import { useTeacherOverviewInjected } from '../composables/useTeacherOverview'
import {
  buildClassStarfieldNodes,
  buildRiskCopy,
  buildRiskTrend,
  buildStarfieldInsight,
  buildStarfieldKpis,
  polylineFromPoints,
  type OrbitNode,
} from '../data/teacherStarfield'

const domainFilter = ref<string | null>(null)
const drawerOpen = ref(false)
const selectedNode = ref<OrbitNode | null>(null)

const { overview, loading, errorMessage, hasSelectedClass, attentionStudents, loadOverview } =
  useTeacherOverviewInjected()

const regionOptions: SelectOption[] = [
  { label: '全部星域', value: 'all' },
  { label: '算法基础', value: 'algo' },
  { label: '数据结构', value: 'ds' },
  { label: '前端开发', value: 'fe' },
  { label: '后端开发', value: 'be' },
  { label: '数据库', value: 'db' },
  { label: '计算机基础', value: 'cs' },
]

const allNodes = computed(() => buildClassStarfieldNodes(overview.value))
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

    <section class="starfield-page" aria-label="星域观测">
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
        <section class="starfield-page__map teacher-panel">
          <header class="teacher-panel__head starfield-page__map-head">
            <h2 class="teacher-panel__title">知识星域全景</h2>
            <n-icon :component="InformationCircleOutline" />
          </header>
          <knowledge-orbit-map :nodes="orbitNodes" title="" @select="onNodeSelect" />
        </section>

        <teacher-insight-card
          class="starfield-page__insight"
          title="AI 洞察"
          :rate="insight.rate"
          :subject="insight.subject"
          :copy="insight.copy"
        />

        <section class="starfield-page__risk teacher-panel">
          <header class="teacher-panel__head">
            <h2 class="teacher-panel__title">风险波动</h2>
          </header>
          <p class="starfield-page__risk-copy">{{ riskCopy }}</p>
          <svg class="starfield-page__risk-chart" viewBox="0 0 280 90" role="img" aria-label="风险波动趋势">
            <line v-for="line in 3" :key="line" x1="0" x2="278" :y1="line * 28" :y2="line * 28" />
            <polyline :points="riskPolyline" />
          </svg>
        </section>

        <div class="starfield-page__kpis">
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
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(300px, 0.85fr);
  grid-template-rows: minmax(480px, 1fr) auto auto;
  gap: 1.1rem;
  height: 100%;
  overflow: auto;
  padding: 0 var(--plex-page-gutter-x) 2rem;
}

.starfield-page__state {
  grid-column: 1 / -1;
}

.starfield-page__map {
  grid-row: span 2;
  padding: 1.25rem 1.5rem 1rem;
  min-height: 520px;
}

.starfield-page__map-head {
  margin-bottom: 0.25rem;
}

.starfield-page__insight {
  grid-column: 2;
  grid-row: 1;
}

.starfield-page__risk {
  grid-column: 2;
  grid-row: 2;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
}

.starfield-page__risk-copy {
  margin: 0 0 0.75rem;
  color: var(--teacher-muted);
  font-size: 0.88rem;
  line-height: 1.6;
}

.starfield-page__risk-chart {
  width: 100%;
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
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.1rem;
}

@media (max-width: 1100px) {
  .starfield-page {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
  }

  .starfield-page__map {
    grid-row: auto;
    min-height: 560px;
  }

  .starfield-page__insight,
  .starfield-page__risk {
    grid-column: 1;
    grid-row: auto;
  }

  .starfield-page__kpis {
    grid-template-columns: 1fr;
  }
}
</style>
