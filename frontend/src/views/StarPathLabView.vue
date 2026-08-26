<script setup lang="ts">
import { computed, onActivated, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, useMessage } from 'naive-ui'
import { fetchLearningPath, fetchLearningPathAdvice, type LearningDomain, type LearningPathOrderedNode, type NextBestAction, type RemediationPath } from '../api/studentProgress'
import { planLearningPath } from '../api/agentService'
import { getPythonTrialQuestion, type PythonTrialQuestion } from '../data/pythonTrialQuestions'
import {
  STAR_PATH_DOMAINS,
  STAR_PATH_TAB_ALL,
  STAR_PATH_TABS,
  getKnowledgePointsForDomain,
  getStarPathDomain,
  getStarPathKnowledgePoint,
  type StarPathKnowledgePoint,
} from '../data/starPathDomains'
import { buildKnowledgeTrack } from '../data/starPathKnowledgeTracks'
import {
  getStarPathNode,
  isStarPathNodeUnlocked,
  getPrimaryQuestionId,
  type StarPathNode,
} from '../data/starPathTrail'
import DashboardShell from '../components/layout/DashboardShell.vue'
import StarPathTrackCanvas from '../components/starpath/StarPathTrackCanvas.vue'
import PlexSyncState from '../components/common/PlexSyncState.vue'
import PlexLearningPathPanel from '../components/agent/PlexLearningPathPanel.vue'
import { useAuthStore } from '../stores/auth'
import { fetchServerMistakeRecords } from '../utils/trialMistakeLog'
import { mergeAcceptedQuestionIds } from '../utils/starPathProgress'
import {
  resolveQuestionById,
  resolveStarPathQuestion,
  generatedQuestionId,
} from '../utils/starPathQuestionGenerator'
import { MIN_QUESTIONS_PER_KP } from '../data/starPathKnowledgeTracks'
import { ensurePracticeQuestionsLoaded, getCachedPracticeQuestion } from '../utils/practiceQuestionCache'
import { openPracticeQuestion, searchPracticeQuestions } from '../utils/practiceQuestionNav'
import { formatQuestionLabel, normalizeQuestion } from '../utils/questionNaming'
import { fetchPracticeQuestionByRef } from '../api/practiceQuestions'
import { wrapEpisodeNarrative } from '../utils/explorationNarrative'
import { sanitizeQuestionContent } from '../utils/questionStemSanitizer'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const auth = useAuthStore()

type Domain = {
  key: string
  title: string
  progress: number
  state: string
  active?: boolean
  locked?: boolean
}

/** 兜底星域与知识点取第一个，跟着 registry 走，避免写死已下线的 id */
const DEFAULT_DOMAIN_KEY = STAR_PATH_DOMAINS[0]?.key ?? ''
const DEFAULT_NODE_ID = STAR_PATH_DOMAINS[0]?.knowledgePoints[0]?.id ?? ''

const loading = ref(true)
const errorMessage = ref('')
const domains = ref<Domain[]>([])
const activeTabKey = ref<string>(STAR_PATH_TAB_ALL)
const activeDomainKey = ref(DEFAULT_DOMAIN_KEY)
const selectedKnowledgeId = ref<string | null>(null)
const selectedNodeId = ref(DEFAULT_NODE_ID)
const activeQuestionSlot = ref(0)
const orderedNodes = ref<LearningPathOrderedNode[]>([])
const activePathNodeId = ref<string | null>(null)
const nextBestAction = ref<NextBestAction | null>(null)
const remediationPaths = ref<RemediationPath[]>([])
const pathAgentTrace = ref<{ backend?: string; steps?: Array<{ agentId: string; name: string; latencyMs: number; summary: string }> } | null>(null)
const graphBackend = ref<string | undefined>()
const pathPanelLoading = ref(false)
const pathAdvice = ref<string | null>(null)
const pathAdviceLoading = ref(false)
const pathAdviceBackend = ref<string | null>(null)
const pageSearch = ref('')
const questionSearchHits = ref<PythonTrialQuestion[]>([])
const questionSearchLoading = ref(false)
const acceptedQuestionIds = ref<Set<string>>(new Set())
const inlinePracticeOpen = ref(false)
const inlineQuestion = ref<PythonTrialQuestion | null>(null)
const inlinePracticeReady = ref(false)
const questionTransitionKey = ref(0)

const activeDomain = computed(() => domains.value.find((item) => item.key === activeDomainKey.value) ?? domains.value[0])
const activeDomainMeta = computed(() => getStarPathDomain(activeDomainKey.value))

const showDomainTrack = computed(() => activeTabKey.value !== STAR_PATH_TAB_ALL)

const starPathNodes = computed<StarPathNode[]>(() => {
  if (!showDomainTrack.value) return []
  return buildKnowledgeTrack(
    activeDomainKey.value,
    orderedNodes.value,
    activePathNodeId.value,
    acceptedQuestionIds.value,
  )
})

const trackVariant = computed<'seven' | 'four'>(() =>
  starPathNodes.value.length > 5 ? 'seven' : 'four',
)

const visibleKnowledgePoints = computed<StarPathKnowledgePoint[]>(() => {
  if (activeTabKey.value === STAR_PATH_TAB_ALL) {
    return STAR_PATH_DOMAINS.flatMap((d) => d.knowledgePoints)
  }
  return getKnowledgePointsForDomain(activeDomainKey.value)
})

const filteredKnowledgePoints = computed(() => {
  const q = pageSearch.value.trim().toLowerCase()
  if (!q) return visibleKnowledgePoints.value
  return visibleKnowledgePoints.value.filter(
    (kp) =>
      kp.title.toLowerCase().includes(q) ||
      kp.summary.toLowerCase().includes(q) ||
      kp.id.toLowerCase().includes(q),
  )
})

const filteredStarPathNodes = computed(() => {
  const q = pageSearch.value.trim().toLowerCase()
  if (!q) return starPathNodes.value
  return starPathNodes.value.filter(
    (node) =>
      node.title.toLowerCase().includes(q) ||
      (node.titleLine2 ?? '').toLowerCase().includes(q) ||
      node.id.toLowerCase().includes(q),
  )
})

const selectedKnowledge = computed(() => {
  if (!selectedKnowledgeId.value) return null
  return getStarPathKnowledgePoint(selectedKnowledgeId.value)
})

const selectedNode = computed(
  () =>
    getStarPathNode(selectedNodeId.value) ??
    starPathNodes.value.find((n) => n.id === selectedNodeId.value) ??
    starPathNodes.value[0] ??
    null,
)

const selectedQuestion = computed(() => {
  const kp = selectedKnowledge.value?.point
  const qid = activeQuestionId.value
  if (kp && qid) {
    const resolved = resolveQuestionById(qid, kp)
    if (resolved) return resolved
  }
  if (kp) return resolveStarPathQuestion(kp, { slot: activeQuestionSlot.value })
  const qidFallback = selectedNode.value ? getPrimaryQuestionId(selectedNode.value) : null
  return qidFallback ? getPythonTrialQuestion(qidFallback) : null
})

const detailMode = computed<'knowledge' | 'node'>(() =>
  selectedKnowledge.value ? 'knowledge' : 'node',
)

const nodeQuestionIds = computed(() => selectedNode.value?.questionIds ?? [])

const activeQuestionId = computed(() => {
  const ids = nodeQuestionIds.value
  if (!ids.length) return null
  const slot = Math.min(activeQuestionSlot.value, ids.length - 1)
  return ids[slot] ?? ids[0] ?? null
})

const activeKnowledgePoint = computed(() => selectedKnowledge.value?.point ?? null)

