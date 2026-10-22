<script setup lang="ts">
import { computed, h, nextTick, onActivated, onDeactivated, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { NPagination, useDialog, NButton, NCollapse, NCollapseItem, NIcon, NInput, NModal, NProgress, NSelect, NTag, useMessage } from 'naive-ui'
import { TrashOutline, BookOutline, LayersOutline, CheckmarkCircleOutline, WarningOutline } from '@vicons/ionicons5'
import { useThemeStore } from '../stores/theme'
import { useResourceTaskSession } from '../composables/useResourceTaskSession'
import DashboardShell from '../components/layout/DashboardShell.vue'
import AiUsageSummary from '../components/shared/AiUsageSummary.vue'
import PlexSyncState from '../components/common/PlexSyncState.vue'
import PersonalizedResourceContentViewer from '../components/personalized/PersonalizedResourceContentViewer.vue'
import AgentStepsTimeline from '../components/personalized/AgentStepsTimeline.vue'
import {
  downloadPersonalizedResource,
  type PersonalizedResource,
  type ResourceTask,
} from '../api/personalizedResources'
import {
  MODULE_CATEGORY_OPTIONS,
  knowledgeKeyForModuleCategory,
  resolveModuleCategory,
  type ModuleCategoryValue,
} from '../data/moduleCategories'
import { xiaoEResourceProgressHint, xiaoEResourceBackendLabel } from '../utils/xiaoEPersona'
import {
  RESOURCE_DATE_FILTER_OPTIONS,
  filterPersonalizedResources,
  type ResourceDateFilter,
} from '../utils/resourceListFilters'

import { practiceRequest } from '../api/studentPractice'
const dialog = useDialog(), trashOpen = ref(false), trashPage = ref(1), trashTotal = ref(0), modalPage = ref(1)
const trashBusy = ref(false), trashError = ref('')
let trashEpoch = 0
const trashRows = ref<Array<{id:number;title:string;batch_id:string;expires_at:string}>>([])
async function loadTrash(){const ticket=++trashEpoch;trashBusy.value=true;trashError.value='';try{const result=await practiceRequest<{items:typeof trashRows.value;total:number}>('get','/resource-trash',undefined,{page:trashPage.value});if(ticket===trashEpoch){trashRows.value=result.items;trashTotal.value=result.total}}catch(e){if(ticket===trashEpoch)trashError.value=e instanceof Error?e.message:'回收站加载失败'}finally{if(ticket===trashEpoch)trashBusy.value=false}}
onDeactivated(()=>{++trashEpoch;trashOpen.value=false;trashBusy.value=false;trashRows.value=[]})
async function restoreTrash(row:typeof trashRows.value[number],batch=false){try{await practiceRequest('post','/resource-trash/restore',batch?{batch_id:row.batch_id}:{resource_id:row.id});await Promise.all([session.load(),loadTrash()]);message.success('资源已恢复')}catch(e){message.error(e instanceof Error?e.message:'恢复失败')}}
function deleteResource(item:PersonalizedResource,whole=false){dialog.warning({title:whole?'删除整个资源包？':'删除这条资源？',content:'移入回收站后保留七天，到期后无法恢复。',positiveText:'移入回收站',negativeText:'取消',onPositiveClick:async()=>{try{await practiceRequest('delete',whole?`/resource-packages/${encodeURIComponent(item.generation_task_id)}`:`/personalized-resources/${item.id}`);selected.value=null;materialViewerOpen.value=false;await session.load();message.success(() => h('span', ['已移入回收站 ', h(NButton, { text: true, onClick: () => { trashOpen.value = true } }, () => '查看回收站')]), { duration: 6000 })}catch(e){message.error(e instanceof Error?e.message:'删除失败')}}})}
watch(trashPage,loadTrash)
watch(trashOpen,v=>{if(v)void loadTrash()})
const message = useMessage()
const themeStore = useThemeStore()
const knowledgeKey = ref<ModuleCategoryValue>('loop')
/** 生成时默认学习阶段（UI 不再展示阶段选择） */
const DEFAULT_LEARNING_STAGE = '学习'
const learningStyles = ref(['案例', '代码实验', '图文'])
/** 生成目标资源类型：all = 完整学习包（不含视频） */
const generateResourceType = ref<'all' | PersonalizedResource['resource_type']>('all')
const resourceFilter = ref('all')
const resourceSearch = ref('')
const resourceDateFilter = ref<ResourceDateFilter>('all')
const resourceThemeFilter = ref<'all' | ModuleCategoryValue>('all')
const route = useRoute()
watch(() => route.query.knowledge_key, value => {
  if (typeof value === 'string') {
    knowledgeKey.value = resolveModuleCategory(value)
    resourceThemeFilter.value = resolveModuleCategory(value)
  }
}, { immediate: true })
const modalResourceSearch = ref('')
const modalResourceDateFilter = ref<ResourceDateFilter>('all')
const modalResourceThemeFilter = ref<'all' | ModuleCategoryValue>('all')
watch([modalResourceSearch,modalResourceDateFilter,modalResourceThemeFilter],()=>{modalPage.value=1})
const session = useResourceTaskSession()
const { task, taskHistory, resources, generating, loading, loadError, taskError, pollingTimedOut } = session
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

const themeFilterOptions = computed(() => [
  { label: '全部主题', value: 'all' },
  ...knowledgeOptions.map((item) => ({ label: item.label, value: item.value })),
])

function applyListFilters(
  items: PersonalizedResource[],
  search: string,
  date: ResourceDateFilter,
  theme: 'all' | ModuleCategoryValue,
) {
  return filterPersonalizedResources(items, { search, date, theme })
}

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
  const typeFiltered = overviewItems.value.filter(
    (item) => resourceFilter.value === 'all' || item.resource_type === resourceFilter.value,
  )
  const filtered = applyListFilters(
    typeFiltered,
    resourceSearch.value,
    resourceDateFilter.value,
    resourceThemeFilter.value,
  )
  return groupByKnowledge(filtered)
})

