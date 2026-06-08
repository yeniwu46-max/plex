<script setup lang="ts">
defineProps<{
  progress: number
  status?: 'uploading' | 'success' | 'error' | 'queued'
}>()
</script>

<template>
  <div class="plex-upload-progress" role="progressbar" :aria-valuenow="progress" aria-valuemin="0" aria-valuemax="100">
    <div class="plex-upload-progress__track">
      <div
        class="plex-upload-progress__fill"
        :class="{
          'plex-upload-progress__fill--success': status === 'success',
          'plex-upload-progress__fill--error': status === 'error',
        }"
        :style="{ width: `${progress}%` }"
      />
    </div>
    <span class="plex-upload-progress__label">{{ progress }}%</span>
  </div>
</template>