const inlineSlotIds = computed(() => {
  const kp = activeKnowledgePoint.value
  if (kp) {
    return Array.from({ length: MIN_QUESTIONS_PER_KP }, (_, slot) => generatedQuestionId(kp.id, slot))
  }
  return nodeQuestionIds.value.length ? [...nodeQuestionIds.value] : []
})

function wrapWithArc(base: PythonTrialQuestion): PythonTrialQuestion {
  const cleaned = sanitizeQuestionContent(base)
  if (cleaned.description.includes('星球探险') || cleaned.description.includes('🛸')) {
    return cleaned
  }
  const kp = activeKnowledgePoint.value
  if (kp && /^gen-.+-s\d+$/.test(cleaned.id)) {
    const slotMatch = /^gen-.+-s(\d+)$/.exec(cleaned.id)
    const slot = slotMatch ? Number(slotMatch[1]) : activeQuestionSlot.value
    const taskLine = cleaned.description.split('\n').filter(Boolean).pop() ?? cleaned.description
    return {
      ...cleaned,
      description: wrapEpisodeNarrative(kp.id, kp.domainKey, slot, taskLine),
    }
  }
  return cleaned
}

function resolveInlineQuestion(qid: string): PythonTrialQuestion | null {
  const cached = getCachedPracticeQuestion(qid)
  if (cached) return wrapWithArc(cached)
  const staticQuestion = getPythonTrialQuestion(qid)
  if (staticQuestion) return wrapWithArc(staticQuestion)
  const kp = activeKnowledgePoint.value
  if (kp) {
    const resolved = resolveQuestionById(qid, kp)
    if (resolved) return wrapWithArc(resolved)
  }
  const node = selectedNode.value
  if (node) {
    const question = questionForNode(node, qid)
    if (question) return wrapWithArc(question)
  }
  return null
}

async function loadInlineQuestion(qid?: string) {
  inlinePracticeReady.value = false
  await ensurePracticeQuestionsLoaded()
  const targetId = qid ?? activeQuestionId.value
  if (!targetId) {
    inlineQuestion.value = null
    inlinePracticeReady.value = true
    return
  }
  let question = resolveInlineQuestion(targetId)
  if (!question) {
    try {
      const item = await fetchPracticeQuestionByRef(targetId)
      question = wrapWithArc(
        normalizeQuestion({
          id: item.id,
          code: item.code,
          title: item.title,
          topic: item.topic,
          difficulty: item.difficulty,
          rewardXp: item.reward_xp,
          durationMin: item.duration_min,
          tags: item.tags,
          description: item.description,
          constraints: item.constraints,
          examples: item.examples,
          testCases: item.test_cases,
          starterCode: item.starter_code,
          runMode: item.run_mode,
          hint: item.hint,
        }),
      )
    } catch {
      question = null
    }
  }
  inlineQuestion.value = question ? sanitizeQuestionContent(question) : null
  inlinePracticeReady.value = true
  questionTransitionKey.value += 1
}

function openInlinePractice(question?: PythonTrialQuestion) {
  inlinePracticeOpen.value = true
  if (question) {
    inlineQuestion.value = sanitizeQuestionContent(wrapWithArc(question))
    inlinePracticeReady.value = true
    questionTransitionKey.value += 1
    return
  }
  void loadInlineQuestion()
}

function closeInlinePractice() {
  inlinePracticeOpen.value = false
}

function launchFullscreenPractice() {
  const question = inlineQuestion.value ?? selectedQuestion.value
  if (!question) {
    message.warning('请先选择一道试炼题')
    return
  }
  void openPracticeQuestion(router, question)
}

async function onInlinePassed() {
  message.success('试炼通过！宝石进度已更新')
  const data = await fetchLearningPath().catch(() => null)
  await refreshAcceptedQuestions(data?.question_ac_status)
}

function selectInlineSlot(slot: number) {
  selectQuestionSlot(slot, inlineSlotIds.value[slot] ?? '')
}

function slotForQuestionId(qid: string): number {
  const index = nodeQuestionIds.value.indexOf(qid)
  return index >= 0 ? index : 0
}

function syncKnowledgeFromNode(node: StarPathNode) {
  if (node.id.includes('-')) {
    selectedKnowledgeId.value = node.id
  }
  activeQuestionSlot.value = 0
  questionTransitionKey.value += 1
}

function onNodeClick(node: StarPathNode) {
  selectedNodeId.value = node.id
  syncKnowledgeFromNode(node)
}

function onGemSelect(payload: { node: StarPathNode; slot: number }) {
  selectedNodeId.value = payload.node.id
  syncKnowledgeFromNode(payload.node)
  activeQuestionSlot.value = payload.slot
  const qid = payload.node.questionIds[payload.slot]
  if (!qid) {
    message.warning('该试炼槽位尚未解锁')
    return
  }
  void (async () => {
    await ensurePracticeQuestionsLoaded()
    const question = questionForNode(payload.node, qid)
    if (question) {
      message.info(`已切换至第 ${payload.slot + 1} 题 · ${formatQuestionLabel(question)}`)
      if (inlinePracticeOpen.value) {
        await loadInlineQuestion(qid)
      }
    }
  })()
}

function questionForNode(node: StarPathNode, questionId?: string) {
  const qid = questionId ?? getPrimaryQuestionId(node)
  const kp = node.id.includes('-') ? getStarPathKnowledgePoint(node.id)?.point : selectedKnowledge.value?.point
  if (kp) {
    if (qid) {
      const resolved = resolveQuestionById(qid, kp)
      if (resolved) return resolved
    }
    return resolveStarPathQuestion(kp)
  }
  if (!qid) return null
  return getPythonTrialQuestion(qid)
}

function openPractice(questionId?: string) {
  void (async () => {
    await ensurePracticeQuestionsLoaded()
    if (questionId) {
      activeQuestionSlot.value = slotForQuestionId(questionId)
    }
    const kp = selectedKnowledge.value?.point
    const targetId = questionId ?? activeQuestionId.value ?? undefined
    if (kp) {
      const question = targetId
        ? resolveQuestionById(targetId, kp)
        : resolveStarPathQuestion(kp, { slot: activeQuestionSlot.value })
      if (question) {
        launchPractice(question)
        return
      }
    }

    const node = selectedNode.value
    if (!node || !isStarPathNodeUnlocked(node)) {
      message.warning('请先选择一个可练习的星轨节点')
      return
    }
    const qid = targetId ?? getPrimaryQuestionId(node)
    let question = qid ? questionForNode(node, qid) : null
    if (!question && kp) {
      question = resolveStarPathQuestion(kp, { slot: activeQuestionSlot.value })
    }
    if (!question) {
      message.warning('题库加载中或未找到匹配题目，请稍后重试')
      return
    }
    launchPractice(question)
  })()
}

function selectQuestionSlot(slot: number, qid: string) {
  if (activeQuestionSlot.value === slot) return
  activeQuestionSlot.value = slot
  void (async () => {
    await ensurePracticeQuestionsLoaded()
    const kp = selectedKnowledge.value?.point
    const node = selectedNode.value
    const question = kp
      ? resolveQuestionById(qid, kp)
      : node
        ? questionForNode(node, qid)
        : null
    if (question) {
      message.info(`已切换至第 ${slot + 1} 题 · ${formatQuestionLabel(question)}`)
      if (inlinePracticeOpen.value) {
        await loadInlineQuestion(qid)
      }
    }
  })()
}

function launchPractice(question: PythonTrialQuestion) {
  void openPracticeQuestion(router, question)
}

