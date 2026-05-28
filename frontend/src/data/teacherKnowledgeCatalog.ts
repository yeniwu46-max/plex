/** 与 backend/app/data/knowledge_catalog.py 对齐 */

export interface KnowledgePointDef {
  key: string
  label: string
}

export interface KnowledgeDomainDef {
  key: string
  label: string
  points: KnowledgePointDef[]
}

export const TEACHER_KNOWLEDGE_UNIVERSE: KnowledgeDomainDef[] = [
  {
    key: 'algo',
    label: '算法基础',
    points: [
      { key: 'algo-complexity', label: '时间复杂度' },
      { key: 'algo-greedy', label: '贪心策略' },
      { key: 'algo-dp-intro', label: '动态规划入门' },
      { key: 'algo-divide', label: '分治思想' },
    ],
  },
  {
    key: 'fe',
    label: '前端开发',
    points: [
      { key: 'fe-vue', label: 'Vue 组件化' },
      { key: 'fe-state', label: '状态管理' },
      { key: 'fe-http', label: 'HTTP 与接口' },
      { key: 'fe-css', label: '布局与样式' },
    ],
  },
  {
    key: 'be',
    label: '后端开发',
    points: [
      { key: 'be-rest', label: 'REST API' },
      { key: 'be-auth', label: '认证与权限' },
      { key: 'be-orm', label: 'ORM 与数据层' },
      { key: 'be-cache', label: '缓存策略' },
    ],
  },
  {
    key: 'cs',
    label: '计算机基础',
    points: [
      { key: 'cs-os', label: '操作系统' },
      { key: 'cs-net', label: '计算机网络' },
      { key: 'cs-memory', label: '内存与进程' },
      { key: 'cs-binary', label: '数制与编码' },
    ],
  },
  {
    key: 'db',
    label: '数据库',
    points: [
      { key: 'db-sql', label: 'SQL 查询' },
      { key: 'db-index', label: '索引优化' },
      { key: 'db-trans', label: '事务 ACID' },
      { key: 'db-design', label: '表结构设计' },
    ],
  },
  {
    key: 'ds',
    label: '数据结构',
    points: [
      { key: 'ds-array', label: '数组与链表' },
      { key: 'ds-stack', label: '栈与队列' },
      { key: 'ds-tree', label: '树与二叉树' },
      { key: 'ds-graph', label: '图的表示' },
    ],
  },
]

export function labelForKnowledgeKey(key: string): string {
  for (const domain of TEACHER_KNOWLEDGE_UNIVERSE) {
    const point = domain.points.find((p) => p.key === key)
    if (point) return point.label
    if (domain.key === key) return domain.label
  }
  return key
}
