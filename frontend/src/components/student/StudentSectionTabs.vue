<script setup lang="ts">
import { RouterLink } from 'vue-router'

defineProps<{
  area: 'learning' | 'me'
}>()

const groups = {
  learning: [
    { label: '学习路径', to: '/student/star-path', exact: true },
    { label: '个性化资源', to: '/student/star-path/resources', exact: false },
  ],
  me: [
    { label: '学习画像', to: '/student/me/profile', exact: false },
    { label: '成长档案', to: '/student/me/growth', exact: false },
    { label: '账号设置', to: '/student/me/settings', exact: false },
  ],
}
</script>

<template>
  <nav class="section-tabs" :aria-label="area === 'learning' ? '星轨学习导航' : '我的导航'">
    <RouterLink
      v-for="item in groups[area]"
      :key="item.to"
      :to="item.to"
      class="section-tabs__item"
      active-class="section-tabs__item--active"
      :exact="item.exact"
    >
      {{ item.label }}
    </RouterLink>
  </nav>
</template>

<style scoped>
.section-tabs {
  position: relative;
  z-index: 2;
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem var(--plex-page-gutter-x);
  background: transparent;
}
.section-tabs__item {
  padding: 0.55rem 0.9rem;
  border-radius: 999px;
  color: rgba(215, 230, 242, 0.68);
  text-decoration: none;
}
.section-tabs__item:hover,
.section-tabs__item--active {
  color: #52fff1;
  background: rgba(37, 245, 238, 0.1);
  box-shadow: inset 0 0 0 1px rgba(82, 255, 241, 0.35);
}
</style>
