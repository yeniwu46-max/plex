<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { NButton, NIcon, NModal, NTag, useMessage } from 'naive-ui'
import {
  cancelDuelMatch,
  fetchDuelMatchStatus,
  fetchStatDetails,
  joinDuelMatch,
  recordDuelWin,
  type ClassmateRankItem,
  type DuelMatchDifficulty,
} from '../../api/studentOverview'
import {
  CheckmarkCircleOutline,
  DocumentTextOutline,
  FlashOutline,
  PeopleOutline,
  PulseOutline,
  TimerOutline,
  TrophyOutline,
} from '@vicons/ionicons5'
import PythonTrialWorkspace from '../trial/PythonTrialWorkspace.vue'
import {
  CLASS_ARENA_MODULES,
  MOCK_EXAM_PROBLEM_COUNT,
  MOCK_EXAM_RULES,
  MOCK_EXAM_TIME_SEC,
  STUDENT_DUEL_PROBLEM_COUNT,
  type ClassArenaModuleKey,
} from '../../data/classArenaModules'
import {
  getDefaultMockExamQuestions,
  MOCK_EXAM_SETS,
  DEFAULT_MOCK_EXAM_SET_ID,
  getMockExamQuestionsForSet,
  STUDENT_DUEL_TIME_BY_DIFFICULTY,
  STUDENT_DUEL_TIME_SEC,
  pickRandomStudentDuelQuestions,
  resolveStudentDuelQuestions,
  type StudentDuelDifficulty,
} from '../../data/classArenaQuestions'
import type { PythonTrialQuestion } from '../../data/pythonTrialQuestions'
import { ensurePracticeQuestionsLoaded } from '../../utils/practiceQuestionCache'

type CodeSessionKind = 'student_duel' | 'mock_exam'

interface CodeSession {
  kind: CodeSessionKind
  question: PythonTrialQuestion
  questionIndex: number
  totalQuestions: number
}

const props = defineProps<{
  className: string
  classRank: number | null
  userName: string
  userLevel: number
  classOnlineCount: number
}>()

const emit = defineEmits<{
  sessionChange: [active: boolean]
}>()

const message = useMessage()
const activeModule = ref<ClassArenaModuleKey>('student_duel')
const showDuelModal = ref(false)
const showExamModal = ref(false)
const showRankDetail = ref(false)
const duelMatching = ref(false)
const duelMatched = ref(false)
const codeSession = ref<CodeSession | null>(null)
const duelQuestions = ref<PythonTrialQuestion[]>([])
const examQuestions = ref<PythonTrialQuestion[]>([...getDefaultMockExamQuestions()])
const selectedExamSetId = ref(DEFAULT_MOCK_EXAM_SET_ID)
const duelQuestionIndex = ref(0)
const duelCompletedCount = ref(0)
const examQuestionIndex = ref(0)
const examCompletedCount = ref(0)
const duelDifficulty = ref<StudentDuelDifficulty>('entry')
const duelTimeLimitSec = computed(
  () => STUDENT_DUEL_TIME_BY_DIFFICULTY[duelDifficulty.value] ?? STUDENT_DUEL_TIME_SEC,
)
const duelRemainingSec = ref(STUDENT_DUEL_TIME_SEC)
const examRemainingSec = ref(MOCK_EXAM_TIME_SEC)
const duelTimerRunning = ref(false)
const examTimerRunning = ref(false)
let duelTimerId: ReturnType<typeof setInterval> | undefined
let examTimerId: ReturnType<typeof setInterval> | undefined
let matchPollId: ReturnType<typeof setInterval> | undefined

const onlineCount = computed(() => Math.max(0, props.classOnlineCount || 0))
const rivalId = ref<number | null>(null)
const rivalName = ref('等待匹配')
const topClassmates = ref<ClassmateRankItem[]>([])
const winLeaderboard = ref<ClassmateRankItem[]>([])
const matchWaitHint = ref('')

function classmateName(mate: ClassmateRankItem) {
  return (mate.real_name || mate.user_name || mate.username || '').trim() || '未命名学员'
}

const moduleIcon: Record<ClassArenaModuleKey, typeof TrophyOutline> = {
  student_duel: FlashOutline,
  mock_exam: DocumentTextOutline,
}

const statusLabel: Record<string, string> = {
  live: '已开放',
  beta: 'Beta',
  soon: '即将上线',
}

const statusType: Record<string, 'success' | 'warning' | 'default'> = {
  live: 'success',
  beta: 'warning',
  soon: 'default',
}

const duelTimerText = computed(() => formatTimer(duelRemainingSec.value))
const examTimerText = computed(() => formatTimer(examRemainingSec.value))
const duelTimerUrgent = computed(() => duelRemainingSec.value <= Math.min(60, Math.floor(duelTimeLimitSec.value / 5)))
const examTimerUrgent = computed(() => examRemainingSec.value <= 600)

