import { http, type ApiEnvelope } from './http'
import type { CurrentStudent } from './studentOverview'

export interface UpdateProfilePayload {
  real_name?: string
  bio?: string
  avatar_url?: string
  phone?: string
  gender?: string
}

export async function updateMyProfile(payload: UpdateProfilePayload) {
  const { data } = await http.patch<ApiEnvelope<Record<string, unknown>>>('/v1/users/me', payload)
  if (data.code !== 0) throw new Error(data.message || '保存失败')
  return data.data
}

export async function uploadMyAvatar(file: File) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await http.post<ApiEnvelope<{ avatar_url: string }>>('/v1/uploads/avatar', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  if (data.code !== 0) throw new Error(data.message || '头像上传失败')
  return data.data.avatar_url
}

export function resolveAvatarUrl(url: string | null | undefined, apiBase?: string) {
  if (!url) return ''
  if (url.startsWith('http') || url.startsWith('data:')) return url
  if (url.startsWith('/api/')) return url
  const base = apiBase ?? import.meta.env.VITE_API_BASE_URL ?? '/api'
  return `${base.replace(/\/$/, '')}${url.startsWith('/') ? url : `/${url}`}`
}

export type { CurrentStudent }
