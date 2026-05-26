<script setup lang="ts">
import type { TeacherActivity } from '../../api/teacherOverview'

defineProps<{
  activities: TeacherActivity[]
}>()

function formatTime(iso: string | null) {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <section class="class-activity teacher-panel" aria-label="班级最近动态">
    <header class="teacher-panel__head">
      <h2 class="teacher-panel__title">班级动态</h2>
    </header>

    <ul v-if="activities.length" class="class-activity__list">
      <li v-for="item in activities" :key="item.id" class="class-activity__item">
        <span class="class-activity__dot" aria-hidden="true" />
        <div class="class-activity__body">
          <p>
            <strong>{{ item.student_name }}</strong>
            <em :class="{ 'is-negative': item.points < 0 }">
              {{ item.points > 0 ? '+' : '' }}{{ item.points }} XP
            </em>
          </p>
          <small>{{ item.reason || '积分变动' }} · {{ formatTime(item.created_at) }}</small>
        </div>
      </li>
    </ul>

    <p v-else class="class-activity__empty">近期暂无积分动态，学生完成委托或试炼后将显示在这里。</p>
  </section>
</template>

<style scoped>
.class-activity {
  padding: 1.35rem 1.25rem;
  min-height: 0;
}

.class-activity__list {
  margin: 0.75rem 0 0;
  padding: 0;
  list-style: none;
  max-height: 280px;
  overflow: auto;
}

.class-activity__item {
  display: flex;
  gap: 0.65rem;
  padding: 0.55rem 0;
  border-bottom: 1px solid rgba(219, 235, 249, 0.06);
}

.class-activity__item:last-child {
  border-bottom: none;
}

.class-activity__dot {
  width: 8px;
  height: 8px;
  flex-shrink: 0;
  margin-top: 0.35rem;
  border-radius: 50%;
  background: var(--teacher-orange);
  box-shadow: 0 0 8px var(--teacher-orange-glow);
}

.class-activity__body p {
  margin: 0;
  color: var(--teacher-text);
  font-size: 0.86rem;
}

.class-activity__body strong {
  margin-right: 0.35rem;
}

.class-activity__body em {
  color: var(--teacher-gold);
  font-style: normal;
  font-weight: 700;
}

.class-activity__body em.is-negative {
  color: #fca5a5;
}

.class-activity__body small {
  display: block;
  margin-top: 0.2rem;
  color: var(--teacher-muted);
  font-size: 0.74rem;
}

.class-activity__empty {
  margin: 1.5rem 0 0;
  color: var(--teacher-muted);
  font-size: 0.88rem;
  line-height: 1.5;
  text-align: center;
}
</style>