function formatTimer(totalSec: number) {
  const sec = Math.max(0, totalSec)
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function stopDuelTimer() {
  duelTimerRunning.value = false
  if (duelTimerId !== undefined) {
    clearInterval(duelTimerId)
    duelTimerId = undefined
  }
}

function stopExamTimer() {
  examTimerRunning.value = false
  if (examTimerId !== undefined) {
    clearInterval(examTimerId)
    examTimerId = undefined
  }
}

function startDuelTimer() {
  stopDuelTimer()
  duelRemainingSec.value = duelTimeLimitSec.value
  duelTimerRunning.value = true
  duelTimerId = setInterval(() => {
    if (duelRemainingSec.value <= 0) {
      stopDuelTimer()
      message.warning('对战时间到！')
      return
    }
    duelRemainingSec.value -= 1
  }, 1000)
}

function startExamTimer() {
  stopExamTimer()
  examRemainingSec.value = MOCK_EXAM_TIME_SEC
  examTimerRunning.value = true
  examTimerId = setInterval(() => {
    if (examRemainingSec.value <= 0) {
      stopExamTimer()
      message.warning('考试时间到！')
      return
    }
    examRemainingSec.value -= 1
  }, 1000)
}

function resetDuelRun() {
  stopDuelTimer()
  duelQuestionIndex.value = 0
  duelCompletedCount.value = 0
  duelRemainingSec.value = duelTimeLimitSec.value
}

function stopMatchPoll() {
  if (matchPollId !== undefined) {
    clearInterval(matchPollId)
    matchPollId = undefined
  }
}

function applyMatchedResult(result: {
  difficulty?: DuelMatchDifficulty
  time_sec?: number
  question_ids?: string[]
  opponent?: { user_id: number; display_name: string }
}) {
  duelMatching.value = false
  duelMatched.value = true
  matchWaitHint.value = ''
  if (result.difficulty === 'entry' || result.difficulty === 'advanced') {
    duelDifficulty.value = result.difficulty
  }
  rivalId.value = result.opponent?.user_id ?? null
  rivalName.value = result.opponent?.display_name || '同班对手'
  const resolved = resolveStudentDuelQuestions(result.question_ids || [])
  duelQuestions.value =
    resolved.length >= STUDENT_DUEL_PROBLEM_COUNT
      ? resolved.slice(0, STUDENT_DUEL_PROBLEM_COUNT)
      : pickRandomStudentDuelQuestions(STUDENT_DUEL_PROBLEM_COUNT, duelDifficulty.value)
  duelRemainingSec.value = result.time_sec || duelTimeLimitSec.value
  stopMatchPoll()
  message.success(`已匹配对手 ${rivalName.value}，双方同一套 ${duelQuestions.value.length} 题`)
}

const activeExamSet = computed(() => MOCK_EXAM_SETS.find((item) => item.id === selectedExamSetId.value) ?? MOCK_EXAM_SETS[0])

function switchExamSet(setId: string) {
  selectedExamSetId.value = setId
  examQuestions.value = getMockExamQuestionsForSet(setId)
}

function resetExamRun() {
  stopExamTimer()
  examQuestionIndex.value = 0
  examCompletedCount.value = 0
  examRemainingSec.value = MOCK_EXAM_TIME_SEC
}

function buildDuelQuestion(index: number): PythonTrialQuestion {
  const base = duelQuestions.value[index]
  const label = base.code ? `${base.code}` : base.title
  return {
    ...base,
    title: `${label} · 对战第 ${index + 1} 题`,
  }
}

function buildExamQuestion(index: number): PythonTrialQuestion {
  const base = examQuestions.value[index]
  const label = base.code ? `${base.code}` : base.title
  return {
    ...base,
    title: `${label} · 卷面第 ${index + 1} 题`,
  }
}

function openCodeSession(session: CodeSession) {
  codeSession.value = session
  emit('sessionChange', true)
}

function openDuelQuestion(index: number) {
  duelQuestionIndex.value = index
  openCodeSession({
    kind: 'student_duel',
    question: buildDuelQuestion(index),
    questionIndex: index,
    totalQuestions: STUDENT_DUEL_PROBLEM_COUNT,
  })
}

function openExamQuestion(index: number) {
  examQuestionIndex.value = index
  openCodeSession({
    kind: 'mock_exam',
    question: buildExamQuestion(index),
    questionIndex: index,
    totalQuestions: MOCK_EXAM_PROBLEM_COUNT,
  })
}

function closeCodeSession() {
  if (codeSession.value?.kind === 'student_duel') resetDuelRun()
  if (codeSession.value?.kind === 'mock_exam') resetExamRun()
  codeSession.value = null
  resetDuelMatch()
  emit('sessionChange', false)
}

function selectModule(key: ClassArenaModuleKey) {
  activeModule.value = key
}

async function startDuelMatch(preferredOpponent?: ClassmateRankItem) {
  if (duelMatching.value) return
  duelMatching.value = true
  matchWaitHint.value = ''
  stopMatchPoll()
  try {
    const result = await joinDuelMatch({
      difficulty: duelDifficulty.value,
      opponentId: preferredOpponent?.user_id ?? null,
    })
    if (result.status === 'matched') {
      applyMatchedResult(result)
      return
    }
    matchWaitHint.value = result.message || '正在等待其他在线同学加入匹配…'
    message.info(matchWaitHint.value)
    matchPollId = setInterval(() => {
      void fetchDuelMatchStatus()
        .then((status) => {
          if (status.status === 'matched') applyMatchedResult(status)
          else if (status.status === 'waiting') {
            matchWaitHint.value = status.message || matchWaitHint.value
          }
        })
        .catch(() => undefined)
    }, 1500)
  } catch (error) {
    duelMatching.value = false
    matchWaitHint.value = ''
    message.warning(error instanceof Error ? error.message : '匹配失败，请稍后重试')
  }
}

function startPkWith(mate: ClassmateRankItem) {
  if (!mate.online) {
    message.info('该同学当前不在线，稍后再邀请 PK')
    return
  }
  showRankDetail.value = false
  activeModule.value = 'student_duel'
  void startDuelMatch(mate)
}

async function openRankDetail() {
  showRankDetail.value = true
  try {
    const details = await fetchStatDetails()
    topClassmates.value = (details.class_rank_detail.classmates || []).slice(0, 4)
    winLeaderboard.value = (details.class_rank_detail.win_leaderboard || topClassmates.value).slice(0, 5)
  } catch {
    /* keep cached */
  }
}

function resetDuelMatch() {
  stopMatchPoll()
  duelMatching.value = false
  duelMatched.value = false
  rivalId.value = null
  rivalName.value = '等待匹配'
  matchWaitHint.value = ''
  duelQuestions.value = []
  void cancelDuelMatch().catch(() => undefined)
}

function confirmDuelStart() {
  resetDuelRun()
  startDuelTimer()
  openDuelQuestion(0)
  message.success('ACM 对战开始！先 AC 者获胜')
}

function confirmExamStart() {
  resetExamRun()
  examQuestions.value = getMockExamQuestionsForSet(selectedExamSetId.value)
  startExamTimer()
  openExamQuestion(0)
  message.success('模拟考试开始，祝你好运！')
}

function onWorkspacePassed() {
  const session = codeSession.value
  if (!session) return

  if (session.kind === 'student_duel') {
    duelCompletedCount.value += 1
    if (duelQuestionIndex.value < session.totalQuestions - 1) {
      message.success(`第 ${duelCompletedCount.value} 题 AC，进入下一题`)
      openDuelQuestion(duelQuestionIndex.value + 1)
      return
    }
    stopDuelTimer()
    message.success(
      `对战胜利！${STUDENT_DUEL_PROBLEM_COUNT} 题全部 AC，用时 ${formatTimer(duelTimeLimitSec.value - duelRemainingSec.value)}`,
    )
    void recordDuelWin(rivalId.value).catch(() => undefined)
    return
  }

  examCompletedCount.value += 1
  if (examQuestionIndex.value < session.totalQuestions - 1) {
    message.success(`第 ${examCompletedCount.value} 题 AC，继续下一题`)
    openExamQuestion(examQuestionIndex.value + 1)
    return
  }
  stopExamTimer()
  const score = Math.round((examCompletedCount.value / MOCK_EXAM_PROBLEM_COUNT) * 100)
  message.success(`模拟考试结束！得分 ${score}，AC ${examCompletedCount.value}/${MOCK_EXAM_PROBLEM_COUNT} 题`)
}

onMounted(() => {
  void ensurePracticeQuestionsLoaded()
  void fetchStatDetails()
    .then((details) => {
      // 概览卡展示前 4 名，保证姓名/XP 行不被裁切
      topClassmates.value = (details.class_rank_detail.classmates || []).slice(0, 4)
      winLeaderboard.value = (details.class_rank_detail.win_leaderboard || topClassmates.value).slice(0, 5)
    })
    .catch(() => {
      topClassmates.value = []
      winLeaderboard.value = []
    })
})

onUnmounted(() => {
  stopDuelTimer()
  stopExamTimer()
  stopMatchPoll()
})
</script>

<template>
  <div class="class-arena" :class="{ 'class-arena--workspace': codeSession }">
    <template v-if="codeSession">
      <header
        v-if="codeSession.kind === 'student_duel'"
        class="arena-hud"
        aria-label="学生对战状态"
      >
        <div class="arena-hud__item" :class="{ 'arena-hud__item--urgent': duelTimerUrgent }">
          <n-icon :component="TimerOutline" />
          <span>{{ duelTimerText }}</span>
          <em>ACM 倒计时</em>
        </div>
        <div class="arena-hud__item arena-hud__item--progress">
          <n-icon :component="CheckmarkCircleOutline" />
          <span>AC {{ duelCompletedCount }} / {{ STUDENT_DUEL_PROBLEM_COUNT }}</span>
          <em>第 {{ duelQuestionIndex + 1 }} 题</em>
        </div>
        <div class="arena-hud__item">
          <n-icon :component="PeopleOutline" />
          <span>VS {{ rivalName }}</span>
        </div>
      </header>
      <header
        v-else
        class="arena-hud"
        aria-label="模拟考试状态"
      >
        <div class="arena-hud__item" :class="{ 'arena-hud__item--urgent': examTimerUrgent }">
          <n-icon :component="TimerOutline" />
          <span>{{ examTimerText }}</span>
          <em>考试剩余</em>
        </div>
        <div class="arena-hud__item arena-hud__item--progress">
          <n-icon :component="DocumentTextOutline" />
          <span>AC {{ examCompletedCount }} / {{ MOCK_EXAM_PROBLEM_COUNT }}</span>
          <em>套卷进度</em>
        </div>
      </header>
      <PythonTrialWorkspace
        :key="codeSession.question.id"
        :question="codeSession.question"
        embedded
        back-label="返回试炼场"
        @back="closeCodeSession"
        @passed="onWorkspacePassed"
      />
    </template>

    <template v-else>
      <header class="class-arena__overview class-arena__overview--tech" aria-label="试炼场总览">
        <div class="class-arena__overview-main">
          <p class="class-arena__eyebrow">TRIAL ARENA · 试炼场</p>
          <h2>{{ className }}</h2>
          <p class="class-arena__desc">
            同班对战或模拟考试套卷，进入后在代码区编写并运行 Python。
          </p>
        </div>
        <dl class="class-arena__stats">
          <div>
            <dt><n-icon :component="PeopleOutline" /> 同班在线</dt>
            <dd>{{ onlineCount }} 人</dd>
          </div>
          <div>
            <dt><n-icon :component="FlashOutline" /> 对战模式</dt>
            <dd>ACM · 3 题</dd>
          </div>
          <div class="class-arena__rank-block">
            <dt><n-icon :component="PulseOutline" /> 我的班排</dt>
            <dd class="class-arena__rank-dd">
              <span>{{ classRank ? `第 ${classRank} 名` : '暂无' }}</span>
              <n-button size="tiny" type="primary" secondary @click="openRankDetail">查看详情</n-button>
            </dd>
            <ol v-if="topClassmates.length" class="class-arena__top5">
              <li v-for="mate in topClassmates" :key="`${mate.rank}-${mate.user_id || mate.user_name}`">
                <span>#{{ mate.rank }}</span>
                <div>
                  <strong>{{ classmateName(mate) }}</strong>
                  <small>{{ mate.title || `Lv.${mate.level || 1}` }}</small>
                </div>
                <em>{{ mate.total_points ?? mate.points }} XP</em>
              </li>
            </ol>
          </div>
        </dl>
      </header>

      <nav class="class-arena__modules" aria-label="试炼场模块">
        <button
          v-for="mod in CLASS_ARENA_MODULES"
          :key="mod.key"
          type="button"
          class="module-card"
          :class="{ 'module-card--active': activeModule === mod.key }"
          @click="selectModule(mod.key)"
        >
          <span class="module-card__icon"><n-icon :component="moduleIcon[mod.key]" /></span>
          <div class="module-card__copy">
            <div class="module-card__title">
              <strong>{{ mod.title }}</strong>
              <n-tag size="small" :type="statusType[mod.status]">{{ statusLabel[mod.status] }}</n-tag>
              <n-tag v-if="mod.badge" size="tiny" :bordered="false">{{ mod.badge }}</n-tag>
            </div>
            <em>{{ mod.subtitle }}</em>
            <p>{{ mod.description }}</p>
            <div class="module-card__tags">
              <n-tag v-for="tag in mod.tags" :key="tag" size="tiny" :bordered="false">{{ tag }}</n-tag>
            </div>
          </div>
        </button>
      </nav>

      <section class="class-arena__panel" :aria-label="CLASS_ARENA_MODULES.find((m) => m.key === activeModule)?.title">
        <template v-if="activeModule === 'student_duel'">
          <header class="panel-head">
            <h3>学生对战 · ACM 赛制</h3>
            <p>匹配同班在线对手，双方同一套题，先全部 AC 者获胜</p>
          </header>
          <div class="duel-preview">
            <div class="duel-diff-tabs" role="tablist" aria-label="对战难度">
              <button
                type="button"
                role="tab"
                class="duel-diff-tab"
                :class="{ 'duel-diff-tab--active': duelDifficulty === 'entry' }"
                :aria-selected="duelDifficulty === 'entry'"
                :disabled="duelMatched || duelMatching"
                @click="duelDifficulty = 'entry'"
              >
                <strong>入门题</strong>
                <span>总时限 05:00</span>
              </button>
              <button
                type="button"
                role="tab"
                class="duel-diff-tab"
                :class="{ 'duel-diff-tab--active': duelDifficulty === 'advanced' }"
                :aria-selected="duelDifficulty === 'advanced'"
                :disabled="duelMatched || duelMatching"
                @click="duelDifficulty = 'advanced'"
              >
                <strong>进阶题</strong>
                <span>总时限 10:00</span>
              </button>
            </div>
            <div class="duel-preview__players">
              <article class="duel-player duel-player--self">
                <span class="duel-player__avatar">{{ userName.slice(0, 1) }}</span>
                <strong>{{ userName }}</strong>
                <em>你 · 已就绪</em>
              </article>
              <span class="duel-preview__vs">VS</span>
              <article class="duel-player duel-player--rival" :class="{ 'duel-player--matched': duelMatched }">
                <span class="duel-player__avatar">{{ duelMatched ? rivalName.slice(0, 1) : '?' }}</span>
                <strong>{{ duelMatched ? rivalName : '等待匹配' }}</strong>
                <em>{{ duelMatched ? `已匹配 · ${rivalName}` : `同班在线 ${onlineCount} 人` }}</em>
              </article>
            </div>
            <article class="duel-problem">
              <h4>随机 {{ STUDENT_DUEL_PROBLEM_COUNT }} 题 · ACM · {{ duelDifficulty === 'entry' ? '入门' : '进阶' }}</h4>
              <p>仅匹配真实在线同学；匹配成功后双方题目一致，先通过全部测试用例者获胜。</p>
              <p v-if="duelMatched && duelQuestions.length" class="duel-problem__limit">
                本轮题目：{{ duelQuestions.map((q) => q.title).join(' → ') }}
              </p>
              <p v-if="matchWaitHint && !duelMatched" class="duel-problem__limit">{{ matchWaitHint }}</p>
              <p class="duel-problem__limit">
                <n-icon :component="TimerOutline" />
                总时限 {{ formatTimer(duelTimeLimitSec) }}
              </p>
            </article>
            <div class="duel-preview__actions">
              <n-button v-if="!duelMatched" type="primary" :loading="duelMatching" @click="startDuelMatch()">
                {{ duelMatching ? '匹配中…' : '寻找对手' }}
              </n-button>
              <template v-else>
                <n-button type="primary" @click="confirmDuelStart">开始对战</n-button>
                <n-button secondary @click="resetDuelMatch">重新匹配</n-button>
              </template>
              <n-button v-if="duelMatching && !duelMatched" secondary @click="resetDuelMatch">取消匹配</n-button>
              <n-button quaternary size="small" @click="showDuelModal = true">ACM 规则说明</n-button>
            </div>
          </div>
        </template>

        <template v-else>
          <header class="panel-head">
            <h3>模拟考试</h3>
            <p>{{ MOCK_EXAM_PROBLEM_COUNT }} 道编程题 · 限时 {{ formatTimer(MOCK_EXAM_TIME_SEC) }}</p>
          </header>
          <div class="exam-set-tabs" role="tablist" aria-label="套卷选择">
            <button
              v-for="set in MOCK_EXAM_SETS"
              :key="set.id"
              type="button"
              role="tab"
              class="exam-set-tab"
              :class="{ 'exam-set-tab--active': selectedExamSetId === set.id }"
              :aria-selected="selectedExamSetId === set.id"
              @click="switchExamSet(set.id)"
            >
              <strong>{{ set.title }}</strong>
              <span>{{ set.difficulty }}</span>
            </button>
          </div>
          <p class="exam-set-desc">{{ activeExamSet?.description }}</p>
          <div class="exam-preview">
            <ol class="exam-rules">
              <li v-for="(rule, index) in MOCK_EXAM_RULES" :key="index">{{ rule }}</li>
            </ol>
            <div class="exam-outline">
              <article v-for="(item, index) in examQuestions" :key="item.id" class="exam-outline__item">
                <strong>第 {{ index + 1 }} 题</strong>
                <span>{{ item.title }}</span>
                <em>{{ item.topic }}</em>
              </article>
            </div>
            <div class="duel-preview__actions">
              <n-button type="primary" @click="confirmExamStart">开始模拟考试</n-button>
              <n-button quaternary size="small" @click="showExamModal = true">考试说明</n-button>
            </div>
          </div>
        </template>
      </section>

      <n-modal
        v-model:show="showRankDetail"
        preset="card"
        title="班排详情 · 对局胜局 Top5"
        style="max-width: 560px"
        class="rank-detail-modal"
      >
        <p class="rank-detail-modal__hint">按对局胜局数从高到低；在线同学可直接发起 PK。</p>
        <ol v-if="winLeaderboard.length" class="rank-detail-modal__list">
          <li v-for="mate in winLeaderboard" :key="`win-${mate.user_id || mate.win_rank || mate.rank}`">
            <span class="rank-detail-modal__pos">#{{ mate.win_rank || mate.rank }}</span>
            <div class="rank-detail-modal__meta">
              <strong>{{ classmateName(mate) }}</strong>
              <small>
                {{ mate.title || `Lv.${mate.level || 1}` }} · {{ mate.total_points ?? mate.points }} XP ·
                胜局 {{ mate.win_count ?? 0 }}
                <em :class="{ 'is-online': mate.online }">{{ mate.online ? '在线' : '离线' }}</em>
              </small>
            </div>
            <n-button
              size="tiny"
              type="primary"
              :disabled="!mate.online"
              @click="startPkWith(mate)"
            >
              与他PK
            </n-button>
          </li>
        </ol>
        <p v-else class="rank-detail-modal__empty">暂无对局榜数据，完成一场学生对战后会更新。</p>
        <template #footer>
          <n-button @click="showRankDetail = false">关闭</n-button>
        </template>
      </n-modal>

      <n-modal v-model:show="showDuelModal" preset="card" title="学生对战 · ACM 规则" style="max-width: 520px">
        <ol class="modal-steps">
          <li>系统仅匹配当前在线的同班同学；无人在线时请稍后重试。</li>
          <li>入门题总时限 5 分钟，进阶题总时限 10 分钟；双方题目一致。</li>
          <li>ACM 赛制：先通过某题全部用例即算该题 AC；先 AC 全部 {{ STUDENT_DUEL_PROBLEM_COUNT }} 题者获胜。</li>
        </ol>
        <template #footer>
          <n-button @click="showDuelModal = false">知道了</n-button>
        </template>
      </n-modal>

      <n-modal v-model:show="showExamModal" preset="card" title="模拟考试说明" style="max-width: 560px">
        <ul class="modal-list">
          <li v-for="(rule, index) in MOCK_EXAM_RULES" :key="`m-${index}`">{{ rule }}</li>
        </ul>
        <template #footer>
          <n-button @click="showExamModal = false">关闭</n-button>
        </template>
      </n-modal>
    </template>
  </div>
</template>

<style scoped>
.class-arena {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  padding-bottom: 0.5rem;
}

.class-arena--workspace {
  overflow: hidden;
  padding: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.arena-hud {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  flex-shrink: 0;
  padding: 0.35rem 0.55rem 0;
}

.arena-hud__item {
  display: flex;
  align-items: center;
  gap: 0.28rem;
  padding: 0.22rem 0.5rem;
  border: 1px solid rgba(130, 212, 255, 0.14);
  border-radius: 999px;
  background: rgba(4, 17, 29, 0.88);
  color: #fff;
  font-size: 0.72rem;
  font-weight: 650;
  line-height: 1.2;
}

.arena-hud__item :deep(.n-icon) {
  font-size: 0.85rem;
}

.arena-hud__item em {
  color: rgba(200, 220, 235, 0.58);
  font-size: 0.58rem;
  font-style: normal;
  font-weight: 500;
}

.arena-hud__item--urgent {
  border-color: rgba(248, 113, 113, 0.45);
  color: #fca5a5;
}

.arena-hud__item--progress {
  border-color: rgba(52, 211, 153, 0.35);
  color: #6ee7b7;
}

.class-arena--workspace :deep(.py-workspace) {
  flex: 1;
  min-height: 0;
  height: auto;
  padding-top: 0.2rem;
}

.class-arena--workspace :deep(.py-workspace__body) {
  /* 考试/对战态进一步拉高编程区 */
  min-height: 0;
}

.class-arena__overview {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(300px, 1.05fr);
  gap: 1rem;
  padding: 1.1rem 1.2rem 1.25rem;
  border: 1px solid rgba(130, 212, 255, 0.14);
  border-radius: 1rem;
  background: rgba(4, 17, 29, 0.82);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
  overflow: hidden;
  min-height: 0;
  animation: arena-banner-enter 0.45s ease both;
}

.class-arena__overview--tech {
  border-color: rgba(46, 255, 241, 0.22);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.04),
    0 0 18px rgba(46, 255, 241, 0.06);
}

.class-arena__overview-main,
.class-arena__stats {
  position: relative;
  z-index: 1;
}

.class-arena__rank-block {
  grid-column: 1 / -1;
  min-height: 168px;
  padding-bottom: 0.35rem !important;
}

.class-arena__rank-dd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.class-arena__top5 {
  list-style: none;
  margin: 0.5rem 0 0;
  padding: 0;
  display: grid;
  gap: 0.35rem;
  max-height: none;
  overflow: visible;
}

.class-arena__top5 li {
  display: grid;
  grid-template-columns: 2rem minmax(0, 1fr) auto;
  gap: 0.4rem;
  align-items: center;
  min-height: 2.4rem;
  padding: 0.35rem 0.45rem;
  border-radius: 0.45rem;
  background: rgba(46, 255, 241, 0.05);
  border: 1px solid rgba(46, 255, 241, 0.1);
  font-size: 0.74rem;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.class-arena__top5 li:hover {
  border-color: rgba(46, 255, 241, 0.28);
  background: rgba(46, 255, 241, 0.08);
}

.class-arena__top5 span {
  color: #52fff1;
  font-weight: 700;
}

.class-arena__top5 strong {
  display: block;
  color: #edf7ff;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.class-arena__top5 small {
  color: rgba(148, 197, 220, 0.72);
  font-size: 0.62rem;
}

.class-arena__top5 em {
  color: rgba(190, 208, 224, 0.72);
  font-style: normal;
}

@keyframes arena-banner-enter {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.rank-detail-modal__hint {
  margin: 0 0 0.75rem;
  color: rgba(200, 220, 235, 0.72);
  font-size: 0.8rem;
}

.rank-detail-modal__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.45rem;
}

.rank-detail-modal__list li {
  display: grid;
  grid-template-columns: 2.2rem minmax(0, 1fr) auto;
  gap: 0.55rem;
  align-items: center;
  padding: 0.55rem 0.65rem;
  border-radius: 0.65rem;
  border: 1px solid rgba(46, 255, 241, 0.12);
  background: rgba(8, 20, 34, 0.55);
}

.rank-detail-modal__pos {
  color: #52fff1;
  font-weight: 700;
}

.rank-detail-modal__meta strong {
  display: block;
  color: #fff;
  font-size: 0.88rem;
}

.rank-detail-modal__meta small {
  display: block;
  margin-top: 0.15rem;
  color: rgba(190, 208, 224, 0.72);
  font-size: 0.72rem;
}

.rank-detail-modal__meta em {
  margin-left: 0.35rem;
  color: rgba(148, 163, 184, 0.9);
  font-style: normal;
}

.rank-detail-modal__meta em.is-online {
  color: #6ee7b7;
}

.rank-detail-modal__empty {
  margin: 0;
  color: rgba(190, 208, 224, 0.68);
  font-size: 0.82rem;
}

.class-arena__eyebrow {
  margin: 0;
  color: rgba(46, 255, 241, 0.75);
  font-size: 0.72rem;
  letter-spacing: 0.08em;
}

.class-arena__overview-main h2 {
  margin: 0.35rem 0 0;
  color: #fff;
  font-size: 1.35rem;
}

.class-arena__desc {
  margin: 0.55rem 0 0;
  color: rgba(220, 230, 241, 0.68);
  font-size: 0.84rem;
  line-height: 1.55;
  max-width: 52ch;
}

.class-arena__stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
  margin: 0;
}

.class-arena__stats div {
  padding: 0.55rem 0.65rem;
  border-radius: 0.65rem;
  border: 1px solid rgba(130, 212, 255, 0.1);
  background: rgba(8, 20, 34, 0.55);
}

.class-arena__stats dt {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin: 0;
  color: rgba(200, 220, 235, 0.62);
  font-size: 0.72rem;
}

.class-arena__stats dd {
  margin: 0.25rem 0 0;
  color: #fff;
  font-size: 0.95rem;
  font-weight: 650;
}

.class-arena__modules {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
}

.module-card {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.65rem;
  align-items: start;
  padding: 0.75rem 0.85rem;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 0.85rem;
  background: rgba(4, 12, 20, 0.55);
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.module-card:hover,
.module-card--active {
  border-color: rgba(37, 245, 238, 0.42);
  background: rgba(37, 245, 238, 0.08);
}

.module-card__icon {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: 50%;
  color: #2efff1;
  background: rgba(37, 245, 238, 0.12);
  font-size: 1.25rem;
}

.module-card__title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
}

.module-card__title strong {
  color: #fff;
  font-size: 0.88rem;
}

.module-card__copy em {
  display: block;
  margin-top: 0.15rem;
  color: rgba(167, 139, 250, 0.75);
  font-size: 0.68rem;
  font-style: normal;
}

.module-card__copy p {
  margin: 0.35rem 0 0;
  color: rgba(220, 230, 241, 0.62);
  font-size: 0.76rem;
  line-height: 1.45;
}

.module-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-top: 0.4rem;
}

