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
    key: 'stage1',
    label: '会写第一段 Python',
    points: [
      { key: 'intro', label: 'Python 与 print' },
      { key: 'comment', label: '注释' },
      { key: 'var', label: '变量与类型' },
      { key: 'io', label: '输入 input' },
    ],
  },
  {
    key: 'stage2',
    label: '条件与循环',
    points: [
      { key: 'ops', label: '运算与表达式' },
      { key: 'cond', label: 'if 分支' },
      { key: 'loop', label: '循环结构' },
      { key: 'range', label: 'range / break / continue' },
    ],
  },
  {
    key: 'stage3',
    label: '容器、字符串与函数',
    points: [
      { key: 'list', label: '列表 list' },
      { key: 'dict', label: '字典 dict' },
      { key: 'str', label: '字符串处理' },
      { key: 'func', label: '函数基础' },
    ],
  },
  {
    key: 'stage4',
    label: '简单算法小任务',
    points: [
      { key: 'file', label: '文件读写' },
      { key: 'except', label: '异常处理' },
      { key: 'algo-sum', label: '求和与统计' },
      { key: 'algo-search', label: '线性查找' },
    ],
  },
]

export function labelForKnowledgeKey(key: string): string {
  for (const domain of TEACHER_KNOWLEDGE_UNIVERSE) {
    const point = domain.points.find((p) => p.key === key)
    if (point) return point.label
  }
  return key
}
