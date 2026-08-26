<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { NButton, NInput, NModal, NProgress, NRadio, NRadioGroup, NTag, useMessage } from 'naive-ui'
import DashboardShell from '../components/layout/DashboardShell.vue'
import PlexSyncState from '../components/common/PlexSyncState.vue'
import PlexRadarChart from '../components/charts/PlexRadarChart.vue'
import MarkdownRenderer from '../components/common/MarkdownRenderer.vue'
import {
  chatDynamicProfile, fetchDynamicProfile, fetchProfileDiagnostic, fetchLearningAdaptations,
  recalibrateDynamicProfile, streamProfileChat, submitProfileDiagnostic,
  type DynamicStudentProfile, type LearningAdaptation, type OnboardingDiagnosticQuestion,
  type ProfileChatResult, type ProfileDimensionKey,
} from '../api/personalizedProfile'
import { fetchStudentLearningReport, generateStudentPhaseReport, type LearningReportResult, type PhaseLearningReport } from '../api/learningReport'

const message = useMessage()
const profile = ref<DynamicStudentProfile | null>(null)
const report = ref<LearningReportResult | null>(null)
const aiReport = ref<PhaseLearningReport | null>(null)
const updatingReport = ref(false)
const adaptations = ref<LearningAdaptation[]>([])
const questions = ref<OnboardingDiagnosticQuestion[]>([])
const answers = ref<Record<string, number>>({})
const diagnosticStatus = ref('pending')
const diagnosticVisible = ref(false)
const calibrationVisible = ref(false)
watch(calibrationVisible, (visible) => {
  if (!visible) {
    calibrationDraft.value = {}
    calibrationTouched.value = false
    return
  }
  calibrationTouched.value = false
  // 打开时用当前画像预填草稿
  const dims = profile.value?.dimensions
  if (dims) {
    const draft: Partial<Record<ProfileDimensionKey, string>> = {}
    for (const key of Object.keys(calibrationOptions) as ProfileDimensionKey[]) {
      const value = dims[key]?.value
      if (value) draft[key] = value
    }
    calibrationDraft.value = draft
  }
})
const selectedCalibration = ref<ProfileDimensionKey>('explanation_preference')
/** 弹窗内待保存的维度草稿（点选项先选中，点「保存并调整」再提交） */
const calibrationDraft = ref<Partial<Record<ProfileDimensionKey, string>>>({})
const calibrationTouched = ref(false)
const saving = ref(false)
const loading = ref(true)

const coreIdentity = computed(() => ({
  stage: report.value?.summary.level_label || 'Python 起航者',
  mission: adaptations.value[0]?.knowledge_key ? `理解 ${adaptations.value[0].knowledge_key} 执行逻辑` : '建立 Python 基础学习节奏',
  mode: profile.value?.dimensions.explanation_preference?.value || '图解辅助型',
  minutes: profile.value?.dimensions.learning_pace?.value?.match(/\d+/)?.[0] || '25',
}))
const radarLabels = computed(() => ['基础语法', '条件判断', '循环控制', '数据结构', '问题求解'])
const radarValues = computed(() => {
  const raw = report.value?.radar.values || []
  return raw.length >= 5 ? raw.slice(0, 5) : [36, 30, 24, 28, 22]
})
const mistakes = computed(() => report.value?.mistake_highlights.slice(0, 3) || [])
const stateText = computed(() => profile.value?.dimensions.cognitive_state?.value || '学习状态稳定，继续保持短时专注练习。')
const calibrationOptions: Record<ProfileDimensionKey, Array<{ label: string; value: string }>> = {
  major_background: [{ label: '零基础探索', value: '零基础探索者' }, { label: '有编程经验', value: '已有基础编程经验' }],
  knowledge_foundation: [{ label: '从基础开始', value: '希望从 Python 基础开始' }, { label: '优先补薄弱点', value: '优先补齐薄弱知识点' }],
  learning_goal: [{ label: '完成入门', value: '完成 Python 入门学习' }, { label: '准备考试', value: '准备课程考试与练习' }, { label: '完成项目', value: '完成一个 Python 小项目' }],
  explanation_preference: [{ label: '图解辅助', value: '图解辅助型' }, { label: '代码示例', value: '代码示例优先' }, { label: '先练后讲', value: '微练习后分步讲解' }],
  mistake_pattern: [{ label: '循环边界', value: '重点关注循环与 range 边界' }, { label: '列表索引', value: '重点关注列表索引与边界' }, { label: '条件逻辑', value: '重点关注条件判断逻辑' }],
  learning_pace: [{ label: '15 分钟', value: '每天 15 分钟短练' }, { label: '25 分钟', value: '每天 25 分钟专注练习' }, { label: '40 分钟', value: '每天 40 分钟进阶学习' }],
  interest_direction: [{ label: '数据处理', value: '对数据处理感兴趣' }, { label: '小游戏', value: '对 Python 小游戏感兴趣' }, { label: '自动化', value: '对自动化脚本感兴趣' }],
  cognitive_state: [{ label: '稳步推进', value: '学习状态稳定，适合稳步推进' }, { label: '需要图解', value: '面对复杂逻辑时需要图解辅助' }, { label: '降低负荷', value: '希望降低单次练习负荷' }],
}

