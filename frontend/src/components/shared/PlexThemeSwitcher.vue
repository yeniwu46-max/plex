<script setup lang="ts">
import { computed, h } from 'vue'
import { NDropdown, NIcon } from 'naive-ui'
import { MoonOutline, SunnyOutline, PartlySunnyOutline } from '@vicons/ionicons5'
import { useThemeStore, type ColorMode } from '../../stores/theme'

withDefaults(
  defineProps<{
    compact?: boolean
  }>(),
  { compact: true },
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

const options = [
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

function handleSelect(key: string) {
  themeStore.setMode(key as ColorMode)
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
      :aria-label="`当前外观：${currentLabel}，点击切换`"
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
