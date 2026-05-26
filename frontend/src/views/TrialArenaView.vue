<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NButton, NIcon, NSelect, NSlider, useMessage, type SelectOption } from 'naive-ui'
import {
  AnalyticsOutline,
  CubeOutline,
  GiftOutline,
  PeopleOutline,
  PlanetOutline,
  RadioButtonOnOutline,
  ShieldCheckmarkOutline,
  SparklesOutline,
  StarOutline,
  TimeOutline,
} from '@vicons/ionicons5'
import TeacherDashboardShell from '../components/layout/TeacherDashboardShell.vue'
import {
  createTeacherTrial,
  fetchTeacherTrials,
  publishTeacherTrial,
  updateTeacherTrial,
  type TeacherTrial,
  type TeacherTrialSummary,
} from '../api/teacherTrials'
import { useTeacherOverviewInjected } from '../composables/useTeacherOverview'

type TrialStatus = 'running' | 'soon' | 'ended' | 'draft'
type TrialTone = 'orange' | 'blue' | 'purple' | 'amber'
type TemplateTone = 'orange' | 'teal' | 'purple' | 'red' | 'gold'

interface TrialCard {
  id: number
  title: string
  status: TrialStatus
  statusText: string
  effectiveStatus: string
  tone: TrialTone
  scene: string
  tags: string[]
  students: string
  timeText: string
  progress: number
  canPublish: boolean
  canEnd: boolean
}

interface TemplateItem {
  id: string
  title: string
  desc: string
  tone: TemplateTone
  icon: typeof CubeOutline
}

const message = useMessage()
const { selectedClassId, hasSelectedClass } = useTeacherOverviewInjected()

const activeTab = ref<'manage' | 'templates'>('manage')
const trialType = ref('solo')
const knowledge = ref<string | null>(null)
const duration = ref('60')
const difficulty = ref(78)
const loading = ref(false)
const creating = ref(false)
const actingTrialId = ref<number | null>(null)
const publishMode = ref<'now' | 'draft' | 'scheduled'>('now')
const scheduleDelay = ref('30')
const errorMessage = ref('')
const summary = ref<TeacherTrialSummary | null>(null)
const trials = ref<TrialCard[]>([])

const typeLabels: Record<string, string> = {
  solo: '个人挑战',
  team: '小组协作',
  timed: '限时竞赛',
  abyss: '深渊试炼',
}

const knowledgeLabels: Record<string, string> = {
  dp: '动态规划',
  graph: '图论基础',
  ds: '数据结构',
  frontend: '前端工程化',
}

const trialTypeOptions: SelectOption[] = [
  { label: '个人挑战', value: 'solo' },
  { label: '小组协作', value: 'team' },
  { label: '限时竞赛', value: 'timed' },
  { label: '深渊试炼', value: 'abyss' },
]

const knowledgeOptions: SelectOption[] = [
  { label: '动态规划', value: 'dp' },
  { label: '图论基础', value: 'graph' },
  { label: '数据结构', value: 'ds' },
  { label: '前端工程化', value: 'frontend' },
]

const durationOptions: SelectOption[] = [
  { label: '30 分钟', value: '30' },
  { label: '60 分钟', value: '60' },
  { label: '90 分钟', value: '90' },
  { label: '120 分钟', value: '120' },
]

const publishModeOptions: SelectOption[] = [
  { label: '立即发布', value: 'now' },
  { label: '保存草稿', value: 'draft' },
  { label: '定时发布', value: 'scheduled' },
]

const scheduleDelayOptions: SelectOption[] = [
  { label: '30 分钟后', value: '30' },
  { label: '1 小时后', value: '60' },
  { label: '明天此时', value: '1440' },
]

const templates: TemplateItem[] = [
  { id: 'solo', title: '个人挑战', desc: '单人提升能力', tone: 'orange', icon: CubeOutline },
  { id: 'team', title: '小组协作', desc: '团队合作任务', tone: 'teal', icon: PeopleOutline },
  { id: 'timed', title: '限时竞赛', desc: '时间限定挑战', tone: 'purple', icon: SparklesOutline },
  { id: 'abyss', title: '深渊试炼', desc: '高难度实践', tone: 'red', icon: PlanetOutline },
  { id: 'custom', title: '自定义试炼', desc: '自由创建任务', tone: 'gold', icon: GiftOutline },
]

