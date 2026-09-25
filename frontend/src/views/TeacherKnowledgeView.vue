<script setup lang="ts">
/**
 * 教师 · 知识星域：查看知识图谱与前置关系、AI 正在使用的教学资源、
 * 审核资源（teacher_verified 提升检索权重）、修正知识点关联、查看学生高频问题与薄弱知识点。
 */
import { computed, onMounted, ref, watch } from 'vue'
import {
  NButton,
  NEmpty,
  NIcon,
  NPopconfirm,
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
import { CloudUploadOutline, GitNetworkOutline, LibraryOutline, PulseOutline, SparklesOutline } from '@vicons/ionicons5'
import TeacherDashboardShell from '../components/layout/TeacherDashboardShell.vue'
import PlexKnowledgeGraph from '../components/shared/PlexKnowledgeGraph.vue'
import { useTeacherOverviewInjected } from '../composables/useTeacherOverview'
import type { KgNode, KgNodeStatus } from '../data/knowledgeGraphData'
import {
  KNOWLEDGE_TYPE_LABELS,
  RELATION_TYPE_LABELS,
  addKnowledgeRelation,
  deleteKnowledgeRelation,
  fetchConceptKnowledge,
  fetchKnowledgeAnalytics,
  fetchKnowledgeConcept,
  fetchKnowledgeGraph,
  uploadKnowledgeDocument,
  verifyKnowledgeDocument,
  verifyKnowledgeRelation,
  type ConceptKnowledgeResult,
  type KnowledgeAnalyticsOverview,
  type KnowledgeConceptDetail,
  type KnowledgeGraphResult,
  type RelationType,
} from '../api/knowledge'
import { mapConceptEdges, mapConceptNodes } from '../utils/knowledgeGraphMap'

defineOptions({ name: 'TeacherKnowledgeView' })

const message = useMessage()
const overview = useTeacherOverviewInjected()

// ------------------------------------------------------------------ 图谱
const graph = ref<KnowledgeGraphResult | null>(null)
const graphLoading = ref(false)
const showMisconceptions = ref(false)
const selected = ref<KnowledgeConceptDetail | null>(null)
const detailLoading = ref(false)

const chapterTitles = computed(() => Object.fromEntries((graph.value?.chapters ?? []).map((c) => [c.key, c.title])))
const weakIds = computed(() => new Set((analytics.value?.weak_concepts ?? []).map((c) => c.concept_id)))

const kgNodes = computed(() =>
  mapConceptNodes(graph.value?.nodes ?? [], {
    chapterTitles: chapterTitles.value,
    highlightIds: selected.value ? [selected.value.concept_id] : [],
    statusOf: (node): KgNodeStatus => {
      if (node.node_type === 'misconception') return 'weak'
      if (weakIds.value.has(node.concept_id)) return 'weak'
      return 'unlearned'
    },
  }).map((node) => {
    const weak = analytics.value?.weak_concepts.find((c) => c.concept_id === node.id)
    return weak ? { ...node, weak_score: Math.min(120, weak.queries * 10 + weak.low_confidence * 15), affected_student_count: weak.students } : node
  }),
)
const kgEdges = computed(() => mapConceptEdges(graph.value?.edges ?? [], new Set(kgNodes.value.map((n) => n.id))))

async function loadGraph() {
  graphLoading.value = true
  try {
    const types = ['concept', 'skill']
    if (showMisconceptions.value) types.push('misconception')
    graph.value = await fetchKnowledgeGraph({ node_types: types.join(',') })
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    graphLoading.value = false
  }
}
watch(showMisconceptions, () => void loadGraph())

async function selectConcept(conceptId: string) {
  detailLoading.value = true
  materials.value = null
  try {
    selected.value = await fetchKnowledgeConcept(conceptId, true)
    void loadMaterials(conceptId)
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    detailLoading.value = false
  }
}

function onNodeClick(node: KgNode) {
  void selectConcept(node.id)
}

// ------------------------------------------------------------------ AI 使用的资源
const materials = ref<ConceptKnowledgeResult | null>(null)
const materialsLoading = ref(false)
const verifyingDoc = ref<string | null>(null)
const expandedChunk = ref<string | null>(null)

async function loadMaterials(conceptId: string) {
  materialsLoading.value = true
  try {
    materials.value = await fetchConceptKnowledge(conceptId, { top_k: 6 })
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    materialsLoading.value = false
  }
}

async function verifyDocument(documentId: string, verified: boolean) {
  verifyingDoc.value = documentId
  try {
    await verifyKnowledgeDocument(documentId, verified)
    message.success(verified ? '已标记为教师审核，检索时将优先采用' : '已取消审核标记')
    if (selected.value) await loadMaterials(selected.value.concept_id)
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    verifyingDoc.value = null
  }
}

// ------------------------------------------------------------------ 关系修正
const relationTypeOptions: SelectOption[] = (['PREREQUISITE_OF', 'RELATED_TO', 'NEXT_RECOMMENDED', 'MISCONCEPTION_OF', 'REMEDIATES', 'PART_OF'] as RelationType[]).map((k) => ({
  label: RELATION_TYPE_LABELS[k],
  value: k,
}))
const newRelTarget = ref<string | null>(null)
const newRelType = ref<RelationType>('PREREQUISITE_OF')
const newRelDirection = ref<'in' | 'out'>('in')
const relSubmitting = ref(false)

const conceptOptions = computed<SelectOption[]>(() =>
  (graph.value?.nodes ?? [])
    .filter((n) => n.concept_id !== selected.value?.concept_id)
    .map((n) => ({ label: n.name, value: n.concept_id })),
)

const conceptRelations = computed(() => {
  const id = selected.value?.concept_id
  if (!id || !graph.value) return []
  const names = Object.fromEntries(graph.value.nodes.map((n) => [n.concept_id, n.name]))
  return graph.value.edges
    .filter((e) => e.source === id || e.target === id)
    .map((e) => ({ ...e, sourceName: names[e.source] ?? e.source, targetName: names[e.target] ?? e.target, label: RELATION_TYPE_LABELS[e.relation_type] ?? e.relation_type }))
})

async function submitRelation() {
  const focus = selected.value?.concept_id
  if (!focus || !newRelTarget.value) return
  relSubmitting.value = true
  try {
    const pair = newRelDirection.value === 'in' ? { source_id: newRelTarget.value, target_id: focus } : { source_id: focus, target_id: newRelTarget.value }
    await addKnowledgeRelation({ ...pair, relation_type: newRelType.value, teacher_verified: true })
    message.success('关联已修正')
    newRelTarget.value = null
    await loadGraph()
    await selectConcept(focus)
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    relSubmitting.value = false
  }
}

async function toggleRelation(id: number, verified: boolean) {
  try {
    await verifyKnowledgeRelation(id, verified)
    await loadGraph()
  } catch (error) {
    message.error((error as Error).message)
  }
}

async function removeRelation(id: number) {
  try {
    await deleteKnowledgeRelation(id)
    await loadGraph()
    if (selected.value) await selectConcept(selected.value.concept_id)
  } catch (error) {
    message.error((error as Error).message)
  }
}

// ------------------------------------------------------------------ 分析
const analytics = ref<KnowledgeAnalyticsOverview | null>(null)
const analyticsLoading = ref(false)
const analyticsDays = ref(14)
const dayOptions: SelectOption[] = [
  { label: '近 7 天', value: 7 },
  { label: '近 14 天', value: 14 },
  { label: '近 30 天', value: 30 },
]
const classFilter = ref<number | null>(null)
const classOptions = computed<SelectOption[]>(() => [{ label: '我的全部班级', value: 0 }, ...overview.classOptions.value])

async function loadAnalytics() {
  analyticsLoading.value = true
  try {
    analytics.value = await fetchKnowledgeAnalytics({ days: analyticsDays.value, class_id: classFilter.value || undefined, limit: 8 })
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    analyticsLoading.value = false
  }
}
watch([analyticsDays, classFilter], () => void loadAnalytics())

// ------------------------------------------------------------------ 教师资源上传
const uploading = ref(false)
async function handleUpload({ file, onFinish, onError }: UploadCustomRequestOptions) {
  if (!file.file) return onError()
  uploading.value = true
  try {
    const doc = await uploadKnowledgeDocument(file.file, {
      resource_type: 'teacher_resource',
      teacher_verified: true,
      concept_ids: selected.value ? [selected.value.concept_id] : undefined,
      chapter: selected.value?.chapter || undefined,
    })
    message.success(`「${doc.title}」已入库并开始索引，小E 将在索引完成后使用`)
    onFinish()
  } catch (error) {
    message.error((error as Error).message)
    onError()
  } finally {
    uploading.value = false
  }
}

onMounted(() => {
  void loadGraph()
  void loadAnalytics()
})
</script>

<template>
  <TeacherDashboardShell active-nav="knowledge" page-title="知识星域" page-subtitle="查看知识点关系、审核 AI 教学资源、修正关联并观察学生的高频疑问" hide-search hide-toolbar>
    <main class="tk-page">
      <section v-if="analytics" class="tk-metrics" aria-label="知识使用指标">
        <article><span>学生提问</span><strong>{{ analytics.total_queries }}</strong></article>
        <article><span>提问学生</span><strong>{{ analytics.unique_students }}</strong></article>
        <article><span>知识锚定率</span><strong>{{ Math.round(analytics.grounded_rate * 100) }}%</strong></article>
        <article><span>薄弱知识点</span><strong>{{ analytics.weak_concepts.length }}</strong></article>
      </section>

      <div class="tk-grid">
        <article class="tk-card tk-card--graph">
          <header class="tk-head">
            <n-icon :component="GitNetworkOutline" />
            <div>
              <h2>知识图谱与前置关系</h2>
              <p>红色为近期学生薄弱知识点；点击节点查看前置、误区与 AI 采用的资源。</p>
            </div>
            <label class="tk-switch"><span>误区节点</span><n-switch v-model:value="showMisconceptions" size="small" /></label>
          </header>
          <n-spin :show="graphLoading">
            <PlexKnowledgeGraph v-if="kgNodes.length" :nodes="kgNodes" :edges="kgEdges" mode="teacher" height="520px" :class-id="overview.selectedClassId.value" @node-click="onNodeClick" />
            <n-empty v-else-if="!graphLoading" description="知识图谱尚未初始化，请联系管理员" />
          </n-spin>
        </article>

        <article class="tk-card tk-card--detail">
          <header class="tk-head">
            <n-icon :component="SparklesOutline" />
            <div>
              <h2>{{ selected ? selected.name : '知识点详情' }}</h2>
              <p v-if="selected">难度 {{ selected.difficulty }} · 掌握阈值 {{ selected.mastery_threshold }}<template v-if="selected.usage"> · 近 14 天被问 {{ selected.usage.queries }} 次 / {{ selected.usage.students }} 人</template></p>
              <p v-else>在图谱中点击一个知识点</p>
            </div>
          </header>
          <n-spin :show="detailLoading">
            <template v-if="selected">
              <p class="tk-desc">{{ selected.description || '暂无描述' }}</p>
              <section class="tk-block">
                <h3>前置知识</h3>
                <div class="tk-chips">
                  <button v-for="n in selected.prerequisite_nodes" :key="n.concept_id" type="button" class="tk-chip" @click="selectConcept(n.concept_id)">{{ n.name }}</button>
                  <em v-if="!selected.prerequisite_nodes.length">无</em>
                </div>
              </section>
              <section class="tk-block">
                <h3>推荐后续</h3>
                <div class="tk-chips">
                  <button v-for="n in selected.next_nodes" :key="n.concept_id" type="button" class="tk-chip" @click="selectConcept(n.concept_id)">{{ n.name }}</button>
                  <em v-if="!selected.next_nodes.length">无</em>
                </div>
              </section>
              <section class="tk-block">
                <h3>常见误区</h3>
                <ul class="tk-list">
                  <li v-for="m in selected.misconception_nodes" :key="m.concept_id"><strong>{{ m.name }}</strong><small>{{ m.description }}</small></li>
                  <li v-for="(m, i) in selected.common_misconceptions" :key="`cm-${i}`"><small>{{ m }}</small></li>
                  <li v-if="!selected.misconception_nodes.length && !selected.common_misconceptions.length"><em>无</em></li>
                </ul>
              </section>

              <section class="tk-block">
                <h3>关联修正</h3>
                <ul class="tk-rel-list">
                  <li v-for="rel in conceptRelations" :key="rel.id">
                    <span>{{ rel.sourceName }} <i>{{ rel.label }}</i> {{ rel.targetName }}</span>
                    <n-tag size="tiny" :bordered="false" :type="rel.teacher_verified ? 'success' : 'default'">{{ rel.teacher_verified ? '已审' : '待审' }}</n-tag>
                    <n-button text size="tiny" @click="toggleRelation(rel.id, !rel.teacher_verified)">{{ rel.teacher_verified ? '撤销' : '确认' }}</n-button>
                    <n-popconfirm @positive-click="removeRelation(rel.id)">
                      <template #trigger><n-button text size="tiny" type="error">删除</n-button></template>
                      删除该关联？
                    </n-popconfirm>
                  </li>
                </ul>
                <div class="tk-rel-form">
                  <n-select v-model:value="newRelTarget" size="small" filterable clearable placeholder="选择知识点" :options="conceptOptions" />
                  <n-select v-model:value="newRelDirection" size="small" :options="[{ label: '是当前的…', value: 'in' }, { label: '当前是它的…', value: 'out' }]" />
                  <n-select v-model:value="newRelType" size="small" :options="relationTypeOptions" />
                  <n-button size="small" type="warning" :loading="relSubmitting" :disabled="!newRelTarget" @click="submitRelation">添加</n-button>
                </div>
              </section>
            </template>
          </n-spin>
        </article>

        <article class="tk-card tk-card--materials">
          <header class="tk-head">
            <n-icon :component="LibraryOutline" />
            <div>
              <h2>AI 正在使用的教学资源</h2>
              <p>小E 回答该知识点时优先引用的材料。标记「教师审核」后会在检索排序中加权。</p>
            </div>
          </header>
          <n-spin :show="materialsLoading">
            <n-empty v-if="!selected" description="先选择一个知识点" />
            <n-empty v-else-if="materials && !materials.chunks.length" description="该知识点暂无已索引材料，可在下方上传教师资源" />
            <ul v-else-if="materials" class="tk-material-list">
              <li v-for="c in materials.chunks" :key="c.chunk_id" :class="{ open: expandedChunk === c.chunk_id }">
                <header @click="expandedChunk = expandedChunk === c.chunk_id ? null : c.chunk_id">
                  <strong>{{ c.title || c.document_title }}</strong>
                  <n-tag size="tiny" :bordered="false">{{ KNOWLEDGE_TYPE_LABELS[c.knowledge_type] ?? c.knowledge_type }}</n-tag>
                  <n-tag v-if="c.teacher_verified" size="tiny" type="success" :bordered="false">教师审核</n-tag>
                  <small>{{ c.document_title }}</small>
                </header>
                <p class="tk-material-preview" :class="{ full: expandedChunk === c.chunk_id }">{{ c.content }}</p>
                <footer>
                  <n-button size="tiny" :type="c.teacher_verified ? 'default' : 'warning'" secondary :loading="verifyingDoc === c.document_id" @click.stop="verifyDocument(c.document_id, !c.teacher_verified)">
                    {{ c.teacher_verified ? '取消审核' : '审核通过并加权' }}
                  </n-button>
                </footer>
              </li>
            </ul>
          </n-spin>
          <n-upload :custom-request="handleUpload" :show-file-list="false" accept=".md,.markdown,.txt,.pdf,.doc,.docx,.pptx" :disabled="uploading" class="tk-upload">
            <n-upload-dragger class="tk-dragger">
              <n-icon :component="CloudUploadOutline" size="22" />
              <p>{{ uploading ? '上传中…' : selected ? `上传「${selected.name}」的教师资源` : '上传教师资源（讲义 / 例题 / 错题解析）' }}</p>
              <small>自动标记为教师审核，索引完成后小E 即可引用</small>
            </n-upload-dragger>
          </n-upload>
        </article>

        <article class="tk-card tk-card--analytics">
          <header class="tk-head">
            <n-icon :component="PulseOutline" />
            <div>
              <h2>学生高频问题与薄弱知识点</h2>
              <p>来自小E 答疑与试炼提示的匿名统计。</p>
            </div>
            <div class="tk-filters">
              <n-select v-model:value="classFilter" size="small" :options="classOptions" class="w160" placeholder="全部班级" />
              <n-select v-model:value="analyticsDays" size="small" :options="dayOptions" class="w110" />
            </div>
          </header>
          <n-spin :show="analyticsLoading">
            <div class="tk-analytics">
              <div>
                <h3>高频问题</h3>
                <ul class="tk-rank">
                  <li v-for="(q, i) in analytics?.hot_queries ?? []" :key="i">
                    <span class="rank">{{ i + 1 }}</span>
                    <div><strong>{{ q.preview }}</strong><small>{{ q.concepts.join(' · ') || '未识别知识点' }}</small></div>
                    <em>{{ q.count }} 次 · {{ q.students }} 人</em>
                  </li>
                  <li v-if="analytics && !analytics.hot_queries.length"><em>暂无提问记录</em></li>
                </ul>
              </div>
              <div>
                <h3>薄弱知识点</h3>
                <ul class="tk-rank">
                  <li v-for="(c, i) in analytics?.weak_concepts ?? []" :key="c.concept_id" class="clickable" @click="selectConcept(c.concept_id)">
                    <span class="rank">{{ i + 1 }}</span>
                    <div><strong>{{ c.name }}</strong><small>低置信回答 {{ c.low_confidence }} 次</small></div>
                    <em>{{ c.queries }} 问 · {{ c.students }} 人</em>
                  </li>
                  <li v-if="analytics && !analytics.weak_concepts.length"><em>暂无数据</em></li>
                </ul>
              </div>
            </div>
          </n-spin>
        </article>
      </div>
    </main>
  </TeacherDashboardShell>
</template>

<style scoped>
.tk-page { width: 100%; padding: 0 var(--plex-page-gutter-x) 2rem; display: grid; gap: 1rem; }

.tk-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.8rem; }
.tk-metrics article { padding: 0.9rem 1rem; border: 1px solid rgba(255, 173, 76, 0.2); border-radius: 14px; background: rgba(25, 15, 7, 0.72); }
.tk-metrics span { display: block; color: rgba(235, 215, 194, 0.68); font-size: 0.8rem; }
.tk-metrics strong { display: block; margin-top: 0.3rem; color: #fff7ec; font-size: 1.3rem; }

.tk-grid { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(320px, 0.9fr); gap: 1rem; }
.tk-card {
  min-width: 0;
  padding: 1.1rem 1.2rem;
  border: 1px solid rgba(251, 146, 60, 0.2);
  border-radius: 14px;
  background:
    radial-gradient(circle at 50% 0%, rgba(251, 146, 60, 0.1), transparent 45%),
    linear-gradient(145deg, rgba(37, 22, 10, 0.86), rgba(15, 23, 42, 0.82));
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.04), 0 18px 50px rgba(0, 0, 0, 0.22);
}
.tk-card--detail { max-height: 640px; overflow: auto; }
.tk-card--analytics { grid-column: 1 / -1; }

