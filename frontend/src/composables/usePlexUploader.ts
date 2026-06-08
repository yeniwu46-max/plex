// @ts-nocheck — Uppy major version type mismatch; suppressed until Uppy is upgraded
import { onUnmounted, ref, shallowRef, watch } from 'vue'
import Uppy from '@uppy/core'
import XHRUpload from '@uppy/xhr-upload'
import type { UppyFile } from '@uppy/core'
import type {
  UploadFileEntry,
  UploadPresetConfig,
  UploadResponse,
  UploadRole,
  UploadScene,
  UploadStatus,
} from '../types/upload'

export interface UsePlexUploaderOptions extends UploadPresetConfig {
  role: UploadRole
  relatedId?: string
  onSuccess?: (file: UploadFileEntry, resp: UploadResponse) => void
  onError?: (file: UploadFileEntry, err: Error) => void
  onProgress?: (file: UploadFileEntry) => void
}

function getAccessToken(): string {
  return localStorage.getItem('a3_access_token') ?? ''
}

function fileIcon(type: string): string {
  if (type.startsWith('image/')) return '🖼️'
  if (type === 'application/pdf') return '📄'
  if (type.includes('zip') || type.includes('compressed')) return '🗜️'
  if (type.includes('json') || type.includes('yaml') || type.includes('csv')) return '📊'
  return '📁'
}

