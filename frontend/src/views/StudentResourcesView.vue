<script setup lang="ts">
import { computed, nextTick, onActivated, onMounted, ref } from 'vue'
import { NButton, NCollapse, NCollapseItem, NModal, NProgress, NSelect, NTag, useMessage } from 'naive-ui'
import DashboardShell from '../components/layout/DashboardShell.vue'
import PlexSyncState from '../components/common/PlexSyncState.vue'
import PersonalizedResourceContentViewer from '../components/personalized/PersonalizedResourceContentViewer.vue'
import AgentStepsTimeline from '../components/personalized/AgentStepsTimeline.vue'
import {
  createResourceTask,
  downloadPersonalizedResource,
  fetchPersonalizedResources,
  fetchResourceTask,
  fetchResourceTasks,
  retryResourceTask,
  type PersonalizedResource,
  type ResourceTask,
} from '../api/personalizedResources'
import {
  MODULE_CATEGORY_OPTIONS,
  knowledgeKeyForModuleCategory,
  type ModuleCategoryValue,
} from '../data/moduleCategories'
import { xiaoEResourceProgressHint, xiaoEResourceBackendLabel } from '../utils/xiaoEPersona'
import { formatHttpError } from '../api/http'

const message = useMessage()
const knowledgeKey = ref<ModuleCategoryValue>('loop')
/** 生成时默认学习阶段（UI 不再展示阶段选择） */
const DEFAULT_LEARNING_STAGE = '学习'
const learningStyles = ref(['案例', '代码实验', '图文'])
/** 生成目标资源类型：all = 完整学习包（不含视频） */
const generateResourceType = ref<'all' | PersonalizedResource['resource_type']>('all')
const resourceFilter = ref('all')
const task = ref<ResourceTask | null>(null)
const taskHistory = ref<ResourceTask[]>([])
const resources = ref<PersonalizedResource[]>([])
const generating = ref(false)
const loading = ref(true)
const loadError = ref('')
const pollingTimedOut = ref(false)
const selected = ref<PersonalizedResource | null>(null)
const materialViewerOpen = ref(false)
const materialViewerItem = ref<PersonalizedResource | null>(null)
const detailPanelRef = ref<HTMLElement | null>(null)
const resourceListRef = ref<HTMLElement | null>(null)
/** 任务完成后默认收起流水线，避免把「已生成资源」顶出首屏 */
const showPipelineDetails = ref(false)
type ResourceStatModal = 'knowledge' | 'resources' | 'anomaly' | null
const resourceStatModal = ref<ResourceStatModal>(null)

const knowledgeOptions = [...MODULE_CATEGORY_OPTIONS]

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

const generatableTypeKeys: PersonalizedResource['resource_type'][] = [
  'learning_bundle',
  'lesson_document',
  'mind_map',
  'exercise_set',
  'extended_reading',
  'coding_lab',
  'audio_explanation',
]

const typeOptions = computed(() => [
  { label: '全部类型', value: 'all' },
  ...Object.entries(typeLabels).map(([value, label]) => ({ value, label })),
])

const generateTypeOptions = computed(() => [
  { label: '完整学习包 · 含语音', value: 'all' },
  ...generatableTypeKeys.map((value) => ({ value, label: typeLabels[value] })),
])

function resolveGenerateTypes(): PersonalizedResource['resource_type'][] {
  if (generateResourceType.value === 'all') {
    return [...generatableTypeKeys]
  }
  if (generateResourceType.value === 'learning_bundle') {
    return ['learning_bundle']
  }
  return ['learning_bundle', generateResourceType.value]
}

const visibleTasks = computed(() => taskHistory.value.slice(0, 6))

/** 同知识点同类型去重：已批准优先，其次更大 id */
function dedupeVisible(items: PersonalizedResource[]) {
  const picked = new Map<string, PersonalizedResource>()
  for (const item of items) {
    if (item.review_status === 'rejected') continue
    const key = `${item.knowledge_key}:${item.resource_type}`
    const previous = picked.get(key)
    if (!previous) {
      picked.set(key, item)
      continue
    }
    const prevApproved = previous.review_status === 'approved'
    const nextApproved = item.review_status === 'approved'
    if (nextApproved && !prevApproved) {
      picked.set(key, item)
    } else if (nextApproved === prevApproved && item.id > previous.id) {
      picked.set(key, item)
    }
  }
  return [...picked.values()]
}