function rerollQuestion() {
  const kp = selectedKnowledge.value?.point
  if (kp) {
    const nextSlot = (activeQuestionSlot.value + 1) % MIN_QUESTIONS_PER_KP
    activeQuestionSlot.value = nextSlot
    const generated = resolveStarPathQuestion(kp, { slot: nextSlot })
    if (generated) {
      message.info(`已切换至第 ${nextSlot + 1} 题 · ${formatQuestionLabel(generated)}`)
      if (inlinePracticeOpen.value) {
        void loadInlineQuestion(generated.id)
      }
    }
    return
  }
  const ids = nodeQuestionIds.value
  if (!ids.length || !selectedNode.value) return
  const nextIndex = (activeQuestionSlot.value + 1) % ids.length
  activeQuestionSlot.value = nextIndex
  const question = questionForNode(selectedNode.value, ids[nextIndex])
  if (question) {
    message.info(`已切换至第 ${nextIndex + 1} 题 · ${formatQuestionLabel(question)}`)
    if (inlinePracticeOpen.value) {
      void loadInlineQuestion(question.id)
    }
  }
}

function continueExplore() {
  openPractice()
}

function isTabActive(tabKey: string) {
  return activeTabKey.value === tabKey
}

function selectTab(tabKey: string) {
  activeTabKey.value = tabKey
  activeQuestionSlot.value = 0
  questionTransitionKey.value += 1
  if (tabKey === STAR_PATH_TAB_ALL) {
    const first = STAR_PATH_DOMAINS[0]?.knowledgePoints[0]
    selectedKnowledgeId.value = first?.id ?? null
    selectedNodeId.value = first?.id ?? DEFAULT_NODE_ID
    void router.replace({ path: '/student/star-path', query: {} })
    return
  }
  activeDomainKey.value = tabKey
  const points = getKnowledgePointsForDomain(tabKey)
  const firstKp = points[0]
  selectedKnowledgeId.value = firstKp?.id ?? null
  selectedNodeId.value = firstKp?.id ?? DEFAULT_NODE_ID
  void router.replace({
    path: '/student/star-path',
    query: { domain: tabKey, kp: firstKp?.id ?? undefined },
  })
}

function selectDomainCard(domain: Domain) {
  if (domain.locked) return
  selectTab(domain.key)
}

// 内联试炼相关处理器暂未挂载到当前模板；显式引用以通过 noUnusedLocals，
// 后续恢复内联练习 UI 时直接使用。
void [openInlinePractice, closeInlinePractice, launchFullscreenPractice, onInlinePassed, selectInlineSlot, selectDomainCard]

async function runQuestionSearch(query: string) {
  pageSearch.value = query
  const q = query.trim()
  if (!q) {
    questionSearchHits.value = []
    return
  }
  questionSearchLoading.value = true
  try {
    questionSearchHits.value = await searchPracticeQuestions(q, 12)
  } finally {
    questionSearchLoading.value = false
  }
}

function openSearchHit(question: PythonTrialQuestion) {
  launchPractice(question)
}

async function refreshPathPlan(focusNode?: string | null) {
  pathPanelLoading.value = true
  pathAdviceLoading.value = true
  try {
    const plan = await planLearningPath({
      focus_node_id: focusNode ?? activePathNodeId.value ?? undefined,
    })
    orderedNodes.value = plan.ordered_nodes ?? orderedNodes.value
    activePathNodeId.value = plan.active_node_id ?? activePathNodeId.value
    nextBestAction.value = plan.next_best_action ?? nextBestAction.value
    remediationPaths.value = plan.remediation_paths ?? remediationPaths.value
    pathAgentTrace.value = plan.agent_trace ?? null
    graphBackend.value = plan.graph_backend
  } catch {
    /* 保留 learning-path GET 已返回的数据 */
  } finally {
    pathPanelLoading.value = false
  }
  try {
    const advice = await fetchLearningPathAdvice(focusNode ?? activePathNodeId.value ?? undefined)
    pathAdvice.value = advice.advice
    pathAdviceBackend.value = advice.backend
  } catch {
    pathAdvice.value = nextBestAction.value?.reason ?? null
    pathAdviceBackend.value = 'local_rules'
  } finally {
    pathAdviceLoading.value = false
  }
}

async function onPathNodeSelect(node: LearningPathOrderedNode) {
  if (node.star_path_id) {
    jumpToKnowledgeById(node.star_path_id)
  }
  await refreshPathPlan(node.id)
}

function onPathAction(action: NextBestAction) {
  const node = orderedNodes.value.find((item) => item.id === action.node_id)
  if (node?.star_path_id) {
    jumpToKnowledgeById(node.star_path_id)
  }
  if (action.action === 'practice') {
    openPractice()
  }
}

function jumpToKnowledgeById(kpId: string) {
  const found = getStarPathKnowledgePoint(kpId)
  if (found) jumpToKnowledge(found.point)
}

function jumpToKnowledge(kp: StarPathKnowledgePoint) {
  activeTabKey.value = kp.domainKey
  activeDomainKey.value = kp.domainKey
  selectedKnowledgeId.value = kp.id
  selectedNodeId.value = kp.id
  activeQuestionSlot.value = 0
  questionTransitionKey.value += 1
  void router.replace({ path: '/student/star-path', query: { domain: kp.domainKey, kp: kp.id } })
}

function applyRouteQuery() {
  const domain = typeof route.query.domain === 'string' ? route.query.domain : null
  const kp = typeof route.query.kp === 'string' ? route.query.kp : null

  if (domain && getStarPathDomain(domain)) {
    activeTabKey.value = domain
    activeDomainKey.value = domain
    if (kp && getStarPathKnowledgePoint(kp)) {
      selectedKnowledgeId.value = kp
      selectedNodeId.value = kp
    } else {
      const points = getKnowledgePointsForDomain(domain)
      const first = points[0]
      selectedKnowledgeId.value = first?.id ?? null
      selectedNodeId.value = first?.id ?? DEFAULT_NODE_ID
    }
  } else {
    activeTabKey.value = STAR_PATH_TAB_ALL
    const first = STAR_PATH_DOMAINS[0]?.knowledgePoints[0]
    selectedKnowledgeId.value = first?.id ?? null
    selectedNodeId.value = first?.id ?? DEFAULT_NODE_ID
  }

}

function continueKnowledgeTrial() {
  void openPractice()
}

function mapDomain(item: LearningDomain): Domain {
  return {
    key: item.key,
    title: item.title,
    progress: item.progress,
    state: item.state,
    active: item.active,
    locked: item.locked ?? false,
  }
}

async function refreshAcceptedQuestions(serverIds?: string[]) {
  const userId = auth.profile?.id ?? 'guest'
  const localRecords = await fetchServerMistakeRecords(userId)
  acceptedQuestionIds.value = mergeAcceptedQuestionIds(serverIds, localRecords)
}

