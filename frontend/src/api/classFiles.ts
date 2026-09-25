import { formatHttpError, http, type ApiEnvelope } from './http'

export interface ClassSharedFile {
  id: string
  fileName: string
  fileType: string
  fileSize: number
  url: string
  scene: string
  owner_id: number
  owner_name?: string
  owner_username?: string | null
  owner_role?: string
  createdAt: string
  score?: number | null
  scored_at?: string | null
  scored_by?: number | null
}

export interface ClassFilesResult {
  items: ClassSharedFile[]
  class_id: number | null
}

export interface ClassFileScoreResult {
  filepath: string
  score: number | null
  scored_at?: string | null
  scored_by?: number | null
  comment?: string
}

export async function fetchClassFiles() {
  const { data } = await http.get<ApiEnvelope<ClassFilesResult>>('/v1/class-files')
  if (data.code !== 0) throw new Error(data.message || '班级文件加载失败')
  return data.data
}

export function filePathFromUrl(url: string) {
  const marker = '/uploads/files/'
  const idx = url.indexOf(marker)
  if (idx >= 0) return url.slice(idx + marker.length)
  return url.replace(/^\/?api\/v1\/uploads\/files\//, '').replace(/^\//, '')
}

export async function fetchClassFileScore(filepath: string) {
  try {
    const { data } = await http.get<ApiEnvelope<ClassFileScoreResult>>('/v1/class-files/score', {
      params: { filepath },
    })
    if (data.code !== 0) throw new Error(data.message || '评分加载失败')
    return data.data
  } catch (error) {
    throw new Error(formatHttpError(error, '评分加载失败'))
  }
}

export async function saveClassFileScore(filepath: string, score: number, comment = '') {
  try {
    const { data } = await http.put<ApiEnvelope<ClassFileScoreResult>>('/v1/class-files/score', {
      filepath,
      score,
      comment,
    })
    if (data.code !== 0) throw new Error(data.message || '评分保存失败')
    return data.data
  } catch (error) {
    throw new Error(formatHttpError(error, '评分保存失败'))
  }
}

export function resolveUploadFileUrl(url: string) {
  const trimmed = (url || '').trim()
  if (!trimmed) return trimmed
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) return trimmed
  if (trimmed.startsWith('/api/')) return trimmed
  const base = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '')
  if (trimmed.startsWith('/v1/')) return `${base}${trimmed}`
  return `${base}${trimmed.startsWith('/') ? trimmed : `/${trimmed}`}`
}

/** 将列表里的 file.url 转为 axios 相对 baseURL 的请求路径 */
export function uploadFileRequestPath(url: string) {
  const resolved = resolveUploadFileUrl(url)
  const apiBase = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '')
  if (resolved.startsWith('http://') || resolved.startsWith('https://')) {
    const baseOrigin = apiBase.startsWith('http') ? apiBase : undefined
    if (baseOrigin && resolved.startsWith(baseOrigin)) {
      return resolved.slice(baseOrigin.length) || '/'
    }
    try {
      const pathname = new URL(resolved).pathname
      if (pathname.startsWith('/api/')) return pathname.replace(/^\/api/, '') || '/'
      return pathname || '/'
    } catch {
      return resolved
    }
  }
  if (resolved.startsWith(apiBase)) {
    return resolved.slice(apiBase.length) || '/'
  }
  if (resolved.startsWith('/api/')) {
    return resolved.replace(/^\/api/, '') || '/'
  }
  return resolved.startsWith('/') ? resolved : `/${resolved}`
}

async function parseBlobErrorMessage(blob: Blob, fallback: string) {
  const sample = await blob.slice(0, 768).text()
  const trimmed = sample.trim()
  if (trimmed.startsWith('{')) {
    try {
      const payload = JSON.parse(trimmed) as { message?: string }
      if (payload.message) return payload.message
    } catch {
      /* ignore */
    }
  }
  return fallback
}

/** 带 JWT 拉取上传文件内容（window.open 无法携带 Authorization） */
export async function fetchUploadFileBlob(url: string) {
  const requestPath = uploadFileRequestPath(url)
  const { data } = await http.get<Blob>(requestPath, {
    responseType: 'blob',
    headers: { Accept: '*/*' },
  })
  if (!(data instanceof Blob) || data.size === 0) {
    throw new Error(await parseBlobErrorMessage(data, '文件内容为空或加载失败'))
  }
  return data
}

/** 校验 PDF 魔数并返回可用于 iframe/object 预览的 Blob */
export async function fetchUploadPdfBlob(url: string) {
  const blob = await fetchUploadFileBlob(url)
  const header = new Uint8Array(await blob.slice(0, 5).arrayBuffer())
  const signature = String.fromCharCode(...header)
  if (!signature.startsWith('%PDF')) {
    throw new Error(await parseBlobErrorMessage(blob, '不是有效的 PDF 文件，请下载后查看'))
  }
  if (blob.type === 'application/pdf') return blob
  return new Blob([await blob.arrayBuffer()], { type: 'application/pdf' })
}

export function isTextPreviewType(fileType: string, fileName: string) {
  const ext = (fileType || fileName.split('.').pop() || '').toLowerCase()
  return ['py', 'txt', 'md', 'json', 'csv', 'js', 'ts', 'html', 'css', 'xml', 'yml', 'yaml', 'sql'].includes(ext)
}

export function isPdfPreviewType(fileType: string, fileName: string) {
  const ext = (fileType || fileName.split('.').pop() || '').toLowerCase()
  return ext === 'pdf'
}

export function isImagePreviewType(fileType: string, fileName: string) {
  const ext = (fileType || fileName.split('.').pop() || '').toLowerCase()
  return ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg'].includes(ext)
}
