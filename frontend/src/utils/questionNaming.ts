import type { PythonTrialQuestion } from '../data/pythonTrialQuestions'

/** 与 backend practice_question.KNOWLEDGE_CODE_PREFIX 对齐（26 个知识点节点） */
export const KNOWLEDGE_CODE_PREFIX: Record<string, string> = {
  'lang-print': 'P',
  'lang-var': 'V',
  'lang-input': 'I',
  'seq-arith': 'O',
  'seq-expr': 'X',
  'seq-type': 'Y',
  'branch-if': 'C',
  'branch-elif': 'M',
  'branch-nested': 'N',
  'loop-for': 'L',
  'loop-while': 'W',
  'loop-nested': 'U',
  'loop-control': 'K',
  'array-basic': 'S',
  'array-traverse': 'Z',
  'array-2d': 'D',
  'string-index': 'T',
  'string-method': 'J',
  'string-scan': 'Q',
  'func-define': 'F',
  'func-param': 'R',
  'func-recursion': 'E',
  'search-linear': 'H',
  'search-binary': 'B',
  'search-sort': 'G',
  'search-stat': 'A',
  // 历史 knowledge_key 别名，老数据里仍会出现
  intro: 'P',
  print: 'P',
  comment: 'P',
  var: 'V',
  io: 'I',
  input: 'I',
  ops: 'O',
  cond: 'C',
  loop: 'L',
  range: 'L',
  list: 'S',
  dict: 'D',
  str: 'T',
  func: 'F',
  file: 'I',
  except: 'I',
  'algo-sum': 'A',
  'algo-search': 'H',
  班级: 'B',
  角斗士: 'D',
  猜拳: 'R',
}

/** 内置题号（与 backend BUILTIN_QUESTION_CODES 对齐） */
export const QUESTION_CODE_BY_ID: Record<string, string> = {
  'hello-print': 'P0001',
  'print-name': 'P0002',
  'print-lines': 'P0003',
  'print-calc': 'O0001',
  'var-sum': 'V0001',
  'var-product': 'V0002',
  'var-diff': 'V0003',
  'var-quotient': 'V0004',
  'if-parity': 'C0003',
  'if-max-two': 'C0001',
  'if-pass': 'C0004',
  'if-sign': 'C0005',
  'for-sum': 'L0001',
  'for-factorial': 'L0004',
  'for-count-evens': 'L0005',
  'for-mult-table': 'R0001',
  'list-max': 'S0001',
  'list-min': 'S0002',
  'list-sum-loop': 'S0003',
  'list-ends': 'S0004',
  'list-total': 'S0005',
  'def-rect-area': 'F0001',
  'def-perimeter': 'F0002',
  'def-double': 'F0003',
  'def-max-two': 'F0004',
  'capstone-positive-count': 'G0001',
  'capstone-range-sum': 'G0002',
  'capstone-fizz': 'C0002',
  'algo-bubble-sort': 'H0001',
  'algo-bubble-pass': 'H0002',
  'algo-bubble-swaps': 'H0003',
  'algo-selection-sort': 'H0004',
  'algo-selection-min-index': 'H0005',
  'algo-selection-step': 'H0006',
  'algo-binary-search': 'H0007',
  'algo-binary-check': 'H0008',
  'algo-binary-first': 'H0009',
  'class-hard-sum-two': 'B0001',
  'class-hard-max-two': 'B0002',
  'class-hard-positive-sum': 'B0003',
  'arena-gladiator-sum': 'D0001',
  'arena-gladiator-max': 'D0002',
  'arena-gladiator-product': 'D0003',
  'arena-rps-move': 'R0001',
}

/** 已知题目 id → 人工短标题（8–20 字） */
export const CURATED_SHORT_TITLES: Record<string, string> = {
  'hello-print': '星际问候输出',
  'print-name': '命名问候信号',
  'print-lines': '双行信号广播',
  'print-calc': '算力表达式输出',
  'var-sum': '双变量能量求和',
  'var-product': '变量乘积运算',
  'var-diff': '变量差值计算',
  'var-quotient': '整除步数换算',
  'if-parity': '奇偶探测器',
  'if-max-two': '双数取大判定',
  'if-pass': '及格线判定',
  'if-sign': '正负零判别',
  'for-sum': '星轨区间求和',
  'for-factorial': '阶乘引擎',
  'for-count-evens': '偶数计数扫描',
  'for-mult-table': '乘法星轨表',
  'list-max': '列表峰值扫描',
  'list-min': '列表谷值扫描',
  'list-sum-loop': '列表循环累加',
  'list-ends': '首尾元素求和',
  'list-total': '星链元素聚合',
  'def-rect-area': '矩形星域面积',
  'def-perimeter': '矩形周长星环',
  'def-double': '双倍增幅函数',
  'def-max-two': '双值择优函数',
  'capstone-positive-count': '正数元素统计',
  'capstone-range-sum': '闭区间整数求和',
  'capstone-fizz': 'Fizz 信号判定',
  'algo-bubble-sort': '冒泡升序排列',
  'algo-bubble-pass': '冒泡单轮交换',
  'algo-bubble-swaps': '冒泡交换计数',
  'algo-selection-sort': '选择升序排列',
  'algo-selection-min-index': '最小元素索引',
  'algo-selection-step': '选择排序单步',
  'algo-binary-search': '二分目标定位',
  'algo-binary-check': '有序表存在判定',
  'algo-binary-first': '首个不小于定位',
}

