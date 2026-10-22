import axios, { AxiosHeaders, isAxiosError, type AxiosError, type InternalAxiosRequestConfig } from 'axios'

const LS_ACCESS = 'a3_access_token'
const LS_REFRESH = 'a3_refresh_token'
const LS_USER = 'a3_user_profile'

export const storageKeys = { access: LS_ACCESS, refresh: LS_REFRESH, profile: LS_USER }

export interface ApiEnvelope<T = unknown> {
  code: number
  message: string
  data: T
}

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' },
})

let refreshInFlight: Promise<string> | null = null
let refreshOwner: string | null = null

function refreshAccess(refresh: string) {
  if (!refreshInFlight || refreshOwner !== refresh) {
    refreshOwner = refresh
    const pending = axios.post<ApiEnvelope<{ access_token: string }>>(
      `${import.meta.env.VITE_API_BASE_URL ?? '/api'}/v1/auth/refresh`, {},
      { headers: { Authorization: `Bearer ${refresh}` }, timeout: 20000 },
    ).then(({ data }) => {
      if (data.code !== 0 || !data.data?.access_token || localStorage.getItem(LS_REFRESH) !== refresh) throw new Error('登录状态已变化')
      localStorage.setItem(LS_ACCESS, data.data.access_token)
      window.dispatchEvent(new Event('plex-session-changed'))
      return data.data.access_token
    }).finally(() => {
      if (refreshInFlight === pending) {
        refreshInFlight = null
        refreshOwner = null
      }
    })
    refreshInFlight = pending
  }
  return refreshInFlight
}

http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem(LS_ACCESS)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']
  }
  return config
})

http.interceptors.response.use(
  (res) => res,
  async (err: AxiosError<ApiEnvelope>) => {
    const original = err.config
    const status = err.response?.status
    if (status === 401 && original && !(original as { _retry?: boolean })._retry) {
      const url = original.url ?? ''
      if (/\/auth\/(login|register|refresh|forgot-password|reset-password)(\?|$)/.test(url)) {
        return Promise.reject(err)
      }
      const refresh = localStorage.getItem(LS_REFRESH)
      if (refresh) {
        ;(original as { _retry?: boolean })._retry = true
        try {
          const access = await refreshAccess(refresh)
          if (access) {
            if (!original.headers) {
              original.headers = new AxiosHeaders()
            }
            original.headers.set('Authorization', `Bearer ${access}`)
            return http(original)
          }
        } catch (refreshError) {
          // A timeout or server outage does not invalidate the saved session.
          if (!isAxiosError(refreshError) || ![401, 403].includes(refreshError.response?.status ?? 0)) {
            return Promise.reject(refreshError)
          }
        }
      }
      if (localStorage.getItem(LS_REFRESH) !== refresh) return Promise.reject(err)
      localStorage.removeItem(LS_ACCESS)
      localStorage.removeItem(LS_REFRESH)
      localStorage.removeItem(LS_USER)
      window.dispatchEvent(new Event('plex-session-changed'))
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        window.location.assign(`/login?redirect=${encodeURIComponent(window.location.pathname + window.location.search + window.location.hash)}`)
      }
    }
    return Promise.reject(err)
  },
)

export function formatHttpError(error: unknown, fallback = '请求失败'): string {
  if (isAxiosError<ApiEnvelope>(error)) {
    const apiMessage = error.response?.data?.message
    if (apiMessage) return apiMessage
    const status = error.response?.status
    if (status === 404) {
      // 业务 404（如班级不存在）优先展示后端 message；真正缺路由时才提示重启
      return apiMessage || '服务接口未找到，请确认班级选择或重启后端后再试'
    }
    if (status === 401 || status === 403) {
      return apiMessage || '鉴权失败，请重新登录后再试'
    }
    if (status === 502 || status === 503) {
      return '后端服务未启动或暂时不可用'
    }
    if (error.code === 'ECONNABORTED' || /timeout/i.test(error.message || '')) {
      return '请求超时，请稍后重试（星火分析较慢时可稍等）'
    }
    if (error.message && !/^Request failed with status code/i.test(error.message)) {
      return error.message
    }
    if (status) return `请求失败（HTTP ${status}）`
    if (error.message) return error.message
  }
  if (error instanceof Error) return error.message
  return fallback
}
