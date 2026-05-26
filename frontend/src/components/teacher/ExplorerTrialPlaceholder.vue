<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function goTrialArena() {
  void router.push('/trial-arena')
}
</script>

<template>
  <section class="explorer-trial" aria-label="试炼记录">
    <p class="explorer-trial__copy">
      试炼战绩与关卡记录将在「试炼中枢」上线后同步到此档案。当前可先查看班级试炼发布与模板配置。
    </p>
    <button type="button" class="explorer-trial__cta" @click="goTrialArena">前往试炼中枢</button>
  </section>
</template>

<style scoped>
.explorer-trial {
  display: grid;
  gap: 1rem;
  padding: 0.5rem 0;
}

.explorer-trial__copy {
  margin: 0;
  color: var(--teacher-muted);
  font-size: 0.9rem;
  line-height: 1.55;
}

.explorer-trial__cta {
  justify-self: start;
  padding: 0.55rem 1.1rem;
  border: 1px solid rgba(251, 146, 60, 0.45);
  border-radius: 12px;
  background: rgba(251, 146, 60, 0.12);
  color: var(--teacher-orange);
  font-size: 0.88rem;
  font-weight: 650;
  cursor: pointer;
  transition: background 0.15s ease;
}

.explorer-trial__cta:hover {
  background: rgba(251, 146, 60, 0.22);
}
</style>
