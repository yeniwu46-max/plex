<script setup lang="ts">
import { computed } from 'vue'
import type { GrowthPoint } from '../../data/teacherExplorerProfile'
import { polylineFromPoints } from '../../data/teacherStarfield'

const props = defineProps<{
  points: GrowthPoint[]
  title?: string
}>()

const values = computed(() => props.points.map((p) => p.value))
const polyline = computed(() => polylineFromPoints(values.value, 360, 100))
</script>

<template>
  <section class="growth-chart">
    <header v-if="title" class="growth-chart__head">
      <h3>{{ title }}</h3>
    </header>
    <svg class="growth-chart__svg" viewBox="0 0 360 110" role="img" aria-label="成长曲线">
      <line v-for="line in 3" :key="line" x1="0" x2="358" :y1="line * 32" :y2="line * 32" class="growth-chart__grid" />
      <polyline :points="polyline" />
      <g class="growth-chart__labels">
        <text v-for="(point, index) in points" :key="point.label" :x="(index / Math.max(1, points.length - 1)) * 340" y="108">
          {{ point.label }}
        </text>
      </g>
    </svg>
  </section>
</template>

<style scoped>
.growth-chart__head h3 {
  margin: 0 0 0.5rem;
  color: var(--teacher-text);
  font-size: 1rem;
  font-weight: 650;
}

.growth-chart__svg {
  width: 100%;
  height: auto;
}

.growth-chart__grid {
  stroke: rgba(221, 230, 239, 0.07);
}

.growth-chart__svg polyline {
  fill: none;
  stroke: var(--teacher-orange, #fb923c);
  stroke-width: 3;
  stroke-linecap: round;
  filter: drop-shadow(0 0 8px rgba(251, 146, 60, 0.4));
}

.growth-chart__labels text {
  fill: var(--teacher-muted);
  font-size: 9px;
}
</style>
