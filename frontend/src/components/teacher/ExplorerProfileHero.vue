<script setup lang="ts">
import type { TeacherStudentRow } from '../../api/teacherOverview'
import type { RadarDimension } from '../../data/teacherExplorerProfile'
import { explorerDisplayId, formatLastActive, studentStatusLabel } from '../../data/teacherExplorerProfile'
import AbilityRadarChart from './AbilityRadarChart.vue'

defineProps<{
  student: TeacherStudentRow
  radar: RadarDimension[]
}>()
</script>

<template>
  <header class="profile-hero">
    <div class="profile-hero__identity">
      <span class="profile-hero__ring" aria-hidden="true">
        <span class="profile-hero__avatar">{{ (student.real_name || student.username || '?').slice(0, 1) }}</span>
      </span>
      <div>
        <h2>{{ student.real_name || student.username }}</h2>
        <p>{{ explorerDisplayId(student) }}</p>
        <div class="profile-hero__meta">
          <span>{{ studentStatusLabel(student) }}</span>
          <span>最近活跃 {{ formatLastActive(student.last_activity_at) }}</span>
        </div>
        <div class="profile-hero__badges">
          <span>探索者 Explorer</span>
          <span>中级探索者 Rank</span>
          <span>{{ student.total_points }} 探索积分</span>
        </div>
      </div>
    </div>
    <div class="profile-hero__radar">
      <p class="profile-hero__radar-title">能力雷达图</p>
      <ability-radar-chart :dimensions="radar" />
    </div>
  </header>
</template>

<style scoped>
.profile-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(220px, 0.9fr);
  gap: 1.25rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(130, 212, 255, 0.1);
}

.profile-hero__identity {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}

.profile-hero__ring {
  position: relative;
  display: grid;
  width: 96px;
  height: 96px;
  flex-shrink: 0;
  place-items: center;
  border-radius: 50%;
  background: conic-gradient(from 0deg, var(--teacher-orange), var(--teacher-gold), var(--teacher-orange));
  padding: 3px;
}

.profile-hero__avatar {
  display: grid;
  width: 100%;
  height: 100%;
  place-items: center;
  border-radius: 50%;
  background: linear-gradient(145deg, #1a2740, #f8c59f);
  color: #0b1422;
  font-size: 2rem;
  font-weight: 900;
}

.profile-hero h2 {
  margin: 0;
  color: var(--teacher-text);
  font-size: 1.5rem;
}

.profile-hero p {
  margin: 0.2rem 0 0.5rem;
  color: var(--teacher-muted);
  font-size: 0.85rem;
}

.profile-hero__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  color: var(--teacher-muted);
  font-size: 0.8rem;
}

.profile-hero__meta span:first-child {
  color: #34d399;
  font-weight: 700;
}

.profile-hero__badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-top: 0.65rem;
}

.profile-hero__badges span {
  padding: 0.25rem 0.55rem;
  border: 1px solid rgba(251, 146, 60, 0.25);
  border-radius: 999px;
  background: rgba(251, 146, 60, 0.08);
  color: rgba(255, 247, 237, 0.82);
  font-size: 0.72rem;
}

.profile-hero__radar-title {
  margin: 0 0 0.25rem;
  text-align: center;
  color: var(--teacher-orange);
  font-size: 0.82rem;
  font-weight: 700;
}

@media (max-width: 900px) {
  .profile-hero {
    grid-template-columns: 1fr;
  }
}
</style>
