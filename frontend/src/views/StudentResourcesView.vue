<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NButton, NCollapse, NCollapseItem, NProgress, NSelect, NTag, useMessage } from 'naive-ui'
import DashboardShell from '../components/layout/DashboardShell.vue'
import StudentSectionTabs from '../components/student/StudentSectionTabs.vue'
import PersonalizedResourceContentViewer from '../components/personalized/PersonalizedResourceContentViewer.vue'
import AgentStepsTimeline from '../components/personalized/AgentStepsTimeline.vue'
import {
  createResourceTask,
  fetchPersonalizedResources,
  fetchResourceTask,
  fetchResourceTasks,
  retryResourceTask,
  type PersonalizedResource,
  type ResourceTask,
} from '../api/personalizedResources'
import { xiaoEResourceProgressHint, xiaoEResourceBackendLabel } from '../utils/xiaoEPersona'

const message = useMessage()
const knowledgeKey = ref('loop')
const learningStage = ref('学习')
const learningStyles = ref(['案例', '代码实验', '图文'])
const resourceFilter = ref('all')
const task = ref<ResourceTask | null>(null)
const taskHistory = ref<ResourceTask[]>([])
const resources = ref<PersonalizedResource[]>([])
const generating = ref(false)
const loading = ref(true)
const loadError = ref('')
const pollingTimedOut = ref(false)
const selected = ref<PersonalizedResource | null>(null)
const detailPanelRef = ref<HTMLElement | null>(null)

const knowledgeOptions = [
  { label: '程序结构', value: 'intro' }, { label: '注释', value: 'comment' },
  { label: '变量与类型', value: 'var' }, { label: '输入输出', value: 'io' },
  { label: '表达式与运算符', value: 'ops' }, { label: '条件分支', value: 'cond' },
  { label: '循环结构', value: 'loop' }, { label: 'range', value: 'range' },
  { label: '字符串', value: 'str' }, { label: '列表', value: 'list' },
  { label: '字典', value: 'dict' }, { label: '函数', value: 'func' },
  { label: '异常处理', value: 'except' }, { label: '文件读写', value: 'file' },
  { label: '累加算法', value: 'algo-sum' }, { label: '查找算法', value: 'algo-search' },
]

const typeLabels: Record<string, string> = {
  learning_bundle: '完整资源包',
  lesson_document: '讲解文档',
  mind_map: '思维导图',
  exercise_set: '分层题库',
  extended_reading: '拓展阅读',
  coding_lab: '代码实操',
  audio_explanation: '语音讲解',
  video_lesson: '教学短视频',
}

const typeOrder: Record<string, number> = {
  learning_bundle: 0,
  lesson_document: 1,
  mind_map: 2,
  exercise_set: 3,
  extended_reading: 4,
  coding_lab: 5,
  audio_explanation: 6,
  video_lesson: 7,
}

const stageOptions = [
  { label: '预习', value: '预习' },
  { label: '学习', value: '学习' },
  { label: '练习', value: '练习' },
  { label: '复习', value: '复习' },
  { label: '考试', value: '考试' },
]

const styleOptions = [
  { label: '图文', value: '图文' },
  { label: '案例', value: '案例' },
  { label: '代码实验', value: '代码实验' },
  { label: '交互', value: '交互' },
]

const typeOptions = computed(() => [
  { label: '全部类型', value: 'all' },
  ...Object.entries(typeLabels).map(([value, label]) => ({ value, label })),
])

const visibleTasks = computed(() => taskHistory.value.slice(0, 6))

const groupedResources = computed(() => {
  const picked = new Map<string, PersonalizedResource>()
  for (const item of resources.value) {
    if (resourceFilter.value !== 'all' && item.resource_type !== resourceFilter.value) continue
    const key = `${item.knowledge_key}:${item.resource_type}`
    const previous = picked.get(key)
    if (!previous || item.id > previous.id) picked.set(key, item)
  }
  const groups = new Map<string, PersonalizedResource[]>()
  for (const item of picked.values()) {
    const groupKey = item.knowledge_label || item.knowledge_key || '未标注知识点'
    const list = groups.get(groupKey) ?? []
    list.push(item)
    groups.set(groupKey, list)
  }
  return Array.from(groups, ([label, items]) => ({
    label,
    items: items.sort(
      (a, b) => (typeOrder[a.resource_type] ?? 99) - (typeOrder[b.resource_type] ?? 99),
    ),
  }))
})

const latestTaskStatus = computed(() => {
  const active = task.value ?? taskHistory.value[0]
  if (!active) return '暂无生成任务'
  if (active.status === 'completed') return '已完成'
  if (active.status === 'failed') return '生成失败'
  return `小E 准备中 · ${Math.round(active.progress)}%`
})

