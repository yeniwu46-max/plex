<script setup lang="ts">
import { ref, watch } from 'vue'
import { NIcon, NInput } from 'naive-ui'
import { CloseCircleOutline, SearchOutline } from '@vicons/ionicons5'
import type { SearchScope } from '../../types/globalSearch'

const props = withDefaults(
  defineProps<{
    variant?: SearchScope
    placeholder?: string
    compact?: boolean
    debounceMs?: number
  }>(),
  {
    variant: 'student',
    placeholder: '搜索当前页面…',
    compact: false,
    debounceMs: 250,
  },
)

const model = defineModel<string>({ default: '' })

const emit = defineEmits<{
  searchSubmit: [query: string]
}>()

const draft = ref(model.value)
let debounceTimer: ReturnType<typeof setTimeout> | undefined

function flushSearch() {
  const q = draft.value.trim()
  model.value = q
  emit('searchSubmit', q)
}

function scheduleSearch() {
  if (debounceTimer !== undefined) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    debounceTimer = undefined
    flushSearch()
  }, props.debounceMs)
}

function onInput(value: string) {
  draft.value = value
  scheduleSearch()
}

function clearSearch() {
  draft.value = ''
  if (debounceTimer !== undefined) {
    clearTimeout(debounceTimer)
    debounceTimer = undefined
  }
  model.value = ''
  emit('searchSubmit', '')
}

watch(
  () => model.value,
  (value) => {
    if (value !== draft.value) draft.value = value
  },
)
</script>

<template>
  <div
    class="plex-local-search"
    :class="[`plex-local-search--${variant}`, { 'plex-local-search--compact': compact }]"
    data-plex-local-search
  >
    <n-input
      :value="draft"
      :placeholder="placeholder"
      clearable
      size="medium"
      class="plex-local-search__input"
      @update:value="onInput"
      @keyup.enter="flushSearch"
      @clear="clearSearch"
    >
      <template #prefix>
        <n-icon :component="SearchOutline" class="plex-local-search__icon" />
      </template>
    </n-input>
    <button
      v-if="draft && !compact"
      type="button"
      class="plex-local-search__clear"
      aria-label="清空搜索"
      @click="clearSearch"
    >
      <n-icon :component="CloseCircleOutline" />
    </button>
  </div>
</template>

<style scoped>
.plex-local-search {
  position: relative;
  width: 100%;
}

.plex-local-search__input :deep(.n-input) {
  --n-border: 1px solid rgba(16, 240, 192, 0.22);
  --n-border-hover: 1px solid rgba(16, 240, 192, 0.38);
  --n-border-focus: 1px solid rgba(16, 240, 192, 0.55);
  --n-box-shadow-focus: 0 0 0 2px rgba(16, 240, 192, 0.12);
  --n-color: rgba(8, 18, 32, 0.72);
  --n-text-color: #edf7ff;
  --n-placeholder-color: rgba(210, 225, 238, 0.58);
  border-radius: 999px;
  backdrop-filter: blur(8px);
}

.plex-local-search--teacher .plex-local-search__input :deep(.n-input) {
  --n-border: 1px solid rgba(251, 146, 60, 0.28);
  --n-border-hover: 1px solid rgba(251, 146, 60, 0.45);
  --n-border-focus: 1px solid rgba(251, 146, 60, 0.62);
  --n-box-shadow-focus: 0 0 0 2px rgba(251, 146, 60, 0.14);
}

.plex-local-search--admin .plex-local-search__input :deep(.n-input) {
  --n-border: 1px solid rgba(167, 139, 250, 0.28);
  --n-border-hover: 1px solid rgba(167, 139, 250, 0.45);
  --n-border-focus: 1px solid rgba(167, 139, 250, 0.62);
  --n-box-shadow-focus: 0 0 0 2px rgba(167, 139, 250, 0.14);
}

.plex-local-search__icon {
  color: rgba(16, 240, 192, 0.75);
}

.plex-local-search--teacher .plex-local-search__icon {
  color: rgba(251, 146, 60, 0.85);
}

.plex-local-search--admin .plex-local-search__icon {
  color: rgba(167, 139, 250, 0.85);
}

.plex-local-search--compact .plex-local-search__input :deep(.n-input) {
  min-height: 36px;
}

.plex-local-search__clear {
  position: absolute;
  right: 0.65rem;
  top: 50%;
  transform: translateY(-50%);
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: rgba(203, 213, 225, 0.75);
  cursor: pointer;
}

html[data-theme='light'] .plex-local-search__input :deep(.n-input) {
  --n-color: rgba(255, 255, 255, 0.92);
  --n-text-color: #0f172a;
  --n-placeholder-color: rgba(100, 116, 139, 0.85);
}
</style>
