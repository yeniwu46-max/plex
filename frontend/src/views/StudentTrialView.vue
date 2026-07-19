<script setup lang="ts">
import { computed, onActivated, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NIcon, NSelect, NTag, useMessage, type SelectOption } from 'naive-ui'
import { CheckmarkCircleOutline, ChevronForwardOutline, CodeSlashOutline } from '@vicons/ionicons5'
import DashboardShell from '../components/layout/DashboardShell.vue'
import {
  fetchStudentTrialStats,
  fetchStudentTrials,
  joinStudentTrial,
  type StudentTrial,
  type StudentTrialStatsResult,
} from '../api/studentTrials'
import TrialExamPanel from '../components/trial/TrialExamPanel.vue'
import {
  formatStarPathNodeLabel,
  getStarPathNode,
  getUnlockedStarPathNodes,
  isStarPathNodeUnlocked,
  resolveQuestionsForNode,
  resolveStarPathNodeId,
} from '../data/starPathTrail'
import { useAuthStore } from '../stores/auth'
import { buildTrialPageRecommendation } from '../utils/trialPageRecommendation'
import { fetchServerMistakeRecords, getTrialMistakeRecords, type TrialMistakeRecord } from '../utils/trialMistakeLog'
import { fetchLearningPath } from '../api/studentProgress'
import { isQuestionAccepted, mergeAcceptedQuestionIds } from '../utils/starPathProgress'
import { formatQuestionLabel } from '../utils/questionNaming'

const message = useMessage()
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const highlightTrialId = computed(() => {
  const raw = route.query.trialId
  const parsed = raw ? Number(raw) : NaN
  return Number.isNaN(parsed) ? null : parsed
})

const loading = ref(true)
const errorMessage = ref('')
const trialStats = ref<StudentTrialStatsResult | null>(null)
const statsLoading = ref(true)
const trials = ref<StudentTrial[]>([])
const serverMistakes = ref<TrialMistakeRecord[]>([])
const acceptedQuestionIds = ref<Set<string>>(new Set())
const actingId = ref<number | null>(null)
const activeMcqTrial = ref<{ id: number; title: string } | null>(null)
const currentView = ref<'card' | 'list'>('card')

const TRIAL_LIST_CACHE_MS = 30_000
let trialListLoadedAt = 0

const displayName = computed(() => auth.profile?.real_name || auth.profile?.username || 'Explorer')
const userId = computed(() => auth.profile?.id ?? 'guest')

const unlockedNodes = computed(() => getUnlockedStarPathNodes(acceptedQuestionIds.value))
const selectedNodeId = ref('stage1-intro')

const nodeSelectOptions = computed<SelectOption[]>(() =>
  unlockedNodes.value.map((node) => ({
    label: formatStarPathNodeLabel(node),
    value: node.id,
  })),
)


const activeQuestions = computed(() => resolveQuestionsForNode(selectedNodeId.value))

const pageRecommendation = computed(() =>
  buildTrialPageRecommendation(
    userId.value,
    selectedNodeId.value,
    activeQuestions.value,
    serverMistakes.value,
  ),
)

const recommendedQuestionId = computed(() => pageRecommendation.value.recommendedQuestionId)


const questionAcStatus = computed(() => {
  const records = serverMistakes.value.length
    ? serverMistakes.value
    : getTrialMistakeRecords(userId.value)
  const map: Record<string, 'ac' | 'wa'> = {}
  for (const r of records) {
    if (isQuestionAccepted(r)) {
      map[r.questionId] = 'ac'
    } else if (r.lastFailedAt) {
      map[r.questionId] = 'wa'
    }
  }
  for (const qid of acceptedQuestionIds.value) {
    map[qid] = 'ac'
  }
  return map
})

watch(
  unlockedNodes,
  (nodes) => {
    if (!nodes.length) return
    const current = nodes.find((node) => node.status === 'current')
    const preferred = current ?? nodes[0]
    if (!nodes.some((node) => node.id === selectedNodeId.value)) {
      selectedNodeId.value = preferred.id
    }
  },
  { immediate: true },
)

async function loadTrialStats() {
  statsLoading.value = true
  try {
    trialStats.value = await fetchStudentTrialStats()
  } catch {
    trialStats.value = null
  } finally {
    statsLoading.value = false
  }
}

