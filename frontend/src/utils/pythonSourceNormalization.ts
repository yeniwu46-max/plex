const FULLWIDTH_PYTHON_SYMBOLS: Readonly<Record<string, string>> = {
  '　': ' ',
  '（': '(',
  '）': ')',
  '［': '[',
  '］': ']',
  '｛': '{',
  '｝': '}',
  '，': ',',
  '：': ':',
  '；': ';',
  '＝': '=',
  '＋': '+',
  '－': '-',
  '＊': '*',
  '／': '/',
  '％': '%',
  '＜': '<',
  '＞': '>',
  '！': '!',
  '＂': '"',
  '＇': "'",
}

export interface PythonSourceNormalizationResult {
  code: string
  replacements: number
}

/**
 * Convert IME-produced full-width Python syntax without changing punctuation
 * inside strings or comments. Full-width quote characters are treated as
 * delimiters so `print（＂hello＂）` can be repaired as a whole.
 */
export function normalizePythonSource(source: string): PythonSourceNormalizationResult {
  let result = ''
  let replacements = 0
  let quote: "'" | '"' | null = null
  let tripleQuoted = false
  let escaped = false
  let inComment = false

  const normalizedAt = (index: number) => FULLWIDTH_PYTHON_SYMBOLS[source[index] ?? ''] ?? source[index] ?? ''

  for (let index = 0; index < source.length; index += 1) {
    const char = source[index]
    const normalized = FULLWIDTH_PYTHON_SYMBOLS[char] ?? char

    if (inComment) {
      result += char
      if (char === '\n') inComment = false
      continue
    }

    if (quote) {
      if (tripleQuoted) {
        if (
          normalized === quote
          && normalizedAt(index + 1) === quote
          && normalizedAt(index + 2) === quote
        ) {
          for (let offset = 0; offset < 3; offset += 1) {
            if (source[index + offset] !== quote) replacements += 1
          }
          result += quote.repeat(3)
          index += 2
          quote = null
          tripleQuoted = false
        } else {
          result += char
        }
        continue
      }

      if (escaped) {
        result += char
        escaped = false
      } else if (char === '\\') {
        result += char
        escaped = true
      } else if (normalized === quote) {
        if (char !== normalized) replacements += 1
        result += quote
        quote = null
      } else {
        result += char
      }
      continue
    }

    if (char === '#') {
      inComment = true
      result += char
      continue
    }

    if (normalized === "'" || normalized === '"') {
      quote = normalized
      tripleQuoted = normalizedAt(index + 1) === quote && normalizedAt(index + 2) === quote
      const count = tripleQuoted ? 3 : 1
      for (let offset = 0; offset < count; offset += 1) {
        if (source[index + offset] !== quote) replacements += 1
      }
      result += quote.repeat(count)
      index += count - 1
      continue
    }

    if (char !== normalized) replacements += 1
    result += normalized
  }

  return { code: result, replacements }
}

/** Remove Pyodide/subprocess internals and keep the actionable Python frame. */
export function concisePythonError(error: string | null | undefined): string | undefined {
  const text = String(error ?? '').replace(/\r\n/g, '\n').trim()
  if (!text) return undefined
  const lines = text.split('\n')
  let start = -1
  for (let index = 0; index < lines.length; index += 1) {
    if (/^\s*File .+, line \d+/.test(lines[index])) start = index
  }
  return (start >= 0 ? lines.slice(start) : lines.slice(-4)).join('\n').slice(0, 1200)
}
