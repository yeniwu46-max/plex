<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NButton,
  NCheckbox,
  NCheckboxGroup,
  NDatePicker,
  NIcon,
  NInput,
  NInputNumber,
  NSelect,
  NSlider,
  useMessage,
  type SelectOption,
} from 'naive-ui'
import { ArrowBackOutline, SparklesOutline } from '@vicons/ionicons5'
import TeacherDashboardShell from '../components/layout/TeacherDashboardShell.vue'
import KnowledgePointPicker from '../components/teacher/KnowledgePointPicker.vue'
import TrialQuestionComposer from '../components/teacher/TrialQuestionComposer.vue'
import {
  QUESTION_TYPE_LABELS,
  composerQuestionsFromCustom,
  createComposerQuestion,
  serializeComposerQuestions,
  type ComposerQuestion,
  type ComposerQuestionType,
} from '../utils/trialQuestionComposerModel'
import {
  aiGenerateTrialQuestions,
  createTeacherTrial,
  fetchTeacherTrialDetail,
  publishTeacherTrial,
  updateTeacherTrial,
  type CustomTrialQuestion,
} from '../api/teacherTrials'
import { labelForKnowledgeKey } from '../data/teacherKnowledgeCatalog'
import { useKnowledgeCatalog } from '../composables/useKnowledgeCatalog'
import { useTeacherOverviewInjected } from '../composables/useTeacherOverview'
import { useAuthStore } from '../stores/auth'
import { useTeacherNotificationStore } from '../stores/teacherNotifications'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const auth = useAuthStore()
const teacherNotifications = useTeacherNotificationStore()
const { selectedClassId, hasSelectedClass, classOptions } = useTeacherOverviewInjected()
const { domains: knowledgeDomains, loadCatalog } = useKnowledgeCatalog()

const draftId = computed(() => {
  const raw = route.query.draftId
  const parsed = raw ? Number(raw) : NaN
  return Number.isNaN(parsed) ? null : parsed
})

const title = ref('')
const description = ref('')
const trialType = ref('solo')
const selectedKnowledgeKeys = ref<string[]>([])
const difficulty = ref(72)
const duration = ref('60')
const publishMode = ref<'now' | 'draft' | 'scheduled'>('now')
const scheduleDelay = ref('30')
const deadline = ref<number | null>(null)
const notifyStudentsOnPublish = ref(true)

const questions = ref<ComposerQuestion[]>([])

const aiCount = ref(3)
const aiDifficulty = ref(60)
const aiQuestionTypes = ref<Array<'mcq' | 'multiple' | 'coding'>>(['mcq'])
const generatingAi = ref(false)
const submitting = ref(false)
const loadingDraft = ref(false)

