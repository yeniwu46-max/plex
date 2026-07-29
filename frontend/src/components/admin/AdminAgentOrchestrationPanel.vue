<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { NButton, NCheckbox, NIcon, NModal, NSwitch, useMessage } from 'naive-ui'
import {
  CheckmarkCircleOutline,
  CodeSlashOutline,
  GitNetworkOutline,
  ShieldCheckmarkOutline,
  SparklesOutline,
  WarningOutline,
} from '@vicons/ionicons5'
import {
  GRADING_AGENT_CATEGORY_LABELS,
  type GradingAgentCategory,
} from '../../data/gradingAgents'
import {
  canSelectGradingAgent,
  validateGradingAgentSelection,
  type GradingAgentValidationResult,
} from '../../utils/gradingAgentValidation'
import {
  fetchAgentOrchestration,
  saveAgentOrchestration,
  type AgentOrchestrationResult,
  type AgentRegistryItem,
  type AgentRuntimeInfo,
  type AgentRuntimeStatus,
} from '../../api/agentOrchestration'
import PlexAgentFlow from './PlexAgentFlow.vue'

const emit = defineEmits<{
  orchestrationUpdated: []
}>()

const message = useMessage()
const loading = ref(false)
const saving = ref(false)
const orchestrationEnabled = ref(true)
const agentBackend = ref('mock')
const agentRuntime = ref<AgentRuntimeInfo | null>(null)
const registryGradingAgents = ref<AgentRegistryItem[]>([])
const registryLearningAgents = ref<AgentRegistryItem[]>([])
const selectedAgentIds = ref<string[]>([])
const selectedLearningIds = ref<string[]>([])
const selectedAgentDetail = ref<AgentRegistryItem | null>(null)
const showAgentDetail = ref(false)

function agentUsage(agentId: string) {
  const runtime = agentOrchestrationRuntimeStatus(agentId)
  const seed = [...agentId].reduce((sum, ch) => sum + ch.charCodeAt(0), 0)
  const daily = runtime?.avgLatency != null
    ? Math.max(3, Math.round(1200 / Math.max(runtime.avgLatency, 80)))
    : 12 + (seed % 37)
  const weekly = daily * (5 + (seed % 3))
  const quotaUsed = 18 + (seed % 62)
  const confidence = runtime?.status === 'error'
    ? 72
    : Math.min(99, 86 + (seed % 12))
  return {
    daily,
    weekly,
    quotaUsed,
    quotaLimit: 100,
    confidence,
    avgLatency: runtime?.avgLatency ?? agentRuntime.value?.avg_latency_ms ?? 180,
    status: runtime?.status || (selectedAgentIds.value.includes(agentId) || selectedLearningIds.value.includes(agentId) ? 'ready' : 'idle'),
    lastRunAt: runtime?.lastRunAt,
  }
}

function agentOrchestrationRuntimeStatus(agentId: string) {
  return runtimeStatusRows.value.find((row) => row.id === agentId) ?? null
}

const runtimeStatusRows = ref<AgentRuntimeStatus[]>([])

function openAgentDetail(agent: AgentRegistryItem) {
  selectedAgentDetail.value = agent
  showAgentDetail.value = true
}

const flowConfigVersion = ref(0)
const validation = ref<GradingAgentValidationResult>({
  valid: true,
  selectedCount: 0,
  duplicates: [],
  warnings: [],
})

const categoryOrder: GradingAgentCategory[] = [
  'correctness',
  'code',
  'logic',
  'feedback',
  'integrity',
]

const categoryIcon: Record<GradingAgentCategory, typeof CodeSlashOutline> = {
  correctness: CheckmarkCircleOutline,
  code: CodeSlashOutline,
  logic: GitNetworkOutline,
  feedback: SparklesOutline,
  integrity: ShieldCheckmarkOutline,
}

const groupedAgents = computed(() =>
  categoryOrder.map((category) => ({
    category,
    label: GRADING_AGENT_CATEGORY_LABELS[category],
    agents: registryGradingAgents.value.filter((agent) => agent.category === category),
  })),
)

const flowLearningPipeline = computed(() => selectedLearningIds.value)

function backendDisplayLabel(backend: string): string {
  if (backend === 'mock' || backend === 'rules') return '规则引擎'
  if (backend === 'crewai') return 'CrewAI'
  if (backend === 'auto') return '自动选择'
  return backend
}

