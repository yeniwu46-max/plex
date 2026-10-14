import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { useColorMode, usePreferredDark, useStorage } from '@vueuse/core'

export type ColorMode = 'dark' | 'light' | 'auto'
export type PlexPersona = 'student' | 'teacher' | 'admin' | 'default'
export type VisualStyle = 'space' | 'comic'

const STORAGE_KEY = 'plex-color-mode'
const VISUAL_STYLE_KEY = 'plex-visual-style'
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

  // 风格与明暗分别持久化；老用户默认保留经典太空。
  const savedVisualStyle = useStorage<string>(VISUAL_STYLE_KEY, 'space')
  const visualStyle = computed<VisualStyle>(() => savedVisualStyle.value === 'comic' ? 'comic' : 'space')
  const persona = ref<PlexPersona>('default')
  const isComic = computed(() => persona.value === 'student' && visualStyle.value === 'comic')

  function setVisualStyle(style: VisualStyle) {
    savedVisualStyle.value = style
  }

  function setPersona(next: PlexPersona) {
    persona.value = next
  }

  // 根节点门控也覆盖挂载到 body 的菜单与引导，离开学生端后立即还原。
  watch([persona, isComic], ([role, comic]) => {
    document.documentElement.dataset.plexPersona = role
    document.documentElement.dataset.plexStyle = comic ? 'comic' : 'space'
  }, { immediate: true, flush: 'sync' })

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
    visualStyle,
    isComic,
    setVisualStyle,
    setPersona,
    setMode,
    toggle,
  }
})
