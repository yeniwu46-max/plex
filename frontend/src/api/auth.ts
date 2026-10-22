import { http, type ApiEnvelope } from './http'

export interface AuthCapabilities {
  registration_enabled: boolean
  password_reset_enabled: boolean
  support_email: string
  oauth_providers: ('google' | 'github')[]
}

export async function fetchAuthCapabilities() {
  const { data } = await http.get<ApiEnvelope<AuthCapabilities>>('/v1/auth/capabilities')
  if (data.code !== 0) throw new Error(data.message)
  return data.data
}

export async function requestPasswordReset(email: string) {
  const { data } = await http.post<ApiEnvelope>('/v1/auth/forgot-password', { email })
  if (data.code !== 0) throw new Error(data.message)
  return data.message
}

export async function resetPassword(token: string, password: string) {
  const { data } = await http.post<ApiEnvelope>('/v1/auth/reset-password', { token, password })
  if (data.code !== 0) throw new Error(data.message)
}
