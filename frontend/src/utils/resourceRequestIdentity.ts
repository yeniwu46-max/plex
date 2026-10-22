import { createRequestId, sha256Hex } from './browserCrypto'

// Retain only an opaque request ID across an ambiguous network failure/reload.
const memory = new Map<string, string>()
const unpersisted = new Set<string>()
export async function resourceRequestIdentity(owner: number, body: object) {
  const hash = await sha256Hex(JSON.stringify(body))
  const key = `plex_resource_request_v1:${owner}:${hash}`
  let id = memory.get(key)
  try {
    const stored = localStorage.getItem(key)
    // Another tab may have received success and removed the persistent ID.
    id = stored || (unpersisted.has(key) ? id : undefined)
  } catch { /* Memory still protects same-page retries. */ }
  if (!id) id = createRequestId()
  memory.set(key, id)
  try { localStorage.setItem(key, id); unpersisted.delete(key) } catch { unpersisted.add(key) }
  const requestId = id
  return { requestId, clear() {
    if (memory.get(key) === requestId) memory.delete(key)
    unpersisted.delete(key)
    try { if (localStorage.getItem(key) === requestId) localStorage.removeItem(key) } catch { /* No persistent state. */ }
  } }
}
