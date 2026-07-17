<script setup lang="ts">
import { computed } from 'vue'
import type { LearningPathOrderedNode, NextBestAction, RemediationPath } from '../../api/studentProgress'
import type { AgentTraceStep } from '../../api/agentService'

const props = withDefaults(
  defineProps<{
    orderedNodes: LearningPathOrderedNode[]
    activeNodeId?: string | null
    nextBestAction?: NextBestAction | null
    remediationPaths?: RemediationPath[]
    agentTrace?: { backend?: string; steps?: AgentTraceStep[] } | null
    graphBackend?: string
    loading?: boolean
  }>(),
  {
    orderedNodes: () => [],
    remediationPaths: () => [],
    loading: false,
  },
)

const emit = defineEmits<{
  selectNode: [node: LearningPathOrderedNode]
  action: [action: NextBestAction]
}>()

const displayNodes = computed(() => props.orderedNodes.slice(0, 8))

function masteryPct(node: LearningPathOrderedNode) {
  return Math.round((node.mastery_score ?? 0) * 100)
}

function difficultyLabel(node: LearningPathOrderedNode) {
  const d = node.default_difficulty ?? 1
  if (d <= 1) return '入门'
  if (d === 2) return '进阶'
  return '挑战'
}
</script>

<template>
  <section class="plex-learning-path" aria-label="小E 学习路径">
    <header class="plex-learning-path__head">
      <h3>小E · 学习路径</h3>
    </header>

    <p v-if="loading" class="plex-learning-path__hint">小E 正在为你规划学习顺序…</p>

    <button
      v-if="nextBestAction"
      type="button"
      class="plex-learning-path__nba"
      @click="emit('action', nextBestAction)"
    >
      <strong>下一步建议</strong>
      <p>{{ nextBestAction.reason }}</p>
      <em>{{ nextBestAction.action === 'practice' ? '进入练习' : '先复习前置' }}</em>
    </button>

    <ol v-if="displayNodes.length" class="plex-learning-path__timeline">
      <li
        v-for="node in displayNodes"
        :key="node.id"
        class="plex-learning-path__step"
        :class="{
          'plex-learning-path__step--active': node.id === activeNodeId,
          'plex-learning-path__step--locked': node.locked,
          'plex-learning-path__step--remediation': node.remediation,
        }"
        @click="emit('selectNode', node)"
      >
        <div class="plex-learning-path__step-head">
          <span class="plex-learning-path__order">{{ node.order_index + 1 }}</span>
          <strong>{{ node.label }}</strong>
          <span class="plex-learning-path__diff">{{ difficultyLabel(node) }}</span>
        </div>
        <div class="plex-learning-path__bar">
          <span :style="{ width: `${masteryPct(node)}%` }" />
        </div>
        <p class="plex-learning-path__meta">
          掌握度 {{ masteryPct(node) }}%
          <template v-if="node.locked"> · 前置未满足</template>
          <template v-else-if="node.remediation"> · 补救中</template>
        </p>
        <ul v-if="node.recommended_resources?.length" class="plex-learning-path__resources">
          <li v-for="res in node.recommended_resources.slice(0, 2)" :key="res.id">{{ res.title }}</li>
        </ul>
      </li>
    </ol>

    <div v-if="remediationPaths?.length" class="plex-learning-path__remediation">
      <strong>补救路径</strong>
      <ul>
        <li v-for="(path, idx) in remediationPaths" :key="idx">
          {{ path.steps.join(' → ') }}
        </li>
      </ul>
    </div>

  </section>
</template>

<style scoped>
.plex-learning-path {
  border: 1px solid rgba(56, 189, 248, 0.25);
  border-radius: 12px;
  padding: 14px 16px;
  background: rgba(15, 23, 42, 0.55);
  margin-bottom: 16px;
}

.plex-learning-path__head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.plex-learning-path__head h3 {
  margin: 0;
  font-size: 15px;
}

.plex-learning-path__badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(56, 189, 248, 0.15);
  color: #7dd3fc;
}

.plex-learning-path__nba {
  display: block;
  width: 100%;
  margin-bottom: 12px;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  font-size: 13px;
  line-height: 1.5;
  text-align: left;
  cursor: pointer;
}

.plex-learning-path__nba p {
  margin: 4px 0;
  color: rgba(226, 232, 240, 0.85);
}

.plex-learning-path__timeline {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.plex-learning-path__step {
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(30, 41, 59, 0.6);
  cursor: pointer;
  transition: background 0.15s;
}

.plex-learning-path__step:hover {
  background: rgba(51, 65, 85, 0.7);
}

.plex-learning-path__step--active {
  border: 1px solid rgba(34, 197, 94, 0.5);
}

.plex-learning-path__step--locked {
  opacity: 0.65;
}

.plex-learning-path__step-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.plex-learning-path__order {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(56, 189, 248, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
}

.plex-learning-path__diff {
  font-size: 11px;
  color: #94a3b8;
}

.plex-learning-path__bar {
  height: 4px;
  background: rgba(148, 163, 184, 0.25);
  border-radius: 2px;
  margin: 6px 0 4px;
}

.plex-learning-path__bar span {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #22c55e, #38bdf8);
  border-radius: 2px;
}

.plex-learning-path__meta {
  font-size: 11px;
  color: #94a3b8;
  margin: 0;
}

.plex-learning-path__resources {
  margin: 6px 0 0;
  padding-left: 16px;
  font-size: 11px;
  color: #cbd5e1;
}

.plex-learning-path__remediation {
  margin-top: 12px;
  font-size: 12px;
}

.plex-learning-path__trace {
  margin-top: 12px;
  font-size: 11px;
  color: #94a3b8;
}

.plex-learning-path__trace ul {
  margin: 4px 0 0;
  padding-left: 16px;
}
</style>
