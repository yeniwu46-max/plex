<script setup lang="ts">
import { NIcon } from 'naive-ui'
import { CodeSlashOutline, LockClosedOutline, ServerOutline } from '@vicons/ionicons5'
import {
  formatStarPathGems,
  isStarPathNodeUnlocked,
  starPathNodeTrackClass,
  type StarPathNode,
} from '../../data/starPathTrail'

const props = defineProps<{
  nodes: StarPathNode[]
  selectedId: string
  variant?: 'seven' | 'four'
}>()

const emit = defineEmits<{
  select: [node: StarPathNode]
}>()

function nodeIcon(node: StarPathNode) {
  if (node.status === 'locked') return LockClosedOutline
  if (node.icon === 'server') return ServerOutline
  return CodeSlashOutline
}

function nodePositionClasses(node: StarPathNode) {
  return [
    `track-node--${starPathNodeTrackClass(node)}`,
    node.position !== 'center' ? `track-node--${node.position}` : '',
    node.anchor ? `track-node--anchor-${node.anchor}` : '',
    { 'track-node--selected': props.selectedId === node.id },
  ]
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
</script>

<template>
  <div class="path-track">
    <div class="path-orbits" aria-hidden="true">
      <span class="orbit orbit--outer" />
      <span class="orbit orbit--middle" />
      <span class="orbit orbit--inner" />
    </div>
    <svg class="path-lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <filter :id="`trackGlow-${variant ?? 'seven'}`" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="0.35" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <g fill="none" :filter="`url(#trackGlow-${variant ?? 'seven'})`">
        <template v-if="variant === 'four'">
          <path class="path-line path-line--done" d="M19.5 46.2 C28 41 38 38 50.5 35.5" />
          <path class="path-line path-line--active" d="M56.2 34.5 C66 27 78 18 89.5 12.2" />
          <path class="path-line path-line--active" d="M50.2 40.2 C42 54 34 70 30.2 82.8" />
          <path class="path-line path-line--locked" d="M32.2 84.4 C52 78 72 68 90.8 58.2" />
        </template>
        <template v-else>
          <path class="path-line path-line--locked" d="M8.5 75.2 C9.5 66 12 56 17.5 48.5" />
          <path class="path-line path-line--done" d="M19.5 46.2 C28 41 38 38 50.5 35.5" />
          <path class="path-line path-line--active" d="M56.2 34.5 C66 27 78 18 89.5 12.2" />
          <path class="path-line path-line--active" d="M50.2 40.2 C42 54 34 70 30.2 82.8" />
          <path class="path-line path-line--active" d="M32.2 84.4 C52 78 72 68 90.8 58.2" />
          <path class="path-line path-line--locked" d="M7.2 12.5 C16 17 32 26 49.2 35.2" />
        </template>
      </g>
    </svg>

    <div
      v-for="node in nodes"
      :key="node.id"
      class="track-node"
      :class="nodePositionClasses(node)"
      role="button"
      :tabindex="isStarPathNodeUnlocked(node) ? 0 : -1"
      :aria-label="`${displayId(node)} ${node.title}${node.status === 'locked' ? '，未解锁' : ''}`"
      @click="onNodeClick(node)"
      @keydown.enter.prevent="onNodeClick(node)"
      @keydown.space.prevent="onNodeClick(node)"
    >
      <span v-if="node.status === 'current'" class="track-node__badge">当前所在</span>
      <span class="track-node__orb">
        <n-icon :component="nodeIcon(node)" />
      </span>
      <strong>{{ displayId(node) }}</strong>
      <p>
        {{ node.title }}<template v-if="node.titleLine2"><br />{{ node.titleLine2 }}</template>
      </p>
      <em>{{ formatStarPathGems(node.gems) }}</em>
    </div>

    <div class="legend">
      <span><i class="legend__dot legend__dot--done" /> 已完成</span>
      <span><i class="legend__dot legend__dot--active" /> 进行中</span>
      <span><i class="legend__dot legend__dot--locked" /> 未解锁</span>
    </div>
  </div>
</template>

<style scoped>
.path-track {
  position: absolute;
  inset: 1.75rem 0.35rem 3rem 0.15rem;
  transform: none;
  transform-origin: center center;
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
  stroke-width: 0.34;
  stroke-dasharray: 2.4 2.4;
}

.path-line--done {
  stroke: rgba(35, 255, 222, 0.72);
}

.path-line--active {
  stroke: rgba(35, 255, 222, 0.86);
}

.path-line--locked {
  stroke: rgba(224, 237, 247, 0.58);
}

.track-node {
  --node-color: #26ffee;
  --node-orb: 52px;
  position: absolute;
  display: grid;
  width: max-content;
  max-width: 92px;
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
  border: 1px solid color-mix(in srgb, var(--node-color) 62%, transparent);
  border-radius: 50%;
  background:
    radial-gradient(circle, color-mix(in srgb, var(--node-color) 28%, transparent), transparent 66%),
    rgba(5, 17, 29, 0.96);
  color: #eaffff;
  box-shadow:
    0 0 0 5px color-mix(in srgb, var(--node-color) 9%, transparent),
    0 0 20px color-mix(in srgb, var(--node-color) 24%, transparent);
}

.track-node__orb .n-icon {
  font-size: 1.35rem;
}

.track-node strong {
  margin-top: 0.4rem;
  color: rgba(255, 255, 255, 0.88);
  font-size: 0.82rem;
}

.track-node p {
  margin: 0.06rem 0 0;
  color: rgba(240, 247, 255, 0.88);
  font-size: 0.78rem;
  line-height: 1.3;
}

.track-node em {
  margin-top: 0.18rem;
  color: #23ffde;
  font-size: 0.62rem;
  font-style: normal;
  letter-spacing: 0.1em;
}

.track-node--anchor-left {
  max-width: 88px;
  transform: translate(0, -50%);
  justify-items: start;
  text-align: left;
}

.track-node--anchor-right {
  max-width: 88px;
  transform: translate(-100%, -50%);
  justify-items: end;
  text-align: right;
}

.track-node--current {
  --node-color: #23ffde;
  --node-orb: 68px;
  left: 52%;
  top: 36%;
  z-index: 3;
  max-width: 96px;
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
  filter: drop-shadow(0 0 14px rgba(37, 245, 238, 0.45));
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

.track-node--n2 {
  left: 19%;
  top: 47%;
  z-index: 2;
}

.track-node--n3 {
  left: 30%;
  top: 86%;
  z-index: 1;
}

.track-node--n4 {
  left: 92%;
  top: 60%;
  z-index: 1;
}

.track-node--n5 {
  left: 92%;
  top: 11%;
  z-index: 2;
}

.track-node--n6 {
  left: 5%;
  top: 10%;
  z-index: 1;
}

.track-node--n7 {
  left: 3%;
  top: 77%;
  z-index: 1;
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