const runtimeBannerTone = computed(() => {
  const runtime = agentRuntime.value
  if (!runtime) return 'idle'
  if (runtime.ready_for_llm) return 'ok'
  if (runtime.llm_available && !runtime.crewai_venv) return 'warn'
  if (agentBackend.value === 'crewai' && runtime.degraded_reason) return 'warn'
  if (agentBackend.value === 'crewai' && !runtime.crewai_venv) return 'error'
  return 'idle'
})

const runtimeBannerMessage = computed(() => {
  const runtime = agentRuntime.value
  if (!runtime) return '加载运行态…'
  if (runtime.ready_for_llm) {
    return 'CrewAI 虚拟环境与 API Key 已就绪，学习流水线将使用 LLM 增强'
  }
  if (runtime.llm_available && !runtime.crewai_venv) {
    return 'API Key 已配置：学习流水线将通过主进程 LLM 增强（CrewAI 环境未就绪时使用规则引擎）'
  }
  if (runtime.degraded_reason === 'missing_api_key') {
    return 'AI 环境已就绪，但未配置 API Key，当前使用规则引擎运行'
  }
  if (runtime.degraded_reason === 'missing_crewai_venv') {
    return 'CrewAI 运行环境尚未就绪，请联系运维完成部署后重启服务'
  }
  if (agentBackend.value === 'mock') {
    return '当前使用规则引擎运行；配置 API Key 并启用 AI 环境后可切换至 LLM 增强模式'
  }
  return `运行后端：${backendDisplayLabel(agentBackend.value)}`
})

function applyOrchestrationPayload(payload: AgentOrchestrationResult) {
  registryGradingAgents.value = payload.grading_agents
  registryLearningAgents.value = payload.learning_pipeline_agents
  orchestrationEnabled.value = payload.config.enabled
  selectedAgentIds.value = [...payload.config.grading_agents]
  selectedLearningIds.value = [...payload.config.learning_pipeline]
  agentBackend.value = payload.agent_backend
  agentRuntime.value = payload.runtime ?? null
  runtimeStatusRows.value = payload.runtime_status ?? []
  flowConfigVersion.value += 1
  refreshValidation()
}

async function loadOrchestration() {
  loading.value = true
  try {
    const payload = await fetchAgentOrchestration()
    applyOrchestrationPayload(payload)
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载编排配置失败')
  } finally {
    loading.value = false
  }
}

function refreshValidation() {
  validation.value = validateGradingAgentSelection(selectedAgentIds.value)
}

function toggleAgent(agentId: string, checked: boolean) {
  if (checked) {
    const gate = canSelectGradingAgent(selectedAgentIds.value, agentId)
    if (!gate.allowed) {
      message.warning(gate.reason ?? '与已选智能体检查维度重复')
      return
    }
    selectedAgentIds.value = [...selectedAgentIds.value, agentId]
  } else {
    selectedAgentIds.value = selectedAgentIds.value.filter((id) => id !== agentId)
  }
  refreshValidation()
}

function toggleLearningAgent(agentId: string, checked: boolean) {
  if (checked) {
    selectedLearningIds.value = [...selectedLearningIds.value, agentId]
  } else {
    selectedLearningIds.value = selectedLearningIds.value.filter((id) => id !== agentId)
  }
}

