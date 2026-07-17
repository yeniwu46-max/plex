import { http, type ApiEnvelope } from './http'

export interface ClassSharedFile {
  id: string
  fileName: string
  fileType: string
  fileSize: number
  url: string
  scene: string
  owner_id: number
  owner_name?: string
  owner_role?: string
  createdAt: string
}

export interface ClassFilesResult {
  items: ClassSharedFile[]
  class_id: number | null
}

export async function fetchClassFiles() {
  const { data } = await http.get<ApiEnvelope<ClassFilesResult>>('/v1/class-files')
  if (data.code !== 0) throw new Error(data.message || '班级文件加载失败')
  return data.data
}

export function resolveUploadFileUrl(url: string) {
  if (url.startsWith('http') || url.startsWith('/api/')) return url
  const base = import.meta.env.VITE_API_BASE_URL ?? '/api'
  return `${base.replace(/\/$/, '')}${url.startsWith('/') ? url : `/${url}`}`
}