async function loadTrials(force = false) {
  if (!force && trials.value.length && Date.now() - trialListLoadedAt < TRIAL_LIST_CACHE_MS) {
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const data = await fetchStudentTrials()
    trials.value = data.trials
    trialListLoadedAt = Date.now()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载失败'
    trials.value = []
  } finally {
    loading.value = false
  }
}

function openPythonQuestion(questionId: string) {
  void router.push(`/student/trials/practice/${questionId}`)
}

async function onJoin(trial: StudentTrial) {
  actingId.value = trial.id
  try {
    await joinStudentTrial(trial.id)
    activeMcqTrial.value = { id: trial.id, title: trial.title }
    message.success(`已进入「${trial.title}」答题`)
  } catch (error) {
    message.error(error instanceof Error ? error.message : '参与失败')
  } finally {
    actingId.value = null
  }
}

async function onMcqCompleted() {
  activeMcqTrial.value = null
  await Promise.all([loadTrials(true), loadTrialStats()])
}

function onSearchSubmit(query: string) {
  const q = query.trim().toLowerCase()
  if (!q) return

  for (const node of getUnlockedStarPathNodes(acceptedQuestionIds.value)) {
    const questions = resolveQuestionsForNode(node.id)
    const hit = questions.find(
      (question) =>
        question.title.toLowerCase().includes(q) ||
        question.topic.toLowerCase().includes(q) ||
        question.tags.some((tag) => tag.toLowerCase().includes(q)),
    )
    if (hit) {
      void router.push(`/student/trials/practice/${hit.id}`)
      return
    }
  }

  // 搜索班级试炼
  const trialHit = trials.value.find((trial) => trial.title.toLowerCase().includes(q))
  if (trialHit) {
    void router.push({ path: '/student/trials', query: { trialId: String(trialHit.id) } })
    return
  }

  message.warning(`未找到"${query}"相关题目或试炼`)
}

async function refreshPracticeProgress() {
  const [records, path] = await Promise.all([
    fetchServerMistakeRecords(userId.value),
    fetchLearningPath().catch(() => null),
  ])
  serverMistakes.value = records
  acceptedQuestionIds.value = mergeAcceptedQuestionIds(path?.question_ac_status, records)
}

onMounted(() => {
  const rawNode = route.query.node
  if (typeof rawNode === 'string') {
    const resolved = resolveStarPathNodeId(rawNode)
    const node = getStarPathNode(resolved, acceptedQuestionIds.value)
    if (isStarPathNodeUnlocked(node)) {
      selectedNodeId.value = resolved
    }
  }
  void Promise.all([loadTrials(), loadTrialStats(), refreshPracticeProgress()])
})

onActivated(() => {
  void refreshPracticeProgress()
})
</script>