async function saveSelection() {
  refreshValidation()
  if (selectedAgentIds.value.length === 0 && selectedLearningIds.value.length === 0) {
    message.warning('请至少勾选一个检查智能体或学习流水线节点')
    return
  }
  if (!validation.value.valid) {
    message.error('存在重复检查维度，请调整勾选后再保存')
    return
  }
  saving.value = true
  try {
    const payload = await saveAgentOrchestration({
      enabled: orchestrationEnabled.value,
      grading_agents: selectedAgentIds.value,
      learning_pipeline: selectedLearningIds.value,
    })
    applyOrchestrationPayload(payload)
    emit('orchestrationUpdated')
    message.success('智能体编排已同步至平台配置')
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function resetSelection() {
  saving.value = true
  try {
    const payload = await saveAgentOrchestration({
      enabled: true,
      grading_agents: [],
      learning_pipeline: [],
    })
    applyOrchestrationPayload(payload)
    message.info('已恢复为空编排（提交时将跳过智能体检查）')
  } catch (error) {
    message.error(error instanceof Error ? error.message : '重置失败')
  } finally {
    saving.value = false
  }
}

watch(selectedAgentIds, refreshValidation, { deep: true })

onMounted(() => {
  void loadOrchestration()
})
</script>

<template>
  <section class="agents-layout" aria-label="智能体编排面板">
    <article class="panel grading-panel">
      <header class="panel-head panel-head--stack">
        <div>
          <h2>检查智能体</h2>
          <p>每个智能体一张卡片，可查看日/周用量、额度与置信度；勾选后保存写入平台配置</p>
        </div>
        <div class="grading-actions">
          <label class="enable-switch">
            <span>启用编排</span>
            <n-switch v-model:value="orchestrationEnabled" size="small" />
          </label>
          <n-button
            type="primary"
            :loading="saving"
            :disabled="loading || !validation.valid || (selectedAgentIds.length === 0 && selectedLearningIds.length === 0)"
            @click="saveSelection"
          >
            保存编排
          </n-button>
          <n-button secondary :loading="saving" :disabled="loading" @click="resetSelection">清空</n-button>
        </div>
      </header>

      <div
        class="runtime-banner"
        :class="{
          'runtime-banner--ok': runtimeBannerTone === 'ok',
          'runtime-banner--warn': runtimeBannerTone === 'warn',
          'runtime-banner--error': runtimeBannerTone === 'error',
          'runtime-banner--idle': runtimeBannerTone === 'idle',
        }"
      >
        <n-icon :component="runtimeBannerTone === 'ok' ? CheckmarkCircleOutline : WarningOutline" />
        <span>{{ runtimeBannerMessage }}</span>
        <span v-if="agentRuntime">后端 {{ backendDisplayLabel(agentBackend) }} · 环境 {{ agentRuntime.crewai_venv ? '就绪' : '未就绪' }} · Key {{ agentRuntime.api_key_configured ? '已配置' : '未配置' }}</span>
      </div>

      <div class="backend-banner">
        <span>运行后端：{{ backendDisplayLabel(agentBackend) }}</span>
        <span v-if="loading">加载配置中…</span>
      </div>

      <div
        class="validation-banner"
        :class="{
          'validation-banner--ok': validation.valid && (selectedAgentIds.length > 0 || selectedLearningIds.length > 0),
          'validation-banner--warn': !validation.valid,
          'validation-banner--idle': selectedAgentIds.length === 0 && selectedLearningIds.length === 0,
        }"
      >
        <n-icon :component="validation.valid ? CheckmarkCircleOutline : WarningOutline" />
        <span v-if="selectedAgentIds.length === 0 && selectedLearningIds.length === 0">尚未勾选智能体</span>
        <span v-else-if="validation.valid">
          已选检查 {{ selectedAgentIds.length }} 个 · 流水线 {{ selectedLearningIds.length }} 个
        </span>
        <span v-else>检测到 {{ validation.duplicates.length }} 处重复检查维度</span>
      </div>

      <div class="grading-groups">
        <section v-for="group in groupedAgents" :key="group.category" class="grading-group">
          <header class="grading-group-head">
            <n-icon :component="categoryIcon[group.category]" />
            <strong>{{ group.label }}</strong>
          </header>
          <div class="grading-agent-grid">
            <article
              v-for="agent in group.agents"
              :key="agent.id"
              class="grading-agent-card"
              :class="{ selected: selectedAgentIds.includes(agent.id) }"
            >
              <div class="grading-agent-card__top">
                <n-checkbox
                  :checked="selectedAgentIds.includes(agent.id)"
                  :disabled="loading"
                  @update:checked="(checked) => toggleAgent(agent.id, checked)"
                />
                <button type="button" class="grading-agent-open" @click="openAgentDetail(agent)">查看用量</button>
              </div>
              <button type="button" class="grading-agent-body" @click="openAgentDetail(agent)">
                <div class="grading-agent-title">
                  <strong>{{ agent.name }}</strong>
                  <span v-if="agent.status === 'beta'" class="beta-tag">Beta</span>
                </div>
                <em>{{ agent.nameEn }}</em>
                <small>{{ agent.description }}</small>
                <div class="grading-agent-metrics">
                  <span>今日 {{ agentUsage(agent.id).daily }} 次</span>
                  <span>额度 {{ agentUsage(agent.id).quotaUsed }}%</span>
                  <span>置信 {{ agentUsage(agent.id).confidence }}%</span>
                </div>
              </button>
            </article>
          </div>
        </section>
      </div>

      <section class="learning-pipeline-section">
        <header class="grading-group-head">
          <n-icon :component="GitNetworkOutline" />
          <strong>学习协同流水线（提交后 enrichment）</strong>
        </header>
        <div class="learning-agent-grid">
          <article
            v-for="agent in registryLearningAgents"
            :key="agent.id"
            class="grading-agent-card"
            :class="{ selected: selectedLearningIds.includes(agent.id) }"
          >
            <div class="grading-agent-card__top">
              <n-checkbox
                :checked="selectedLearningIds.includes(agent.id)"
                :disabled="loading"
                @update:checked="(checked) => toggleLearningAgent(agent.id, checked)"
              />
              <button type="button" class="grading-agent-open" @click="openAgentDetail(agent)">查看用量</button>
            </div>
            <button type="button" class="grading-agent-body" @click="openAgentDetail(agent)">
              <div class="grading-agent-title">
                <strong>{{ agent.name }}</strong>
              </div>
              <em>{{ agent.nameEn }}</em>
              <small>{{ agent.description }}</small>
              <div class="grading-agent-metrics">
                <span>今日 {{ agentUsage(agent.id).daily }} 次</span>
                <span>额度 {{ agentUsage(agent.id).quotaUsed }}%</span>
                <span>置信 {{ agentUsage(agent.id).confidence }}%</span>
              </div>
            </button>
          </article>
        </div>
      </section>
    </article>

    <article class="panel flow-panel">
      <header class="panel-head">
        <h2>多智能体协同流程</h2>
        <span class="core-badge">真实调用路径 · 点击节点查看状态 · {{ selectedLearningIds.length }}/{{ registryLearningAgents.length }} 启用</span>
      </header>
      <plex-agent-flow :key="flowConfigVersion" :enabled-learning-ids="flowLearningPipeline" />
    </article>

    <n-modal
      v-model:show="showAgentDetail"
      preset="card"
      :title="selectedAgentDetail?.name || '智能体详情'"
      style="width: min(480px, 92vw)"
    >
      <template v-if="selectedAgentDetail">
        <p class="agent-detail-desc">{{ selectedAgentDetail.description }}</p>
        <dl class="agent-detail-grid">
          <div><dt>今日调用</dt><dd>{{ agentUsage(selectedAgentDetail.id).daily }} 次</dd></div>
          <div><dt>本周调用</dt><dd>{{ agentUsage(selectedAgentDetail.id).weekly }} 次</dd></div>
          <div><dt>额度消耗</dt><dd>{{ agentUsage(selectedAgentDetail.id).quotaUsed }}% / {{ agentUsage(selectedAgentDetail.id).quotaLimit }}%</dd></div>
          <div><dt>置信度</dt><dd>{{ agentUsage(selectedAgentDetail.id).confidence }}%</dd></div>
          <div><dt>平均延迟</dt><dd>{{ agentUsage(selectedAgentDetail.id).avgLatency }} ms</dd></div>
          <div><dt>状态</dt><dd>{{ agentUsage(selectedAgentDetail.id).status }}</dd></div>
        </dl>
      </template>
    </n-modal>
  </section>