type QuestionBadgeType = 'default' | 'success' | 'warning' | 'info' | 'error'
function questionKind(question: OnboardingDiagnosticQuestion): { label: string; type: QuestionBadgeType } {
  switch (question.question_type) {
    case 'code_reading': return { label: '代码阅读', type: 'success' }
    case 'scenario': return { label: '情境判断', type: 'warning' }
    case 'true_false': return { label: '判断对错', type: 'error' }
    case 'fill_blank': return { label: '代码填空', type: 'info' }
    default:
      if (question.knowledge_key === 'loop' || question.knowledge_key === 'range') return { label: '代码阅读', type: 'success' }
      if (question.knowledge_key === 'except') return { label: '情境判断', type: 'warning' }
      return { label: '概念选择', type: 'default' }
  }
}
// ===== 画像对话工作台 =====
const DIMENSION_LABELS: Record<ProfileDimensionKey, string> = {
  major_background: '专业背景',
  knowledge_foundation: '知识基础',
  learning_goal: '学习目标',
  explanation_preference: '讲解偏好',
  mistake_pattern: '易错模式',
  learning_pace: '学习节奏',
  interest_direction: '兴趣方向',
  cognitive_state: '认知状态',
}
const DIMENSION_KEYS = Object.keys(DIMENSION_LABELS) as ProfileDimensionKey[]

type ProfileChatMessage = {
  role: 'user' | 'assistant'
  text: string
  streaming?: boolean
  stageLabel?: string
}

const chatInput = ref('')
const chatBusy = ref(false)
const profileChatMessages = ref<ProfileChatMessage[]>([])
const chatThreadEl = ref<HTMLElement | null>(null)
const changedDimensions = ref<Set<ProfileDimensionKey>>(new Set())
const pendingChanges = ref<ProfileChatResult['proposed_changes']>([])
const lastUserMessage = ref('')

const dimensionCards = computed(() =>
  DIMENSION_KEYS.map((key) => {
    const dim = profile.value?.dimensions?.[key]
    return {
      key,
      label: DIMENSION_LABELS[key],
      value: dim?.value || '待了解',
      confidence: Math.round((dim?.confidence ?? 0) * 100),
      source: dim?.source ?? 'mixed',
      changed: changedDimensions.value.has(key),
    }
  }),
)

const sourceLabels: Record<string, string> = {
  conversation: '对话', behavior: '行为', mixed: '综合', confirmed: '已确认',
}

