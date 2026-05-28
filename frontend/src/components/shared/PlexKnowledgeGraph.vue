<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Graph, type GraphData } from '@antv/g6'
import type { KgEdge, KgEdgeType, KgNode, KgNodeStatus } from '../../data/knowledgeGraphData'
import { KG_NODE_STATUS_COLOR, KG_NODE_STATUS_LABEL } from '../../data/knowledgeGraphData'

const props = withDefaults(
  defineProps<{
    nodes: KgNode[]
    edges: KgEdge[]
    mode?: 'student' | 'teacher' | 'admin'
    height?: string
  }>(),
  {
    mode: 'student',
    height: '480px',
  },
)

const emit = defineEmits<{
  nodeClick: [node: KgNode]
}>()

const containerRef = ref<HTMLDivElement>()
let graphInstance: Graph | null = null

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

function buildGraphData(): GraphData {
  const accent = MODE_ACCENT[props.mode] ?? '#22c55e'
  return {
    nodes: props.nodes.map((n) => ({
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
        size: n.level === 'advanced' ? 48 : n.level === 'intermediate' ? 42 : 36,
        fill: KG_NODE_STATUS_COLOR[n.status as KgNodeStatus] + '22',
        stroke: KG_NODE_STATUS_COLOR[n.status as KgNodeStatus],
        lineWidth: n.status === 'recommended' ? 2.5 : 1.5,
        labelText: n.label,
        labelFill: '#e2e8f0',
        labelFontSize: 12,
        labelFontFamily: 'Microsoft YaHei, sans-serif',
        labelOffsetY: 4,
        shadowColor: KG_NODE_STATUS_COLOR[n.status as KgNodeStatus],
        shadowBlur: n.status === 'mastered' || n.status === 'recommended' ? 10 : 0,
        cursor: 'pointer',
        badgeFill: accent,
      },
    })),
    edges: props.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      data: { type: e.type, label: e.label },
      style: {
        stroke: EDGE_COLOR[e.type],
        lineWidth: 1.5,
        endArrow: true,
        endArrowType: 'vee',
        endArrowSize: 8,
        opacity: 0.65,
        labelText: e.label ?? '',
        labelFill: EDGE_LABEL_COLOR[e.type],
        labelFontSize: 10,
      },
    })),
  }
}

async function initGraph() {
  if (!containerRef.value) return
  if (graphInstance) {
    graphInstance.destroy()
    graphInstance = null
  }

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
          return `<div style="padding:8px 12px;background:#0a1628;border:1px solid ${color}33;border-radius:8px;max-width:220px;">
            <strong style="color:${color};font-size:13px;">${node.label}</strong>
            <div style="color:#94a3b8;font-size:11px;margin-top:4px;">${node.domain} · ${statusLabel}</div>
            <div style="color:#cbd5e1;font-size:12px;margin-top:6px;line-height:1.5;">${node.description}</div>
          </div>`
        },
      },
    ],
    data: buildGraphData(),
  })

  await graphInstance.render()

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  graphInstance.on('node:click', (evt: any) => {
    const nodeId = evt?.target?.id ?? evt?.itemId ?? evt?.item?.getID?.()
    const node = props.nodes.find((n) => n.id === nodeId)
    if (node) {
      selectedNode.value = node
      emit('nodeClick', node)
    }
  })
}

onMounted(() => {
  void initGraph()
})

watch(
  () => [props.nodes, props.edges],
  () => {
    if (graphInstance) {
      graphInstance.setData(buildGraphData())
      void graphInstance.render()
    }
  },
  { deep: true },
)

onBeforeUnmount(() => {
  graphInstance?.destroy()
  graphInstance = null
})
</script>

<template>
  <div class="plex-kg-wrap" :class="`plex-kg-wrap--${mode}`">
    <div ref="containerRef" class="plex-kg-canvas" :style="{ height }" />

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
  background: linear-gradient(135deg, rgba(3, 10, 20, 0.96), rgba(5, 14, 26, 0.92));
  border: 1px solid rgba(130, 212, 255, 0.1);
}

.plex-kg-wrap--student { border-color: rgba(34, 197, 94, 0.15); }
.plex-kg-wrap--teacher { border-color: rgba(249, 115, 22, 0.15); }
.plex-kg-wrap--admin { border-color: rgba(129, 140, 248, 0.15); }

.plex-kg-canvas {
  width: 100%;
}

.plex-kg-detail {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 220px;
  padding: 1rem;
  border-radius: 10px;
  background: rgba(5, 14, 26, 0.92);
  border: 1px solid rgba(130, 212, 255, 0.18);
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
  color: #fff;
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
  color: rgba(203, 213, 225, 0.65);
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
