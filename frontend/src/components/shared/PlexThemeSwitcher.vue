<script setup lang="ts">
import { computed, h } from 'vue'
import { NDropdown, NIcon, type DropdownOption } from 'naive-ui'
import { MoonOutline, SunnyOutline, PartlySunnyOutline, PlanetOutline, SparklesOutline } from '@vicons/ionicons5'
import { useThemeStore, type ColorMode } from '../../stores/theme'

const props = withDefaults(
  defineProps<{
    compact?: boolean
    allowVisualStyle?: boolean
  }>(),
  { compact: true, allowVisualStyle: false },
)

const themeStore = useThemeStore()

const currentIcon = computed(() => {
  if (themeStore.mode === 'dark') return MoonOutline
  if (themeStore.mode === 'light') return SunnyOutline
  return PartlySunnyOutline
})

const currentLabel = computed(() => {
  if (themeStore.mode === 'dark') return '深色模式'
  if (themeStore.mode === 'light') return '浅色模式'
  return '跟随系统'
})

const visualLabel = computed(() => themeStore.visualStyle === 'comic' ? '太空漫画' : '经典太空')
const appearanceLabel = computed(() => props.allowVisualStyle ? `${visualLabel.value}，${currentLabel.value}` : currentLabel.value)
const colorOptions: DropdownOption[] = [
  {
    key: 'dark',
    label: '深色模式',
    icon: () => h(NIcon, { component: MoonOutline }),
  },
  {
    key: 'light',
    label: '浅色模式',
    icon: () => h(NIcon, { component: SunnyOutline }),
  },
  {
    key: 'auto',
    label: '跟随系统',
    icon: () => h(NIcon, { component: PartlySunnyOutline }),
  },
]

const options = computed<DropdownOption[]>(() => {
  if (!props.allowVisualStyle) return colorOptions
  return [
    { key: 'style-heading', type: 'group', label: '界面风格', children: [
      { key: 'style-space', label: `经典太空${themeStore.visualStyle === 'space' ? ' ✓' : ''}`, icon: () => h(NIcon, { component: PlanetOutline }) },
      { key: 'style-comic', label: `太空漫画${themeStore.visualStyle === 'comic' ? ' ✓' : ''}`, icon: () => h(NIcon, { component: SparklesOutline }) },
    ] },
    { key: 'style-divider', type: 'divider' },
    { key: 'mode-heading', type: 'group', label: '明暗模式', children: colorOptions },
  ]
})

function handleSelect(key: string) {
  if (props.allowVisualStyle && (key === 'style-space' || key === 'style-comic')) {
    themeStore.setVisualStyle(key === 'style-comic' ? 'comic' : 'space')
  } else if (key === 'dark' || key === 'light' || key === 'auto') {
    themeStore.setMode(key as ColorMode)
  }
}
</script>

<template>
  <n-dropdown
    trigger="click"
    :options="options"
    :value="themeStore.mode"
    @select="handleSelect"
  >
    <button
      type="button"
      class="plex-theme-switcher"
      :aria-label="`当前外观：${appearanceLabel}，点击切换`"
      :title="props.allowVisualStyle ? '切换界面风格与明暗模式' : '切换明暗模式'"
    >
      <n-icon :component="currentIcon" :size="22" />
      <span v-if="!compact" class="plex-theme-switcher__label">{{ currentLabel }}</span>
    </button>
  </n-dropdown>
</template>

<style scoped>
.plex-theme-switcher {
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--plex-text, #edf7ff);
  cursor: pointer;
  transition: background 0.15s;
}

.plex-theme-switcher:hover {
  background: rgba(255, 255, 255, 0.08);
}

.plex-theme-switcher:focus-visible {
  outline: 2px solid var(--plex-primary, #55eee9);
  outline-offset: 3px;
}

html[data-theme='light'] .plex-theme-switcher {
  color: var(--plex-text, #0f172a);
}

html[data-theme='light'] .plex-theme-switcher:hover {
  background: rgba(0, 0, 0, 0.06);
}

.plex-theme-switcher:not([style*='width: 46px']) {
  width: auto;
  padding: 0.4rem 0.85rem;
  border-radius: 8px;
  gap: 0.45rem;
}

.plex-theme-switcher__label {
  font-size: 0.88rem;
  white-space: nowrap;
}
</style>
