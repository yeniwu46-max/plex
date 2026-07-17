<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { GraphData } from '@antv/g6'
import type { KgEdge, KgEdgeType, KgNode, KgNodeStatus } from '../../data/knowledgeGraphData'
import { KG_NODE_STATUS_COLOR, KG_NODE_STATUS_LABEL } from '../../data/knowledgeGraphData'
import { useThemeStore } from '../../stores/theme'
import { getG6Tokens, buildG6TooltipHtml } from '../../theme/g6Theme'

type G6Graph = import('@antv/g6').Graph

const props = withDefaults(
  defineProps<{
    nodes: KgNode[]
    edges: KgEdge[]
    mode?: 'student' | 'teacher' | 'admin'
    height?: string
    pathNodeIds?: string[]
    remediationNodeIds?: string[]
    activePathNodeId?: string | null
  }>(),
  {
    mode: 'student',
    height: '480px',
    pathNodeIds: () => [],
    remediationNodeIds: () => [],
    activePathNodeId: null,
  },
)

const emit = defineEmits<{
  nodeClick: [node: KgNode]
}>()

const themeStore = useThemeStore()
const g6Tokens = computed(() => getG6Tokens(themeStore.resolvedTheme))

const containerRef = ref<HTMLDivElement>()
let graphInstance: G6Graph | null = null
let destroyed = false
const graphLoading = ref(true)

const selectedNode = ref<KgNode | null>(null)

const EDGE_COLOR: Record<KgEdgeType, string> = {
  prerequisite: '#38bdf8',
  related: '#6ee7b7',
  path: '#a78bfa',
  advanced: '#fb923c',
}

const EDGE_LABEL_COLOR: Record<KgEdgeType, string> = {
  prerequisite: '#7dd3fc',
  related: '#86efac',
  path: '#c4b5fd',
  advanced: '#fdba74',
}

const MODE_ACCENT: Record<string, string> = {
  student: '#22c55e',
  teacher: '#f97316',
  admin: '#818cf8',
}

function heatLevel(node: KgNode) {
  return Math.min(1, Math.max(0, (node.weak_score ?? 0) / 120))
}

function metricText(value: number | null | undefined, suffix = '') {
  if (value === null || value === undefined) return '—'
  return `${value}${suffix}`
}

function errorTypeLabel(type: string) {
  const labels: Record<string, string> = {
    wrong_output: '输出不符',
    runtime_error: '运行错误',
    wrong_answer: '答案错误',
  }
  return labels[type] ?? type
}

function buildMetricTooltip(node: KgNode) {
  if (
    node.weak_score === undefined &&
    node.fail_count === undefined &&
    node.accuracy === undefined &&
    node.affected_student_count === undefined
  ) {
    return ''
  }
  const errors = (node.top_error_types ?? [])
    .map((item) => `${errorTypeLabel(item.error_type)} ${item.count}`)
    .join('、')
  const notMasteredPercent =
    node.not_mastered_percent ??
    (
      node.student_count && node.affected_student_count !== undefined
        ? Math.round((node.affected_student_count / node.student_count) * 100)
        : null
    )
  return `<div style="margin-top:8px;padding-top:8px;border-top:1px solid rgba(148,163,184,.24);display:grid;gap:4px;color:${g6Tokens.value.tooltipTextColor};font-size:11px;">
    <span>薄弱热度：${metricText(node.weak_score)}</span>
    <span>失败次数：${metricText(node.fail_count)} · 错题数：${metricText(node.wrong_count)}</span>
    <span>正确率：${metricText(node.accuracy, '%')} · 影响学生：${metricText(node.affected_student_count)}人</span>
    ${props.mode === 'teacher' ? `<span>未掌握学生：${metricText(notMasteredPercent, '%')}</span>` : ''}
    ${errors ? `<span>常见错误：${errors}</span>` : ''}
  </div>`
}