const LIST_TITLE_PREFIXES = ['[沙盒]', '【沙盒】', '[沙盒] ', '【沙盒】 ']

/** 列表展示时去除冗余前缀（如沙盒标记） */
export function stripListTitlePrefix(title: string): string {
  let line = (title || '').trim()
  for (const prefix of LIST_TITLE_PREFIXES) {
    if (line.startsWith(prefix)) {
      line = line.slice(prefix.length).trim()
    }
  }
  return line
}

const VERBOSE_PREFIXES = [
  '编写程序，',
  '编写程序',
  '设计一个程序来',
  '设计一个程序',
  '设计程序',
  '请编写',
  '请实现',
  '实现一个',
  '实现函数',
  '那个兔子又对你说：',
  '那个兔子',
  '用户输入',
  '输入三个整数',
  '输入{[三个整数]}，你的程序',
  '【教师试炼】',
]

const CODE_TITLE_SPLIT = /^([A-Z]\d{4})\s*[·•\-—]\s*(.+)$/

/** 题干关键词 → 语义短标题 */
const SEMANTIC_TITLE_RULES: Array<{ pattern: RegExp; title: string }> = [
  { pattern: /哥德巴赫|Goldbach|质数之和|二个质数|两个质数|两.*质数.*之和/, title: '哥德巴赫分解' },
  { pattern: /冒泡|bubble.?sort|相邻.*交换/, title: '冒泡排序' },
  { pattern: /选择排序|selection.?sort|每轮.*最小/, title: '选择排序' },
  { pattern: /二分|binary.?search|有序.*查找/, title: '二分查找' },
  { pattern: /斐波那契|爬楼梯|台阶.*方案/, title: '爬楼梯方案数' },
  { pattern: /最大子段|Kadane|连续子数组.*最大和/, title: '最大子段和' },
  { pattern: /水仙花/, title: '水仙花数判定' },
  { pattern: /质数|素数|prime/, title: '质数判定' },
  { pattern: /阶乘|factorial/, title: '阶乘计算' },
  { pattern: /最大公约|gcd|GCD/, title: '最大公约数' },
  { pattern: /最小公倍|lcm|LCM/, title: '最小公倍数' },
  { pattern: /排序|sort/, title: '序列排序' },
  { pattern: /Hello|PLEX|问候/, title: '问候语输出' },
  { pattern: /print|输出/, title: '标准输出' },
  { pattern: /input|输入/, title: '读取输入' },
  { pattern: /变量|赋值/, title: '变量运算' },
  { pattern: /if|分支|判断|奇偶/, title: '条件分支' },
  { pattern: /for|while|循环|累加|计数/, title: '循环统计' },
  { pattern: /列表|list|数组/, title: '列表处理' },
  { pattern: /字典|dict|键值/, title: '字典操作' },
  { pattern: /字符串|strip|split|切片/, title: '字符串处理' },
  { pattern: /函数|def|return/, title: '函数封装' },
  { pattern: /三角形.*面积|底.*高/, title: '三角形面积' },
  { pattern: /圆.*面积|半径/, title: '圆面积计算' },
  { pattern: /一元二次|方程.*解/, title: '一元二次方程' },
  { pattern: /三个数.*排序|从小到大/, title: '三数排序' },
  { pattern: /较大|最大|max/, title: '取较大值' },
  { pattern: /千位/, title: '千位数字提取' },
  { pattern: /约数|因子/, title: '约数求和' },
  { pattern: /完全数/, title: '完全数判定' },
  { pattern: /硬币|换法/, title: '硬币凑数' },
  { pattern: /BFS|广度优先|最短路/, title: 'BFS 最短路' },
  { pattern: /点积|向量/, title: '向量点积' },
  { pattern: /叉积|转向/, title: '叉积转向' },
  { pattern: /栈|stack|LIFO/, title: '栈模拟' },
  { pattern: /二叉树|树.*深度/, title: '二叉树深度' },
  { pattern: /图.*度|邻接/, title: '图的度数' },
  { pattern: /能被.*整除|整除.*个数/, title: '整除条件计数' },
  { pattern: /Fizz|Buzz/, title: 'Fizz 信号' },
]

