<script setup lang="ts">
import { computed } from 'vue'
import { useManifest } from '../composables/useManifest'

const props = defineProps<{
  path?: string | null
  label?: string
  variant?: 'student' | 'teacher' | 'default'
}>()

const { demoHref } = useManifest()

const href = computed(() => demoHref(props.path ?? null))
const displayLabel = computed(() => props.label ?? '打开演示')
</script>

<template>
  <a
    v-if="href"
    class="btn"
    :class="{ 'btn--teacher': variant === 'teacher' }"
    :href="href"
    target="_blank"
    rel="noopener"
  >
    {{ displayLabel }} →
  </a>
  <span v-else class="demo-muted">（讲解环节，无现场演示）</span>
</template>

<style scoped>
.demo-muted {
  font-size: 0.85rem;
  color: var(--plex-muted);
}
</style>
