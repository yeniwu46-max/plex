import { http, type ApiEnvelope } from './http'

export interface AdminRulesSettings {
  open_time: string
  daily_limit: string
  difficulty: number
  punish: string
}

export interface AdminToggleItem {
  key: string
  enabled: boolean
}

export interface AdminSettingsPayload {
  rules: AdminRulesSettings
  data_scope: string
  ai_strategies: AdminToggleItem[]
  notices: AdminToggleItem[]
  channels?: Record<string, boolean>
}

export interface AdminSettingsResult {
  class_id: number | null
  scope_class_id: number | null
  settings: AdminSettingsPayload
  updated_at: string | null
}

export async function fetchAdminSettings(classId?: number) {
  const { data } = await http.get<ApiEnvelope<AdminSettingsResult>>('/v1/admin/settings', {
    params: classId ? { class_id: classId } : undefined,
  })
  if (data.code !== 0) throw new Error(data.message || '加载配置失败')
  return data.data
}

export async function saveAdminSettings(settings: Partial<AdminSettingsPayload>, classId?: number) {
  const { data } = await http.put<ApiEnvelope<AdminSettingsResult>>('/v1/admin/settings', {
    class_id: classId,
    settings,
  })
  if (data.code !== 0) throw new Error(data.message || '保存配置失败')
  return data.data
}
