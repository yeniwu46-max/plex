<script setup lang="ts">
import type { UploadFileEntry } from '../../../types/upload'
import { formatFileSize } from '../../../config/upload/uploadPresets'
import PlexUploadProgress from './PlexUploadProgress.vue'

defineProps<{
  files: UploadFileEntry[]
  fileIcon: (type: string) => string
}>()

const emit = defineEmits<{
  remove: [id: string]
  cancel: [id: string]
  retry: [id: string]
  view: [entry: UploadFileEntry]
}>()

const STATUS_LABELS: Record<string, string> = {
  idle: '等待',
  queued: '待上传',
  uploading: '上传中',
  success: '成功',
  error: '失败',
  cancelled: '已取消',
}
</script>

<template>
  <ul v-if="files.length" class="plex-upload-list" role="list">
    <li v-for="file in files" :key="file.id" class="plex-upload-list__item">
      <span class="plex-upload-list__icon" aria-hidden="true">{{ fileIcon(file.type) }}</span>

      <div class="plex-upload-list__info">
        <p class="plex-upload-list__name" :title="file.name">{{ file.name }}</p>
        <p class="plex-upload-list__meta">
          {{ formatFileSize(file.size) }}
          <template v-if="file.error"> · <span style="color:#f87171">{{ file.error }}</span></template>
          <template v-if="file.isDuplicate"> · <span style="color:#f59e0b">同名文件</span></template>
        </p>
        <plex-upload-progress
          v-if="file.status === 'uploading'"
          :progress="file.progress"
          :status="file.status"
        />
      </div>

      <span
        class="plex-upload-list__status"
        :class="`plex-upload-list__status--${file.status}`"
      >
        {{ STATUS_LABELS[file.status] ?? file.status }}
      </span>

      <div class="plex-upload-list__actions">
        <template v-if="file.status === 'uploading'">
          <button type="button" class="plex-upload-list__action-btn" @click="emit('cancel', file.id)">取消</button>
        </template>
        <template v-else-if="file.status === 'error'">
          <button type="button" class="plex-upload-list__action-btn" @click="emit('retry', file.id)">重试</button>
          <button type="button" class="plex-upload-list__action-btn plex-upload-list__action-btn--danger" @click="emit('remove', file.id)">删除</button>
        </template>
        <template v-else-if="file.status === 'success'">
          <button v-if="file.url" type="button" class="plex-upload-list__action-btn" @click="emit('view', file)">查看</button>
          <button type="button" class="plex-upload-list__action-btn plex-upload-list__action-btn--danger" @click="emit('remove', file.id)">删除</button>
        </template>
        <template v-else>
          <button type="button" class="plex-upload-list__action-btn plex-upload-list__action-btn--danger" @click="emit('remove', file.id)">删除</button>
        </template>
      </div>
    </li>
  </ul>
</template>
