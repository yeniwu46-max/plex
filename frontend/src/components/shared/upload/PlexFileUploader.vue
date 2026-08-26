<script setup lang="ts">
import { useMessage } from 'naive-ui'
import { computed } from 'vue'
import type { UploadFileEntry, UploadPresetConfig, UploadResponse, UploadRole, UploadScene } from '../../../types/upload'
import { usePlexUploader } from '../../../composables/usePlexUploader'
import { getSuccessMessage } from '../../../services/uploadService'
import PlexDropzone from './PlexDropzone.vue'
import PlexUploadList from './PlexUploadList.vue'
import PlexUploadPanel from './PlexUploadPanel.vue'

interface Props extends Partial<UploadPresetConfig> {
  role: UploadRole
  scene: UploadScene
  title?: string
  description?: string
  relatedId?: string
  maxFileSize?: number
  maxNumberOfFiles?: number
  accept?: string[]
  multiple?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  multiple: true,
  maxFileSize: 50 * 1024 * 1024,
  maxNumberOfFiles: 10,
})

const emit = defineEmits<{
  uploadSuccess: [file: UploadFileEntry, resp: UploadResponse]
  uploadError: [file: UploadFileEntry, err: Error]
  fileAdded: [file: UploadFileEntry]
  fileRemoved: [id: string]
  uploadProgress: [file: UploadFileEntry]
}>()

const message = useMessage()

const uploader = usePlexUploader({
  role: props.role,
  scene: props.scene,
  title: props.title ?? '',
  description: props.description ?? '',
  accept: props.accept ?? [],
  maxFileSize: props.maxFileSize,
  maxNumberOfFiles: props.maxNumberOfFiles,
  multiple: props.multiple,
  relatedId: props.relatedId,
  onSuccess(file, resp) {
    message.success(getSuccessMessage(props.scene, file.name))
    emit('uploadSuccess', file, resp)
  },
  onError(file, err) {
    message.error(`「${file.name}」上传失败：${err.message}`)
    emit('uploadError', file, err)
  },
  onProgress(file) {
    emit('uploadProgress', file)
  },
})

const { files, isUploading, uploadError, addFile, startUpload, cancelUpload, removeFile, retryUpload, clearFiles, fileIcon } = uploader

const dropText = computed(() => {
  const m: Record<UploadRole, string> = {
    student: '拖拽代码文件、学习报告或截图到这里',
    teacher: '拖拽课程资料、题库或作业附件到这里',
    admin: '拖拽知识库文档或系统配置文件到这里',
  }
  return m[props.role]
})

function onFilesSelected(selectedFiles: File[]) {
  for (const f of selectedFiles) {
    if (f.size === 0) {
      message.warning(`文件「${f.name}」为空，已跳过`)
      continue
    }
    addFile(f)
    emit('fileAdded', files.value.find((e) => e.name === f.name && e.status === 'queued')!)
  }
}

function onRemove(id: string) {
  removeFile(id)
  emit('fileRemoved', id)
  message.success('文件已删除')
}

function onCancel(id: string) {
  cancelUpload(id)
  message.info('已取消上传')
}

function onRetry(id: string) {
  retryUpload(id)
  message.info('正在重试…')
}

function onView(entry: UploadFileEntry) {
  if (entry.url) window.open(entry.url, '_blank')
}

function onRetryFailed() {
  files.value
    .filter((f) => f.status === 'error')
    .forEach((f) => {
      retryUpload(f.id)
    })
}

</script>

<template>
  <div class="plex-uploader">
    <div class="plex-uploader__header">
      <div>
        <h4 v-if="title" class="plex-uploader__title">{{ title }}</h4>
        <p v-if="description" class="plex-uploader__desc">{{ description }}</p>
      </div>
    </div>

    <plex-dropzone
      :accept="accept"
      :multiple="multiple"
      :disabled="isUploading"
      :drop-text="dropText"
      @files-selected="onFilesSelected"
    />

    <p v-if="uploadError" class="plex-upload-error">{{ uploadError }}</p>

    <plex-upload-list
      :files="files"
      :file-icon="fileIcon"
      @remove="onRemove"
      @cancel="onCancel"
      @retry="onRetry"
      @view="onView"
    />

    <plex-upload-panel
      :files="files"
      :is-uploading="isUploading"
      @start-upload="startUpload"
      @clear-all="clearFiles"
      @retry-failed="onRetryFailed"
    />

  </div>
</template>