const stats = computed(() => {
  const s = summary.value
  return [
    { label: '进行中试炼', value: s?.running_count ?? 0, icon: ShieldCheckmarkOutline, tone: 'orange' },
    { label: '即将开始', value: s?.scheduled_count ?? 0, icon: TimeOutline, tone: 'blue' },
    { label: '草稿', value: s?.draft_count ?? 0, icon: CubeOutline, tone: 'amber' },
    { label: '参与 Explorer', value: s?.participant_count ?? 0, icon: PeopleOutline, tone: 'teal' },
    { label: '平均完成率', value: `${s?.avg_completion_rate ?? 0}%`, icon: AnalyticsOutline, tone: 'purple' },
    {
      label: '班级人数',
      value: s?.class_student_count ?? 0,
      icon: RadioButtonOnOutline,
      tone: 'red',
    },
    { label: '试炼模板', value: s?.template_count ?? templates.length, icon: StarOutline, tone: 'gold' },
  ]
})

function mapTrial(item: TeacherTrial): TrialCard {
  const effective = item.effective_status ?? item.status
  const status: TrialStatus =
    effective === 'ended'
      ? 'ended'
      : effective === 'draft'
        ? 'draft'
        : effective === 'scheduled'
          ? 'soon'
          : 'running'
  const statusText =
    effective === 'ended'
      ? '已结束'
      : effective === 'draft'
        ? '草稿'
        : effective === 'scheduled'
          ? '即将开始'
          : '进行中'
  const toneMap: Record<string, TrialTone> = {
    solo: 'orange',
    team: 'blue',
    timed: 'purple',
    abyss: 'amber',
  }
  const sceneMap: Record<string, string> = {
    dp: 'canyon',
    graph: 'crystal',
    ds: 'nebula',
    frontend: 'planet',
  }
  const typeLabel = typeLabels[item.trial_type] ?? item.trial_type
  const knowLabel = item.knowledge_key ? knowledgeLabels[item.knowledge_key] ?? item.knowledge_key : ''
  return {
    id: item.id,
    title: item.title,
    status,
    statusText,
    tone: toneMap[item.trial_type] ?? 'orange',
    scene: sceneMap[item.knowledge_key ?? ''] ?? 'canyon',
    tags: [typeLabel, knowLabel].filter(Boolean),
    students: `${item.completed_count ?? 0}/${item.participant_count ?? 0}`,
    timeText: `约 ${item.duration_minutes} 分钟 · 奖励 ${item.reward_points} XP`,
    progress: item.progress ?? item.completion_rate ?? 0,
    effectiveStatus: effective,
    canPublish: effective === 'draft' || effective === 'scheduled',
    canEnd: effective === 'running' || effective === 'scheduled',
  }
}

async function loadTrials() {
  if (!selectedClassId.value) {
    trials.value = []
    summary.value = null
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const data = await fetchTeacherTrials(selectedClassId.value)
    trials.value = data.trials.map(mapTrial)
    summary.value = data.summary
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '试炼数据加载失败'
    trials.value = []
  } finally {
    loading.value = false
  }
}

async function createTrial() {
  if (!selectedClassId.value) {
    message.warning('请先选择班级')
    return
  }
  if (!knowledge.value) {
    message.warning('请选择知识星域')
    return
  }
  const typeLabel = trialTypeOptions.find((item) => item.value === trialType.value)?.label ?? '个人挑战'
  const knowLabel = knowledgeOptions.find((item) => item.value === knowledge.value)?.label ?? ''
  const title = `${knowLabel}${typeLabel}`.replace(/^$/, '未命名试炼')

  creating.value = true
  try {
    await createTeacherTrial({
      class_id: selectedClassId.value,
      title,
      trial_type: trialType.value,
      knowledge_key: knowledge.value,
      difficulty: difficulty.value,
      duration_minutes: Number(duration.value),
      reward_points: Math.max(15, Math.round(difficulty.value / 2)),
      publish_mode: publishMode.value,
      start_delay_minutes: publishMode.value === 'scheduled' ? Number(scheduleDelay.value) : undefined,
    })
    const modeLabel =
      publishMode.value === 'draft' ? '已保存草稿' : publishMode.value === 'scheduled' ? '已创建定时试炼' : '已发布试炼'
    message.success(`${modeLabel}「${title}」`)
    await loadTrials()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '创建失败')
  } finally {
    creating.value = false
  }
}