.class-arena__panel {
  flex: 1;
  min-height: 420px;
  padding: 0.85rem 0.95rem 1.15rem;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 1rem;
  background: rgba(3, 12, 22, 0.62);
}

.duel-diff-tabs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.45rem;
}

.duel-diff-tab {
  display: grid;
  gap: 0.12rem;
  padding: 0.55rem 0.7rem;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 0.65rem;
  background: rgba(6, 16, 28, 0.55);
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.duel-diff-tab strong {
  color: #fff;
  font-size: 0.82rem;
}

.duel-diff-tab span {
  color: rgba(200, 220, 235, 0.62);
  font-size: 0.72rem;
}

.duel-diff-tab--active {
  border-color: rgba(37, 245, 238, 0.45);
  background: rgba(37, 245, 238, 0.1);
}

.duel-diff-tab:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.panel-head h3 {
  margin: 0;
  color: #37fff1;
  font-size: 1rem;
}

.panel-head p {
  margin: 0.25rem 0 0.75rem;
  color: rgba(220, 230, 241, 0.58);
  font-size: 0.78rem;
}

.duel-preview,
.exam-preview {
  display: grid;
  gap: 1rem;
}

.duel-preview__players {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1.25rem;
}

.duel-player {
  display: grid;
  justify-items: center;
  gap: 0.35rem;
  min-width: 120px;
  padding: 0.75rem;
  border-radius: 0.75rem;
  border: 1px solid rgba(130, 212, 255, 0.12);
  background: rgba(8, 20, 34, 0.55);
}

.duel-player--self {
  border-color: rgba(46, 255, 241, 0.35);
}

.duel-player--matched {
  border-color: rgba(255, 197, 109, 0.45);
}

.duel-player__avatar {
  display: grid;
  width: 48px;
  height: 48px;
  place-items: center;
  border-radius: 50%;
  background: rgba(37, 245, 238, 0.18);
  color: #2efff1;
  font-size: 1.1rem;
  font-weight: 700;
}

.duel-player--matched .duel-player__avatar {
  background: rgba(255, 197, 109, 0.18);
  color: #ffc56d;
}

.duel-player strong {
  color: #fff;
  font-size: 0.88rem;
}

.duel-player em {
  color: rgba(200, 220, 235, 0.6);
  font-size: 0.72rem;
  font-style: normal;
}

.duel-preview__vs {
  color: #ffc56d;
  font-size: 1.1rem;
  font-weight: 800;
}

.duel-problem {
  padding: 0.85rem 1rem;
  border-radius: 0.75rem;
  border: 1px solid rgba(130, 212, 255, 0.1);
  background: rgba(6, 16, 28, 0.65);
}

.duel-problem h4 {
  margin: 0;
  color: #fff;
  font-size: 0.95rem;
}

.duel-problem p {
  margin: 0.45rem 0 0;
  color: rgba(220, 230, 241, 0.72);
  font-size: 0.84rem;
}

.duel-problem__limit {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin-top: 0.65rem !important;
  color: rgba(255, 197, 109, 0.9) !important;
  font-size: 0.78rem !important;
}

.duel-preview__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.55rem;
}

