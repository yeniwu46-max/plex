export type KgNodeStatus = 'mastered' | 'learning' | 'weak' | 'unlearned' | 'recommended'

export interface KgNode {
  id: string
  label: string
  domain: string
  status: KgNodeStatus
  description: string
  level: 'basic' | 'intermediate' | 'advanced'
  x?: number
  y?: number
}

export type KgEdgeType = 'prerequisite' | 'related' | 'path' | 'advanced'

export interface KgEdge {
  id: string
  source: string
  target: string
  type: KgEdgeType
  label?: string
}

export const KG_NODE_STATUS_COLOR: Record<KgNodeStatus, string> = {
  mastered: '#22c55e',
  learning: '#38bdf8',
  weak: '#f87171',
  unlearned: '#475569',
  recommended: '#a78bfa',
}

export const KG_NODE_STATUS_LABEL: Record<KgNodeStatus, string> = {
  mastered: '已掌握',
  learning: '学习中',
  weak: '薄弱',
  unlearned: '未学习',
  recommended: '推荐学习',
}

/** Python 初学者静态拓扑（与后端 knowledge_graph.py 对齐，API 失败时作轻量回退） */
export const KG_NODES: KgNode[] = [
  { id: 'intro', label: 'Python 入门', domain: '入门', status: 'unlearned', level: 'basic', description: '认识 Python 与 print 输出', x: 80, y: 180 },
  { id: 'comment', label: '注释', domain: '入门', status: 'unlearned', level: 'basic', description: '单行与多行注释', x: 80, y: 320 },
  { id: 'var', label: '变量与类型', domain: '基础', status: 'unlearned', level: 'basic', description: '变量、数字、字符串、布尔与类型转换', x: 240, y: 180 },
  { id: 'io', label: '输入 input', domain: '基础', status: 'unlearned', level: 'basic', description: '使用 input 读取用户输入', x: 240, y: 320 },
  { id: 'ops', label: '运算与表达式', domain: '基础', status: 'unlearned', level: 'basic', description: '算术、比较、逻辑运算与格式化输出', x: 400, y: 180 },
  { id: 'cond', label: '条件分支', domain: '控制流', status: 'unlearned', level: 'basic', description: 'if / elif / else', x: 400, y: 320 },
  { id: 'loop', label: '循环结构', domain: '控制流', status: 'unlearned', level: 'basic', description: 'while 与 for 循环', x: 560, y: 180 },
  { id: 'range', label: 'range 与控制', domain: '控制流', status: 'unlearned', level: 'basic', description: 'range、break、continue', x: 560, y: 320 },
  { id: 'list', label: '列表 list', domain: '容器', status: 'unlearned', level: 'basic', description: '列表创建、索引、切片与遍历', x: 720, y: 180 },
  { id: 'tuple', label: '元组与集合', domain: '容器', status: 'unlearned', level: 'basic', description: 'tuple 与 set 基础', x: 720, y: 320 },
  { id: 'dict', label: '字典 dict', domain: '容器', status: 'unlearned', level: 'intermediate', description: '键值对与常见操作', x: 880, y: 180 },
  { id: 'str', label: '字符串处理', domain: '容器', status: 'unlearned', level: 'basic', description: '索引、切片、常用方法与简单统计', x: 880, y: 320 },
  { id: 'func', label: '函数基础', domain: '函数', status: 'unlearned', level: 'intermediate', description: '定义函数、参数与返回值', x: 1040, y: 250 },
  { id: 'file', label: '文件读写', domain: '工程', status: 'unlearned', level: 'intermediate', description: '读取与写入文本文件', x: 1200, y: 180 },
  { id: 'except', label: '异常处理', domain: '工程', status: 'unlearned', level: 'intermediate', description: 'try / except 与常见错误', x: 1200, y: 320 },
  { id: 'algo-sum', label: '求和与统计', domain: '算法入门', status: 'unlearned', level: 'basic', description: '累加、计数、最大值最小值', x: 1360, y: 180 },
  { id: 'algo-search', label: '线性查找', domain: '算法入门', status: 'unlearned', level: 'basic', description: '在列表中查找目标元素', x: 1360, y: 320 },
  { id: 'algo-sort', label: '简单排序思想', domain: '算法入门', status: 'unlearned', level: 'intermediate', description: '理解冒泡排序的基本过程', x: 1520, y: 180 },
  { id: 'algo-dedup', label: '去重与频率', domain: '算法入门', status: 'unlearned', level: 'intermediate', description: '集合去重与简单频率统计', x: 1520, y: 320 },
  { id: 'nested', label: '嵌套循环', domain: '算法入门', status: 'unlearned', level: 'intermediate', description: '双重循环解决简单组合问题', x: 1680, y: 250 },
]

export const KG_EDGES: KgEdge[] = [
  { id: 'e1', source: 'intro', target: 'comment', type: 'prerequisite', label: '前置' },
  { id: 'e2', source: 'intro', target: 'var', type: 'prerequisite', label: '前置' },
  { id: 'e3', source: 'var', target: 'io', type: 'prerequisite', label: '前置' },
  { id: 'e4', source: 'var', target: 'ops', type: 'prerequisite', label: '前置' },
  { id: 'e5', source: 'ops', target: 'cond', type: 'prerequisite', label: '前置' },
  { id: 'e6', source: 'cond', target: 'loop', type: 'prerequisite', label: '前置' },
  { id: 'e7', source: 'loop', target: 'range', type: 'related', label: '相关' },
  { id: 'e8', source: 'loop', target: 'list', type: 'prerequisite', label: '前置' },
  { id: 'e9', source: 'list', target: 'tuple', type: 'related', label: '相关' },
  { id: 'e10', source: 'list', target: 'dict', type: 'prerequisite', label: '前置' },
  { id: 'e11', source: 'var', target: 'str', type: 'related', label: '相关' },
  { id: 'e12', source: 'str', target: 'func', type: 'prerequisite', label: '前置' },
  { id: 'e13', source: 'loop', target: 'func', type: 'prerequisite', label: '前置' },
  { id: 'e14', source: 'func', target: 'file', type: 'path', label: '推荐路径' },
  { id: 'e15', source: 'file', target: 'except', type: 'related', label: '相关' },
  { id: 'e16', source: 'loop', target: 'algo-sum', type: 'prerequisite', label: '前置' },
  { id: 'e17', source: 'list', target: 'algo-search', type: 'prerequisite', label: '前置' },
  { id: 'e18', source: 'algo-sum', target: 'algo-sort', type: 'path', label: '推荐路径' },
  { id: 'e19', source: 'list', target: 'algo-dedup', type: 'path', label: '推荐路径' },
  { id: 'e20', source: 'loop', target: 'nested', type: 'prerequisite', label: '前置' },
]

export function getStudentNodes(masteredIds: string[] = []): KgNode[] {
  return KG_NODES.map((node) => ({
    ...node,
    status: masteredIds.includes(node.id) ? 'mastered' : node.status,
  }))
}
