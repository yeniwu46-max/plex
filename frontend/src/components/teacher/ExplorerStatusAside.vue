<script setup lang="ts">
import type { RiskTodoItem } from '../../data/teacherExplorerProfile'

defineProps<{
  overallStatus: number
  aiText: string
  todos: RiskTodoItem[]
}>()
</script>

<template>
  <aside class="status-aside" aria-label="学生状态与洞察">
    <section class="status-aside__ring teacher-panel">
      <h2 class="teacher-panel__title">当前状态</h2>
      <div class="status-ring" :style="{ '--progress': `${overallStatus}%` }">
        <strong>{{ overallStatus }}%</strong>
        <span>整体状态</span>
        <small>{{ overallStatus >= 75 ? '状态良好' : overallStatus >= 55 ? '需要关注' : '风险偏高' }}</small>
      </div>
    </section>

    <section class="status-aside__ai teacher-panel">
      <h2 class="teacher-panel__title">AI 观察</h2>
      <div class="ai-scene" aria-hidden="true">
        <span v-for="star in 12" :key="star" class="ai-scene__star" />
      </div>
      <p>{{ aiText }}</p>
    </section>

    <section class="status-aside__todos teacher-panel">
      <h2 class="teacher-panel__title">待办事项</h2>
      <ul>
        <li v-for="item in todos" :key="item.id">
          <span>{{ item.text }}</span>
          <em :class="item.level === '高风险' ? 'is-high' : item.level === '中风险' ? 'is-mid' : 'is-low'">{{ item.level }}</em>
        </li>
      </ul>
    </section>
  </aside>
</template>

<style scoped>
.status-aside {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-height: 0;
  height: 100%;
}

.status-aside > section {
  padding: 1.1rem 1.15rem;
}

.status-aside__title,
.teacher-panel__title {
  margin: 0 0 0.85rem;
  font-size: 1rem;
}

.status-ring {
  --progress: 0%;
  display: grid;
  width: 140px;
  aspect-ratio: 1;
  margin: 0 auto;
  place-items: center;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, #06121f 58%, transparent 59%),
    conic-gradient(var(--teacher-orange, #fb923c) var(--progress), rgba(255, 255, 255, 0.08) 0);
  box-shadow: 0 0 28px rgba(251, 146, 60, 0.25);
}

.status-ring strong {
  color: #fff;
  font-size: 1.75rem;
  transform: translateY(0.5rem);
}

.status-ring span {
  color: var(--teacher-muted);
  font-size: 0.78rem;
  transform: translateY(-1.2rem);
}

.status-ring small {
  color: var(--teacher-orange);
  font-weight: 700;
  transform: translateY(-2.4rem);
}

.status-aside__ai p {
  margin: 0;
  color: rgba(255, 247, 237, 0.82);
  font-size: 0.88rem;
  line-height: 1.65;
}

.ai-scene {
  position: relative;
  height: 64px;
  margin-bottom: 0.65rem;
  border-radius: 12px;
  background: radial-gradient(circle at 30% 40%, rgba(251, 146, 60, 0.15), transparent 55%), #06121f;
  overflow: hidden;
}

.ai-scene__star {
  position: absolute;
  width: 2px;
  height: 2px;
  border-radius: 50%;
  background: #fff;
  opacity: 0.6;
}

.ai-scene__star:nth-child(1) { left: 12%; top: 22%; }
.ai-scene__star:nth-child(2) { left: 28%; top: 55%; }
.ai-scene__star:nth-child(3) { left: 45%; top: 18%; }
.ai-scene__star:nth-child(4) { left: 62%; top: 40%; }
.ai-scene__star:nth-child(5) { left: 78%; top: 28%; }
.ai-scene__star:nth-child(6) { left: 88%; top: 62%; }

.status-aside__todos ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.status-aside__todos li {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  align-items: flex-start;
  color: rgba(255, 247, 237, 0.8);
  font-size: 0.82rem;
}

.status-aside__todos em {
  flex-shrink: 0;
  font-style: normal;
  font-size: 0.72rem;
  font-weight: 800;
  padding: 0.15rem 0.45rem;
  border-radius: 6px;
}

.status-aside__todos .is-high {
  color: #fecaca;
  background: rgba(255, 85, 77, 0.18);
}

.status-aside__todos .is-mid {
  color: #fde68a;
  background: rgba(251, 191, 36, 0.15);
}

.status-aside__todos .is-low {
  color: #a7f3d0;
  background: rgba(52, 211, 153, 0.12);
}

.status-aside__todos {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
</style>
