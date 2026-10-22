import { createRequestId, sha256Hex } from './browserCrypto'

// Persist opaque IDs only; questions, histories and answers stay out of browser storage.
const memory = new Map<string, string>()
const volatile = new Set<string>()
function read(key: string) {
  try { return localStorage.getItem(key) || (volatile.has(key) ? memory.get(key) : undefined) }
  catch { return memory.get(key) }
}
function write(key: string, value: string) {
  memory.set(key, value)
  try { localStorage.setItem(key, value); volatile.delete(key) } catch { volatile.add(key) }
}
function canonical(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonical)
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value)
    .filter(([, v]) => v !== undefined).sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => [k, canonical(v)]))
  return value
}
const latestKey = (owner: number) => `plex_rag_latest_v1:${owner}`
export function latestRagRequest(owner: number) { return read(latestKey(owner)) || null }
export async function ragRequestIdentity(owner: number, body: object, explicit?: string) {
  const hash = await sha256Hex(JSON.stringify(canonical(body)))
  const key = `plex_rag_request_v1:${owner}:${hash}`
  const requestId = explicit || read(key) || createRequestId()
  if (!explicit) write(key, requestId)
  write(latestKey(owner), requestId)
  return { requestId, clear() {
    if (explicit) return
    if (read(key) !== requestId) return
    memory.delete(key); volatile.delete(key)
    try { localStorage.removeItem(key) } catch { /* In-memory state was removed. */ }
  } }
}
