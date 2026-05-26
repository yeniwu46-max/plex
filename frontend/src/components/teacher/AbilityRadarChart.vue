<script setup lang="ts">
import { computed } from 'vue'
import type { RadarDimension } from '../../data/teacherExplorerProfile'

const props = defineProps<{
  dimensions: RadarDimension[]
}>()

const size = 220
const center = size / 2
const radius = 78

const polygonPoints = computed(() => {
  const count = props.dimensions.length || 6
  return props.dimensions
    .map((dim, index) => {
      const angle = (Math.PI * 2 * index) / count - Math.PI / 2
      const r = (dim.value / 100) * radius
      const x = center + Math.cos(angle) * r
      const y = center + Math.sin(angle) * r
      return `${x},${y}`
    })
    .join(' ')
})

const gridLevels = [0.25, 0.5, 0.75, 1]

function gridPolygon(scale: number) {
  const count = props.dimensions.length || 6
  return Array.from({ length: count }, (_, index) => {
    const angle = (Math.PI * 2 * index) / count - Math.PI / 2
    const r = radius * scale
    const x = center + Math.cos(angle) * r
    const y = center + Math.sin(angle) * r
    return `${x},${y}`
  }).join(' ')
}

function labelPosition(index: number) {
  const count = props.dimensions.length || 6
  const angle = (Math.PI * 2 * index) / count - Math.PI / 2
  const r = radius + 28
  return {
    x: center + Math.cos(angle) * r,
    y: center + Math.sin(angle) * r,
    anchor: Math.abs(Math.cos(angle)) < 0.2 ? 'middle' : Math.cos(angle) > 0 ? 'start' : 'end',
  }
}
</script>

<template>
  <div class="radar" aria-label="能力雷达图">
    <svg :viewBox="`0 0 ${size} ${size}`" class="radar__svg" role="img">
      <g v-for="level in gridLevels" :key="level">
        <polygon :points="gridPolygon(level)" class="radar__grid" />
      </g>
      <g v-for="(_, index) in dimensions" :key="`axis-${index}`">
        <line
          :x1="center"
          :y1="center"
          :x2="labelPosition(index).x"
          :y2="labelPosition(index).y"
          class="radar__axis"
        />
      </g>
      <polygon :points="polygonPoints" class="radar__fill" />
      <text
        v-for="(dim, index) in dimensions"
        :key="dim.key"
        :x="labelPosition(index).x"
        :y="labelPosition(index).y"
        :text-anchor="labelPosition(index).anchor"
        class="radar__label"
      >
        {{ dim.label }}
      </text>
      <text
        v-for="(dim, index) in dimensions"
        :key="`${dim.key}-val`"
        :x="labelPosition(index).x"
        :y="labelPosition(index).y + 14"
        :text-anchor="labelPosition(index).anchor"
        class="radar__value"
      >
        {{ dim.value }}
      </text>
    </svg>
  </div>
</template>

<style scoped>
.radar {
  display: flex;
  justify-content: center;
  align-items: center;
}

.radar__svg {
  width: 100%;
  max-width: 280px;
  height: auto;
}

.radar__grid {
  fill: none;
  stroke: rgba(130, 212, 255, 0.12);
  stroke-width: 1;
}

.radar__axis {
  stroke: rgba(130, 212, 255, 0.1);
  stroke-width: 1;
}

.radar__fill {
  fill: rgba(251, 146, 60, 0.22);
  stroke: var(--teacher-orange, #fb923c);
  stroke-width: 2;
  filter: drop-shadow(0 0 10px rgba(251, 146, 60, 0.35));
}

.radar__label {
  fill: rgba(255, 247, 237, 0.75);
  font-size: 9px;
}

.radar__value {
  fill: var(--teacher-orange, #fb923c);
  font-size: 10px;
  font-weight: 700;
}
</style>
