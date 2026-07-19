<script setup lang="ts">
import { computed } from 'vue'
import { NIcon } from 'naive-ui'
import { AlertCircleOutline, CubeOutline, ScanOutline, SparklesOutline } from '@vicons/ionicons5'
import type { OrbitNode } from '../../data/teacherStarfield'

const props = withDefaults(
  defineProps<{
    nodes: OrbitNode[]
    title?: string
    compact?: boolean
  }>(),
  {
    title: '知识星域全景',
    compact: false,
  },
)

const emit = defineEmits<{
  select: [node: OrbitNode]
}>()

const displayNodes = computed(() => {
  const seen = new Map<string, number>()
  return props.nodes.map((node, index) => {
    const key = node.domainKey ?? node.label
    const dup = seen.get(key) ?? 0
    seen.set(key, dup + 1)
    const clampX = (v: number) => Math.min(84, Math.max(14, v))
    const clampY = (v: number) => Math.min(76, Math.max(16, v))
    if (dup === 0) {
      return { ...node, x: clampX(node.x), y: clampY(node.y) }
    }
    const offset = dup * 6
    return {
      ...node,
      x: clampX(node.x + offset),
      y: clampY(node.y + offset * 0.5),
    }
  })
})

function iconForTone(tone: OrbitNode['tone']) {
  if (tone === 'teal') return ScanOutline
  if (tone === 'red') return AlertCircleOutline
  return CubeOutline
}

function nodeKey(node: OrbitNode, index: number) {
  return node.domainKey ? `${node.domainKey}-${index}` : `${node.label}-${index}`
}
</script>

<template>
  <section class="orbit-panel" :class="{ 'orbit-panel--compact': compact }">
    <header v-if="title" class="orbit-panel__head">
      <h2>{{ title }}</h2>
    </header>
    <div class="orbit-map" role="img" :aria-label="title">
      <span class="orbit-center">
        <n-icon :component="SparklesOutline" />
      </span>
      <span v-for="ring in 7" :key="ring" class="orbit-ring" :style="{ '--ring': ring }" />
      <button
        v-for="(node, index) in displayNodes"
        :key="nodeKey(node, index)"
        type="button"
        class="orbit-node"
        :class="`orbit-node--${node.tone}`"
        :style="{ left: `${node.x}%`, top: `${node.y}%`, '--node-index': index }"
        @click="emit('select', node)"
      >
        <span class="orbit-node__halo" aria-hidden="true" />
        <span class="orbit-node__planet">
          <n-icon :component="iconForTone(node.tone)" />
        </span>
        <span class="orbit-node__meta">
          <strong>{{ node.label }}</strong>
          <span class="orbit-node__score-row">
            <em>{{ node.score }}%</em>
            <small :class="{ 'is-down': node.delta === '下降', 'is-flat': node.delta === '稳定' }">{{ node.delta }}</small>
          </span>
        </span>
      </button>
      <div class="orbit-legend">
        <span><i class="good" />掌握良好</span>
        <span><i class="mid" />中等水平</span>
        <span><i class="bad" />高风险</span>
        <span><i class="none" />数据不足</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.orbit-panel {
  position: relative;
  height: 100%;
  min-height: 360px;
  overflow: hidden;
}

.orbit-panel--compact {
  min-height: 360px;
}

