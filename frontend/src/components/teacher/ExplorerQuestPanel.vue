<script setup lang="ts">
import { computed } from 'vue'
import type { HeatmapRow } from '../../api/teacherOverview'
import type { TeacherStudentRow } from '../../api/teacherOverview'

const props = defineProps<{
  student: TeacherStudentRow
  heatmapRow: HeatmapRow | null
}>()

const todaySummary = computed(() => {
  const completed = props.student.today_completed ?? 0
  const total = props.student.today_total ?? 0
  const rate = props.student.today_completion_rate ?? 0
  return { completed, total, rate }
})

const cells = computed(() => props.heatmapRow?.cells ?? [])
</script>

<template>
  <section class="explorer-quest" aria-label="委托完成情况">
    <article class="explorer-quest__today">
      <h3>今日委托</h3>
      <p>
        已完成 <strong>{{ todaySummary.completed }}</strong> / {{ todaySummary.total }} 项
        <span>（{{ todaySummary.rate }}%）</span>
      </p>
      <div class="explorer-quest__bar">
        <i :style="{ width: `${todaySummary.rate}%` }" />
      </div>
    </article>

    <article v-if="cells.length" class="explorer-quest__calendar">
      <h3>周期完成率</h3>
      <div class="explorer-quest__cells">
        <div
          v-for="cell in cells"
          :key="cell.date"
          class="explorer-quest__cell"
          :class="{
            'explorer-quest__cell--high': cell.rate >= 70,
            'explorer-quest__cell--mid': cell.rate >= 40 && cell.rate < 70,
            'explorer-quest__cell--low': cell.rate > 0 && cell.rate < 40,
          }"
          :title="`${cell.date}：${cell.completed}/${cell.total}（${cell.rate}%）`"
        >
          <span>{{ cell.date.slice(5) }}</span>
          <strong>{{ cell.rate }}%</strong>
        </div>
      </div>
    </article>

    <p v-else class="explorer-quest__empty">暂无历史委托完成记录，学生开始今日委托后将显示趋势。</p>
  </section>
</template>

<style scoped>
.explorer-quest {
  display: grid;
  gap: 1.25rem;
}

.explorer-quest h3 {
  margin: 0 0 0.5rem;
  color: var(--teacher-text);
  font-size: 0.95rem;
  font-weight: 650;
}

.explorer-quest__today p {
  margin: 0;
  color: var(--teacher-muted);
  font-size: 0.88rem;
}

.explorer-quest__today strong {
  color: var(--teacher-orange);
  font-size: 1.1rem;
}

.explorer-quest__today span {
  color: var(--teacher-gold);
}

.explorer-quest__bar {
  height: 6px;
  margin-top: 0.65rem;
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.08);
}

.explorer-quest__bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--teacher-orange), var(--teacher-gold));
}

.explorer-quest__cells {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(72px, 1fr));
  gap: 0.5rem;
}

.explorer-quest__cell {
  display: grid;
  gap: 0.2rem;
  padding: 0.45rem 0.35rem;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.05);
  text-align: center;
}

.explorer-quest__cell span {
  color: var(--teacher-muted);
  font-size: 0.68rem;
}

.explorer-quest__cell strong {
  color: var(--teacher-text);
  font-size: 0.82rem;
}

.explorer-quest__cell--high {
  background: rgba(251, 146, 60, 0.18);
}

.explorer-quest__cell--mid {
  background: rgba(251, 191, 36, 0.12);
}

.explorer-quest__cell--low {
  background: rgba(148, 163, 184, 0.12);
}

.explorer-quest__empty {
  margin: 0;
  color: var(--teacher-muted);
  font-size: 0.88rem;
}
</style>