async function onPublishTrial(trialId: number) {
  actingTrialId.value = trialId
  try {
    await publishTeacherTrial(trialId)
    message.success('试炼已发布')
    await loadTrials()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '发布失败')
  } finally {
    actingTrialId.value = null
  }
}

async function onEndTrial(trialId: number) {
  actingTrialId.value = trialId
  try {
    await updateTeacherTrial(trialId, { status: 'ended' })
    message.success('试炼已结束')
    await loadTrials()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '结束失败')
  } finally {
    actingTrialId.value = null
  }
}

function switchTemplate(template: TemplateItem) {
  trialType.value = template.id === 'custom' ? 'solo' : template.id
  message.info(`已选用「${template.title}」模板`)
}

watch(selectedClassId, () => {
  void loadTrials()
}, { immediate: true })
</script>

<template>
  <TeacherDashboardShell
    active-nav="trial"
    page-title="试炼中枢"
    page-subtitle="设计与调度试炼任务，激发探索者的潜能"
    search-placeholder="搜索试炼任务或模板"
    hide-search
    toolbar-label="试炼中枢筛选与状态"
  >
    <section class="trial-command teacher-page" aria-label="试炼中枢">
      <main class="command-main">
        <section class="command-panel mission-panel">
          <header class="tabbar">
            <button type="button" :class="{ active: activeTab === 'manage' }" @click="activeTab = 'manage'">试炼管理</button>
            <button type="button" :class="{ active: activeTab === 'templates' }" @click="activeTab = 'templates'">我的模板</button>
          </header>

          <div class="panel-section">
            <div class="section-head">
              <h2>进行中的试炼</h2>
              <button type="button" @click="loadTrials()">刷新 <span>›</span></button>
            </div>

            <div v-if="!hasSelectedClass" class="teacher-state-panel trial-command__state">请先在顶部选择班级。</div>
            <div v-else-if="loading" class="teacher-state-panel trial-command__state">正在加载试炼列表…</div>
            <div v-else-if="errorMessage" class="teacher-state-panel teacher-state-panel--error trial-command__state">
              <span>{{ errorMessage }}</span>
              <n-button secondary size="small" @click="loadTrials()">重试</n-button>
            </div>
            <div v-else-if="!trials.length" class="teacher-state-panel trial-command__state">暂无试炼，使用右侧表单快速创建。</div>

            <div v-else class="trial-grid">
              <article v-for="trial in trials" :key="trial.id" class="trial-card" :class="[`trial-card--${trial.tone}`, `trial-card--${trial.scene}`]">
                <div class="trial-art" aria-hidden="true">
                  <span class="trial-art__sun" />
                  <span class="trial-art__scape" />
                </div>
                <div class="trial-card__meta">
                  <span class="status-pill" :class="`status-pill--${trial.status}`">{{ trial.statusText }}</span>
                  <span class="student-count"><n-icon :component="PeopleOutline" /> {{ trial.students }}</span>
                </div>
                <div class="trial-card__body">
                  <h3>{{ trial.title }}</h3>
                  <div class="tag-row">
                    <span v-for="tag in trial.tags" :key="tag">{{ tag }}</span>
                  </div>
                  <p><n-icon :component="TimeOutline" /> {{ trial.timeText }}</p>
                  <div class="progress-line" :class="{ 'progress-line--muted': trial.status !== 'running' }">
                    <i :style="{ width: `${trial.progress}%` }" />
                  </div>
                  <strong v-if="trial.status === 'running'">{{ trial.progress }}%</strong>
                  <span v-if="trial.status === 'ended'" class="complete-mark">✓</span>
                  <div v-if="trial.canPublish || trial.canEnd" class="trial-card__actions">
                    <n-button
                      v-if="trial.canPublish"
                      size="tiny"
                      secondary
                      :loading="actingTrialId === trial.id"
                      @click.stop="onPublishTrial(trial.id)"
                    >
                      发布
                    </n-button>
                    <n-button
                      v-if="trial.canEnd"
                      size="tiny"
                      quaternary
                      :loading="actingTrialId === trial.id"
                      @click.stop="onEndTrial(trial.id)"
                    >
                      结束
                    </n-button>
                  </div>
                </div>
              </article>
            </div>
          </div>

          <div class="panel-section template-section">
            <div class="section-head">
              <h2>试炼模板库</h2>
              <button type="button">进入模板库 <span>›</span></button>
            </div>
            <div class="template-row">
              <button
                v-for="template in templates"
                :key="template.id"
                type="button"
                class="template-card"
                :class="`template-card--${template.tone}`"
                @click="switchTemplate(template)"
              >
                <span><n-icon :component="template.icon" /></span>
                <strong>{{ template.title }}</strong>
                <small>{{ template.desc }}</small>
              </button>
            </div>
          </div>
        </section>

        <section class="command-panel data-panel">
          <h2>试炼数据概览</h2>
          <div class="stats-row">
            <article v-for="item in stats" :key="item.label" :class="`stat-card stat-card--${item.tone}`">
              <span><n-icon :component="item.icon" /></span>
              <strong>{{ item.value }}</strong>
              <small>{{ item.label }}</small>
            </article>
          </div>
        </section>
      </main>

      <aside class="create-panel">
        <h2>快速创建试炼</h2>
        <div class="create-orbit" aria-hidden="true">
          <span v-for="ring in 6" :key="ring" :style="{ '--ring': ring }" />
          <i />
          <b>+</b>
        </div>

        <label class="field">
          <span>选择试炼类型</span>
          <n-select v-model:value="trialType" :options="trialTypeOptions" class="field-select" />
        </label>

        <label class="field">
          <span>选择知识星域</span>
          <n-select v-model:value="knowledge" :options="knowledgeOptions" placeholder="请选择知识星域" class="field-select" />
        </label>

        <div class="field">
          <span>难度设置</span>
          <n-slider v-model:value="difficulty" :min="0" :max="100" :step="1" class="difficulty-slider" />
          <div class="difficulty-labels">
            <small>简单</small>
            <small>中等</small>
            <small>困难</small>
          </div>
        </div>

        <label class="field">
          <span>预计时长</span>
          <n-select v-model:value="duration" :options="durationOptions" class="field-select" />
        </label>

        <label class="field">
          <span>发布方式</span>
          <n-select v-model:value="publishMode" :options="publishModeOptions" class="field-select" />
        </label>

        <label v-if="publishMode === 'scheduled'" class="field">
          <span>开始时间</span>
          <n-select v-model:value="scheduleDelay" :options="scheduleDelayOptions" class="field-select" />
        </label>

        <n-button type="primary" size="large" block class="create-btn" :loading="creating" @click="createTrial">
          {{ publishMode === 'draft' ? '保存草稿' : publishMode === 'scheduled' ? '创建定时试炼' : '创建并发布' }}
        </n-button>
      </aside>
    </section>
  </TeacherDashboardShell>
