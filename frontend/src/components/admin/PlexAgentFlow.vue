<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { VueFlow, useVueFlow, type Node, type Edge } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
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

const AGENT_DEFS = [
  { id: 'diagnose', name: '学习诊断智能体', nameEn: 'Learning Diagnostics', desc: '分析学生答题记录与代码运行结果，识别薄弱点', icon: '🔍', x: 60, y: 200 },
  { id: 'kg', name: '知识图谱智能体', nameEn: 'Knowledge Graph', desc: '基于知识图谱定位相关前置知识与关联节点', icon: '🗺️', x: 320, y: 100 },
  { id: 'path', name: '路径推荐智能体', nameEn: 'Path Planner', desc: '结合能力画像生成个性化学习路径', icon: '🧭', x: 320, y: 300 },
  { id: 'code', name: '代码分析智能体', nameEn: 'Code Analyzer', desc: '解析编译错误、运行时错误与逻辑问题', icon: '💻', x: 580, y: 100 },
  { id: 'feedback', name: '反馈生成智能体', nameEn: 'Feedback Generator', desc: '整合诊断与路径结果，生成自然语言学习反馈', icon: '💬', x: 580, y: 300 },
  { id: 'teacher', name: '教师助理智能体', nameEn: 'Teacher Assistant', desc: '汇总班级数据，生成教学干预建议与讲解重点', icon: '👩‍🏫', x: 840, y: 200 },
]

const agentStatuses = ref<Record<string, AgentStatus>>({
  diagnose: 'idle',
  kg: 'idle',
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
            : agent.id === 'knowledge_graph'
              ? 'kg'
              : agent.id === 'path_recommendation'
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
    const status = agentStatuses.value[def.id]
    const color = STATUS_COLOR[status]
    return {
      id: def.id,
      type: 'default',
      position: { x: def.x, y: def.y },
      label: def.name,
      data: { ...def, status },
      style: {
        background: `${color}15`,
        border: `1.5px solid ${color}`,
        borderRadius: '10px',
        padding: '10px 14px',
        color: '#e2e8f0',
        fontSize: '12px',
        fontFamily: 'Microsoft YaHei, sans-serif',
        minWidth: '140px',
        textAlign: 'center',
        cursor: 'pointer',
        boxShadow: status === 'running' ? `0 0 12px ${color}55` : 'none',
        transition: 'all 0.3s',
      },
    }
  })
}

const FLOW_EDGES: Edge[] = [
  { id: 'e1', source: 'diagnose', target: 'kg', label: '薄弱知识点', animated: true, style: { stroke: '#38bdf8', strokeWidth: 1.5 }, labelStyle: { fill: '#7dd3fc', fontSize: 10 } },
  { id: 'e2', source: 'diagnose', target: 'path', label: '能力画像', animated: true, style: { stroke: '#38bdf8', strokeWidth: 1.5 }, labelStyle: { fill: '#7dd3fc', fontSize: 10 } },
  { id: 'e3', source: 'diagnose', target: 'code', label: '代码错误', animated: true, style: { stroke: '#38bdf8', strokeWidth: 1.5 }, labelStyle: { fill: '#7dd3fc', fontSize: 10 } },
  { id: 'e4', source: 'kg', target: 'feedback', label: '知识上下文', style: { stroke: '#a78bfa', strokeWidth: 1.5 }, labelStyle: { fill: '#c4b5fd', fontSize: 10 } },
  { id: 'e5', source: 'path', target: 'feedback', label: '推荐路径', style: { stroke: '#a78bfa', strokeWidth: 1.5 }, labelStyle: { fill: '#c4b5fd', fontSize: 10 } },
  { id: 'e6', source: 'code', target: 'feedback', label: '分析结论', style: { stroke: '#a78bfa', strokeWidth: 1.5 }, labelStyle: { fill: '#c4b5fd', fontSize: 10 } },
  { id: 'e7', source: 'feedback', target: 'teacher', label: '学情摘要', style: { stroke: '#22c55e', strokeWidth: 1.5 }, labelStyle: { fill: '#86efac', fontSize: 10 } },
]

const nodes = ref<Node[]>(makeNodes())
const edges = ref<Edge[]>(FLOW_EDGES)

const { onNodeClick } = useVueFlow()