<template>
  <DashboardShell
    active-nav="trial"
    page-title="试炼关卡"
    page-subtitle="Python 入门代码试炼 · 参与班级任务赢取探索积分"
    search-placeholder="搜索试炼、题目或知识点…"
    @search-submit="onSearchSubmit"
  >
    <section class="student-trial" aria-label="学生试炼关卡">
      <p class="student-trial__welcome">你好，{{ displayName }} — 从 Python 入门题开始试炼，或参与班级任务。</p>

      <section v-if="!activeMcqTrial" class="student-trial__stats" aria-label="试炼战绩">
        <div v-if="statsLoading" class="student-trial__stats-loading">同步战绩…</div>
        <template v-else-if="trialStats">
          <div class="student-trial__stats-grid">
            <article class="student-trial__stat-card">
              <span class="student-trial__stat-label">已完成</span>
              <strong>{{ trialStats.summary.completed_count }}</strong>
            </article>
            <article class="student-trial__stat-card">
              <span class="student-trial__stat-label">进行中</span>
              <strong>{{ trialStats.summary.active_count }}</strong>
            </article>
            <article class="student-trial__stat-card">
              <span class="student-trial__stat-label">均分</span>
              <strong>{{ trialStats.summary.avg_score }}</strong>
            </article>
            <article class="student-trial__stat-card">
              <span class="student-trial__stat-label">累计参与</span>
              <strong>{{ trialStats.summary.total_participations }}</strong>
            </article>
          </div>
          <ul v-if="trialStats.recent_completions.length" class="student-trial__recent">
            <li v-for="item in trialStats.recent_completions" :key="`${item.trial_id}-${item.completed_at}`">
              <span>{{ item.title }}</span>
              <em>{{ item.score }} 分</em>
            </li>
          </ul>
        </template>
      </section>

      <TrialExamPanel
        v-if="activeMcqTrial"
        :trial-id="activeMcqTrial.id"
        :trial-title="activeMcqTrial.title"
        class="student-trial__mcq"
        @back="activeMcqTrial = null"
        @completed="onMcqCompleted"
      />

      <template v-else>
      <div class="student-trial__python-layout">
        <section class="student-trial__section student-trial__section--python" aria-label="Python 入门试炼">
        <header class="student-trial__section-head">
          <div class="student-trial__section-intro">
            <h2>Python 入门试炼</h2>
            <p>选择已解锁的星轨板块，完成该节点下的全部代码试炼。</p>
          </div>
          <div class="student-trial__section-picker">
            <label class="student-trial__picker-label" for="starpath-node-select">星轨板块</label>
            <n-select
              id="starpath-node-select"
              v-model:value="selectedNodeId"
              :options="nodeSelectOptions"
              :disabled="!nodeSelectOptions.length"
              placeholder="选择板块"
              class="student-trial__node-select"
            />
            <span class="student-trial__section-badge">
              <n-icon :component="CodeSlashOutline" />
              {{ activeQuestions.length }} 题
            </span>
          </div>
        </header>

        <ul v-if="activeQuestions.length" class="student-trial__python-list" :class="{ 'student-trial__python-list--list': currentView === 'list' }">
          <li v-for="(question, index) in activeQuestions" :key="question.id">
            <button
              type="button"
              class="student-trial__python-card"
              :class="{
                'student-trial__python-card--recommended': question.id === recommendedQuestionId,
                'student-trial__python-card--ac': questionAcStatus[question.id] === 'ac',
                'student-trial__python-card--wa': questionAcStatus[question.id] === 'wa',
              }"
              @click="openPythonQuestion(question.id)"
            >
              <span class="student-trial__python-index">{{ String(index + 1).padStart(2, '0') }}</span>
              <div class="student-trial__python-copy">
                <strong>
                  {{ formatQuestionLabel(question) }}
                  <span v-if="question.id === recommendedQuestionId" class="student-trial__rec-badge">推荐优先</span>
                </strong>
                <small>{{ question.topic }} · {{ question.difficulty }} · 约 {{ question.durationMin }} 分钟</small>
                <div class="student-trial__tags">
                  <span v-for="tag in question.tags" :key="tag">{{ tag }}</span>
                </div>
              </div>
              <div class="student-trial__python-side">
                <n-tag v-if="questionAcStatus[question.id] === 'ac'" type="success" size="small" class="student-trial__ac-tag">
                  <template #icon><n-icon :component="CheckmarkCircleOutline" /></template>
                  AC
                </n-tag>
                <n-tag v-else-if="questionAcStatus[question.id] === 'wa'" type="warning" size="small" class="student-trial__ac-tag">WA</n-tag>
                <em v-else>+{{ question.rewardXp }} XP</em>
                <n-icon :component="ChevronForwardOutline" />
              </div>
            </button>
          </li>
        </ul>
        <p v-else class="student-trial__state">暂无已解锁板块，请先在星轨路径中推进进度。</p>
        </section>
      </div>

      <section class="student-trial__section" aria-label="班级试炼">
        <header class="student-trial__section-head">
          <div>
            <h2>班级试炼</h2>
            <p>教师发布的进行中任务，完成后可获得班级积分奖励。</p>
          </div>
        </header>

        <div v-if="loading" class="student-trial__state">正在同步试炼列表…</div>
        <div v-else-if="errorMessage" class="student-trial__state student-trial__state--error">
          <span>{{ errorMessage }}</span>
          <n-button secondary size="small" @click="loadTrials()">重试</n-button>
        </div>
        <p v-else-if="!trials.length" class="student-trial__state">当前没有进行中的班级试炼，可先完成上方 Python 入门题。</p>

        <ul v-else class="student-trial__list">
          <li
            v-for="trial in trials"
            :key="trial.id"
            class="student-trial__card"
            :class="{ 'student-trial__card--highlight': highlightTrialId === trial.id }"
          >
            <header>
              <h3>{{ trial.title }}</h3>
              <span class="student-trial__badge">{{ trial.reward_points }} XP</span>
            </header>
            <p class="student-trial__meta">
              难度 {{ trial.difficulty }} · 约 {{ trial.duration_minutes }} 分钟 ·
              {{ trial.participant_count ?? 0 }} 人已参与
            </p>
            <p v-if="trial.my_status === 'completed'" class="student-trial__done">已完成（得分 {{ trial.my_score }}）</p>
            <div v-else class="student-trial__actions">
              <n-button
                v-if="!trial.my_status"
                type="primary"
                :loading="actingId === trial.id"
                @click="onJoin(trial)"
              >
                参与试炼
              </n-button>
              <n-button
                v-else-if="trial.my_status === 'joined'"
                type="primary"
                :loading="actingId === trial.id"
                @click="activeMcqTrial = { id: trial.id, title: trial.title }"
              >
                继续答题
              </n-button>
            </div>
          </li>
        </ul>
      </section>
      </template>
    </section>
  </DashboardShell>
