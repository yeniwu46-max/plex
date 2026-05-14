<script setup lang="ts">
import { RouterLink } from 'vue-router'
import DashboardShell from '../components/layout/DashboardShell.vue'
</script>

<template>
  <DashboardShell
    active-nav="cabin"
    page-title="学生首页"
    search-placeholder="搜索课程、任务、知识点…"
  >
    <section class="placeholder">
      <p class="placeholder__lead">欢迎回来。此处为「学生端」占位首页，后续可接入课表、推荐与进度总览。</p>
      <div class="placeholder__actions">
        <router-link to="/discovery" class="link-btn">进入探索舱</router-link>
        <router-link to="/star-path" class="link-btn link-btn--ghost">星轨路径（图谱 / 编辑器示例）</router-link>
      </div>
    </section>
  </DashboardShell>
</template>

<style scoped>
.placeholder {
  position: relative;
  z-index: 1;
  padding: 1.5rem 1.25rem 2rem;
  max-width: 42rem;
}
.placeholder__lead {
  margin: 0 0 1.25rem;
  line-height: 1.65;
  color: rgba(226, 232, 240, 0.85);
  font-size: 0.95rem;
}
.placeholder__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}
.link-btn {
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 1rem;
  border-radius: 999px;
  font-size: 0.9rem;
  font-weight: 600;
  text-decoration: none;
  color: #020617;
  background: linear-gradient(90deg, #00f5d4, #00c9ae);
}
.link-btn--ghost {
  background: transparent;
  color: #00f5d4;
  border: 1px solid rgba(0, 245, 212, 0.45);
}
</style>