</template>

<style scoped>
.trial-toolbar {
  position: relative;
  z-index: 4;
  display: flex;
  width: fit-content;
  align-items: center;
  gap: 1.25rem;
  margin: -3.95rem var(--plex-page-gutter-x) 1.8rem auto;
  color: rgba(255, 247, 237, 0.84);
}

:deep(.plex-topbar__heading h1)::after {
  content: 'TRIAL COMMAND';
  color: rgba(221, 230, 239, 0.62);
  font-size: 1rem;
  font-weight: 500;
}

:deep(.plex-topbar__heading h1 span) {
  background: var(--orange, #fb923c);
  box-shadow: 0 0 12px rgba(251, 146, 60, 0.85);
}

:deep(.nav-item--active) {
  color: #fb923c !important;
  background: rgba(251, 146, 60, 0.14) !important;
  box-shadow: inset 0 0 24px rgba(251, 146, 60, 0.12), 0 0 22px rgba(251, 146, 60, 0.12) !important;
}

:deep(.nav-item--active *) {
  color: #fb923c !important;
}

:deep(.nav-item--active .nav-item__accent) {
  background: linear-gradient(180deg, #fb923c, #f59e0b);
  box-shadow: 0 0 12px rgba(251, 146, 60, 0.65);
}

.class-select {
  width: 210px;
}

.class-select :deep(.n-base-selection),
.field-select :deep(.n-base-selection) {
  --n-color: rgba(5, 18, 30, 0.72) !important;
  --n-color-active: rgba(5, 18, 30, 0.92) !important;
  --n-border: 1px solid rgba(130, 212, 255, 0.13) !important;
  --n-border-active: 1px solid rgba(251, 146, 60, 0.46) !important;
  --n-border-hover: 1px solid rgba(251, 146, 60, 0.34) !important;
  --n-text-color: #fff7ed !important;
  --n-placeholder-color: rgba(221, 230, 239, 0.5) !important;
}

.keeper-chip {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 220px;
  padding-left: 1.35rem;
  border-left: 1px solid rgba(219, 235, 249, 0.1);
}

.keeper-avatar {
  display: grid;
  width: 50px;
  height: 50px;
  place-items: center;
  border-radius: 50%;
  background:
    radial-gradient(circle at 50% 30%, rgba(251, 146, 60, 0.22), transparent 54%),
    #061827;
  border: 1px solid rgba(255, 237, 213, 0.24);
  box-shadow: 0 0 0 5px rgba(251, 146, 60, 0.06);
}

.keeper-avatar span {
  width: 29px;
  height: 21px;
  border-radius: 9px;
  background: #e9f3fb;
  box-shadow: inset 0 -8px #111926;
}

.keeper-chip strong {
  display: block;
  color: rgba(255, 247, 237, 0.92);
  font-size: 0.9rem;
}

.keeper-chip small {
  color: #34d399;
}

.trial-command {
  --orange: #fb923c;
  --gold: #fbbf24;
  --teal: #2efff1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  grid-template-rows: minmax(480px, 1fr);
  gap: var(--teacher-quad-gap, 1.1rem);
  align-items: stretch;
  align-content: start;
}

.trial-command__state {
  min-height: 180px;
  margin-bottom: 1rem;
}

.command-main {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: var(--teacher-quad-gap, 1.1rem);
  min-width: 0;
  min-height: 0;
  height: 100%;
}

.mission-panel {
  display: flex;
  min-height: 520px;
  flex-direction: column;
}

.create-panel {
  display: flex;
  height: 100%;
  flex-direction: column;
}

.command-panel,
.create-panel {
  position: relative;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 18px;
  background:
    radial-gradient(circle at 45% 0%, rgba(251, 146, 60, 0.08), transparent 34%),
    linear-gradient(145deg, rgba(5, 18, 30, 0.91), rgba(3, 12, 20, 0.78));
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.04), 0 22px 70px rgba(0, 0, 0, 0.2);
}

.tabbar {
  display: flex;
  gap: 2.5rem;
  height: 58px;
  align-items: end;
  padding: 0 1.45rem;
  border-bottom: 1px solid rgba(219, 235, 249, 0.08);
}

.tabbar button,
.section-head button {
  border: 0;
  background: transparent;
  color: rgba(221, 230, 239, 0.6);
  cursor: pointer;
  font: inherit;
}

.tabbar button {
  position: relative;
  padding: 0 0 1rem;
  font-weight: 700;
}

.tabbar button.active {
  color: #fff7ed;
}

.tabbar button.active::after {
  position: absolute;
  left: 50%;
  bottom: 0;
  width: 58px;
  height: 3px;
  transform: translateX(-50%);
  border-radius: 999px 999px 0 0;
  background: var(--orange);
  box-shadow: 0 0 18px rgba(251, 146, 60, 0.8);
  content: '';
}

.panel-section {
  padding: 1.35rem 1.35rem 1.25rem;
}

.template-section {
  border-top: 1px solid rgba(219, 235, 249, 0.08);
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.05rem;
}

.section-head h2,
.data-panel h2,
.create-panel h2 {
  margin: 0;
  color: #fff7ed;
  font-size: 1.18rem;
  font-weight: 740;
}

.section-head button {
  color: rgba(221, 230, 239, 0.62);
}

.trial-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1rem;
}