</template>

<style scoped>
.student-trial {
  flex: 1;
  width: 100%;
  min-width: 0;
  min-height: 0;
  box-sizing: border-box;
  overflow-y: auto;
  padding: 0 var(--plex-page-gutter-x) 2rem;
}

.student-trial__python-layout {
  display: block;
  margin-bottom: 1.75rem;
}

.student-trial__section--python {
  margin-bottom: 0;
  min-width: 0;
}

.student-trial__welcome {
  margin: 0 0 1.35rem;
  color: rgba(226, 232, 240, 0.75);
  font-size: 0.92rem;
}

.student-trial__stats {
  margin-bottom: 1.35rem;
}

.student-trial__stats-loading {
  padding: 0.85rem 1rem;
  border-radius: 12px;
  background: rgba(5, 17, 29, 0.72);
  color: rgba(226, 232, 240, 0.7);
  font-size: 0.86rem;
}

.student-trial__stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.65rem;
}

.student-trial__stat-card {
  padding: 0.85rem 1rem;
  border-radius: 12px;
  border: 1px solid rgba(130, 212, 255, 0.14);
  background: rgba(5, 18, 30, 0.85);
}

.student-trial__stat-label {
  display: block;
  color: rgba(221, 230, 239, 0.55);
  font-size: 0.76rem;
}

.student-trial__stat-card strong {
  display: block;
  margin-top: 0.25rem;
  color: #5fffe8;
  font-size: 1.35rem;
  font-weight: 800;
}

.student-trial__recent {
  margin: 0.75rem 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.4rem;
}

.student-trial__recent li {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.55rem 0.75rem;
  border-radius: 10px;
  background: rgba(5, 17, 29, 0.55);
  color: rgba(226, 232, 240, 0.82);
  font-size: 0.84rem;
}

.student-trial__recent em {
  font-style: normal;
  color: #fb923c;
  font-weight: 700;
}

@media (max-width: 720px) {
  .student-trial__stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.student-trial__section {
  margin-bottom: 1.75rem;
}

.student-trial__section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.85rem;
  flex-wrap: wrap;
}

.student-trial__section-intro {
  flex: 1 1 220px;
  min-width: 0;
}

.student-trial__section-picker {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.4rem;
  flex: 0 1 240px;
  min-width: 200px;
}

.student-trial__picker-label {
  align-self: stretch;
  color: rgba(221, 230, 239, 0.58);
  font-size: 0.76rem;
  font-weight: 600;
}

.student-trial__node-select {
  width: 100%;
  min-width: 220px;
}

.student-trial__node-select :deep(.n-base-selection) {
  --n-border: 1px solid rgba(46, 255, 241, 0.22);
  --n-border-hover: 1px solid rgba(46, 255, 241, 0.38);
  --n-border-active: 1px solid rgba(46, 255, 241, 0.45);
  --n-box-shadow-active: 0 0 0 2px rgba(46, 255, 241, 0.12);
  background: rgba(5, 18, 30, 0.92);
}

.student-trial__node-select :deep(.n-base-selection-label) {
  color: #e2e8f0;
}

.student-trial__section-head h2 {
  margin: 0;
  color: #fff7ed;
  font-size: 1.08rem;
  font-weight: 700;
}

.student-trial__section-head p {
  margin: 0.35rem 0 0;
  color: rgba(221, 230, 239, 0.58);
  font-size: 0.84rem;
  line-height: 1.5;
}

.student-trial__section-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  flex-shrink: 0;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  background: rgba(46, 255, 241, 0.1);
  border: 1px solid rgba(46, 255, 241, 0.22);
  color: #5fffe8;
  font-size: 0.78rem;
  font-weight: 650;
}

.student-trial__python-list,
.student-trial__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.75rem;
}

