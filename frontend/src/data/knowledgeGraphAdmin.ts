/** 管理端知识图谱 · 关联、题库映射与同步记录 */

export interface KnowledgeRelation {
  from: string
  to: string
  relation: '前置' | '关联' | '扩展'
}

export interface KnowledgeSyncRecord {
  time: string
  action: string
  target: string
  status: '完成' | '进行中' | '待审核'
}

export const KNOWLEDGE_POINT_BANK_MAP: Record<string, string> = {
  'algo-complexity': '算法题库',
  'algo-greedy': '算法题库',
  'algo-dp-intro': '动态规划题库',
  'algo-divide': '算法题库',
  'fe-vue': '前端题库',
  'fe-state': '前端题库',
  'fe-http': '前端题库',
  'fe-css': '前端题库',
  'be-rest': '后端题库',
  'be-auth': '后端题库',
  'be-orm': '后端题库',
  'be-cache': '后端题库',
  'cs-os': '计基题库',
  'cs-net': '计基题库',
  'cs-memory': '计基题库',
  'cs-binary': '计基题库',
  'db-sql': '数据库题库',
  'db-index': '数据库题库',
  'db-trans': '数据库题库',
  'db-design': '数据库题库',
  'ds-array': '数据结构题库',
  'ds-stack': '数据结构题库',
  'ds-tree': '数据结构题库',
  'ds-graph': '图论题库',
}

export const KNOWLEDGE_PREREQUISITE_EDGES: KnowledgeRelation[] = [
  { from: '时间复杂度', to: '贪心策略', relation: '前置' },
  { from: '分治思想', to: '动态规划入门', relation: '前置' },
  { from: '数组与链表', to: '栈与队列', relation: '前置' },
  { from: '树与二叉树', to: '图的表示', relation: '前置' },
  { from: 'SQL 查询', to: '索引优化', relation: '前置' },
  { from: 'REST API', to: '认证与权限', relation: '前置' },
  { from: 'Vue 组件化', to: '状态管理', relation: '前置' },
  { from: '变量与数据类型', to: '条件与循环', relation: '前置' },
  { from: '算法思维入门', to: '时间复杂度', relation: '前置' },
  { from: '递归与分治', to: '贪心策略', relation: '关联' },
  { from: 'DP 三要素', to: '背包问题', relation: '前置' },
  { from: '图的表示', to: 'BFS 与 DFS', relation: '前置' },
  { from: 'BFS 与 DFS', to: '最短路径', relation: '前置' },
  { from: '栈与队列', to: '二叉树遍历', relation: '关联' },
]

export const KNOWLEDGE_SYNC_LOG: KnowledgeSyncRecord[] = [
  { time: '14:32', action: '新增节点', target: '递归算法优化 → 算法基础', status: '完成' },
  { time: '14:18', action: '更新关联', target: '动态规划入门 → 背包问题', status: '完成' },
  { time: '13:55', action: '题库绑定', target: 'fe-vue → 前端题库', status: '完成' },
  { time: '13:40', action: '学域同步', target: '星轨 · 图论域 4 节点', status: '完成' },
  { time: '13:12', action: '待审核', target: 'ORM 与数据层 · 扩展题包', status: '待审核' },
  { time: '12:48', action: '索引重建', target: '知识图谱全文检索', status: '进行中' },
]
