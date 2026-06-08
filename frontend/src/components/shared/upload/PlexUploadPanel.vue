<script setup lang="ts">
import { computed } from 'vue'
import type { UploadFileEntry } from '../../../types/upload'
import { formatFileSize } from '../../../config/upload/uploadPresets'

const props = defineProps<{
  files: UploadFileEntry[]
  isUploading: boolean
}>()

const emit = defineEmits<{
  startUpload: []
  clearAll: []
  retryFailed: []
}>()

const totalSize = computed(() =>
  props.files.reduce((sum, f) => sum + (f.size ?? 0), 0),
)
const successCount = computed(() => props.files.filter((f) => f.status === 'success').length)
const failedCount = computed(() => props.files.filter((f) => f.status === 'error').length)
const pendingCount = computed(() => props.files.filter((f) => f.status === 'queued').length)
</script>

<template>
  <div v-if="files.length" class="plex-upload-panel">
    <div class="plex-upload-panel__summary">
      <span>共 <strong>{{ files.length }}</strong> 个文件 · {{ formatFileSize(totalSize) }}</span>
      <span v-if="successCount">✓ {{ successCount }} 成功</span>
      <span v-if="failedCount" style="color:#f87171">✗ {{ failedCount }} 失败</span>
      <span v-if="pendingCount">⏳ {{ pendingCount }} 等待</span>
    </div>

    <div class="plex-upload-panel__actions">
      <button
        v-if="pendingCount > 0"
        type="button"
        class="plex-upload-panel__action-btn plex-upload-panel__action-btn--primary"
        :disabled="isUploading"
        @click="emit('startUpload')"
      >
        {{ isUploading ? '上传中…' : '开始上传' }}
      </button>

      <button
        v-if="failedCount > 0"
        type="button"
        class="plex-upload-panel__action-btn"
        @click="emit('retryFailed')"
      >
        重试失败
      </button>

      <button
        type="button"
        class="plex-upload-panel__action-btn"
        :disabled="isUploading"
        @click="emit('clearAll')"
      >
        清空列表
      </button>
    </div>
  </div>
</template>
