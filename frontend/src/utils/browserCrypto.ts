import { sha256 } from '@noble/hashes/sha2.js'

/** Request identities must also work on HTTP deployments, where Web Crypto is limited. */
export function createRequestId(): string {
  const crypto = globalThis.crypto
  if (typeof crypto?.randomUUID === 'function') return crypto.randomUUID()
  if (typeof crypto?.getRandomValues !== 'function') {
    throw new Error('当前浏览器无法生成请求标识，请使用较新版本的浏览器重试。')
  }
  // getRandomValues is available in insecure contexts; retain UUID v4 entropy.
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6]! & 0x0f) | 0x40
  bytes[8] = (bytes[8]! & 0x3f) | 0x80
  const hex = toHex(bytes)
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

function toHex(bytes: Uint8Array): string {
  return Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('')
}

/** Keep exactly the same SHA-256 storage keys on HTTP, HTTPS and localhost. */
export async function sha256Hex(value: string): Promise<string> {
  const bytes = new TextEncoder().encode(value)
  if (typeof globalThis.crypto?.subtle?.digest === 'function') {
    return toHex(new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256', bytes)))
  }
  return toHex(sha256(bytes))
}
