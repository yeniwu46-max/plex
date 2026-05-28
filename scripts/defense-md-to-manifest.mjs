#!/usr/bin/env node
/**
 * 可选：从答辩 MD 校验 manifest 是否齐全。
 * 主数据源为 docs/defense/manifest.json；MD 为人类可读长文。
 *
 * 用法: node scripts/defense-md-to-manifest.mjs
 */
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const manifestPath = join(root, 'docs/defense/manifest.json')
const mdPath = join(root, 'docs/defense/A3-PLEX-答辩项目说明.md')

const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'))
const md = readFileSync(mdPath, 'utf8')

const sectionIds = manifest.sections.map((s) => s.id)
const pageSectionIds = manifest.pages.flatMap((p) => p.sections)
const missing = pageSectionIds.filter((id) => !sectionIds.includes(id))

if (missing.length) {
  console.error('manifest 引用了不存在的 section:', missing.join(', '))
  process.exit(1)
}

if (!md.includes('A3') || !md.includes('PLEX')) {
  console.error('答辩 MD 缺少关键术语')
  process.exit(1)
}

console.log(`OK: ${sectionIds.length} sections, ${manifest.screenshots.length} screenshots`)
console.log(`MD length: ${md.length} chars`)
