import Fuse from 'fuse.js'
import { resolveModuleCategory, type ModuleCategoryValue } from '../data/moduleCategories'
import type { PersonalizedResource } from '../api/personalizedResources'

export type ResourceDateFilter = 'all' | '7d' | '30d' | '90d'

export interface ResourceListFilterState {
  search: string
  date: ResourceDateFilter
  theme: 'all' | ModuleCategoryValue
}

export const RESOURCE_DATE_FILTER_OPTIONS: Array<{ label: string; value: ResourceDateFilter }> = [
  { label: '全部时间', value: 'all' },
  { label: '近 7 天', value: '7d' },
  { label: '近 30 天', value: '30d' },
  { label: '近 90 天', value: '90d' },
]

function resourceTimestamp(item: PersonalizedResource): number | null {
  const raw = item.created_at
  if (!raw) return null
  const ms = Date.parse(raw)
  return Number.isFinite(ms) ? ms : null
}

function matchesDateFilter(item: PersonalizedResource, date: ResourceDateFilter): boolean {
  if (date === 'all') return true
  const ts = resourceTimestamp(item)
  if (ts === null) return true
  const days = date === '7d' ? 7 : date === '30d' ? 30 : 90
  const cutoff = Date.now() - days * 24 * 60 * 60 * 1000
  return ts >= cutoff
}

function matchesThemeFilter(item: PersonalizedResource, theme: ResourceListFilterState['theme']): boolean {
  if (theme === 'all') return true
  return resolveModuleCategory(item.knowledge_key) === theme
}

export function filterPersonalizedResources(
  items: PersonalizedResource[],
  filters: ResourceListFilterState,
): PersonalizedResource[] {
  let result = items.filter(
    (item) => matchesDateFilter(item, filters.date) && matchesThemeFilter(item, filters.theme),
  )
  const query = filters.search.trim()
  if (!query) return result

  const fuse = new Fuse(result, {
    keys: [
      { name: 'title', weight: 0.55 },
      { name: 'knowledge_label', weight: 0.3 },
      { name: 'knowledge_key', weight: 0.15 },
    ],
    threshold: 0.42,
    ignoreLocation: true,
  })
  result = fuse.search(query).map((row) => row.item)
  return result
}
