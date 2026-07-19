/** 与 backend/app/services/student_progress.py DOMAIN_CATALOG 对齐 · Python 七大学域 */

export interface StarPathKnowledgePoint {
  id: string
  domainKey: string
  title: string
  summary: string
  detail: string
  tags: string[]
  level: '入门' | '进阶' | '挑战'
  /** 初识导引步骤（仅首个知识点） */
  introSteps?: string[]
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
  { key: 'data-vars', label: '数据与变量' },
  { key: 'operators', label: '运算符的使用' },
  { key: 'flow-control', label: '流程控制' },
  { key: 'strings', label: '字符串' },
  { key: 'lists-dicts', label: '列表与字典' },
  { key: 'functions', label: '函数' },
  { key: 'recursion-iter', label: '递归与迭代' },
]

export const STAR_PATH_DOMAINS: StarPathDomainMeta[] = [
  {
    key: 'data-vars',
    title: '数据与变量',
    description: '你与小E 登陆「数据星」，从第一行 print 到变量与 input，收集星球通讯的基础数据。',
    focus: 'print · 注释 · 变量 · input',
    knowledgePoints: [
      {
        id: 'stage1-intro',
        domainKey: 'data-vars',
        title: 'Python 与 print',
        summary: '小E 的探测器需要发出第一束信号——用 print 向宇宙问好。',
        detail: '运行环境、print 函数、字符串字面量与换行。',
        introSteps: [
          '在编辑器里写 print("Hello")，点击运行测试确认输出。',
          '尝试用逗号连接多个内容：print("XP", 100)。',
          '完成左侧示例后，点击「开始编程试炼」进入第一题。',
        ],
        tags: ['intro', 'print'],
        level: '入门',
        questionId: 'hello-print',
      },
      {
        id: 'stage1-comment',
        domainKey: 'data-vars',
        title: '注释',
        summary: '在星图日志里用 # 留下航行备注，让代码更易读。',
        detail: '单行注释、多行字符串注释、注释与代码混排规范。',
        tags: ['comment'],
        level: '入门',
        questionId: 'print-name',
      },
      {
        id: 'stage1-var',
        domainKey: 'data-vars',
        title: '变量与类型',
        summary: '把探测器读数存进变量舱，理解 int/float/str/bool。',
        detail: '赋值、基本类型、简单类型转换与命名习惯。',
        tags: ['var', '类型'],
        level: '入门',
        questionId: 'var-sum',
      },
      {
        id: 'stage1-io',
        domainKey: 'data-vars',
        title: '输入 input',
        summary: '接收地面站传来的指令字符串，用 input 读取并处理。',
        detail: 'input 返回值、拼接与 int/float 转换。',
        tags: ['input', 'io'],
        level: '入门',
        questionId: 'var-product',
      },
    ],
  },
  {
    key: 'operators',
    title: '运算符的使用',
    description: '在「运算星云」中，小E 教你组合算术、比较与逻辑运算，校准飞船的计算核心。',
    focus: '算术 · 比较 · 逻辑 · 优先级',
    knowledgePoints: [
      {
        id: 'stage2-ops',
        domainKey: 'operators',
        title: '运算与表达式',
        summary: '算术、比较与逻辑运算组合判断。',
        detail: '运算符优先级、布尔表达式与格式化输出。',
        tags: ['ops', '表达式'],
        level: '入门',
        questionId: 'print-calc',
      },
    ],
  },
  {
    key: 'flow-control',
    title: '流程控制',
    description: '穿越「分支峡谷」与「循环环带」，小E 带你用 if 与 for 决定飞船的每一步航向。',
    focus: 'if · for/while · range · break',
    knowledgePoints: [
      {
        id: 'stage2-cond',
        domainKey: 'flow-control',
        title: 'if 分支',
        summary: '用 if/elif/else 处理多路分支。',
        detail: '缩进规则、嵌套分支与常见边界条件。',
        tags: ['cond', '分支'],
        level: '入门',
        questionId: 'if-max-two',
      },
      {
        id: 'stage2-loop',
        domainKey: 'flow-control',
        title: '循环结构',
        summary: 'for 与 while 重复执行任务。',
        detail: '遍历序列、累加计数、循环终止条件。',
        tags: ['loop', '循环'],
        level: '入门',
        questionId: 'for-sum',
      },
      {
        id: 'stage2-range',
        domainKey: 'flow-control',
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
    key: 'strings',
    title: '字符串',
    description: '在「语符卫星」上，索引、切片与字符串方法是破译外星电报的关键。',
    focus: '索引 · 切片 · split · strip',
    knowledgePoints: [
      {
        id: 'stage3-str',
        domainKey: 'strings',
        title: '字符串处理',
        summary: '索引、切片与常用字符串方法。',
        detail: 'split、strip、replace 与简单统计。',
        tags: ['str', '字符串'],
        level: '入门',
        questionId: 'print-name',
      },
    ],
  },
  {
    key: 'lists-dicts',
    title: '列表与字典',
    description: '小E 打开货舱：用 list 与 dict 整理探险样本与星图坐标。',
    focus: 'list · dict · 遍历 · 键值访问',
    knowledgePoints: [
      {
        id: 'stage3-list',
        domainKey: 'lists-dicts',
        title: '列表 list',
        summary: '创建列表、索引切片与遍历。',
        detail: 'append、len、索引与 for 遍历列表元素。',
        tags: ['list', '容器'],
        level: '入门',
        questionId: 'list-max',
      },
      {
        id: 'stage3-dict',
        domainKey: 'lists-dicts',
        title: '字典 dict',
        summary: '键值对存储与常见操作。',
        detail: '访问、更新、遍历 keys/values 与成员检测。',
        tags: ['dict', '容器'],
        level: '进阶',
        questionId: 'list-sum-loop',
      },
    ],
  },
  {
    key: 'functions',
    title: '函数',
    description: '在「封装空间站」定义可复用的函数模块，让小E 的探测器任务一键部署。',
    focus: 'def · 参数 · return · 局部变量',
    knowledgePoints: [
      {
        id: 'stage3-func',
        domainKey: 'functions',
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
    key: 'recursion-iter',
    title: '递归与迭代',
    description: '深入「算法深空」，用循环与排序/查找算法整理混沌星尘，找到规律。',
    focus: '迭代 · 嵌套循环 · 排序 · 查找',
    knowledgePoints: [
      {
        id: 'stage4-algo-sum',
        domainKey: 'recursion-iter',
        title: '迭代求和与统计',
        summary: '用循环累加、计数与求最值。',
        detail: '遍历列表求和、计数满足条件的元素。',
        tags: ['algo-sum', '迭代'],
        level: '入门',
        questionId: 'list-sum-loop',
      },
      {
        id: 'stage4-bubble',
        domainKey: 'recursion-iter',
        title: '冒泡排序',
        summary: '相邻比较交换，理解最基础的排序过程。',
        detail: '双重循环、交换元素、每轮将最大值“冒”到末尾。',
        tags: ['algo-bubble', '排序'],
        level: '进阶',
        questionId: 'algo-bubble-sort',
      },
      {
        id: 'stage4-selection',
        domainKey: 'recursion-iter',
        title: '选择排序',
        summary: '每轮选择最小元素放到前面。',
        detail: '找最小索引、交换、理解选择排序与冒泡的区别。',
        tags: ['algo-selection', '排序'],
        level: '进阶',
        questionId: 'algo-selection-sort',
      },
      {
        id: 'stage4-binary',
        domainKey: 'recursion-iter',
        title: '二分查找',
        summary: '在有序列表中快速定位目标。',
        detail: '维护左右边界、取中点比较、缩小搜索范围。',
        tags: ['algo-binary', '查找'],
        level: '进阶',
        questionId: 'algo-binary-search',
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
