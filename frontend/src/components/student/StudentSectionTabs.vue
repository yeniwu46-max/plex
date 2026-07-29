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
.section-tabs{display:flex;gap:.5rem;padding:.75rem var(--plex-page-gutter-x);border-bottom:1px solid rgba(37,245,238,.1);background:rgba(2,12,21,.72)}.section-tabs__item{padding:.55rem .9rem;border-radius:999px;color:rgba(215,230,242,.68);text-decoration:none}.section-tabs__item:hover,.section-tabs__item--active{color:#52fff1;background:rgba(37,245,238,.1)}
</style>
