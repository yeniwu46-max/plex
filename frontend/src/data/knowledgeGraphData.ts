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

export const KG_NODES: KgNode[] = [
  { id: 'var', label: '变量与类型', domain: '基础', status: 'mastered', level: 'basic', description: '变量赋值、基本数据类型（int/float/str/bool）', x: 100, y: 200 },
  { id: 'io', label: '输入输出', domain: '基础', status: 'mastered', level: 'basic', description: 'input() 与 print() 的基本用法', x: 100, y: 350 },
  { id: 'cond', label: '条件判断', domain: '控制流', status: 'mastered', level: 'basic', description: 'if / elif / else 控制结构', x: 280, y: 180 },
  { id: 'loop', label: '循环结构', domain: '控制流', status: 'learning', level: 'basic', description: 'for 循环与 while 循环', x: 280, y: 320 },
  { id: 'func', label: '函数', domain: '函数', status: 'learning', level: 'intermediate', description: '函数定义、参数、返回值', x: 460, y: 250 },
  { id: 'list', label: '列表', domain: '数据结构', status: 'weak', level: 'basic', description: '列表增删改查与切片操作', x: 460, y: 400 },
  { id: 'str', label: '字符串', domain: '数据结构', status: 'weak', level: 'basic', description: '字符串方法、格式化与处理', x: 280, y: 460 },
  { id: 'dict', label: '字典', domain: '数据结构', status: 'recommended', level: 'intermediate', description: '键值对存储与字典操作', x: 640, y: 350 },
  { id: 'recur', label: '递归', domain: '函数', status: 'unlearned', level: 'advanced', description: '递归思想与常见递归问题', x: 640, y: 200 },
  { id: 'sort', label: '排序算法', domain: '算法', status: 'unlearned', level: 'advanced', description: '冒泡、选择、快排等排序算法', x: 820, y: 280 },
  { id: 'search', label: '搜索算法', domain: '算法', status: 'unlearned', level: 'advanced', description: '线性搜索与二分查找', x: 820, y: 420 },
  { id: 'class', label: '类与对象', domain: '面向对象', status: 'unlearned', level: 'advanced', description: '类定义、封装、继承、多态', x: 640, y: 500 },
  { id: 'except', label: '异常处理', domain: '工程', status: 'recommended', level: 'intermediate', description: 'try/except/finally 与自定义异常', x: 460, y: 550 },
  { id: 'file', label: '文件操作', domain: '工程', status: 'unlearned', level: 'intermediate', description: '文件读写、上下文管理器', x: 820, y: 560 },
  { id: 'dp', label: '动态规划', domain: '算法', status: 'unlearned', level: 'advanced', description: '状态转移与记忆化搜索', x: 1000, y: 350 },
  { id: 'greedy', label: '贪心算法', domain: '算法', status: 'unlearned', level: 'advanced', description: '局部最优推导全局最优', x: 1000, y: 480 },
  { id: 'graph', label: '图论基础', domain: '算法', status: 'unlearned', level: 'advanced', description: '图的表示、BFS/DFS 遍历', x: 1000, y: 220 },
  { id: 'complex', label: '算法复杂度', domain: '基础', status: 'unlearned', level: 'intermediate', description: '时间复杂度与空间复杂度分析', x: 460, y: 120 },
  { id: 'tuple', label: '元组与集合', domain: '数据结构', status: 'recommended', level: 'basic', description: 'tuple 不可变特性与 set 去重操作', x: 640, y: 460 },
  { id: 'comp', label: '推导式', domain: '函数', status: 'unlearned', level: 'intermediate', description: '列表/字典/集合推导式', x: 820, y: 150 },
]

export const KG_EDGES: KgEdge[] = [
  { id: 'e1', source: 'var', target: 'cond', type: 'prerequisite', label: '前置' },
  { id: 'e2', source: 'var', target: 'loop', type: 'prerequisite', label: '前置' },
  { id: 'e3', source: 'io', target: 'loop', type: 'prerequisite', label: '前置' },
  { id: 'e4', source: 'cond', target: 'func', type: 'prerequisite', label: '前置' },
  { id: 'e5', source: 'loop', target: 'func', type: 'prerequisite', label: '前置' },
  { id: 'e6', source: 'loop', target: 'list', type: 'prerequisite', label: '前置' },
  { id: 'e7', source: 'var', target: 'str', type: 'related', label: '相关' },
  { id: 'e8', source: 'list', target: 'dict', type: 'prerequisite', label: '前置' },
  { id: 'e9', source: 'func', target: 'recur', type: 'prerequisite', label: '前置' },
  { id: 'e10', source: 'recur', target: 'sort', type: 'path', label: '推荐路径' },
  { id: 'e11', source: 'list', target: 'sort', type: 'prerequisite', label: '前置' },
  { id: 'e12', source: 'cond', target: 'search', type: 'prerequisite', label: '前置' },
  { id: 'e13', source: 'sort', target: 'dp', type: 'prerequisite', label: '前置' },
  { id: 'e14', source: 'recur', target: 'dp', type: 'prerequisite', label: '前置' },
  { id: 'e15', source: 'func', target: 'class', type: 'prerequisite', label: '前置' },
  { id: 'e16', source: 'dict', target: 'graph', type: 'path', label: '推荐路径' },
  { id: 'e17', source: 'loop', target: 'except', type: 'related', label: '相关' },
  { id: 'e18', source: 'func', target: 'comp', type: 'path', label: '推荐路径' },
  { id: 'e19', source: 'list', target: 'tuple', type: 'related', label: '相关' },
  { id: 'e20', source: 'sort', target: 'greedy', type: 'advanced', label: '进阶' },
]

export function getStudentNodes(masteredIds: string[] = []): KgNode[] {
  return KG_NODES.map((node) => ({
    ...node,
    status: masteredIds.includes(node.id)
      ? 'mastered'
      : node.status,
  }))
}
