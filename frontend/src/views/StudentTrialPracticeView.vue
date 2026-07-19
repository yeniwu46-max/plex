<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, useMessage } from 'naive-ui'
import DashboardShell from '../components/layout/DashboardShell.vue'
import PythonTrialWorkspace from '../components/trial/PythonTrialWorkspace.vue'
import { getPythonTrialQuestion, type PythonTrialQuestion } from '../data/pythonTrialQuestions'
import { getStarPathNodeByQuestionId } from '../data/starPathTrail'
import { getStarPathKnowledgePoint } from '../data/starPathDomains'
import { generatedQuestionId, resolveQuestionById } from '../utils/starPathQuestionGenerator'
import { MIN_QUESTIONS_PER_KP } from '../data/starPathKnowledgeTracks'
import { ensurePracticeQuestionsLoaded, getCachedPracticeQuestion } from '../utils/practiceQuestionCache'
import { fetchPracticeQuestionByRef } from '../api/practiceQuestions'
import { formatQuestionLabel, normalizeQuestion } from '../utils/questionNaming'
import { wrapEpisodeNarrative } from '../utils/explorationNarrative'
import { sanitizeQuestionContent } from '../utils/questionStemSanitizer'
import { stashActivePracticeQuestion } from '../utils/practiceQuestionNav'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const practiceReady = ref(false)
const remoteQuestion = ref<PythonTrialQuestion | null>(null)
const questionTransitionKey = ref(0)

onMounted(() => {
  void loadQuestion(String(route.params.questionId ?? ''))
})

const questionId = computed(() => String(route.params.questionId ?? ''))
const generatedKnowledgeId = computed(() => {
  const match = /^gen-(.+)-s\d+$/.exec(questionId.value)
  return match?.[1] ?? null
})

const knowledgePoint = computed(() =>
  generatedKnowledgeId.value
    ? getStarPathKnowledgePoint(generatedKnowledgeId.value)?.point ?? null
    : null,
)

const slotIds = computed(() => {
  if (!knowledgePoint.value) return [] as string[]
  return Array.from({ length: MIN_QUESTIONS_PER_KP }, (_, slot) =>
    generatedQuestionId(knowledgePoint.value!.id, slot),
  )
})

const activeSlot = computed(() => {
  const match = /^gen-.+-s(\d+)$/.exec(questionId.value)
  if (match) return Number(match[1])
  const index = slotIds.value.indexOf(questionId.value)
  return index >= 0 ? index : 0
})

function readStoredQuestion(): PythonTrialQuestion | null {
  try {
    const raw = sessionStorage.getItem('plex:active-practice-question')
    return raw ? sanitizeQuestionContent(JSON.parse(raw) as PythonTrialQuestion) : null
  } catch {
    return null
  }
}

function wrapWithArc(base: PythonTrialQuestion): PythonTrialQuestion {
  const cleaned = sanitizeQuestionContent(base)
  if (cleaned.description.includes('星球探险') || cleaned.description.includes('🛸')) {
    return cleaned
  }
  const kp = knowledgePoint.value
  if (kp && /^gen-.+-s\d+$/.test(cleaned.id)) {
    const slotMatch = /^gen-.+-s(\d+)$/.exec(cleaned.id)
    const slot = slotMatch ? Number(slotMatch[1]) : 0
    const taskLine = cleaned.description.split('\n').filter(Boolean).pop() ?? cleaned.description
    return {
      ...cleaned,
      description: wrapEpisodeNarrative(kp.id, kp.domainKey, slot, taskLine),
    }
  }
  return cleaned
}

function resolveLocalQuestion(qid: string): PythonTrialQuestion | null {
  const cached = getCachedPracticeQuestion(qid)
  if (cached) return wrapWithArc(cached)
  const staticQuestion = getPythonTrialQuestion(qid)
  if (staticQuestion) return wrapWithArc(staticQuestion)
  const stored = readStoredQuestion()
  if (stored?.id === qid) return stored
  const kp = knowledgePoint.value
  if (!kp) return null
  const generated = resolveQuestionById(qid, kp)
  return generated ? wrapWithArc(generated) : null
}

const question = computed(() => {
  const resolved = remoteQuestion.value ?? resolveLocalQuestion(questionId.value)
  return resolved ? sanitizeQuestionContent(resolved) : null
})

const starPathNode = computed(() => getStarPathNodeByQuestionId(questionId.value))
const pageSubtitle = computed(() => {
  if (!question.value) return 'Python 入门 · 代码试炼'
  if (starPathNode.value) {
    return `星轨 ${starPathNode.value.title} · s${activeSlot.value} · ${formatQuestionLabel(question.value)}`
  }
  return formatQuestionLabel(question.value)
})

async function loadQuestion(qid: string) {
  practiceReady.value = false
  remoteQuestion.value = null
  await ensurePracticeQuestionsLoaded()
  if (!resolveLocalQuestion(qid)) {
    try {
      const item = await fetchPracticeQuestionByRef(qid)
      const base = normalizeQuestion({
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
      })
      remoteQuestion.value = wrapWithArc(base)
      stashActivePracticeQuestion(remoteQuestion.value)
    } catch {
      /* 保留下方缺失提示 */
    }
  }
  practiceReady.value = true
  questionTransitionKey.value += 1
}

function switchSlot(slot: number) {
  if (!knowledgePoint.value || slot === activeSlot.value) return
  const nextId = generatedQuestionId(knowledgePoint.value.id, slot)
  message.info(`正在切换至 s${slot} · 第 ${slot + 1} 题…`)
  void router.push(`/student/trials/practice/${encodeURIComponent(nextId)}`)
}

watch(
  () => route.params.questionId,
  (nextId) => {
    if (typeof nextId === 'string' && nextId) {
      void loadQuestion(nextId)
    }
  },
)
</script>

<template>
  <DashboardShell
    active-nav="trial"
    page-title="试炼关卡"
    :page-subtitle="pageSubtitle"
    search-placeholder="搜索题号或关键词…"
  >
    <PythonTrialWorkspace
      v-if="practiceReady && question"
      :key="`${question.id}-${questionTransitionKey}`"
      class="practice-workspace"
      :question="question"
      :slot-ids="slotIds"
      :active-slot="activeSlot"
      @select-slot="switchSlot"
    />
    <section v-else-if="!practiceReady" class="practice-missing" aria-label="题目加载中">
      <p>正在加载练习题库…</p>
    </section>
    <section v-else class="practice-missing" aria-label="题目不存在">
      <p>未找到该题目，可能已被移除或链接有误。</p>
      <n-button type="primary" @click="router.push('/student/star-path')">返回星轨学习</n-button>
    </section>
  </DashboardShell>
</template>

<style scoped>
:deep(.main-body) {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
}

.practice-workspace {
  flex: 1;
  min-height: 0;
}

.practice-missing {
  display: flex;
  min-height: 280px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin: 0 var(--plex-page-gutter-x, 1.25rem);
  padding: 2rem;
  border-radius: 16px;
  background: rgba(5, 17, 29, 0.72);
  color: rgba(226, 232, 240, 0.78);
  text-align: center;
}
</style>
