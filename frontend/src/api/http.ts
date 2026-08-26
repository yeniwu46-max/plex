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
      if (url.includes('/auth/refresh')) {
        return Promise.reject(err)
      }
      const refresh = localStorage.getItem(LS_REFRESH)
      if (refresh) {
        ;(original as { _retry?: boolean })._retry = true
        try {
          const { data } = await axios.post<ApiEnvelope<{ access_token: string; expiresIn: number }>>(
            `${import.meta.env.VITE_API_BASE_URL ?? '/api'}/v1/auth/refresh`,
            {},
            { headers: { Authorization: `Bearer ${refresh}` } },
          )
          if (data.code === 0 && data.data?.access_token) {
            localStorage.setItem(LS_ACCESS, data.data.access_token)
            if (!original.headers) {
              original.headers = new AxiosHeaders()
            }
            original.headers.set('Authorization', `Bearer ${data.data.access_token}`)
            return http(original)
          }
        } catch {
          /* fall through */
        }
      }
      localStorage.removeItem(LS_ACCESS)
      localStorage.removeItem(LS_REFRESH)
      localStorage.removeItem(LS_USER)
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        window.location.assign('/login')
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