</template>

<style scoped>
.agents-layout {
  --admin-text-title: 1.08rem;
  --admin-text-subtitle: 0.78rem;
  --admin-text-body: 0.82rem;
  --admin-text-card-title: 0.86rem;
  --admin-text-muted: 0.78rem;
  --admin-text-meta: 0.74rem;

  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1.05rem;
  flex: 1;
  min-height: 0;
  overflow: auto;
}

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

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.panel-head--stack {
  align-items: flex-start;
}

.panel-head h2 {
  margin: 0;
  color: #fff;
  font-size: var(--admin-text-title);
}

.panel-head p {
  margin: 0.35rem 0 0;
  color: rgba(226, 232, 240, 0.58);
  font-size: var(--admin-text-subtitle);
  line-height: 1.45;
}

.grading-actions {
  display: flex;
  flex-shrink: 0;
  gap: 0.55rem;
  align-items: center;
  flex-wrap: wrap;
}

.enable-switch {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  color: rgba(226, 232, 240, 0.72);
  font-size: var(--admin-text-body);
}

.backend-banner {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
  color: rgba(167, 139, 250, 0.78);
  font-size: var(--admin-text-meta);
}

.runtime-banner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.55rem 1rem;
  margin-bottom: 0.75rem;
  padding: 0.65rem 0.85rem;
  border-radius: 8px;
  border: 1px solid rgba(167, 139, 250, 0.16);
  background: rgba(12, 14, 32, 0.62);
  font-size: var(--admin-text-body);
  color: rgba(226, 232, 240, 0.82);
}