function groupByKnowledge(items: PersonalizedResource[]) {
  const groups = new Map<string, PersonalizedResource[]>()
  for (const item of items) {
    const groupKey = item.knowledge_label || item.knowledge_key || '未标注知识点'
    const list = groups.get(groupKey) ?? []
    list.push(item)
    groups.set(groupKey, list)
  }
  return Array.from(groups, ([label, groupItems]) => ({
    label,
    items: groupItems.sort(
      (a, b) => (typeOrder[a.resource_type] ?? 99) - (typeOrder[b.resource_type] ?? 99),
    ),
  }))
}

/** 概览卡片不受类型下拉影响，避免筛到「思维导图」时误以为只有导图 */
const overviewItems = computed(() => dedupeVisible(resources.value))

const overviewGroupCount = computed(() => groupByKnowledge(overviewItems.value).length)

const overviewResourceCount = computed(() => overviewItems.value.length)

const groupedResources = computed(() => {
  const filtered = overviewItems.value.filter(
    (item) => resourceFilter.value === 'all' || item.resource_type === resourceFilter.value,
  )
  return groupByKnowledge(filtered)
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

const hasAnyVisibleResources = computed(() => overviewResourceCount.value > 0)

const pendingCount = computed(
  () => resources.value.filter((item) => item.review_status === 'pending_review').length,
)

const anomalyCount = computed(
  () => resources.value.filter((item) => Boolean(item.is_anomaly)).length,
)

const approvedResources = computed(() =>
  overviewItems.value.filter((item) => item.review_status === 'approved'),
)

const anomalyResources = computed(() =>
  resources.value.filter((item) => Boolean(item.is_anomaly) && item.review_status !== 'rejected'),
)

const knowledgeGroups = computed(() => groupByKnowledge(overviewItems.value))

function openResourceStatModal(kind: ResourceStatModal) {
  resourceStatModal.value = kind
}

const resourceStatModalVisible = computed({
  get: () => resourceStatModal.value !== null,
  set: (value: boolean) => {
    if (!value) resourceStatModal.value = null
  },
})

const pipelineExpanded = computed(() => {
  if (!task.value) return false
  if (task.value.status !== 'completed') return true
  return showPipelineDetails.value
})

function bundleForTask(taskId: string) {
  return resources.value.find(
    (item) => item.generation_task_id === taskId && item.resource_type === 'learning_bundle',
  )
}

function preferLearningBundle(items: PersonalizedResource[]) {
  return (
    items.find((item) => item.resource_type === 'learning_bundle' && item.review_status !== 'rejected')
    ?? items.find((item) => item.review_status !== 'rejected')
    ?? null
  )
}

function pickDefaultSelection(force = false) {
  if (selected.value && !force) return
  const preferred = preferLearningBundle(overviewItems.value) ?? flatResources.value[0]
  if (preferred) selected.value = preferred
}

function selectResource(item: PersonalizedResource) {
  selected.value = item
  resourceStatModal.value = null
  window.requestAnimationFrame(() => {
    detailPanelRef.value?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  })
}

function hasRenderableContent(item: PersonalizedResource | null | undefined) {
  if (!item) return false
  const content = item.content
  if (!content || typeof content !== 'object') return false
  if (typeof content.markdown === 'string' && content.markdown.trim()) return true
  if (content.format === 'pedagogical_v2') return true
  if (content.format === 'coding_lab' && (content.scenario || content.starter_code)) return true
  if (content.format === 'tree' && (content.root || (Array.isArray(content.children) && content.children.length))) {
    return true
  }
  if (Array.isArray(content.questions) && content.questions.length) return true
  if (typeof content.transcript === 'string' && content.transcript.trim()) return true
  if (typeof content.script === 'string' && content.script.trim()) return true
  if (item.content_url) return true
  return Object.keys(content).length > 0
}

function openMaterialViewer(item: PersonalizedResource) {
  materialViewerItem.value = item
  materialViewerOpen.value = true
  selected.value = item
  resourceStatModal.value = null
}

function viewResourceMaterial(item: PersonalizedResource) {
  openMaterialViewer(item)
  if (!hasRenderableContent(item)) {
    message.warning(`「${item.title}」暂无正文，可尝试下载或重新生成`)
    return
  }
  message.success(`已打开「${item.title}」资料`)
}

function downloadResourceMaterial(item: PersonalizedResource) {
  try {
    downloadPersonalizedResource(item)
    message.success(`开始下载「${item.title}」`)
  } catch (error) {
    message.error(error instanceof Error ? error.message : '下载失败')
  }
}

async function generateQuizSet() {
  generating.value = true
  showPipelineDetails.value = true
  resetTypeFilter()
  try {
    // 借鉴 QuickForm：围绕知识点生成可回收的结构化题目集（exercise_set）
    task.value = await createResourceTask(
      knowledgeKeyForModuleCategory(knowledgeKey.value),
      ['exercise_set', 'learning_bundle'],
      undefined,
      {
        target: '大学',
        learning_stage: DEFAULT_LEARNING_STAGE,
        learning_style: learningStyles.value.length ? learningStyles.value : ['案例', '代码实验'],
        force_regenerate: true,
        require_real_api: true,
      },
    )
    if (task.value.status !== 'completed') await poll(task.value.task_id)
    if (task.value.status === 'failed') throw new Error(task.value.error || '出题失败')
    await load()
    if (task.value.resources?.length) {
      const merged = new Map<number, PersonalizedResource>()
      for (const item of resources.value) merged.set(item.id, item)
      for (const item of task.value.resources) merged.set(item.id, item)
      resources.value = [...merged.values()].filter((item) => item.review_status !== 'rejected')
    }
    const quiz =
      resources.value.find(
        (item) =>
          item.resource_type === 'exercise_set' &&
          item.generation_task_id === task.value?.task_id,
      ) || preferLearningBundle(task.value.resources || [])
    if (quiz) selectResource(quiz)
    message.success('分层题库已生成，可查看资料或下载')
    await revealResourceList()
  } catch (error) {
    message.error(formatHttpError(error, '出题失败'))
  } finally {
    generating.value = false
  }
}

function resetTypeFilter() {
  resourceFilter.value = 'all'
}

async function revealResourceList() {
  await nextTick()
  resourceListRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function load(options?: { silent?: boolean }) {
  const silent = Boolean(options?.silent && resources.value.length)
  if (!silent) {
    loading.value = true
    loadError.value = ''
  }
  try {
    const [resourceResult, taskResult] = await Promise.all([
      fetchPersonalizedResources(),
      fetchResourceTasks(),
    ])
    resources.value = resourceResult.items
    taskHistory.value = taskResult.items
    // 若当前选中项已被驳回，切到可见项
    if (selected.value) {
      const fresh = resources.value.find((item) => item.id === selected.value?.id)
      selected.value = fresh && fresh.review_status !== 'rejected' ? fresh : null
    }
    pickDefaultSelection()
  } catch (error) {
    if (!silent) {
      loadError.value = formatHttpError(error, '资源加载失败')
    }
  } finally {
    loading.value = false
  }
}

async function poll(id: string) {
  pollingTimedOut.value = false
  // 资源包 JSON 较大，云端生成可能 20–40s，多等一会
  for (let index = 0; index < 120; index += 1) {
    task.value = await fetchResourceTask(id)
    if (task.value.status !== 'completed') showPipelineDetails.value = true
    if (['completed', 'failed'].includes(task.value.status)) return
    await new Promise((resolve) => window.setTimeout(resolve, 1000))
  }
  pollingTimedOut.value = true
}

async function generate() {
  generating.value = true
  showPipelineDetails.value = true
  resetTypeFilter()
  try {
    const coreTypes = resolveGenerateTypes()
    task.value = await createResourceTask(
      knowledgeKeyForModuleCategory(knowledgeKey.value),
      coreTypes,
      undefined,
      {
      target: '大学',
      learning_stage: DEFAULT_LEARNING_STAGE,
      learning_style: learningStyles.value,
      force_regenerate: true,
      require_real_api: true,
    },
    )
    if (task.value.status !== 'completed') await poll(task.value.task_id)
    if (pollingTimedOut.value) {
      message.info('真实模型仍在生成，任务会在后台继续；可从最近生成记录查看进度')
      return
    }
    if (task.value.status === 'failed') throw new Error(task.value.error || '生成任务失败')
    await load()
    // 任务内嵌资源优先合并，避免列表接口滞后导致「看不到」
    if (task.value.resources?.length) {
      const merged = new Map<number, PersonalizedResource>()
      for (const item of resources.value) merged.set(item.id, item)
      for (const item of task.value.resources) merged.set(item.id, item)
      resources.value = [...merged.values()].filter((item) => item.review_status !== 'rejected')
    }
    resetTypeFilter()
    showPipelineDetails.value = false
    const preferred =
      preferLearningBundle(task.value.resources ?? [])
      ?? preferLearningBundle(overviewItems.value)
      ?? flatResources.value[0]
    if (preferred) selectResource(preferred)
    else pickDefaultSelection(true)
    await revealResourceList()
    if (!resources.value.length) {
      message.warning('任务已完成，但暂未返回可展示资源，请稍后刷新或查看任务历史')
    } else if (pollingTimedOut.value) {
      message.info('任务仍在处理中，可稍后从任务历史继续查看')
    } else if (task.value.fallback_reason) {
      message.warning('云端生成服务暂时不可用，请稍后重新生成')
    } else {
      const pending = resources.value.filter((item) => item.review_status === 'pending_review').length
      const approved = resources.value.filter((item) => item.review_status === 'approved').length
      message.success(
        approved
          ? `学习资源已就绪 · ${approved} 项可直接学习${pending ? ` · 另有 ${pending} 项待审可预览` : ''}`
          : pending
            ? `学习资源包已生成 · ${pending} 项待审，可先预览学习`
            : '学习资源包已生成，可在下方列表点开查看',
      )
    }
  } catch (error) {
    message.error(formatHttpError(error, '生成失败'))
  } finally {
    generating.value = false
  }
}

async function retry(item: ResourceTask) {
  try {
    showPipelineDetails.value = true
    task.value = await retryResourceTask(item.task_id)
    await poll(task.value.task_id)
    await load()
    resetTypeFilter()
    showPipelineDetails.value = false
    pickDefaultSelection(true)
    await revealResourceList()
  } catch (error) {
    message.error(formatHttpError(error, '重试失败'))
  }
}

function reviewStatusLabel(status: PersonalizedResource['review_status']) {
  if (status === 'pending_review') return '待教师审核'
  if (status === 'rejected') return '已驳回'
  return '已发布'
}

onMounted(() => {
  resetTypeFilter()
  void load()
})

onActivated(() => {
  // KeepAlive 可能残留「思维导图」等筛选项，切回页面时恢复全部类型
  resetTypeFilter()
  // 教师/智能体审核后切回本页时刷新，确保已批准与待审资源立刻可见
  void load({ silent: true }).then(() => {
    pickDefaultSelection()
  })
})
</script>

<template>
  <DashboardShell
    active-nav="track"
    page-title="个性化资源中心"
    page-subtitle="左侧选资源、右侧看内容；已审核通过与待审资源均可学习"
    search-placeholder=""
    hide-search
  >
    <main class="resource-page">
      <section class="generator">
        <div class="generator__copy">
          <h2>生成个性化学习资源</h2>
          <p>选择知识点与资源类型，生成讲解、导图、练习、实操和语音资料。</p>
        </div>
        <div class="generator__controls">
          <n-select v-model:value="knowledgeKey" :options="knowledgeOptions" class="knowledge-select" placeholder="知识点" />
          <n-select
            v-model:value="generateResourceType"
            :options="generateTypeOptions"
            class="type-select"
            placeholder="资源类型"
          />
          <n-button type="primary" :loading="generating" @click="generate">生成学习资源</n-button>
          <n-button secondary :loading="generating" @click="generateQuizSet">生成题目</n-button>
        </div>
      </section>

      <section class="resource-summary" aria-label="资源概览">
        <article role="button" tabindex="0" @click="openResourceStatModal('knowledge')" @keydown.enter.prevent="openResourceStatModal('knowledge')">
          <span>知识点</span>
          <strong>{{ overviewGroupCount }}</strong>
        </article>
        <article role="button" tabindex="0" @click="openResourceStatModal('resources')" @keydown.enter.prevent="openResourceStatModal('resources')">
          <span>可学习资源</span>
          <strong>{{ overviewResourceCount }}</strong>
        </article>
        <article>
          <span>最新任务</span>
          <strong>{{ latestTaskStatus }}</strong>
        </article>
        <article role="button" tabindex="0" @click="openResourceStatModal('anomaly')" @keydown.enter.prevent="openResourceStatModal('anomaly')">
          <span>异常待关注</span>
          <strong>{{ anomalyCount }}</strong>
        </article>
      </section>

      <n-modal
        v-model:show="resourceStatModalVisible"
        preset="card"
        class="resource-stat-modal"
        :style="{ width: 'min(480px, 92vw)', maxWidth: '92vw' }"
        :title="resourceStatModal === 'knowledge' ? '按知识点分类' : resourceStatModal === 'resources' ? '可学习资源' : '异常待关注'"
      >
        <div v-if="resourceStatModal === 'knowledge'" class="resource-stat-modal__body">
          <p v-if="!knowledgeGroups.length" class="resource-stat-modal__empty">暂无已生成资源</p>
          <section v-for="group in knowledgeGroups" :key="group.label" class="resource-stat-group">
            <h4>{{ group.label }}</h4>
            <ul class="resource-stat-list">
              <li v-for="item in group.items" :key="item.id">
                <div class="resource-stat-list__main">
                  <strong>{{ typeLabels[item.resource_type] || item.resource_type }} · {{ item.title }}</strong>
                  <span>{{ item.knowledge_label }}</span>
                </div>
                <div class="resource-stat-list__actions">
                  <n-button size="tiny" type="primary" secondary @click="viewResourceMaterial(item)">查看资料</n-button>
                  <n-button size="tiny" quaternary @click="downloadResourceMaterial(item)">下载</n-button>
                </div>
              </li>
            </ul>
          </section>
        </div>
        <div v-else-if="resourceStatModal === 'resources'" class="resource-stat-modal__body">
          <p v-if="!approvedResources.length" class="resource-stat-modal__empty">暂无审核通过的资源，可先预览待审内容</p>
          <ul v-else class="resource-stat-list">
            <li v-for="item in approvedResources" :key="item.id">
              <div class="resource-stat-list__main">
                <strong>{{ item.title }}</strong>
                <span>{{ item.knowledge_label }} · {{ typeLabels[item.resource_type] || item.resource_type }}</span>
              </div>
              <div class="resource-stat-list__actions">
                <n-button size="tiny" type="primary" secondary @click="viewResourceMaterial(item)">查看资料</n-button>
                <n-button size="tiny" quaternary @click="downloadResourceMaterial(item)">下载</n-button>
              </div>
            </li>
          </ul>
        </div>
        <div v-else class="resource-stat-modal__body">
          <p v-if="!anomalyResources.length" class="resource-stat-modal__empty">暂无异常待关注项</p>
          <ul v-else class="resource-stat-list">
            <li v-for="item in anomalyResources" :key="item.id">
              <div class="resource-stat-list__main">
                <strong>{{ item.title }}</strong>
                <span>{{ item.knowledge_label }} · 教师已放行，建议留意</span>
              </div>
              <div class="resource-stat-list__actions">
                <n-button size="tiny" type="primary" secondary @click="viewResourceMaterial(item)">查看资料</n-button>
                <n-button size="tiny" quaternary @click="downloadResourceMaterial(item)">下载</n-button>
              </div>
            </li>
          </ul>
        </div>
      </n-modal>

      <n-modal
        v-model:show="materialViewerOpen"
        preset="card"
        class="resource-material-modal"
        :style="{ width: 'min(920px, 96vw)', maxWidth: '96vw' }"
        :title="materialViewerItem ? `资料 · ${materialViewerItem.title}` : '资料详情'"
      >
        <template v-if="materialViewerItem">
          <header class="resource-material-modal__header">
            <div>
              <p>
                {{ materialViewerItem.knowledge_label }} ·
                {{ typeLabels[materialViewerItem.resource_type] || materialViewerItem.resource_type }}
              </p>
              <n-tag
                v-if="materialViewerItem.review_status === 'pending_review' || materialViewerItem.is_anomaly"
                type="warning"
                size="small"
              >
                {{
                  materialViewerItem.is_anomaly
                    ? '内容异常警示 · 可先预览'
                    : '待教师审核 · 可先学习'
                }}
              </n-tag>
            </div>
            <n-button size="small" secondary @click="downloadResourceMaterial(materialViewerItem)">
              下载
            </n-button>
          </header>
          <aside
            v-if="materialViewerItem.student_warning || materialViewerItem.is_anomaly"
            class="resource-warning"
            role="note"
          >
            <strong>学习提示</strong>
            <p>
              {{
                materialViewerItem.student_warning
                  || '本资源由 AI 生成且尚未通过教师最终确认，内容可能存在不准确之处，请以课堂讲解与教材为准。'
              }}
            </p>
          </aside>
          <div v-if="!hasRenderableContent(materialViewerItem)" class="resource-material-modal__empty">
            暂无正文内容。可点击下载，或回到上方按知识点与资源类型重新生成。
          </div>
          <PersonalizedResourceContentViewer
            v-else
            :item="materialViewerItem"
            :bundle-item="bundleForTask(materialViewerItem.generation_task_id)"
            theme="student"
          />
        </template>
      </n-modal>

      <p v-if="anomalyCount" class="pending-note">
        有 {{ anomalyCount }} 项异常内容待教师关注；其余资源已可直接学习。
      </p>
      <p v-else-if="pendingCount" class="pending-note pending-note--soft">
        有 {{ pendingCount }} 项内容仍在复核中，可先预习。
      </p>

      <section v-if="task" class="task-panel">
        <header>
          <strong>{{ task.status === 'completed' ? '资源已准备完成' : '小E 正在准备资源' }}</strong>
          <div class="task-panel__header-actions">
            <span v-if="task.fallback_reason">云端生成服务暂时不可用，请稍后重新生成</span>
            <span v-else-if="task.backend === 'deepseek' || task.backend === 'iflytek_spark'">本次为云端实时生成</span>
            <n-button
              v-if="task.status === 'completed'"
              size="tiny"
              quaternary
              @click="showPipelineDetails = !showPipelineDetails"
            >
              {{ showPipelineDetails ? '收起流水线' : '查看流水线' }}
            </n-button>
          </div>
        </header>
        <n-progress :percentage="task.progress" color="#25f5ee" />
        <p class="task-panel__hint">{{ taskProgressHint }}</p>
        <AgentStepsTimeline v-if="pipelineExpanded" :steps="task.steps ?? []" />
        <p v-if="task.status === 'failed' && task.error" class="task-panel__error">{{ task.error }}</p>
      </section>

      <p v-if="pollingTimedOut" class="processing-note">任务仍在后台处理中，页面未将其标记为成功。</p>
      <PlexSyncState
        v-if="loading && !resources.length"
        label="正在整理你的资源包…"
        hint="同步已生成与已审核通过的学习材料"
      />
      <div v-else-if="loadError" class="resource-state resource-state--error">
        <span>{{ loadError }}</span>
        <n-button secondary size="small" @click="load()">重试</n-button>
      </div>

      <template v-else>
        <section ref="resourceListRef" class="resource-tools">
          <div>
            <h2>已生成资源</h2>
            <p class="resource-tools__hint">已批准与待审资源均可点开学习；默认显示全部类型。</p>
          </div>
          <n-select v-model:value="resourceFilter" :options="typeOptions" class="type-select" />
        </section>

        <div v-if="groupedResources.length" class="resource-layout">
          <div class="resource-layout__list">
            <section
              v-for="group in groupedResources"
              :key="group.label"
              class="resource-group"
            >
              <header class="resource-group__header">
                <h3>{{ group.label }}</h3>
                <span class="resource-group__count">{{ group.items.length }} 类资源</span>
              </header>
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
                      v-if="item.review_status === 'approved'"
                      type="success"
                      size="small"
                    >
                      已发布
                    </n-tag>
                    <n-tag
                      v-else-if="item.review_status === 'pending_review' || item.is_anomaly"
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
            </section>
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
                <div class="resource-detail__actions">
                  <n-button size="small" secondary @click="downloadResourceMaterial(selected)">下载</n-button>
                  <n-button quaternary @click="selected = null">关闭</n-button>
                </div>
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
        <section v-else-if="hasAnyVisibleResources" class="resource-state">
          当前类型下没有资源。
          <n-button type="primary" size="small" @click="resetTypeFilter">查看全部类型</n-button>
        </section>
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
                <n-button size="small" secondary @click="task = item; showPipelineDetails = item.status !== 'completed'">查看进度</n-button>
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
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}

.knowledge-select,
.type-select {
  width: 220px;
}

.resource-material-modal__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.85rem;
}

.resource-material-modal__header p {
  margin: 0 0 0.4rem;
  color: rgba(180, 210, 225, 0.78);
  font-size: 0.88rem;
}

.resource-material-modal__empty {
  padding: 1.25rem 0.5rem;
  color: rgba(255, 210, 138, 0.95);
  font-size: 0.92rem;
  line-height: 1.55;
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

.resource-summary article[role='button'] {
  cursor: pointer;
  transition: border-color 0.15s ease, transform 0.15s ease;
}

.resource-summary article[role='button']:hover {
  transform: translateY(-2px);
  border-color: rgba(37, 245, 238, 0.35);
}

.resource-stat-modal {
  width: min(480px, 92vw);
}

.resource-stat-modal :deep(.n-card__content) {
  max-height: min(68vh, 520px);
  overflow-y: auto;
}

.resource-stat-modal__empty {
  margin: 0;
  color: rgba(148, 163, 184, 0.9);
}

.resource-stat-group + .resource-stat-group {
  margin-top: 0.85rem;
}

.resource-stat-group h4 {
  margin: 0 0 0.35rem;
  color: #e2f7ff;
}

.resource-stat-group ul,
.resource-stat-list {
  margin: 0;
  padding-left: 1rem;
  color: rgba(226, 232, 240, 0.85);
  font-size: 0.86rem;
}

.resource-stat-list {
  list-style: none;
  padding-left: 0;
}

.resource-stat-list li {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.65rem;
  padding: 0.55rem 0.65rem;
  border-radius: 0.65rem;
  border: 1px solid rgba(46, 255, 241, 0.1);
  background: rgba(8, 20, 34, 0.45);
}

.resource-stat-list__main {
  min-width: 0;
  flex: 1;
}

.resource-stat-list strong {
  display: block;
  color: #f8fafc;
}

.resource-stat-list span {
  color: rgba(148, 163, 184, 0.95);
  font-size: 0.78rem;
}

.resource-stat-list__actions {
  display: flex;
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.resource-detail__actions {
  display: flex;
  align-items: center;
  gap: 0.4rem;
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

.task-panel__header-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 0.55rem;
  text-align: right;
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
  scroll-margin-top: 1rem;
}

.resource-tools__hint {
  margin: 0.35rem 0 0;
  color: #7da5b6;
  font-size: 0.82rem;
}

.resource-group {
  margin-bottom: 0.85rem;
  padding: 0.85rem 1rem 1rem;
}

.resource-group__header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.resource-group__header h3 {
  margin: 0;
  color: #f2fbff;
  font-size: 0.98rem;
}

.resource-group__count {
  color: rgba(125, 165, 182, 0.9);
  font-size: 0.82rem;
  font-weight: 500;
}

.resource-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
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
    grid-template-columns: 1fr;
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
