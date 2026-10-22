export function passwordValid(value: string) {
  return value.length >= 8 && value.length <= 128 && /[A-Za-z]/.test(value) && /\d/.test(value)
}

export function safeAuthRedirect(value: unknown, fallback: string) {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || /[\\\x00-\x20]/.test(value)) return fallback
  if (/^\/(login|register|reset-password|oauth)([/?#]|$)/.test(value)) return fallback
  return value
}
