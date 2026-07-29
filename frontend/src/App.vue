<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { destroyActiveTour } from './composables/usePlexTour'
import { NConfigProvider, NMessageProvider, darkTheme, zhCN, dateZhCN } from 'naive-ui'
import { getPlexNaiveOverrides } from './theme/plexTokens'
import { useThemeStore } from './stores/theme'

const route = useRoute()
const themeStore = useThemeStore()

const currentTheme = computed(() => (themeStore.isDark ? darkTheme : null))
const themeOverrides = computed(() =>
  getPlexNaiveOverrides(themeStore.resolvedTheme, themeStore.persona),
)

// 根据路由路径写入角色标记
watch(
  () => route.path,
  (path, previous) => {
    const prevArea = previous?.startsWith('/student')
      ? 'student'
      : previous?.startsWith('/teacher')
        ? 'teacher'
        : previous?.startsWith('/admin')
          ? 'admin'
          : 'other'
    const nextArea = path.startsWith('/student')
      ? 'student'
      : path.startsWith('/teacher')
        ? 'teacher'
        : path.startsWith('/admin')
          ? 'admin'
          : 'other'
    // 仅跨角色区域时销毁引导，避免同端页面跳转抖动
    if (previous && prevArea !== nextArea) {
      destroyActiveTour()
    }
    let persona = 'default'
    if (path.startsWith('/student')) persona = 'student'
    else if (path.startsWith('/teacher')) persona = 'teacher'
    else if (path.startsWith('/admin') || path === '/trial-arena') persona = 'admin'
    document.documentElement.dataset.plexPersona = persona
  },
  { immediate: true },
)

</script>

<template>
  <n-config-provider
    :theme="currentTheme"
    :theme-overrides="themeOverrides"
    :locale="zhCN"
    :date-locale="dateZhCN"
  >
    <n-message-provider>
      <div class="app-root">
        <router-view />
      </div>
    </n-message-provider>
  </n-config-provider>
</template>