.tk-head { display: grid; grid-template-columns: 26px minmax(0, 1fr) auto; gap: 0.6rem; align-items: center; margin-bottom: 0.9rem; color: #fdba74; }
.tk-head > .n-icon { font-size: 1.2rem; }
.tk-head h2 { margin: 0; color: #fff7ec; font-size: 1rem; }
.tk-head p { margin: 0.25rem 0 0; color: rgba(254, 215, 170, 0.7); font-size: 0.76rem; line-height: 1.45; }
.tk-switch { display: inline-flex; align-items: center; gap: 0.4rem; color: rgba(254, 215, 170, 0.75); font-size: 0.74rem; }
.tk-filters { display: flex; gap: 0.4rem; }
.w160 { width: 160px; }
.w110 { width: 110px; }

.tk-desc { margin: 0 0 0.6rem; color: rgba(254, 243, 230, 0.82); font-size: 0.83rem; line-height: 1.55; }
.tk-block { margin-top: 0.75rem; }
.tk-block h3 { margin: 0 0 0.4rem; color: #fdba74; font-size: 0.78rem; font-weight: 600; }
.tk-chips { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.tk-chip { border: 1px solid rgba(251, 146, 60, 0.32); border-radius: 999px; padding: 0.2rem 0.6rem; background: rgba(251, 146, 60, 0.12); color: #fed7aa; font-size: 0.74rem; cursor: pointer; }
.tk-chip:hover { background: rgba(251, 146, 60, 0.24); color: #fff; }
.tk-chips em, .tk-list em, .tk-rank em { color: rgba(254, 215, 170, 0.5); font-style: normal; font-size: 0.74rem; }
.tk-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.35rem; }
.tk-list li { display: grid; gap: 0.1rem; font-size: 0.8rem; }
.tk-list strong { color: #fecdd3; }
.tk-list small { color: rgba(254, 243, 230, 0.65); font-size: 0.74rem; }

.tk-rel-list { list-style: none; margin: 0 0 0.6rem; padding: 0; display: grid; gap: 0.3rem; }
.tk-rel-list li { display: grid; grid-template-columns: minmax(0, 1fr) auto auto auto; gap: 0.4rem; align-items: center; font-size: 0.74rem; color: rgba(254, 243, 230, 0.8); }
.tk-rel-list i { color: #fdba74; font-style: normal; margin: 0 0.25rem; }
.tk-rel-form { display: grid; grid-template-columns: 1fr 1fr; gap: 0.4rem; }
.tk-rel-form > :first-child { grid-column: 1 / -1; }

.tk-material-list { list-style: none; margin: 0 0 0.8rem; padding: 0; display: grid; gap: 0.5rem; }
.tk-material-list li { border: 1px solid rgba(251, 146, 60, 0.18); border-radius: 10px; padding: 0.6rem 0.75rem; background: rgba(251, 146, 60, 0.06); }
.tk-material-list header { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; cursor: pointer; font-size: 0.82rem; }
.tk-material-list header strong { color: #fff7ec; }
.tk-material-list header small { color: rgba(254, 215, 170, 0.55); font-size: 0.72rem; margin-left: auto; }
.tk-material-preview { margin: 0.4rem 0; color: rgba(254, 243, 230, 0.78); font-size: 0.78rem; line-height: 1.5; white-space: pre-wrap; max-height: 3.2em; overflow: hidden; }
.tk-material-preview.full { max-height: 320px; overflow: auto; }
.tk-material-list footer { display: flex; justify-content: flex-end; }
.tk-upload { display: block; }
.tk-dragger { background: rgba(251, 146, 60, 0.05) !important; border-color: rgba(251, 146, 60, 0.32) !important; text-align: center; }
.tk-dragger p { margin: 0.3rem 0 0.1rem; color: #fff7ec; font-size: 0.8rem; }
.tk-dragger small { color: rgba(254, 215, 170, 0.55); font-size: 0.72rem; }

.tk-analytics { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.tk-analytics h3 { margin: 0 0 0.5rem; color: #fdba74; font-size: 0.8rem; }
.tk-rank { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.45rem; }
.tk-rank li { display: grid; grid-template-columns: 24px minmax(0, 1fr) auto; gap: 0.6rem; align-items: center; font-size: 0.82rem; }
.tk-rank li.clickable { cursor: pointer; }
.tk-rank li.clickable:hover strong { color: #fdba74; }
.tk-rank .rank { display: inline-grid; place-items: center; width: 22px; height: 22px; border-radius: 6px; background: rgba(251, 146, 60, 0.2); color: #fed7aa; font-size: 0.72rem; }
.tk-rank strong { display: block; color: #fff7ec; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tk-rank small { color: rgba(254, 215, 170, 0.55); font-size: 0.72rem; }
.tk-rank em { white-space: nowrap; }

@media (max-width: 1200px) {
  .tk-grid { grid-template-columns: 1fr; }
  .tk-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .tk-analytics { grid-template-columns: 1fr; }
}
</style>
