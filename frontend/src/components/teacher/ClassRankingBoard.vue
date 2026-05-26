<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { TeacherRankingItem } from '../../api/teacherOverview'

const props = defineProps<{
  ranking: TeacherRankingItem[]
}>()

const router = useRouter()

const medal = ['🥇', '🥈', '🥉']

function goExplorer(userId: number) {
  void router.push({ path: '/teacher/explorers', query: { studentId: String(userId) } })
}
</script>

<template>
  <section class="class-ranking teacher-panel" aria-label="班级排名看板">
    <header class="teacher-panel__head">
      <h2 class="teacher-panel__title">排名看板</h2>
      <span class="class-ranking__hint">本周积分</span>
    </header>

    <ul v-if="ranking.length" class="class-ranking__list">
      <li v-for="item in ranking" :key="item.user_id">
        <button type="button" class="class-ranking__row" @click="goExplorer(item.user_id)">
          <span class="class-ranking__rank">
            <template v-if="item.rank <= 3">{{ medal[item.rank - 1] }}</template>
            <template v-else>{{ item.rank }}</template>
          </span>
          <span class="class-ranking__name">{{ item.student_name }}</span>
          <span class="class-ranking__meta">
            <strong>{{ item.points }}</strong> XP · Lv{{ item.level }}
          </span>
          <span class="class-ranking__ach">🏆×{{ item.achievements_count }}</span>
        </button>
      </li>
    </ul>

    <p v-else class="class-ranking__empty">暂无排名数据，请先为学生积累积分记录。</p>
  </section>
</template>

<style scoped>
.class-ranking {
  padding: 1.35rem 1.25rem;
  min-height: 0;
}

.class-ranking__hint {
  color: var(--teacher-muted);
  font-size: 0.78rem;
}

.class-ranking__list {
  margin: 0.75rem 0 0;
  padding: 0;
  list-style: none;
  max-height: 320px;
  overflow: auto;
}

.class-ranking__row {
  display: grid;
  grid-template-columns: 2rem minmax(0, 1fr) auto auto;
  gap: 0.5rem 0.65rem;
  align-items: center;
  width: 100%;
  padding: 0.55rem 0.35rem;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s ease;
}

.class-ranking__row:hover {
  background: rgba(251, 146, 60, 0.08);
}

.class-ranking__rank {
  color: var(--teacher-orange);
  font-size: 0.95rem;
  font-weight: 800;
  text-align: center;
}

.class-ranking__name {
  overflow: hidden;
  color: var(--teacher-text);
  font-size: 0.88rem;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.class-ranking__meta {
  color: var(--teacher-muted);
  font-size: 0.76rem;
  white-space: nowrap;
}

.class-ranking__meta strong {
  color: var(--teacher-gold);
  font-weight: 700;
}

.class-ranking__ach {
  color: var(--teacher-muted);
  font-size: 0.72rem;
  white-space: nowrap;
}

.class-ranking__empty {
  margin: 1.5rem 0 0;
  color: var(--teacher-muted);
  font-size: 0.88rem;
  text-align: center;
}
</style>