const taskProgressHint = computed(() => {
  if (!task.value) return ''
  return xiaoEResourceProgressHint(task.value.status, task.value.progress, task.value.current_agent)
})

const flatResources = computed(() =>
  groupedResources.value.flatMap((group) => group.items),
)

const pendingCount = computed(
  () => resources.value.filter((item) => item.review_status === 'pending_review').length,
)

const anomalyCount = computed(
  () => resources.value.filter((item) => Boolean(item.is_anomaly)).length,
)

function bundleForTask(taskId: string) {
  return resources.value.find(
    (item) => item.generation_task_id === taskId && item.resource_type === 'learning_bundle',
  )
}

function pickDefaultSelection() {
  const first = flatResources.value[0]
  if (first && !selected.value) selected.value = first
}

function selectResource(item: PersonalizedResource) {
  selected.value = item
  window.requestAnimationFrame(() => {
    detailPanelRef.value?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  })
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [resourceResult, taskResult] = await Promise.all([
      fetchPersonalizedResources(),
      fetchResourceTasks(),
    ])
    resources.value = resourceResult.items
    taskHistory.value = taskResult.items
    pickDefaultSelection()
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '资源加载失败'
  } finally {
    loading.value = false
  }
}

async function poll(id: string) {
  pollingTimedOut.value = false
  // 资源包 JSON 较大，云端生成可能 20–40s，多等一会
  for (let index = 0; index < 120; index += 1) {
    task.value = await fetchResourceTask(id)
    if (['completed', 'failed'].includes(task.value.status)) return
    await new Promise((resolve) => window.setTimeout(resolve, 1000))
  }
  pollingTimedOut.value = true
}

async function generate() {
  generating.value = true
  try {
    const coreTypes: PersonalizedResource['resource_type'][] = [
      'learning_bundle',
      'lesson_document',
      'mind_map',
      'exercise_set',
      'extended_reading',
      'coding_lab',
      'audio_explanation',
      'video_lesson',
    ]
    task.value = await createResourceTask(knowledgeKey.value, coreTypes, undefined, {
      target: '大学',
      learning_stage: learningStage.value,
      learning_style: learningStyles.value,
      force_regenerate: true,
    })
    if (task.value.status !== 'completed') await poll(task.value.task_id)
    if (task.value.status === 'failed') throw new Error(task.value.error || '生成任务失败')
    await load()
    // 任务内嵌资源优先合并，避免列表接口滞后导致「看不到」
    if (task.value.resources?.length) {
      const merged = new Map<number, PersonalizedResource>()
      for (const item of resources.value) merged.set(item.id, item)
      for (const item of task.value.resources) merged.set(item.id, item)
      resources.value = [...merged.values()]
    }
    const preferred =
      task.value.resources?.find((item) => item.resource_type === 'learning_bundle')
      ?? task.value.resources?.[0]
      ?? flatResources.value[0]
    if (preferred) selectResource(preferred)
    if (!resources.value.length) {
      message.warning('任务已完成，但暂未返回可展示资源，请稍后刷新或查看任务历史')
    } else if (pollingTimedOut.value) {
      message.info('任务仍在处理中，可稍后从任务历史继续查看')
    } else if (task.value.fallback_reason) {
      message.warning('云端暂时不可用，已用本地课程模板生成；修好网络后可再点生成')
    } else {
      const pending = resources.value.filter((item) => item.review_status === 'pending_review').length
      message.success(
        pending
          ? `学习资源包已生成（${pending} 项待审，可先预览学习）`
          : '学习资源包已生成，可在下方列表点开查看',
      )
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : '生成失败')
  } finally {
    generating.value = false
  }
}

async function retry(item: ResourceTask) {
  try {
    task.value = await retryResourceTask(item.task_id)
    await poll(task.value.task_id)
    await load()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '重试失败')
  }
}

function reviewStatusLabel(status: PersonalizedResource['review_status']) {
  if (status === 'pending_review') return '待教师审核'
  if (status === 'rejected') return '已驳回'
  return '已发布'
}

onMounted(() => {
  void load()
})
</script>