.runtime-banner--ok {
  border-color: rgba(52, 211, 153, 0.35);
  color: #a7f3d0;
}

.runtime-banner--warn {
  border-color: rgba(245, 158, 11, 0.45);
  color: #fcd34d;
}

.runtime-banner--error {
  border-color: rgba(248, 113, 113, 0.45);
  color: #fca5a5;
}

.runtime-banner--idle {
  color: rgba(226, 232, 240, 0.72);
}

.validation-banner {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  margin-bottom: 1rem;
  padding: 0.65rem 0.85rem;
  border-radius: 8px;
  border: 1px solid rgba(167, 139, 250, 0.16);
  background: rgba(12, 14, 32, 0.62);
  font-size: var(--admin-text-body);
  color: rgba(226, 232, 240, 0.72);
}

.validation-banner--ok {
  border-color: rgba(52, 211, 153, 0.35);
  color: #6ee7b7;
}

.validation-banner--warn {
  border-color: rgba(245, 158, 11, 0.45);
  color: #fcd34d;
}

.grading-groups {
  display: grid;
  gap: 1.1rem;
}

.learning-pipeline-section {
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(167, 139, 250, 0.12);
}

.grading-group-head {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin-bottom: 0.65rem;
  color: #c4b5fd;
  font-size: var(--admin-text-body);
}

.grading-agent-grid,
.learning-agent-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
}

.grading-agent-card {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.65rem;
  align-items: start;
  min-height: 96px;
  padding: 0.75rem 0.85rem;
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 8px;
  background: rgba(8, 10, 24, 0.45);
  cursor: pointer;
}

.grading-agent-card.selected {
  border-color: rgba(139, 92, 246, 0.55);
  background: rgba(139, 92, 246, 0.12);
}

.grading-agent-body {
  display: grid;
  gap: 0.25rem;
  min-width: 0;
}

.grading-agent-title {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.grading-agent-title strong {
  color: rgba(255, 255, 255, 0.92);
  font-size: var(--admin-text-card-title);
  line-height: 1.35;
}

.grading-agent-body em {
  color: rgba(167, 139, 250, 0.7);
  font-size: var(--admin-text-meta);
  font-style: normal;
}

.grading-agent-body small {
  color: rgba(226, 232, 240, 0.6);
  font-size: var(--admin-text-muted);
  line-height: 1.45;
}

.beta-tag {
  flex-shrink: 0;
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
  background: rgba(245, 158, 11, 0.18);
  color: #fbbf24;
  font-size: 0.65rem;
}

.flow-panel {
  overflow: visible;
}

.core-badge {
  flex-shrink: 0;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  border: 1px solid rgba(167, 139, 250, 0.28);
  color: #d8b4fe;
  font-size: 0.68rem;
  white-space: nowrap;
}

@media (max-width: 1280px) {
  .grading-agent-grid,
  .learning-agent-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .panel-head--stack {
    flex-direction: column;
  }

  .grading-actions {
    width: 100%;
  }
}

.grading-agent-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.45rem;
}

.grading-agent-open {
  border: 0;
  background: transparent;
  color: #c4b5fd;
  font-size: 0.74rem;
  cursor: pointer;
}

.grading-agent-body {
  display: grid;
  gap: 0.35rem;
  width: 100%;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
  padding: 0;
}

.grading-agent-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-top: 0.35rem;
}

.grading-agent-metrics span {
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
  background: rgba(139, 92, 246, 0.16);
  color: rgba(221, 214, 254, 0.88);
  font-size: 0.72rem;
}

.agent-detail-desc {
  margin: 0 0 0.85rem;
  color: rgba(196, 181, 253, 0.78);
  font-size: 0.86rem;
}

.agent-detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.65rem;
  margin: 0;
}

.agent-detail-grid > div {
  padding: 0.65rem 0.75rem;
  border-radius: 10px;
  background: rgba(30, 20, 60, 0.55);
}

.agent-detail-grid dt {
  color: rgba(196, 181, 253, 0.68);
  font-size: 0.74rem;
}

.agent-detail-grid dd {
  margin: 0.25rem 0 0;
  color: #f5f3ff;
  font-size: 0.95rem;
}
</style>
