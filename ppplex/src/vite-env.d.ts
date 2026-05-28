/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_A3_BASE: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module '@defense/manifest.json' {
  import type { DefenseManifest } from './types/defense'
  const manifest: DefenseManifest
  export default manifest
}