async function loadPath(options?: { soft?: boolean }) {
  const soft = Boolean(options?.soft && domains.value.length)
  if (!soft) loading.value = true
  errorMessage.value = ''
  try {
    const data = await fetchLearningPath()
    domains.value = data.domains.map(mapDomain)
    orderedNodes.value = data.ordered_nodes ?? []
    activePathNodeId.value = data.active_node_id ?? null
    nextBestAction.value = data.next_best_action ?? null
    remediationPaths.value = data.remediation_paths ?? []
    graphBackend.value = data.graph_backend
    await refreshAcceptedQuestions(data.question_ac_status)
    if (!route.query.domain) {
      activeDomainKey.value = data.active_domain_key
    }
    applyRouteQuery()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '星轨数据加载失败'
    if (!soft) domains.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => [route.query.domain, route.query.kp],
  () => applyRouteQuery(),
)

onMounted(() => {
  void ensurePracticeQuestionsLoaded()
  void loadPath()
})

onActivated(() => {
  void refreshAcceptedQuestions()
  if (domains.value.length) void loadPath({ soft: true })
})
</script>

<template>
  <DashboardShell
    active-nav="track"
    page-title="星轨学习"
    page-subtitle="探索编程知识宇宙，点亮你的能力星图"
    search-placeholder="搜索题号、关键词或知识点…"
    @search-submit="runQuestionSearch"
  >
    <main class="starpath-main">
      <section class="starpath-tabs" aria-label="星域分类">
        <button
          v-for="tab in STAR_PATH_TABS"
          :key="tab.key"
          type="button"
          class="domain-tab"
          :class="{ 'domain-tab--active': isTabActive(tab.key) }"
          @click="selectTab(tab.key)"
        >
          {{ tab.label }}
        </button>
      </section>

      <section
        v-if="pageSearch.trim()"
        class="question-search-panel"
        aria-label="题目搜索结果"
      >
        <header>
          <strong>题目搜索</strong>
          <span v-if="questionSearchLoading">检索中…</span>
          <span v-else>{{ questionSearchHits.length ? `共 ${questionSearchHits.length} 条` : '无匹配题目' }}</span>
        </header>
        <ul v-if="questionSearchHits.length" class="question-search-list">
          <li v-for="item in questionSearchHits" :key="item.id">
            <button type="button" @click="openSearchHit(item)">
              <em>{{ item.code || item.id }}</em>
              <strong>{{ formatQuestionLabel(item) }}</strong>
              <span>{{ item.topic }}</span>
            </button>
          </li>
        </ul>
      </section>

      <PlexSyncState
        v-if="loading && !domains.length"
        label="正在同步学习路径…"
        hint="连接知识图谱与你的练习进度"
      />
      <div v-else-if="errorMessage" class="starpath-state starpath-state--error">
        <span>{{ errorMessage }}</span>
        <n-button secondary size="small" @click="loadPath()">重试</n-button>
      </div>

      <section
        v-else
        class="starpath-content"
        :aria-label="`${activeDomain?.title ?? '星域'}星轨`"
      >
        <div class="content-left">
          <section class="path-board">
            <div class="domain-copy">
              <div class="domain-copy__head">
                <h2>{{ activeDomain?.title ?? '星域' }}星域</h2>
                <span>{{ activeDomain?.state ?? '探索中' }}</span>
              </div>
              <p>星域探索进度</p>
              <strong>{{ activeDomain?.progress ?? 0 }}%</strong>
              <div class="progress-line"><span :style="{ width: `${activeDomain?.progress ?? 0}%` }" /></div>
              <p class="domain-copy__desc">
                <template v-if="activeDomainMeta">
                  {{ activeDomainMeta.description }}
                  <br />
                  <span class="domain-copy__focus">重点：{{ activeDomainMeta.focus }}</span>
                </template>
                <template v-else>浏览全部学域，点击标签或下方卡片进入对应知识点。</template>
              </p>
            </div>

            <div class="path-canvas" aria-label="星轨节点图">
              <StarPathTrackCanvas
                v-if="showDomainTrack"
                :key="activeDomainKey"
                :nodes="filteredStarPathNodes"
                :selected-id="selectedNodeId"
                :highlight-gem-slot="activeQuestionSlot"
                :variant="trackVariant"
                :domain-key="activeDomainKey"
                @select="onNodeClick"
                @select-gem="onGemSelect"
              />
              <div v-else class="knowledge-map" aria-label="全部星域知识点">
                <p v-if="pageSearch.trim() && !filteredKnowledgePoints.length" class="plex-local-search-empty">
                  当前页面没有匹配的知识点
                </p>
                <button
                  v-for="kp in filteredKnowledgePoints"
                  :key="kp.id"
                  type="button"
                  class="knowledge-node"
                  :class="{ 'knowledge-node--active': selectedKnowledgeId === kp.id }"
                  @click="jumpToKnowledge(kp)"
                >
                  <span class="knowledge-node__level">{{ kp.level }}</span>
                  <strong>{{ kp.title }}</strong>
                  <p>{{ kp.summary }}</p>
                  <em>{{ getStarPathDomain(kp.domainKey)?.title }}</em>
                </button>
              </div>
            </div>
          </section>

          <div class="path-board-actions">
            <button
              type="button"
              class="continue-btn continue-btn--launch"
              :disabled="detailMode === 'node' && (!selectedNode || !isStarPathNodeUnlocked(selectedNode))"
              @click="detailMode === 'knowledge' ? continueKnowledgeTrial() : continueExplore()"
            >
              {{ detailMode === 'knowledge' || isStarPathNodeUnlocked(selectedNode) ? '开始编程试炼' : '节点未解锁' }}
            </button>
            <button
              v-if="(detailMode === 'knowledge' && !selectedKnowledge?.point.questionId) || (detailMode === 'node' && nodeQuestionIds.length > 1)"
              type="button"
              class="continue-btn continue-btn--ghost"
              @click="rerollQuestion"
            >
              换一题
            </button>
          </div>

          <section class="domain-overview domain-overview--removed" aria-hidden="true" />
        </div>

        <aside class="detail-panel" aria-label="小E 学习路径">
          <PlexLearningPathPanel
            :ordered-nodes="orderedNodes"
            :active-node-id="activePathNodeId"
            :next-best-action="nextBestAction"
            :remediation-paths="remediationPaths"
            :agent-trace="pathAgentTrace"
            :graph-backend="graphBackend"
            :loading="pathPanelLoading"
            :ai-advice="pathAdvice"
            :ai-advice-loading="pathAdviceLoading"
            :ai-advice-backend="pathAdviceBackend"
            @select-node="onPathNodeSelect"
            @action="onPathAction"
          />
        </aside>
      </section>
    </main>
  </DashboardShell>
</template>

<style scoped>
.starpath-shell {
  display: flex;
  height: 100dvh;
  min-height: 100dvh;
  overflow: hidden;
  background: #020a12;
  color: #edf7ff;
  font-family:
    'Outfit',
    'Noto Sans SC',
    'Microsoft YaHei',
    system-ui,
    sans-serif;
}

.starpath-sidebar {
  position: relative;
  z-index: 4;
  width: 180px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 1.9rem 0 1.35rem;
  background:
    radial-gradient(circle at 22% 8%, rgba(20, 241, 226, 0.08), transparent 26%),
    linear-gradient(180deg, rgba(3, 15, 25, 0.98), rgba(1, 8, 15, 0.99));
  border-right: 1px solid rgba(110, 228, 255, 0.11);
}

.starpath-brand {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0 1.95rem 2.25rem;
  color: #25f5ee;
}

.brand-mark {
  filter: drop-shadow(0 0 12px rgba(37, 245, 238, 0.65));
}

.starpath-brand span {
  color: #ffffff;
  font-size: 1.55rem;
  font-weight: 780;
  letter-spacing: 0.06em;
}

.starpath-nav {
  display: grid;
  gap: 0.45rem;
  flex: 1;
  padding-top: 1rem;
}

.starpath-nav__item {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 78px;
  gap: 0.9rem;
  padding: 0.65rem 0.9rem 0.65rem 2.35rem;
  color: rgba(220, 230, 241, 0.68);
  text-decoration: none;
  transition: color 0.18s ease, background 0.18s ease;
}

.starpath-nav__item:hover {
  color: #ffffff;
  background: rgba(37, 245, 238, 0.045);
}

.starpath-nav__item--active {
  color: #4ffff2;
  background:
    linear-gradient(90deg, rgba(16, 240, 192, 0.27), rgba(16, 240, 192, 0.08) 72%, transparent),
    rgba(6, 182, 212, 0.035);
}

.starpath-nav__bar {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  opacity: 0;
  background: linear-gradient(180deg, #5ffff3, #12d8c8);
  box-shadow: 0 0 18px rgba(37, 245, 238, 0.76);
}

.starpath-nav__item--active .starpath-nav__bar {
  opacity: 1;
}

.starpath-nav__item .n-icon {
  font-size: 1.7rem;
}

.starpath-nav__item span:last-child {
  font-size: 1rem;
  font-weight: 680;
  white-space: nowrap;
}

.starpath-main {
  position: relative;
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background:
    radial-gradient(circle at 54% 48%, rgba(16, 240, 192, 0.09), transparent 34%),
    radial-gradient(circle at 78% 25%, rgba(79, 70, 229, 0.09), transparent 28%),
    linear-gradient(180deg, #06121f 0%, #020a12 60%, #01070e 100%);
}

.starpath-main::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.45;
  background-image:
    radial-gradient(1px 1px at 11% 21%, rgba(255, 255, 255, 0.3), transparent),
    radial-gradient(1px 1px at 38% 23%, rgba(93, 214, 255, 0.38), transparent),
    radial-gradient(1px 1px at 62% 47%, rgba(255, 255, 255, 0.18), transparent),
    radial-gradient(1px 1px at 86% 18%, rgba(166, 111, 255, 0.36), transparent);
  background-size: 340px 340px;
}

.question-search-panel {
  position: relative;
  z-index: 2;
  margin: 0 var(--plex-page-gutter-x) 0.75rem;
  padding: 0.75rem 1rem;
  border: 1px solid rgba(16, 240, 192, 0.18);
  border-radius: 14px;
  background: rgba(4, 14, 24, 0.82);
}

.question-search-panel header {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.55rem;
  color: rgba(224, 237, 247, 0.78);
  font-size: 0.82rem;
}

.question-search-panel header strong {
  color: #22ffde;
}

.question-search-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.45rem;
}

.question-search-list button {
  width: 100%;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 0.35rem 0.75rem;
  align-items: center;
  padding: 0.55rem 0.7rem;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 10px;
  background: rgba(8, 22, 36, 0.72);
  color: #edf7ff;
  text-align: left;
  cursor: pointer;
}

.question-search-list button:hover {
  border-color: rgba(16, 240, 192, 0.35);
}

.question-search-list em {
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
  background: rgba(16, 240, 192, 0.14);
  color: #22ffde;
  font-style: normal;
  font-size: 0.78rem;
  font-weight: 700;
}

.question-search-list span {
  color: rgba(190, 208, 224, 0.72);
  font-size: 0.78rem;
}

.starpath-top {
  position: relative;
  z-index: 3;
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(320px, 500px) minmax(260px, 1fr);
  align-items: center;
  gap: 1.4rem;
  padding: 1.45rem 2.25rem 1rem;
}

.starpath-title {
  position: relative;
  padding-left: 1.45rem;
}

.starpath-title::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.2rem;
  bottom: 0.2rem;
  width: 1px;
  background: rgba(39, 255, 238, 0.48);
}