function scrollChatToBottom() {
  void nextTick(() => {
    const el = chatThreadEl.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function applyChatResult(result: ProfileChatResult, live: ProfileChatMessage) {
  profile.value = result.profile
  changedDimensions.value = new Set(result.proposed_changes.map((c) => c.dimension))
  pendingChanges.value = result.proposed_changes.filter((c) => c.requires_confirmation)
  // 保留已流式输出的正文；若流式为空再用最终文案兜底
  if (!live.text && result.assistant_reply) live.text = result.assistant_reply
  live.streaming = false
  live.stageLabel = undefined
}

async function sendProfileChat(text: string, confirmChanges = false) {
  if (!text || chatBusy.value) return
  chatBusy.value = true
  lastUserMessage.value = text
  profileChatMessages.value.push({ role: 'user', text })
  const placeholder: ProfileChatMessage = {
    role: 'assistant',
    text: '',
    streaming: true,
    stageLabel: '小E 正在思考下一个问题',
  }
  profileChatMessages.value.push(placeholder)
  const live = profileChatMessages.value[profileChatMessages.value.length - 1]!
  scrollChatToBottom()
  const history = profileChatMessages.value
    .slice(0, -1)
    .map((msg) => ({ role: msg.role, content: msg.text }))
  try {
    const result = await streamProfileChat(
      text,
      confirmChanges,
      (delta) => {
        live.stageLabel = undefined
        live.text += delta
        scrollChatToBottom()
      },
      (_stage, label) => {
        if (!live.text) live.stageLabel = label
      },
      undefined,
      history,
    )
    applyChatResult(result, live)
  } catch (error) {
    try {
      const result = await chatDynamicProfile(text, confirmChanges)
      live.text = result.assistant_reply
      applyChatResult(result, live)
    } catch (fallbackError) {
      live.streaming = false
      live.stageLabel = undefined
      const errText = fallbackError instanceof Error
        ? fallbackError.message
        : error instanceof Error ? error.message : '画像分析失败，请稍后再试'
      live.text = errText
      message.error(errText)
    }
  } finally {
    chatBusy.value = false
    scrollChatToBottom()
  }
}

async function submitProfileChat() {
  const text = chatInput.value.trim()
  if (!text) return
  chatInput.value = ''
  await sendProfileChat(text)
}

async function confirmPendingChanges() {
  if (!lastUserMessage.value || chatBusy.value) return
  await sendProfileChat(lastUserMessage.value, true)
  message.success('低置信度画像条目已确认更新')
}

const chatStarters = [
  '我是计算机专业大二学生，Python 刚入门，想在期末前掌握循环和函数',
  '我学东西喜欢先看例子再看讲解，每天大概能抽出 25 分钟练习',
  '我经常在 range 边界和列表索引上出错，讲解时最好配图',
]

async function load() {
  loading.value = true
  try {
    const [current, diagnostic, learning, active] = await Promise.all([
      fetchDynamicProfile(), fetchProfileDiagnostic(), fetchStudentLearningReport('7d'), fetchLearningAdaptations(),
    ])
    profile.value = current
    questions.value = diagnostic.questions
    diagnosticStatus.value = diagnostic.diagnostic.status
    report.value = learning
    adaptations.value = active
    // 阶段报告可异步补齐，不阻塞首屏画像
    void generateStudentPhaseReport('7d')
      .then((result) => { aiReport.value = result.report })
      .catch(() => { aiReport.value = null })
  } finally {
    loading.value = false
  }
}

async function refreshPhaseReport() {
  if (updatingReport.value) return
  updatingReport.value = true
  try {
    const result = await generateStudentPhaseReport('7d', { force: true })
    aiReport.value = result.report
    message.success('阶段性薄弱点报告已根据近期做题与最新画像更新')
  } catch (error) {
    message.error(error instanceof Error ? error.message : '更新报告失败')
  } finally {
    updatingReport.value = false
  }
}
async function finishDiagnostic(skip = false) {
  saving.value = true
  try {
    const result = await submitProfileDiagnostic(answers.value, skip)
    profile.value = result.profile; diagnosticStatus.value = skip ? 'skipped' : 'completed'; diagnosticVisible.value = false
    await load(); message.success(skip ? '已跳过测验，小E 会根据后续练习补全画像' : '诊断完成，学习报告已刷新')
  } catch (error) { message.error(error instanceof Error ? error.message : '诊断提交失败') } finally { saving.value = false }
}
function pickCalibrationOption(value: string) {
  calibrationTouched.value = true
  calibrationDraft.value = {
    ...calibrationDraft.value,
    [selectedCalibration.value]: value,
  }
}

const calibrationDirty = computed(
  () => calibrationTouched.value && Object.keys(calibrationDraft.value).length > 0,
)

async function saveAndRecalibrate() {
  if (!calibrationDirty.value || saving.value) return
  saving.value = true
  try {
    const changes = { ...calibrationDraft.value }
    const result = await recalibrateDynamicProfile(changes)
    profile.value = result.profile
    changedDimensions.value = new Set(Object.keys(result.applied_changes) as ProfileDimensionKey[])
    calibrationVisible.value = false
    await load()
    const provider = result.backend === 'spark' ? '讯飞星火' : '大模型'
    message.success(`已通过${provider} API 校准并更新用户画像`)
  } catch (error) {
    message.error(error instanceof Error ? error.message : '画像校准失败')
  } finally {
    saving.value = false
  }
}
onMounted(() => { void load().catch((error) => message.error(error instanceof Error ? error.message : '学习画像加载失败')) })
</script>

<template>
  <DashboardShell active-nav="me" page-title="学习画像" page-subtitle="小E 会根据你的练习持续更新学习报告" search-placeholder="" hide-search>
    <main class="profile-page">
      <PlexSyncState
        v-if="loading && !profile"
        label="正在整理学习画像…"
        hint="小E 正在汇总诊断、对话与练习证据"
      />
      <section class="profile-header">
        <div><p class="eyebrow">学习画像 · 第 {{ profile?.version ?? 1 }} 版</p><h2>今天，先让学习路径更懂你</h2><p>基于诊断、对话和练习行为生成。每一条结论都可以通过“校准画像”调整。</p></div>
        <div class="header-actions"><n-progress type="circle" :percentage="profile?.completion_rate ?? 0" color="#34e6c5" /><n-button type="primary" @click="diagnosticVisible = true">{{ diagnosticStatus === 'pending' ? '开始入门诊断' : '重新进行诊断' }}</n-button></div>
      </section>

      <section class="chat-workbench" data-tour="profile-chat">
        <article class="chat-panel">
          <header class="chat-panel__head">
            <div><span class="eyebrow">对话式画像构建</span><h3>和小E聊聊，画像实时刷新</h3></div>
            <n-tag size="small" round type="success" :bordered="false">流式对话</n-tag>
          </header>
          <div ref="chatThreadEl" class="chat-panel__thread">
            <div v-if="!profileChatMessages.length" class="chat-panel__empty">
              <p>先随便介绍一句你的专业、目标或学习困惑，小E 会主动追问并实时刷新右侧画像。</p>
              <button
                v-for="starter in chatStarters"
                :key="starter"
                type="button"
                class="chat-panel__starter"
                :disabled="chatBusy"
                @click="void sendProfileChat(starter)"
              >
                {{ starter }}
              </button>
            </div>
            <article v-for="(msg, idx) in profileChatMessages" :key="idx" :class="`chat-panel__msg chat-panel__msg--${msg.role}`">
              <template v-if="msg.role === 'assistant'">
                <p v-if="msg.streaming && !msg.text" class="chat-panel__stage">
                  {{ msg.stageLabel || '小E 正在整理回复' }}…
                </p>
                <MarkdownRenderer v-if="msg.text" :content="msg.text" :streaming="msg.streaming" />
                <span v-if="msg.streaming" class="chat-panel__cursor" aria-hidden="true" />
              </template>
              <p v-else>{{ msg.text }}</p>
            </article>
            <div v-if="pendingChanges.length && !chatBusy" class="chat-panel__pending">
              <p>小E 不太确定这些信息，确认后会写入画像：</p>
              <ul>
                <li v-for="change in pendingChanges" :key="change.dimension">
                  <strong>{{ change.label }}</strong>：{{ change.new_value }}
                </li>
              </ul>
              <n-button size="small" type="primary" @click="confirmPendingChanges">确认更新</n-button>
            </div>
          </div>
          <div class="chat-panel__composer">
            <n-input
              v-model:value="chatInput"
              placeholder="介绍一下你的专业、目标、学习偏好…"
              :disabled="chatBusy"
              @keydown.enter.prevent="submitProfileChat"
            />
            <n-button type="primary" :loading="chatBusy" @click="submitProfileChat">发送</n-button>
          </div>
        </article>
        <article class="dimension-panel">
          <header class="chat-panel__head">
            <div><span class="eyebrow">动态学生画像</span><h3>8 维画像 · 第 {{ profile?.version ?? 1 }} 版</h3></div>
          </header>
          <div class="dimension-grid">
            <div
              v-for="card in dimensionCards"
              :key="card.key"
              class="dimension-card"
              :class="{ 'dimension-card--changed': card.changed }"
            >
              <header>
                <small>{{ card.label }}</small>
                <n-tag size="tiny" round :bordered="false" :type="card.source === 'confirmed' ? 'success' : 'info'">
                  {{ sourceLabels[card.source] ?? card.source }}
                </n-tag>
              </header>
              <strong>{{ card.value }}</strong>
              <div class="dimension-card__meter" role="presentation">
                <i :style="{ width: `${card.confidence}%` }" />
              </div>
              <small class="dimension-card__confidence">置信度 {{ card.confidence }}%</small>
            </div>
          </div>
        </article>
      </section>

      <section class="identity-card"><div class="identity-title"><h3>当前学习身份</h3></div><div class="identity-grid"><div><small>当前阶段</small><strong>{{ coreIdentity.stage }}</strong></div><div><small>当前任务</small><strong>{{ coreIdentity.mission }}</strong></div><div><small>当前学习模式</small><strong>{{ coreIdentity.mode }}</strong></div><div><small>今日推荐时长</small><strong>{{ coreIdentity.minutes }} 分钟</strong></div></div></section>

      <section class="report-grid" data-tour="student-learning-report">
        <article class="report-card radar-card"><header><h3>知识雷达图</h3><p>只关注五个会直接影响下一步学习的核心能力。</p></header><plex-radar-chart :dimensions="radarLabels" :values="radarValues" title="当前掌握度" color="#34e6c5" /></article>
        <article class="report-card"><header><h3>易错模式</h3><p>小E 从近期作答中提取，优先安排针对性练习。</p></header><ul class="mistake-list"><li v-for="item in mistakes" :key="item.id"><i>!</i><div><strong>{{ item.knowledge_label }}</strong><span>{{ item.question_title || '高频错误，建议用微练习巩固' }}</span></div></li><li v-if="!mistakes.length" class="empty">完成几道练习后，小E 会帮你找出高频错误。</li></ul></article>
        <article class="report-card state-card"><header><h3>学习状态提醒</h3></header><p>{{ stateText }}</p><div v-if="adaptations.length" class="adaptation"><n-tag type="warning">小E 已介入</n-tag><strong>{{ adaptations[0].action_plan.resources.join(' + ') }}</strong><small>{{ adaptations[0].action_plan.recovery_rule }}</small></div><div v-else class="adaptation stable"><n-tag type="success">节奏稳定</n-tag><strong>继续保持 25 分钟短时专注</strong><small>下一次练习会根据正确率自动调整。</small></div></article>
      </section>

      <section class="ai-summary">
        <header>
          <div>
            <span>小E 的阶段分析</span>
            <h3>{{ aiReport?.headline || '正在整理你的阶段学习报告' }}</h3>
          </div>
          <div class="ai-summary__actions">
            <n-tag size="small">{{ aiReport ? '已基于近 7 天数据' : '等待学习证据' }}</n-tag>
            <n-button size="small" type="primary" secondary :loading="updatingReport" @click="refreshPhaseReport">
              更新报告
            </n-button>
          </div>
        </header>
        <p v-for="line in aiReport?.summary" :key="line">{{ line }}</p>
        <div v-if="aiReport?.focus_items?.length" class="focus-items">
          <strong>薄弱点与证据</strong>
          <ul>
            <li v-for="item in aiReport.focus_items" :key="`${item.label}-${item.knowledge_key || ''}`">
              <em>{{ item.label }}</em>
              <span>{{ item.reason }}</span>
            </li>
          </ul>
        </div>
        <div class="next-actions">
          <strong>下一步建议</strong>
          <ol>
            <li v-for="item in aiReport?.next_actions" :key="item">{{ item }}</li>
            <li v-if="!aiReport?.next_actions?.length">先完成一轮短练习，小E 会给出更具体的下一步。</li>
          </ol>
        </div>
      </section>

      <section class="calibration"><div><span>不是填表，而是让小E 更懂你</span><h3>校准我的学习画像</h3><p>选择更接近你的真实偏好，小E 会立刻重排资源和学习节奏。</p></div><n-button secondary type="primary" @click="calibrationVisible = true">优化画像</n-button></section>
    </main>

    <n-modal
      v-model:show="diagnosticVisible"
      preset="card"
      class="diagnostic-modal"
      :style="{ width: 'min(520px, 92vw)', maxWidth: '92vw' }"
      title="Python 入门诊断"
    >
      <template #header-extra><n-tag size="small" round type="info">已答 {{ Object.keys(answers).length }} / {{ questions.length }}</n-tag></template>
      <p class="modal-intro">这不是考试，而是帮小E 了解你的起点，生成更合适的首周学习计划。</p>
      <n-progress class="diagnostic-progress" type="line" :height="6" :show-indicator="false" :percentage="questions.length ? Math.round(Object.keys(answers).length / questions.length * 100) : 0" color="#34e6c5" />
      <div class="diagnostic-body">
        <article v-for="(question, index) in questions" :key="question.id" class="question">
          <header><span class="q-index">Q{{ index + 1 }}</span><n-tag size="small" round :type="questionKind(question).type" :bordered="false">{{ questionKind(question).label }}</n-tag></header>
          <p class="q-stem">{{ question.stem }}</p>
          <pre v-if="question.code_preview" class="q-code">{{ question.code_preview }}</pre>
          <n-radio-group v-model:value="answers[question.id]" class="q-options">
            <n-radio v-for="(option, optionIndex) in question.options" :key="option" :value="optionIndex">{{ option }}</n-radio>
          </n-radio-group>
        </article>
      </div>
      <template #footer><div class="modal-footer"><n-button text @click="finishDiagnostic(true)">暂时跳过</n-button><n-button type="primary" :loading="saving" :disabled="Object.keys(answers).length !== questions.length" @click="finishDiagnostic()">生成我的 AI 学习报告</n-button></div></template>
    </n-modal>

    <n-modal
      v-model:show="calibrationVisible"
      preset="card"
      class="calibration-modal"
      :style="{ width: 'min(420px, 92vw)', maxWidth: '92vw' }"
      title="优化学习画像"
    >
      <p class="modal-intro">选择你最认可的学习方式，AI 会以此校准资源推荐和讲解策略。</p>
      <div class="calibration-tabs">
        <n-button
          v-for="key in (Object.keys(calibrationOptions) as ProfileDimensionKey[])"
          :key="key"
          size="small"
          :type="selectedCalibration === key ? 'primary' : 'default'"
          @click="selectedCalibration = key"
        >
          {{ DIMENSION_LABELS[key] }}
        </n-button>
      </div>
      <div class="option-grid">
        <n-button
          v-for="option in calibrationOptions[selectedCalibration]"
          :key="option.value"
          secondary
          :type="calibrationDraft[selectedCalibration] === option.value ? 'primary' : 'default'"
          @click="pickCalibrationOption(option.value)"
        >
          {{ option.label }}
        </n-button>
      </div>
      <p v-if="selectedCalibration === 'mistake_pattern'" class="calibration-hint">
        近期错题证据不足时，建议先完成 2–3 道代码试炼以生成更准确诊断。
      </p>
      <template #footer>
        <div class="modal-footer">
          <n-button text @click="calibrationVisible = false">取消</n-button>
          <n-button
            type="primary"
            :loading="saving || chatBusy"
            :disabled="!calibrationDirty"
            @click="saveAndRecalibrate"
          >
            保存并调整
          </n-button>
        </div>
      </template>
    </n-modal>
  </DashboardShell>
</template>

<style scoped>
.chat-workbench{display:grid;grid-template-columns:1.2fr 1fr;gap:1rem;margin-bottom:1rem}
.chat-panel,.dimension-panel{border:1px solid rgba(52,230,197,.16);background:rgba(3,16,28,.86);border-radius:16px;padding:1.1rem;display:flex;flex-direction:column;min-height:430px}
.chat-panel__head{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.6rem}
.chat-panel__head h3{margin:.3rem 0 0;color:#f5fbff}
.chat-panel__thread{flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:.6rem;padding-right:.35rem;max-height:420px}
.chat-panel__thread::-webkit-scrollbar{width:6px}
.chat-panel__thread::-webkit-scrollbar-thumb{background:rgba(52,230,197,.28);border-radius:3px}
.chat-panel__empty{color:#8da7b6;font-size:.86rem;display:grid;gap:.5rem}
.chat-panel__starter{text-align:left;padding:.55rem .8rem;border:1px dashed rgba(52,230,197,.3);border-radius:10px;background:rgba(52,230,197,.05);color:#bfe6dc;cursor:pointer;font-size:.82rem}
.chat-panel__starter:hover{background:rgba(52,230,197,.12)}
.chat-panel__msg{max-width:92%;padding:.6rem .85rem;border-radius:12px;font-size:.88rem;line-height:1.6}
.chat-panel__msg--user{align-self:flex-end;background:rgba(52,230,197,.14);color:#eafcf7;border:1px solid rgba(52,230,197,.25)}
.chat-panel__msg--user p{margin:0}
.chat-panel__msg--assistant{align-self:flex-start;background:rgba(255,255,255,.04);color:#d9e9f1;border:1px solid rgba(120,160,180,.14)}
.chat-panel__stage{margin:0;color:#39e6c7;font-size:.82rem}
.chat-panel__cursor{display:inline-block;width:8px;height:1em;margin-left:2px;vertical-align:text-bottom;background:#34e6c5;border-radius:1px;animation:profile-cursor-blink .9s steps(2,start) infinite}
@keyframes profile-cursor-blink{to{visibility:hidden}}
.chat-panel__pending{border:1px solid rgba(255,184,90,.35);background:rgba(255,184,90,.07);border-radius:10px;padding:.7rem .85rem;font-size:.84rem;color:#f4e3c8}
.chat-panel__pending p{margin:0 0 .3rem}
.chat-panel__pending ul{margin:0 0 .5rem;padding-left:1.1rem}
.chat-panel__composer{display:flex;gap:.5rem;margin-top:.7rem}
.dimension-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.6rem;overflow-y:auto}
.dimension-card{border:1px solid rgba(120,160,180,.14);border-radius:12px;padding:.65rem .75rem;background:rgba(255,255,255,.02);transition:border-color .3s ease,box-shadow .3s ease}
.dimension-card--changed{border-color:rgba(52,230,197,.65);box-shadow:0 0 14px rgba(52,230,197,.18)}
.dimension-card header{display:flex;justify-content:space-between;align-items:center}
.dimension-card header small{color:#88a3b5;font-size:.75rem}
.dimension-card strong{display:block;margin:.3rem 0;color:#edf8fb;font-size:.84rem;line-height:1.45;min-height:2.4em}
.dimension-card__meter{height:4px;border-radius:2px;background:rgba(120,160,180,.18);overflow:hidden}
.dimension-card__meter i{display:block;height:100%;border-radius:2px;background:linear-gradient(90deg,#34e6c5,#5ad9ff);transition:width .5s ease}
.dimension-card__confidence{color:#7da5b6;font-size:.72rem}
@media(max-width:1080px){.chat-workbench{grid-template-columns:1fr}}
.profile-page{width:100%;padding:0 var(--plex-page-gutter-x) 2rem;overflow-y:auto}.profile-header,.identity-card,.report-card,.ai-summary,.calibration{border:1px solid rgba(52,230,197,.16);background:rgba(3,16,28,.86);border-radius:16px}.profile-header{display:flex;justify-content:space-between;gap:2rem;padding:1.5rem;margin-bottom:1rem}.eyebrow,.identity-title span,.report-card header>span,.ai-summary header span,.calibration span{color:#39e6c7;font-size:.72rem;letter-spacing:.12em}.profile-header h2,.identity-card h3,.report-card h3,.ai-summary h3,.calibration h3{margin:.35rem 0;color:#f5fbff}.profile-header p{color:#a9c2d0;margin:.3rem 0}.header-actions{display:flex;align-items:center;gap:1rem;flex-shrink:0}.identity-card{padding:1.2rem;margin-bottom:1rem}.identity-title{display:flex;align-items:baseline;gap:.8rem}.identity-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.75rem}.identity-grid>div{padding:.9rem;border-left:2px solid rgba(52,230,197,.45);background:rgba(52,230,197,.04)}small{display:block;color:#88a3b5;font-size:.78rem}.identity-grid strong{display:block;margin-top:.35rem;color:#edf8fb;line-height:1.4}.report-grid{display:grid;grid-template-columns:1.15fr 1fr;gap:1rem}.report-card{min-height:270px;padding:1.2rem}.report-card header p{color:#8da7b6;font-size:.85rem;margin:.2rem 0}.radar-card{grid-row:span 2}.mistake-list{padding:0;list-style:none}.mistake-list li{display:flex;gap:.7rem;padding:.65rem 0;border-bottom:1px solid rgba(142,177,192,.12)}.mistake-list i{display:grid;place-items:center;width:1.35rem;height:1.35rem;border-radius:50%;background:#5b3a46;color:#ff9da5;font-style:normal}.mistake-list span{display:block;color:#8da7b6;font-size:.82rem;margin-top:.15rem}.empty{color:#8da7b6}.state-card p{line-height:1.65;color:#d4e7ee}.adaptation{display:grid;gap:.45rem;margin-top:1rem;padding:.85rem;background:rgba(255,184,90,.08);border-left:2px solid #ffb85a}.adaptation.stable{background:rgba(52,230,197,.06);border-color:#34e6c5}.adaptation small{color:#a2bbc7}.ai-summary{margin-top:1rem;padding:1.35rem 1.35rem 1.6rem;min-height:320px}.ai-summary header{display:flex;justify-content:space-between;align-items:flex-start;gap:1rem}.ai-summary__actions{display:flex;align-items:center;gap:.55rem;flex-shrink:0}.ai-summary>p{color:#bed0da;line-height:1.65}.focus-items{margin-top:.85rem;padding:.9rem;background:rgba(46,255,241,.04);border:1px solid rgba(46,255,241,.12);border-radius:10px}.focus-items strong{color:#9ef3ea}.focus-items ul{margin:.55rem 0 0;padding:0;list-style:none}.focus-items li{margin:.45rem 0}.focus-items em{display:block;color:#f5fbff;font-style:normal;font-weight:650}.focus-items span{display:block;margin-top:.15rem;color:#9eb6c3;font-size:.84rem;line-height:1.5}.next-actions{margin-top:.9rem;padding:1rem 1rem 1.15rem;min-height:120px;background:rgba(255,255,255,.03);border-radius:10px}.next-actions ol{margin:.5rem 0 0;padding-left:1.2rem;color:#d7e8ee}.next-actions li{margin:.4rem 0;line-height:1.55}.calibration{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:1.2rem;margin-top:1rem}.calibration p{margin:0;color:#98b2bf}.diagnostic-modal{width:min(520px,92vw)}.calibration-modal{width:min(420px,92vw)}.calibration-modal :deep(.n-card__content){max-height:min(70vh,520px);overflow-y:auto}.modal-intro{color:#8da7b6;line-height:1.55;font-size:.84rem;margin:.1rem 0 .6rem}.calibration-hint{margin:.85rem 0 0;color:#8da7b6;font-size:.82rem;line-height:1.5}.diagnostic-progress{margin-bottom:.5rem}.diagnostic-body{max-height:min(58vh,520px);overflow-y:auto;padding-right:.45rem;margin-right:-.25rem}.diagnostic-body::-webkit-scrollbar{width:6px}.diagnostic-body::-webkit-scrollbar-thumb{background:rgba(52,230,197,.28);border-radius:3px}.question{padding:.7rem .8rem;margin-bottom:.55rem;border:1px solid rgba(52,230,197,.12);border-radius:10px;background:rgba(52,230,197,.03)}.question header{display:flex;align-items:center;justify-content:space-between;margin-bottom:.4rem}.question .q-index{color:#39e6c7;font-weight:700;font-size:.82rem;letter-spacing:.06em}.question .q-stem{color:#eef8fb;font-size:.9rem;line-height:1.5;margin:0 0 .5rem}.question .q-code{margin:0 0 .55rem;padding:.6rem .75rem;border-radius:8px;background:#020b15;border:1px solid rgba(52,230,197,.16);color:#9be8d6;font-family:'JetBrains Mono','Fira Code',Consolas,monospace;font-size:.8rem;line-height:1.55;white-space:pre;overflow-x:auto}.q-options{display:flex;flex-direction:column;gap:.1rem}.question :deep(.n-radio){display:flex;align-items:flex-start;margin:.2rem 0;padding:.35rem .5rem;border-radius:7px;font-size:.86rem;transition:background .15s ease}.question :deep(.n-radio:hover){background:rgba(52,230,197,.07)}.modal-footer{display:flex;align-items:center;justify-content:space-between}.calibration-tabs{display:flex;flex-wrap:wrap;gap:.45rem}.option-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.65rem;margin-top:1rem}.option-grid .n-button{height:auto;min-height:3rem;white-space:normal}@media(max-width:900px){.identity-grid{grid-template-columns:repeat(2,1fr)}.report-grid{grid-template-columns:1fr}.radar-card{grid-row:auto}.profile-header{align-items:flex-start;flex-direction:column}.header-actions{width:100%;justify-content:space-between}}@media(max-width:560px){.profile-page{padding:0 1rem 1.5rem}.identity-grid,.option-grid{grid-template-columns:1fr}.calibration{align-items:flex-start;flex-direction:column}}
</style>
