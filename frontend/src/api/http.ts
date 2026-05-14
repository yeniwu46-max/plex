import axios, { AxiosHeaders, type AxiosError, type InternalAxiosRequestConfig } from 'axios'

const LS_ACCESS = 'a3_access_token'
const LS_REFRESH = 'a3_refresh_token'

export const storageKeys = { access: LS_ACCESS, refresh: LS_REFRESH }

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
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        window.location.assign('/login')
      }
    }
    return Promise.reject(err)
  },
)