.exam-set-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.45rem;
  margin-bottom: 0.65rem;
}

.exam-set-tab {
  display: grid;
  gap: 0.15rem;
  padding: 0.55rem 0.65rem;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 0.65rem;
  background: rgba(6, 16, 28, 0.55);
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.exam-set-tab strong {
  color: #fff;
  font-size: 0.76rem;
  line-height: 1.35;
}

.exam-set-tab span {
  color: rgba(200, 220, 235, 0.58);
  font-size: 0.68rem;
}

.exam-set-tab--active {
  border-color: rgba(37, 245, 238, 0.45);
  background: rgba(37, 245, 238, 0.1);
}

.exam-set-desc {
  margin: 0 0 0.75rem;
  color: rgba(220, 230, 241, 0.68);
  font-size: 0.78rem;
  line-height: 1.5;
}

.exam-rules {
  margin: 0;
  padding-left: 1.15rem;
  color: rgba(220, 230, 241, 0.72);
  font-size: 0.82rem;
  line-height: 1.55;
}

.exam-outline {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.55rem;
}

.exam-outline__item {
  padding: 0.65rem 0.75rem;
  border-radius: 0.65rem;
  border: 1px solid rgba(130, 212, 255, 0.1);
  background: rgba(8, 18, 30, 0.65);
}

.exam-outline__item strong {
  display: block;
  color: #5fffe8;
  font-size: 0.74rem;
}

.exam-outline__item span {
  display: block;
  margin-top: 0.2rem;
  color: #fff;
  font-size: 0.82rem;
}

.exam-outline__item em {
  display: block;
  margin-top: 0.15rem;
  color: rgba(200, 220, 235, 0.55);
  font-size: 0.68rem;
  font-style: normal;
}

.modal-steps,
.modal-list {
  margin: 0;
  padding-left: 1.2rem;
  color: rgba(226, 232, 240, 0.88);
  line-height: 1.55;
}

@media (max-width: 1100px) {
  .class-arena__overview {
    grid-template-columns: 1fr;
  }

  .class-arena__modules {
    grid-template-columns: 1fr;
  }

  .exam-outline {
    grid-template-columns: 1fr;
  }
}
</style>
