<script setup lang="ts">
import type { TrialPageRecommendation } from '../../utils/trialPageRecommendation'

defineProps<{
  recommendation: TrialPageRecommendation
  nodeLabel: string
}>()
</script>

<template>
  <aside class="trial-recommend" aria-label="题目推荐逻辑">
    <header class="trial-recommend__head">
      <h2>小E · 推荐逻辑</h2>
      <span>{{ nodeLabel }}</span>
    </header>

    <p v-if="recommendation.recommendedTitle" class="trial-recommend__pick">
      当前优先：<strong>{{ recommendation.recommendedTitle }}</strong>
      <em>匹配 {{ recommendation.matchPercent }}%</em>
    </p>
    <p v-else class="trial-recommend__pick trial-recommend__pick--empty">暂无推荐题目</p>

    <p class="trial-recommend__summary">{{ recommendation.summary }}</p>

    <ol v-if="recommendation.steps.length" class="trial-recommend__steps">
      <li v-for="step in recommendation.steps" :key="step.label">
        <strong>{{ step.label }}</strong>
        <span>{{ step.detail }}</span>
      </li>
    </ol>
  </aside>
</template>

<style scoped>
.trial-recommend {
  position: sticky;
  top: 0.5rem;
  align-self: start;
  padding: 1.1rem 1rem 1.15rem;
  border: 1px solid rgba(90, 208, 255, 0.14);
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(8, 25, 39, 0.88), rgba(4, 15, 26, 0.82));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.trial-recommend__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.85rem;
}

.trial-recommend__head h2 {
  margin: 0;
  color: #fff7ed;
  font-size: 0.98rem;
  font-weight: 700;
}

.trial-recommend__head span {
  flex-shrink: 0;
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
  background: rgba(46, 255, 241, 0.12);
  color: #5fffe8;
  font-size: 0.72rem;
  font-weight: 650;
}

.trial-recommend__pick {
  margin: 0 0 0.65rem;
  color: rgba(226, 232, 240, 0.85);
  font-size: 0.88rem;
  line-height: 1.45;
}

.trial-recommend__pick strong {
  color: #5fffe8;
}

.trial-recommend__pick em {
  display: block;
  margin-top: 0.2rem;
  color: #fb923c;
  font-style: normal;
  font-size: 0.8rem;
  font-weight: 700;
}

.trial-recommend__pick--empty {
  color: rgba(221, 230, 239, 0.55);
}

.trial-recommend__summary {
  margin: 0 0 0.85rem;
  padding: 0.65rem 0.75rem;
  border-radius: 10px;
  background: rgba(6, 18, 31, 0.55);
  color: rgba(221, 230, 239, 0.72);
  font-size: 0.8rem;
  line-height: 1.55;
}

.trial-recommend__steps {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.55rem;
  max-height: min(52vh, 420px);
  overflow-y: auto;
}

.trial-recommend__steps li {
  padding: 0.55rem 0.6rem;
  border: 1px solid rgba(130, 212, 255, 0.08);
  border-radius: 10px;
  background: rgba(4, 12, 20, 0.45);
}

.trial-recommend__steps strong {
  display: block;
  color: #5fffe8;
  font-size: 0.74rem;
  font-weight: 700;
}

.trial-recommend__steps span {
  display: block;
  margin-top: 0.2rem;
  color: rgba(221, 230, 239, 0.62);
  font-size: 0.72rem;
  line-height: 1.45;
}

@media (max-width: 1024px) {
  .trial-recommend {
    position: static;
    margin-top: 0.5rem;
  }

  .trial-recommend__steps {
    max-height: none;
  }
}
</style>
