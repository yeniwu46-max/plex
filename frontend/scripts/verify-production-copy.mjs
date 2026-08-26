import { readdir, readFile } from 'node:fs/promises'
import { extname, relative, resolve } from 'node:path'

const frontendRoot = resolve(import.meta.dirname, '..')
const sourceRoot = resolve(frontendRoot, 'src')

async function collectSourceFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true })
  const files = []

  for (const entry of entries) {
    const path = resolve(directory, entry.name)
    if (entry.isDirectory()) files.push(...await collectSourceFiles(path))
    else if (['.vue', '.ts'].includes(extname(entry.name)) && !entry.name.includes('.test.')) files.push(path)
  }

  return files
}

function templateOf(source) {
  return source.match(/<template(?:\s[^>]*)?>([\s\S]*?)<\/template>/i)?.[1] ?? ''
}

function lineNumber(source, index) {
  return source.slice(0, index).split('\n').length
}

const templateRules = [
  {
    name: '说明性括号',
    pattern: /（[^）\r\n]{1,80}）/g,
    message: '请将括号说明改为正式字段、完整句子或“·”分隔表达',
  },
  {
    name: '开发阶段文案',
    pattern: /\b(?:demo|mock|debug)\b|测试账号|演示数据|示例数据|占位功能|调试模式|开发模式|暂未开放|即将开放|建设中|fallback only|Loading daily quests|>\s*Retry\s*</gi,
    message: '请移除测试、演示、占位或调试阶段文案',
  },
  {
    name: '示例型占位符',
    pattern: /placeholder\s*=\s*["'][^"']*(?:例如[：:]|example\.com)[^"']*["']/gi,
    message: '请使用业务动作型占位提示，例如“请输入…”',
  },
]

const sourceRules = [
  {
    name: '调试上报地址',
    pattern: /127\.0\.0\.1:7606|\/api\/v1\/debug\//g,
    message: '生产源码中不得保留本地调试上报',
  },
  {
    name: '开发任务标记',
    pattern: /['"`]#\s*(?:TODO|FIXME)\b/gi,
    message: '面向用户的代码反馈中不得注入 TODO 或 FIXME',
  },
]

const failures = []
for (const file of await collectSourceFiles(sourceRoot)) {
  const source = await readFile(file, 'utf8')
  const template = extname(file) === '.vue' ? templateOf(source) : ''
  const templateStart = template ? source.indexOf(template) : -1

  for (const rule of templateRules) {
    rule.pattern.lastIndex = 0
    for (const match of template.matchAll(rule.pattern)) {
      failures.push({
        file,
        line: lineNumber(source, templateStart + match.index),
        rule: rule.name,
        text: match[0].replace(/\s+/g, ' ').trim(),
        message: rule.message,
      })
    }
  }

  for (const rule of sourceRules) {
    rule.pattern.lastIndex = 0
    for (const match of source.matchAll(rule.pattern)) {
      failures.push({
        file,
        line: lineNumber(source, match.index),
        rule: rule.name,
        text: match[0],
        message: rule.message,
      })
    }
  }
}

if (failures.length) {
  console.error(`生产文案检查失败，共发现 ${failures.length} 项：`)
  for (const failure of failures) {
    console.error(`- ${relative(frontendRoot, failure.file)}:${failure.line} [${failure.rule}] ${failure.text}`)
    console.error(`  ${failure.message}`)
  }
  process.exit(1)
}

console.log('生产文案检查通过：未发现说明性括号、开发阶段文案或调试上报。')
