<script setup lang="ts">
import { computed } from 'vue'
import type { AgentTraceStep } from '../../api/agentService'

const props = defineProps<{
  trace?: AgentTraceStep[]
  loading?: boolean
}>()

const PIPELINE = [
  { id: 'learning_diagnosis', name: '学习诊断', icon: '🔍' },
  { id: 'code_analysis', name: '代码分析', icon: '🧩' },
  { id: 'knowledge_graph', name: '知识图谱', icon: '🌐' },
  { id: 'learning_path', name: '学习路径', icon: '🧭' },
  { id: 'feedback', name: '反馈生成', icon: '💬' },
]

const steps = computed(() =>
  PIPELINE.map((stage) => {
    const hit = props.trace?.find((t) => t.agentId === stage.id)
    return {
      ...stage,
      status: hit?.status ?? (props.loading ? 'running' : 'pending'),
      latencyMs: hit?.latencyMs,
      summary: hit?.summary ?? (props.loading ? '智能体协作处理中…' : ''),
    }
  }),
)

const totalLatency = computed(() =>
  (props.trace ?? []).reduce((sum, t) => sum + (t.latencyMs || 0), 0),
)
</script>

<template>
  <section class="plex-trace" aria-label="智能体协作过程">
    <header class="plex-trace__head">
      <h3>智能体协作流程</h3>
      <span v-if="totalLatency > 0" class="plex-trace__total">
        共 {{ Math.round(totalLatency) }} ms
      </span>
      <span v-else-if="loading" class="plex-trace__total plex-trace__total--live">运行中</span>
    </header>

    <ol class="plex-trace__list">
      <li
        v-for="(step, idx) in steps"
        :key="step.id"
        class="plex-trace__item"
        :class="`is-${step.status}`"
      >
        <span class="plex-trace__node">
          <span class="plex-trace__icon">{{ step.icon }}</span>
          <span v-if="idx < steps.length - 1" class="plex-trace__line" />
        </span>
        <div class="plex-trace__body">
          <p class="plex-trace__name">
            {{ step.name }}
            <span v-if="step.latencyMs != null" class="plex-trace__ms">{{ Math.round(step.latencyMs) }}ms</span>
            <span v-if="step.status === 'running'" class="plex-trace__dot" aria-label="处理中" />
          </p>
          <p v-if="step.summary" class="plex-trace__summary">{{ step.summary }}</p>
        </div>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.plex-trace {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  padding: 0.85rem 1rem;
  border: 1px solid rgba(56, 189, 248, 0.22);
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(8, 24, 40, 0.7), rgba(4, 14, 26, 0.6));
}

.plex-trace__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.plex-trace__head h3 {
  margin: 0;
  color: #bae6fd;
  font-size: 0.95rem;
  font-weight: 700;
}

.plex-trace__total {
  padding: 0.12rem 0.45rem;
  border-radius: 999px;
  background: rgba(56, 189, 248, 0.16);
  color: #7dd3fc;
  font-size: 0.72rem;
}

.plex-trace__total--live {
  animation: plex-trace-blink 1s ease-in-out infinite;
}

.plex-trace__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
}

.plex-trace__item {
  display: flex;
  gap: 0.65rem;
  min-height: 2.6rem;
}

.plex-trace__node {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.plex-trace__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.7rem;
  height: 1.7rem;
  border-radius: 50%;
  font-size: 0.85rem;
  background: rgba(148, 163, 184, 0.15);
  border: 1px solid rgba(148, 163, 184, 0.3);
  transition: all 0.3s ease;
}

.plex-trace__line {
  flex: 1;
  width: 2px;
  margin: 2px 0;
  background: rgba(148, 163, 184, 0.22);
}

.plex-trace__item.is-success .plex-trace__icon {
  background: rgba(34, 197, 94, 0.2);
  border-color: rgba(74, 222, 128, 0.5);
}

.plex-trace__item.is-running .plex-trace__icon {
  background: rgba(56, 189, 248, 0.22);
  border-color: rgba(56, 189, 248, 0.6);
  animation: plex-trace-pulse 1.1s ease-in-out infinite;
}

.plex-trace__item.is-error .plex-trace__icon {
  background: rgba(248, 113, 113, 0.2);
  border-color: rgba(248, 113, 113, 0.55);
}

.plex-trace__item.is-pending .plex-trace__icon {
  opacity: 0.5;
}

.plex-trace__body {
  padding-bottom: 0.45rem;
}

.plex-trace__name {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: #e2e8f0;
  font-size: 0.85rem;
  font-weight: 600;
}

.plex-trace__ms {
  color: #7dd3fc;
  font-size: 0.7rem;
  font-weight: 400;
}

.plex-trace__dot {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 50%;
  background: #38bdf8;
  animation: plex-trace-blink 0.9s ease-in-out infinite;
}

.plex-trace__summary {
  margin: 0.15rem 0 0;
  color: rgba(203, 213, 225, 0.78);
  font-size: 0.78rem;
  line-height: 1.45;
}

@keyframes plex-trace-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.12); }
}

@keyframes plex-trace-blink {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}
</style>
