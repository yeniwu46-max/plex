<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { NIcon } from 'naive-ui'
import { CodeSlashOutline, LockClosedOutline, ServerOutline } from '@vicons/ionicons5'
import {
  isStarPathNodeUnlocked,
  starPathNodeTrackClass,
  type StarPathNode,
} from '../../data/starPathTrail'
import { useMapViewport } from '../../composables/useMapViewport'
import { bezierPath, computeDagreLayout, lineGradientId } from '../../utils/starPathTrackLayout'

const props = defineProps<{
  nodes: StarPathNode[]
  selectedId: string
  highlightGemSlot?: number
  variant?: 'seven' | 'four'
  domainKey?: string
}>()

const layoutKey = computed(() => props.domainKey ?? 'data-vars')
const viewportRef = ref<HTMLElement | null>(null)

const { transformStyle, isDragging, onWheel, onPointerDown, onPointerMove, onPointerUp, fitView } =
  useMapViewport(viewportRef)

onMounted(() => {
  fitView()
})

watch(
  () => [props.nodes.length, layoutKey.value],
  () => {
    fitView()
  },
)

const emit = defineEmits<{
  select: [node: StarPathNode]
  selectGem: [payload: { node: StarPathNode; slot: number }]
}>()

type LineStatus = 'done' | 'active' | 'locked'

const nodePositions = computed(() =>
  computeDagreLayout(props.nodes, layoutKey.value),
)

const connectionPaths = computed(() => {
  const nodes = props.nodes
  if (nodes.length < 2) return []

  return nodes.slice(0, -1).map((fromNode, index) => {
    const toNode = nodes[index + 1]!
    const from = nodePositions.value[fromNode.id] ?? { x: 50, y: 50 }
    const to = nodePositions.value[toNode.id] ?? { x: 50, y: 50 }
    return {
      key: `${fromNode.id}-${toNode.id}`,
      d: bezierPath(from, to),
      status: lineStatus(fromNode, toNode),
    }
  })
})

function lineStatus(fromNode: StarPathNode, toNode: StarPathNode): LineStatus {
  if (toNode.status === 'locked') return 'locked'
  if (fromNode.status === 'done' && toNode.status === 'done') return 'done'
  if (fromNode.status === 'locked') return 'locked'
  return 'active'
}

function nodeIcon(node: StarPathNode) {
  if (node.status === 'locked') return LockClosedOutline
  if (node.icon === 'server') return ServerOutline
  return CodeSlashOutline
}

function nodePositionClasses(node: StarPathNode) {
  return [
    `track-node--${starPathNodeTrackClass(node)}`,
    node.anchor ? `track-node--anchor-${node.anchor}` : '',
    { 'track-node--selected': props.selectedId === node.id },
  ]
}

function nodeStyle(node: StarPathNode) {
  const pos = nodePositions.value[node.id] ?? { x: 50, y: 42 }
  return {
    left: `${pos.x}%`,
    top: `${pos.y}%`,
  }
}

function displayId(node: StarPathNode) {
  if (props.variant === 'four' && node.id.includes('-')) {
    const parts = node.id.split('-')
    return parts[parts.length - 1] ?? node.id
  }
  return node.id
}

function onNodeClick(node: StarPathNode) {
  emit('select', node)
}

function onGemClick(event: MouseEvent, node: StarPathNode, slot: number) {
  event.stopPropagation()
  emit('selectGem', { node, slot })
}

function gemSlots(node: StarPathNode) {
  return node.gems?.length ? node.gems.length : node.questionIds.length || 5
}
</script>