onNodeClick(({ node }) => {
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

    setStatus('code', 'running')
    setStatus('kg', 'running')
    setStatus('path', 'running')
    addLog('code', pipeline.codeAnalysis.codeIssueSummary, 'success')
    addLog('kg', pipeline.graphInsight.graphReason, 'success')
    addLog('path', pipeline.recommendation.nextKnowledgePoint, 'success')
    setStatus('code', 'done')
    setStatus('kg', 'done')
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

    addLog('system', `✓ 多智能体协同推理完成（backend: ${pipeline.backend ?? 'mock'}）`, 'success')
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
        <p class="plex-agent-flow__agent-en">{{ selectedAgent.nameEn }}</p>
        <p class="plex-agent-flow__agent-desc">{{ selectedAgent.desc }}</p>
        <div class="plex-agent-flow__agent-status">
          <span>状态：</span>
          <em :style="{ color: STATUS_COLOR[agentStatuses[selectedAgent.id]] }">
            {{ STATUS_LABEL[agentStatuses[selectedAgent.id]] }}
          </em>
        </div>
        <div class="plex-agent-flow__params">
          <div class="plex-agent-flow__param-title">接口预留</div>
          <code>/api/v1/agents/{{ selectedAgent.id === 'diagnose' ? 'student-diagnose' : selectedAgent.id === 'teacher' ? 'teacher-suggestion' : 'status' }}</code>
          <div class="plex-agent-flow__param-hint">顺序流水线 · Mock / CrewAI 可切换</div>
        </div>
      </div>
      <div v-else class="plex-agent-flow__agent-placeholder">
        <p>点击节点查看智能体详情</p>
      </div>

      <div class="plex-agent-flow__log-area">
        <h4>运行日志</h4>
        <ul class="plex-agent-flow__logs">
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
      </div>

      <div v-if="agentStatusRows.length" class="plex-agent-flow__status-grid">
        <h4>智能体状态</h4>
        <plex-agent-status-card v-for="agent in agentStatusRows" :key="agent.id" :agent="agent" />
      </div>
    </aside>
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
  display: grid;
  grid-template-columns: 1fr 280px;
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
  font-size: 0.8rem;
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
  font-size: 0.68rem;
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
  gap: 0.75rem;
  overflow: hidden;
}

.plex-agent-flow__agent-detail,
.plex-agent-flow__agent-placeholder {
  padding: 1rem;
  border-radius: 10px;
  background: rgba(8, 10, 26, 0.88);
  border: 1px solid rgba(129, 140, 248, 0.15);
  flex-shrink: 0;
}

.plex-agent-flow__agent-placeholder p {
  margin: 0;
  color: rgba(148, 163, 184, 0.55);
  font-size: 0.8rem;
  text-align: center;
  padding: 1rem 0;
}

.plex-agent-flow__agent-icon {
  font-size: 1.5rem;
  margin-bottom: 0.4rem;
}

.plex-agent-flow__agent-detail h3 {
  margin: 0 0 0.15rem;
  color: #fff;
  font-size: 0.95rem;
}

.plex-agent-flow__agent-en {
  margin: 0 0 0.5rem;
  color: rgba(167, 139, 250, 0.8);
  font-size: 0.72rem;
}

.plex-agent-flow__agent-desc {
  margin: 0 0 0.65rem;
  color: rgba(203, 213, 225, 0.72);
  font-size: 0.78rem;
  line-height: 1.5;
}

.plex-agent-flow__agent-status {
  font-size: 0.78rem;
  color: rgba(203, 213, 225, 0.65);
  margin-bottom: 0.65rem;
}

.plex-agent-flow__agent-status em {
  font-style: normal;
  font-weight: 600;
}

.plex-agent-flow__params {
  padding: 0.6rem 0.75rem;
  border-radius: 7px;
  background: rgba(4, 8, 18, 0.55);
  border: 1px solid rgba(129, 140, 248, 0.1);
}

.plex-agent-flow__param-title {
  color: rgba(167, 139, 250, 0.8);
  font-size: 0.7rem;
  margin-bottom: 0.3rem;
}

.plex-agent-flow__params code {
  display: block;
  color: #7dd3fc;
  font-family: monospace;
  font-size: 0.78rem;
  margin-bottom: 0.3rem;
}

.plex-agent-flow__param-hint {
  color: rgba(148, 163, 184, 0.5);
  font-size: 0.68rem;
}

.plex-agent-flow__log-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-radius: 10px;
  background: rgba(8, 10, 26, 0.88);
  border: 1px solid rgba(129, 140, 248, 0.15);
  overflow: hidden;
  min-height: 0;
}

.plex-agent-flow__log-area h4 {
  margin: 0;
  padding: 0.6rem 0.85rem;
  color: rgba(255, 255, 255, 0.88);
  font-size: 0.82rem;
  border-bottom: 1px solid rgba(129, 140, 248, 0.1);
  flex-shrink: 0;
}

.plex-agent-flow__logs {
  list-style: none;
  margin: 0;
  padding: 0.5rem 0;
  overflow-y: auto;
  flex: 1;
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
  font-size: 0.72rem;
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
  font-size: 0.7rem;
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
  margin-top: 0.65rem;
  max-height: 220px;
  overflow-y: auto;
}

.plex-agent-flow__status-grid h4 {
  margin: 0;
  color: rgba(255, 255, 255, 0.88);
  font-size: 0.82rem;
}
</style>