const trialTypeOptions: SelectOption[] = [
  { label: '个人挑战', value: 'solo' },
  { label: '小组协作', value: 'team' },
  { label: '限时竞赛', value: 'timed' },
  { label: '深渊试炼', value: 'abyss' },
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

const aiTypeOptions = [
  { label: '单选题', value: 'mcq' as const },
  { label: '多选题', value: 'multiple' as const },
  { label: '代码题', value: 'coding' as const },
]

const classLabel = computed(() => {
  const found = classOptions.value.find((item) => item.value === selectedClassId.value)
  return typeof found?.label === 'string' ? found.label : '未选择班级'
})

const totalScore = computed(() => questions.value.reduce((sum, q) => sum + (q.score || 0), 0))

const typeBreakdown = computed(() => {
  const counter = new Map<ComposerQuestionType, number>()
  for (const q of questions.value) {
    counter.set(q.type, (counter.get(q.type) ?? 0) + 1)
  }
  return [...counter.entries()].map(([type, count]) => ({
    label: QUESTION_TYPE_LABELS[type],
    count,
  }))
})

const knowledgeCoverage = computed(() =>
  selectedKnowledgeKeys.value.map((key) => labelForKnowledgeKey(key)),
)

const computedTitle = computed(() => {
  if (title.value.trim()) return title.value.trim()
  const typeLabel =
    (trialTypeOptions.find((item) => item.value === trialType.value)?.label as string) ?? '个人挑战'
  const knowLabel = knowledgeCoverage.value.join('、')
  const head = knowLabel.slice(0, 24) + (knowLabel.length > 24 ? '…' : '')
  return head ? `${head} · ${typeLabel}` : `${typeLabel}试炼`
})

const primaryLabel = computed(() => {
  if (draftId.value) return '保存草稿修改'
  if (publishMode.value === 'draft') return '保存草稿'
  if (publishMode.value === 'scheduled') return '创建定时试炼'
  return '创建并发布'
})

async function loadDraft(id: number) {
  loadingDraft.value = true
  try {
    const detail = await fetchTeacherTrialDetail(id)
    title.value = detail.trial.title ?? ''
    trialType.value = detail.trial.trial_type || 'solo'
    difficulty.value = detail.trial.difficulty ?? 72
    duration.value = String(detail.trial.duration_minutes ?? 60)
    const keys = detail.trial.knowledge_keys?.length
      ? detail.trial.knowledge_keys
      : detail.trial.knowledge_key
        ? [detail.trial.knowledge_key]
        : []
    selectedKnowledgeKeys.value = keys
    const draft = detail.draft_questions?.length ? detail.draft_questions : detail.questions
    questions.value = composerQuestionsFromCustom(draft as CustomTrialQuestion[], keys[0])
    publishMode.value = 'draft'
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载草稿失败')
  } finally {
    loadingDraft.value = false
  }
}

async function runAiGenerate() {
  if (!selectedKnowledgeKeys.value.length) {
    message.warning('请先在左侧勾选知识点')
    return
  }
  if (!aiQuestionTypes.value.length) {
    message.warning('请至少选择一种 AI 出题题型')
    return
  }
  generatingAi.value = true
  try {
    const generated = await aiGenerateTrialQuestions(
      selectedKnowledgeKeys.value,
      Math.max(1, Math.min(20, aiCount.value)),
      { difficulty: aiDifficulty.value, question_types: aiQuestionTypes.value },
    )
    const mapped = generated.map((item) => {
      const key = item.knowledge_key || selectedKnowledgeKeys.value[0]
      if (item.question_type === 'coding') {
        const q = createComposerQuestion('coding', key)
        q.stem = item.stem
        q.starterCode = item.starter_code || q.starterCode
        q.runMode = (item.run_mode as 'stdout' | 'expression') || q.runMode
        q.hint = item.hint || ''
        q.testCases = (item.test_cases?.length
          ? item.test_cases.map((tc) => ({ ...tc }))
          : q.testCases) as typeof q.testCases
        q.difficulty = aiDifficulty.value
        return q
      }
      if (item.question_type === 'multiple') {
        const q = createComposerQuestion('multiple', key)
        q.stem = item.stem
        q.options = item.options?.length ? [...item.options] : ['', '', '', '']
        q.correctIndexes = item.correct_indexes?.length
          ? [...item.correct_indexes]
          : [item.correct_index ?? 0]
        q.difficulty = aiDifficulty.value
        return q
      }
      const q = createComposerQuestion('single', key)
      q.stem = item.stem
      q.options = item.options?.length ? [...item.options] : ['', '', '', '']
      q.correctIndex = item.correct_index ?? 0
      q.difficulty = aiDifficulty.value
      return q
    })
    questions.value = [...questions.value, ...mapped]
    message.success(`已生成 ${mapped.length} 道题目，可在中间栏继续编辑`)
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'AI 出题失败')
  } finally {
    generatingAi.value = false
  }
}

function ensureValid(forPublish: boolean): boolean {
  if (!selectedClassId.value) {
    message.warning('请先在顶部选择班级')
    return false
  }
  if (!selectedKnowledgeKeys.value.length) {
    message.warning('请至少勾选一个知识点')
    return false
  }
  if (forPublish && !questions.value.length) {
    message.warning('发布前请至少添加一道题目')
    return false
  }
  return true
}

function buildPayloadBase() {
  return {
    class_id: selectedClassId.value as number,
    title: computedTitle.value,
    description: description.value || undefined,
    trial_type: trialType.value,
    knowledge_keys: selectedKnowledgeKeys.value,
    knowledge_key: selectedKnowledgeKeys.value[0],
    difficulty: difficulty.value,
    duration_minutes: Number(duration.value),
    reward_points: Math.max(15, Math.round(difficulty.value / 2)),
    total_score: totalScore.value,
    deadline_at: deadline.value ? new Date(deadline.value).toISOString() : undefined,
    notify_students: notifyStudentsOnPublish.value,
  }
}

function notifyIfNeeded(studentCount: number) {
  if (notifyStudentsOnPublish.value && auth.profile?.id) {
    teacherNotifications.notifyAssignmentPublished(auth.profile.id, computedTitle.value, studentCount)
  }
}

