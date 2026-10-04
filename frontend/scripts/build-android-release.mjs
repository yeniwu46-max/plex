import { existsSync, createReadStream } from 'node:fs'
import { resolve } from 'node:path'
import { createHash } from 'node:crypto'
import { spawnSync } from 'node:child_process'

const root = resolve(import.meta.dirname, '..')
if (process.platform === 'win32' && !process.env.ANDROID_HOME && process.env.LOCALAPPDATA) {
  const sdk = resolve(process.env.LOCALAPPDATA, 'Android/Sdk')
  if (existsSync(sdk)) process.env.ANDROID_HOME = sdk
}
const apiBase = process.env.VITE_API_BASE_URL
const keystore = process.env.PLEX_ANDROID_KEYSTORE
const required = {
  VITE_API_BASE_URL: apiBase,
  PLEX_ANDROID_KEYSTORE: keystore,
  PLEX_ANDROID_STORE_PASSWORD: process.env.PLEX_ANDROID_STORE_PASSWORD,
  PLEX_ANDROID_KEY_ALIAS: process.env.PLEX_ANDROID_KEY_ALIAS,
  PLEX_ANDROID_KEY_PASSWORD: process.env.PLEX_ANDROID_KEY_PASSWORD,
}
const missing = Object.entries(required).filter(([, value]) => !value).map(([key]) => key)
if (missing.length) {
  throw new Error(`缺少正式 APK 构建配置：${missing.join(', ')}`)
}
const parsed = new URL(apiBase)
if (parsed.protocol !== 'https:' || !parsed.pathname.replace(/\/$/, '').endsWith('/api')) {
  throw new Error('VITE_API_BASE_URL 必须是公网 HTTPS 地址，并以 /api 结尾')
}
if (/^(localhost|127\.0\.0\.1|0\.0\.0\.0)$/.test(parsed.hostname)) {
  throw new Error('正式 APK 不能使用本机 API 地址')
}
if (!existsSync(keystore)) {
  throw new Error(`签名文件不存在：${keystore}`)
}

const healthUrl = new URL('v1/health', `${apiBase.replace(/\/$/, '')}/`)
let healthResponse
try {
  healthResponse = await fetch(healthUrl, {
    headers: { Origin: 'https://localhost' },
    signal: AbortSignal.timeout(15000),
  })
} catch (error) {
  throw new Error(`手机无法连接后端健康接口 ${healthUrl}：${error instanceof Error ? error.message : String(error)}`)
}
if (!healthResponse.ok) {
  throw new Error(`后端健康接口返回 HTTP ${healthResponse.status}`)
}
const health = await healthResponse.json()
if (health?.code !== 0 || health?.data?.database !== 'healthy') {
  throw new Error('后端健康接口未确认数据库可用，停止生成正式 APK')
}
const allowedOrigin = healthResponse.headers.get('access-control-allow-origin')
if (allowedOrigin !== '*' && allowedOrigin !== 'https://localhost') {
  throw new Error('后端未允许 Android WebView 来源 https://localhost 的跨域请求')
}
const preflight = await fetch(new URL('v1/auth/login', `${apiBase.replace(/\/$/, '')}/`), {
  method: 'OPTIONS',
  headers: {
    Origin: 'https://localhost',
    'Access-Control-Request-Method': 'POST',
    'Access-Control-Request-Headers': 'authorization,content-type',
  },
  signal: AbortSignal.timeout(15000),
})
const allowedHeaders = (preflight.headers.get('access-control-allow-headers') || '').toLowerCase()
if (!preflight.ok || !allowedHeaders.includes('authorization') || !allowedHeaders.includes('content-type')) {
  throw new Error('后端未通过 Android 登录请求的 CORS 预检')
}

function run(command, args, cwd = root) {
  const result = process.platform === 'win32'
    ? spawnSync('cmd.exe', ['/d', '/s', '/c', `${command} ${args.join(' ')}`], { cwd, env: process.env, stdio: 'inherit' })
    : spawnSync(command, args, { cwd, env: process.env, stdio: 'inherit' })
  if (result.status !== 0) throw new Error(`${command} 执行失败，退出码 ${result.status}`)
}

run('npm', ['run', 'build'])
run('npx', ['cap', 'sync', 'android'])
run(process.platform === 'win32' ? 'gradlew.bat' : './gradlew', ['assembleRelease', '--no-daemon', '--console=plain'], resolve(root, 'android'))

const apk = resolve(root, 'android/app/build/outputs/apk/release/app-release.apk')
if (!existsSync(apk)) throw new Error('Gradle 构建成功，但未找到 app-release.apk')
const hash = createHash('sha256')
for await (const chunk of createReadStream(apk)) hash.update(chunk)
console.log(`\nAPK: ${apk}\nSHA-256: ${hash.digest('hex')}`)
