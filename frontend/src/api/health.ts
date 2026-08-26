import { http, type ApiEnvelope } from './http'

export interface AiHealth {
  deepseek?: {
    configured: boolean
    backend?: string
    model?: string | null
    status?: 'available' | 'unavailable'
  }
  spark: {
    configured: boolean
    status: 'available' | 'unavailable'
    request_id?: string | null
    latency_ms?: number | null
    model?: string | null
    error_code?: string | null
  }
  xfyun_agent?: {
    configured: boolean
    status?: 'available' | 'unavailable'
    error_code?: string | null
  }
  fallback: { backend: 'local_rules'; available: boolean }
  effective_backend: 'deepseek' | 'llm' | 'iflytek_spark' | 'xfyun_agent' | 'local_rules'
}

export async function fetchAiHealth() {
  const { data } = await http.get<ApiEnvelope<AiHealth>>('/v1/system/ai-health')
  if (data.code !== 0) throw new Error(data.message || 'AI 服务状态加载失败')
  return data.data
}
