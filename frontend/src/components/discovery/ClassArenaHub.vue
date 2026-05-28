<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'
import { NButton, NIcon, NModal, NTag, useMessage } from 'naive-ui'
import {
  CheckmarkCircleOutline,
  FlashOutline,
  GameControllerOutline,
  PeopleOutline,
  PulseOutline,
  ShieldHalfOutline,
  TimerOutline,
  TrophyOutline,
} from '@vicons/ionicons5'
import TrialArenaMap from './TrialArenaMap.vue'
import TrialMcqPanel from '../trial/TrialMcqPanel.vue'
import PythonTrialWorkspace from '../trial/PythonTrialWorkspace.vue'
import { joinStudentTrial } from '../../api/studentTrials'
import {
  CLASS_ARENA_MODULES,
  RPS_SAMPLE_RULES,
  RPS_STRATEGY_EXAMPLES,
  type ClassArenaModuleKey,
} from '../../data/classArenaModules'
import {
  GLADIATOR_DUEL_QUESTIONS,
  GLADIATOR_DUEL_TIME_SEC,
  RPS_STRATEGY_QUESTION,
} from '../../data/classArenaQuestions'
import type { PythonTrialQuestion } from '../../data/pythonTrialQuestions'
import type { TrialMode } from '../../data/trialArena'

type CodeSessionKind = 'gladiator' | 'rps'

interface CodeSession {
  kind: CodeSessionKind
  question: PythonTrialQuestion
}

interface TrialMcqSession {
  trialId: number
  title: string
}

const props = defineProps<{
  className: string
  classRank: number | null
  userName: string
  userLevel: number
  trials: TrialMode[]
  trialsLoading: boolean
  trialsError: string
  selectedArenaKey: string | null
}>()

const emit = defineEmits<{
  'update:selectedArenaKey': [key: string | null]
  retryTrials: []
  sessionChange: [active: boolean]
}>()

const message = useMessage()
const activeModule = ref<ClassArenaModuleKey>('trials')
const showGladiatorModal = ref(false)
const showRpsModal = ref(false)
const duelMatching = ref(false)
const duelMatched = ref(false)
const rpsConfirmed = ref(false)
const codeSession = ref<CodeSession | null>(null)
const trialMcqSession = ref<TrialMcqSession | null>(null)
const entering = ref(false)
const gladiatorQuestionIndex = ref(0)
const gladiatorCompletedCount = ref(0)
const gladiatorRemainingSec = ref(GLADIATOR_DUEL_TIME_SEC)
const gladiatorTimerRunning = ref(false)
let gladiatorTimerId: ReturnType<typeof setInterval> | undefined

const gladiatorTotalQuestions = GLADIATOR_DUEL_QUESTIONS.length
const gladiatorTimerText = computed(() => formatTimer(gladiatorRemainingSec.value))
const gladiatorTimerUrgent = computed(() => gladiatorRemainingSec.value <= 60)

const onlineMock = computed(() => Math.max(2, (props.classRank ?? 3) % 5 + 2))
const activeTrialCount = computed(() => props.trials.length)
const rivalName = computed(() => `探索者-${String((props.classRank ?? 2) + 1).padStart(2, '0')}`)

