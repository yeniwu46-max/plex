<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NButton, NModal, NProgress, NRadio, NRadioGroup, NTag, useMessage } from 'naive-ui'
import DashboardShell from '../components/layout/DashboardShell.vue'
import StudentSectionTabs from '../components/student/StudentSectionTabs.vue'
import PlexRadarChart from '../components/charts/PlexRadarChart.vue'
import {
  fetchDynamicProfile, fetchProfileDiagnostic, fetchLearningAdaptations, submitProfileDiagnostic,
  updateDynamicProfile, type DynamicStudentProfile, type LearningAdaptation, type OnboardingDiagnosticQuestion,
  type ProfileDimensionKey,
} from '../api/personalizedProfile'
import { fetchStudentLearningReport, generateStudentPhaseReport, type LearningReportResult, type PhaseLearningReport } from '../api/learningReport'

const message = useMessage()
const profile = ref<DynamicStudentProfile | null>(null)
const report = ref<LearningReportResult | null>(null)
const aiReport = ref<PhaseLearningReport | null>(null)
const adaptations = ref<LearningAdaptation[]>([])
const questions = ref<OnboardingDiagnosticQuestion[]>([])
const answers = ref<Record<string, number>>({})
const diagnosticStatus = ref('pending')
const diagnosticVisible = ref(false)
const calibrationVisible = ref(false)
const selectedCalibration = ref<ProfileDimensionKey>('explanation_preference')
const saving = ref(false)

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

function questionKind(question: OnboardingDiagnosticQuestion) {
  if (question.question_type === 'code_reading') return '代码阅读'
  if (question.question_type === 'scenario') return '情境判断'
  if (question.knowledge_key === 'loop' || question.knowledge_key === 'range') return '代码阅读'
  if (question.knowledge_key === 'except') return '情境判断'
  return '概念选择'
}
async function load() {
  const [current, diagnostic, learning, active] = await Promise.all([
    fetchDynamicProfile(), fetchProfileDiagnostic(), fetchStudentLearningReport('7d'), fetchLearningAdaptations(),
  ])
  profile.value = current; questions.value = diagnostic.questions; diagnosticStatus.value = diagnostic.diagnostic.status
  report.value = learning; adaptations.value = active
  try { aiReport.value = (await generateStudentPhaseReport('7d')).report } catch { aiReport.value = null }
}
async function finishDiagnostic(skip = false) {
  saving.value = true
  try {
    const result = await submitProfileDiagnostic(answers.value, skip)
    profile.value = result.profile; diagnosticStatus.value = skip ? 'skipped' : 'completed'; diagnosticVisible.value = false
    await load(); message.success(skip ? '已跳过测验，系统将根据后续练习补全画像' : '诊断完成，AI 学习报告已刷新')
  } catch (error) { message.error(error instanceof Error ? error.message : '诊断提交失败') } finally { saving.value = false }
}
async function applyCalibration(value: string) {
  saving.value = true
  try {
    profile.value = await updateDynamicProfile({ [selectedCalibration.value]: value })
    calibrationVisible.value = false; await load(); message.success('画像已校准，报告已按你的选择更新')
  } catch (error) { message.error(error instanceof Error ? error.message : '画像校准失败') } finally { saving.value = false }
}
onMounted(() => { void load().catch((error) => message.error(error instanceof Error ? error.message : '学习画像加载失败')) })
</script>

