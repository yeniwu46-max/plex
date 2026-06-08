/** 管理端知识图谱 · Python 初学者关联、题库映射与同步记录 */

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
  intro: 'Python 入门题库',
  comment: 'Python 入门题库',
  var: '变量与类型题库',
  io: '输入输出题库',
  ops: '表达式题库',
  cond: '条件分支题库',
  loop: '循环结构题库',
  range: '循环结构题库',
  list: '列表题库',
  dict: '字典题库',
  str: '字符串题库',
  func: '函数题库',
  file: '文件异常题库',
  except: '文件异常题库',
  'algo-sum': '算法入门题库',
  'algo-search': '算法入门题库',
}

export const KNOWLEDGE_PREREQUISITE_EDGES: KnowledgeRelation[] = [
  { from: 'Python 与 print', to: '变量与类型', relation: '前置' },
  { from: '变量与类型', to: '输入 input', relation: '前置' },
  { from: '运算与表达式', to: 'if 分支', relation: '前置' },
  { from: 'if 分支', to: '循环结构', relation: '前置' },
  { from: '循环结构', to: '列表 list', relation: '前置' },
  { from: '列表 list', to: '字典 dict', relation: '前置' },
  { from: '字符串处理', to: '函数基础', relation: '前置' },
  { from: '函数基础', to: '文件读写', relation: '前置' },
  { from: '循环结构', to: '求和与统计', relation: '前置' },
  { from: '列表 list', to: '线性查找', relation: '前置' },
]

export const KNOWLEDGE_SYNC_LOG: KnowledgeSyncRecord[] = [
  { time: '14:32', action: '节点更新', target: 'Python 入门 → 变量与类型', status: '完成' },
  { time: '14:18', action: '更新关联', target: '循环结构 → 求和与统计', status: '完成' },
  { time: '13:55', action: '题库绑定', target: 'list → 列表题库', status: '完成' },
  { time: '13:40', action: '学域同步', target: '星轨 · 条件与循环 4 节点', status: '完成' },
  { time: '13:12', action: '待审核', target: '线性查找 · 扩展题包', status: '待审核' },
  { time: '12:48', action: '索引重建', target: '知识图谱全文检索', status: '进行中' },
]