<template>
  <div
    ref="viewportRef"
    class="path-viewport"
    :class="{ 'path-viewport--dragging': isDragging }"
    @wheel="onWheel"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointercancel="onPointerUp"
  >
    <div class="path-viewport__inner" :style="transformStyle">
      <div class="path-track" :class="layoutKey ? `path-track--${layoutKey}` : ''">
        <div class="path-orbits" aria-hidden="true">
          <span class="orbit orbit--outer" />
          <span class="orbit orbit--middle" />
          <span class="orbit orbit--inner" />
        </div>
        <svg class="path-lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <defs>
            <linearGradient :id="lineGradientId('done', variant ?? 'four')" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="rgba(18,216,200,0.35)" />
              <stop offset="100%" stop-color="rgba(35,255,222,0.92)" />
            </linearGradient>
            <linearGradient :id="lineGradientId('active', variant ?? 'four')" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="rgba(56,189,248,0.55)" />
              <stop offset="100%" stop-color="rgba(35,255,222,1)" />
            </linearGradient>
            <linearGradient :id="lineGradientId('locked', variant ?? 'four')" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="rgba(148,163,184,0.25)" />
              <stop offset="100%" stop-color="rgba(148,163,184,0.45)" />
            </linearGradient>
            <filter :id="`trackGlow-${variant ?? 'four'}`" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="0.35" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <marker
              :id="`arrow-${variant ?? 'four'}`"
              markerWidth="5"
              markerHeight="5"
              refX="4"
              refY="2.5"
              orient="auto"
            >
              <path d="M0,0 L5,2.5 L0,5 Z" fill="rgba(35,255,222,0.85)" />
            </marker>
          </defs>
          <g fill="none" :filter="`url(#trackGlow-${variant ?? 'four'})`">
            <path
              v-for="segment in connectionPaths"
              :key="segment.key"
              class="path-line"
              :class="`path-line--${segment.status}`"
              :d="segment.d"
              :stroke="`url(#${lineGradientId(segment.status, variant ?? 'four')})`"
              :marker-end="segment.status !== 'locked' ? `url(#arrow-${variant ?? 'four'})` : undefined"
            />
          </g>
        </svg>

        <div
          v-for="node in nodes"
          :key="node.id"
          class="track-node"
          :class="nodePositionClasses(node)"
          :style="nodeStyle(node)"
          role="button"
          :tabindex="isStarPathNodeUnlocked(node) ? 0 : -1"
          :aria-label="`${displayId(node)} ${node.title}${node.status === 'locked' ? '，未解锁' : ''}`"
          @click.stop="onNodeClick(node)"
          @keydown.enter.prevent="onNodeClick(node)"
          @keydown.space.prevent="onNodeClick(node)"
        >
          <span v-if="node.status === 'current'" class="track-node__badge">当前所在</span>
          <span class="track-node__orb">
            <n-icon :component="nodeIcon(node)" />
          </span>
          <strong>{{ displayId(node) }}</strong>
          <p class="track-node__label">
            {{ node.title }}<template v-if="node.titleLine2"><br />{{ node.titleLine2 }}</template>
          </p>
          <div class="track-node__gems" role="group" :aria-label="`${node.title} 试炼进度`">
            <button
              v-for="slot in gemSlots(node)"
              :key="`${node.id}-gem-${slot - 1}`"
              type="button"
              class="track-gem"
              :class="[
                `track-gem--${node.gems?.[slot - 1] ?? 'pending'}`,
                { 'track-gem--selected': props.selectedId === node.id && slot - 1 === (props.highlightGemSlot ?? 0) },
              ]"
              :disabled="node.gems?.[slot - 1] === 'locked'"
              :title="`试炼 s${slot - 1}`"
              :aria-label="`切换到第 ${slot} 题 s${slot - 1}`"
              @click="onGemClick($event, node, slot - 1)"
            />
          </div>
        </div>
      </div>
    </div>

    <div class="legend">
      <span><i class="legend__dot legend__dot--done" /> 已完成</span>
      <span><i class="legend__dot legend__dot--active" /> 进行中</span>
      <span><i class="legend__dot legend__dot--locked" /> 未解锁</span>
    </div>
  </div>
</template>

<style scoped>
.path-viewport {
  position: absolute;
  inset: 0;
  overflow: hidden;
  cursor: grab;
  touch-action: none;
}

.path-viewport--dragging {
  cursor: grabbing;
}

.path-viewport__inner {
  position: absolute;
  inset: 0;
  transform-origin: center center;
  will-change: transform;
}

.path-track {
  position: absolute;
  inset: 1.5rem 0.5rem 3.25rem 0.25rem;
  transform: none;
  transform-origin: center center;
}