async function saveDraftEdit(thenPublish: boolean) {
  if (!draftId.value) return
  if (!ensureValid(thenPublish)) return
  submitting.value = true
  try {
    await updateTeacherTrial(draftId.value, {
      title: computedTitle.value,
      draft_questions: serializeComposerQuestions(questions.value),
    })
    if (thenPublish) {
      const result = await publishTeacherTrial(draftId.value, notifyStudentsOnPublish.value)
      notifyIfNeeded(result.student_count ?? 0)
      message.success(
        result.student_count
          ? `已发布并通知 ${result.student_count} 名学生`
          : '草稿已发布',
      )
    } else {
      message.success('草稿试卷已更新')
    }
    void router.push('/teacher/trials')
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    submitting.value = false
  }
}

async function createNew() {
  if (!ensureValid(publishMode.value !== 'draft')) return
  submitting.value = true
  try {
    const result = await createTeacherTrial({
      ...buildPayloadBase(),
      publish_mode: publishMode.value,
      start_delay_minutes:
        publishMode.value === 'scheduled' ? Number(scheduleDelay.value) : undefined,
      custom_questions: questions.value.length
        ? serializeComposerQuestions(questions.value)
        : undefined,
    })
    const modeLabel =
      publishMode.value === 'draft'
        ? '已保存草稿'
        : publishMode.value === 'scheduled'
          ? '已创建定时试炼'
          : '已发布试炼'
    if (publishMode.value === 'now') {
      notifyIfNeeded(result.student_count ?? 0)
      message.success(
        result.student_count
          ? `${modeLabel}「${computedTitle.value}」，已通知 ${result.student_count} 名学生`
          : `${modeLabel}「${computedTitle.value}」`,
      )
    } else {
      message.success(`${modeLabel}「${computedTitle.value}」`)
    }
    void router.push('/teacher/trials')
  } catch (error) {
    message.error(error instanceof Error ? error.message : '创建失败')
  } finally {
    submitting.value = false
  }
}

function onPrimary() {
  if (draftId.value) {
    void saveDraftEdit(false)
  } else {
    void createNew()
  }
}

function goBack() {
  void router.push('/teacher/trials')
}

onMounted(() => {
  void loadCatalog()
  if (draftId.value) void loadDraft(draftId.value)
})
</script>