<template>
  <DashboardShell active-nav="me" page-title="学习画像" page-subtitle="你的 AI 学习报告会随练习持续更新" search-placeholder="" hide-search>
    <template #toolbar><StudentSectionTabs area="me" /></template>
    <main class="profile-page">
      <section class="profile-header">
        <div><p class="eyebrow">AI LEARNING PROFILE · V{{ profile?.version ?? 1 }}</p><h2>今天，先让学习路径更懂你</h2><p>基于诊断、对话和练习行为生成。每一条结论都可以通过“校准画像”调整。</p></div>
        <div class="header-actions"><n-progress type="circle" :percentage="profile?.completion_rate ?? 0" color="#34e6c5" /><n-button type="primary" @click="diagnosticVisible = true">{{ diagnosticStatus === 'pending' ? '开始入门诊断' : '重新进行诊断' }}</n-button></div>
      </section>

      <section class="identity-card"><div class="identity-title"><span>AI 报告 A</span><h3>当前学习身份</h3></div><div class="identity-grid"><div><small>当前阶段</small><strong>{{ coreIdentity.stage }}</strong></div><div><small>当前任务</small><strong>{{ coreIdentity.mission }}</strong></div><div><small>当前学习模式</small><strong>{{ coreIdentity.mode }}</strong></div><div><small>今日推荐时长</small><strong>{{ coreIdentity.minutes }} 分钟</strong></div></div></section>

      <section class="report-grid">
        <article class="report-card radar-card"><header><span>AI 报告 B</span><h3>知识雷达图</h3><p>只关注五个会直接影响下一步学习的核心能力。</p></header><plex-radar-chart :dimensions="radarLabels" :values="radarValues" title="当前掌握度" color="#34e6c5" /></article>
        <article class="report-card"><header><span>AI 报告 C</span><h3>易错模式</h3><p>系统从近期作答中提取，优先安排针对性练习。</p></header><ul class="mistake-list"><li v-for="item in mistakes" :key="item.id"><i>!</i><div><strong>{{ item.knowledge_label }}</strong><span>{{ item.question_title || '高频错误，建议用微练习巩固' }}</span></div></li><li v-if="!mistakes.length" class="empty">完成几道练习后，系统会识别你的高频错误。</li></ul></article>
        <article class="report-card state-card"><header><span>AI 报告 D</span><h3>学习状态提醒</h3></header><p>{{ stateText }}</p><div v-if="adaptations.length" class="adaptation"><n-tag type="warning">已自动介入</n-tag><strong>{{ adaptations[0].action_plan.resources.join(' + ') }}</strong><small>{{ adaptations[0].action_plan.recovery_rule }}</small></div><div v-else class="adaptation stable"><n-tag type="success">节奏稳定</n-tag><strong>继续保持 25 分钟短时专注</strong><small>下一次练习会根据正确率自动调整。</small></div></article>
      </section>

      <section class="ai-summary"><header><div><span>AI 深度分析</span><h3>{{ aiReport?.headline || '正在生成你的阶段学习报告' }}</h3></div><n-tag size="small">{{ aiReport ? '已基于近 7 天数据' : '等待学习证据' }}</n-tag></header><p v-for="line in aiReport?.summary" :key="line">{{ line }}</p><div class="next-actions"><strong>下一步建议</strong><ol><li v-for="item in aiReport?.next_actions" :key="item">{{ item }}</li><li v-if="!aiReport?.next_actions">先完成一轮短练习，AI 会给出更具体的下一步。</li></ol></div></section>

      <section class="calibration"><div><span>不是填表，而是让 AI 更准确</span><h3>校准我的学习画像</h3><p>选择更接近你的真实偏好，系统会立刻重排资源和学习节奏。</p></div><n-button secondary type="primary" @click="calibrationVisible = true">优化画像</n-button></section>
    </main>

    <n-modal v-model:show="diagnosticVisible" preset="card" class="diagnostic-modal" title="Python 入门诊断">
      <template #header-extra><n-tag type="info">{{ Object.keys(answers).length }}/{{ questions.length }}</n-tag></template>
      <p class="modal-intro">这不是考试。它会帮助 AI 识别你的起点，并生成更合适的首周学习计划。</p>
      <article v-for="(question, index) in questions" :key="question.id" class="question"><header><span>Q{{ index + 1 }}</span><n-tag size="small">{{ questionKind(question) }}</n-tag></header><p>{{ question.stem }}</p><pre v-if="question.code_preview">{{ question.code_preview }}</pre><n-radio-group v-model:value="answers[question.id]"><n-radio v-for="(option, optionIndex) in question.options" :key="option" :value="optionIndex">{{ option }}</n-radio></n-radio-group></article>
      <template #footer><div class="modal-footer"><n-button text @click="finishDiagnostic(true)">暂时跳过</n-button><n-button type="primary" :loading="saving" :disabled="Object.keys(answers).length !== questions.length" @click="finishDiagnostic()">生成我的 AI 学习报告</n-button></div></template>
    </n-modal>

    <n-modal v-model:show="calibrationVisible" preset="card" class="calibration-modal" title="优化学习画像">
      <p class="modal-intro">选择你最认可的学习方式，AI 会以此校准资源推荐和讲解策略。</p><div class="calibration-tabs"><n-button v-for="key in (Object.keys(calibrationOptions) as ProfileDimensionKey[])" :key="key" size="small" :type="selectedCalibration === key ? 'primary' : 'default'" @click="selectedCalibration = key">{{ key === 'explanation_preference' ? '讲解方式' : key === 'learning_pace' ? '学习节奏' : key === 'learning_goal' ? '学习目标' : key === 'cognitive_state' ? '学习状态' : key }}</n-button></div><div class="option-grid"><n-button v-for="option in calibrationOptions[selectedCalibration]" :key="option.value" secondary @click="applyCalibration(option.value)">{{ option.label }}</n-button></div>
    </n-modal>
  </DashboardShell>
