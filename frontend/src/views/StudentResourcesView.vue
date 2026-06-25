<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NButton, NCollapse, NCollapseItem, NProgress, NSelect, NTag, useMessage } from 'naive-ui'
import DashboardShell from '../components/layout/DashboardShell.vue'
import StudentSectionTabs from '../components/student/StudentSectionTabs.vue'
import { fetchAiHealth, type AiHealth } from '../api/health'
import {
  createResourceTask,
  fetchPersonalizedResources,
  fetchResourceTask,
  fetchResourceTasks,
  retryResourceTask,
  type PersonalizedResource,
  type ResourceTask,
} from '../api/personalizedResources'

const message = useMessage()
const knowledgeKey = ref('loop')
const resourceFilter = ref('all')
const task = ref<ResourceTask | null>(null)
const taskHistory = ref<ResourceTask[]>([])
const resources = ref<PersonalizedResource[]>([])
const generating = ref(false)
const loading = ref(true)
const loadError = ref('')
const pollingTimedOut = ref(false)
const selected = ref<PersonalizedResource | null>(null)
const aiHealth = ref<AiHealth | null>(null)

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
  lesson_document: '讲解文档',
  mind_map: '思维导图',
  exercise_set: '分层题库',
  extended_reading: '拓展阅读',
  coding_lab: '代码实操',
  audio_explanation: '语音讲解',
}

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
    items: items.sort((a, b) => a.resource_type.localeCompare(b.resource_type)),
  }))
})

const latestTaskStatus = computed(() => {
  const active = task.value ?? taskHistory.value[0]
  if (!active) return '暂无生成任务'
  return `${active.status} · 画像 v${active.profile_version} · ${active.backend}`
})

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
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '资源加载失败'
  } finally {
    loading.value = false
  }
}

async function poll(id: string) {
  pollingTimedOut.value = false
  for (let index = 0; index < 90; index += 1) {
    task.value = await fetchResourceTask(id)
    if (['completed', 'failed'].includes(task.value.status)) return
    await new Promise((resolve) => window.setTimeout(resolve, 1000))
  }
  pollingTimedOut.value = true
}