.path-track::before {
  content: '';
  position: absolute;
  inset: 8% 4%;
  pointer-events: none;
  background:
    linear-gradient(rgba(35, 255, 222, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(35, 255, 222, 0.04) 1px, transparent 1px);
  background-size: 24px 24px;
  mask-image: radial-gradient(circle at 50% 45%, black 35%, transparent 88%);
  opacity: 0.55;
}

.path-orbits {
  position: absolute;
  z-index: 0;
  inset: 0;
  pointer-events: none;
}

.orbit {
  position: absolute;
  left: 50%;
  top: 44%;
  border: 1px solid rgba(40, 238, 219, 0.12);
  border-radius: 50%;
  transform: translate(-50%, -50%) rotate(-14deg);
}

.orbit--outer {
  width: min(100%, 920px);
  height: 460px;
  border-color: rgba(143, 190, 221, 0.08);
}

.orbit--middle {
  width: min(82%, 700px);
  height: 340px;
  border-style: dashed;
}

.orbit--inner {
  width: min(56%, 440px);
  height: 220px;
}

.path-lines {
  position: absolute;
  z-index: 0;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.path-line {
  stroke-width: 0.48;
  stroke-linecap: round;
}

.path-line--done {
  stroke-width: 0.44;
}

.path-line--active {
  stroke-width: 0.56;
}

.path-line--locked {
  stroke-dasharray: 1.6 2.4;
}

.track-node {
  --node-color: #26ffee;
  --node-orb: 60px;
  position: absolute;
  z-index: 2;
  display: grid;
  width: max-content;
  max-width: 128px;
  justify-items: center;
  align-items: center;
  text-align: center;
  color: #ffffff;
  transform: translate(-50%, -50%);
  cursor: pointer;
}

.track-node__orb {
  position: relative;
  z-index: 1;
  display: grid;
  width: var(--node-orb);
  aspect-ratio: 1;
  place-items: center;
  border: 1px solid color-mix(in srgb, var(--node-color) 68%, transparent);
  border-radius: 50%;
  background:
    radial-gradient(circle at 35% 28%, rgba(255, 255, 255, 0.12), transparent 42%),
    radial-gradient(circle, color-mix(in srgb, var(--node-color) 32%, transparent), transparent 68%),
    rgba(5, 17, 29, 0.96);
  color: #eaffff;
  box-shadow:
    0 0 0 6px color-mix(in srgb, var(--node-color) 10%, transparent),
    0 0 24px color-mix(in srgb, var(--node-color) 28%, transparent);
}

.track-node strong {
  margin-top: 0.45rem;
  color: rgba(255, 255, 255, 0.92);
  font-size: 0.76rem;
  line-height: 1.25;
  word-break: break-all;
  letter-spacing: 0.02em;
}

.track-node__label {
  margin: 0.08rem 0 0;
  color: rgba(240, 247, 255, 0.86);
  font-size: 0.72rem;
  line-height: 1.35;
  max-width: 112px;
}

.track-node__gems {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.38rem;
  margin-top: 0.4rem;
  max-width: 128px;
}

.track-gem {
  width: 13px;
  height: 13px;
  padding: 0;
  border: 0;
  transform: rotate(45deg);
  border-radius: 2px;
  background: rgba(130, 212, 255, 0.32);
  cursor: pointer;
  box-shadow: 0 0 0 1.5px rgba(130, 212, 255, 0.18);
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease;
}

.track-gem--done {
  background: linear-gradient(135deg, #23ffde, #0891b2);
  box-shadow: 0 0 8px rgba(35, 255, 222, 0.42);
}

.track-gem--active,
.track-gem--selected {
  background: linear-gradient(135deg, #5ffff3, #12d8c8);
  box-shadow: 0 0 14px rgba(35, 255, 222, 0.65);
  transform: rotate(45deg) scale(1.15);
}

.track-gem--locked {
  background: rgba(125, 135, 145, 0.45);
  cursor: not-allowed;
  box-shadow: none;
}

.track-gem--pending:hover:not(:disabled) {
  background: rgba(56, 189, 248, 0.55);
}

.track-node__orb .n-icon {
  font-size: 1.35rem;
}

.track-node strong {
  margin-top: 0.4rem;
  color: rgba(255, 255, 255, 0.88);
  font-size: 0.78rem;
  line-height: 1.25;
  word-break: break-all;
}

.track-node p {
  margin: 0.06rem 0 0;
  color: rgba(240, 247, 255, 0.88);
  font-size: 0.74rem;
  line-height: 1.35;
  max-width: 104px;
}

.track-node em {
  margin-top: 0.18rem;
  color: #23ffde;
  font-size: 0.58rem;
  font-style: normal;
  letter-spacing: 0.06em;
  white-space: nowrap;
}

.track-node--anchor-left {
  max-width: 104px;
  transform: translate(0, -50%);
  justify-items: start;
  text-align: left;
}

.track-node--anchor-right {
  max-width: 104px;
  transform: translate(-100%, -50%);
  justify-items: end;
  text-align: right;
}

.track-node--current {
  --node-color: #23ffde;
  --node-orb: 68px;
  z-index: 3;
  max-width: 124px;
}

.track-node--current .track-node__orb {
  box-shadow:
    0 0 0 8px rgba(35, 255, 222, 0.12),
    0 0 32px rgba(35, 255, 222, 0.48);
}

.track-node--current .track-node__orb .n-icon {
  font-size: 1.55rem;
}

.track-node__badge {
  position: absolute;
  bottom: calc(100% + 0.35rem);
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
  margin-bottom: 0;
  padding: 0.25rem 0.5rem;
  border-radius: 0.35rem;
  background: rgba(16, 240, 192, 0.16);
  color: #22ffde;
  font-size: 0.78rem;
  font-weight: 720;
}

.track-node--done {
  --node-color: #23ffde;
}

.track-node--progress {
  --node-color: #23ffde;
}

.track-node--selected {
  filter: drop-shadow(0 0 16px rgba(37, 245, 238, 0.52));
}

.track-node--selected .track-node__orb {
  box-shadow:
    0 0 0 8px rgba(35, 255, 222, 0.14),
    0 0 32px rgba(35, 255, 222, 0.52);
}

.track-node--locked {
  --node-color: #d7e6ef;
}

.track-node--locked .track-node__orb {
  opacity: 0.72;
}

.track-node--locked em {
  color: rgba(230, 240, 247, 0.58);
}

.legend {
  position: absolute;
  z-index: 5;
  right: 1.45rem;
  bottom: 1.25rem;
  display: flex;
  gap: 1.3rem;
  padding: 0.35rem 0.5rem;
  border-radius: 0.4rem;
  background: rgba(4, 14, 24, 0.72);
  color: rgba(224, 237, 247, 0.68);
  font-size: 0.78rem;
  pointer-events: none;
}

.legend span {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}

.legend__dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  transform: rotate(45deg);
}

.legend__dot--done {
  background: #23ffde;
}

.legend__dot--active {
  background: #38bdf8;
}

.legend__dot--locked {
  background: #7d8791;
}
</style>