function buildGraphData(): GraphData {
  const accent = MODE_ACCENT[props.mode] ?? '#22c55e'
  const tk = g6Tokens.value
  const pathSet = new Set(props.pathNodeIds ?? [])
  const remediationSet = new Set(props.remediationNodeIds ?? [])
  const pathOrder = props.pathNodeIds ?? []

  return {
    nodes: props.nodes.map((n) => {
      const onPath = pathSet.has(n.id)
      const isActive = props.activePathNodeId === n.id
      const isRemediation = remediationSet.has(n.id)
      const statusColor = KG_NODE_STATUS_COLOR[n.status as KgNodeStatus]
      const heat = heatLevel(n)
      const isTeacherWeak = props.mode === 'teacher' && (n.status === 'weak' || (n.weak_score ?? 0) > 0)
      const heatColor = isTeacherWeak ? '#fb7185' : statusColor
      const stroke = isActive ? '#22c55e' : isRemediation ? '#f97316' : heatColor
      const lineWidth = isActive ? 3 : onPath ? 2.2 : n.status === 'recommended' ? 2.5 : 1.5 + heat * 3
      const labelSuffix = isRemediation ? ' · 补救' : isActive ? ' · 下一步' : onPath ? ' · 路径' : ''
      return {
        id: n.id,
        data: {
          label: n.label,
          status: n.status,
          domain: n.domain,
          description: n.description,
          level: n.level,
          originalNode: n,
        },
        style: {
          x: n.x ?? Math.random() * 800,
          y: n.y ?? Math.random() * 480,
          size: (n.level === 'advanced' ? 48 : n.level === 'intermediate' ? 42 : 36) + heat * 18,
          fill: heatColor + (heat > 0 ? '55' : onPath ? '33' : '22'),
          stroke,
          lineWidth,
          labelText: n.label + labelSuffix,
          labelFill: tk.labelFill,
          labelFontSize: 12,
          labelFontFamily: 'Microsoft YaHei, sans-serif',
          labelOffsetY: 4,
          shadowColor: stroke,
          shadowBlur: isActive || n.status === 'mastered' || n.status === 'recommended' ? 12 : onPath ? 8 : heat * 22,
          cursor: 'pointer',
          badgeFill: accent,
        },
      }
    }),
    edges: props.edges.map((e) => {
      const onPath =
        pathSet.has(e.source) &&
        pathSet.has(e.target) &&
        pathOrder.indexOf(e.source) >= 0 &&
        pathOrder.indexOf(e.target) > pathOrder.indexOf(e.source)
      const edgeType = onPath ? 'path' : e.type
      return {
        id: e.id,
        source: e.source,
        target: e.target,
        data: { type: edgeType, label: e.label },
        style: {
          stroke: EDGE_COLOR[edgeType],
          lineWidth: onPath ? 2.5 : 1.5,
          endArrow: true,
          endArrowType: 'vee',
          endArrowSize: 8,
          opacity: onPath ? 1 : tk.edgeOpacity,
          labelText: e.label ?? '',
          labelFill: EDGE_LABEL_COLOR[edgeType],
          labelFontSize: 10,
        },
      }
    }),
  }
}

async function initGraph() {
  if (!containerRef.value) return
  if (graphInstance) {
    graphInstance.destroy()
    graphInstance = null
  }

  graphLoading.value = true
  try {
    const { Graph } = await import('@antv/g6')

    graphInstance = new Graph({
    container: containerRef.value,
    width: containerRef.value.clientWidth,
    height: containerRef.value.clientHeight,
    autoFit: 'view',
    padding: 32,
    node: {
      type: 'circle',
    },
    edge: {
      type: 'cubic-horizontal',
    },
    behaviors: [
      'drag-canvas',
      'zoom-canvas',
      'drag-element',
    ],
    plugins: [
      {
        type: 'tooltip',
        getContent: (_e: Event, items: { id: string }[]) => {
          if (!items?.length) return ''
          const nodeId = items[0]?.id
          const node = props.nodes.find((n) => n.id === nodeId)
          if (!node) return ''
          const statusLabel = KG_NODE_STATUS_LABEL[node.status as KgNodeStatus]
          const color = KG_NODE_STATUS_COLOR[node.status as KgNodeStatus]
          return buildG6TooltipHtml(
            node.label,
            node.domain,
            statusLabel,
            node.description,
            color,
            g6Tokens.value,
          ).replace('</div>', `${buildMetricTooltip(node)}</div>`)
        },
      },
    ],
    data: buildGraphData(),
    })

    try {
      await graphInstance.render()
    } catch {
      return
    }

    if (destroyed || !graphInstance) return

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    graphInstance.on('node:click', (evt: any) => {
      const nodeId = evt?.target?.id ?? evt?.itemId ?? evt?.item?.getID?.()
      const node = props.nodes.find((n) => n.id === nodeId)
      if (node) {
        selectedNode.value = node
        emit('nodeClick', node)
      }
    })
  } finally {
    graphLoading.value = false
  }
}