const filteredApprovedResources = computed(() =>
  applyListFilters(
    approvedResources.value,
    modalResourceSearch.value,
    modalResourceDateFilter.value,
    modalResourceThemeFilter.value,
  ),
)

const filteredKnowledgeGroups = computed(() => {
  const filtered = applyListFilters(
    overviewItems.value,
    modalResourceSearch.value,
    modalResourceDateFilter.value,
    modalResourceThemeFilter.value,
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

function openResourceStatModal(kind: ResourceStatModal) {
  modalPage.value = 1
  resourceStatModal.value = kind
  modalResourceSearch.value = ''
  modalResourceDateFilter.value = 'all'
  modalResourceThemeFilter.value = 'all'
}

function formatResourceDate(value: string | null | undefined) {
  if (!value) return '时间未记录'
  return value.slice(0, 10)
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

async function downloadResourceMaterial(item: PersonalizedResource) {
  try {
    await downloadPersonalizedResource(item)
    message.success(`开始下载「${item.title}」`)
  } catch (error) {
    message.error(error instanceof Error ? error.message : '下载失败')
  }
}

function resetTypeFilter() {
  resourceFilter.value = 'all'
  resourceSearch.value = ''
  resourceDateFilter.value = 'all'
  resourceThemeFilter.value = 'all'
}

async function revealResourceList() {
  await nextTick()
  resourceListRef.value?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' })
}

async function presentResult(result: ResourceTask | null, preferQuiz = false) {
  if (!result) return
  if (result.status === 'failed') return
  if (result.status !== 'completed') {
    message.info('任务仍在后台处理中，可从最近生成记录继续查看进度')
    return
  }
  if (loadError.value) return
  resetTypeFilter()
  showPipelineDetails.value = false
  const candidates = resources.value.filter(item => item.generation_task_id === result.task_id)
  const preferred = (preferQuiz ? candidates.find(item => item.resource_type === 'exercise_set') : null)
    ?? preferLearningBundle(candidates) ?? candidates[0]
  if (preferred) selectResource(preferred)
  else pickDefaultSelection(true)
  await revealResourceList()
  if (task.value?.task_id !== result.task_id) return
  if (!candidates.length) message.warning('任务已完成，当前没有可展示的资源；请查看课程依据与任务状态')
  else message.success('学习资源已生成，可查看资料；发布状态以教师审核为准')
}

async function generate(preferQuiz = false) {
  if (generating.value) return
  showPipelineDetails.value = true
  resetTypeFilter()
  const result = await session.generate(
    knowledgeKeyForModuleCategory(knowledgeKey.value),
    preferQuiz ? ['exercise_set', 'learning_bundle'] : resolveGenerateTypes(),
    undefined,
    { target: '大学', learning_stage: DEFAULT_LEARNING_STAGE,
      learning_style: learningStyles.value, force_regenerate: true, require_real_api: true },
  )
  await presentResult(result, preferQuiz)
}

async function retry(item: ResourceTask) {
  if (generating.value) return
  showPipelineDetails.value = true
  await presentResult(await session.retry(item.task_id))
}

async function inspectTask(item: ResourceTask) {
  if (generating.value) return
  showPipelineDetails.value = item.status !== 'completed'
  await session.inspect(item.task_id)
}

watch(resources, () => {
  const fresh = resources.value.find(item => item.id === selected.value?.id)
  selected.value = fresh && fresh.review_status !== 'rejected' ? fresh : null
  const material = resources.value.find(item => item.id === materialViewerItem.value?.id)
  materialViewerItem.value = material && material.review_status !== 'rejected' ? material : null
  if (!materialViewerItem.value) materialViewerOpen.value = false
  pickDefaultSelection()
}, { flush: 'sync' })

function reviewStatusLabel(status: PersonalizedResource['review_status']) {
  if (status === 'pending_review') return '待教师审核'
  if (status === 'rejected') return '已驳回'
  return '已发布'
}

onActivated(resetTypeFilter)
onDeactivated(() => {
  materialViewerOpen.value = false
  materialViewerItem.value = null
  selected.value = null
  resourceStatModal.value = null
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
      <n-modal v-model:show="trashOpen" preset="card" class="plex-reading-modal resource-trash-modal" title="资源回收站 · 七天内可恢复" :style="{width:'min(900px,94vw)',maxHeight:'80dvh'}"><div class="trash-list"><p v-if="trashBusy" role="status">正在读取回收站…</p><p v-else-if="trashError" role="alert">{{trashError}} <n-button @click="loadTrash">重试</n-button></p><p v-else-if="!trashRows.length">回收站为空</p><article v-for="row in trashBusy || trashError ? [] : trashRows" :key="row.id"><div><strong>{{row.title}}</strong><p>剩余约 {{Math.max(0,Math.ceil((Date.parse(row.expires_at)-Date.now())/3600000))}} 小时 · 保留至 {{new Date(row.expires_at).toLocaleString()}}</p></div><n-button @click="restoreTrash(row)">恢复</n-button><n-button @click="restoreTrash(row,true)">恢复同批次</n-button></article></div><template #footer><n-pagination v-model:page="trashPage" :item-count="trashTotal" :page-size="20"/></template></n-modal>
      <AiUsageSummary />
      <section class="generator" data-tour="student-resources">
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
          <n-button type="primary" :loading="generating" @click="generate(false)">生成学习资源</n-button>
          <n-button secondary :loading="generating" @click="generate(true)">生成题目</n-button>
        </div>
      </section>

      <header class="resource-management-tools"><h2>我的资源</h2><n-button class="plex-action-button" @click="trashOpen=true"><template #icon><n-icon :component="TrashOutline" /></template>回收站</n-button></header>
      <section class="resource-summary" aria-label="资源概览">
        <article role="button" tabindex="0" @click="openResourceStatModal('knowledge')" @keydown.enter.prevent="openResourceStatModal('knowledge')" @keydown.space.prevent="openResourceStatModal('knowledge')">
          <n-icon v-if="themeStore.isComic" class="comic-stat-icon" :component="BookOutline" aria-hidden="true" />
          <span>知识点</span>
          <strong>{{ overviewGroupCount }}</strong>
        </article>
        <article role="button" tabindex="0" @click="openResourceStatModal('resources')" @keydown.enter.prevent="openResourceStatModal('resources')" @keydown.space.prevent="openResourceStatModal('resources')">
          <n-icon v-if="themeStore.isComic" class="comic-stat-icon" :component="LayersOutline" aria-hidden="true" />
          <span>可学习资源</span>
          <strong>{{ overviewResourceCount }}</strong>
        </article>
        <article>
          <n-icon v-if="themeStore.isComic" class="comic-stat-icon" :component="CheckmarkCircleOutline" aria-hidden="true" />
          <span>最新任务</span>
          <strong>{{ latestTaskStatus }}</strong>
        </article>
        <article role="button" tabindex="0" @click="openResourceStatModal('anomaly')" @keydown.enter.prevent="openResourceStatModal('anomaly')" @keydown.space.prevent="openResourceStatModal('anomaly')">
          <n-icon v-if="themeStore.isComic" class="comic-stat-icon" :component="WarningOutline" aria-hidden="true" />
          <span>异常待关注</span>
          <strong>{{ anomalyCount }}</strong>
        </article>
      </section>

      <n-modal
        v-model:show="resourceStatModalVisible"
        preset="card"
        class="resource-stat-modal plex-reading-modal"
        :style="{ width: 'min(960px, 94vw)', maxWidth: '94vw', maxHeight: '78dvh' }"
        :title="resourceStatModal === 'knowledge' ? '按知识点分类' : resourceStatModal === 'resources' ? '可学习资源' : '异常待关注'"
      >
        <div
          v-if="resourceStatModal === 'knowledge' || resourceStatModal === 'resources'"
          class="resource-stat-modal__filters"
        >
          <n-input
            v-model:value="modalResourceSearch"
            size="small"
            clearable
            placeholder="搜索标题或知识点"
          />
          <n-select
            v-model:value="modalResourceDateFilter"
            size="small"
            :options="RESOURCE_DATE_FILTER_OPTIONS"
          />
          <n-select
            v-model:value="modalResourceThemeFilter"
            size="small"
            :options="themeFilterOptions"
          />
        </div>
        <div v-if="resourceStatModal === 'knowledge'" class="resource-stat-modal__body">
          <p v-if="!filteredKnowledgeGroups.length" class="resource-stat-modal__empty">暂无已生成资源</p>
          <section v-for="group in filteredKnowledgeGroups" :key="group.label" class="resource-stat-group">
            <h4>{{ group.label }}</h4>
            <ul class="resource-stat-list">
              <li v-for="item in group.items" :key="item.id">
                <div class="resource-stat-list__main">
                  <strong>{{ typeLabels[item.resource_type] || item.resource_type }} · {{ item.title }}</strong>
                  <span>{{ item.knowledge_label }} · {{ formatResourceDate(item.created_at) }}</span>
                </div>
                <div class="resource-stat-list__actions">
                  <n-button size="tiny" type="primary" secondary @click="viewResourceMaterial(item)">查看资料</n-button>
                  <n-button size="tiny" quaternary @click="downloadResourceMaterial(item)">下载</n-button>
              <n-button size="tiny" quaternary @click="deleteResource(item)">删除</n-button>
                </div>
              </li>
            </ul>
          </section>
        </div>
        <div v-else-if="resourceStatModal === 'resources'" class="resource-stat-modal__body">
          <p v-if="!approvedResources.length" class="resource-stat-modal__empty">暂无审核通过的资源，可先预览待审内容</p>
          <p v-else-if="!filteredApprovedResources.length" class="resource-stat-modal__empty">没有符合筛选条件的资源</p>
          <ul v-else class="resource-stat-list">
            <li v-for="item in filteredApprovedResources.slice((modalPage-1)*8,modalPage*8)" :key="item.id">
              <div class="resource-stat-list__main">
                <strong>{{ item.title }}</strong>
                <span>
                  {{ item.knowledge_label }} · {{ typeLabels[item.resource_type] || item.resource_type }}
                  · {{ formatResourceDate(item.created_at) }}
                </span>
              </div>
              <div class="resource-stat-list__actions">
                <n-button size="tiny" type="primary" secondary @click="viewResourceMaterial(item)">查看资料</n-button>
                <n-button size="tiny" quaternary @click="downloadResourceMaterial(item)">下载</n-button>
              <n-button size="tiny" quaternary @click="deleteResource(item)">删除</n-button>
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
              <n-button size="tiny" quaternary @click="deleteResource(item)">删除</n-button>
              </div>
            </li>
          </ul>
        </div>
        <template #footer><n-pagination v-if="resourceStatModal==='resources'" v-model:page="modalPage" :item-count="filteredApprovedResources.length" :page-size="8" /></template>
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
          <strong>{{ task.status === 'completed' ? '资源已准备完成' : task.status === 'failed' ? '资源生成未完成' : '小E 正在准备资源' }}</strong>
          <div class="task-panel__header-actions">
            <span v-if="task.fallback_reason && task.status === 'completed' && task.backend !== 'local_rules'">本次已由备用模型完成生成</span>
            <span v-else-if="task.fallback_reason">本次使用了回退方式，请结合任务状态查看结果</span>
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
        <div v-if="task.learning_context" class="task-panel__hint">
          <p>本次学习建议：{{ task.learning_context.reason }}</p>
          <p v-if="task.learning_context.exercise_action">{{ task.learning_context.exercise_action }}</p>
          <p>这份资源保留生成时的学习依据。完成新的练习后，可重新生成适合当前进度的资源。</p>
        </div>
        <AgentStepsTimeline v-if="pipelineExpanded" :steps="task.steps ?? []" />
        <p v-if="task.course_evidence" class="task-panel__hint" role="status">{{ task.course_evidence.message }}</p>
        <p v-if="task.status === 'failed' && task.error" class="task-panel__error">{{ task.error }}</p>
      </section>

      <p v-if="taskError" class="task-panel__error" role="alert">{{ taskError }} · 可刷新页面或从最近生成记录核对任务，提交状态不确定时请先核对历史，避免重复创建。</p>
      <p v-if="pollingTimedOut" class="processing-note">任务仍在后台处理中，页面未将其标记为成功。</p>
      <PlexSyncState
        v-if="loading && !resources.length"
        label="正在整理你的资源包…"
        hint="同步已生成与已审核通过的学习材料"
      />
      <div v-else-if="loadError" class="resource-state resource-state--error">
        <span>{{ loadError }}</span>
        <n-button secondary size="small" @click="session.load()">重试</n-button>
      </div>

      <template v-else>
        <section ref="resourceListRef" class="resource-tools">
          <div>
            <h2>已生成资源</h2>
            <p class="resource-tools__hint">已批准与待审资源均可点开学习；支持按标题、时间与知识主题筛选。</p>
          </div>
          <div class="resource-tools__filters">
            <n-input
              v-model:value="resourceSearch"
              size="small"
              clearable
              placeholder="搜索标题"
              class="resource-tools__search"
            />
            <n-select
              v-model:value="resourceDateFilter"
              size="small"
              :options="RESOURCE_DATE_FILTER_OPTIONS"
              class="resource-tools__select"
            />
            <n-select
              v-model:value="resourceThemeFilter"
              size="small"
              :options="themeFilterOptions"
              class="resource-tools__select"
            />
            <n-select v-model:value="resourceFilter" :options="typeOptions" class="type-select" />
          </div>
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
                  <n-button @click="deleteResource(selected)">删除资源</n-button><n-button @click="deleteResource(selected,true)">删除整包</n-button>
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
                  :key="`${citation.document_id}-${citation.chunk_id || citation.section}`"
                >
                  {{ citation.title }} · {{ citation.section }}<span v-if="citation.version"> · 版本 {{ citation.version }}</span>：{{ citation.snippet }}
                </li>
              </ul>
            </template>
            <div v-else class="resource-detail__placeholder">
              <p>点击左侧资源卡片，在这里查看讲解、案例、代码与练习。</p>
            </div>
          </section>
        </div>
        <section v-else-if="hasAnyVisibleResources" class="resource-state">
          当前筛选条件下没有资源。
          <n-button type="primary" size="small" @click="resetTypeFilter">清除筛选</n-button>
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
                <n-button size="small" secondary :disabled="generating" @click="inspectTask(item)">查看进度</n-button>
                <n-button v-if="item.status === 'failed' && item.recoverable" size="small" :disabled="generating" @click="retry(item)">重试</n-button>
              </div>
            </article>
          </n-collapse-item>
        </n-collapse>
      </template>
    </main>
  </DashboardShell>
</template>

<style scoped>
.resource-management-tools{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:20px}.resource-management-tools h2{margin:0;font-size:17px;color:var(--plex-text)}

.resource-page,
.resource-material-modal,
.resource-stat-modal {
  --resource-warning-text: #f6cd68;
  --resource-error-text: #fca5a5;
}

.resource-page {
  min-width: 0;
  overflow-wrap: anywhere;
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
  border: 1px solid var(--plex-border);
  border-radius: 0.75rem;
  background: var(--plex-bg-glass);
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
  color: var(--plex-text);
}

.generator p,
.resource-detail header p {
  margin: 0.35rem 0 0;
  color: var(--plex-text-muted);
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
  color: var(--plex-text-muted);
  font-size: 0.88rem;
}

.resource-material-modal__empty {
  padding: 1.25rem 0.5rem;
  color: var(--resource-warning-text);
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
  color: var(--resource-warning-text);
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
  color: var(--plex-text-muted);
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
  background: color-mix(in srgb, var(--resource-warning-text) 10%, var(--plex-bg-card));
}

.resource-warning strong {
  display: block;
  margin-bottom: 0.35rem;
  color: var(--resource-warning-text);
  font-size: 0.9rem;
}

.resource-warning p {
  margin: 0;
  color: var(--resource-warning-text);
  font-size: 0.86rem;
  line-height: 1.55;
}

.resource-summary article {
  padding: 0.9rem 1rem;
}

.resource-summary span {
  display: block;
  color: var(--plex-text-muted);
  font-size: 0.78rem;
}

.resource-summary strong {
  display: block;
  margin-top: 0.3rem;
  color: var(--plex-text);
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

.resource-stat-modal :deep(.n-card-content) {
  max-height: min(52vh, 380px);
  overflow-y: auto;
}

.resource-stat-modal__filters {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 0.45rem;
  margin-bottom: 0.65rem;
}

.resource-tools__filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 0.45rem;
}

.resource-tools__search {
  width: min(200px, 42vw);
}

.resource-tools__select {
  width: 118px;
}

.resource-stat-modal__empty {
  margin: 0;
  color: var(--plex-text-muted);
}

.resource-stat-group + .resource-stat-group {
  margin-top: 0.85rem;
}

.resource-stat-group h4 {
  margin: 0 0 0.35rem;
  color: var(--plex-text);
}

.resource-stat-group ul,
.resource-stat-list {
  margin: 0;
  padding-left: 1rem;
  color: var(--plex-text-muted);
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
  background: var(--plex-bg-card);
}

.resource-stat-list__main {
  min-width: 0;
  flex: 1;
}

.resource-stat-list strong {
  display: block;
  color: var(--plex-text);
}

.resource-stat-list span {
  color: var(--plex-text-muted);
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
  color: var(--plex-text);
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
  color: var(--plex-text-muted);
  font-size: 0.86rem;
  line-height: 1.55;
}

.task-panel__error {
  margin: 0.55rem 0 0;
  color: var(--resource-error-text);
  font-size: 0.84rem;
}

.processing-note {
  color: var(--resource-warning-text);
}

.resource-state {
  display: flex;
  min-height: 140px;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  margin-top: 1rem;
  padding: 1rem;
  color: var(--plex-text-muted);
}

.resource-state--error {
  color: var(--resource-error-text);
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
  color: var(--plex-text-muted);
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
  color: var(--plex-text);
  font-size: 0.98rem;
}

.resource-group__count {
  color: var(--plex-text-muted);
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
  border: 1px solid var(--plex-border);
  border-radius: 0.55rem;
  background: var(--plex-bg-card);
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
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0.5rem;
}

.resource-card strong {
  color: var(--plex-text);
}

.resource-card p,
.resource-card__meta {
  color: var(--plex-text-muted);
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
  color: var(--plex-text);
}

.task-history__row span {
  color: var(--plex-text-muted);
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
  color: var(--plex-text);
  line-height: 1.6;
}

.resource-detail li {
  color: var(--plex-text-muted);
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

:global(html[data-theme='light']) .resource-page,
:global(html[data-theme='light']) .resource-material-modal,
:global(html[data-theme='light']) .resource-stat-modal {
  --resource-warning-text: #8b5900;
  --resource-error-text: #b42318;
}

.resource-material-modal__header p,
.resource-material-modal__empty {
  color: var(--plex-text-muted);
}

.resource-card:focus-visible,
.resource-summary article[role='button']:focus-visible {
  outline: 3px solid var(--plex-accent);
  outline-offset: 3px;
}

.resource-detail,
.resource-card,
.task-panel,
.resource-state {
  min-width: 0;
}

@media (prefers-reduced-motion: reduce) {
  .resource-summary article[role='button'] {
    transition: none;
  }
  .resource-summary article[role='button']:hover {
    transform: none;
  }
}

@media (max-width: 760px) {
  .resource-detail header,
  .task-panel > header,
  .resource-state,
  .resource-stat-list li {
    flex-wrap: wrap;
  }
  .resource-detail__actions {
    flex-wrap: wrap;
  }
}
</style>

<style>
.resource-stat-modal.n-card{display:flex;max-height:78dvh}.resource-stat-modal.n-card>.n-card-content{min-height:0;display:flex;flex-direction:column;overflow:hidden;max-height:none!important}.resource-stat-modal__body{overflow:auto;min-height:0;scrollbar-width:none}.resource-stat-modal__body::-webkit-scrollbar{display:none}.resource-stat-modal>.n-card-header,.resource-stat-modal>.n-card__footer{flex-shrink:0}.resource-stat-modal .resource-stat-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.resource-stat-modal .resource-stat-list>li{min-width:0;display:flex;flex-direction:column;align-items:stretch;border:1px solid var(--plex-border);border-radius:12px;padding:14px}.resource-stat-list__main strong{overflow-wrap:anywhere;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.resource-stat-modal__filters{flex-shrink:0}.trash-list{max-height:56dvh;overflow:auto}.trash-list article{display:flex;align-items:center;gap:12px;border-bottom:1px solid var(--plex-border);padding:16px 0;flex-wrap:wrap}.trash-list article>div{flex:1;min-width:160px}.trash-list p{font-size:12px;opacity:.7}@media(max-width:600px){.resource-stat-modal .resource-stat-list{grid-template-columns:1fr}}
</style>
