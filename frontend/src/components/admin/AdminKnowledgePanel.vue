<script setup lang="ts">
/**
 * 管理员 · 知识智能层：知识库文档 / 索引状态 / 知识星域 / 使用分析。
 * 检索测试与 RAG Debug 见 AdminRagDebugPanel。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  NButton,
  NDrawer,
  NDrawerContent,
  NEmpty,
  NIcon,
  NInput,
  NPopconfirm,
  NProgress,
  NSelect,
  NSpin,
  NSwitch,
  NTag,
  NUpload,
  NUploadDragger,
  useMessage,
  type SelectOption,
  type UploadCustomRequestOptions,
} from 'naive-ui'
import {
  CloudUploadOutline,
  DocumentTextOutline,
  GitNetworkOutline,
  LayersOutline,
  PulseOutline,
  RefreshOutline,
  SparklesOutline,
  TrashOutline,
} from '@vicons/ionicons5'
import PlexKnowledgeGraph from '../shared/PlexKnowledgeGraph.vue'
import AdminRagDebugPanel from './AdminRagDebugPanel.vue'
import type { KgNode } from '../../data/knowledgeGraphData'
import {
  INDEX_STATUS_LABELS,
  KNOWLEDGE_TYPE_LABELS,
  RELATION_TYPE_LABELS,
  RESOURCE_TYPE_LABELS,
  RUNNING_INDEX_STATUSES,
  addKnowledgeRelation,
  createKnowledgeTextDocument,
  deleteKnowledgeDocument,
  deleteKnowledgeRelation,
  fetchKnowledgeAnalytics,
  fetchKnowledgeChunks,
  fetchKnowledgeConcept,
  fetchKnowledgeDocuments,
  fetchKnowledgeGraph,
  fetchKnowledgeIndexStatus,
  reindexKnowledgeDocument,
  seedKnowledge,
  uploadKnowledgeDocument,
  verifyKnowledgeDocument,
  verifyKnowledgeRelation,
  type IndexStatus,
  type KnowledgeAnalyticsOverview,
  type KnowledgeChunk,
  type KnowledgeConceptDetail,
  type KnowledgeDocument,
  type KnowledgeGraphResult,
  type KnowledgeIndexStatus,
  type RelationType,
  type ResourceType,
} from '../../api/knowledge'
import { mapConceptEdges, mapConceptNodes } from '../../utils/knowledgeGraphMap'

type TabKey = 'documents' | 'graph' | 'debug' | 'analytics'

const message = useMessage()
const activeTab = ref<TabKey>('documents')
const tabs: Array<{ key: TabKey; label: string; icon: typeof DocumentTextOutline }> = [
  { key: 'documents', label: '知识库与索引', icon: DocumentTextOutline },
  { key: 'graph', label: '知识星域', icon: GitNetworkOutline },
  { key: 'debug', label: '检索测试与诊断', icon: SparklesOutline },
  { key: 'analytics', label: '使用分析', icon: PulseOutline },
]

// ------------------------------------------------------------------ 索引状态
const indexStatus = ref<KnowledgeIndexStatus | null>(null)
const statusLoading = ref(false)
let pollTimer: ReturnType<typeof setInterval> | undefined

async function loadStatus() {
  statusLoading.value = true
  try {
    indexStatus.value = await fetchKnowledgeIndexStatus()
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    statusLoading.value = false
  }
}

const embeddedRate = computed(() => {
  const s = indexStatus.value
  if (!s || !s.chunk_total) return 0
  return Math.round((s.chunk_embedded / s.chunk_total) * 100)
})

const hasRunningJobs = computed(() => (indexStatus.value?.running_jobs.length ?? 0) > 0 || documents.value.some((d) => RUNNING_INDEX_STATUSES.includes(d.status)))

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => {
    if (hasRunningJobs.value) {
      void loadStatus()
      void loadDocuments(false)
    }
  }, 3000)
}

function stopPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = undefined
}

// ------------------------------------------------------------------ 文档
const documents = ref<KnowledgeDocument[]>([])
const docTotal = ref(0)
const docPage = ref(1)
const docPerPage = 12
const docLoading = ref(false)
const docStatusFilter = ref<IndexStatus | ''>('')
const docKeyword = ref('')

const statusFilterOptions: SelectOption[] = [
  { label: '全部状态', value: '' },
  ...(Object.keys(INDEX_STATUS_LABELS) as IndexStatus[]).map((k) => ({ label: INDEX_STATUS_LABELS[k], value: k })),
]

async function loadDocuments(showLoading = true) {
  if (showLoading) docLoading.value = true
  try {
    const result = await fetchKnowledgeDocuments({
      page: docPage.value,
      per_page: docPerPage,
      status: docStatusFilter.value || undefined,
      keyword: docKeyword.value.trim() || undefined,
    })
    documents.value = result.items
    docTotal.value = result.total
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    docLoading.value = false
  }
}

const docPages = computed(() => Math.max(1, Math.ceil(docTotal.value / docPerPage)))

watch([docStatusFilter], () => {
  docPage.value = 1
  void loadDocuments()
})

function statusTone(status: IndexStatus): 'success' | 'error' | 'warning' | 'info' {
  if (status === 'READY') return 'success'
  if (status === 'FAILED') return 'error'
  if (status === 'PENDING') return 'info'
  return 'warning'
}

// 上传
const uploadResourceType = ref<ResourceType>('markdown')
const uploadChapter = ref('')
const uploadVerified = ref(false)
const uploading = ref(false)
const resourceTypeOptions: SelectOption[] = (Object.keys(RESOURCE_TYPE_LABELS) as ResourceType[]).map((k) => ({
  label: RESOURCE_TYPE_LABELS[k],
  value: k,
}))

async function handleUpload({ file, onFinish, onError }: UploadCustomRequestOptions) {
  if (!file.file) {
    onError()
    return
  }
  uploading.value = true
  try {
    const doc = await uploadKnowledgeDocument(file.file, {
      resource_type: uploadResourceType.value,
      chapter: uploadChapter.value.trim() || undefined,
      teacher_verified: uploadVerified.value,
    })
    message.success(`「${doc.title}」已入库，开始索引`)
    onFinish()
    docPage.value = 1
    await Promise.all([loadDocuments(false), loadStatus()])
  } catch (error) {
    message.error((error as Error).message)
    onError()
  } finally {
    uploading.value = false
  }
}

const showTextComposer = ref(false)
const textTitle = ref('')
const textBody = ref('')
const textSubmitting = ref(false)

async function submitTextDocument() {
  if (!textTitle.value.trim() || textBody.value.trim().length < 20) {
    message.warning('标题不能为空，正文至少 20 字')
    return
  }
  textSubmitting.value = true
  try {
    await createKnowledgeTextDocument({
      title: textTitle.value.trim(),
      text: textBody.value,
      resource_type: uploadResourceType.value,
      chapter: uploadChapter.value.trim() || undefined,
      teacher_verified: uploadVerified.value,
    })
    message.success('文本文档已入库')
    showTextComposer.value = false
    textTitle.value = ''
    textBody.value = ''
    docPage.value = 1
    await Promise.all([loadDocuments(false), loadStatus()])
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    textSubmitting.value = false
  }
}

const busyDocIds = ref<Set<string>>(new Set())
function setBusy(id: string, on: boolean) {
  const next = new Set(busyDocIds.value)
  if (on) next.add(id)
  else next.delete(id)
  busyDocIds.value = next
}

async function reindex(doc: KnowledgeDocument) {
  setBusy(doc.id, true)
  try {
    await reindexKnowledgeDocument(doc.id)
    message.success(`已重新排队索引：${doc.title}`)
    await Promise.all([loadDocuments(false), loadStatus()])
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    setBusy(doc.id, false)
  }
}

async function toggleVerified(doc: KnowledgeDocument) {
  setBusy(doc.id, true)
  try {
    const updated = await verifyKnowledgeDocument(doc.id, !doc.teacher_verified)
    documents.value = documents.value.map((d) => (d.id === doc.id ? { ...d, ...updated } : d))
    message.success(updated.teacher_verified ? '已标记为教师审核' : '已取消审核标记')
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    setBusy(doc.id, false)
  }
}

async function removeDocument(doc: KnowledgeDocument) {
  setBusy(doc.id, true)
  try {
    await deleteKnowledgeDocument(doc.id)
    message.success(`已删除「${doc.title}」及其向量`)
    await Promise.all([loadDocuments(false), loadStatus()])
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    setBusy(doc.id, false)
  }
}

// Chunk 抽屉
const chunkDrawer = ref(false)
const chunkDoc = ref<KnowledgeDocument | null>(null)
const chunks = ref<KnowledgeChunk[]>([])
const chunkTotal = ref(0)
const chunkLoading = ref(false)
const expandedChunk = ref<string | null>(null)

async function openChunks(doc: KnowledgeDocument) {
  chunkDoc.value = doc
  chunkDrawer.value = true
  chunkLoading.value = true
  expandedChunk.value = null
  try {
    const result = await fetchKnowledgeChunks(doc.id, { per_page: 200, include_content: true })
    chunks.value = result.items
    chunkTotal.value = result.total
  } catch (error) {
    message.error((error as Error).message)
    chunks.value = []
  } finally {
    chunkLoading.value = false
  }
}

const seeding = ref(false)
async function runSeed() {
  seeding.value = true
  try {
    await seedKnowledge({ seed_graph: true, index_builtin: true })
    message.success('内置知识图谱与课程材料已初始化')
    await Promise.all([loadDocuments(false), loadStatus(), loadGraph()])
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    seeding.value = false
  }
}

// ------------------------------------------------------------------ 图谱
const graph = ref<KnowledgeGraphResult | null>(null)
const graphLoading = ref(false)
const graphNodeTypes = ref<string[]>(['concept', 'skill'])
const graphIncludeMisconceptions = ref(false)

const chapterTitles = computed(() => Object.fromEntries((graph.value?.chapters ?? []).map((c) => [c.key, c.title])))

const kgNodes = computed(() =>
  mapConceptNodes(graph.value?.nodes ?? [], {
    chapterTitles: chapterTitles.value,
    highlightIds: selectedConcept.value ? [selectedConcept.value.concept_id] : [],
  }),
)
const kgEdges = computed(() => mapConceptEdges(graph.value?.edges ?? [], new Set(kgNodes.value.map((n) => n.id))))

async function loadGraph() {
  graphLoading.value = true
  try {
    const types = [...graphNodeTypes.value]
    if (graphIncludeMisconceptions.value) types.push('misconception')
    graph.value = await fetchKnowledgeGraph({ node_types: types.join(',') })
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    graphLoading.value = false
  }
}

watch(graphIncludeMisconceptions, () => void loadGraph())

const selectedConcept = ref<KnowledgeConceptDetail | null>(null)
const conceptLoading = ref(false)

async function onGraphNodeClick(node: KgNode) {
  await selectConcept(node.id)
}

async function selectConcept(conceptId: string) {
  conceptLoading.value = true
  try {
    selectedConcept.value = await fetchKnowledgeConcept(conceptId, true)
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    conceptLoading.value = false
  }
}

const conceptRelations = computed(() => {
  const id = selectedConcept.value?.concept_id
  if (!id || !graph.value) return []
  const names = Object.fromEntries(graph.value.nodes.map((n) => [n.concept_id, n.name]))
  return graph.value.edges
    .filter((e) => e.source === id || e.target === id)
    .map((e) => ({
      ...e,
      sourceName: names[e.source] ?? e.source,
      targetName: names[e.target] ?? e.target,
      label: RELATION_TYPE_LABELS[e.relation_type] ?? e.relation_type,
    }))
})

const relationTypeOptions: SelectOption[] = (Object.keys(RELATION_TYPE_LABELS) as RelationType[]).map((k) => ({
  label: `${RELATION_TYPE_LABELS[k]} (${k})`,
  value: k,
}))
const newRelationTarget = ref<string | null>(null)
const newRelationType = ref<RelationType>('PREREQUISITE_OF')
const newRelationDirection = ref<'out' | 'in'>('out')
const relationSubmitting = ref(false)

const conceptOptions = computed<SelectOption[]>(() =>
  (graph.value?.nodes ?? [])
    .filter((n) => n.concept_id !== selectedConcept.value?.concept_id)
    .map((n) => ({ label: `${n.name} · ${n.concept_id}`, value: n.concept_id })),
)

async function submitRelation() {
  const focus = selectedConcept.value?.concept_id
  if (!focus || !newRelationTarget.value) return
  relationSubmitting.value = true
  try {
    const payload =
      newRelationDirection.value === 'out'
        ? { source_id: focus, target_id: newRelationTarget.value }
        : { source_id: newRelationTarget.value, target_id: focus }
    await addKnowledgeRelation({ ...payload, relation_type: newRelationType.value, teacher_verified: true })
    message.success('关系已添加')
    newRelationTarget.value = null
    await loadGraph()
    await selectConcept(focus)
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    relationSubmitting.value = false
  }
}

async function toggleRelationVerified(relationId: number, verified: boolean) {
  try {
    await verifyKnowledgeRelation(relationId, verified)
    await loadGraph()
  } catch (error) {
    message.error((error as Error).message)
  }
}

async function removeRelation(relationId: number) {
  try {
    await deleteKnowledgeRelation(relationId)
    message.success('关系已删除')
    await loadGraph()
    if (selectedConcept.value) await selectConcept(selectedConcept.value.concept_id)
  } catch (error) {
    message.error((error as Error).message)
  }
}

// ------------------------------------------------------------------ 分析
const analytics = ref<KnowledgeAnalyticsOverview | null>(null)
const analyticsLoading = ref(false)
const analyticsDays = ref(14)
const analyticsDayOptions: SelectOption[] = [
  { label: '近 7 天', value: 7 },
  { label: '近 14 天', value: 14 },
  { label: '近 30 天', value: 30 },
]

async function loadAnalytics() {
  analyticsLoading.value = true
  try {
    analytics.value = await fetchKnowledgeAnalytics({ days: analyticsDays.value, limit: 10 })
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    analyticsLoading.value = false
  }
}

watch(analyticsDays, () => void loadAnalytics())

function percent(value: number) {
  return `${Math.round(value * 100)}%`
}

function sortedEntries(record: Record<string, number> | undefined) {
  return Object.entries(record ?? {}).sort((a, b) => b[1] - a[1])
}

// ------------------------------------------------------------------ 生命周期
watch(activeTab, (tab) => {
  if (tab === 'graph' && !graph.value) void loadGraph()
  if (tab === 'analytics' && !analytics.value) void loadAnalytics()
})

onMounted(() => {
  void loadStatus()
  void loadDocuments()
  startPolling()
})

onBeforeUnmount(stopPolling)

function fmtTime(value: string | null | undefined) {
  if (!value) return '—'
  return value.slice(0, 16).replace('T', ' ')
}

function fmtSize(bytes: number) {
  if (!bytes) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
</script>

<template>
  <section class="knowledge-admin" aria-label="知识智能层">
    <nav class="ki-tabs" role="tablist">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        role="tab"
        class="ki-tab"
        :class="{ active: activeTab === tab.key }"
        :aria-selected="activeTab === tab.key"
        @click="activeTab = tab.key"
      >
        <n-icon :component="tab.icon" />
        <span>{{ tab.label }}</span>
      </button>
    </nav>

    <!-- ============================== 知识库与索引 -->
    <div v-if="activeTab === 'documents'" class="ki-grid ki-grid--docs">
      <article class="panel">
        <header class="section-head section-head--row">
          <n-icon :component="LayersOutline" />
          <div>
            <h2>索引状态</h2>
            <p>Vector DB 与 MySQL 元数据分离；状态机 PENDING → PARSING → CHUNKING → EMBEDDING → INDEXING → READY。</p>
          </div>
          <n-button quaternary size="small" :loading="statusLoading" @click="loadStatus"><n-icon :component="RefreshOutline" /></n-button>
        </header>
        <n-spin :show="statusLoading && !indexStatus">
          <div v-if="indexStatus" class="status-grid">
            <div class="status-card">
              <small>知识文档</small>
              <strong>{{ indexStatus.document_total }}</strong>
              <em>READY {{ indexStatus.documents.READY ?? 0 }} · FAILED {{ indexStatus.documents.FAILED ?? 0 }}</em>
            </div>
            <div class="status-card">
              <small>Chunk / 已向量化</small>
              <strong>{{ indexStatus.chunk_embedded }}<span class="dim"> / {{ indexStatus.chunk_total }}</span></strong>
              <n-progress type="line" :percentage="embeddedRate" :show-indicator="false" :height="6" color="#a78bfa" rail-color="rgba(148,163,184,.18)" />
            </div>
            <div class="status-card">
              <small>知识点节点</small>
              <strong>{{ indexStatus.concept_total }}</strong>
              <em>{{ indexStatus.ready ? '知识层就绪' : '知识层未就绪' }}</em>
            </div>
            <div class="status-card">
              <small>向量库</small>
              <strong class="mono">{{ indexStatus.vector.backend }}</strong>
              <em>{{ indexStatus.vector.count }} 向量 · {{ indexStatus.vector.embedding?.provider ?? '—' }} / {{ indexStatus.vector.embedding?.model ?? '—' }}</em>
            </div>
          </div>
          <div v-if="indexStatus?.running_jobs.length" class="job-list">
            <h3>进行中的索引任务</h3>
            <div v-for="job in indexStatus.running_jobs" :key="job.id" class="job-row">
              <n-tag size="small" type="warning" :bordered="false">{{ INDEX_STATUS_LABELS[job.status] }}</n-tag>
              <span class="mono">{{ job.document_id.slice(0, 8) }}</span>
              <n-progress type="line" :percentage="Math.round(job.progress * 100)" :show-indicator="false" :height="6" color="#38bdf8" rail-color="rgba(148,163,184,.18)" />
              <em>{{ job.embedded_count }}/{{ job.chunk_count }} chunk</em>
            </div>
          </div>
          <div v-if="indexStatus?.recent_failed.length" class="job-list job-list--failed">
            <h3>最近失败</h3>
            <div v-for="job in indexStatus.recent_failed" :key="job.id" class="job-row job-row--failed">
              <n-tag size="small" type="error" :bordered="false">FAILED</n-tag>
              <span class="mono">{{ job.document_id.slice(0, 8) }}</span>
              <em class="ellipsis" :title="job.error_message ?? ''">{{ job.error_message || '未知错误' }}</em>
            </div>
          </div>
          <footer class="status-actions">
            <n-button size="small" secondary :loading="seeding" @click="runSeed">初始化内置图谱与课程材料</n-button>
            <em>{{ indexStatus?.async_mode ? '异步索引 · 后台线程运行' : '同步索引' }}</em>
          </footer>
        </n-spin>
      </article>

      <article class="panel">
        <header class="section-head">
          <n-icon :component="CloudUploadOutline" />
          <div>
            <h2>导入知识文档</h2>
            <p>支持 Markdown / TXT / PDF / Word / PPTX。入库后按语义切块、映射知识点并向量化。</p>
          </div>
        </header>
        <div class="upload-meta">
          <label><span>资源类型</span><n-select v-model:value="uploadResourceType" :options="resourceTypeOptions" size="small" /></label>
          <label><span>章节 · 可留空</span><n-input v-model:value="uploadChapter" size="small" placeholder="如 循环结构" /></label>
          <label class="switch-field"><span>教师已审核</span><n-switch v-model:value="uploadVerified" size="small" /></label>
        </div>
        <n-upload
          :custom-request="handleUpload"
          :show-file-list="false"
          accept=".md,.markdown,.txt,.pdf,.doc,.docx,.pptx"
          multiple
          :disabled="uploading"
        >
          <n-upload-dragger class="upload-dragger">
            <n-icon :component="CloudUploadOutline" size="28" />
            <p>{{ uploading ? '上传中…' : '拖拽文件到此处，或点击选择' }}</p>
            <small>单文件 ≤ 100 MB · 重复内容将自动版本化并替换旧向量</small>
          </n-upload-dragger>
        </n-upload>
        <n-button text size="small" class="text-composer-toggle" @click="showTextComposer = !showTextComposer">
          {{ showTextComposer ? '收起' : '直接粘贴文本入库' }}
        </n-button>
        <div v-if="showTextComposer" class="text-composer">
          <n-input v-model:value="textTitle" size="small" placeholder="文档标题" />
          <n-input v-model:value="textBody" type="textarea" :autosize="{ minRows: 5, maxRows: 12 }" placeholder="粘贴 Markdown / 文本正文" />
          <n-button size="small" type="primary" :loading="textSubmitting" @click="submitTextDocument">入库并索引</n-button>
        </div>
      </article>

      <article class="panel panel--wide">
        <header class="section-head section-head--row">
          <n-icon :component="DocumentTextOutline" />
          <div>
            <h2>知识库文档</h2>
            <p>共 {{ docTotal }} 篇 · 点击「Chunk」查看切块与 Embedding 状态。</p>
          </div>
          <div class="doc-filters">
            <n-input v-model:value="docKeyword" size="small" clearable placeholder="搜索标题" @keyup.enter="docPage = 1; loadDocuments()" @clear="docPage = 1; loadDocuments()" />
            <n-select v-model:value="docStatusFilter" :options="statusFilterOptions" size="small" class="status-select" />
            <n-button quaternary size="small" :loading="docLoading" @click="loadDocuments()"><n-icon :component="RefreshOutline" /></n-button>
          </div>
        </header>
        <n-spin :show="docLoading">
          <n-empty v-if="!documents.length && !docLoading" description="暂无知识文档，先上传或初始化内置材料" />
          <ul v-else class="doc-list">
            <li v-for="doc in documents" :key="doc.id" class="doc-row">
              <div class="doc-main">
                <strong :title="doc.title">{{ doc.title }}</strong>
                <small>
                  {{ RESOURCE_TYPE_LABELS[doc.resource_type] ?? doc.resource_type }} · v{{ doc.version }} · {{ fmtSize(doc.file_size) }}
                  <template v-if="doc.chapter"> · {{ doc.chapter }}</template>
                  · {{ doc.source }}
                </small>
                <small v-if="doc.status === 'FAILED' && doc.error_message" class="doc-error">{{ doc.error_message }}</small>
              </div>
              <div class="doc-status">
                <n-tag size="small" :type="statusTone(doc.status)" :bordered="false">{{ INDEX_STATUS_LABELS[doc.status] }}</n-tag>
                <n-progress
                  v-if="RUNNING_INDEX_STATUSES.includes(doc.status)"
                  type="line"
                  :percentage="Math.round(doc.stage_progress * 100)"
                  :show-indicator="false"
                  :height="4"
                  color="#38bdf8"
                  rail-color="rgba(148,163,184,.18)"
                />
                <em v-else>{{ doc.chunk_count }} chunk · {{ fmtTime(doc.indexed_at ?? doc.updated_at) }}</em>
              </div>
              <div class="doc-flags">
                <n-tag v-if="doc.teacher_verified" size="small" type="success" :bordered="false">教师审核</n-tag>
                <n-tag v-if="doc.concept_ids.length" size="small" :bordered="false">{{ doc.concept_ids.length }} 知识点</n-tag>
              </div>
              <div class="doc-actions">
                <n-button text size="small" :disabled="busyDocIds.has(doc.id)" @click="openChunks(doc)">Chunk</n-button>
                <n-button text size="small" :loading="busyDocIds.has(doc.id)" @click="toggleVerified(doc)">{{ doc.teacher_verified ? '取消审核' : '标记审核' }}</n-button>
                <n-button text size="small" :loading="busyDocIds.has(doc.id)" :disabled="RUNNING_INDEX_STATUSES.includes(doc.status)" @click="reindex(doc)">重索引</n-button>
                <n-popconfirm @positive-click="removeDocument(doc)">
                  <template #trigger>
                    <n-button text size="small" type="error" :loading="busyDocIds.has(doc.id)"><n-icon :component="TrashOutline" /></n-button>
                  </template>
                  删除文档及其全部 Chunk 与向量？
                </n-popconfirm>
              </div>
            </li>
          </ul>
        </n-spin>
        <footer v-if="docPages > 1" class="pager">
          <n-button size="tiny" quaternary :disabled="docPage <= 1" @click="docPage--; loadDocuments()">上一页</n-button>
          <span>{{ docPage }} / {{ docPages }}</span>
          <n-button size="tiny" quaternary :disabled="docPage >= docPages" @click="docPage++; loadDocuments()">下一页</n-button>
        </footer>
      </article>
    </div>

    <!-- ============================== 知识星域 -->
    <div v-else-if="activeTab === 'graph'" class="ki-grid ki-grid--graph">
      <article class="panel panel--graph">
        <header class="section-head section-head--row">
          <n-icon :component="GitNetworkOutline" />
          <div>
            <h2>知识星域 · Knowledge Universe</h2>
            <p>{{ graph?.stats.node_count ?? 0 }} 节点 · {{ graph?.stats.edge_count ?? 0 }} 关系。点击节点查看前置、误区与关联材料。</p>
          </div>
          <div class="graph-tools">
            <label class="switch-field"><span>显示误区节点</span><n-switch v-model:value="graphIncludeMisconceptions" size="small" /></label>
            <n-button quaternary size="small" :loading="graphLoading" @click="loadGraph"><n-icon :component="RefreshOutline" /></n-button>
          </div>
        </header>
        <n-spin :show="graphLoading">
          <PlexKnowledgeGraph v-if="kgNodes.length" :nodes="kgNodes" :edges="kgEdges" mode="admin" height="560px" @node-click="onGraphNodeClick" />
          <n-empty v-else-if="!graphLoading" description="尚无图谱数据，请先在「知识库与索引」初始化内置图谱" />
        </n-spin>
      </article>

      <article class="panel panel--concept">
        <header class="section-head">
          <n-icon :component="SparklesOutline" />
          <div>
            <h2>{{ selectedConcept ? selectedConcept.name : '知识点详情' }}</h2>
            <p v-if="selectedConcept" class="mono">{{ selectedConcept.concept_id }} · {{ selectedConcept.node_type }} · 难度 {{ selectedConcept.difficulty }} · 阈值 {{ selectedConcept.mastery_threshold }}</p>
            <p v-else>在星域中点击一个节点</p>
          </div>
        </header>
        <n-spin :show="conceptLoading">
          <template v-if="selectedConcept">
            <p class="concept-desc">{{ selectedConcept.description || '暂无描述' }}</p>
            <div v-if="selectedConcept.usage" class="usage-strip">
              <span>近 14 天提问 <strong>{{ selectedConcept.usage.queries }}</strong></span>
              <span>学生 <strong>{{ selectedConcept.usage.students }}</strong></span>
              <span>低置信 <strong>{{ selectedConcept.usage.low_confidence }}</strong></span>
            </div>
            <section class="concept-block">
              <h3>前置知识</h3>
              <div class="chip-row">
                <button v-for="n in selectedConcept.prerequisite_nodes" :key="n.concept_id" type="button" class="chip" @click="selectConcept(n.concept_id)">{{ n.name }}</button>
                <em v-if="!selectedConcept.prerequisite_nodes.length">无</em>
              </div>
            </section>
            <section class="concept-block">
              <h3>常见误区</h3>
              <ul class="plain-list">
                <li v-for="m in selectedConcept.misconception_nodes" :key="m.concept_id"><strong>{{ m.name }}</strong><small>{{ m.description }}</small></li>
                <li v-for="(m, i) in selectedConcept.common_misconceptions" :key="`cm-${i}`"><small>{{ m }}</small></li>
                <li v-if="!selectedConcept.misconception_nodes.length && !selectedConcept.common_misconceptions.length"><em>无</em></li>
              </ul>
            </section>
            <section class="concept-block">
              <h3>推荐后续</h3>
              <div class="chip-row">
                <button v-for="n in selectedConcept.next_nodes" :key="n.concept_id" type="button" class="chip" @click="selectConcept(n.concept_id)">{{ n.name }}</button>
                <em v-if="!selectedConcept.next_nodes.length">无</em>
              </div>
            </section>
            <section class="concept-block">
              <h3>关系（{{ conceptRelations.length }}）</h3>
              <ul class="relation-list">
                <li v-for="rel in conceptRelations" :key="rel.id">
                  <span class="rel-text">{{ rel.sourceName }} <i>{{ rel.label }}</i> {{ rel.targetName }}</span>
                  <n-tag size="tiny" :bordered="false" :type="rel.teacher_verified ? 'success' : 'default'">{{ rel.teacher_verified ? '已审' : rel.origin }}</n-tag>
                  <n-button text size="tiny" @click="toggleRelationVerified(rel.id, !rel.teacher_verified)">{{ rel.teacher_verified ? '撤销' : '审核' }}</n-button>
                  <n-popconfirm @positive-click="removeRelation(rel.id)">
                    <template #trigger><n-button text size="tiny" type="error">删除</n-button></template>
                    删除该关系？
                  </n-popconfirm>
                </li>
              </ul>
              <div class="relation-form">
                <n-select v-model:value="newRelationDirection" size="small" :options="[{ label: '当前 →', value: 'out' }, { label: '→ 当前', value: 'in' }]" class="dir-select" />
                <n-select v-model:value="newRelationType" size="small" :options="relationTypeOptions" />
                <n-select v-model:value="newRelationTarget" size="small" filterable clearable placeholder="选择另一个知识点" :options="conceptOptions" />
                <n-button size="small" type="primary" :loading="relationSubmitting" :disabled="!newRelationTarget" @click="submitRelation">添加关系</n-button>
              </div>
            </section>
          </template>
        </n-spin>
      </article>
    </div>

    <!-- ============================== 检索测试与诊断 -->
    <AdminRagDebugPanel v-else-if="activeTab === 'debug'" />

    <!-- ============================== 使用分析 -->
    <div v-else class="ki-grid ki-grid--analytics">
      <article class="panel panel--wide">
        <header class="section-head section-head--row">
          <n-icon :component="PulseOutline" />
          <div>
            <h2>知识使用分析</h2>
            <p>基于 RAG 请求日志（查询已脱敏，仅保留摘要与哈希）。</p>
          </div>
          <div class="graph-tools">
            <n-select v-model:value="analyticsDays" :options="analyticsDayOptions" size="small" class="status-select" />
            <n-button quaternary size="small" :loading="analyticsLoading" @click="loadAnalytics"><n-icon :component="RefreshOutline" /></n-button>
          </div>
        </header>
        <n-spin :show="analyticsLoading">
          <div v-if="analytics" class="status-grid">
            <div class="status-card"><small>请求总数</small><strong>{{ analytics.total_queries }}</strong></div>
            <div class="status-card"><small>提问学生</small><strong>{{ analytics.unique_students }}</strong></div>
            <div class="status-card"><small>知识锚定率</small><strong>{{ percent(analytics.grounded_rate) }}</strong></div>
            <div class="status-card"><small>平均延迟</small><strong>{{ analytics.avg_latency_ms }}<span class="dim"> ms</span></strong></div>
          </div>
        </n-spin>
      </article>

      <article class="panel">
        <header class="section-head"><n-icon :component="SparklesOutline" /><div><h2>高频问题</h2><p>相同语义的问题聚合后的热度。</p></div></header>
        <ul class="rank-list">
          <li v-for="(q, i) in analytics?.hot_queries ?? []" :key="i">
            <span class="rank">{{ i + 1 }}</span>
            <div><strong>{{ q.preview }}</strong><small>{{ q.concepts.join(' · ') || '未识别知识点' }}</small></div>
            <em>{{ q.count }} 次 · {{ q.students }} 人</em>
          </li>
          <li v-if="analytics && !analytics.hot_queries.length"><em>暂无数据</em></li>
        </ul>
      </article>

      <article class="panel">
        <header class="section-head"><n-icon :component="GitNetworkOutline" /><div><h2>薄弱知识点</h2><p>被提问最多且低置信比例高的知识点。</p></div></header>
        <ul class="rank-list">
          <li v-for="(c, i) in analytics?.weak_concepts ?? []" :key="c.concept_id">
            <span class="rank">{{ i + 1 }}</span>
            <div><strong>{{ c.name }}</strong><small class="mono">{{ c.concept_id }}</small></div>
            <em>{{ c.queries }} 问 · {{ c.students }} 人 · 低置信 {{ c.low_confidence }}</em>
          </li>
          <li v-if="analytics && !analytics.weak_concepts.length"><em>暂无数据</em></li>
        </ul>
      </article>

      <article class="panel">
        <header class="section-head"><n-icon :component="LayersOutline" /><div><h2>意图 / 策略 / 置信度分布</h2></div></header>
        <div class="dist-grid">
          <div>
            <h3>意图</h3>
            <p v-for="[k, v] in sortedEntries(analytics?.intents)" :key="k"><span>{{ k }}</span><strong>{{ v }}</strong></p>
          </div>
          <div>
            <h3>教学策略</h3>
            <p v-for="[k, v] in sortedEntries(analytics?.strategies)" :key="k"><span>{{ k }}</span><strong>{{ v }}</strong></p>
          </div>
          <div>
            <h3>置信度</h3>
            <p v-for="[k, v] in sortedEntries(analytics?.confidence_levels)" :key="k"><span>{{ k }}</span><strong>{{ v }}</strong></p>
          </div>
        </div>
      </article>
    </div>

    <!-- Chunk 抽屉 -->
    <n-drawer v-model:show="chunkDrawer" :width="640" placement="right">
      <n-drawer-content :title="chunkDoc ? `Chunk · ${chunkDoc.title}` : 'Chunk'" closable>
        <n-spin :show="chunkLoading">
          <p class="drawer-meta" v-if="chunkDoc">
            {{ chunkTotal }} 个 Chunk · v{{ chunkDoc.version }} · {{ INDEX_STATUS_LABELS[chunkDoc.status] }}
          </p>
          <n-empty v-if="!chunks.length && !chunkLoading" description="暂无 Chunk" />
          <ul class="chunk-list">
            <li v-for="c in chunks" :key="c.chunk_id" class="chunk-item" :class="{ open: expandedChunk === c.chunk_id }">
              <header @click="expandedChunk = expandedChunk === c.chunk_id ? null : c.chunk_id">
                <span class="seq">#{{ c.sequence + 1 }}</span>
                <strong>{{ c.title || '（无标题）' }}</strong>
                <n-tag size="tiny" :bordered="false">{{ KNOWLEDGE_TYPE_LABELS[c.knowledge_type] ?? c.knowledge_type }}</n-tag>
                <n-tag size="tiny" :bordered="false" :type="c.embedding_status === 'READY' ? 'success' : 'warning'">{{ c.embedding_status }}</n-tag>
                <em>{{ c.token_count }} tok</em>
              </header>
              <div class="chunk-meta">
                <span v-for="cid in c.concept_ids" :key="cid" class="chip chip--static">{{ cid }}</span>
                <span v-if="c.embedding_model" class="mono dim">{{ c.embedding_model }}</span>
                <span v-if="c.teacher_verified" class="dim">· 教师审核</span>
              </div>
              <pre v-if="expandedChunk === c.chunk_id" class="chunk-content">{{ c.content }}</pre>
            </li>
          </ul>
        </n-spin>
      </n-drawer-content>
    </n-drawer>
  </section>
</template>

<style scoped>
.knowledge-admin {
  --ki-title: 1.02rem;
  --ki-body: 0.82rem;
  --ki-meta: 0.72rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1.05rem;
  min-width: 0;
}

.ki-tabs {
  display: flex;
  gap: 0.4rem;
  padding: 0.3rem;
  border-radius: 10px;
  border: 1px solid rgba(167, 139, 250, 0.14);
  background: linear-gradient(145deg, rgba(19, 20, 43, 0.7), rgba(8, 11, 26, 0.6));
  width: fit-content;
}

.ki-tab {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.45rem 0.9rem;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: rgba(226, 232, 240, 0.7);
  font-size: var(--ki-body);
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}

.ki-tab:hover { color: #fff; background: rgba(139, 92, 246, 0.12); }
.ki-tab.active {
  color: #fff;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.32), rgba(56, 189, 248, 0.2));
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.08);
}

.ki-grid { display: grid; gap: 1rem; min-width: 0; }
.ki-grid--docs { grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr); }
.ki-grid--graph { grid-template-columns: minmax(0, 1.55fr) minmax(320px, 0.85fr); }
.ki-grid--analytics { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.panel--wide { grid-column: 1 / -1; }

.panel {
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 9px;
  background:
    radial-gradient(circle at 50% 0%, rgba(139, 92, 246, 0.11), transparent 42%),
    linear-gradient(145deg, rgba(19, 20, 43, 0.88), rgba(8, 11, 26, 0.82));
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.04), 0 18px 50px rgba(0, 0, 0, 0.22);
  min-width: 0;
  padding: 1.15rem 1.25rem;
}

.section-head {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 0.65rem;
  align-items: start;
  margin-bottom: 1rem;
  color: #c4b5fd;
}
.section-head--row { grid-template-columns: 28px minmax(0, 1fr) auto; align-items: center; }
.section-head > .n-icon { font-size: 1.25rem; }
.section-head h2 { margin: 0; color: #fff; font-size: var(--ki-title); }
.section-head p { margin: 0.3rem 0 0; color: rgba(226, 232, 240, 0.58); font-size: 0.76rem; line-height: 1.45; }

.status-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.65rem; }
.ki-grid--docs .status-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.status-card {
  display: grid;
  gap: 0.25rem;
  padding: 0.75rem 0.85rem;
  border-radius: 8px;
  background: rgba(129, 140, 248, 0.08);
  border: 1px solid rgba(129, 140, 248, 0.15);
}
.status-card small { color: rgba(226, 232, 240, 0.55); font-size: var(--ki-meta); }
.status-card strong { color: #fff; font-size: 1.25rem; font-weight: 600; }
.status-card em { color: #a5b4fc; font-style: normal; font-size: var(--ki-meta); }
.dim { color: rgba(226, 232, 240, 0.45); font-weight: 400; font-size: 0.85em; }
.mono { font-family: 'JetBrains Mono', Consolas, monospace; font-size: 0.9em; }

.job-list { margin-top: 0.9rem; }
.job-list h3 { margin: 0 0 0.4rem; font-size: 0.78rem; color: #c4b5fd; font-weight: 600; }
.job-row {
  display: grid;
  grid-template-columns: auto 72px minmax(0, 1fr) auto;
  gap: 0.6rem;
  align-items: center;
  padding: 0.35rem 0;
  font-size: var(--ki-meta);
  color: rgba(226, 232, 240, 0.7);
}
.job-row--failed { grid-template-columns: auto 72px minmax(0, 1fr); }
.job-row em { font-style: normal; }
.ellipsis { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.status-actions { display: flex; align-items: center; justify-content: space-between; margin-top: 0.9rem; }
.status-actions em { color: rgba(226, 232, 240, 0.5); font-style: normal; font-size: var(--ki-meta); }

.upload-meta { display: grid; grid-template-columns: 1fr 1fr auto; gap: 0.6rem; margin-bottom: 0.75rem; align-items: end; }
.upload-meta label { display: grid; gap: 0.25rem; font-size: var(--ki-meta); color: rgba(226, 232, 240, 0.6); }
.switch-field { display: inline-flex !important; align-items: center; gap: 0.45rem; }
.upload-dragger { background: rgba(139, 92, 246, 0.06) !important; border-color: rgba(167, 139, 250, 0.3) !important; text-align: center; }
.upload-dragger p { margin: 0.4rem 0 0.15rem; color: #fff; font-size: var(--ki-body); }
.upload-dragger small { color: rgba(226, 232, 240, 0.5); font-size: var(--ki-meta); }
.text-composer-toggle { margin-top: 0.5rem; }
.text-composer { display: grid; gap: 0.5rem; margin-top: 0.5rem; }

.doc-filters { display: flex; gap: 0.45rem; align-items: center; }
.doc-filters .n-input { width: 180px; }
.status-select { width: 130px; }
.doc-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.45rem; }
.doc-row {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(140px, 0.9fr) auto auto;
  gap: 0.85rem;
  align-items: center;
  padding: 0.6rem 0.8rem;
  border-radius: 8px;
  background: rgba(129, 140, 248, 0.07);
  border: 1px solid rgba(129, 140, 248, 0.14);
  font-size: var(--ki-body);
}
.doc-main { display: grid; gap: 0.15rem; min-width: 0; }
.doc-main strong { color: rgba(255, 255, 255, 0.92); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.doc-main small { color: rgba(226, 232, 240, 0.55); font-size: var(--ki-meta); }
.doc-error { color: #fda4af !important; }
.doc-status { display: grid; gap: 0.3rem; }
.doc-status em { color: rgba(226, 232, 240, 0.5); font-style: normal; font-size: var(--ki-meta); }
.doc-flags { display: flex; gap: 0.3rem; flex-wrap: wrap; }
.doc-actions { display: flex; gap: 0.35rem; align-items: center; white-space: nowrap; }
.pager { display: flex; justify-content: center; align-items: center; gap: 0.75rem; margin-top: 0.75rem; color: rgba(226, 232, 240, 0.6); font-size: var(--ki-meta); }

.graph-tools { display: flex; gap: 0.6rem; align-items: center; color: rgba(226, 232, 240, 0.65); font-size: var(--ki-meta); }
.panel--concept { max-height: 680px; overflow: auto; }
.concept-desc { margin: 0 0 0.7rem; color: rgba(226, 232, 240, 0.78); font-size: var(--ki-body); line-height: 1.55; }
.usage-strip { display: flex; gap: 1rem; margin-bottom: 0.7rem; font-size: var(--ki-meta); color: rgba(226, 232, 240, 0.6); }
.usage-strip strong { color: #fff; margin-left: 0.2rem; }
.concept-block { margin-top: 0.8rem; }
.concept-block h3 { margin: 0 0 0.4rem; font-size: 0.78rem; color: #c4b5fd; font-weight: 600; }
.chip-row { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.chip {
  border: 1px solid rgba(129, 140, 248, 0.3);
  border-radius: 999px;
  padding: 0.2rem 0.6rem;
  background: rgba(129, 140, 248, 0.12);
  color: #c7d2fe;
  font-size: var(--ki-meta);
  cursor: pointer;
}
.chip:hover { background: rgba(129, 140, 248, 0.22); color: #fff; }
.chip--static { cursor: default; }
.chip-row em, .plain-list em { color: rgba(226, 232, 240, 0.45); font-style: normal; font-size: var(--ki-meta); }
.plain-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.35rem; }
.plain-list li { display: grid; gap: 0.1rem; font-size: var(--ki-body); }
.plain-list strong { color: #fecdd3; }
.plain-list small { color: rgba(226, 232, 240, 0.6); font-size: var(--ki-meta); }
.relation-list { list-style: none; margin: 0 0 0.6rem; padding: 0; display: grid; gap: 0.3rem; }
.relation-list li { display: grid; grid-template-columns: minmax(0, 1fr) auto auto auto; gap: 0.45rem; align-items: center; font-size: var(--ki-meta); color: rgba(226, 232, 240, 0.75); }
.rel-text i { color: #a5b4fc; font-style: normal; margin: 0 0.25rem; }
.relation-form { display: grid; grid-template-columns: 90px 1fr; gap: 0.4rem; }
.relation-form > :nth-child(3) { grid-column: 1 / -1; }
.relation-form > :nth-child(4) { grid-column: 1 / -1; }

.rank-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.45rem; }
.rank-list li { display: grid; grid-template-columns: 24px minmax(0, 1fr) auto; gap: 0.6rem; align-items: center; font-size: var(--ki-body); }
.rank-list .rank { display: inline-grid; place-items: center; width: 22px; height: 22px; border-radius: 6px; background: rgba(139, 92, 246, 0.2); color: #c4b5fd; font-size: var(--ki-meta); }
.rank-list strong { display: block; color: rgba(255, 255, 255, 0.9); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rank-list small { color: rgba(226, 232, 240, 0.5); font-size: var(--ki-meta); }
.rank-list em { color: #a5b4fc; font-style: normal; font-size: var(--ki-meta); white-space: nowrap; }
.dist-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.75rem; }
.dist-grid h3 { margin: 0 0 0.35rem; font-size: 0.76rem; color: #c4b5fd; }
.dist-grid p { display: flex; justify-content: space-between; margin: 0.15rem 0; font-size: var(--ki-meta); color: rgba(226, 232, 240, 0.65); }
.dist-grid strong { color: #fff; }

.drawer-meta { margin: 0 0 0.6rem; color: rgba(226, 232, 240, 0.6); font-size: var(--ki-meta); }
.chunk-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.45rem; }
.chunk-item { border: 1px solid rgba(129, 140, 248, 0.16); border-radius: 8px; padding: 0.55rem 0.7rem; background: rgba(129, 140, 248, 0.06); }
.chunk-item header { display: flex; gap: 0.45rem; align-items: center; cursor: pointer; font-size: var(--ki-body); }
.chunk-item header strong { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chunk-item header em { color: rgba(226, 232, 240, 0.5); font-style: normal; font-size: var(--ki-meta); }
.seq { color: #a5b4fc; font-size: var(--ki-meta); }
.chunk-meta { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-top: 0.35rem; font-size: var(--ki-meta); }
.chunk-content { margin: 0.5rem 0 0; padding: 0.6rem; border-radius: 6px; background: rgba(5, 14, 26, 0.6); color: rgba(226, 232, 240, 0.85); font-size: 0.76rem; line-height: 1.5; white-space: pre-wrap; word-break: break-word; max-height: 360px; overflow: auto; }

@media (max-width: 1280px) {
  .ki-grid--docs, .ki-grid--graph { grid-template-columns: 1fr; }
  .ki-grid--analytics { grid-template-columns: 1fr 1fr; }
  .status-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .doc-row { grid-template-columns: 1fr; }
}
</style>
