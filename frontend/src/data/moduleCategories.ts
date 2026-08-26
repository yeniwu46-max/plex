/**
 * 模块 / 星轨板块下拉统一大类。
 * 细粒度知识点（如 print 输出与注释）不再直接展示，统一映射到下列大类。
 */
export const MODULE_CATEGORY_OPTIONS = [
  { label: '语言入门', value: 'lang-basics' },
  { label: '顺序结构', value: 'sequence' },
  { label: '分支结构', value: 'branch' },
  { label: '循环结构', value: 'loop' },
  { label: '数组', value: 'array' },
  { label: '字符串', value: 'string' },
  { label: '函数与递归', value: 'function' },
  { label: '查找与搜索', value: 'search' },
  { label: '其它', value: 'other' },
] as const

export type ModuleCategoryValue = (typeof MODULE_CATEGORY_OPTIONS)[number]['value']

/** 各大类用于资源生成 / 取题的代表知识点节点 */
export const MODULE_CATEGORY_REPRESENTATIVE: Record<ModuleCategoryValue, string> = {
  'lang-basics': 'lang-print',
  sequence: 'seq-arith',
  branch: 'branch-if',
  loop: 'loop-for',
  array: 'array-basic',
  string: 'string-index',
  function: 'func-define',
  search: 'search-linear',
  other: 'lang-var',
}

/** 旧细粒度 key / 节点 id → 大类 */
const FINE_TO_CATEGORY: Record<string, ModuleCategoryValue> = {
  'lang-basics': 'lang-basics',
  'lang-print': 'lang-basics',
  'lang-var': 'lang-basics',
  'lang-input': 'lang-basics',
  intro: 'lang-basics',
  print: 'lang-basics',
  comment: 'lang-basics',
  python: 'lang-basics',
  lang: 'lang-basics',
  var: 'lang-basics',
  syntax: 'lang-basics',
  basic: 'lang-basics',
  io: 'lang-basics',
  input: 'lang-basics',
  file: 'lang-basics',
  except: 'lang-basics',
  exception: 'lang-basics',
  sequence: 'sequence',
  'seq-arith': 'sequence',
  'seq-expr': 'sequence',
  'seq-type': 'sequence',
  ops: 'sequence',
  arith: 'sequence',
  expr: 'sequence',
  'operator-priority': 'sequence',
  datatype: 'sequence',
  cast: 'sequence',
  hightype: 'sequence',
  branch: 'branch',
  'branch-if': 'branch',
  'branch-elif': 'branch',
  'branch-nested': 'branch',
  cond: 'branch',
  condition: 'branch',
  if: 'branch',
  elif: 'branch',
  'multi-branch': 'branch',
  'nested-condition': 'branch',
  nested_condition: 'branch',
  loop: 'loop',
  'loop-for': 'loop',
  'loop-while': 'loop',
  'loop-nested': 'loop',
  'loop-control': 'loop',
  for: 'loop',
  range: 'loop',
  while: 'loop',
  nested: 'loop',
  nested_loop: 'loop',
  break: 'loop',
  continue: 'loop',
  array: 'array',
  'array-basic': 'array',
  'array-traverse': 'array',
  'array-2d': 'array',
  list: 'array',
  dict: 'array',
  string: 'string',
  'string-index': 'string',
  'string-method': 'string',
  'string-scan': 'string',
  str: 'string',
  function: 'function',
  'func-define': 'function',
  'func-param': 'function',
  'func-recursion': 'function',
  func: 'function',
  search: 'search',
  'search-linear': 'search',
  'search-binary': 'search',
  'search-sort': 'search',
  'search-stat': 'search',
  'algo-sum': 'search',
  'algo-search': 'search',
  algo: 'search',
  sum: 'search',
  count: 'search',
  'algo-dedup': 'search',
  dedup: 'search',
  other: 'other',
}

export function resolveModuleCategory(key: string | null | undefined): ModuleCategoryValue {
  if (!key) return 'other'
  return FINE_TO_CATEGORY[key] ?? FINE_TO_CATEGORY[key.toLowerCase()] ?? 'other'
}

export function knowledgeKeyForModuleCategory(category: ModuleCategoryValue): string {
  return MODULE_CATEGORY_REPRESENTATIVE[category] ?? MODULE_CATEGORY_REPRESENTATIVE.other
}

export function labelForModuleCategory(value: string): string {
  return MODULE_CATEGORY_OPTIONS.find((item) => item.value === value)?.label ?? value
}