<template>
  <TeacherDashboardShell
    active-nav="trial"
    :page-title="draftId ? '编辑试炼试卷' : '创建试炼'"
    page-subtitle="TRIAL COMPOSER · 全屏出题工作台"
    hide-search
    toolbar-label="创建试炼班级与状态"
  >
    <div class="trial-create teacher-page">
      <header class="trial-create__bar">
        <n-button quaternary @click="goBack">
          <template #icon><n-icon :component="ArrowBackOutline" /></template>
          返回试炼中枢
        </n-button>
        <div class="trial-create__bar-meta">
          <span>目标班级：<strong>{{ classLabel }}</strong></span>
          <span>共 {{ questions.length }} 题 · {{ totalScore }} 分</span>
        </div>
      </header>

      <div v-if="!hasSelectedClass" class="teacher-state-panel trial-create__state">
        当前没有可用班级，请先在顶部选择班级后再创建试炼。
      </div>

      <div v-else class="trial-create__grid">
        <!-- 左：AI 出题优先 + 知识点 + 试卷配置 -->
        <aside class="trial-create__col trial-create__config">
          <section class="trial-create__card trial-create__ai trial-create__ai--hero">
            <header class="trial-create__ai-head">
              <h3><n-icon :component="SparklesOutline" /> AI 智能出题</h3>
              <span>推荐</span>
            </header>
            <p class="trial-create__ai-lead">基于所选知识点与题型批量生成题目，生成后可在中间栏继续编辑与微调。</p>
            <div class="tc-field">
              <span>题型（可多选）</span>
              <n-checkbox-group v-model:value="aiQuestionTypes">
                <n-checkbox v-for="opt in aiTypeOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </n-checkbox>
              </n-checkbox-group>
            </div>
            <div class="tc-ai-row">
              <label class="tc-field tc-field--narrow">
                <span>题量</span>
                <n-input-number v-model:value="aiCount" :min="1" :max="20" />
              </label>
              <label class="tc-field">
                <span>难度：{{ aiDifficulty }}</span>
                <n-slider v-model:value="aiDifficulty" :min="0" :max="100" :step="1" />
              </label>
            </div>
            <n-button
              type="warning"
              block
              class="tc-ai-generate"
              :loading="generatingAi"
              :disabled="!selectedKnowledgeKeys.length"
              @click="runAiGenerate"
            >
              <template #icon><n-icon :component="SparklesOutline" /></template>
              一键生成并加入试卷
            </n-button>
          </section>

          <section class="trial-create__card">
            <h3>知识点（知识宇宙）</h3>
            <KnowledgePointPicker v-model="selectedKnowledgeKeys" :domains="knowledgeDomains" />
          </section>

          <section class="trial-create__card">
            <h3>试卷设置</h3>
            <label class="tc-field">
              <span>试卷标题</span>
              <n-input v-model:value="title" :placeholder="computedTitle" />
            </label>
            <label class="tc-field">
              <span>试卷说明</span>
              <n-input
                v-model:value="description"
                type="textarea"
                :autosize="{ minRows: 2, maxRows: 4 }"
                placeholder="向学生说明本次试炼的目标与要求"
              />
            </label>
            <label class="tc-field">
              <span>试炼类型</span>
              <n-select v-model:value="trialType" :options="trialTypeOptions" />
            </label>
            <div class="tc-field">
              <span>难度：{{ difficulty }}</span>
              <n-slider v-model:value="difficulty" :min="0" :max="100" :step="1" />
              <div class="tc-difficulty-labels"><small>简单</small><small>中等</small><small>困难</small></div>
            </div>
            <label class="tc-field">
              <span>预计时长</span>
              <n-select v-model:value="duration" :options="durationOptions" />
            </label>
            <label class="tc-field" v-if="!draftId">
              <span>发布方式</span>
              <n-select v-model:value="publishMode" :options="publishModeOptions" />
            </label>
            <label v-if="!draftId && publishMode === 'scheduled'" class="tc-field">
              <span>开始时间</span>
              <n-select v-model:value="scheduleDelay" :options="scheduleDelayOptions" />
            </label>
            <label class="tc-field">
              <span>截止时间（可选）</span>
              <n-date-picker
                v-model:value="deadline"
                type="datetime"
                clearable
                placeholder="选择截止时间"
                style="width: 100%"
              />
            </label>
            <n-checkbox v-model:checked="notifyStudentsOnPublish">发布时通知全班学生</n-checkbox>
          </section>
        </aside>

        <!-- 中：题目列表与编辑 -->
        <section class="trial-create__col trial-create__main">
          <div v-if="loadingDraft" class="teacher-state-panel">正在加载草稿试卷…</div>
          <TrialQuestionComposer
            v-else
            v-model="questions"
            :domains="knowledgeDomains"
            :default-knowledge-key="selectedKnowledgeKeys[0]"
          />
        </section>

        <!-- 右：汇总与发布 -->
        <aside class="trial-create__col trial-create__summary">
          <section class="trial-create__card trial-create__sticky">
            <h3>试卷汇总</h3>
            <dl class="tc-summary">
              <div><dt>标题</dt><dd>{{ computedTitle }}</dd></div>
              <div><dt>目标班级</dt><dd>{{ classLabel }}</dd></div>
              <div><dt>题目数</dt><dd>{{ questions.length }} 题</dd></div>
              <div><dt>总分</dt><dd>{{ totalScore }} 分</dd></div>
              <div><dt>预计时长</dt><dd>{{ duration }} 分钟</dd></div>
            </dl>

            <div class="tc-summary__block">
              <span class="tc-summary__label">题型分布</span>
              <div v-if="typeBreakdown.length" class="tc-chips">
                <span v-for="item in typeBreakdown" :key="item.label" class="tc-chip">
                  {{ item.label }} ×{{ item.count }}
                </span>
              </div>
              <p v-else class="tc-summary__empty">尚未添加题目</p>
            </div>

            <div class="tc-summary__block">
              <span class="tc-summary__label">知识点覆盖</span>
              <div v-if="knowledgeCoverage.length" class="tc-chips">
                <span v-for="label in knowledgeCoverage" :key="label" class="tc-chip tc-chip--gold">
                  {{ label }}
                </span>
              </div>
              <p v-else class="tc-summary__empty">尚未勾选知识点</p>
            </div>

            <div class="tc-actions">
              <n-button
                type="primary"
                size="large"
                block
                class="tc-primary"
                :loading="submitting"
                @click="onPrimary"
              >
                {{ primaryLabel }}
              </n-button>
              <n-button
                v-if="draftId"
                secondary
                block
                :loading="submitting"
                @click="saveDraftEdit(true)"
              >
                保存并发布
              </n-button>
            </div>
          </section>
        </aside>
      </div>
    </div>
  </TeacherDashboardShell>
</template>

<style scoped>
.trial-create {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding-inline: var(--plex-page-gutter-x);
  padding-bottom: 1.5rem;
}