.trial-card {
  position: relative;
  min-height: 320px;
  overflow: hidden;
  border: 1px solid rgba(219, 235, 249, 0.1);
  border-radius: 13px;
  background: rgba(3, 12, 20, 0.9);
}

.trial-art {
  position: absolute;
  inset: 0 0 auto;
  height: 174px;
  overflow: hidden;
  background:
    radial-gradient(circle at 62% 40%, rgba(255, 237, 213, 0.68), transparent 12%),
    linear-gradient(155deg, rgba(251, 146, 60, 0.45), rgba(60, 16, 8, 0.2) 46%, rgba(6, 18, 30, 0.86)),
    #08131f;
}

.trial-card--crystal .trial-art {
  background:
    radial-gradient(diamond at 50% 34%, rgba(125, 211, 252, 0.9), transparent 12%),
    linear-gradient(155deg, rgba(14, 165, 233, 0.42), rgba(4, 32, 62, 0.6) 50%, rgba(6, 18, 30, 0.9));
}

.trial-card--nebula .trial-art {
  background:
    radial-gradient(ellipse at 54% 44%, rgba(255, 237, 213, 0.85), rgba(168, 85, 247, 0.28) 18%, transparent 34%),
    linear-gradient(155deg, rgba(88, 28, 135, 0.52), rgba(10, 15, 35, 0.88));
}

