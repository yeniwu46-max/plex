<script setup lang="ts">
import { computed, inject, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { TEACHER_SHELL_SEARCH_KEY } from '../composables/useTeacherOverview'
import { NButton, NIcon } from 'naive-ui'
import { CompassOutline } from '@vicons/ionicons5'
import TeacherDashboardShell from '../components/layout/TeacherDashboardShell.vue'
import ExplorerKnowledgePanel from '../components/teacher/ExplorerKnowledgePanel.vue'
import ExplorerListPanel from '../components/teacher/ExplorerListPanel.vue'
import ExplorerMemberManage from '../components/teacher/ExplorerMemberManage.vue'
import ExplorerProfileHero from '../components/teacher/ExplorerProfileHero.vue'
import ExplorerQuestPanel from '../components/teacher/ExplorerQuestPanel.vue'
import ExplorerStatusAside from '../components/teacher/ExplorerStatusAside.vue'
import ExplorerTrialPanel from '../components/teacher/ExplorerTrialPanel.vue'
import GrowthLineChart from '../components/teacher/GrowthLineChart.vue'
import { fetchStudentAchievements } from '../api/teacherStudentDetail'
import type { UserAchievementRecord } from '../api/studentOverview'
import { useTeacherOverviewInjected } from '../composables/useTeacherOverview'
import {
  buildAiObservation,
  buildExplorerRadarFromStudent,
  buildExplorerStats,
  buildGrowthSeriesFromHeatmap,
  buildOverallStatus,
  buildRiskTodos,
} from '../data/teacherExplorerProfile'
import type { TeacherStudentRow } from '../api/teacherOverview'

const route = useRoute()
const shellSearch = inject(TEACHER_SHELL_SEARCH_KEY, null)

const { overview, loading, errorMessage, selectedClassId, period, students, hasSelectedClass, loadOverview } =
  useTeacherOverviewInjected()

const selectedStudentId = ref<number | null>(null)
const search = ref('')
const statusFilter = ref<string | null>(null)
const domainFilter = ref<string | null>(null)
const sortBy = ref('activity')
const pageMode = ref<'archive' | 'manage'>('archive')
const detailTab = ref<'growth' | 'knowledge' | 'trial' | 'quest'>('growth')

const selectedStudent = computed<TeacherStudentRow | null>(() => {
  if (!selectedStudentId.value) return students.value[0] ?? null
  return students.value.find((s) => s.id === selectedStudentId.value) ?? students.value[0] ?? null
})

const achievements = ref<UserAchievementRecord[]>([])
const achievementsLoading = ref(false)
const achievementsError = ref('')
let achievementsRequestId = 0

const selectedHeatmapRow = computed(() => {
  const id = selectedStudent.value?.id
  if (!id) return null
  return overview.value?.heatmap.rows.find((row) => row.user_id === id) ?? null
})

const radar = computed(() =>
  selectedStudent.value ? buildExplorerRadarFromStudent(selectedStudent.value, achievements.value) : [],
)
const growthPoints = computed(() =>
  selectedStudent.value
    ? buildGrowthSeriesFromHeatmap(selectedHeatmapRow.value, period.value, selectedStudent.value)
    : [],
)
const statCards = computed(() => (selectedStudent.value ? buildExplorerStats(selectedStudent.value) : []))
const overallStatus = computed(() => (selectedStudent.value ? buildOverallStatus(selectedStudent.value) : 0))
const todos = computed(() => (selectedStudent.value ? buildRiskTodos(selectedStudent.value) : []))
const aiText = computed(() =>
  selectedStudent.value && radar.value.length
    ? buildAiObservation(selectedStudent.value, radar.value)
    : '选择一名 Explorer 查看 AI 观察。',
)

function applyRouteStudentId() {
  const raw = route.query.studentId
  const parsed = raw ? Number(raw) : NaN
  if (!Number.isNaN(parsed) && students.value.some((s) => s.id === parsed)) {
    selectedStudentId.value = parsed
  }
}

watch(
  students,
  (rows) => {
    if (!rows.length) {
      selectedStudentId.value = null
      return
    }
    applyRouteStudentId()
    if (!rows.some((row) => row.id === selectedStudentId.value)) {
      selectedStudentId.value = rows[0].id
    }
  },
  { immediate: true },
)

watch(
  () => route.query.studentId,
  () => applyRouteStudentId(),
)

async function loadAchievements(userId: number) {
  const requestId = ++achievementsRequestId
  achievementsLoading.value = true
  achievementsError.value = ''
  try {
    const result = await fetchStudentAchievements(userId)
    if (requestId !== achievementsRequestId) return
    achievements.value = result.achievements
  } catch (error) {
    if (requestId !== achievementsRequestId) return
    achievements.value = []
    achievementsError.value = error instanceof Error ? error.message : '成就数据加载失败'
  } finally {
    if (requestId === achievementsRequestId) {
      achievementsLoading.value = false
    }
  }
}

watch(
  selectedStudentId,
  (id) => {
    if (!id) {
      achievements.value = []
      achievementsError.value = ''
      return
    }
    void loadAchievements(id)
  },
  { immediate: true },
)

function onMembersChanged() {
  void loadOverview()
}

if (shellSearch) {
  watch(
    shellSearch,
    (value) => {
      if (search.value !== value) search.value = value
    },
    { immediate: true },
  )
  watch(search, (value) => {
    if (shellSearch.value !== value) shellSearch.value = value
  })
}

</script>

<template>
  <TeacherDashboardShell
    active-nav="explorers"
    page-title="Explorer 档案"
    page-subtitle="EXPLORER ARCHIVES · 查看 Explorer 的成长轨迹与能力画像"
    toolbar-label="Explorer 档案筛选"
    search-placeholder="搜索 Explorer 姓名或编号…"
  >
    <section class="explorers-page" :class="{ 'explorers-page--manage': pageMode === 'manage' }" aria-label="Explorer 档案">
      <div class="explorers-page__mode-tabs" role="tablist" aria-label="档案视图切换">
        <button type="button" role="tab" :aria-selected="pageMode === 'archive'" :class="{ 'is-active': pageMode === 'archive' }" @click="pageMode = 'archive'">
          档案浏览
        </button>
        <button type="button" role="tab" :aria-selected="pageMode === 'manage'" :class="{ 'is-active': pageMode === 'manage' }" @click="pageMode = 'manage'">
          成员管理
        </button>
      </div>

      <div v-if="loading && pageMode === 'archive'" class="teacher-state-panel explorers-page__state">正在加载 Explorer 档案…</div>
      <div v-else-if="errorMessage && pageMode === 'archive'" class="teacher-state-panel teacher-state-panel--error explorers-page__state">
        <span>{{ errorMessage }}</span>
        <n-button secondary @click="loadOverview()">重试</n-button>
      </div>
      <div v-else-if="!hasSelectedClass && pageMode === 'archive'" class="teacher-state-panel explorers-page__state">
        <n-icon :component="CompassOutline" />
        <span>当前教师账号还没有负责的班级。</span>
      </div>

      <explorer-member-manage
        v-else-if="pageMode === 'manage'"
        class="explorers-page__manage"
        :default-class-id="selectedClassId"
        @changed="onMembersChanged"
      />

      <template v-else-if="pageMode === 'archive' && hasSelectedClass">
        <explorer-list-panel
          class="explorers-page__list"
          :students="students"
          :selected-id="selectedStudent?.id ?? null"
          :search="search"
          :status-filter="statusFilter"
          :domain-filter="domainFilter"
          :sort-by="sortBy"
          @update:selected-id="selectedStudentId = $event"
          @update:search="search = $event"
          @update:status-filter="statusFilter = $event"
          @update:domain-filter="domainFilter = $event"
          @update:sort-by="sortBy = $event"
        />

        <section v-if="selectedStudent" class="explorers-page__detail teacher-panel">
          <explorer-profile-hero :student="selectedStudent" :radar="radar" />

          <div class="explorers-page__tabs">
            <button type="button" :class="{ 'is-active': detailTab === 'growth' }" @click="detailTab = 'growth'">成长轨迹</button>
            <button type="button" :class="{ 'is-active': detailTab === 'knowledge' }" @click="detailTab = 'knowledge'">知识掌握</button>
            <button type="button" :class="{ 'is-active': detailTab === 'trial' }" @click="detailTab = 'trial'">试炼记录</button>
            <button type="button" :class="{ 'is-active': detailTab === 'quest' }" @click="detailTab = 'quest'">委托完成</button>
          </div>

          <div v-if="detailTab === 'growth'" class="explorers-page__growth">
            <growth-line-chart class="explorers-page__chart" title="委托完成率趋势" :points="growthPoints" />
            <div class="explorers-page__stats">
              <article v-for="card in statCards" :key="card.key">
                <span>{{ card.label }}</span>
                <strong>{{ card.value }}</strong>
                <em :class="{ 'is-muted': card.delta === '待试炼系统' }">{{ card.delta }}</em>
              </article>
            </div>
          </div>
          <explorer-quest-panel
            v-else-if="detailTab === 'quest' && selectedStudent"
            :student="selectedStudent"
            :heatmap-row="selectedHeatmapRow"
          />
          <explorer-knowledge-panel
            v-else-if="detailTab === 'knowledge'"
            :loading="achievementsLoading"
            :error="achievementsError"
            :achievements="achievements"
          />
          <explorer-trial-panel v-else-if="detailTab === 'trial' && selectedStudent" :student-id="selectedStudent.id" />
        </section>

        <explorer-status-aside
          v-if="selectedStudent"
          class="explorers-page__aside"
          :overall-status="overallStatus"
          :ai-text="aiText"
          :todos="todos"
        />
      </template>
    </section>
  </TeacherDashboardShell>
</template>

<style scoped>
.explorers-page {
  display: grid;
  grid-template-columns: minmax(260px, 320px) minmax(0, 1fr) minmax(260px, 300px);
  grid-template-rows: auto 1fr;
  gap: 1.1rem;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  padding: 0 var(--plex-page-gutter-x) 1.5rem;
}

.explorers-page--manage {
  grid-template-columns: 1fr;
}

.explorers-page__mode-tabs {
  grid-column: 1 / -1;
  display: flex;
  gap: 0.55rem;
  flex-shrink: 0;
}

.explorers-page__mode-tabs button {
  padding: 0.5rem 1.1rem;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 999px;
  background: rgba(4, 12, 20, 0.55);
  color: var(--teacher-muted);
  cursor: pointer;
  font-size: 0.86rem;
}

.explorers-page__mode-tabs button.is-active {
  border-color: rgba(251, 146, 60, 0.5);
  background: rgba(251, 146, 60, 0.14);
  color: var(--teacher-text);
  box-shadow: 0 0 20px rgba(251, 146, 60, 0.12);
}

.explorers-page__manage {
  grid-column: 1 / -1;
  min-height: 0;
}

.explorers-page__state {
  grid-column: 1 / -1;
}

.explorers-page__list {
  min-height: 0;
}

.explorers-page__detail {
  padding: 1.25rem 1.35rem;
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
}

.explorers-page__tabs {
  display: flex;
  gap: 0.5rem;
  margin: 1rem 0;
  flex-wrap: wrap;
}

.explorers-page__tabs button {
  padding: 0.45rem 0.85rem;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 999px;
  background: transparent;
  color: var(--teacher-muted);
  cursor: pointer;
  font-size: 0.82rem;
}

.explorers-page__tabs .is-active {
  border-color: rgba(251, 146, 60, 0.45);
  color: var(--teacher-text);
  background: rgba(251, 146, 60, 0.12);
}

.explorers-page__growth {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(180px, 220px);
  gap: 1rem;
  align-items: start;
}

.explorers-page__stats {
  display: grid;
  gap: 0.65rem;
}

.explorers-page__stats article {
  padding: 0.75rem 0.85rem;
  border: 1px solid rgba(130, 212, 255, 0.1);
  border-radius: 12px;
  background: rgba(4, 12, 20, 0.45);
}

.explorers-page__stats span {
  display: block;
  color: var(--teacher-muted);
  font-size: 0.78rem;
}

.explorers-page__stats strong {
  display: block;
  margin: 0.2rem 0;
  color: var(--teacher-text);
  font-size: 1.35rem;
}

.explorers-page__stats em {
  color: #34d399;
  font-style: normal;
  font-size: 0.78rem;
  font-weight: 700;
}

.explorers-page__stats em.is-muted {
  color: var(--teacher-muted);
  font-weight: 500;
}

.explorers-page__aside {
  min-height: 0;
}

@media (max-width: 1200px) {
  .explorers-page {
    grid-template-columns: 1fr;
    overflow: auto;
  }

  .explorers-page__list {
    max-height: 320px;
  }

  .explorers-page__growth {
    grid-template-columns: 1fr;
  }
}
</style>