.starpath-title h1 {
  margin: 0;
  color: #ffffff;
  font-size: 1.85rem;
  font-weight: 780;
  line-height: 1.08;
}

.starpath-title p {
  margin: 0.5rem 0 0;
  color: rgba(224, 237, 247, 0.72);
  font-size: 0.95rem;
}

.starpath-search__input :deep(.n-input) {
  --n-height: 48px !important;
  --n-color: rgba(6, 18, 31, 0.7) !important;
  --n-border: 1px solid rgba(130, 212, 255, 0.12) !important;
  --n-border-hover: 1px solid rgba(37, 245, 238, 0.32) !important;
  --n-text-color: #edf7ff !important;
  --n-placeholder-color: rgba(210, 225, 238, 0.58) !important;
  font-size: 0.9rem;
}

.search-kbd {
  padding: 0.12rem 0.42rem;
  border: 1px solid rgba(210, 225, 238, 0.13);
  border-radius: 0.35rem;
  color: rgba(220, 232, 242, 0.64);
  font-size: 0.75rem;
}

.starpath-userbar {
  justify-self: end;
  display: flex;
  align-items: center;
  gap: 1.35rem;
}

.icon-button {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #edf7ff;
  cursor: pointer;
}

.user-pill {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  border: 0;
  background: transparent;
  color: #ffffff;
  cursor: pointer;
}

.bot-avatar {
  border: 1px solid rgba(37, 245, 238, 0.28);
  background:
    radial-gradient(circle, rgba(37, 245, 238, 0.18), transparent 62%),
    #061827 !important;
  box-shadow:
    0 0 0 6px rgba(61, 163, 255, 0.1),
    0 0 22px rgba(37, 245, 238, 0.28);
}

.bot-avatar__face {
  position: relative;
  display: block;
  width: 32px;
  height: 22px;
  border-radius: 9px;
  background: #111926;
  box-shadow: inset 0 8px 0 #edf6f8;
}

.bot-avatar__face::before,
.bot-avatar__face::after {
  content: '';
  position: absolute;
  top: 12px;
  width: 8px;
  height: 3px;
  border-radius: 99px;
  background: #35fff1;
}

.bot-avatar__face::before {
  left: 7px;
  transform: rotate(28deg);
}

.bot-avatar__face::after {
  right: 7px;
  transform: rotate(-28deg);
}

.user-pill__copy {
  display: grid;
  gap: 0.2rem;
  text-align: left;
}

.user-pill__copy strong {
  font-size: 0.95rem;
}

.user-pill__copy em {
  width: fit-content;
  padding: 0.04rem 0.32rem;
  border-radius: 0.35rem;
  background: rgba(37, 245, 238, 0.18);
  color: #57fff2;
  font-size: 0.75rem;
  font-style: normal;
}

.starpath-tabs {
  position: relative;
  z-index: 3;
  display: flex;
  align-items: stretch;
  flex-wrap: wrap;
  gap: 0.5rem 0.85rem;
  padding: 0.55rem var(--plex-page-gutter-x) 0.65rem;
  border-bottom: 1px solid rgba(126, 188, 220, 0.08);
  min-height: 56px;
}

.domain-tab {
  position: relative;
  flex: 1 1 auto;
  min-width: 7.5rem;
  min-height: 44px;
  padding: 0.45rem 0.85rem;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 0.65rem;
  background: rgba(6, 18, 31, 0.55);
  color: rgba(224, 237, 247, 0.7);
  cursor: pointer;
  font-size: 1.02rem;
  font-weight: 650;
  white-space: nowrap;
}

.domain-tab--active {
  color: #eaffff;
  border-color: rgba(35, 255, 222, 0.55);
  background: rgba(16, 240, 192, 0.1);
  box-shadow: inset 0 0 18px rgba(35, 255, 222, 0.06);
}

.domain-tab--active::after {
  display: none;
}

.starpath-content {
  position: relative;
  z-index: 2;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 420px);
  align-items: stretch;
  gap: 1rem;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: 0 var(--plex-page-gutter-x) var(--plex-page-gutter-bottom);
}

.content-left {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 0.85rem;
  min-width: 0;
  min-height: 0;
  align-content: stretch;
}

.path-board-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 0.15rem 1rem 0.35rem;
}

.path-board-actions .continue-btn {
  width: min(100%, 320px);
}

