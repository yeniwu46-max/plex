<script setup lang="ts">
import { computed, ref } from 'vue'
import type { TeacherOverview } from '../../api/teacherOverview'

const props = defineProps<{
  heatmap: TeacherOverview['heatmap']
}>()

const hoveredUserId = ref<number | null>(null)

const rows = computed(() => props.heatmap?.rows ?? [])
const days = computed(() => props.heatmap?.days ?? [])

const summary = computed(() => {
  if (!rows.value.length) {
    return { active: 0, medium: 0, low: 0 }
  }
  let active = 0
  let medium = 0
  let low = 0
  for (const row of rows.value) {
    const rate = row.avg_rate ?? 0
    if (rate >= 70) active += 1
    else if (rate >= 40) medium += 1
    else low += 1
  }
  return { active, medium, low }
})

function cellTone(rate: number) {
  if (rate >= 70) return 'high'
  if (rate >= 40) return 'mid'
  if (rate > 0) return 'low'
  return 'empty'
}

</script>

<template>
  <section class="class-heatmap teacher-panel" aria-label="班级学习热力图">
    <header class="teacher-panel__head">
      <h2 class="teacher-panel__title">班级学习热力图</h2>
      <p class="class-heatmap__summary">
        积极 <strong>{{ summary.active }}</strong> 人 · 中等 <strong>{{ summary.medium }}</strong> 人 · 低迷
        <strong>{{ summary.low }}</strong> 人
      </p>
    </header>

    <div v-if="!rows.length" class="class-heatmap__empty">暂无学生委托完成数据</div>

    <div v-else class="class-heatmap__scroll">
      <div class="class-heatmap__grid" :style="{ '--day-count': days.length }">
        <div class="class-heatmap__corner" />
        <div v-for="day in days" :key="day.date" class="class-heatmap__day">{{ day.label }}</div>

        <template v-for="row in rows" :key="row.user_id">
          <div
            class="class-heatmap__name"
            :class="{ 'is-hovered': hoveredUserId === row.user_id }"
            @mouseenter="hoveredUserId = row.user_id"
            @mouseleave="hoveredUserId = null"
          >
            <span>{{ row.student_name }}</span>
            <em>{{ row.avg_rate }}%</em>
          </div>
          <button
            v-for="(cell, idx) in row.cells"
            :key="`${row.user_id}-${cell.date}`"
            type="button"
            class="class-heatmap__cell"
            :class="[`class-heatmap__cell--${cellTone(cell.rate)}`, { 'is-hovered': hoveredUserId === row.user_id }]"
            :title="`${row.student_name} · ${days[idx]?.label ?? cell.date}：${cell.completed}/${cell.total}（${cell.rate}%）`"
            @mouseenter="hoveredUserId = row.user_id"
            @mouseleave="hoveredUserId = null"
          />
        </template>
      </div>
    </div>

    <div class="class-heatmap__legend">
      <span><i class="class-heatmap__cell--high" /> ≥70%</span>
      <span><i class="class-heatmap__cell--mid" /> 40–69%</span>
      <span><i class="class-heatmap__cell--low" /> 1–39%</span>
      <span><i class="class-heatmap__cell--empty" /> 无记录</span>
    </div>
  </section>
</template>

<style scoped>
.class-heatmap {
  padding: 1.35rem 1.45rem 1.2rem;
  min-height: 0;
}

.class-heatmap__summary {
  margin: 0;
  color: var(--teacher-muted);
  font-size: 0.8rem;
}

.class-heatmap__summary strong {
  color: var(--teacher-orange);
  font-weight: 700;
}

.class-heatmap__empty {
  padding: 2rem 0;
  color: var(--teacher-muted);
  font-size: 0.9rem;
  text-align: center;
}

.class-heatmap__scroll {
  margin-top: 0.85rem;
  max-height: 280px;
  overflow: auto;
}

.class-heatmap__grid {
  display: grid;
  grid-template-columns: minmax(108px, 140px) repeat(var(--day-count), minmax(22px, 1fr));
  gap: 4px;
  min-width: min(100%, 520px);
}

.class-heatmap__corner {
  min-height: 24px;
}

.class-heatmap__day {
  color: var(--teacher-muted);
  font-size: 0.68rem;
  text-align: center;
}

.class-heatmap__name {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 0.1rem;
  padding-right: 0.5rem;
  min-width: 0;
}

.class-heatmap__name span {
  overflow: hidden;
  color: var(--teacher-text);
  font-size: 0.78rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.class-heatmap__name em {
  color: var(--teacher-muted);
  font-size: 0.68rem;
  font-style: normal;
}

.class-heatmap__name.is-hovered span,
.class-heatmap__name.is-hovered em {
  color: var(--teacher-orange);
}

.class-heatmap__cell {
  height: 22px;
  border: none;
  border-radius: 4px;
  padding: 0;
  cursor: default;
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}

.class-heatmap__cell.is-hovered {
  transform: scale(1.08);
  box-shadow: 0 0 10px rgba(251, 146, 60, 0.35);
}

.class-heatmap__cell--high {
  background: linear-gradient(180deg, #fb923c, #f97316);
}

.class-heatmap__cell--mid {
  background: rgba(251, 191, 36, 0.55);
}

.class-heatmap__cell--low {
  background: rgba(148, 163, 184, 0.35);
}

.class-heatmap__cell--empty {
  background: rgba(255, 255, 255, 0.06);
}

.class-heatmap__legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.85rem;
  margin-top: 0.85rem;
  color: var(--teacher-muted);
  font-size: 0.72rem;
}

.class-heatmap__legend span {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.class-heatmap__legend i {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 3px;
}
</style>