.orbit-panel__head h2 {
  margin: 0 0 0.75rem;
  color: var(--teacher-text, #fff7ed);
  font-size: 1.28rem;
  font-weight: 720;
}

.orbit-map {
  position: absolute;
  inset: 2.5rem 0.75rem 3.75rem;
  overflow: hidden;
}

.orbit-panel:not(:has(.orbit-panel__head)) .orbit-map {
  inset: 0.75rem 0.75rem 3.75rem;
}

.orbit-map::before {
  position: absolute;
  inset: 0;
  opacity: 0.55;
  background-image:
    radial-gradient(1px 1px at 14% 34%, rgba(255, 255, 255, 0.5), transparent),
    radial-gradient(1px 1px at 74% 18%, rgba(251, 191, 36, 0.45), transparent),
    radial-gradient(1px 1px at 82% 78%, rgba(251, 191, 36, 0.4), transparent);
  background-size: 160px 160px;
  content: '';
  pointer-events: none;
}

.orbit-ring {
  position: absolute;
  left: 50%;
  top: 52%;
  width: calc(var(--ring) * 82px);
  height: calc(var(--ring) * 34px);
  transform: translate(-50%, -50%) rotate(-8deg);
  border: 1px solid rgba(251, 146, 60, 0.16);
  border-radius: 50%;
  pointer-events: none;
}

.orbit-center {
  position: absolute;
  left: 50%;
  top: 52%;
  z-index: 2;
  display: grid;
  width: 66px;
  height: 66px;
  place-items: center;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  background:
    radial-gradient(circle, rgba(255, 255, 255, 0.95), rgba(251, 146, 60, 0.86) 21%, transparent 58%),
    rgba(251, 146, 60, 0.18);
  color: #fff7ed;
  font-size: 2.3rem;
  box-shadow: 0 0 38px rgba(251, 146, 60, 0.8);
  pointer-events: none;
}

.orbit-node {
  position: absolute;
  z-index: 3;
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  align-items: center;
  gap: 0.55rem;
  width: max-content;
  max-width: min(168px, 38vw);
  padding: 0;
  border: 0;
  background: transparent;
  transform: translate(-26px, -50%);
  color: #fff7ed;
  cursor: pointer;
  text-align: left;
}

.orbit-node::before {
  position: absolute;
  left: 26px;
  top: 26px;
  width: 118px;
  height: 1px;
  transform-origin: left;
  background: linear-gradient(90deg, rgba(251, 146, 60, 0.55), transparent);
  content: '';
  pointer-events: none;
}

.orbit-node__halo {
  position: absolute;
  left: 26px;
  top: 26px;
  width: 52px;
  height: 52px;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  background: radial-gradient(circle, rgba(251, 146, 60, 0.22), transparent 68%);
  animation: orbit-pulse 3.6s ease-in-out infinite;
  animation-delay: calc(var(--node-index, 0) * 0.18s);
  pointer-events: none;
}

.orbit-node__meta {
  display: grid;
  gap: 0.12rem;
  min-width: 0;
}

.orbit-node__score-row {
  display: flex;
  align-items: baseline;
  gap: 0.35rem;
  flex-wrap: nowrap;
}

.orbit-node__planet {
  grid-column: 1;
  grid-row: 1 / span 2;
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border-radius: 50%;
  color: #fff7ed;
  background: rgba(251, 146, 60, 0.12);
  border: 1px solid rgba(251, 146, 60, 0.8);
  box-shadow: 0 0 28px rgba(251, 146, 60, 0.45), 0 0 0 12px rgba(251, 146, 60, 0.06);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.orbit-node:hover .orbit-node__planet {
  transform: scale(1.06);
  box-shadow: 0 0 36px rgba(251, 146, 60, 0.62), 0 0 0 14px rgba(251, 146, 60, 0.08);
}

.orbit-node strong {
  color: rgba(255, 247, 237, 0.92);
  font-size: 0.82rem;
  font-weight: 650;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.orbit-node em {
  color: #ffffff;
  font-size: 1.02rem;
  font-style: normal;
  font-weight: 700;
  white-space: nowrap;
}

.orbit-node small {
  color: #fb923c;
  font-weight: 800;
  font-size: 0.72rem;
  white-space: nowrap;
}

.orbit-node small::before {
  content: '⬆ ';
}

.orbit-node small.is-down {
  color: #ff554d;
}

.orbit-node small.is-down::before {
  content: '⬇ ';
}

.orbit-node small.is-flat {
  color: #fbbf24;
}

.orbit-node small.is-flat::before {
  content: '● ';
}

.orbit-node--teal .orbit-node__planet {
  border-color: rgba(251, 191, 36, 0.78);
  background: rgba(251, 191, 36, 0.12);
  box-shadow: 0 0 26px rgba(251, 191, 36, 0.38), 0 0 0 12px rgba(251, 191, 36, 0.05);
}

.orbit-node--red .orbit-node__planet {
  border-color: rgba(255, 85, 77, 0.82);
  background: rgba(255, 85, 77, 0.12);
  box-shadow: 0 0 26px rgba(255, 85, 77, 0.36), 0 0 0 12px rgba(255, 85, 77, 0.05);
}

.orbit-legend {
  position: absolute;
  left: 50%;
  bottom: 0.15rem;
  z-index: 4;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.85rem 1.25rem;
  transform: translateX(-50%);
  padding: 0.55rem 1rem;
  border: 1px solid rgba(130, 212, 255, 0.08);
  border-radius: 999px;
  background: rgba(2, 11, 18, 0.74);
  color: rgba(221, 230, 239, 0.68);
  white-space: nowrap;
  pointer-events: none;
}

.orbit-legend span {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}

.orbit-legend i {
  width: 9px;
  height: 9px;
  border-radius: 50%;
}

.orbit-legend .good {
  background: var(--teacher-gold, #fbbf24);
}

.orbit-legend .mid {
  background: var(--teacher-orange, #fb923c);
}

.orbit-legend .bad {
  background: #ff554d;
}

.orbit-legend .none {
  background: #94a3b8;
}

@keyframes orbit-pulse {
  0%, 100% { opacity: 0.45; transform: translate(-50%, -50%) scale(1); }
  50% { opacity: 0.9; transform: translate(-50%, -50%) scale(1.12); }
}
</style>
