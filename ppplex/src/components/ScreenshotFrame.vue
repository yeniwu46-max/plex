<script setup lang="ts">
import { ref } from 'vue'
import { useManifest } from '../composables/useManifest'

defineProps<{
  file: string
  alt?: string
}>()

const { assetUrl } = useManifest()
const open = ref(false)

function close() {
  open.value = false
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') close()
}
</script>

<template>
  <img
    :src="assetUrl(file)"
    :alt="alt ?? file"
    loading="lazy"
    @click="open = true"
  />
  <Teleport to="body">
    <div
      v-if="open"
      class="lightbox"
      role="dialog"
      aria-modal="true"
      @click.self="close"
      @keydown="onKey"
    >
      <button type="button" class="lightbox-close" @click="close">关闭 Esc</button>
      <img :src="assetUrl(file)" :alt="alt ?? file" />
    </div>
  </Teleport>
</template>