.trial-card--planet .trial-art {
  background:
    radial-gradient(circle at 70% 58%, rgba(251, 146, 60, 0.86), transparent 14%),
    radial-gradient(circle at 18% 54%, rgba(148, 163, 184, 0.24), transparent 13%),
    linear-gradient(155deg, rgba(92, 43, 11, 0.56), rgba(6, 18, 30, 0.92));
}

.trial-art::after {
  position: absolute;
  inset: auto 0 0;
  height: 58px;
  background: linear-gradient(180deg, transparent, rgba(3, 12, 20, 0.96));
  content: '';
}

.trial-art__scape {
  position: absolute;
  left: -10%;
  right: -10%;
  bottom: 0;
  height: 70px;
  background:
    linear-gradient(142deg, transparent 18%, rgba(2, 6, 23, 0.82) 19% 38%, transparent 39%),
    linear-gradient(38deg, transparent 16%, rgba(2, 6, 23, 0.76) 17% 36%, transparent 37%),
    linear-gradient(180deg, transparent, rgba(2, 6, 23, 0.88));
}

.trial-card__meta {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem;
}

.status-pill,
.student-count,
.tag-row span {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  border-radius: 999px;
  background: rgba(2, 8, 14, 0.62);
  color: rgba(255, 247, 237, 0.86);
  font-size: 0.75rem;
}

.status-pill {
  padding: 0.28rem 0.55rem;
  border: 1px solid rgba(251, 146, 60, 0.45);
  color: var(--orange);
}

.status-pill--draft {
  color: #fcd34d;
  border-color: rgba(252, 211, 77, 0.45);
  background: rgba(252, 211, 77, 0.12);
}

.trial-card__actions {
  display: flex;
  gap: 0.45rem;
  margin-top: 0.65rem;
}

.status-pill--soon {
  border-color: rgba(168, 85, 247, 0.48);
  color: #c084fc;
}