<template>
  <DashboardShell
    active-nav="track"
    page-title="个性化资源中心"
    page-subtitle="左侧选资源、右侧看内容；待审核资源也可先预览"
    search-placeholder=""
    hide-search
  >
    <template #toolbar><StudentSectionTabs area="learning" /></template>
    <main class="resource-page">
      <section class="generator">
        <div class="generator__copy">
          <h2>生成多模态学习资源</h2>
          <p>小E 会根据你的学习情况，生成讲解文档、思维导图、分层题库、代码实操与语音讲解。</p>
        </div>
        <div class="generator__controls">
          <n-select v-model:value="knowledgeKey" :options="knowledgeOptions" class="knowledge-select" />
          <n-select v-model:value="learningStage" :options="stageOptions" class="stage-select" />
          <n-select
            v-model:value="learningStyles"
            :options="styleOptions"
            multiple
            class="style-select"
            placeholder="学习方式"
          />
          <n-button type="primary" :loading="generating" @click="generate">生成学习资源包</n-button>
        </div>
      </section>

      <section class="resource-summary" aria-label="资源概览">
        <article>
          <span>资源包</span>
          <strong>{{ groupedResources.length }}</strong>
        </article>
        <article>
          <span>去重后资源</span>
          <strong>{{ groupedResources.reduce((sum, group) => sum + group.items.length, 0) }}</strong>
        </article>
        <article>
          <span>最新任务</span>
          <strong>{{ latestTaskStatus }}</strong>
        </article>
        <article>
          <span>异常待关注</span>
          <strong>{{ anomalyCount }}</strong>
        </article>
      </section>

      <p v-if="anomalyCount" class="pending-note">
        有 {{ anomalyCount }} 项异常内容待教师关注；其余资源已可直接学习。
      </p>
      <p v-else-if="pendingCount" class="pending-note pending-note--soft">
        有 {{ pendingCount }} 项内容仍在复核中，可先预习。
      </p>

      <section v-if="task" class="task-panel">
        <header>
          <strong>小E 正在准备资源</strong>
          <span v-if="task.fallback_reason">云端模型暂时不可用，小E 先用本地课程模板生成（内容较通用，可稍后重试）</span>
          <span v-else-if="task.backend === 'deepseek' || task.backend === 'iflytek_spark'">本次为云端实时生成</span>
        </header>
        <n-progress :percentage="task.progress" color="#25f5ee" />
        <p class="task-panel__hint">{{ taskProgressHint }}</p>
        <AgentStepsTimeline :steps="task.steps ?? []" />
        <p v-if="task.status === 'failed' && task.error" class="task-panel__error">{{ task.error }}</p>
      </section>

      <p v-if="pollingTimedOut" class="processing-note">任务仍在后台处理中，页面未将其标记为成功。</p>
      <div v-if="loading" class="resource-state">正在整理你的资源包...</div>
      <div v-else-if="loadError" class="resource-state resource-state--error">
        <span>{{ loadError }}</span>
        <n-button secondary size="small" @click="load">重试</n-button>
      </div>

      <template v-else>
        <section class="resource-tools">
          <h2>已生成资源</h2>
          <n-select v-model:value="resourceFilter" :options="typeOptions" class="type-select" />
        </section>

        <div v-if="groupedResources.length" class="resource-layout">
          <div class="resource-layout__list">
            <n-collapse class="resource-groups-collapse" :default-expanded-names="groupedResources.map((g) => g.label)">
              <n-collapse-item
                v-for="group in groupedResources"
                :key="group.label"
                :title="group.label"
                :name="group.label"
              >
                <template #header-extra>
                  <span class="resource-group__count">{{ group.items.length }} 类资源</span>
                </template>
                <div class="resource-grid">
                  <button
                    v-for="item in group.items"
                    :key="item.id"
                    type="button"
                    class="resource-card"
                    :class="{ 'resource-card--active': selected?.id === item.id }"
                    @click="selectResource(item)"
                  >
                    <span class="resource-card__tags">
                      <n-tag type="info">{{ typeLabels[item.resource_type] }}</n-tag>
                      <n-tag
                        v-if="item.review_status === 'pending_review' || item.is_anomaly"
                        type="warning"
                        size="small"
                      >
                        {{ item.is_anomaly ? '内容警示' : reviewStatusLabel(item.review_status) }}
                      </n-tag>
                      <n-tag :type="item.backend === 'iflytek_spark' ? 'success' : 'warning'">
                        {{ xiaoEResourceBackendLabel(item.backend) }}
                      </n-tag>
                    </span>
                    <strong>{{ item.title }}</strong>
                    <p>{{ item.recommendation_reason }}</p>
                    <span class="resource-card__meta">
                      <em>约 {{ item.estimated_minutes }} 分钟</em>
                    </span>
                  </button>
                </div>
              </n-collapse-item>
            </n-collapse>
          </div>

          <section
            ref="detailPanelRef"
            class="resource-detail"
            :class="{ 'resource-detail--empty': !selected }"
            aria-label="资源详情"
          >
            <template v-if="selected">
              <header>
                <div>
                  <h2>{{ selected.title }}</h2>
                  <p>{{ selected.knowledge_label }} · {{ typeLabels[selected.resource_type] }}</p>
                </div>
                <n-button quaternary @click="selected = null">关闭</n-button>
              </header>
              <n-tag
                v-if="selected.review_status === 'pending_review' || selected.is_anomaly"
                type="warning"
                class="pending-tag"
              >
                {{
                  selected.is_anomaly
                    ? '内容异常警示 · 可先预览，请以教师讲解与教材为准'
                    : '待教师审核 · 可先学习，正式发布以教师批准为准'
                }}
              </n-tag>
              <aside
                v-if="selected.student_warning || selected.is_anomaly"
                class="resource-warning"
                role="note"
              >
                <strong>学习提示</strong>
                <p>
                  {{
                    selected.student_warning
                      || '本资源由 AI 生成且尚未通过教师最终确认，内容可能存在不准确之处，请以课堂讲解与教材为准。'
                  }}
                </p>
              </aside>
              <PersonalizedResourceContentViewer
                :item="selected"
                :bundle-item="bundleForTask(selected.generation_task_id)"
                theme="student"
              />
              <h4>参考来源</h4>
              <ul>
                <li
                  v-for="citation in selected.citations"
                  :key="`${citation.document_id}-${citation.section}`"
                >
                  {{ citation.title }} · {{ citation.section }}：{{ citation.snippet }}
                </li>
              </ul>
            </template>
            <div v-else class="resource-detail__placeholder">
              <p>点击左侧资源卡片，在这里查看讲解、案例、代码与练习。</p>
            </div>
          </section>
        </div>
        <section v-else class="resource-state">
          暂无匹配资源。可在上方选择知识点后点击「生成」，生成完成后会出现在这里。
          <br />
          若刚生成成功却仍为空，请点「最近生成记录」里的「查看进度」，或刷新页面。
        </section>

        <n-collapse v-if="visibleTasks.length" class="task-history">
          <n-collapse-item title="最近生成记录" name="history">
            <article v-for="item in visibleTasks" :key="item.task_id" class="task-history__row">
              <div>
                <strong>{{ item.resources[0]?.knowledge_label || item.resources[0]?.title || '学习资源' }}</strong>
                <span>{{ item.status === 'completed' ? '已完成' : item.status === 'failed' ? '失败' : '进行中' }}</span>
              </div>
              <div class="task-history__actions">
                <n-button size="small" secondary @click="task = item">查看进度</n-button>
                <n-button v-if="item.status === 'failed' && item.recoverable" size="small" @click="retry(item)">重试</n-button>
              </div>
            </article>
          </n-collapse-item>
        </n-collapse>
      </template>
    </main>
  </DashboardShell>
