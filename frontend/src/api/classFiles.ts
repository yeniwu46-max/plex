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
  if (url.startsWith('http') || url.startsWith('/api/')) return url
  const base = import.meta.env.VITE_API_BASE_URL ?? '/api'
  return `${base.replace(/\/$/, '')}${url.startsWith('/') ? url : `/${url}`}`
}

/** 带 JWT 拉取上传文件内容（window.open 无法携带 Authorization） */
export async function fetchUploadFileBlob(url: string) {
  const resolved = resolveUploadFileUrl(url)
  const apiBase = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '')
  let requestPath = resolved
  if (resolved.startsWith(apiBase)) {
    requestPath = resolved.slice(apiBase.length) || '/'
  } else if (resolved.startsWith('/api/')) {
    requestPath = resolved.replace(/^\/api/, '')
  }
  const { data } = await http.get<Blob>(requestPath, { responseType: 'blob' })
  return data
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
