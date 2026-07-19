<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { VueFlow, useVueFlow, type Node, type Edge } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { NModal } from 'naive-ui'
import {
  fetchAgentsStatus,
  studentDiagnose,
  teacherAgentSuggestion,
  type AgentStatusItem,
} from '../../api/agentService'
import PlexAgentStatusCard from '../agent/PlexAgentStatusCard.vue'

type AgentStatus = 'idle' | 'running' | 'done' | 'error' | 'pending'

interface AgentLog {
  time: string
  agentId: string
  agentName: string
  message: string
  level: 'info' | 'success' | 'error'
}

const STATUS_COLOR: Record<AgentStatus, string> = {
  idle: '#475569',
  running: '#38bdf8',
  done: '#22c55e',
  error: '#f87171',
  pending: '#a78bfa',
}

const STATUS_LABEL: Record<AgentStatus, string> = {
  idle: '待机',
  running: '运行中',
  done: '已完成',
  error: '异常',
  pending: '待触发',
}

const props = withDefaults(
  defineProps<{
    enabledLearningIds?: string[]
  }>(),
  {
    enabledLearningIds: () => [],
  },
)

const FLOW_TO_BACKEND: Record<string, string> = {
  diagnose: 'learning_diagnosis',
  path: 'learning_path',
  code: 'code_analysis',
  feedback: 'feedback',
  teacher: 'teacher_assistant',
}

const AGENT_DEFS = [
  { id: 'diagnose', name: '学习诊断', nameEn: 'Diagnostics', desc: '识别薄弱知识点与能力画像', icon: '🔍', x: 80, y: 200 },
  { id: 'path', name: '路径推荐', nameEn: 'Path Planner', desc: '生成下一步学习路径', icon: '🧭', x: 380, y: 120 },
  { id: 'code', name: '代码分析', nameEn: 'Code Analyzer', desc: '解析代码与运行错误', icon: '💻', x: 380, y: 280 },
  { id: 'feedback', name: '反馈生成', nameEn: 'Feedback', desc: '输出分层学习反馈', icon: '💬', x: 680, y: 200 },
  { id: 'teacher', name: '教师助理', nameEn: 'Teacher Assist', desc: '汇总班级学情与干预建议', icon: '👩‍🏫', x: 960, y: 200 },
]

function isNodeEnabled(flowId: string): boolean {
  if (!props.enabledLearningIds.length) return true
  const backendId = FLOW_TO_BACKEND[flowId]
  return props.enabledLearningIds.includes(backendId)
}

const enabledNodeCount = computed(() => AGENT_DEFS.filter((def) => isNodeEnabled(def.id)).length)

const agentStatuses = ref<Record<string, AgentStatus>>({
  diagnose: 'idle',
  path: 'idle',
  code: 'idle',
  feedback: 'idle',
  teacher: 'idle',
})

const logs = ref<AgentLog[]>([
  { time: '00:00:00', agentId: 'system', agentName: 'PLEX Core', message: '多智能体协同系统就绪，等待触发信号', level: 'info' },
])

const selectedAgent = ref<(typeof AGENT_DEFS)[number] | null>(null)
const isSimulating = ref(false)
const agentStatusRows = ref<AgentStatusItem[]>([])
const showLogsModal = ref(false)
const showStatusModal = ref(false)
let statusTimer: ReturnType<typeof setInterval> | undefined

async function refreshAgentStatus() {
  try {
    const payload = await fetchAgentsStatus()
    agentStatusRows.value = payload.agents
    for (const agent of payload.agents) {
      const mapped =
        agent.id === 'learning_diagnosis'
          ? 'diagnose'
          : agent.id === 'code_analysis'
            ? 'code'
            : agent.id === 'path_recommendation' || agent.id === 'learning_path'
              ? 'path'
              : agent.id === 'feedback'
                ? 'feedback'
                : agent.id === 'teacher_assistant'
                  ? 'teacher'
                  : agent.id
      if (mapped in agentStatuses.value) {
        agentStatuses.value[mapped] =
          agent.status === 'success' ? 'done' : agent.status === 'running' ? 'running' : agent.status === 'error' ? 'error' : 'idle'
      }
    }
    nodes.value = makeNodes()
  } catch {
    /* 管理员页静默失败，避免打断观测 */
  }
}

