import fs from 'node:fs'
import path from 'node:path'
import zlib from 'node:zlib'

const root = process.cwd()
const dist = path.join(root, 'dist')
const manifestPath = path.join(dist, '.vite', 'manifest.json')
const reportPath = path.join(root, 'reports', 'bundle-budget.json')

const budgets = {
  initialGzipBytes: 150 * 1024,
  largestLazyGzipBytes: 450 * 1024,
}

if (!fs.existsSync(manifestPath)) {
  console.error(`Bundle manifest not found: ${manifestPath}`)
  process.exit(1)
}

const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'))
const entries = Object.entries(manifest)
const entry = entries.find(([, item]) => item.isEntry)

if (!entry) {
  console.error('No application entry was found in the Vite manifest.')
  process.exit(1)
}

function gzipBytes(file) {
  return zlib.gzipSync(fs.readFileSync(path.join(dist, file))).length
}

const initialKeys = new Set()
function visitInitial(key) {
  if (initialKeys.has(key) || !manifest[key]) return
  initialKeys.add(key)
  for (const dependency of manifest[key].imports ?? []) {
    visitInitial(dependency)
  }
}
visitInitial(entry[0])

const initialAssets = [...initialKeys].map((key) => ({
  key,
  file: manifest[key].file,
  gzip_bytes: gzipBytes(manifest[key].file),
}))
const initialGzipBytes = initialAssets.reduce(
  (total, asset) => total + asset.gzip_bytes,
  0,
)

const lazyAssets = entries
  .filter(([key, item]) => !initialKeys.has(key) && item.file?.endsWith('.js'))
  .map(([key, item]) => ({
    key,
    file: item.file,
    gzip_bytes: gzipBytes(item.file),
    dynamic_entry: item.isDynamicEntry === true,
  }))
  .sort((left, right) => right.gzip_bytes - left.gzip_bytes)

const largestLazy = lazyAssets[0] ?? null
const checks = {
  initial_gzip: {
    actual_bytes: initialGzipBytes,
    budget_bytes: budgets.initialGzipBytes,
    passed: initialGzipBytes <= budgets.initialGzipBytes,
  },
  largest_lazy_gzip: {
    actual_bytes: largestLazy?.gzip_bytes ?? 0,
    budget_bytes: budgets.largestLazyGzipBytes,
    passed: (largestLazy?.gzip_bytes ?? 0) <= budgets.largestLazyGzipBytes,
    file: largestLazy?.file ?? null,
  },
}

const report = {
  passed: Object.values(checks).every((check) => check.passed),
  checks,
  initial_assets: initialAssets,
  largest_lazy_assets: lazyAssets.slice(0, 10),
}

fs.mkdirSync(path.dirname(reportPath), { recursive: true })
fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8')
console.log(JSON.stringify(report, null, 2))
process.exit(report.passed ? 0 : 1)