.student-trial__python-card {
  display: grid;
  width: 100%;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 0.85rem;
  align-items: center;
  padding: 0.95rem 1rem;
  border: 1px solid rgba(130, 212, 255, 0.14);
  border-radius: 14px;
  background: linear-gradient(145deg, rgba(5, 18, 30, 0.92), rgba(3, 12, 20, 0.78));
  color: inherit;
  cursor: pointer;
  font: inherit;
  text-align: left;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.student-trial__python-card:hover {
  border-color: rgba(46, 255, 241, 0.35);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.22), 0 0 0 1px rgba(46, 255, 241, 0.12);
  transform: translateY(-1px);
}

.student-trial__python-card--recommended {
  border-color: rgba(251, 146, 60, 0.42);
  box-shadow: 0 0 0 1px rgba(251, 146, 60, 0.15);
}

.student-trial__rec-badge {
  display: inline-block;
  margin-left: 0.45rem;
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
  background: rgba(251, 146, 60, 0.18);
  color: #fb923c;
  font-size: 0.68rem;
  font-weight: 700;
  vertical-align: middle;
}

.student-trial__python-index {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 12px;
  background: rgba(46, 255, 241, 0.1);
  color: #5fffe8;
  font-size: 0.88rem;
  font-weight: 800;
}

.student-trial__python-copy strong {
  display: block;
  color: #fff7ed;
  font-size: 1rem;
}

.student-trial__python-copy small {
  display: block;
  margin-top: 0.25rem;
  color: rgba(221, 230, 239, 0.58);
  font-size: 0.8rem;
}

.student-trial__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-top: 0.45rem;
}

.student-trial__tags span {
  padding: 0.12rem 0.45rem;
  border-radius: 999px;
  background: rgba(130, 212, 255, 0.1);
  color: rgba(221, 230, 239, 0.68);
  font-size: 0.72rem;
}

.student-trial__python-side {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  color: #fb923c;
}

.student-trial__python-side em {
  font-style: normal;
  font-size: 0.82rem;
  font-weight: 700;
}

.student-trial__state {
  padding: 2rem 1rem;
  border-radius: 14px;
  background: rgba(5, 17, 29, 0.72);
  color: rgba(226, 232, 240, 0.8);
  text-align: center;
}

.student-trial__state--error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  color: #fecaca;
}

.student-trial__card--highlight {
  border-color: rgba(251, 146, 60, 0.55);
  box-shadow: 0 0 0 1px rgba(251, 146, 60, 0.2), 0 12px 32px rgba(251, 146, 60, 0.12);
}

.student-trial__card {
  padding: 1.15rem 1.25rem;
  border: 1px solid rgba(130, 212, 255, 0.14);
  border-radius: 16px;
  background: linear-gradient(145deg, rgba(5, 18, 30, 0.92), rgba(3, 12, 20, 0.78));
}

.student-trial__card header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.student-trial__card h3 {
  margin: 0;
  color: #fff7ed;
  font-size: 1.05rem;
  font-weight: 650;
}

.student-trial__badge {
  flex-shrink: 0;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  background: rgba(251, 146, 60, 0.18);
  color: #fb923c;
  font-size: 0.78rem;
  font-weight: 700;
}

.student-trial__meta {
  margin: 0.5rem 0 0.85rem;
  color: rgba(221, 230, 239, 0.62);
  font-size: 0.84rem;
}

.student-trial__done {
  margin: 0;
  color: #34d399;
  font-size: 0.88rem;
  font-weight: 600;
}

.student-trial__actions {
  display: flex;
  gap: 0.5rem;
}

.student-trial__python-card--ac {
  border-color: rgba(52, 211, 153, 0.35) !important;
  background: linear-gradient(135deg, rgba(5, 25, 18, 0.92), rgba(3, 15, 10, 0.78)) !important;
}

.student-trial__python-card--wa {
  border-color: rgba(251, 146, 60, 0.25) !important;
}

.student-trial__ac-tag {
  flex-shrink: 0;
}

.student-trial__python-list--list .student-trial__python-card {
  gap: 0.65rem;
  padding: 0.6rem 0.85rem;
}

.student-trial__python-list--list .student-trial__python-index {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  font-size: 0.78rem;
}

.student-trial__python-list--list .student-trial__python-copy strong {
  font-size: 0.88rem;
}

.student-trial__python-list--list .student-trial__tags {
  display: none;
}
</style>
