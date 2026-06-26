<script setup lang="ts">
import { computed } from 'vue'
import type { ErrorLayer, StudentDiagnoseResult } from '../../api/agentService'

const props = defineProps<{
  result: StudentDiagnoseResult
  loading?: boolean
}>()

const LAYER_META: Record<ErrorLayer, { label: string; cls: string }> = {
  syntax: { label: '语法层', cls: 'layer-syntax' },
  rule: { label: '规则层', cls: 'layer-rule' },
  logic: { label: '逻辑层', cls: 'layer-logic' },
  transfer: { label: '迁移层', cls: 'layer-transfer' },
  none: { label: '已掌握', cls: 'layer-none' },
}

const MASTERY_META: Record<string, { label: string; cls: string }> = {
  mastered: { label: '已掌握', cls: 'm-mastered' },
  learning: { label: '学习中', cls: 'm-learning' },
  weak: { label: '偏弱', cls: 'm-weak' },
  recommended: { label: '建议复习', cls: 'm-weak' },
  unlearned: { label: '未学', cls: 'm-unlearned' },
  unknown: { label: '未知', cls: 'm-unlearned' },
}

const layer = computed(() => {
  const l = props.result.diagnosis.errorLayer
  return l ? LAYER_META[l] : null
})

const proficiency = computed(() => props.result.diagnosis.proficiencyLabel || '')
const proficiencyReason = computed(() => props.result.diagnosis.proficiencyReason || '')
const isCanButWrong = computed(() => props.result.diagnosis.proficiency === 'can_but_wrong')

const relatedKp = computed(() => props.result.diagnosis.relatedKnowledgePoints || [])
const strategy = computed(() => props.result.diagnosis.remediationStrategy)

function masteryMeta(m: string) {
  return MASTERY_META[m] || MASTERY_META.unknown
}
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
      <div class="plex-diagnosis__judge">
        <span v-if="layer" class="plex-diagnosis__layer" :class="layer.cls">{{ layer.label }}</span>
        <span
          v-if="proficiency"
          class="plex-diagnosis__prof"
          :class="isCanButWrong ? 'is-detail' : 'is-concept'"
        >
          {{ proficiency }}
        </span>
      </div>

      <p class="plex-diagnosis__summary">{{ result.diagnosis.diagnosis }}</p>
      <p v-if="proficiencyReason" class="plex-diagnosis__profreason">
        判别依据：{{ proficiencyReason }}
      </p>

      <article class="plex-diagnosis__block">
        <h4>代码错误解释</h4>
        <p><strong>{{ result.codeAnalysis.codeIssueSummary }}</strong></p>
        <p>{{ result.codeAnalysis.possibleCause }}</p>
        <p class="plex-diagnosis__hint">{{ result.codeAnalysis.fixDirection }}</p>
      </article>

      <article class="plex-diagnosis__block">
        <h4>关联知识点</h4>
        <div v-if="relatedKp.length" class="plex-diagnosis__kplist">
          <span v-for="kp in relatedKp" :key="kp.node" class="plex-diagnosis__kp">
            {{ kp.node }}
            <em class="plex-diagnosis__mastery" :class="masteryMeta(kp.mastery).cls">
              {{ masteryMeta(kp.mastery).label }}
            </em>
          </span>
        </div>
        <div v-else class="plex-diagnosis__tags plex-diagnosis__tags--nodes">
          <span v-for="node in result.graphInsight.relatedNodes" :key="node">{{ node }}</span>
        </div>
        <p class="plex-diagnosis__reason">{{ result.graphInsight.graphReason }}</p>
        <small v-if="result.graphInsight.prerequisiteNodes.length">
          前置：{{ result.graphInsight.prerequisiteNodes.join('、') }}
        </small>
      </article>

      <article v-if="strategy" class="plex-diagnosis__block plex-diagnosis__strategy">
        <h4>建议策略 · {{ strategy.title }}</h4>
        <p class="plex-diagnosis__strategy-detail">{{ strategy.detail }}</p>
        <ol v-if="strategy.steps.length" class="plex-diagnosis__steps">
          <li v-for="(step, idx) in strategy.steps" :key="idx">{{ step }}</li>
        </ol>
        <p v-if="strategy.microExercise" class="plex-diagnosis__micro">
          <strong>微型修复题：</strong>{{ strategy.microExercise }}
        </p>
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

.plex-diagnosis__judge {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.plex-diagnosis__layer,
.plex-diagnosis__prof {
  padding: 0.18rem 0.55rem;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 700;
}

.plex-diagnosis__layer.layer-syntax { background: rgba(250, 204, 21, 0.16); color: #fde047; }
.plex-diagnosis__layer.layer-rule { background: rgba(56, 189, 248, 0.16); color: #7dd3fc; }
.plex-diagnosis__layer.layer-logic { background: rgba(248, 113, 113, 0.16); color: #fca5a5; }
.plex-diagnosis__layer.layer-transfer { background: rgba(167, 139, 250, 0.18); color: #c4b5fd; }
.plex-diagnosis__layer.layer-none { background: rgba(34, 197, 94, 0.16); color: #86efac; }

.plex-diagnosis__prof.is-detail { background: rgba(251, 146, 60, 0.16); color: #fdba74; }
.plex-diagnosis__prof.is-concept { background: rgba(148, 163, 184, 0.18); color: #cbd5e1; }

.plex-diagnosis__profreason {
  margin: -0.2rem 0 0;
  color: rgba(203, 213, 225, 0.72);
  font-size: 0.78rem;
  line-height: 1.45;
}

.plex-diagnosis__kplist {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.plex-diagnosis__kp {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.18rem 0.5rem;
  border-radius: 999px;
  background: rgba(34, 197, 94, 0.1);
  color: #d1fae5;
  font-size: 0.74rem;
}

.plex-diagnosis__mastery {
  font-style: normal;
  padding: 0.02rem 0.32rem;
  border-radius: 999px;
  font-size: 0.66rem;
}

.plex-diagnosis__mastery.m-mastered { background: rgba(34, 197, 94, 0.25); color: #bbf7d0; }
.plex-diagnosis__mastery.m-learning { background: rgba(56, 189, 248, 0.22); color: #bae6fd; }
.plex-diagnosis__mastery.m-weak { background: rgba(251, 146, 60, 0.22); color: #fed7aa; }
.plex-diagnosis__mastery.m-unlearned { background: rgba(148, 163, 184, 0.22); color: #e2e8f0; }

.plex-diagnosis__strategy {
  border-top: 1px solid rgba(74, 222, 128, 0.18);
}

.plex-diagnosis__strategy-detail {
  color: rgba(226, 232, 240, 0.85) !important;
}

.plex-diagnosis__steps {
  margin: 0.35rem 0;
  padding-left: 1.15rem;
  color: rgba(226, 232, 240, 0.85);
  font-size: 0.82rem;
  line-height: 1.55;
}

.plex-diagnosis__steps li {
  margin-bottom: 0.15rem;
}

.plex-diagnosis__micro {
  margin: 0.3rem 0 0;
  padding: 0.45rem 0.55rem;
  border-radius: 10px;
  background: rgba(34, 197, 94, 0.12);
  color: #d1fae5 !important;
  font-size: 0.8rem;
  line-height: 1.5;
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
