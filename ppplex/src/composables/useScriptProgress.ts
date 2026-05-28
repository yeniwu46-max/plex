const STORAGE_KEY = 'ppplex-script-checked'

export function useScriptProgress() {
  function load(): Record<string, boolean> {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      return raw ? (JSON.parse(raw) as Record<string, boolean>) : {}
    } catch {
      return {}
    }
  }

  function save(state: Record<string, boolean>) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  }

  function toggle(key: string): Record<string, boolean> {
    const next = { ...load(), [key]: !load()[key] }
    save(next)
    return next
  }

  function reset() {
    localStorage.removeItem(STORAGE_KEY)
  }

  return { load, toggle, reset }
}
