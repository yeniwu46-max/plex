<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { destroyActiveTour } from './composables/usePlexTour'
import { NConfigProvider, NMessageProvider, darkTheme, zhCN, dateZhCN } from 'naive-ui'
import { getPlexNaiveOverrides } from './theme/plexTokens'
import { useThemeStore, type PlexPersona } from './stores/theme'
import { useAuthStore } from './stores/auth'

const route = useRoute()
const themeStore = useThemeStore()
const authStore = useAuthStore()
watch(() => [authStore.profile?.id, authStore.profile?.preferences] as const,
  ([id, preferences]) => themeStore.bindAccount(id ?? null, preferences), { immediate: true })

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
    let persona: PlexPersona = 'default'
    if (path.startsWith('/student')) persona = 'student'
    else if (path.startsWith('/teacher')) persona = 'teacher'
    else if (path.startsWith('/admin') || path === '/trial-arena') persona = 'admin'
    themeStore.setPersona(persona)
  },
  { immediate: true },
)

watch(() => themeStore.visualStyle, () => destroyActiveTour())

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
        <div v-if="themeStore.preferenceError" role="status" class="appearance-sync-notice">
          {{ themeStore.preferenceError }} <button type="button" @click="themeStore.persistAppearance">重试同步</button>
        </div>
        <router-view :key="authStore.profile?.id ?? 'guest'" />
      </div>
    </n-message-provider>
  </n-config-provider>
</template>

<style scoped>
.appearance-sync-notice { position: fixed; bottom: 16px; left: 50%; transform: translateX(-50%); z-index: 9999; max-width: calc(100vw - 32px); width: max-content; padding: 12px 18px; background: #11263a; color: #eef7ff; border: 1px solid #f6cd68; border-radius: 12px; }
.appearance-sync-notice button { color: #55eee9; background: transparent; border: 0; text-decoration: underline; cursor: pointer; }
.app-root {
  height: 100%;
  min-height: 100%;
}
</style>