.path-board,
.domain-overview,
.detail-panel {
  border: 1px solid rgba(90, 208, 255, 0.13);
  border-radius: 0.7rem;
  background:
    linear-gradient(180deg, rgba(8, 25, 39, 0.62), rgba(4, 15, 26, 0.54)),
    rgba(4, 14, 24, 0.56);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

.path-board {
  position: relative;
  display: grid;
  grid-template-columns: 1fr;
  grid-template-rows: auto minmax(320px, 1fr);
  min-height: 0;
  overflow: hidden;
}

.domain-copy {
  position: relative;
  z-index: 2;
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 0.55rem 1rem;
  padding: 0.65rem 1rem 0.55rem;
  border-bottom: 1px solid rgba(90, 208, 255, 0.1);
}

.domain-copy__head {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-width: 0;
}

.domain-copy h2 {
  margin: 0;
  min-width: 0;
  flex: 1 1 auto;
  color: #ffffff;
  font-size: 1.45rem;
  line-height: 1.25;
}

.domain-copy__head span {
  flex-shrink: 0;
  align-self: center;
  padding: 0.2rem 0.55rem;
  border-radius: 0.35rem;
  background: rgba(16, 240, 192, 0.16);
  color: #22ffde;
  font-size: 0.78rem;
  font-weight: 720;
  line-height: 1.2;
  white-space: nowrap;
}

.domain-copy p {
  margin: 0;
  color: rgba(224, 237, 247, 0.68);
  font-size: 0.88rem;
}

.domain-copy strong {
  display: block;
  margin-top: 0.15rem;
  color: #ffffff;
  font-size: 1.55rem;
  line-height: 1;
}

.progress-line {
  width: 120px;
  height: 6px;
  margin-top: 0.35rem;
  overflow: hidden;
  border-radius: 99px;
  background: rgba(197, 219, 236, 0.12);
}

.progress-line span {
  display: block;
  width: 62%;
  height: 100%;
  border-radius: inherit;
  background: #19f0c9;
  box-shadow: 0 0 14px rgba(25, 240, 201, 0.38);
}

.domain-copy__desc {
  line-height: 1.65;
}

.domain-copy__focus {
  display: inline-block;
  margin-top: 0.35rem;
  color: rgba(35, 255, 222, 0.85);
  font-size: 0.82rem;
}

.knowledge-map {
  position: absolute;
  inset: 1.25rem 1rem 1rem;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 0.75rem;
  align-content: start;
  overflow-y: auto;
  padding-right: 0.25rem;
}

.knowledge-node {
  display: grid;
  gap: 0.35rem;
  text-align: left;
  padding: 0.75rem 0.85rem;
  border: 1px solid rgba(130, 212, 255, 0.14);
  border-radius: 0.55rem;
  background: rgba(6, 18, 31, 0.82);
  color: #edf7ff;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease, background 0.2s ease;
}

.knowledge-node:hover,
.knowledge-node--active {
  border-color: rgba(35, 255, 222, 0.55);
  box-shadow: 0 0 18px rgba(35, 255, 222, 0.12);
  transform: translateY(-3px);
}

.knowledge-node--active {
  animation: knowledge-node-lock 0.48s cubic-bezier(0.2, 0.8, 0.25, 1);
}

.knowledge-node:active {
  transform: translateY(0) scale(0.98);
}

@keyframes knowledge-node-lock {
  0% { box-shadow: 0 0 0 rgba(35, 255, 222, 0); }
  50% { box-shadow: 0 0 0 7px rgba(35, 255, 222, 0.16), 0 0 28px rgba(35, 255, 222, 0.28); }
  100% { box-shadow: 0 0 18px rgba(35, 255, 222, 0.12); }
}

.knowledge-node__level {
  width: fit-content;
  padding: 0.1rem 0.4rem;
  border-radius: 0.3rem;
  background: rgba(16, 240, 192, 0.14);
  color: #22ffde;
  font-size: 0.68rem;
  font-style: normal;
}

.knowledge-node strong {
  font-size: 0.9rem;
  line-height: 1.35;
}

.knowledge-node p {
  margin: 0;
  font-size: 0.78rem;
  color: rgba(224, 237, 247, 0.68);
  line-height: 1.45;
}

.knowledge-node em {
  font-size: 0.68rem;
  font-style: normal;
  color: rgba(142, 163, 184, 0.9);
}

.starpath-content--practice {
  grid-template-columns: 1fr;
}

.practice-shell {
  grid-column: 1 / -1;
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(90, 208, 255, 0.13);
  border-radius: 0.7rem;
  overflow: hidden;
  background: rgba(4, 14, 24, 0.72);
}

.practice-shell :deep(.py-workspace) {
  flex: 1;
  min-height: 0;
}

.sub-trials {
  margin-top: 1rem;
}

.sub-trials strong {
  color: #ffffff;
  font-size: 0.9rem;
}

.sub-trials__list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  margin-top: 0.65rem;
}

.sub-trials__chip {
  min-height: 2.2rem;
  padding: 0.5rem 0.9rem;
  border: 1.5px solid rgba(130, 212, 255, 0.2);
  border-radius: 0.55rem;
  background: rgba(7, 22, 36, 0.82);
  color: #edf7ff;
  cursor: pointer;
  font-size: 0.92rem;
  font-weight: 500;
}

.sub-trials__chip--active {
  border-color: rgba(35, 255, 222, 0.65);
  background: rgba(16, 240, 192, 0.16);
  box-shadow: 0 0 16px rgba(35, 255, 222, 0.2);
}

.sub-trials__chip:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.continue-btn--ghost {
  margin-top: 0.45rem;
  background: transparent;
  border: 1px solid rgba(35, 255, 222, 0.35);
  color: #23ffde;
}

.detail-panel__detail {
  margin: 0.5rem 0 0.75rem;
  color: rgba(224, 237, 247, 0.78);
  font-size: 0.88rem;
  line-height: 1.65;
}

.intro-guide {
  margin: 0.75rem 0;
  padding: 0.65rem 0.75rem;
  border: 1px solid rgba(35, 255, 222, 0.22);
  border-radius: 0.55rem;
  background: rgba(16, 240, 192, 0.06);
}

.intro-guide strong {
  display: block;
  color: #22ffde;
  font-size: 0.86rem;
  margin-bottom: 0.45rem;
}

.intro-guide ol {
  margin: 0;
  padding-left: 1.15rem;
  color: rgba(224, 237, 247, 0.82);
  font-size: 0.84rem;
  line-height: 1.55;
}

.intro-guide li + li {
  margin-top: 0.35rem;
}

.detail-panel__level {
  background: rgba(35, 255, 222, 0.12) !important;
  color: #23ffde !important;
}

.overview-card--clickable {
  cursor: pointer;
}

.overview-card--clickable:hover {
  border-color: rgba(35, 255, 222, 0.35);
}

.domain-copy button {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  min-height: 46px;
  margin-top: 1.8rem;
  padding: 0 1rem;
  border: 1px solid rgba(130, 212, 255, 0.1);
  border-radius: 0.5rem;
  background: rgba(6, 18, 31, 0.72);
  color: #edf7ff;
  cursor: pointer;
  font-weight: 650;
}

.path-canvas {
  position: relative;
  min-width: 0;
  min-height: 460px;
  height: 100%;
  overflow: hidden;
}

.path-track {
  position: absolute;
  inset: 1.75rem 0.35rem 3rem 0.15rem;
  transform: none;
  transform-origin: center center;
}

.path-orbits {
  position: absolute;
  z-index: 0;
  inset: 0;
  pointer-events: none;
}

.orbit {
  position: absolute;
  left: 50%;
  top: 44%;
  border: 1px solid rgba(40, 238, 219, 0.12);
  border-radius: 50%;
  transform: translate(-50%, -50%) rotate(-14deg);
}

.orbit--outer {
  width: min(100%, 920px);
  height: 460px;
  border-color: rgba(143, 190, 221, 0.08);
}

.orbit--middle {
  width: min(82%, 700px);
  height: 340px;
  border-style: dashed;
}

.orbit--inner {
  width: min(56%, 440px);
  height: 220px;
}

