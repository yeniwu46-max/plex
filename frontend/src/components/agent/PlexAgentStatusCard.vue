<script setup lang="ts">
import type { AgentStatusItem } from '../../api/agentService'

defineProps<{
  agent: AgentStatusItem
}>()

const STATUS_LABEL: Record<AgentStatusItem['status'], string> = {
  idle: '待机',
  running: '运行中',
  success: '就绪',
  error: '异常',
}
</script>

<template>
  <article class="plex-agent-card" :data-status="agent.status">
    <header>
      <h4>{{ agent.name }}</h4>
      <span>{{ STATUS_LABEL[agent.status] }}</span>
    </header>
    <p>{{ agent.role }}</p>
    <footer>
      <small v-if="agent.lastRunAt">最近：{{ new Date(agent.lastRunAt).toLocaleString('zh-CN') }}</small>
      <small v-if="agent.avgLatency != null">均延迟 {{ agent.avgLatency }}ms</small>
    </footer>
  </article>
</template>

<style scoped>
.plex-agent-card {
  padding: 0.75rem 0.85rem;
  border-radius: 12px;
  border: 1px solid rgba(129, 140, 248, 0.22);
  background: rgba(15, 23, 42, 0.55);
}

.plex-agent-card[data-status='running'] {
  border-color: rgba(56, 189, 248, 0.45);
  box-shadow: 0 0 12px rgba(56, 189, 248, 0.15);
}

.plex-agent-card[data-status='success'] {
  border-color: rgba(34, 197, 94, 0.35);
}

.plex-agent-card[data-status='error'] {
  border-color: rgba(248, 113, 113, 0.4);
}

.plex-agent-card header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.35rem;
  margin-bottom: 0.35rem;
}

.plex-agent-card h4 {
  margin: 0;
  color: #e0e7ff;
  font-size: 0.86rem;
  font-weight: 700;
}

.plex-agent-card header span {
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
  background: rgba(99, 102, 241, 0.18);
  color: #c7d2fe;
  font-size: 0.68rem;
}

.plex-agent-card p {
  margin: 0 0 0.45rem;
  color: rgba(203, 213, 225, 0.78);
  font-size: 0.76rem;
  line-height: 1.45;
}

.plex-agent-card footer {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 0.65rem;
}

.plex-agent-card footer small {
  color: rgba(148, 163, 184, 0.85);
  font-size: 0.68rem;
}
</style>
