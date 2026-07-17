<script setup lang="ts">
import type { TeacherSuggestionResult } from '../../api/agentService'

defineProps<{
  result: TeacherSuggestionResult | null
  loading?: boolean
  error?: string
}>()
</script>

<template>
  <section class="plex-teacher-agent" aria-label="AI 教师建议">
    <header class="plex-teacher-agent__head">
      <h3>AI 教学建议</h3>
      <small>建议仅供参考，不替代教师最终判断</small>
    </header>

    <div v-if="loading" class="plex-teacher-agent__skeleton">
      <span /><span /><span />
    </div>

    <p v-else-if="error" class="plex-teacher-agent__error">{{ error }}</p>

    <template v-else-if="result">
      <p class="plex-teacher-agent__summary">{{ result.classSummary }}</p>

      <article v-if="result.teachingSuggestions.length" class="plex-teacher-agent__block">
        <h4>教学干预建议</h4>
        <ul>
          <li v-for="(item, idx) in result.teachingSuggestions" :key="idx">{{ item }}</li>
        </ul>
      </article>

      <article v-if="result.interventionGroups.length" class="plex-teacher-agent__block">
        <h4>学生分组建议</h4>
        <div
          v-for="group in result.interventionGroups"
          :key="group.groupName"
          class="plex-teacher-agent__group"
        >
          <div class="plex-teacher-agent__group-head">
            <strong>{{ group.groupName }}</strong>
            <span v-if="group.studentCount" class="plex-teacher-agent__group-count">{{ group.studentCount }} 人</span>
          </div>
          <p>{{ group.focus }}</p>
          <div v-if="group.students && group.students.length" class="plex-teacher-agent__members">
            <span v-for="name in group.students" :key="name" class="plex-teacher-agent__member">{{ name }}</span>
          </div>
        </div>
      </article>
    </template>

    <p v-else class="plex-teacher-agent__empty">暂无班级分析，点击「刷新洞察」生成。</p>
  </section>
</template>

<style scoped>
.plex-teacher-agent {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  padding: 1rem 1.05rem;
  border: 1px solid rgba(251, 146, 60, 0.28);
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(42, 22, 8, 0.55), rgba(28, 15, 6, 0.45));
}

.plex-teacher-agent__head h3 {
  margin: 0;
  color: #fed7aa;
  font-size: 1rem;
  font-weight: 700;
}

.plex-teacher-agent__head small {
  color: rgba(254, 215, 170, 0.65);
  font-size: 0.72rem;
}

.plex-teacher-agent__summary {
  margin: 0;
  color: rgba(255, 247, 237, 0.9);
  font-size: 0.88rem;
  line-height: 1.55;
}

.plex-teacher-agent__block h4 {
  margin: 0 0 0.35rem;
  color: #fdba74;
  font-size: 0.82rem;
  font-weight: 650;
}

.plex-teacher-agent__block ul {
  margin: 0;
  padding-left: 1.1rem;
  color: rgba(254, 243, 226, 0.88);
  font-size: 0.84rem;
  line-height: 1.55;
}

.plex-teacher-agent__group {
  padding: 0.45rem 0.55rem;
  margin-top: 0.35rem;
  border-radius: 10px;
  background: rgba(249, 115, 22, 0.1);
}

.plex-teacher-agent__group-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.plex-teacher-agent__group strong {
  color: #fdba74;
  font-size: 0.82rem;
}

.plex-teacher-agent__group-count {
  flex-shrink: 0;
  padding: 0.05rem 0.45rem;
  border-radius: 999px;
  background: rgba(251, 146, 60, 0.18);
  color: #fed7aa;
  font-size: 0.7rem;
  font-weight: 700;
}

.plex-teacher-agent__members {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-top: 0.4rem;
}

.plex-teacher-agent__member {
  padding: 0.1rem 0.5rem;
  border: 1px solid rgba(251, 146, 60, 0.22);
  border-radius: 999px;
  background: rgba(8, 14, 22, 0.5);
  color: rgba(254, 243, 226, 0.9);
  font-size: 0.72rem;
}

.plex-teacher-agent__group p {
  margin: 0.2rem 0 0;
  color: rgba(254, 243, 226, 0.82);
  font-size: 0.8rem;
  line-height: 1.45;
}

.plex-teacher-agent__empty,
.plex-teacher-agent__error {
  margin: 0;
  font-size: 0.84rem;
  line-height: 1.5;
}

.plex-teacher-agent__empty {
  color: rgba(254, 215, 170, 0.72);
}

.plex-teacher-agent__error {
  color: #fca5a5;
}

.plex-teacher-agent__skeleton {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.plex-teacher-agent__skeleton span {
  display: block;
  height: 0.65rem;
  border-radius: 6px;
  background: linear-gradient(90deg, rgba(251, 146, 60, 0.08), rgba(251, 146, 60, 0.2), rgba(251, 146, 60, 0.08));
  animation: plex-teacher-pulse 1.2s ease-in-out infinite;
}

.plex-teacher-agent__skeleton span:nth-child(2) { width: 86%; }
.plex-teacher-agent__skeleton span:nth-child(3) { width: 70%; }

@keyframes plex-teacher-pulse {
  0%, 100% { opacity: 0.55; }
  50% { opacity: 1; }
}
</style>
