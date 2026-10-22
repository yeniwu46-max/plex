import { readFileSync } from 'node:fs'
import { webcrypto } from 'node:crypto'
import vm from 'node:vm'
import ts from 'typescript'
import { sha256 } from '@noble/hashes/sha2.js'

// Match a real HTTP origin: crypto exists, but subtle and randomUUID do not.
export const httpCrypto = { getRandomValues: webcrypto.getRandomValues.bind(webcrypto) }
export function loadBrowserCrypto(crypto = httpCrypto) {
  const source = readFileSync(new URL('../../src/utils/browserCrypto.ts', import.meta.url), 'utf8')
  const code = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
  }).outputText
  const exports = {}
  vm.runInNewContext(code, {
    exports, crypto, TextEncoder, Uint8Array,
    require(name) {
      if (name === '@noble/hashes/sha2.js') return { sha256 }
      throw new Error(`Unexpected dependency ${name}`)
    },
  })
  return exports
}