.path-lines {
  position: absolute;
  z-index: 0;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.path-line {
  stroke-width: 0.34;
  stroke-dasharray: 2.4 2.4;
}

.path-line--done {
  stroke: rgba(35, 255, 222, 0.72);
}

.path-line--active {
  stroke: rgba(35, 255, 222, 0.86);
}

.path-line--locked {
  stroke: rgba(224, 237, 247, 0.58);
}

.track-node {
  --node-color: #26ffee;
  --node-orb: 52px;
  position: absolute;
  display: grid;
  width: max-content;
  max-width: 92px;
  justify-items: center;
  align-items: center;
  text-align: center;
  color: #ffffff;
  transform: translate(-50%, -50%);
}

.track-node__orb {
  position: relative;
  z-index: 1;
  display: grid;
  width: var(--node-orb);
  aspect-ratio: 1;
  place-items: center;
  border: 1px solid color-mix(in srgb, var(--node-color) 62%, transparent);
  border-radius: 50%;
  background:
    radial-gradient(circle, color-mix(in srgb, var(--node-color) 28%, transparent), transparent 66%),
    rgba(5, 17, 29, 0.96);
  color: #eaffff;
  box-shadow:
    0 0 0 5px color-mix(in srgb, var(--node-color) 9%, transparent),
    0 0 20px color-mix(in srgb, var(--node-color) 24%, transparent);
}

.track-node__orb .n-icon {
  font-size: 1.35rem;
}

.track-node strong {
  margin-top: 0.4rem;
  color: rgba(255, 255, 255, 0.88);
  font-size: 0.82rem;
}

.track-node p {
  margin: 0.06rem 0 0;
  color: rgba(240, 247, 255, 0.88);
  font-size: 0.78rem;
  line-height: 1.3;
}

.track-node em {
  margin-top: 0.18rem;
  color: #23ffde;
  font-size: 0.62rem;
  font-style: normal;
  letter-spacing: 0.1em;
}

.track-node--anchor-left {
  max-width: 88px;
  transform: translate(0, -50%);
  justify-items: start;
  text-align: left;
}

.track-node--anchor-right {
  max-width: 88px;
  transform: translate(-100%, -50%);
  justify-items: end;
  text-align: right;
}

.track-node--current {
  --node-color: #23ffde;
  --node-orb: 68px;
  left: 52%;
  top: 36%;
  z-index: 3;
  max-width: 96px;
}

.track-node--current .track-node__orb {
  box-shadow:
    0 0 0 8px rgba(35, 255, 222, 0.12),
    0 0 32px rgba(35, 255, 222, 0.48);
}

.track-node--current .track-node__orb .n-icon {
  font-size: 1.55rem;
}

.track-node__badge {
  position: absolute;
  bottom: calc(100% + 0.35rem);
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
  margin-bottom: 0;
  padding: 0.25rem 0.5rem;
  border-radius: 0.35rem;
  background: rgba(16, 240, 192, 0.16);
  color: #22ffde;
  font-size: 0.78rem;
  font-weight: 720;
}

.track-node {
  cursor: pointer;
}

.track-node--done {
  --node-color: #23ffde;
}

.track-node--progress {
  --node-color: #23ffde;
}

.track-node--selected {
  filter: drop-shadow(0 0 14px rgba(37, 245, 238, 0.45));
}

.track-node--locked {
  --node-color: #d7e6ef;
}

.track-node--locked .track-node__orb {
  opacity: 0.72;
}

.track-node--locked em {
  color: rgba(230, 240, 247, 0.58);
}

/* 圆心对齐 path-lines；左侧三节点阶梯错落，避免挤成一条竖线 */
.track-node--n2 {
  left: 19%;
  top: 47%;
  z-index: 2;
}

.track-node--n3 {
  left: 30%;
  top: 86%;
  z-index: 1;
}

.track-node--n4 {
  left: 92%;
  top: 60%;
  z-index: 1;
}

.track-node--n5 {
  left: 92%;
  top: 11%;
  z-index: 2;
}

.track-node--n6 {
  left: 5%;
  top: 10%;
  z-index: 1;
}

.track-node--n7 {
  left: 3%;
  top: 77%;
  z-index: 1;
}

.legend {
  position: absolute;
  z-index: 5;
  right: 1.45rem;
  bottom: 1.25rem;
  display: flex;
  gap: 1.3rem;
  padding: 0.35rem 0.5rem;
  border-radius: 0.4rem;
  background: rgba(4, 14, 24, 0.72);
  color: rgba(224, 237, 247, 0.68);
  font-size: 0.78rem;
  pointer-events: none;
}

.legend span {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}

.legend__dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  transform: rotate(45deg);
}

.legend__dot--done {
  background: #23ffde;
}

.legend__dot--active {
  background: #38bdf8;
}

.legend__dot--locked {
  background: #7d8791;
}

.domain-overview--removed {
  display: none !important;
}

.domain-overview h2 {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: 0 0 0.85rem;
  color: #ffffff;
  font-size: 1.1rem;
}

.domain-overview h2 span {
  width: 3px;
  height: 22px;
  background: #23ffde;
  box-shadow: 0 0 12px rgba(35, 255, 222, 0.65);
}

.overview-list {
  display: grid;
  grid-template-columns: repeat(var(--overview-cols, 4), minmax(0, 1fr));
  gap: 0.75rem;
  width: 100%;
}

.overview-card {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 82px;
  align-items: center;
  min-height: 100px;
  min-width: 0;
  overflow: hidden;
  border: 1px solid rgba(130, 212, 255, 0.11);
  border-radius: 0.55rem;
  background: rgba(7, 22, 36, 0.72);
  padding: 1rem;
}

.overview-card--active {
  border-color: rgba(35, 255, 222, 0.62);
  box-shadow: inset 0 0 18px rgba(35, 255, 222, 0.05);
}

.overview-card strong {
  color: #ffffff;
  font-size: 1rem;
  line-height: 1.35;
  word-break: break-word;
}

.overview-card p {
  margin: 0.42rem 0 0;
  color: #ffffff;
  font-size: 1.25rem;
}

.overview-card em {
  display: block;
  margin-top: 0.4rem;
  color: #23ffde;
  font-style: normal;
  font-size: 0.82rem;
}

.planet {
  position: relative;
  display: block;
  width: 78px;
  aspect-ratio: 1;
  border-radius: 50%;
  background:
    radial-gradient(circle at 35% 30%, rgba(102, 255, 220, 0.62), transparent 22%),
    radial-gradient(circle at 60% 70%, rgba(3, 86, 88, 0.9), rgba(8, 38, 56, 0.95));
  box-shadow: 0 0 24px rgba(35, 255, 222, 0.2);
}

.planet--locked {
  filter: grayscale(0.9);
  opacity: 0.55;
}

.planet--locked .n-icon {
  position: absolute;
  right: 0;
  bottom: 6px;
  color: #edf7ff;
  font-size: 1.15rem;
}

.detail-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 0;
  max-height: 100%;
  align-self: stretch;
  overflow: hidden;
  padding: 0.85rem 1.15rem;
}

.detail-panel :deep(.plex-learning-path) {
  flex: 1;
  min-height: 0;
  max-height: none;
  height: 100%;
  margin-bottom: 0;
}

.detail-panel__head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.detail-panel h2 {
  margin: 0;
  color: #ffffff;
  font-size: 1.22rem;
}

.detail-panel__head span {
  align-self: start;
  padding: 0.25rem 0.5rem;
  border-radius: 0.35rem;
  background: rgba(16, 240, 192, 0.16);
  color: #22ffde;
  font-size: 0.76rem;
  font-weight: 720;
  white-space: nowrap;
}

.detail-panel__trial {
  margin: 0.85rem 0 0;
  color: rgba(221, 230, 239, 0.72);
  font-size: 0.84rem;
  line-height: 1.5;
}

.detail-panel__trial strong {
  color: #5fffe8;
  font-weight: 700;
}

.detail-panel__trial small {
  display: block;
  margin-top: 0.2rem;
  color: rgba(221, 230, 239, 0.52);
  font-size: 0.78rem;
}

