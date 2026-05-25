import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import axios, { type AxiosError } from 'axios'
import { http, storageKeys, type ApiEnvelope } from '../api/http'

export interface LoginPayload {
  id: number
  username: string
  email: string
  real_name: string
  role: string
  level?: number
  total_points?: number
  access_token: string
  refresh_token: string
  expiresIn?: number
}

const LS_USER = 'a3_user_profile'

function readProfile(): Omit<LoginPayload, 'access_token' | 'refresh_token' | 'expiresIn'> | null {
  try {
    const raw = localStorage.getItem(LS_USER)
    if (!raw) return null
    return JSON.parse(raw) as Omit<LoginPayload, 'access_token' | 'refresh_token' | 'expiresIn'>
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem(storageKeys.access))
  const refreshToken = ref<string | null>(localStorage.getItem(storageKeys.refresh))
  const profile = ref(readProfile())

  const isAuthenticated = computed(() => Boolean(accessToken.value))

  function persistSession(payload: LoginPayload) {
    const { access_token, refresh_token, expiresIn: _e, ...rest } = payload
    accessToken.value = access_token
    refreshToken.value = refresh_token
    profile.value = rest
    localStorage.setItem(storageKeys.access, access_token)
    localStorage.setItem(storageKeys.refresh, refresh_token)
    localStorage.setItem(LS_USER, JSON.stringify(rest))
  }

  function clearSession() {
    accessToken.value = null
    refreshToken.value = null
    profile.value = null
    localStorage.removeItem(storageKeys.access)
    localStorage.removeItem(storageKeys.refresh)
    localStorage.removeItem(LS_USER)
  }

  function syncProfile(nextProfile: Partial<Omit<LoginPayload, 'access_token' | 'refresh_token' | 'expiresIn'>>) {
    if (!profile.value) return
    profile.value = { ...profile.value, ...nextProfile }
    localStorage.setItem(LS_USER, JSON.stringify(profile.value))
  }

  async function login(username: string, password: string) {
    try {
      const { data } = await http.post<ApiEnvelope<LoginPayload>>('/v1/auth/login', { username, password })
      if (data.code !== 0) {
        throw new Error(data.message || '登录失败')
      }
      if (!data.data?.access_token) {
        throw new Error('响应缺少 access_token')
      }
      persistSession(data.data)
      return data.data
    } catch (e) {
      if (axios.isAxiosError(e)) {
        const ax = e as AxiosError<ApiEnvelope>
        const body = ax.response?.data
        if (body && typeof body.message === 'string') {
          throw new Error(body.message)
        }
        const status = ax.response?.status
        if (status === 502 || status === 503 || ax.code === 'ERR_NETWORK') {
          throw new Error(
            '无法连接后端 API（502）。请先在 backend 目录执行 python run.py，并确认 http://127.0.0.1:5000 可访问。',
          )
        }
      }
      throw e instanceof Error ? e : new Error('登录失败')
    }
  }

  async function logout() {
    try {
      await http.post('/v1/auth/logout')
    } catch {
      /* 无状态 JWT，忽略网络错误 */
    } finally {
      clearSession()
    }
  }

  /** 登录后进入学生端总览，再由总览承接探索舱、委托、档案与试炼入口。 */
  function homePathForRole(role?: string) {
    if (role === 'admin') return '/admin'
    if (role === 'teacher') return '/teacher'
    return '/student'
  }

  return {
    accessToken,
    refreshToken,
    profile,
    isAuthenticated,
    login,
    logout,
    clearSession,
    syncProfile,
    homePathForRole,
  }
})