.trial-create__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.trial-create__bar-meta {
  display: flex;
  gap: 1.25rem;
  color: rgba(221, 230, 239, 0.7);
  font-size: 0.85rem;
}

.trial-create__bar-meta strong {
  color: #fff7ed;
}

.trial-create__state {
  padding: 2rem;
  text-align: center;
}

.trial-create__grid {
  display: grid;
  grid-template-columns: minmax(320px, 26%) minmax(0, 1fr) minmax(300px, 24%);
  gap: 1.1rem;
  align-items: start;
}

.trial-create__col {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-width: 0;
}

.trial-create__card {
  padding: 1.1rem 1.15rem;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 16px;
  background:
    radial-gradient(circle at 40% 0%, rgba(251, 146, 60, 0.07), transparent 38%),
    linear-gradient(145deg, rgba(5, 18, 30, 0.9), rgba(3, 12, 20, 0.76));
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.04);
}

.trial-create__card h3 {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0 0 0.9rem;
  color: #fff7ed;
  font-size: 1.02rem;
  font-weight: 720;
}

.trial-create__main .teacher-state-panel {
  padding: 2rem;
  text-align: center;
}

.trial-create__main {
  padding: 1.1rem 1.15rem;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 16px;
  background: linear-gradient(145deg, rgba(5, 18, 30, 0.78), rgba(3, 12, 20, 0.66));
  min-height: 480px;
  width: 100%;
}

.tc-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-bottom: 0.85rem;
  color: rgba(255, 237, 213, 0.72);
  font-size: 0.82rem;
}

.tc-field--narrow {
  max-width: 120px;
}

.tc-difficulty-labels {
  display: flex;
  justify-content: space-between;
  color: rgba(221, 230, 239, 0.45);
}

.tc-ai-row {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr);
  gap: 0.75rem;
  align-items: start;
}

.trial-create__ai--hero {
  border-color: rgba(251, 146, 60, 0.42);
  background:
    radial-gradient(circle at 80% 0%, rgba(251, 191, 36, 0.14), transparent 42%),
    linear-gradient(145deg, rgba(67, 20, 7, 0.55), rgba(5, 18, 30, 0.88));
  box-shadow: 0 0 28px rgba(251, 146, 60, 0.12);
}

.trial-create__ai-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.trial-create__ai-head h3 {
  margin: 0;
}

.trial-create__ai-head span {
  padding: 0.12rem 0.55rem;
  border-radius: 999px;
  border: 1px solid rgba(251, 191, 36, 0.45);
  background: rgba(251, 191, 36, 0.12);
  color: #fcd34d;
  font-size: 0.72rem;
  font-weight: 700;
}

.trial-create__ai-lead {
  margin: 0 0 0.85rem;
  color: rgba(254, 215, 170, 0.78);
  font-size: 0.82rem;
  line-height: 1.55;
}

.tc-ai-generate {
  margin-top: 0.25rem;
  font-weight: 750 !important;
}

.trial-create__sticky {
  position: sticky;
  top: 1rem;
}

.tc-summary {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin: 0 0 1rem;
}

.tc-summary div {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
}

.tc-summary dt {
  color: rgba(221, 230, 239, 0.6);
  font-size: 0.8rem;
}

.tc-summary dd {
  margin: 0;
  color: #fff7ed;
  font-size: 0.84rem;
  font-weight: 600;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tc-summary__block {
  margin-bottom: 0.9rem;
}

.tc-summary__label {
  display: block;
  margin-bottom: 0.45rem;
  color: rgba(255, 237, 213, 0.72);
  font-size: 0.8rem;
}

.tc-summary__empty {
  margin: 0;
  color: rgba(221, 230, 239, 0.45);
  font-size: 0.76rem;
}

.tc-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.tc-chip {
  padding: 0.22rem 0.55rem;
  border-radius: 999px;
  border: 1px solid rgba(251, 146, 60, 0.38);
  background: rgba(251, 146, 60, 0.1);
  color: #fdba74;
  font-size: 0.74rem;
}

.tc-chip--gold {
  border-color: rgba(251, 191, 36, 0.42);
  background: rgba(251, 191, 36, 0.1);
  color: #fcd34d;
}

.tc-actions {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  margin-top: 0.5rem;
}

.tc-primary {
  --n-color: #ea580c !important;
  --n-color-hover: #f97316 !important;
  --n-color-pressed: #c2410c !important;
  font-weight: 800 !important;
}

@media (max-width: 1280px) {
  .trial-create__grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .trial-create__sticky {
    position: static;
  }
}
</style>
