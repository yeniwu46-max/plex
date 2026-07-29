/** 登录页「记住我」账号历史（仅存用户名/邮箱，不存密码） */

const STORAGE_KEY = 'plex_login_account_history'
const REMEMBER_FLAG_KEY = 'plex_login_remember'
const MAX_ACCOUNTS = 8

export function loadRememberFlag(): boolean {
  try {
    return localStorage.getItem(REMEMBER_FLAG_KEY) === '1'
  } catch {
    return false
  }
}

export function saveRememberFlag(remember: boolean) {
  try {
    if (remember) localStorage.setItem(REMEMBER_FLAG_KEY, '1')
    else localStorage.removeItem(REMEMBER_FLAG_KEY)
  } catch {
    /* ignore quota / private mode */
  }
}

export function loadAccountHistory(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return []
    return parsed
      .filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
      .map((item) => item.trim())
      .slice(0, MAX_ACCOUNTS)
  } catch {
    return []
  }
}

export function rememberAccount(account: string) {
  const normalized = account.trim()
  if (!normalized) return
  const next = [normalized, ...loadAccountHistory().filter((item) => item.toLowerCase() !== normalized.toLowerCase())]
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next.slice(0, MAX_ACCOUNTS)))
  } catch {
    /* ignore */
  }
}

export function filterAccountSuggestions(query: string, history: string[] = loadAccountHistory()): string[] {
  const q = query.trim().toLowerCase()
  if (!q) return history.slice(0, MAX_ACCOUNTS)
  return history.filter((item) => item.toLowerCase().includes(q)).slice(0, MAX_ACCOUNTS)
}