async function generate() {
  generating.value = true
  try {
    task.value = await createResourceTask(knowledgeKey.value)
    if (task.value.status !== 'completed') await poll(task.value.task_id)
    if (task.value.status === 'failed') throw new Error(task.value.error || '生成任务失败')
    await load()
    if (pollingTimedOut.value) message.info('任务仍在处理中，可稍后从任务历史继续查看')
    else message.success('五类个性化资源已生成')
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

function contentText(item: PersonalizedResource) {
  return typeof item.content.markdown === 'string' ? item.content.markdown : JSON.stringify(item.content, null, 2)
}

function summaryText(value?: Record<string, unknown>) {
  if (!value || !Object.keys(value).length) return '等待执行'
  const formatValue = (item: unknown) => {
    if (Array.isArray(item)) {
      return item.map((entry) => (
        typeof entry === 'object' ? JSON.stringify(entry) : String(entry)
      )).join('、')
    }
    return typeof item === 'object' && item !== null ? JSON.stringify(item) : String(item)
  }
  return Object.entries(value)
    .map(([key, item]) => `${key}: ${formatValue(item)}`)
    .join('；')
}

onMounted(() => {
  void load()
  void fetchAiHealth().then((value) => { aiHealth.value = value }).catch(() => undefined)
})
</script>

<template>
  <DashboardShell
    active-nav="track"
    page-title="个性化资源中心"
    page-subtitle="按知识点收拢资源包，优先看最新可用材料"
    search-placeholder=""
    hide-search
  >
    <template #toolbar><StudentSectionTabs area="learning" /></template>
    <main class="resource-page">
      <section class="generator">
        <div class="generator__copy">
          <h2>生成学习资源包</h2>
          <p>画像解释、知识检索、教学设计、资源生成和质量审核会作为一条任务轨迹保留。</p>
          <n-tag v-if="aiHealth" :type="aiHealth.effective_backend === 'iflytek_spark' ? 'success' : 'warning'">
            当前 AI 后端：{{ aiHealth.effective_backend }}
          </n-tag>
        </div>
        <div class="generator__controls">
          <n-select v-model:value="knowledgeKey" :options="knowledgeOptions" class="knowledge-select" />
          <n-button type="primary" :loading="generating" @click="generate">生成五类资源</n-button>
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
      </section>

      <section v-if="task" class="task-panel">
        <header>
          <strong>{{ task.status }} · {{ task.backend }}</strong>
          <span v-if="task.fallback_reason">已降级：{{ task.fallback_reason }}</span>
        </header>
        <n-progress :percentage="task.progress" color="#25f5ee" />
        <div class="agent-trace">
          <article v-for="step in task.steps" :key="step.agent" class="trace-step" :class="`trace-step--${step.status}`">
            <header>
              <div>
                <strong>{{ step.name || step.agent }}</strong>
                <small>{{ step.agent }} · {{ step.contract_version || 'legacy' }}</small>
              </div>
              <n-tag :type="step.status === 'completed' ? 'success' : step.status === 'running' ? 'warning' : step.status === 'failed' ? 'error' : 'default'">
                {{ step.status }}
              </n-tag>
            </header>
            <p><b>输入摘要</b>{{ summaryText(step.input_summary) }}</p>
            <p><b>输出摘要</b>{{ summaryText(step.output_summary) }}</p>
            <footer>
              <span>{{ step.backend || '等待分配后端' }}<template v-if="step.model"> · {{ step.model }}</template></span>
              <span v-if="step.latency_ms !== null && step.latency_ms !== undefined">{{ step.latency_ms }} ms</span>
              <span v-if="step.depends_on">上游：{{ step.depends_on }}</span>
            </footer>
            <em v-if="step.error">{{ step.error }}</em>
          </article>
        </div>
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

        <section v-if="groupedResources.length" class="resource-groups">
          <article v-for="group in groupedResources" :key="group.label" class="resource-group">
            <header>
              <h3>{{ group.label }}</h3>
              <span>{{ group.items.length }} 类资源</span>
            </header>
            <div class="resource-grid">
              <button
                v-for="item in group.items"
                :key="item.id"
                type="button"
                class="resource-card"
                @click="selected = item"
              >
                <span class="resource-card__tags">
                  <n-tag type="info">{{ typeLabels[item.resource_type] }}</n-tag>
                  <n-tag :type="item.backend === 'iflytek_spark' ? 'success' : 'warning'">{{ item.backend }}</n-tag>
                </span>
                <strong>{{ item.title }}</strong>
                <p>{{ item.recommendation_reason }}</p>
                <span class="resource-card__meta">
                  <em>置信度 {{ Math.round(item.confidence * 100) }}%</em>
                  <em>{{ item.estimated_minutes }} 分钟</em>
                </span>
              </button>
            </div>
          </article>
        </section>
        <section v-else class="resource-state">暂无匹配资源。可以切换类型筛选，或生成新的资源包。</section>

        <n-collapse v-if="visibleTasks.length" class="task-history">
          <n-collapse-item title="生成任务历史" name="history">
            <article v-for="item in visibleTasks" :key="item.task_id" class="task-history__row">
              <div>
                <strong>{{ item.task_id }}</strong>
                <span>{{ item.status }} · 画像 v{{ item.profile_version }} · {{ item.backend }}</span>
              </div>
              <div class="task-history__actions">
                <n-button size="small" secondary @click="task = item">查看轨迹</n-button>
                <n-button v-if="item.status === 'failed' && item.recoverable" size="small" @click="retry(item)">重试</n-button>
              </div>
            </article>
          </n-collapse-item>
        </n-collapse>
      </template>

      <section v-if="selected" class="resource-detail" aria-label="资源详情">
        <header>
          <div>
            <h2>{{ selected.title }}</h2>
            <p>{{ selected.knowledge_label }} · {{ typeLabels[selected.resource_type] }}</p>
          </div>
          <n-button quaternary @click="selected = null">关闭</n-button>
        </header>
        <pre>{{ contentText(selected) }}</pre>
        <h4>知识库引用</h4>
        <ul>
          <li v-for="citation in selected.citations" :key="`${citation.document_id}-${citation.section}`">
            {{ citation.title }} · {{ citation.section }}：{{ citation.snippet }}
          </li>
        </ul>
      </section>
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
.type-select {
  width: 190px;
}

.resource-summary {
  display: grid;
  grid-template-columns: 0.8fr 0.8fr 1.4fr;
  gap: 0.8rem;
  margin-top: 1rem;
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

.agent-trace {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  margin-top: 1rem;
}

.trace-step {
  padding: 0.9rem;
  border: 1px solid rgba(120, 150, 170, 0.16);
  border-radius: 0.6rem;
  background: rgba(2, 10, 18, 0.7);
}

.trace-step--completed {
  border-color: rgba(37, 245, 238, 0.22);
}

.trace-step--failed {
  border-color: rgba(248, 113, 113, 0.4);
}

.trace-step header {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
}

.trace-step header div {
  display: flex;
  flex-direction: column;
}

.trace-step small,
.trace-step p,
.trace-step footer {
  color: #7da5b6;
  font-size: 0.76rem;
}

.trace-step p {
  line-height: 1.55;
}

.trace-step p b {
  display: block;
  color: #b9e9e6;
}

.trace-step footer {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0.4rem;
}

.trace-step em {
  display: block;
  margin-top: 0.5rem;
  color: #fca5a5;
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

.resource-groups {
  display: grid;
  gap: 0.9rem;
}

.resource-group {
  padding: 1rem;
}

.resource-group > header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.resource-group > header span {
  color: rgba(125, 165, 182, 0.9);
  font-size: 0.82rem;
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
  margin-top: 1rem;
  padding: 1.2rem;
}

.resource-detail header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.resource-detail pre {
  max-height: 520px;
  overflow: auto;
  white-space: pre-wrap;
  color: #cce6ef;
  line-height: 1.6;
}

.resource-detail li {
  color: #8fb7c4;
  margin: 0.45rem 0;
}

@media (max-width: 1050px) {
  .resource-grid,
  .agent-trace {
    grid-template-columns: repeat(2, minmax(0, 1fr));
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
  .resource-grid,
  .agent-trace {
    grid-template-columns: 1fr;
  }
}
</style>
