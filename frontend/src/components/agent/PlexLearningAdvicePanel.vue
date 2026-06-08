<script setup lang="ts">
import type { StudentDiagnoseResult } from '../../api/agentService'

defineProps<{
  result: StudentDiagnoseResult
  loading?: boolean
}>()
</script>

<template>
  <section class="plex-advice" aria-label="AI 学习建议">
    <header class="plex-advice__head">
      <h3>下一步推荐</h3>
      <span class="plex-advice__diff">{{ result.recommendation.estimatedDifficulty === 'easy' ? '入门巩固' : '稳步提升' }}</span>
    </header>

    <div v-if="loading" class="plex-advice__skeleton">
      <span /><span /><span />
    </div>

    <template v-else>
      <p class="plex-advice__focus">
        重点：<strong>{{ result.recommendation.nextKnowledgePoint }}</strong>
      </p>

      <ul v-if="result.recommendation.recommendedExercises.length" class="plex-advice__list">
        <li v-for="ex in result.recommendation.recommendedExercises" :key="ex">{{ ex }}</li>
      </ul>

      <ol v-if="result.feedback.stepHints.length" class="plex-advice__hints">
        <li v-for="(hint, idx) in result.feedback.stepHints" :key="idx">{{ hint }}</li>
      </ol>

      <p class="plex-advice__encourage">{{ result.feedback.encouragement }}</p>
      <p class="plex-advice__action">{{ result.feedback.nextAction }}</p>
    </template>
  </section>
</template>

<style scoped>
.plex-advice {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  padding: 0.85rem 1rem;
  border: 1px solid rgba(52, 211, 153, 0.18);
  border-radius: 14px;
  background: rgba(4, 24, 18, 0.55);
}

.plex-advice__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.plex-advice__head h3 {
  margin: 0;
  color: #bbf7d0;
  font-size: 0.95rem;
  font-weight: 700;
}

.plex-advice__diff {
  padding: 0.12rem 0.45rem;
  border-radius: 999px;
  background: rgba(16, 185, 129, 0.14);
  color: #6ee7b7;
  font-size: 0.72rem;
}

.plex-advice__focus {
  margin: 0;
  color: rgba(226, 232, 240, 0.88);
  font-size: 0.86rem;
}

.plex-advice__focus strong {
  color: #a7f3d0;
}

.plex-advice__list,
.plex-advice__hints {
  margin: 0;
  padding-left: 1.15rem;
  color: rgba(226, 232, 240, 0.85);
  font-size: 0.84rem;
  line-height: 1.55;
}

.plex-advice__encourage {
  margin: 0.15rem 0 0;
  color: #86efac;
  font-size: 0.84rem;
  line-height: 1.5;
}

.plex-advice__action {
  margin: 0;
  padding: 0.45rem 0.55rem;
  border-radius: 10px;
  background: rgba(34, 197, 94, 0.1);
  color: #d1fae5;
  font-size: 0.82rem;
  line-height: 1.45;
}

.plex-advice__skeleton {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.plex-advice__skeleton span {
  display: block;
  height: 0.65rem;
  border-radius: 6px;
  background: linear-gradient(90deg, rgba(52, 211, 153, 0.08), rgba(52, 211, 153, 0.18), rgba(52, 211, 153, 0.08));
  animation: plex-advice-pulse 1.2s ease-in-out infinite;
}

.plex-advice__skeleton span:nth-child(2) { width: 80%; }
.plex-advice__skeleton span:nth-child(3) { width: 65%; }

@keyframes plex-advice-pulse {
  0%, 100% { opacity: 0.55; }
  50% { opacity: 1; }
}
</style>
