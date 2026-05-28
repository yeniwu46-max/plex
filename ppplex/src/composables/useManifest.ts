import manifest from '@defense/manifest.json'
import type { DefenseManifest, FeatureSection } from '../types/defense'

const data = manifest as DefenseManifest

export function useManifest() {
  const a3Base =
    import.meta.env.VITE_A3_BASE?.replace(/\/$/, '') || data.meta.a3BaseUrl.replace(/\/$/, '')

  function sectionById(id: string): FeatureSection | undefined {
    return data.sections.find((s) => s.id === id)
  }

  function demoHref(path?: string | null): string | null {
    if (!path) return null
    return `${a3Base}${path.startsWith('/') ? path : `/${path}`}`
  }

  function assetUrl(file: string): string {
    return `/assets/${encodeURIComponent(file)}`
  }

  return { manifest: data, a3Base, sectionById, demoHref, assetUrl }
}
