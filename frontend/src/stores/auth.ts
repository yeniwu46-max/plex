import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import axios, { type AxiosError } from 'axios'
import { http, storageKeys, type ApiEnvelope } from '../api/http'
import type { Appearance, ArrivalSummary } from '../api/onboarding'

export interface LoginPayload {
  id: number
  username: string
  email: string
  real_name: string
  role: string
  level?: number
  total_points?: number
  bio?: string | null
  avatar_url?: string | null
  access_token: string
  refresh_token: string
  expiresIn?: number
  onboarding?: ArrivalSummary
  preferences?: Appearance | null
}

export interface RegisterPayload {
  username: string
  email: string
  password: string
  real_name: string
  role?: string
}

function readProfile(): Omit<LoginPayload, 'access_token' | 'refresh_token' | 'expiresIn'> | null {
  try {
    const raw = localStorage.getItem(storageKeys.profile)
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
  const accountReady = ref(false)
  let loadingAccount: Promise<void> | null = null
  let loadingToken: string | null = null
  function syncStoredSession() {
    const previousRefresh = refreshToken.value
    accessToken.value = localStorage.getItem(storageKeys.access)
    refreshToken.value = localStorage.getItem(storageKeys.refresh)
    profile.value = readProfile()
    if (previousRefresh !== refreshToken.value) accountReady.value = false
  }
  window.addEventListener('plex-session-changed', syncStoredSession)
  window.addEventListener('storage', syncStoredSession)

  const isAuthenticated = computed(() => Boolean(accessToken.value))

  function persistSession(payload: LoginPayload) {
    const { access_token, refresh_token, expiresIn: _e, ...rest } = payload
    accessToken.value = access_token
    refreshToken.value = refresh_token
    profile.value = rest
    accountReady.value = Boolean(payload.onboarding)
    localStorage.setItem(storageKeys.access, access_token)
    localStorage.setItem(storageKeys.refresh, refresh_token)
    localStorage.setItem(storageKeys.profile, JSON.stringify(rest))
  }

  function clearSession() {
    accountReady.value = false
    accessToken.value = null
    refreshToken.value = null
    profile.value = null
    localStorage.removeItem(storageKeys.access)
    localStorage.removeItem(storageKeys.refresh)
    localStorage.removeItem(storageKeys.profile)
  }

  async function ensureAccount() {
    if (accountReady.value) return
    const owner = refreshToken.value
    if (!loadingAccount || loadingToken !== owner) {
      loadingToken = owner
      const pending = http.get<ApiEnvelope<Omit<LoginPayload, 'access_token' | 'refresh_token'>>>('/v1/users/me')
        .then(({ data }) => {
          if (owner !== refreshToken.value) throw new Error('登录状态已变化，请重试')
          if (data.code !== 0 || !data.data?.onboarding) throw new Error('账号信息加载失败，请重试')
          syncProfile(data.data)
          accountReady.value = true
        }).finally(() => { if (loadingAccount === pending) loadingAccount = null })
      loadingAccount = pending
    }
    await loadingAccount
  }

  function syncProfile(nextProfile: Partial<Omit<LoginPayload, 'access_token' | 'refresh_token' | 'expiresIn'>>) {
    if (!profile.value) return
    profile.value = { ...profile.value, ...nextProfile }
    localStorage.setItem(storageKeys.profile, JSON.stringify(profile.value))
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
            '暂时无法连接服务，请稍后重试。',
          )
        }
      }
      throw e instanceof Error ? e : new Error('登录失败')
    }
  }

  async function register(payload: RegisterPayload) {
    try {
      const { data } = await http.post<ApiEnvelope<LoginPayload>>('/v1/auth/register', payload)
      if (data.code !== 0) {
        throw new Error(data.message || '注册失败')
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
      }
      throw e instanceof Error ? e : new Error('注册失败')
    }
  }

  function acceptSession(payload: LoginPayload) {
    if (!payload.access_token || !payload.refresh_token) {
      throw new Error('第三方登录回调缺少登录凭证')
    }
    persistSession(payload)
    return payload
  }

  async function logout() {
    try {
      await http.post('/v1/auth/logout', { refresh_token: refreshToken.value })
    } catch {
      /* 离线时仍清理本机状态；服务端撤销需网络请求成功。 */
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
    accountReady,
    ensureAccount,
    login,
    register,
    acceptSession,
    logout,
    clearSession,
    syncProfile,
    homePathForRole,
  }
})
