<script setup lang="ts">
import { RouterLink } from 'vue-router'
import DashboardShell from '../components/layout/DashboardShell.vue'
</script>

<template>
  <DashboardShell
    active-nav="cabin"
    page-title="管理后台"
    search-placeholder="搜索用户、权限…"
  >
    <section class="placeholder">
      <p class="placeholder__lead">管理员占位页：后续可接用户 / 角色 / 权限与系统配置。</p>
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
  color: #f8fafc;
  background: linear-gradient(90deg, #7c3aed, #5b21b6);
}
</style>