onMounted(() => {
  void initGraph()
})

watch(
  () => [props.nodes, props.edges, props.pathNodeIds, props.activePathNodeId, props.remediationNodeIds],
  () => {
    if (graphInstance && !destroyed) {
      graphInstance.setData(buildGraphData())
      graphInstance.render().catch(() => {})
    }
  },
  { deep: true },
)

// 主题切换时重绘图谱
watch(
  () => themeStore.resolvedTheme,
  () => {
    if (graphInstance && !destroyed) {
      graphInstance.setData(buildGraphData())
      graphInstance.render().catch(() => {})
    }
  },
)

onBeforeUnmount(() => {
  destroyed = true
  graphInstance?.destroy()
  graphInstance = null
})
</script>

<template>
  <div class="plex-kg-wrap" :class="`plex-kg-wrap--${mode}`">
    <div ref="containerRef" class="plex-kg-canvas" :style="{ height }" />
    <p v-if="graphLoading" class="plex-kg-loading">正在加载知识图谱…</p>

    <transition name="slide">
      <aside v-if="selectedNode" class="plex-kg-detail">
        <button class="plex-kg-detail__close" type="button" @click="selectedNode = null">✕</button>
        <div
          class="plex-kg-detail__status"
          :style="{ background: KG_NODE_STATUS_COLOR[selectedNode.status] + '22', borderColor: KG_NODE_STATUS_COLOR[selectedNode.status] + '55' }"
        >
          <span :style="{ color: KG_NODE_STATUS_COLOR[selectedNode.status] }">
            {{ KG_NODE_STATUS_LABEL[selectedNode.status] }}
          </span>
        </div>
        <h3>{{ selectedNode.label }}</h3>
        <p class="plex-kg-detail__domain">{{ selectedNode.domain }} · {{ selectedNode.level === 'basic' ? '入门' : selectedNode.level === 'intermediate' ? '进阶' : '挑战' }}</p>
        <p class="plex-kg-detail__desc">{{ selectedNode.description }}</p>
        <dl
          v-if="selectedNode.weak_score !== undefined || selectedNode.fail_count !== undefined"
          class="plex-kg-detail__metrics"
        >
          <div>
            <dt>薄弱热度</dt>
            <dd>{{ selectedNode.weak_score ?? '—' }}</dd>
          </div>
          <div>
            <dt>正确率</dt>
            <dd>
              {{ selectedNode.accuracy ?? '—' }}
              <span v-if="selectedNode.accuracy !== null && selectedNode.accuracy !== undefined">%</span>
            </dd>
          </div>
          <div>
            <dt>{{ mode === 'teacher' ? '影响学生' : '失败次数' }}</dt>
            <dd>{{ mode === 'teacher' ? selectedNode.affected_student_count ?? 0 : selectedNode.fail_count ?? 0 }}</dd>
          </div>
        </dl>
        <div class="plex-kg-detail__edges">
          <p>
            <small>前置知识：</small>
            <span v-for="e in edges.filter(ed => ed.target === selectedNode!.id && ed.type === 'prerequisite')" :key="e.id">
              {{ nodes.find(n => n.id === e.source)?.label }}
            </span>
            <em v-if="!edges.some(ed => ed.target === selectedNode!.id && ed.type === 'prerequisite')">无</em>
          </p>
        </div>
      </aside>
    </transition>

    <div class="plex-kg-legend">
      <span v-for="(color, key) in KG_NODE_STATUS_COLOR" :key="key" class="plex-kg-legend__item">
        <i :style="{ background: color }" />
        {{ KG_NODE_STATUS_LABEL[key] }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.plex-kg-wrap {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  background: var(--plex-kg-canvas-bg, linear-gradient(135deg, rgba(3, 10, 20, 0.96), rgba(5, 14, 26, 0.92)));
  border: 1px solid rgba(130, 212, 255, 0.1);
}

.plex-kg-wrap--student { border-color: rgba(34, 197, 94, 0.15); }
.plex-kg-wrap--teacher { border-color: rgba(249, 115, 22, 0.15); }
.plex-kg-wrap--admin { border-color: rgba(129, 140, 248, 0.15); }

.plex-kg-canvas {
  width: 100%;
}

.plex-kg-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  color: rgba(203, 213, 225, 0.75);
  font-size: 0.85rem;
  pointer-events: none;
}