</template>

<style scoped>
.resource-page {
  width: 100%;
  padding: 0 var(--plex-page-gutter-x) 2rem;
  overflow-y: auto;
}

.generator,
.task-panel,
.resource-state,
.resource-group,
.resource-detail,
.resource-summary article {
  border: 1px solid rgba(37, 245, 238, 0.15);
  border-radius: 0.75rem;
  background: rgba(3, 16, 28, 0.84);
}

.generator {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.2rem;
}

.generator__copy {
  flex: 1;
  min-width: 0;
}

.generator h2,
.resource-tools h2,
.resource-group h3,
.resource-detail h2,
.resource-detail h4 {
  margin: 0;
  color: #f2fbff;
}

.generator p,
.resource-detail header p {
  margin: 0.35rem 0 0;
  color: #7da5b6;
}

.generator__controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.knowledge-select,
.type-select,
.stage-select,
.style-select {
  width: 190px;
}

.style-select {
  min-width: 220px;
}

.resource-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.8rem;
  margin-top: 1rem;
}

.pending-note {
  margin: 0.75rem 0 0;
  color: #ffd28a;
  font-size: 0.9rem;
}

.resource-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.15fr);
  gap: 1rem;
  margin-top: 0.75rem;
  align-items: start;
}

.resource-layout__list {
  min-width: 0;
}

.resource-card--active {
  border-color: rgba(37, 245, 238, 0.55);
  box-shadow: 0 0 0 1px rgba(37, 245, 238, 0.25);
}

.resource-detail--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 320px;
}

.resource-detail__placeholder {
  text-align: center;
  color: rgba(125, 165, 182, 0.95);
  padding: 1.5rem;
}

.pending-tag {
  margin-bottom: 0.75rem;
}

