/** 与 backend/app/data/knowledge_node_registry.py 对齐（星轨 id ↔ 图谱 kg_id） */
export interface KnowledgeNodeRegistryEntry {
  kg_id: string
  label: string
  domain_key: string
  star_path_id: string | null
  knowledge_keys: string[]
  level: string
  default_difficulty: number
}

export const KNOWLEDGE_NODE_REGISTRY: KnowledgeNodeRegistryEntry[] = [
  { kg_id: 'intro', label: 'Python 入门', domain_key: 'stage1', star_path_id: 'stage1-intro', knowledge_keys: ['intro', 'print'], level: 'basic', default_difficulty: 1 },
  { kg_id: 'comment', label: '注释', domain_key: 'stage1', star_path_id: 'stage1-comment', knowledge_keys: ['comment'], level: 'basic', default_difficulty: 1 },
  { kg_id: 'var', label: '变量与类型', domain_key: 'stage1', star_path_id: 'stage1-var', knowledge_keys: ['var'], level: 'basic', default_difficulty: 1 },
  { kg_id: 'io', label: '输入 input', domain_key: 'stage1', star_path_id: 'stage1-io', knowledge_keys: ['io', 'input'], level: 'basic', default_difficulty: 1 },
  { kg_id: 'ops', label: '运算与表达式', domain_key: 'stage2', star_path_id: 'stage2-ops', knowledge_keys: ['ops'], level: 'basic', default_difficulty: 1 },
  { kg_id: 'cond', label: '条件分支', domain_key: 'stage2', star_path_id: 'stage2-cond', knowledge_keys: ['cond'], level: 'basic', default_difficulty: 1 },
  { kg_id: 'loop', label: '循环结构', domain_key: 'stage2', star_path_id: 'stage2-loop', knowledge_keys: ['loop'], level: 'basic', default_difficulty: 1 },
  { kg_id: 'range', label: 'range 与控制', domain_key: 'stage2', star_path_id: 'stage2-range', knowledge_keys: ['range'], level: 'basic', default_difficulty: 2 },
  { kg_id: 'list', label: '列表 list', domain_key: 'stage3', star_path_id: 'stage3-list', knowledge_keys: ['list'], level: 'basic', default_difficulty: 1 },
  { kg_id: 'dict', label: '字典 dict', domain_key: 'stage3', star_path_id: 'stage3-dict', knowledge_keys: ['dict'], level: 'intermediate', default_difficulty: 2 },
  { kg_id: 'str', label: '字符串处理', domain_key: 'stage3', star_path_id: 'stage3-str', knowledge_keys: ['str', 'string'], level: 'basic', default_difficulty: 1 },
  { kg_id: 'func', label: '函数基础', domain_key: 'stage3', star_path_id: 'stage3-func', knowledge_keys: ['func', 'function'], level: 'intermediate', default_difficulty: 2 },
  { kg_id: 'file', label: '文件读写', domain_key: 'stage4', star_path_id: 'stage4-file', knowledge_keys: ['file'], level: 'intermediate', default_difficulty: 2 },
  { kg_id: 'except', label: '异常处理', domain_key: 'stage4', star_path_id: 'stage4-except', knowledge_keys: ['except', 'exception'], level: 'intermediate', default_difficulty: 2 },
  { kg_id: 'algo-sum', label: '求和与统计', domain_key: 'stage4', star_path_id: 'stage4-algo-sum', knowledge_keys: ['algo-sum', 'algo'], level: 'basic', default_difficulty: 1 },
  { kg_id: 'algo-search', label: '线性查找', domain_key: 'stage4', star_path_id: 'stage4-algo-search', knowledge_keys: ['algo-search'], level: 'basic', default_difficulty: 1 },
]

export function kgIdFromStarPath(starPathId: string): string | null {
  const entry = KNOWLEDGE_NODE_REGISTRY.find((e) => e.star_path_id === starPathId)
  return entry?.kg_id ?? null
}

export function starPathIdFromKg(kgId: string): string | null {
  const entry = KNOWLEDGE_NODE_REGISTRY.find((e) => e.kg_id === kgId)
  return entry?.star_path_id ?? null
}