.status-pill--ended {
  border-color: rgba(148, 163, 184, 0.22);
  color: rgba(221, 230, 239, 0.68);
}

.student-count {
  padding: 0.24rem 0.48rem;
}

.trial-card__body {
  position: absolute;
  inset: 174px 0 0;
  padding: 1.05rem 1rem 1rem;
}

.trial-card__body h3 {
  margin: 0 0 0.55rem;
  color: #fff7ed;
  font-size: 1.02rem;
  font-weight: 740;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.tag-row span {
  padding: 0.24rem 0.52rem;
  color: rgba(221, 230, 239, 0.7);
}

.trial-card__body p {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin: 1rem 0 1.35rem;
  color: rgba(221, 230, 239, 0.58);
  font-size: 0.8rem;
}

.progress-line {
  position: relative;
  width: calc(100% - 2.8rem);
  height: 4px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
}

.progress-line i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--orange), var(--gold));
  box-shadow: 0 0 12px rgba(251, 146, 60, 0.6);
}

.trial-card--blue .progress-line i {
  background: linear-gradient(90deg, #38bdf8, #22d3ee);
  box-shadow: 0 0 12px rgba(56, 189, 248, 0.52);
}

.progress-line--muted i {
  opacity: 0.35;
}

.trial-card__body > strong {
  position: absolute;
  right: 1rem;
  bottom: 1.02rem;
  color: var(--orange);
  font-size: 0.8rem;
}

.complete-mark {
  position: absolute;
  right: 1rem;
  bottom: 1rem;
  display: grid;
  width: 26px;
  height: 26px;
  place-items: center;
  border: 1px solid rgba(221, 230, 239, 0.42);
  border-radius: 50%;
  color: rgba(221, 230, 239, 0.84);
}

.template-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.65rem;
}