onMounted(() => {
  void refreshAgentStatus()
  statusTimer = setInterval(() => {
    void refreshAgentStatus()
  }, 30_000)
})

onBeforeUnmount(() => {
  if (statusTimer) clearInterval(statusTimer)
})

function makeNodes(): Node[] {
  return AGENT_DEFS.map((def) => {
    const enabled = isNodeEnabled(def.id)
    const status = enabled ? agentStatuses.value[def.id] : 'idle'
    const color = enabled ? STATUS_COLOR[status] : '#334155'
    return {
      id: def.id,
      type: 'default',
      position: { x: def.x, y: def.y },
      label: def.name,
      data: { ...def, status, enabled },
      selectable: enabled,
      style: {
        background: `${color}15`,
        border: `1.5px solid ${color}`,
        borderRadius: '10px',
        padding: '10px 14px',
        color: enabled ? '#e2e8f0' : '#64748b',
        fontSize: '12px',
        fontFamily: 'Microsoft YaHei, sans-serif',
        minWidth: '120px',
        textAlign: 'center',
        cursor: enabled ? 'pointer' : 'not-allowed',
        opacity: enabled ? 1 : 0.38,
        boxShadow: status === 'running' && enabled ? `0 0 12px ${color}55` : 'none',
        transition: 'all 0.3s',
      },
    }
  })
}

const FLOW_EDGES: Edge[] = [
  { id: 'e1', source: 'diagnose', target: 'path', label: '能力画像', animated: true, style: { stroke: '#38bdf8', strokeWidth: 1.5 }, labelStyle: { fill: '#7dd3fc', fontSize: 10 } },
  { id: 'e2', source: 'diagnose', target: 'code', label: '代码错误', animated: true, style: { stroke: '#38bdf8', strokeWidth: 1.5 }, labelStyle: { fill: '#7dd3fc', fontSize: 10 } },
  { id: 'e3', source: 'path', target: 'feedback', label: '推荐路径', style: { stroke: '#a78bfa', strokeWidth: 1.5 }, labelStyle: { fill: '#c4b5fd', fontSize: 10 } },
  { id: 'e4', source: 'code', target: 'feedback', label: '分析结论', style: { stroke: '#a78bfa', strokeWidth: 1.5 }, labelStyle: { fill: '#c4b5fd', fontSize: 10 } },
  { id: 'e5', source: 'feedback', target: 'teacher', label: '学情摘要', style: { stroke: '#22c55e', strokeWidth: 1.5 }, labelStyle: { fill: '#86efac', fontSize: 10 } },
]

const nodes = ref<Node[]>(makeNodes())

function makeEdges(): Edge[] {
  return FLOW_EDGES.filter((edge) => isNodeEnabled(String(edge.source)) && isNodeEnabled(String(edge.target)))
}

const edges = ref<Edge[]>(makeEdges())

watch(
  () => props.enabledLearningIds,
  () => {
    nodes.value = makeNodes()
    edges.value = makeEdges()
  },
  { deep: true },
)

const { onNodeClick } = useVueFlow()

onNodeClick(({ node }) => {
  if (!isNodeEnabled(node.id)) return
  const def = AGENT_DEFS.find((d) => d.id === node.id)
  if (def) selectedAgent.value = def
})

