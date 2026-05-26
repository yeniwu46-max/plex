<script setup lang="ts">
import { computed } from 'vue'
import { polylineFromPoints } from '../../data/teacherStarfield'

const props = defineProps<{
  label: string
  value: string
  delta: string
  points: number[]
}>()

const polyline = computed(() => polylineFromPoints(props.points, 200, 56))
</script>

<template>
  <article class="spark-card teacher-panel">
    <div class="spark-card__top">
      <span>{{ label }}</span>
      <em>{{ delta }}</em>
    </div>
    <strong>{{ value }}</strong>
    <svg class="spark-card__chart" viewBox="0 0 200 56" role="img" :aria-label="`${label}趋势`">
      <polyline :points="polyline" />
    </svg>
  </article>
</template>

<style scoped>
.spark-card {
  padding: 1.1rem 1.25rem;
  min-height: 120px;
}

.spark-card__top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--teacher-muted);
  font-size: 0.82rem;
}

.spark-card__top em {
  color: #34d399;
  font-style: normal;
  font-weight: 700;
}

.spark-card strong {
  display: block;
  margin: 0.35rem 0 0.5rem;
  color: var(--teacher-text);
  font-size: 1.65rem;
  font-weight: 650;
}

.spark-card__chart {
  width: 100%;
  height: 48px;
}

.spark-card__chart polyline {
  fill: none;
  stroke: var(--teacher-orange, #fb923c);
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-linejoin: round;
  filter: drop-shadow(0 0 6px rgba(251, 146, 60, 0.4));
}
</style>
