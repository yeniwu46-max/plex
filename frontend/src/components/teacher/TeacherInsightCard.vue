<script setup lang="ts">
defineProps<{
  title?: string
  rate?: number
  subject: string
  copy: string
  showDetail?: boolean
}>()
</script>

<template>
  <section class="insight-card teacher-panel">
    <header class="teacher-panel__head">
      <h2 class="teacher-panel__title">{{ title ?? 'AI 洞察' }}</h2>
      <button v-if="showDetail !== false" type="button" class="insight-card__link">查看详情</button>
    </header>
    <div class="insight-body">
      <div class="mini-orbit" aria-hidden="true">
        <span v-for="ring in 4" :key="ring" :style="{ '--ring': ring }" />
        <i />
      </div>
      <div>
        <p v-if="rate !== undefined">
          <strong>{{ rate }}%</strong> 的 Explorer 在「{{ subject }}」出现理解波动。
        </p>
        <p v-else>「{{ subject }}」是当前班级需要重点关注的星域。</p>
        <small>{{ copy }}</small>
      </div>
    </div>
  </section>
</template>

<style scoped>
.insight-card {
  padding: 1.45rem;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.insight-card__link {
  border: 0;
  background: transparent;
  color: rgba(221, 230, 239, 0.72);
  cursor: pointer;
  font-size: 0.86rem;
}

.insight-body {
  display: grid;
  grid-template-columns: 175px minmax(0, 1fr);
  gap: 1.6rem;
  align-items: center;
  flex: 1;
}

.mini-orbit {
  position: relative;
  height: 145px;
}

.mini-orbit span {
  position: absolute;
  left: 50%;
  top: 50%;
  width: calc(var(--ring) * 42px);
  height: calc(var(--ring) * 27px);
  transform: translate(-50%, -50%) rotate(18deg);
  border: 1px solid rgba(251, 146, 60, 0.22);
  border-radius: 50%;
}

.mini-orbit i {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 18px;
  height: 18px;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  background: #fff7ed;
  box-shadow: 0 0 32px rgba(251, 146, 60, 0.85);
}

.insight-body p {
  margin: 0;
  color: var(--teacher-text, #fff7ed);
  font-size: 1.1rem;
  line-height: 1.75;
}

.insight-body p strong {
  color: var(--teacher-orange, #fb923c);
}

.insight-body small {
  display: block;
  margin-top: 0.7rem;
  color: var(--teacher-muted, rgba(221, 230, 239, 0.62));
  line-height: 1.6;
  font-size: 0.88rem;
}

@media (max-width: 760px) {
  .insight-body {
    grid-template-columns: 1fr;
  }
}
</style>
