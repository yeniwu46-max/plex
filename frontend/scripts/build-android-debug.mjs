import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { spawnSync } from 'node:child_process'

const root = resolve(import.meta.dirname, '..')
if (process.platform === 'win32' && !process.env.ANDROID_HOME && process.env.LOCALAPPDATA) {
  const sdk = resolve(process.env.LOCALAPPDATA, 'Android/Sdk')
  if (existsSync(sdk)) process.env.ANDROID_HOME = sdk
}

function run(command, args, cwd = root) {
  const result = process.platform === 'win32'
    ? spawnSync('cmd.exe', ['/d', '/s', '/c', `${command} ${args.join(' ')}`], { cwd, env: process.env, stdio: 'inherit' })
    : spawnSync(command, args, { cwd, env: process.env, stdio: 'inherit' })
  if (result.status !== 0) throw new Error(`${command} 执行失败，退出码 ${result.status}`)
}

run('npm', ['run', 'android:sync'])
run(process.platform === 'win32' ? 'gradlew.bat' : './gradlew', ['assembleDebug', '--no-daemon', '--console=plain'], resolve(root, 'android'))
console.log(`\n调试 APK: ${resolve(root, 'android/app/build/outputs/apk/debug/app-debug.apk')}`)