function addLog(agentId: string, message: string, level: AgentLog['level'] = 'info') {
  const now = new Date()
  const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`
  const def = AGENT_DEFS.find((d) => d.id === agentId)
  logs.value.unshift({
    time,
    agentId,
    agentName: def?.name ?? agentId,
    message,
    level,
  })
  if (logs.value.length > 30) logs.value.pop()
}

function setStatus(id: string, status: AgentStatus) {
  agentStatuses.value[id] = status
  nodes.value = makeNodes()
}

async function simulate() {
  if (isSimulating.value) return
  isSimulating.value = true
  Object.keys(agentStatuses.value).forEach((k) => (agentStatuses.value[k] = 'pending' as AgentStatus))
  nodes.value = makeNodes()

  const sampleCode = 'for i in range(1, n):\n    total += i'

  try {
    addLog('system', `收到模拟样本提交 · 平台启用 ${enabledNodeCount.value}/${AGENT_DEFS.length} 个流水线节点`, 'info')
    addLog('system', '收到学生代码提交，启动多智能体协同推理…', 'info')

    setStatus('diagnose', 'running')
    addLog('diagnose', '调用 /api/v1/agents/student-diagnose', 'info')
    const pipeline = await studentDiagnose({
      exerciseId: 'demo-range-sum',
      code: sampleCode,
      stderr: '输出与预期不一致',
      expectedOutput: '15',
      knowledgePoints: ['for 循环', 'range', '累加求和'],
      attemptCount: 2,
      answerStatus: 'wrong',
    })
    setStatus('diagnose', 'done')
    addLog('diagnose', pipeline.diagnosis.diagnosis, 'success')
    for (const row of pipeline.pipelineTrace ?? []) {
      const latency = row.latencyMs != null ? ` · ${row.latencyMs}ms` : ''
      const source = row.source ? ` · ${row.source}` : ''
      addLog(row.agentId ?? 'system', `${row.summary ?? '已完成'}${latency}${source}`, row.status === 'error' ? 'error' : 'info')
    }

    setStatus('code', 'running')
    setStatus('path', 'running')
    addLog('code', pipeline.codeAnalysis.codeIssueSummary, 'success')
    addLog('path', pipeline.recommendation.nextKnowledgePoint, 'success')
    setStatus('code', 'done')
    setStatus('path', 'done')

    setStatus('feedback', 'running')
    addLog('feedback', pipeline.feedback.shortFeedback, 'success')
    setStatus('feedback', 'done')

    setStatus('teacher', 'running')
    const teacher = await teacherAgentSuggestion({
      classId: 'demo-class',
      weakPointStats: [{ knowledgePoint: 'range 边界', count: 6 }],
      commonErrorTypes: ['logic'],
      recentExercises: ['1 到 n 求和'],
    })
    setStatus('teacher', 'done')
    addLog('teacher', teacher.classSummary, 'success')

    const backendLabel = pipeline.backend === 'mock' || !pipeline.backend ? '规则引擎' : pipeline.backend
    addLog('system', `✓ 多智能体协同推理完成（${backendLabel}）`, 'success')
    await refreshAgentStatus()
  } catch (error) {
    addLog('system', error instanceof Error ? error.message : '智能体链路失败', 'error')
    Object.keys(agentStatuses.value).forEach((k) => {
      if (agentStatuses.value[k] === 'running') agentStatuses.value[k] = 'error'
    })
    nodes.value = makeNodes()
  } finally {
    isSimulating.value = false
  }
}

function resetFlow() {
  Object.keys(agentStatuses.value).forEach((k) => (agentStatuses.value[k] = 'idle' as AgentStatus))
  nodes.value = makeNodes()
  edges.value = makeEdges()
  logs.value = [{ time: '00:00:00', agentId: 'system', agentName: 'PLEX Core', message: '多智能体协同系统已重置', level: 'info' }]
  selectedAgent.value = null
}
</script>

<template>
  <div class="plex-agent-flow">
    <div class="plex-agent-flow__canvas-area">
      <div class="plex-agent-flow__toolbar">
        <button
          class="plex-agent-flow__btn plex-agent-flow__btn--primary"
          :disabled="isSimulating"
          type="button"
          @click="simulate"
        >
          {{ isSimulating ? '⏳ 推理中…' : '▶ 运行协同推理' }}
        </button>
        <button class="plex-agent-flow__btn" type="button" @click="resetFlow">↺ 重置</button>
        <button class="plex-agent-flow__btn" type="button" @click="showLogsModal = true">运行日志</button>
        <button class="plex-agent-flow__btn" type="button" @click="showStatusModal = true">智能体状态</button>
        <div class="plex-agent-flow__status-legend">
          <span v-for="(color, key) in STATUS_COLOR" :key="key" class="plex-agent-flow__legend-item">
            <i :style="{ background: color }" />
            {{ STATUS_LABEL[key] }}
          </span>
        </div>
      </div>

      <div class="plex-agent-flow__vue-flow-wrap">
        <vue-flow
          v-model:nodes="nodes"
          v-model:edges="edges"
          :fit-view-on-init="true"
          :nodes-draggable="true"
          :edges-updatable="false"
          :delete-key-code="null"
          class="plex-vue-flow"
        >
          <background pattern-color="rgba(129,140,248,0.08)" :gap="24" :size="1" />
          <controls position="bottom-left" />
        </vue-flow>
      </div>
    </div>

    <aside class="plex-agent-flow__sidebar">
      <div v-if="selectedAgent" class="plex-agent-flow__agent-detail">
        <div class="plex-agent-flow__agent-icon">{{ selectedAgent.icon }}</div>
        <h3>{{ selectedAgent.name }}</h3>
        <p class="plex-agent-flow__agent-desc">{{ selectedAgent.desc }}</p>
        <div class="plex-agent-flow__agent-status">
          <span>状态：</span>
          <em :style="{ color: STATUS_COLOR[agentStatuses[selectedAgent.id]] }">
            {{ STATUS_LABEL[agentStatuses[selectedAgent.id]] }}
          </em>
        </div>
      </div>
      <div v-else class="plex-agent-flow__agent-placeholder">
        <p>点击流程图节点查看智能体详情</p>
      </div>
    </aside>

    <n-modal v-model:show="showLogsModal" preset="card" title="运行日志" :style="{ maxWidth: '640px', width: '92vw' }">
      <ul class="plex-agent-flow__logs plex-agent-flow__logs--modal">
        <li
          v-for="(log, i) in logs"
          :key="i"
          :class="`plex-agent-flow__log-item--${log.level}`"
        >
          <time>{{ log.time }}</time>
          <span class="plex-agent-flow__log-agent">{{ log.agentName }}</span>
          <span class="plex-agent-flow__log-msg">{{ log.message }}</span>
        </li>
      </ul>
    </n-modal>

    <n-modal v-model:show="showStatusModal" preset="card" title="智能体状态" :style="{ maxWidth: '560px', width: '92vw' }">
      <div v-if="agentStatusRows.length" class="plex-agent-flow__status-grid plex-agent-flow__status-grid--modal">
        <plex-agent-status-card v-for="agent in agentStatusRows" :key="agent.id" :agent="agent" />
      </div>
      <p v-else class="plex-agent-flow__status-empty">暂无运行态数据</p>
    </n-modal>
  </div>
</template>

<style>
@import '@vue-flow/core/dist/style.css';
@import '@vue-flow/core/dist/theme-default.css';
@import '@vue-flow/controls/dist/style.css';

.plex-vue-flow .vue-flow__background {
  background: transparent !important;
}

.plex-vue-flow .vue-flow__edge-path {
  stroke-width: 1.5;
}

.plex-vue-flow .vue-flow__controls {
  background: rgba(10, 22, 40, 0.9) !important;
  border: 1px solid rgba(129, 140, 248, 0.2) !important;
  border-radius: 8px !important;
  box-shadow: none !important;
}

.plex-vue-flow .vue-flow__controls-button {
  background: transparent !important;
  border-color: rgba(129, 140, 248, 0.15) !important;
  color: rgba(203, 213, 225, 0.7) !important;
  fill: rgba(203, 213, 225, 0.7) !important;
}

.plex-vue-flow .vue-flow__controls-button:hover {
  background: rgba(129, 140, 248, 0.12) !important;
}
</style>

<style scoped>
.plex-agent-flow {
  --admin-text-title: 1.08rem;
  --admin-text-subtitle: 0.78rem;
  --admin-text-body: 0.82rem;
  --admin-text-card-title: 0.86rem;
  --admin-text-muted: 0.78rem;
  --admin-text-meta: 0.74rem;

  display: grid;
  grid-template-columns: minmax(0, 1fr) 200px;
  gap: 1rem;
  height: 520px;
  min-height: 0;
}

.plex-agent-flow__canvas-area {
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(129, 140, 248, 0.15);
  background: linear-gradient(145deg, rgba(8, 10, 26, 0.95), rgba(4, 8, 22, 0.92));
}

.plex-agent-flow__toolbar {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.55rem 0.85rem;
  border-bottom: 1px solid rgba(129, 140, 248, 0.1);
  flex-shrink: 0;
  flex-wrap: wrap;
}

.plex-agent-flow__btn {
  padding: 0.35rem 0.85rem;
  border-radius: 6px;
  border: 1px solid rgba(129, 140, 248, 0.28);
  background: rgba(129, 140, 248, 0.08);
  color: rgba(203, 213, 225, 0.85);
  font-size: var(--admin-text-body);
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}

.plex-agent-flow__btn:hover {
  background: rgba(129, 140, 248, 0.18);
}

.plex-agent-flow__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.plex-agent-flow__btn--primary {
  border-color: rgba(56, 189, 248, 0.4);
  background: rgba(56, 189, 248, 0.1);
  color: #7dd3fc;
}

.plex-agent-flow__btn--primary:hover:not(:disabled) {
  background: rgba(56, 189, 248, 0.2);
}

.plex-agent-flow__status-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-left: auto;
}

.plex-agent-flow__legend-item {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  color: rgba(203, 213, 225, 0.6);
  font-size: var(--admin-text-meta);
}

.plex-agent-flow__legend-item i {
  display: block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.plex-agent-flow__vue-flow-wrap {
  flex: 1;
  min-height: 0;
}

.plex-vue-flow {
  width: 100%;
  height: 100%;
  background: transparent;
}

.plex-agent-flow__sidebar {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.plex-agent-flow__agent-detail,
.plex-agent-flow__agent-placeholder {
  padding: 1rem;
  border-radius: 10px;
  background: rgba(8, 10, 26, 0.88);
  border: 1px solid rgba(129, 140, 248, 0.15);
  flex: 1;
}

.plex-agent-flow__agent-placeholder p {
  margin: 0;
  color: rgba(148, 163, 184, 0.55);
  font-size: var(--admin-text-body);
  text-align: center;
  padding: 1rem 0;
}

.plex-agent-flow__agent-icon {
  font-size: 1.5rem;
  margin-bottom: 0.4rem;
}

.plex-agent-flow__agent-detail h3 {
  margin: 0 0 0.5rem;
  color: #fff;
  font-size: var(--admin-text-card-title);
}

.plex-agent-flow__agent-desc {
  margin: 0 0 0.65rem;
  color: rgba(203, 213, 225, 0.72);
  font-size: var(--admin-text-muted);
  line-height: 1.5;
}

.plex-agent-flow__agent-status {
  font-size: var(--admin-text-muted);
  color: rgba(203, 213, 225, 0.65);
}

.plex-agent-flow__agent-status em {
  font-style: normal;
  font-weight: 600;
}

.plex-agent-flow__logs {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 420px;
  overflow-y: auto;
}

.plex-agent-flow__logs--modal {
  max-height: 60vh;
}

.plex-agent-flow__log-item--info,
.plex-agent-flow__log-item--success,
.plex-agent-flow__log-item--error {
  display: grid;
  grid-template-columns: 52px auto;
  grid-template-rows: auto auto;
  gap: 0.1rem 0.4rem;
  padding: 0.35rem 0.75rem;
  border-bottom: 1px solid rgba(129, 140, 248, 0.05);
  font-size: var(--admin-text-meta);
  line-height: 1.4;
}

.plex-agent-flow__log-item--info time,
.plex-agent-flow__log-item--success time,
.plex-agent-flow__log-item--error time {
  color: rgba(148, 163, 184, 0.5);
  grid-row: 1;
  font-family: monospace;
}

.plex-agent-flow__log-agent {
  grid-row: 1;
  font-size: var(--admin-text-meta);
}

.plex-agent-flow__log-item--info .plex-agent-flow__log-agent { color: #7dd3fc; }
.plex-agent-flow__log-item--success .plex-agent-flow__log-agent { color: #4ade80; }
.plex-agent-flow__log-item--error .plex-agent-flow__log-agent { color: #f87171; }

.plex-agent-flow__log-msg {
  grid-column: 1 / -1;
  grid-row: 2;
  color: rgba(203, 213, 225, 0.75);
  padding-left: 0.2rem;
}

.plex-agent-flow__status-grid {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.plex-agent-flow__status-grid--modal {
  max-height: 60vh;
  overflow-y: auto;
}

.plex-agent-flow__status-empty {
  margin: 0;
  padding: 1.5rem 0;
  text-align: center;
  color: rgba(148, 163, 184, 0.65);
  font-size: var(--admin-text-body);
}

@media (max-width: 900px) {
  .plex-agent-flow {
    grid-template-columns: 1fr;
    height: auto;
    min-height: 480px;
  }

  .plex-agent-flow__sidebar {
    min-height: 120px;
  }
}
</style>