.resource-warning {
  margin: 0 0 1rem;
  padding: 0.85rem 1rem;
  border-radius: 12px;
  border: 1px solid rgba(245, 158, 11, 0.35);
  background: rgba(120, 53, 15, 0.28);
}

.resource-warning strong {
  display: block;
  margin-bottom: 0.35rem;
  color: #fde68a;
  font-size: 0.9rem;
}

.resource-warning p {
  margin: 0;
  color: rgba(254, 243, 199, 0.92);
  font-size: 0.86rem;
  line-height: 1.55;
}

.resource-summary article {
  padding: 0.9rem 1rem;
}

.resource-summary span {
  display: block;
  color: rgba(203, 225, 235, 0.68);
  font-size: 0.78rem;
}

.resource-summary strong {
  display: block;
  margin-top: 0.3rem;
  color: #effcff;
  font-size: 1.05rem;
}

.task-panel {
  margin-top: 1rem;
  padding: 1rem;
}

.task-panel > header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  color: #b9e9e6;
  margin-bottom: 0.7rem;
}

.task-panel__hint {
  margin: 0.75rem 0 0;
  color: #8fb7c4;
  font-size: 0.86rem;
  line-height: 1.55;
}

.task-panel__error {
  margin: 0.55rem 0 0;
  color: #fca5a5;
  font-size: 0.84rem;
}

.processing-note {
  color: #ffd28a;
}

.resource-state {
  display: flex;
  min-height: 140px;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  margin-top: 1rem;
  padding: 1rem;
  color: rgba(214, 236, 245, 0.78);
}

.resource-state--error {
  color: #fecaca;
}

.resource-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin: 1rem 0 0.75rem;
}

.resource-groups-collapse {
  display: grid;
  gap: 0.65rem;
}

.resource-groups-collapse :deep(.n-collapse-item) {
  border: 1px solid rgba(37, 245, 238, 0.15);
  border-radius: 0.75rem;
  background: rgba(3, 16, 28, 0.84);
  overflow: hidden;
}

.resource-groups-collapse :deep(.n-collapse-item__header) {
  padding: 0.85rem 1rem;
  color: #f2fbff;
  font-weight: 650;
}

.resource-group__count {
  color: rgba(125, 165, 182, 0.9);
  font-size: 0.82rem;
  font-weight: 500;
}

.resource-groups-collapse :deep(.n-collapse-item__content-inner) {
  padding: 0 1rem 1rem;
}

.resource-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.8rem;
}

.resource-card {
  display: grid;
  gap: 0.65rem;
  padding: 1rem;
  border: 1px solid rgba(37, 245, 238, 0.12);
  border-radius: 0.55rem;
  background: rgba(2, 10, 18, 0.58);
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.resource-card:hover {
  border-color: rgba(37, 245, 238, 0.34);
}

.resource-card__tags,
.resource-card__meta {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
}

.resource-card strong {
  color: #f0faff;
}

.resource-card p,
.resource-card__meta {
  color: #86a8b7;
  font-size: 0.84rem;
}

.resource-card p {
  margin: 0;
  line-height: 1.55;
}

.resource-card__meta em {
  font-style: normal;
}

.task-history {
  margin-top: 1rem;
}

.task-history__row {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 0;
  border-top: 1px solid rgba(37, 245, 238, 0.1);
}

.task-history__row:first-child {
  border-top: 0;
}

.task-history__row > div:first-child {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.25rem;
  color: #d8f4f3;
}

.task-history__row span {
  color: #7da5b6;
  font-size: 0.78rem;
}

.task-history__actions {
  display: flex;
  flex-shrink: 0;
  gap: 0.5rem;
}

.resource-detail {
  margin-top: 0;
  padding: 1.2rem;
  position: sticky;
  top: 1rem;
  max-height: calc(100vh - 7rem);
  overflow: auto;
}

.resource-detail header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.resource-detail pre {
  max-height: none;
  overflow: visible;
  white-space: pre-wrap;
  color: #cce6ef;
  line-height: 1.6;
}

.resource-detail li {
  color: #8fb7c4;
  margin: 0.45rem 0;
}

@media (max-width: 1050px) {
  .resource-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .resource-layout {
    grid-template-columns: 1fr;
  }

  .resource-detail {
    position: static;
    max-height: none;
  }
}

@media (max-width: 760px) {
  .resource-page {
    padding-inline: 1rem;
  }

  .generator,
  .generator__controls,
  .resource-tools,
  .task-history__row {
    align-items: stretch;
    flex-direction: column;
  }

  .knowledge-select,
  .type-select {
    width: 100%;
  }

  .resource-summary,
  .resource-grid {
    grid-template-columns: 1fr;
  }
}
</style>