</template>

<style scoped>
.profile-page{width:100%;padding:0 var(--plex-page-gutter-x) 2rem;overflow-y:auto}.profile-header,.identity-card,.report-card,.ai-summary,.calibration{border:1px solid rgba(52,230,197,.16);background:rgba(3,16,28,.86);border-radius:16px}.profile-header{display:flex;justify-content:space-between;gap:2rem;padding:1.5rem;margin-bottom:1rem}.eyebrow,.identity-title span,.report-card header>span,.ai-summary header span,.calibration span{color:#39e6c7;font-size:.72rem;letter-spacing:.12em}.profile-header h2,.identity-card h3,.report-card h3,.ai-summary h3,.calibration h3{margin:.35rem 0;color:#f5fbff}.profile-header p{color:#a9c2d0;margin:.3rem 0}.header-actions{display:flex;align-items:center;gap:1rem;flex-shrink:0}.identity-card{padding:1.2rem;margin-bottom:1rem}.identity-title{display:flex;align-items:baseline;gap:.8rem}.identity-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.75rem}.identity-grid>div{padding:.9rem;border-left:2px solid rgba(52,230,197,.45);background:rgba(52,230,197,.04)}small{display:block;color:#88a3b5;font-size:.78rem}.identity-grid strong{display:block;margin-top:.35rem;color:#edf8fb;line-height:1.4}.report-grid{display:grid;grid-template-columns:1.15fr 1fr;gap:1rem}.report-card{min-height:270px;padding:1.2rem}.report-card header p{color:#8da7b6;font-size:.85rem;margin:.2rem 0}.radar-card{grid-row:span 2}.mistake-list{padding:0;list-style:none}.mistake-list li{display:flex;gap:.7rem;padding:.65rem 0;border-bottom:1px solid rgba(142,177,192,.12)}.mistake-list i{display:grid;place-items:center;width:1.35rem;height:1.35rem;border-radius:50%;background:#5b3a46;color:#ff9da5;font-style:normal}.mistake-list span{display:block;color:#8da7b6;font-size:.82rem;margin-top:.15rem}.empty{color:#8da7b6}.state-card p{line-height:1.65;color:#d4e7ee}.adaptation{display:grid;gap:.45rem;margin-top:1rem;padding:.85rem;background:rgba(255,184,90,.08);border-left:2px solid #ffb85a}.adaptation.stable{background:rgba(52,230,197,.06);border-color:#34e6c5}.adaptation small{color:#a2bbc7}.ai-summary{margin-top:1rem;padding:1.2rem}.ai-summary header{display:flex;justify-content:space-between;align-items:flex-start}.ai-summary>p{color:#bed0da;line-height:1.65}.next-actions{margin-top:.8rem;padding:.9rem;background:rgba(255,255,255,.03)}.next-actions ol{margin:.5rem 0 0;padding-left:1.2rem;color:#d7e8ee}.next-actions li{margin:.35rem 0}.calibration{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:1.2rem;margin-top:1rem}.calibration p{margin:0;color:#98b2bf}.diagnostic-modal,.calibration-modal{width:min(760px,94vw)}.modal-intro{color:#8da7b6;line-height:1.6}.question{padding:1rem 0;border-bottom:1px solid rgba(142,177,192,.14)}.question header{display:flex;justify-content:space-between}.question header span{color:#39e6c7;font-weight:700}.question p{color:#eef8fb}.question :deep(.n-radio){display:flex;margin:.45rem 0}.modal-footer{display:flex;align-items:center;justify-content:space-between}.calibration-tabs{display:flex;flex-wrap:wrap;gap:.45rem}.option-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.65rem;margin-top:1rem}.option-grid .n-button{height:auto;min-height:3rem;white-space:normal}@media(max-width:900px){.identity-grid{grid-template-columns:repeat(2,1fr)}.report-grid{grid-template-columns:1fr}.radar-card{grid-row:auto}.profile-header{align-items:flex-start;flex-direction:column}.header-actions{width:100%;justify-content:space-between}}@media(max-width:560px){.profile-page{padding:0 1rem 1.5rem}.identity-grid,.option-grid{grid-template-columns:1fr}.calibration{align-items:flex-start;flex-direction:column}}
</style>
