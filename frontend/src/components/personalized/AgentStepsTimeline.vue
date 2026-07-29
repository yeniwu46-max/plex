<script setup lang="ts">
/**
 * 多智能体协作时间线：可视化资源生成任务中各智能体（画像解释 → 知识检索 →
 * 教学设计 → 资源生成 → 质量审核）的实时状态、耗时与依赖顺序。
 */
import { computed } from 'vue'
import type { AgentTraceStep } from '../../api/personalizedResources'
import { xiaoEResourceStepLabel } from '../../utils/xiaoEPersona'

const props = defineProps<{ steps: AgentTraceStep[] }>()

const STATUS_META: Record<string, { label: string; cls: string }> = {
  pending: { label: '等待中', cls: 'is-pending' },
  running: { label: '进行中', cls: 'is-running' },
  completed: { label: '已完成', cls: 'is-completed' },
  failed: { label: '失败', cls: 'is-failed' },
}

const items = computed(() =>
  (props.steps ?? []).map((step) => {
    const meta = STATUS_META[step.status] ?? STATUS_META.pending!
    return {
      key: step.agent,
      name: step.name || xiaoEResourceStepLabel(step.agent),
      statusLabel: meta.label,
      statusCls: meta.cls,
      latency:
        typeof step.latency_ms === 'number' && step.latency_ms > 0
          ? step.latency_ms >= 1000
            ? `${(step.latency_ms / 1000).toFixed(1)}s`
            : `${Math.round(step.latency_ms)}ms`
          : '',
      backend: step.backend && step.backend !== 'in_process' ? step.backend : '',
      error: step.error || '',
    }
  }),
)
</script>

<template>
  <ol v-if="items.length" class="agent-timeline" aria-label="智能体协作进度">
    <li v-for="(item, idx) in items" :key="item.key" class="agent-timeline__step" :class="item.statusCls">
      <span class="agent-timeline__dot" aria-hidden="true">
        <svg v-if="item.statusCls === 'is-completed'" viewBox="0 0 12 12" width="10" height="10">
          <path d="M2 6.2 5 9l5-6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <i v-else-if="item.statusCls === 'is-running'" class="agent-timeline__spin" />
        <b v-else-if="item.statusCls === 'is-failed'">!</b>
      </span>
      <span v-if="idx < items.length - 1" class="agent-timeline__link" aria-hidden="true" />
      <div class="agent-timeline__body">
        <strong>{{ item.name }}</strong>
        <small>
          {{ item.statusLabel }}<template v-if="item.latency"> · {{ item.latency }}</template>
          <template v-if="item.backend"> · {{ item.backend }}</template>
        </small>
        <small v-if="item.error" class="agent-timeline__error">{{ item.error }}</small>
      </div>
    </li>
  </ol>
</template>

<style scoped>
.agent-timeline {
  display: flex;
  gap: 0;
  margin: 0.75rem 0 0;
  padding: 0;
  list-style: none;
  overflow-x: auto;
}

.agent-timeline__step {
  position: relative;
  flex: 1 1 0;
  min-width: 108px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 0 0.4rem;
}

.agent-timeline__dot {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 2px solid rgba(120, 160, 180, 0.4);
  background: rgba(2, 12, 21, 0.9);
  color: #25f5ee;
  z-index: 1;
}

.agent-timeline__link {
  position: absolute;
  top: 11px;
  left: calc(50% + 13px);
  width: calc(100% - 26px);
  height: 2px;
  background: rgba(120, 160, 180, 0.25);
}

.is-completed .agent-timeline__dot {
  border-color: #25f5ee;
  background: rgba(37, 245, 238, 0.15);
}

.is-completed + .agent-timeline__step .agent-timeline__link,
.is-completed .agent-timeline__link {
  background: rgba(37, 245, 238, 0.45);
}

.is-running .agent-timeline__dot {
  border-color: #ffc56d;
}

.agent-timeline__spin {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 2px solid rgba(255, 197, 109, 0.35);
  border-top-color: #ffc56d;
  animation: agent-step-spin 0.8s linear infinite;
}

@keyframes agent-step-spin {
  to {
    transform: rotate(360deg);
  }
}

.is-failed .agent-timeline__dot {
  border-color: #ff9da5;
  color: #ff9da5;
}

.is-failed .agent-timeline__dot b {
  font-style: normal;
  font-size: 0.8rem;
}

.agent-timeline__body {
  margin-top: 0.45rem;
  display: grid;
  gap: 0.1rem;
}

.agent-timeline__body strong {
  font-size: 0.78rem;
  color: #dcEEf5;
  font-weight: 600;
  line-height: 1.3;
}

.is-pending .agent-timeline__body strong {
  color: rgba(220, 238, 245, 0.5);
}

.agent-timeline__body small {
  color: rgba(150, 180, 195, 0.85);
  font-size: 0.7rem;
}

.agent-timeline__error {
  color: #ff9da5 !important;
}
</style>
