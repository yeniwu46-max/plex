<script setup lang="ts">
import { RouterLink } from 'vue-router'
import DashboardShell from '../components/layout/DashboardShell.vue'
</script>

<template>
  <DashboardShell
    active-nav="cabin"
    page-title="教师工作台"
    search-placeholder="搜索班级、学生…"
  >
    <section class="placeholder">
      <p class="placeholder__lead">教师端占位页：后续可接班级列表、作业批改与学习热力图。</p>
      <div class="placeholder__actions">
        <router-link to="/discovery" class="link-btn">进入探索舱（共用）</router-link>
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
  background: linear-gradient(90deg, #fbbf24, #f59e0b);
}
</style>