.template-card {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  grid-template-rows: auto auto;
  column-gap: 0.8rem;
  align-items: center;
  min-height: 78px;
  padding: 0.75rem;
  border: 1px solid rgba(219, 235, 249, 0.09);
  border-radius: 10px;
  background: rgba(5, 18, 30, 0.66);
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.template-card span {
  grid-row: 1 / span 2;
  display: grid;
  width: 50px;
  height: 50px;
  place-items: center;
  border-radius: 50%;
  background: rgba(251, 146, 60, 0.12);
  border: 1px solid rgba(251, 146, 60, 0.44);
  color: var(--orange);
  font-size: 1.45rem;
  box-shadow: 0 0 18px rgba(251, 146, 60, 0.2);
}

.template-card--teal span {
  color: #34d399;
  border-color: rgba(52, 211, 153, 0.42);
  background: rgba(52, 211, 153, 0.12);
}

.template-card--purple span {
  color: #c084fc;
  border-color: rgba(192, 132, 252, 0.42);
  background: rgba(192, 132, 252, 0.12);
}

.template-card--red span {
  color: #f87171;
  border-color: rgba(248, 113, 113, 0.42);
  background: rgba(248, 113, 113, 0.12);
}

.template-card--gold span {
  color: var(--gold);
  border-color: rgba(251, 191, 36, 0.42);
  background: rgba(251, 191, 36, 0.12);
}

.template-card strong {
  color: #fff7ed;
  font-size: 0.92rem;
}

.template-card small {
  color: rgba(221, 230, 239, 0.58);
}

.data-panel {
  padding: 1.45rem;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 1.3rem;
  margin-top: 1.15rem;
}

.stat-card {
  display: grid;
  grid-template-columns: 54px auto;
  grid-template-rows: auto auto;
  column-gap: 1rem;
  align-items: center;
  min-width: 0;
  border-right: 1px solid rgba(219, 235, 249, 0.08);
}

.stat-card:last-child {
  border-right: 0;
}

.stat-card > span {
  grid-row: 1 / span 2;
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border-radius: 50%;
  color: var(--orange);
  background: rgba(251, 146, 60, 0.12);
  border: 1px solid rgba(251, 146, 60, 0.3);
  font-size: 1.45rem;
}

.stat-card--teal > span {
  color: #34d399;
  background: rgba(52, 211, 153, 0.12);
  border-color: rgba(52, 211, 153, 0.3);
}

.stat-card--purple > span {
  color: #c084fc;
  background: rgba(192, 132, 252, 0.12);
  border-color: rgba(192, 132, 252, 0.3);
}

.stat-card--red > span {
  color: #f87171;
  background: rgba(248, 113, 113, 0.12);
  border-color: rgba(248, 113, 113, 0.3);
}

.stat-card--gold > span {
  color: var(--gold);
  background: rgba(251, 191, 36, 0.12);
  border-color: rgba(251, 191, 36, 0.3);
}

.stat-card strong {
  color: #ffffff;
  font-size: 1.55rem;
  font-weight: 650;
}

.stat-card small {
  color: rgba(221, 230, 239, 0.62);
}

.create-panel {
  align-self: stretch;
  padding: 1.55rem 1.45rem;
}

.create-orbit {
  position: relative;
  height: 220px;
  margin: 0.8rem 0 1.2rem;
}

.create-orbit span {
  position: absolute;
  left: 50%;
  top: 50%;
  width: calc(var(--ring) * 33px);
  height: calc(var(--ring) * 33px);
  transform: translate(-50%, -50%);
  border: 1px solid rgba(251, 146, 60, 0.16);
  border-radius: 50%;
}

.create-orbit i {
  position: absolute;
  inset: 50% auto auto 50%;
  width: 96px;
  height: 96px;
  transform: translate(-50%, -50%) rotate(45deg);
  border: 1px solid rgba(251, 146, 60, 0.55);
  background:
    radial-gradient(circle at center, rgba(251, 146, 60, 0.54), transparent 56%),
    rgba(251, 146, 60, 0.08);
  box-shadow: 0 0 42px rgba(251, 146, 60, 0.34);
}

.create-orbit b {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  color: #fff7ed;
  font-size: 3rem;
  font-weight: 260;
}

.field {
  display: grid;
  gap: 0.7rem;
  margin-top: 1.15rem;
}

.field > span {
  color: rgba(255, 237, 213, 0.72);
  font-size: 0.92rem;
}

.difficulty-slider :deep(.n-slider) {
  --n-fill-color: var(--orange) !important;
  --n-fill-color-hover: var(--orange) !important;
}

.difficulty-slider :deep(.n-slider-rail__fill) {
  background: var(--orange) !important;
}

.difficulty-slider :deep(.n-slider-handle) {
  border-color: var(--orange) !important;
}

.difficulty-slider :deep(.n-slider-handle) {
  --n-handle-color: var(--orange) !important;
  --n-handle-color-hover: var(--orange) !important;
}

.difficulty-labels {
  display: flex;
  justify-content: space-between;
  color: rgba(221, 230, 239, 0.5);
}

.create-btn {
  margin-top: 1.55rem;
  --n-color: #ea580c !important;
  --n-color-hover: #f97316 !important;
  --n-color-pressed: #c2410c !important;
  --n-border: 1px solid rgba(251, 146, 60, 0.58) !important;
  --n-border-hover: 1px solid rgba(251, 146, 60, 0.78) !important;
  font-weight: 800 !important;
}

@media (max-width: 1280px) {
  .trial-toolbar {
    margin: 1rem var(--plex-page-gutter-x);
  }

  .trial-command {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
  }

  .mission-panel {
    min-height: 0;
  }

  .create-panel {
    display: none;
  }
}

@media (max-width: 980px) {
  .trial-grid,
  .template-row,
  .stats-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .trial-toolbar {
    flex-direction: column;
    align-items: stretch;
    margin-inline: 1rem;
  }

  .keeper-chip {
    min-width: 0;
    padding-left: 0;
    border-left: 0;
  }

  .class-select {
    width: 100%;
  }

  .trial-command {
    grid-template-columns: 1fr;
    padding-inline: 1rem;
  }

  .trial-grid,
  .template-row,
  .stats-row {
    grid-template-columns: 1fr;
  }
}
</style>
