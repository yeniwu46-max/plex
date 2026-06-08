/** 与 backend/app/services/student_progress.py DOMAIN_CATALOG 对齐 · Python 初学四阶段 */

export interface StarPathKnowledgePoint {
  id: string
  domainKey: string
  title: string
  summary: string
  detail: string
  tags: string[]
  level: '入门' | '进阶' | '挑战'
  /** 关联 Python 试炼题 id */
  questionId?: string
}

export interface StarPathDomainMeta {
  key: string
  title: string
  description: string
  focus: string
  knowledgePoints: StarPathKnowledgePoint[]
}

export const STAR_PATH_TAB_ALL = 'all' as const

export const STAR_PATH_TABS: Array<{ key: typeof STAR_PATH_TAB_ALL | string; label: string }> = [
  { key: STAR_PATH_TAB_ALL, label: '全部阶段' },
  { key: 'stage1', label: '第一段 Python' },
  { key: 'stage2', label: '条件与循环' },
  { key: 'stage3', label: '容器与函数' },
  { key: 'stage4', label: '算法小任务' },
]

export const STAR_PATH_DOMAINS: StarPathDomainMeta[] = [
  {
    key: 'stage1',
    title: '会写第一段 Python',
    description: '从 print 输出、注释到变量与 input，完成第一个可运行程序。',
    focus: 'print · 注释 · 变量 · input',
    knowledgePoints: [
      {
        id: 'stage1-intro',
        domainKey: 'stage1',
        title: 'Python 与 print',
        summary: '认识 Python 并用 print 输出文本。',
        detail: '运行环境、print 函数、字符串字面量与换行。',
        tags: ['intro', 'print'],
        level: '入门',
        questionId: 'hello-print',
      },
      {
        id: 'stage1-comment',
        domainKey: 'stage1',
        title: '注释',
        summary: '用 # 与三引号写注释，提升代码可读性。',
        detail: '单行注释、多行字符串注释、注释与代码混排规范。',
        tags: ['comment'],
        level: '入门',
        questionId: 'print-name',
      },
      {
        id: 'stage1-var',
        domainKey: 'stage1',
        title: '变量与类型',
        summary: '声明变量并理解 int/float/str/bool。',
        detail: '赋值、基本类型、简单类型转换与命名习惯。',
        tags: ['var', '类型'],
        level: '入门',
        questionId: 'var-sum',
      },
      {
        id: 'stage1-io',
        domainKey: 'stage1',
        title: '输入 input',
        summary: '用 input 读取用户输入并处理字符串。',
        detail: 'input 返回值、拼接与 int/float 转换。',
        tags: ['input', 'io'],
        level: '入门',
        questionId: 'var-product',
      },
    ],
  },
  {
    key: 'stage2',
    title: '条件与循环',
    description: '掌握运算表达式、分支与循环，写出能处理不同情况的程序。',
    focus: '运算 · if · for/while · range',
    knowledgePoints: [
      {
        id: 'stage2-ops',
        domainKey: 'stage2',
        title: '运算与表达式',
        summary: '算术、比较与逻辑运算组合判断。',
        detail: '运算符优先级、布尔表达式与格式化输出。',
        tags: ['ops', '表达式'],
        level: '入门',
        questionId: 'print-calc',
      },
      {
        id: 'stage2-cond',
        domainKey: 'stage2',
        title: 'if 分支',
        summary: '用 if/elif/else 处理多路分支。',
        detail: '缩进规则、嵌套分支与常见边界条件。',
        tags: ['cond', '分支'],
        level: '入门',
        questionId: 'if-max-two',
      },
      {
        id: 'stage2-loop',
        domainKey: 'stage2',
        title: '循环结构',
        summary: 'for 与 while 重复执行任务。',
        detail: '遍历序列、累加计数、循环终止条件。',
        tags: ['loop', '循环'],
        level: '入门',
        questionId: 'for-sum',
      },
      {
        id: 'stage2-range',
        domainKey: 'stage2',
        title: 'range 与控制',
        summary: 'range、break 与 continue 精细控制循环。',
        detail: 'range 参数、提前退出与跳过当前轮次。',
        tags: ['range', 'break'],
        level: '进阶',
        questionId: 'for-mult-table',
      },
    ],
  },
  {
    key: 'stage3',
    title: '容器、字符串与函数',
    description: '使用 list/dict/str 组织数据，并用函数封装可复用逻辑。',
    focus: 'list · dict · str · def',
    knowledgePoints: [
      {
        id: 'stage3-list',
        domainKey: 'stage3',
        title: '列表 list',
        summary: '创建列表、索引切片与遍历。',
        detail: 'append、len、索引与 for 遍历列表元素。',
        tags: ['list', '容器'],
        level: '入门',
        questionId: 'list-max',
      },
      {
        id: 'stage3-dict',
        domainKey: 'stage3',
        title: '字典 dict',
        summary: '键值对存储与常见操作。',
        detail: '访问、更新、遍历 keys/values 与成员检测。',
        tags: ['dict', '容器'],
        level: '进阶',
        questionId: 'list-sum-loop',
      },
      {
        id: 'stage3-str',
        domainKey: 'stage3',
        title: '字符串处理',
        summary: '索引、切片与常用字符串方法。',
        detail: 'split、strip、replace 与简单统计。',
        tags: ['str', '字符串'],
        level: '入门',
        questionId: 'print-name',
      },
      {
        id: 'stage3-func',
        domainKey: 'stage3',
        title: '函数基础',
        summary: '定义函数、参数与返回值。',
        detail: 'def、return、局部变量与简单封装。',
        tags: ['func', '函数'],
        level: '进阶',
        questionId: 'def-rect-area',
      },
    ],
  },
  {
    key: 'stage4',
    title: '简单算法小任务',
    description: '结合文件、异常与循环，完成求和、查找等入门算法练习。',
    focus: '文件 · 异常 · 统计 · 查找',
    knowledgePoints: [
      {
        id: 'stage4-file',
        domainKey: 'stage4',
        title: '文件读写',
        summary: '读取与写入文本文件。',
        detail: 'open、read/write、with 上下文管理器入门。',
        tags: ['file', '文件'],
        level: '进阶',
        questionId: 'capstone-range-sum',
      },
      {
        id: 'stage4-except',
        domainKey: 'stage4',
        title: '异常处理',
        summary: 'try/except 捕获常见错误。',
        detail: 'ValueError、ZeroDivisionError 与友好提示。',
        tags: ['except', '异常'],
        level: '进阶',
        questionId: 'if-pass',
      },
      {
        id: 'stage4-algo-sum',
        domainKey: 'stage4',
        title: '求和与统计',
        summary: '累加、计数与最值统计。',
        detail: '遍历列表求和、计数满足条件的元素。',
        tags: ['algo-sum', '统计'],
        level: '入门',
        questionId: 'list-sum-loop',
      },
      {
        id: 'stage4-algo-search',
        domainKey: 'stage4',
        title: '线性查找',
        summary: '在列表中查找目标元素。',
        detail: '顺序扫描、找到即返回、未找到的处理。',
        tags: ['algo-search', '查找'],
        level: '入门',
        questionId: 'list-min',
      },
    ],
  },
]

export function getStarPathDomain(key: string): StarPathDomainMeta | undefined {
  return STAR_PATH_DOMAINS.find((d) => d.key === key)
}

export function getKnowledgePointsForDomain(domainKey: string): StarPathKnowledgePoint[] {
  return getStarPathDomain(domainKey)?.knowledgePoints ?? []
}

export function getStarPathKnowledgePoint(id: string) {
  for (const domain of STAR_PATH_DOMAINS) {
    const point = domain.knowledgePoints.find((p) => p.id === id)
    if (point) return { domain, point }
  }
  return null
}
