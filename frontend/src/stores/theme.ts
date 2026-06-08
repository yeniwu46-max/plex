import { defineStore } from 'pinia'
import { computed, watch } from 'vue'
import { useColorMode, usePreferredDark } from '@vueuse/core'

export type ColorMode = 'dark' | 'light' | 'auto'
export type PlexPersona = 'student' | 'teacher' | 'admin' | 'default'

const STORAGE_KEY = 'plex-color-mode'
const TRANSITION_CLASS = 'theme-transition'
const TRANSITION_MS = 160

export const useThemeStore = defineStore('theme', () => {
  const prefersDark = usePreferredDark()

  // VueUse 管理 localStorage 持久化 + html[data-theme] 属性写入
  const colorMode = useColorMode({
    attribute: 'data-theme',
    modes: { light: 'light', dark: 'dark', auto: 'auto' },
    storageKey: STORAGE_KEY,
    initialValue: 'dark',
    // VueUse 14.x: emitAuto 让 resolved 在 auto 时自动解析
    emitAuto: true,
  })

  // 用户选择的模式 (dark | light | auto)
  const mode = computed<ColorMode>(() => colorMode.value as ColorMode)

  // 实际生效主题 (dark | light)
  const resolvedTheme = computed<'dark' | 'light'>(() => {
    const m = colorMode.value
    if (m === 'auto') return prefersDark.value ? 'dark' : 'light'
    return (m === 'light' ? 'light' : 'dark') as 'dark' | 'light'
  })

  const isDark = computed(() => resolvedTheme.value === 'dark')

  // 角色标记 (由 App.vue 路由监听来写入，此处只读)
  const persona = computed<PlexPersona>(() => {
    const attr = document.documentElement.dataset.plexPersona
    return (attr as PlexPersona) || 'default'
  })

  function setMode(m: ColorMode) {
    applyTransition()
    colorMode.value = m
  }

  // 兼容旧的 toggle() 调用
  function toggle() {
    const next: ColorMode = resolvedTheme.value === 'dark' ? 'light' : 'dark'
    setMode(next)
  }

  function applyTransition() {
    const el = document.documentElement
    el.classList.add(TRANSITION_CLASS)
    setTimeout(() => el.classList.remove(TRANSITION_CLASS), TRANSITION_MS + 20)
  }

  // 同步 html.dark class 与 data-plex-theme 兼容属性
  watch(
    resolvedTheme,
    (theme) => {
      const el = document.documentElement
      if (theme === 'dark') {
        el.classList.add('dark')
      } else {
        el.classList.remove('dark')
      }
      // 兼容现有 data-plex-theme 选择器
      el.setAttribute('data-plex-theme', theme)
    },
    { immediate: true },
  )

  return {
    mode,
    resolvedTheme,
    isDark,
    persona,
    setMode,
    toggle,
  }
})