export function usePlexUploader(options: UsePlexUploaderOptions) {
  const files = ref<UploadFileEntry[]>([])
  const isUploading = ref(false)
  const uploadStatus = ref<UploadStatus>('idle')
  const uploadError = ref<string | null>(null)

  const uppyRef = shallowRef<Uppy | null>(null)

  function destroyUploader() {
    uppyRef.value?.cancelAll()
    uppyRef.value?.close()
    uppyRef.value = null
  }

  function createUploader(): Uppy {
    destroyUploader()

    const endpointUrl = (import.meta.env.VITE_API_BASE_URL ?? '/api') + '/v1/upload'

    const uppy = new Uppy({
      autoProceed: false,
      restrictions: {
        maxFileSize: options.maxFileSize,
        maxNumberOfFiles: options.maxNumberOfFiles,
        allowedFileTypes: options.accept,
      },
    }).use(XHRUpload, {
      endpoint: endpointUrl,
      method: 'POST',
      fieldName: 'file',
      allowedMetaFields: ['role', 'scene', 'relatedId'],
      headers: () => ({
        Authorization: `Bearer ${getAccessToken()}`,
      }),
      timeout: 120000,
    })

    uppy.on('file-added', (f: UppyFile) => {
      const duplicate = files.value.some(
        (e) => e.name === f.name && e.status !== 'cancelled' && e.status !== 'error',
      )
      if (duplicate) {
        uploadError.value = `文件 "${f.name}" 已在列表中，请勿重复添加`
        uppy.removeFile(f.id)
        return
      }

      const entry: UploadFileEntry = {
        id: f.id,
        name: f.name ?? 'unknown',
        type: f.type ?? '',
        size: f.size ?? 0,
        status: 'queued',
        progress: 0,
        isDuplicate: false,
      }
      files.value = [...files.value, entry]

      uppy.setFileMeta(f.id, {
        role: options.role,
        scene: options.scene,
        relatedId: options.relatedId ?? '',
      })
    })

    uppy.on('upload-progress', (f: UppyFile, progress: { bytesUploaded: number; bytesTotal: number }) => {
      const pct = progress.bytesTotal > 0 ? Math.round((progress.bytesUploaded / progress.bytesTotal) * 100) : 0
      files.value = files.value.map((e) =>
        e.id === f.id ? { ...e, status: 'uploading', progress: pct } : e,
      )
      const entry = files.value.find((e) => e.id === f.id)
      if (entry) options.onProgress?.(entry)
    })

    uppy.on('upload-success', (f: UppyFile | undefined, resp: { body: unknown }) => {
      if (!f) return
      const body = resp.body as { code?: number; data?: UploadResponse; message?: string }
      const uploadResp: UploadResponse | undefined =
        body?.code === 0 && body.data ? body.data : undefined

      files.value = files.value.map((e) =>
        e.id === f.id
          ? {
              ...e,
              status: uploadResp ? 'success' : 'error',
              progress: uploadResp ? 100 : e.progress,
              url: uploadResp?.url,
              uploadResponse: uploadResp,
              error: uploadResp ? undefined : body?.message || '服务器未返回有效上传结果',
            }
          : e,
      )
      const entry = files.value.find((e) => e.id === f.id)!
      if (uploadResp) {
        options.onSuccess?.(entry, uploadResp)
      } else {
        options.onError?.(entry, new Error(entry.error || '上传失败'))
        uploadError.value = entry.error || '上传失败'
      }
    })

    uppy.on('upload-error', (f: UppyFile | undefined, err: Error) => {
      if (!f) return
      files.value = files.value.map((e) =>
        e.id === f.id ? { ...e, status: 'error', error: err.message } : e,
      )
      const entry = files.value.find((e) => e.id === f.id)!
      uploadError.value = err.message
      options.onError?.(entry, err)
    })

    uppy.on('upload', () => {
      isUploading.value = true
      uploadStatus.value = 'uploading'
      uploadError.value = null
    })

    uppy.on('complete', (result) => {
      isUploading.value = false
      if (result.failed.length > 0 && result.successful.length === 0) {
        uploadStatus.value = 'error'
        uploadError.value = `${result.failed.length} 个文件上传失败`
      } else if (result.failed.length > 0) {
        uploadStatus.value = 'error'
        uploadError.value = `${result.failed.length} 个文件失败，${result.successful.length} 个成功`
      } else {
        uploadStatus.value = 'success'
      }
    })

    uppyRef.value = uppy
    return uppy
  }

  function ensureUploader() {
    if (!uppyRef.value) createUploader()
    return uppyRef.value!
  }

  function addFile(file: File) {
    if (file.size === 0) {
      uploadError.value = `文件 "${file.name}" 为空，已忽略`
      return
    }
    try {
      ensureUploader().addFile({ name: file.name, type: file.type, data: file })
    } catch (e: unknown) {
      uploadError.value = e instanceof Error ? e.message : '文件添加失败'
    }
  }

  async function startUpload() {
    const pending = files.value.filter((f) => f.status === 'queued')
    if (pending.length === 0) return
    uploadError.value = null
    ensureUploader()
    await uppyRef.value!.upload()
  }

  function cancelUpload(fileId: string) {
    uppyRef.value?.removeFile(fileId)
    files.value = files.value.map((f) => (f.id === fileId ? { ...f, status: 'cancelled' } : f))
  }

  function removeFile(fileId: string) {
    try {
      uppyRef.value?.removeFile(fileId)
    } catch {
      // file may already be removed after upload
    }
    files.value = files.value.filter((f) => f.id !== fileId)
  }

  function retryUpload(fileId: string) {
    if (!uppyRef.value) return
    files.value = files.value.map((f) =>
      f.id === fileId ? { ...f, status: 'queued', progress: 0, error: undefined } : f,
    )
    void uppyRef.value.retryUpload(fileId)
  }

  function clearFiles() {
    uppyRef.value?.cancelAll()
    files.value = []
    uploadStatus.value = 'idle'
    uploadError.value = null
    isUploading.value = false
  }

  watch(
    () => [options.role, options.scene, options.relatedId, options.maxFileSize, options.accept?.join(',')],
    () => {
      if (uppyRef.value && !isUploading.value) {
        createUploader()
      }
    },
  )

  onUnmounted(() => {
    destroyUploader()
  })

  return {
    files,
    isUploading,
    uploadStatus,
    uploadError,
    addFile,
    startUpload,
    cancelUpload,
    removeFile,
    retryUpload,
    clearFiles,
    fileIcon,
  }
}