.plex-kg-detail {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 220px;
  padding: 1rem;
  border-radius: 10px;
  background: var(--plex-kg-detail-bg, rgba(5, 14, 26, 0.92));
  border: 1px solid var(--plex-kg-detail-border, rgba(130, 212, 255, 0.18));
  backdrop-filter: blur(8px);
}

.plex-kg-detail__close {
  position: absolute;
  top: 8px;
  right: 10px;
  background: transparent;
  border: none;
  color: rgba(226, 232, 240, 0.5);
  cursor: pointer;
  font-size: 0.8rem;
  line-height: 1;
}

.plex-kg-detail__status {
  display: inline-flex;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  border: 1px solid transparent;
  margin-bottom: 0.5rem;
  font-size: 0.72rem;
}

.plex-kg-detail h3 {
  margin: 0 0 0.2rem;
  color: var(--plex-kg-label, #fff);
  font-size: 1rem;
}

.plex-kg-detail__domain {
  margin: 0 0 0.6rem;
  color: rgba(148, 163, 184, 0.8);
  font-size: 0.75rem;
}

.plex-kg-detail__desc {
  margin: 0 0 0.6rem;
  color: rgba(203, 213, 225, 0.82);
  font-size: 0.8rem;
  line-height: 1.5;
}

.plex-kg-detail__metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.4rem;
  margin: 0.7rem 0;
}

.plex-kg-detail__metrics div {
  padding: 0.45rem;
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.plex-kg-detail__metrics dt {
  margin: 0 0 0.2rem;
  color: rgba(203, 213, 225, 0.62);
  font-size: 0.68rem;
}

.plex-kg-detail__metrics dd {
  margin: 0;
  color: #f8fafc;
  font-weight: 700;
}

.plex-kg-detail__edges p {
  margin: 0;
  font-size: 0.75rem;
  color: rgba(203, 213, 225, 0.7);
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  align-items: center;
}

.plex-kg-detail__edges small {
  color: rgba(148, 163, 184, 0.7);
  margin-right: 0.2rem;
}

.plex-kg-detail__edges span {
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
  background: rgba(130, 212, 255, 0.1);
  color: #7dd3fc;
  font-size: 0.72rem;
}

.plex-kg-detail__edges em {
  color: rgba(148, 163, 184, 0.5);
  font-style: normal;
  font-size: 0.72rem;
}

.plex-kg-legend {
  position: absolute;
  bottom: 10px;
  left: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
}

.plex-kg-legend__item {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  color: var(--plex-text-muted, rgba(203, 213, 225, 0.65));
  font-size: 0.68rem;
}

.plex-kg-legend__item i {
  display: block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: opacity 0.22s, transform 0.22s;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateX(12px);
}
</style>