.tags {
  margin-top: 1.55rem;
}

.tags strong,
.mastery strong,
.advice strong,
.rewards strong {
  color: #ffffff;
  font-size: 0.9rem;
}

.tags div {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-top: 0.75rem;
}

.tags span {
  padding: 0.4rem 0.62rem;
  border-radius: 0.35rem;
  background: rgba(224, 237, 247, 0.08);
  color: rgba(240, 247, 255, 0.9);
  font-size: 0.78rem;
  font-weight: 650;
}

.panel-bot {
  position: relative;
  height: 165px;
  margin: 0.55rem 0 0;
}

.panel-bot--hidden {
  display: none;
}

.panel-bot__head {
  position: absolute;
  left: 50%;
  top: 28px;
  width: 118px;
  height: 86px;
  border: 8px solid #edf6f8;
  border-radius: 34px;
  background: #101824;
  transform: translateX(-50%);
  box-shadow: 0 0 0 7px rgba(37, 245, 238, 0.12);
}

.panel-bot__head::before,
.panel-bot__head::after {
  content: '';
  position: absolute;
  top: 31px;
  width: 21px;
  height: 11px;
  border-radius: 999px;
  background: #35fff1;
  box-shadow: 0 0 12px rgba(53, 255, 241, 0.9);
}

.panel-bot__head::before {
  left: 25px;
  transform: rotate(32deg);
}

.panel-bot__head::after {
  right: 25px;
  transform: rotate(-32deg);
}

.panel-bot__body {
  position: absolute;
  left: 50%;
  top: 108px;
  width: 82px;
  height: 66px;
  border-radius: 28px 28px 22px 22px;
  background: #edf6f8;
  transform: translateX(-50%);
}

.panel-bot__card {
  position: absolute;
  top: 48px;
  width: 48px;
  height: 70px;
  border: 1px solid rgba(35, 255, 222, 0.36);
  border-radius: 0.35rem;
  background: rgba(16, 240, 192, 0.08);
  box-shadow: 0 0 16px rgba(35, 255, 222, 0.13);
}

.panel-bot__card--left {
  left: 46px;
  transform: rotate(12deg);
}

.panel-bot__card--right {
  right: 46px;
  transform: rotate(-12deg);
}

.mastery {
  margin-top: 0.4rem;
}

.mastery div {
  display: flex;
  justify-content: space-between;
  color: #ffffff;
}

.mastery div span {
  font-weight: 720;
}

.mastery p {
  height: 7px;
  margin: 0.65rem 0 0;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(224, 237, 247, 0.12);
}

.mastery p span {
  display: block;
  width: 85%;
  height: 100%;
  background: #23ffde;
  box-shadow: 0 0 14px rgba(35, 255, 222, 0.38);
}

.advice {
  margin-top: 1.1rem;
  padding-top: 1.1rem;
  border-top: 1px solid rgba(224, 237, 247, 0.08);
}

.advice p {
  margin: 0.75rem 0 0;
  color: rgba(224, 237, 247, 0.72);
  font-size: 0.9rem;
  line-height: 1.6;
}

.advice-link {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  margin-top: 0.9rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: #23ffde;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 720;
  text-decoration: none;
}

.rewards {
  margin-top: 0.9rem;
  padding-top: 0.9rem;
  border-top: 1px solid rgba(224, 237, 247, 0.08);
}

.reward-row {
  display: flex;
  justify-content: space-between;
  gap: 0.8rem;
  margin-top: 0.9rem;
}

.reward-row span {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: #dff8ff;
  font-weight: 680;
}

.reward-row em {
  font-style: normal;
}

.continue-btn {
  flex-shrink: 0;
  width: 100%;
  min-height: 48px;
  margin-top: 0;
  border: 0;
  border-radius: 0.38rem;
  background: linear-gradient(90deg, rgba(16, 240, 192, 0.8), rgba(18, 150, 130, 0.88));
  color: #eaffff;
  cursor: pointer;
  font-size: 0.96rem;
  font-weight: 760;
  transition: transform 0.18s ease, filter 0.18s ease, box-shadow 0.18s ease;
}

.continue-btn--launch:not(:disabled):hover {
  transform: translateY(-2px);
  filter: brightness(1.08);
  box-shadow: 0 0 0 4px rgba(35, 255, 222, 0.1), 0 10px 24px rgba(16, 240, 192, 0.2);
}

.continue-btn--launch:not(:disabled)::after {
  content: '›';
  display: inline-block;
  margin-left: 0.45rem;
  animation: launch-chevron 1.2s ease-in-out infinite;
}

@keyframes launch-chevron {
  50% { transform: translateX(4px); }
}

.continue-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
  background: rgba(80, 100, 110, 0.5);
}

@media (max-width: 1280px) {
  .starpath-top {
    grid-template-columns: 1fr;
  }

  .starpath-userbar {
    justify-self: start;
  }

  .starpath-content {
    grid-template-columns: 1fr;
  }

  .content-left {
    grid-template-rows: minmax(480px, 1fr) auto;
  }

  .detail-panel {
    min-height: 360px;
    height: auto;
    padding: 1.1rem;
  }

  .path-board-actions .continue-btn {
    width: min(100%, 360px);
  }
}

@media (max-width: 900px) {
  .starpath-shell {
    flex-direction: column;
    overflow: auto;
  }

  .starpath-sidebar {
    width: 100%;
    min-height: auto;
    padding: 0.75rem;
  }

  .starpath-brand {
    padding: 0.25rem 0.65rem 0.75rem;
  }

  .starpath-nav {
    display: flex;
    overflow-x: auto;
    gap: 0.45rem;
    padding-top: 0;
  }

  .starpath-nav__item {
    min-width: 132px;
    min-height: 64px;
    padding: 0.6rem 0.85rem;
  }

  .starpath-top,
  .starpath-tabs,
  .starpath-content {
    padding-inline: var(--plex-page-gutter-x);
  }

  .starpath-tabs {
    overflow-x: auto;
    gap: 1.65rem;
    padding-bottom: 1rem;
  }

  .path-board {
    grid-template-columns: 1fr;
  }

  .domain-copy {
    padding: 1.2rem 1rem 0;
  }

  .content-left {
    grid-template-rows: minmax(520px, 1fr) auto;
  }

  .path-canvas {
    min-height: 520px;
  }

  .overview-list {
    grid-template-columns: 1fr;
  }

  .legend {
    left: 1rem;
    right: auto;
    flex-wrap: wrap;
  }

  .detail-panel {
    min-height: 0;
    height: auto;
    padding: 1.1rem;
  }

  .path-board-actions {
    padding-bottom: 0.75rem;
  }

}

.inline-practice {
  margin: 1rem var(--plex-page-gutter-x, 1.25rem) 1.5rem;
  padding: 1rem 1rem 0.5rem;
  border: 1px solid rgba(35, 255, 222, 0.22);
  border-radius: 18px;
  background:
    radial-gradient(circle at 12% 0%, rgba(35, 255, 222, 0.08), transparent 42%),
    linear-gradient(180deg, rgba(4, 18, 30, 0.96), rgba(2, 10, 18, 0.98));
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.35);
}

.inline-practice__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.75rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid rgba(130, 212, 255, 0.12);
}

.inline-practice__eyebrow {
  display: block;
  margin-bottom: 0.25rem;
  color: rgba(35, 255, 222, 0.78);
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.inline-practice__head h3 {
  margin: 0;
  color: #f3fbff;
  font-size: 1.05rem;
  font-weight: 650;
}

.inline-practice__head-actions {
  display: flex;
  flex-shrink: 0;
  gap: 0.35rem;
}

.inline-practice__loading {
  min-height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(214, 230, 244, 0.72);
}

</style>