const moduleIcon: Record<ClassArenaModuleKey, typeof TrophyOutline> = {
  trials: TrophyOutline,
  gladiator: FlashOutline,
  rps: GameControllerOutline,
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

function formatTimer(totalSec: number) {
  const sec = Math.max(0, totalSec)
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function stopGladiatorTimer() {
  gladiatorTimerRunning.value = false
  if (gladiatorTimerId !== undefined) {
    clearInterval(gladiatorTimerId)
    gladiatorTimerId = undefined
  }
}

function startGladiatorTimer() {
  stopGladiatorTimer()
  gladiatorRemainingSec.value = GLADIATOR_DUEL_TIME_SEC
  gladiatorTimerRunning.value = true
  gladiatorTimerId = setInterval(() => {
    if (gladiatorRemainingSec.value <= 0) {
      stopGladiatorTimer()
      message.warning('对决时间到！')
      return
    }
    gladiatorRemainingSec.value -= 1
  }, 1000)
}

function resetGladiatorRun() {
  stopGladiatorTimer()
  gladiatorQuestionIndex.value = 0
  gladiatorCompletedCount.value = 0
  gladiatorRemainingSec.value = GLADIATOR_DUEL_TIME_SEC
}

function buildGladiatorQuestion(index: number): PythonTrialQuestion {
  const base = GLADIATOR_DUEL_QUESTIONS[index]
  return {
    ...base,
    title: `第 ${index + 1} 题 · ${base.title}`,
    description: `${base.description}\n\n对手：${rivalName.value} · 限时 ${formatTimer(gladiatorRemainingSec.value)} · 已完成 ${gladiatorCompletedCount.value}/${gladiatorTotalQuestions} 题`,
  }
}

function openGladiatorQuestion(index: number) {
  gladiatorQuestionIndex.value = index
  openCodeSession({
    kind: 'gladiator',
    question: buildGladiatorQuestion(index),
  })
}

function selectModule(key: ClassArenaModuleKey) {
  activeModule.value = key
}

function openCodeSession(session: CodeSession) {
  codeSession.value = session
  emit('sessionChange', true)
}

function closeCodeSession() {
  if (codeSession.value?.kind === 'gladiator') {
    resetGladiatorRun()
  }
  codeSession.value = null
  duelMatched.value = false
  rpsConfirmed.value = false
  emit('sessionChange', false)
}

function closeTrialMcqSession() {
  trialMcqSession.value = null
  emit('sessionChange', false)
}

function onTrialMcqCompleted() {
  message.success('班级试炼已完成，数据已同步至数据库')
  emit('retryTrials')
  closeTrialMcqSession()
}

async function onEnterTrial(trial: TrialMode) {
  if (!trial.trialId) {
    message.warning('该试炼暂不可用')
    return
  }
  entering.value = true
  try {
    await joinStudentTrial(trial.trialId)
    trialMcqSession.value = { trialId: trial.trialId, title: trial.title }
    emit('sessionChange', true)
  } catch (error) {
    message.error(error instanceof Error ? error.message : '进入试炼失败')
  } finally {
    entering.value = false
  }
}

function startGladiatorMatch() {
  duelMatching.value = true
  window.setTimeout(() => {
    duelMatching.value = false
    duelMatched.value = true
    message.success(`已匹配对手 ${rivalName.value}`)
  }, 1200)
}

function confirmGladiatorDuel() {
  resetGladiatorRun()
  startGladiatorTimer()
  openGladiatorQuestion(0)
  message.success('对决开始！计时器已启动')
}

function confirmRpsStrategy() {
  rpsConfirmed.value = true
  openCodeSession({
    kind: 'rps',
    question: RPS_STRATEGY_QUESTION,
  })
}

async function onWorkspacePassed() {
  const session = codeSession.value
  if (!session) return
  if (session.kind === 'gladiator') {
    gladiatorCompletedCount.value += 1
    if (gladiatorQuestionIndex.value < gladiatorTotalQuestions - 1) {
      message.success(`第 ${gladiatorCompletedCount.value} 题完成，进入下一题`)
      openGladiatorQuestion(gladiatorQuestionIndex.value + 1)
      return
    }
    stopGladiatorTimer()
    message.success(`全部 ${gladiatorTotalQuestions} 题完成！用时 ${formatTimer(GLADIATOR_DUEL_TIME_SEC - gladiatorRemainingSec.value)}`)
    return
  }
  message.success('策略有效！系统将用此出招与对手进行多轮猜拳对战（演示）')
}

onUnmounted(() => {
  stopGladiatorTimer()
})
</script>

<template>
  <div class="class-arena" :class="{ 'class-arena--workspace': codeSession || trialMcqSession }">
    <template v-if="trialMcqSession">
      <TrialMcqPanel
        :trial-id="trialMcqSession.trialId"
        :trial-title="trialMcqSession.title"
        @back="closeTrialMcqSession"
        @completed="onTrialMcqCompleted"
      />
    </template>
    <template v-else-if="codeSession">
      <header
        v-if="codeSession.kind === 'gladiator'"
        class="gladiator-hud"
        aria-label="角斗士对决状态"
      >
        <div class="gladiator-hud__item" :class="{ 'gladiator-hud__item--urgent': gladiatorTimerUrgent }">
          <n-icon :component="TimerOutline" />
          <span>{{ gladiatorTimerText }}</span>
          <em>{{ gladiatorTimerRunning ? '倒计时' : '已结束' }}</em>
        </div>
        <div class="gladiator-hud__item gladiator-hud__item--progress">
          <n-icon :component="CheckmarkCircleOutline" />
          <span>完成题数 {{ gladiatorCompletedCount }} / {{ gladiatorTotalQuestions }}</span>
          <em>当前第 {{ gladiatorQuestionIndex + 1 }} 题</em>
        </div>
        <div class="gladiator-hud__item">
          <n-icon :component="PeopleOutline" />
          <span>VS {{ rivalName }}</span>
        </div>
      </header>
      <PythonTrialWorkspace
        :key="codeSession.question.id"
        :question="codeSession.question"
        embedded
        back-label="返回班级模块"
        @back="closeCodeSession"
        @passed="onWorkspacePassed"
      />
    </template>

    <template v-else>
      <header class="class-arena__overview" aria-label="班级总览">
        <div class="class-arena__overview-main">
          <p class="class-arena__eyebrow">CLASS HUB · 班级协作空间</p>
          <h2>{{ className }}</h2>
          <p class="class-arena__desc">
            与同班探索者一起完成教师高难度试炼、实时竞速编程，或用代码策略进行猜拳攻防。点击进入后均可编写并运行 Python 代码。
          </p>
        </div>
        <dl class="class-arena__stats">
          <div>
            <dt><n-icon :component="PeopleOutline" /> 同班在线</dt>
            <dd>{{ onlineMock }} 人</dd>
          </div>
          <div>
            <dt><n-icon :component="TrophyOutline" /> 进行中试炼</dt>
            <dd>{{ activeTrialCount }} 场</dd>
          </div>
          <div>
            <dt><n-icon :component="PulseOutline" /> 我的班排</dt>
            <dd>{{ classRank ? `第 ${classRank} 名` : '暂无' }}</dd>
          </div>
          <div>
            <dt><n-icon :component="ShieldHalfOutline" /> 探索者</dt>
            <dd>Lv.{{ userLevel }} · {{ userName }}</dd>
          </div>
        </dl>
      </header>

      <nav class="class-arena__modules" aria-label="班级模块">
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
        <template v-if="activeModule === 'trials'">
          <header class="panel-head">
            <h3>教师试炼场 · 高难度编程题</h3>
            <p>点击地图节点进入，将打开代码编辑区与测试运行</p>
          </header>
          <div v-if="trialsLoading" class="panel-state">正在同步班级试炼…</div>
          <div v-else-if="trialsError" class="panel-state panel-state--error">
            <span>{{ trialsError }}</span>
            <n-button secondary size="small" @click="emit('retryTrials')">重试</n-button>
          </div>
          <p v-else-if="!trials.length" class="panel-state">
            暂无进行中的班级试炼。可先体验「角斗士」或「代码攻防」模块的代码编写区。
          </p>
          <TrialArenaMap
            v-else
            :model-value="selectedArenaKey"
            :trials="trials"
            :allow-demo-fallback="false"
            :user-level="userLevel"
            @update:model-value="emit('update:selectedArenaKey', $event)"
            @enter="onEnterTrial"
          />
          <p v-if="entering" class="panel-state">正在进入试炼代码区…</p>
        </template>

        <template v-else-if="activeModule === 'gladiator'">
          <header class="panel-head">
            <h3>角斗士 · 竞速对决</h3>
            <p>匹配成功后确认进入，即可在同题代码区中与对手竞速</p>
          </header>
          <div class="duel-preview">
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
                <em>{{ duelMatched ? '已匹配 · 在线' : `同班在线 ${onlineMock} 人` }}</em>
              </article>
            </div>
            <article class="duel-problem">
              <h4>同题竞速 · 共 {{ gladiatorTotalQuestions }} 题</h4>
              <p>两数之和 → 较大值 → 乘积，连续闯关。双方题目一致，先全部 AC 者胜。</p>
              <p class="duel-problem__limit">
                <n-icon :component="TimerOutline" />
                总时限 {{ formatTimer(GLADIATOR_DUEL_TIME_SEC) }} · 开始后显示计时与完成题数
              </p>
            </article>
            <div class="duel-preview__actions">
              <n-button v-if="!duelMatched" type="primary" :loading="duelMatching" @click="startGladiatorMatch">
                寻找对手
              </n-button>
              <template v-else>
                <n-button type="primary" @click="confirmGladiatorDuel">开始对决</n-button>
                <n-button secondary @click="duelMatched = false">重新匹配</n-button>
              </template>
              <n-button quaternary size="small" @click="showGladiatorModal = true">对战流程说明</n-button>
            </div>
          </div>
        </template>

        <template v-else>
          <header class="panel-head">
            <h3>代码攻防 · 猜拳对决</h3>
            <p>确认后进入策略代码区，编写出招逻辑</p>
          </header>
          <div class="rps-preview">
            <ol class="rps-rules">
              <li v-for="(rule, index) in RPS_SAMPLE_RULES" :key="index">{{ rule }}</li>
            </ol>
            <div class="rps-strategies">
              <article v-for="item in RPS_STRATEGY_EXAMPLES" :key="item.name" class="rps-strategy">
                <strong>{{ item.name }}</strong>
                <pre><code>{{ item.code }}</code></pre>
              </article>
            </div>
            <div class="duel-preview__actions">
              <n-button type="primary" @click="confirmRpsStrategy">确认 · 进入代码编写区</n-button>
              <n-button quaternary size="small" @click="showRpsModal = true">查看对战流程</n-button>
            </div>
          </div>
        </template>
      </section>

      <n-modal v-model:show="showGladiatorModal" preset="card" title="角斗士 · 对战流程" style="max-width: 520px">
        <ol class="modal-steps">
          <li>匹配一名同时在线的同班探索者。</li>
          <li>点击「确认进入对决」，打开<strong>同一道</strong>编程题代码区。</li>
          <li>在编辑区编写 Python，运行测试；先全部通过者获胜。</li>
        </ol>
        <template #footer>
          <n-button @click="showGladiatorModal = false">知道了</n-button>
        </template>
      </n-modal>

      <n-modal v-model:show="showRpsModal" preset="card" title="代码攻防 · 猜拳规则" style="max-width: 560px">
        <p class="modal-lead">程序输出 rock / paper / scissors，系统自动多轮对战：</p>
        <ul class="modal-list">
          <li v-for="(rule, index) in RPS_SAMPLE_RULES" :key="`m-${index}`">{{ rule }}</li>
        </ul>
        <template #footer>
          <n-button @click="showRpsModal = false">关闭</n-button>
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

.gladiator-hud {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  flex-shrink: 0;
  padding: 0.55rem 0.75rem 0;
}

.gladiator-hud__item {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.45rem 0.75rem;
  border: 1px solid rgba(130, 212, 255, 0.14);
  border-radius: 999px;
  background: rgba(4, 17, 29, 0.88);
  color: #fff;
  font-size: 0.86rem;
  font-weight: 650;
}

.gladiator-hud__item em {
  color: rgba(200, 220, 235, 0.58);
  font-size: 0.68rem;
  font-style: normal;
  font-weight: 500;
}

.gladiator-hud__item--urgent {
  border-color: rgba(248, 113, 113, 0.45);
  color: #fca5a5;
}

.gladiator-hud__item--progress {
  border-color: rgba(52, 211, 153, 0.35);
  color: #6ee7b7;
}

.class-arena--workspace :deep(.py-workspace) {
  flex: 1;
  min-height: 0;
  height: auto;
  padding-top: 0.35rem;
}

.class-arena__overview {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(280px, 1fr);
  gap: 1rem;
  padding: 1rem 1.15rem;
  border: 1px solid rgba(130, 212, 255, 0.14);
  border-radius: 1rem;
  background: rgba(4, 17, 29, 0.82);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
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
  grid-template-columns: repeat(3, minmax(0, 1fr));
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
  min-height: 360px;
  padding: 0.85rem 0.95rem 1rem;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 1rem;
  background: rgba(3, 12, 22, 0.62);
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

.panel-state {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 0;
  color: rgba(220, 230, 241, 0.78);
  font-size: 0.86rem;
}

.panel-state--error {
  color: #fecaca;
}

.duel-preview,
.rps-preview {
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

.rps-rules {
  margin: 0;
  padding-left: 1.15rem;
  color: rgba(220, 230, 241, 0.72);
  font-size: 0.82rem;
  line-height: 1.55;
}

.rps-strategies {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.55rem;
}

.rps-strategy {
  padding: 0.65rem 0.75rem;
  border-radius: 0.65rem;
  border: 1px solid rgba(130, 212, 255, 0.1);
  background: rgba(8, 18, 30, 0.65);
}

.rps-strategy strong {
  display: block;
  margin-bottom: 0.35rem;
  color: #fff;
  font-size: 0.8rem;
}

.rps-strategy pre {
  margin: 0;
  overflow-x: auto;
  color: #8cecff;
  font-size: 0.72rem;
  line-height: 1.4;
}

.modal-steps,
.modal-list {
  margin: 0;
  padding-left: 1.2rem;
  color: rgba(30, 41, 59, 0.88);
  line-height: 1.55;
}

.modal-lead {
  margin: 0 0 0.5rem;
  color: rgba(30, 41, 59, 0.85);
}

@media (max-width: 1100px) {
  .class-arena__overview {
    grid-template-columns: 1fr;
  }

  .class-arena__modules {
    grid-template-columns: 1fr;
  }

  .rps-strategies {
    grid-template-columns: 1fr;
  }
}
</style>
