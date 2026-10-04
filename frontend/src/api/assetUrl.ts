/** 将后端返回的资源路径转换为当前部署环境可访问的 URL。 */
export function resolveApiAssetUrl(url: string, apiBase = import.meta.env.VITE_API_BASE_URL ?? '/api') {
  const value = url.trim()
  if (!value || /^(https?:|data:|blob:)/i.test(value)) return value

  const base = apiBase.replace(/\/$/, '')
  if (value.startsWith('/api/')) {
    return base.startsWith('http') ? `${new URL(base).origin}${value}` : value
  }
  return `${base}${value.startsWith('/') ? value : `/${value}`}`
}
