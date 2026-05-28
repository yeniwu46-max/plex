<script setup lang="ts">
import { useManifest } from '../composables/useManifest'

defineProps<{
  title: string
  subtitle?: string
}>()

const { manifest, a3Base } = useManifest()
</script>

<template>
  <header class="defense-header">
    <div>
      <h1>{{ title }}</h1>
      <p v-if="subtitle">{{ subtitle }}</p>
    </div>
    <div class="defense-header__actions">
      <a class="btn btn--ghost" :href="a3Base" target="_blank" rel="noopener">打开 A3 前端</a>
      <span class="defense-header__ver">v{{ manifest.meta.version }}</span>
    </div>
  </header>
</template>

<style scoped>
.defense-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.25rem 2rem;
  border-bottom: 1px solid var(--plex-border);
  background: rgba(6, 18, 32, 0.85);
}

.defense-header h1 {
  margin: 0;
  font-size: 1.5rem;
}

.defense-header p {
  margin: 0.25rem 0 0;
  color: var(--plex-muted);
  font-size: 0.95rem;
}

.defense-header__actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.defense-header__ver {
  font-size: 0.75rem;
  color: var(--plex-muted);
}
</style>