function stripVerboseStem(stem: string): string {
  let line = (stem || '').trim().split('\n')[0]?.replace(/\s+/g, ' ') ?? ''
  for (const prefix of VERBOSE_PREFIXES) {
    if (line.startsWith(prefix)) {
      line = line.slice(prefix.length).replace(/^[：:，,\s]+/, '')
    }
  }
  line = line.split(/[。；;！!？?]/)[0]?.trim() ?? line
  line = line.replace(/^(给定|已有|已知|请|你)/, '').trim()
  return line.replace(/[`"{\[]/g, '').trim()
}

/** 从题干推导 8–20 字短标题（语义优先，避免截断题干） */
export function deriveShortTitle(
  stem: string,
  fallback = '编程练习',
  maxLen = 20,
): string {
  const raw = (stem || '').trim()
  if (!raw) return fallback

  for (const rule of SEMANTIC_TITLE_RULES) {
    if (rule.pattern.test(raw)) {
      const title = rule.title
      return title.length <= maxLen ? title : `${title.slice(0, maxLen - 1)}…`
    }
  }

  let line = stripVerboseStem(raw)
  if (!line) return fallback

  if (line.length > maxLen) {
    line = `${line.slice(0, maxLen - 1).replace(/[，,\s]+$/, '')}…`
  }

  return line || fallback
}

function looksLikeTruncatedContent(title: string, description: string): boolean {
  const t = title.trim()
  if (!t) return true
  if (/…$|\.\.\.$/.test(t)) return true
  if (t.length > 22) return true
  const descStart = stripVerboseStem(description).slice(0, Math.min(12, t.length))
  if (descStart && t.startsWith(descStart)) return true
  const verboseStarts = ['对于', '输入', '用户', '编写', '设计', '实现', '给定', '输出文件', '输入文件']
  if (verboseStarts.some((p) => t.startsWith(p))) return true
  return false
}

export function splitCodeAndTitle(rawTitle: string): { code?: string; title: string } {
  const match = CODE_TITLE_SPLIT.exec(rawTitle.trim())
  if (match) {
    return { code: match[1], title: match[2]?.trim() || rawTitle }
  }
  return { title: rawTitle.trim() }
}

function prefixForQuestion(question: PythonTrialQuestion): string {
  for (const tag of question.tags) {
    const key = tag.trim().toLowerCase()
    if (KNOWLEDGE_CODE_PREFIX[key]) return KNOWLEDGE_CODE_PREFIX[key]
    if (KNOWLEDGE_CODE_PREFIX[tag]) return KNOWLEDGE_CODE_PREFIX[tag]
  }
  const topicKey = question.topic.split(/[·\s]/)[0]?.trim().toLowerCase()
  if (topicKey && KNOWLEDGE_CODE_PREFIX[topicKey]) return KNOWLEDGE_CODE_PREFIX[topicKey]
  return 'Q'
}

function fallbackCode(question: PythonTrialQuestion): string {
  const prefix = prefixForQuestion(question)
  let hash = 0
  for (let i = 0; i < question.id.length; i += 1) {
    hash = (hash << 5) - hash + question.id.charCodeAt(i)
    hash |= 0
  }
  return `${prefix}${String(Math.abs(hash) % 1000).padStart(3, '0')}`
}

export function resolveQuestionCode(question: PythonTrialQuestion): string | undefined {
  if (question.code) return question.code
  if (QUESTION_CODE_BY_ID[question.id]) return QUESTION_CODE_BY_ID[question.id]
  const fromTitle = splitCodeAndTitle(question.title).code
  if (fromTitle) return fromTitle
  return fallbackCode(question)
}

export function resolveQuestionShortTitle(question: PythonTrialQuestion): string {
  if (CURATED_SHORT_TITLES[question.id]) {
    return CURATED_SHORT_TITLES[question.id]!
  }

  const parsed = splitCodeAndTitle(stripListTitlePrefix(question.title))
  const fromTitle = parsed.title
  const stem = question.description || fromTitle || question.topic

  const semantic = deriveShortTitle(stem, question.topic || '编程练习')
  const titleLooksCurated =
    fromTitle.length >= 4 &&
    fromTitle.length <= 20 &&
    !looksLikeTruncatedContent(fromTitle, stem) &&
    !fromTitle.includes('编写程序') &&
    !fromTitle.includes('请实现') &&
    !fromTitle.includes('用户输入')

  if (titleLooksCurated) return fromTitle
  return semantic
}

/** 规范化题目：分离题号与短标题 */
export function normalizeQuestion<T extends PythonTrialQuestion>(question: T): T {
  const code = resolveQuestionCode(question)
  const title = resolveQuestionShortTitle({ ...question, code })
  return { ...question, code, title }
}

/** 展示用：P0001 · print输出Hello */
export function formatQuestionLabel(question: Pick<PythonTrialQuestion, 'code' | 'title' | 'id' | 'description' | 'topic' | 'tags'>): string {
  const normalized = normalizeQuestion({
    id: question.id ?? '',
    title: question.title,
    topic: question.topic ?? '',
    difficulty: '入门',
    rewardXp: 0,
    durationMin: 0,
    tags: question.tags ?? [],
    description: question.description ?? question.title,
    constraints: [],
    examples: [],
    testCases: [],
    starterCode: '',
    runMode: 'stdout',
    hint: '',
    code: question.code,
  })
  if (normalized.code) return `${normalized.code} · ${normalized.title}`
  return normalized.title
}
