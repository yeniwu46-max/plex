<script setup lang="ts">
import { computed, defineAsyncComponent, watch } from 'vue'
import { useRoute } from 'vue-router'
import { NConfigProvider, NMessageProvider, darkTheme, zhCN, dateZhCN } from 'naive-ui'
import { getPlexNaiveOverrides } from './theme/plexTokens'
import { useThemeStore } from './stores/theme'
import { useAuthStore } from './stores/auth'
const PlexGuideTour = defineAsyncComponent(() => import('./components/common/PlexGuideTour.vue'))
import type { TourRole } from './composables/usePlexTour'

const route = useRoute()
const themeStore = useThemeStore()
const auth = useAuthStore()

const currentTheme = computed(() => (themeStore.isDark ? darkTheme : null))
const themeOverrides = computed(() =>
  getPlexNaiveOverrides(themeStore.resolvedTheme, themeStore.persona),
)

// 根据路由路径写入角色标记
watch(
  () => route.path,
  (path) => {
    let persona = 'default'
    if (path.startsWith('/student')) persona = 'student'
    else if (path.startsWith('/teacher')) persona = 'teacher'
    else if (path.startsWith('/admin') || path === '/trial-arena') persona = 'admin'
    document.documentElement.dataset.plexPersona = persona
  },
  { immediate: true },
)

/**
 * 当前路由对应的导览角色：
 * - student 账号在 /student 路由 → student tour
 * - teacher 账号在 /teacher 路由 → teacher tour
 * - admin 账号在 /admin 路由 → admin tour（进 /teacher 不触发 teacher tour）
 */
const tourRole = computed<TourRole | null>(() => {
  const role = auth.profile?.role
  const path = route.path
  if (!role) return null
  if (role === 'student' && path.startsWith('/student')) return 'student'
  if (role === 'teacher' && path.startsWith('/teacher')) return 'teacher'
  if (role === 'admin' && path.startsWith('/admin')) return 'admin'
  return null
})

// 只在进入各端"首页"时触发（避免子页面重复触发）
const isRoleHomePage = computed(() => {
  const path = route.path
  return path === '/student' || path === '/teacher' || path === '/admin'
})
</script>

<template>
  <n-config-provider
    :theme="currentTheme"
    :theme-overrides="themeOverrides"
    :locale="zhCN"
    :date-locale="dateZhCN"
  >
    <n-message-provider class="app-root">
      <router-view />
      <plex-guide-tour
        v-if="tourRole && isRoleHomePage"
        :key="tourRole"
        :role="tourRole"
        :auto-start="true"
      />
    </n-message-provider>
  </n-config-provider>
</template>
