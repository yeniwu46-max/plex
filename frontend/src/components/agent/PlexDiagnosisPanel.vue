<script setup lang="ts">
import type { StudentDiagnoseResult } from '../../api/agentService'

defineProps<{
  result: StudentDiagnoseResult
  loading?: boolean
}>()
</script>

<template>
  <section class="plex-diagnosis" aria-label="AI 学习诊断">
    <header class="plex-diagnosis__head">
      <h3>当前问题诊断</h3>
      <span v-if="result.diagnosis.confidence" class="plex-diagnosis__badge">
        置信度 {{ Math.round(result.diagnosis.confidence * 100) }}%
      </span>
    </header>

    <div v-if="loading" class="plex-diagnosis__skeleton">
      <span /><span /><span />
    </div>

    <template v-else>
      <p class="plex-diagnosis__summary">{{ result.diagnosis.diagnosis }}</p>

      <div class="plex-diagnosis__tags">
        <span class="plex-diagnosis__type">{{ result.diagnosis.errorType }}</span>
        <span v-for="point in result.diagnosis.weakPoints" :key="point">{{ point }}</span>
      </div>

      <article class="plex-diagnosis__block">
        <h4>代码错误解释</h4>
        <p><strong>{{ result.codeAnalysis.codeIssueSummary }}</strong></p>
        <p>{{ result.codeAnalysis.possibleCause }}</p>
        <p class="plex-diagnosis__hint">{{ result.codeAnalysis.fixDirection }}</p>
      </article>

      <article class="plex-diagnosis__block">
        <h4>相关知识点</h4>
        <div class="plex-diagnosis__tags plex-diagnosis__tags--nodes">
          <span v-for="node in result.graphInsight.relatedNodes" :key="node">{{ node }}</span>
        </div>
        <p class="plex-diagnosis__reason">{{ result.graphInsight.graphReason }}</p>
        <small v-if="result.graphInsight.prerequisiteNodes.length">
          前置：{{ result.graphInsight.prerequisiteNodes.join('、') }}
        </small>
      </article>
    </template>
  </section>
</template>

<style scoped>
.plex-diagnosis {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  padding: 0.85rem 1rem;
  border: 1px solid rgba(74, 222, 128, 0.22);
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(6, 30, 20, 0.72), rgba(4, 18, 14, 0.65));
}

.plex-diagnosis__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.plex-diagnosis__head h3 {
  margin: 0;
  color: #bbf7d0;
  font-size: 0.95rem;
  font-weight: 700;
}

.plex-diagnosis__badge {
  padding: 0.12rem 0.45rem;
  border-radius: 999px;
  background: rgba(34, 197, 94, 0.16);
  color: #86efac;
  font-size: 0.72rem;
}

.plex-diagnosis__summary {
  margin: 0;
  color: rgba(226, 232, 240, 0.9);
  font-size: 0.88rem;
  line-height: 1.55;
}

.plex-diagnosis__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.plex-diagnosis__tags span {
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
  background: rgba(34, 197, 94, 0.12);
  color: #86efac;
  font-size: 0.72rem;
}

.plex-diagnosis__type {
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.plex-diagnosis__block {
  padding-top: 0.35rem;
  border-top: 1px solid rgba(74, 222, 128, 0.12);
}

.plex-diagnosis__block h4 {
  margin: 0 0 0.35rem;
  color: #d1fae5;
  font-size: 0.82rem;
  font-weight: 650;
}

.plex-diagnosis__block p {
  margin: 0 0 0.25rem;
  color: rgba(226, 232, 240, 0.82);
  font-size: 0.84rem;
  line-height: 1.5;
}

.plex-diagnosis__hint {
  color: #a7f3d0 !important;
}

.plex-diagnosis__reason,
.plex-diagnosis__block small {
  color: rgba(203, 213, 225, 0.72);
  font-size: 0.78rem;
  line-height: 1.45;
}

.plex-diagnosis__skeleton {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.plex-diagnosis__skeleton span {
  display: block;
  height: 0.65rem;
  border-radius: 6px;
  background: linear-gradient(90deg, rgba(74, 222, 128, 0.08), rgba(74, 222, 128, 0.18), rgba(74, 222, 128, 0.08));
  animation: plex-diagnosis-pulse 1.2s ease-in-out infinite;
}

.plex-diagnosis__skeleton span:nth-child(2) { width: 88%; }
.plex-diagnosis__skeleton span:nth-child(3) { width: 72%; }

@keyframes plex-diagnosis-pulse {
  0%, 100% { opacity: 0.55; }
  50% { opacity: 1; }
}
</style>
