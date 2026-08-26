/** 本文件由 backend/scripts/knowledge_rebuild/gen_frontend.py 生成，请勿手改。 */
/** 与 backend/app/data/knowledge_node_registry.py 一一对应。 */

export interface KnowledgeNodeRegistryEntry {
  kg_id: string
  label: string
  domain_key: string
  domain_title: string
  /** 重排后星轨 id 与图谱 id 统一，保留字段只为兼容旧调用 */
  star_path_id: string
  knowledge_keys: string[]
  level: string
  default_difficulty: number
  summary: string
}

export const KNOWLEDGE_NODE_REGISTRY: KnowledgeNodeRegistryEntry[] = [
  { kg_id: "lang-print", label: "print 输出与注释", domain_key: "lang-basics", domain_title: "语言入门", star_path_id: "lang-print", knowledge_keys: ["lang-print", "intro", "print", "python", "lang", "comment"], level: "basic", default_difficulty: 1, summary: "用 print 输出信息，用注释解释代码" },
  { kg_id: "lang-var", label: "变量与类型", domain_key: "lang-basics", domain_title: "语言入门", star_path_id: "lang-var", knowledge_keys: ["lang-var", "var", "syntax", "basic"], level: "basic", default_difficulty: 1, summary: "给数据起名字，认识整数、小数、字符串和布尔值" },
  { kg_id: "lang-input", label: "输入 input", domain_key: "lang-basics", domain_title: "语言入门", star_path_id: "lang-input", knowledge_keys: ["lang-input", "io", "input", "file", "except", "exception"], level: "basic", default_difficulty: 1, summary: "用 input 读取用户输入，并处理读入时的异常" },
  { kg_id: "seq-arith", label: "算术运算", domain_key: "sequence", domain_title: "顺序结构", star_path_id: "seq-arith", knowledge_keys: ["seq-arith", "ops", "arith"], level: "basic", default_difficulty: 1, summary: "加减乘除、整除、取余与幂运算" },
  { kg_id: "seq-expr", label: "表达式与优先级", domain_key: "sequence", domain_title: "顺序结构", star_path_id: "seq-expr", knowledge_keys: ["seq-expr", "expr", "operator-priority"], level: "basic", default_difficulty: 2, summary: "把多个运算组合起来，理解谁先算谁后算" },
  { kg_id: "seq-type", label: "数据类型与转换", domain_key: "sequence", domain_title: "顺序结构", star_path_id: "seq-type", knowledge_keys: ["seq-type", "datatype", "cast", "hightype"], level: "basic", default_difficulty: 2, summary: "int / float / str 之间的相互转换与取整" },
  { kg_id: "branch-if", label: "单分支与双分支", domain_key: "branch", domain_title: "分支结构", star_path_id: "branch-if", knowledge_keys: ["branch-if", "cond", "condition", "if"], level: "basic", default_difficulty: 1, summary: "if 与 if-else：让程序二选一" },
  { kg_id: "branch-elif", label: "多分支 elif", domain_key: "branch", domain_title: "分支结构", star_path_id: "branch-elif", knowledge_keys: ["branch-elif", "elif", "multi-branch"], level: "basic", default_difficulty: 2, summary: "用 elif 串起三条以上的分支，如成绩等第" },
  { kg_id: "branch-nested", label: "嵌套与复合条件", domain_key: "branch", domain_title: "分支结构", star_path_id: "branch-nested", knowledge_keys: ["branch-nested", "nested-condition", "nested_condition"], level: "intermediate", default_difficulty: 3, summary: "分支里再套分支，以及 and / or / not 复合判断" },
  { kg_id: "loop-for", label: "for 与 range", domain_key: "loop", domain_title: "循环结构", star_path_id: "loop-for", knowledge_keys: ["loop-for", "loop", "for", "range"], level: "basic", default_difficulty: 1, summary: "用 for 配合 range 重复固定次数" },
  { kg_id: "loop-while", label: "while 循环", domain_key: "loop", domain_title: "循环结构", star_path_id: "loop-while", knowledge_keys: ["loop-while", "while"], level: "basic", default_difficulty: 2, summary: "条件成立就一直做，重点是想清楚终止条件" },
  { kg_id: "loop-nested", label: "嵌套循环", domain_key: "loop", domain_title: "循环结构", star_path_id: "loop-nested", knowledge_keys: ["loop-nested", "nested", "nested_loop"], level: "intermediate", default_difficulty: 3, summary: "双重循环打印图形、遍历组合" },
  { kg_id: "loop-control", label: "break 与 continue", domain_key: "loop", domain_title: "循环结构", star_path_id: "loop-control", knowledge_keys: ["loop-control", "break", "continue"], level: "intermediate", default_difficulty: 3, summary: "提前跳出循环或跳过本轮" },
  { kg_id: "array-basic", label: "列表基础", domain_key: "array", domain_title: "数组", star_path_id: "array-basic", knowledge_keys: ["array-basic", "list", "array", "tuple", "set", "dict"], level: "basic", default_difficulty: 2, summary: "创建列表、索引取值、切片与增删改" },
  { kg_id: "array-traverse", label: "遍历与统计", domain_key: "array", domain_title: "数组", star_path_id: "array-traverse", knowledge_keys: ["array-traverse", "list-traverse"], level: "intermediate", default_difficulty: 2, summary: "遍历列表求和、计数、找最值" },
  { kg_id: "array-2d", label: "二维列表", domain_key: "array", domain_title: "数组", star_path_id: "array-2d", knowledge_keys: ["array-2d", "list-2d", "matrix"], level: "intermediate", default_difficulty: 3, summary: "用嵌套列表表示表格与矩阵" },
  { kg_id: "string-index", label: "索引与切片", domain_key: "string", domain_title: "字符串", star_path_id: "string-index", knowledge_keys: ["string-index", "str", "string"], level: "basic", default_difficulty: 2, summary: "按下标取字符、用切片截取子串与反转" },
  { kg_id: "string-method", label: "常用方法", domain_key: "string", domain_title: "字符串", star_path_id: "string-method", knowledge_keys: ["string-method", "str-method", "string_ops"], level: "intermediate", default_difficulty: 2, summary: "split / join / replace / strip / upper 等" },
  { kg_id: "string-scan", label: "遍历与统计", domain_key: "string", domain_title: "字符串", star_path_id: "string-scan", knowledge_keys: ["string-scan", "str-scan"], level: "intermediate", default_difficulty: 3, summary: "逐字符遍历，统计字符出现次数与回文判断" },
  { kg_id: "func-define", label: "定义与调用", domain_key: "function", domain_title: "函数与递归", star_path_id: "func-define", knowledge_keys: ["func-define", "func", "function", "def"], level: "intermediate", default_difficulty: 2, summary: "用 def 把一段逻辑打包，然后反复调用" },
  { kg_id: "func-param", label: "参数与返回值", domain_key: "function", domain_title: "函数与递归", star_path_id: "func-param", knowledge_keys: ["func-param", "parameter", "return"], level: "intermediate", default_difficulty: 3, summary: "传入参数、返回结果，理解作用域" },
  { kg_id: "func-recursion", label: "递归", domain_key: "function", domain_title: "函数与递归", star_path_id: "func-recursion", knowledge_keys: ["func-recursion", "recursion"], level: "advanced", default_difficulty: 4, summary: "函数调用自己，关键是找到出口条件" },
  { kg_id: "search-linear", label: "顺序查找", domain_key: "search", domain_title: "查找与搜索", star_path_id: "search-linear", knowledge_keys: ["search-linear", "algo-search", "search"], level: "basic", default_difficulty: 2, summary: "从头到尾逐个比对，找到目标就停" },
  { kg_id: "search-binary", label: "二分查找", domain_key: "search", domain_title: "查找与搜索", star_path_id: "search-binary", knowledge_keys: ["search-binary", "algo-binary", "binary-search"], level: "advanced", default_difficulty: 4, summary: "在有序数据里每次砍掉一半" },
  { kg_id: "search-sort", label: "排序思想", domain_key: "search", domain_title: "查找与搜索", star_path_id: "search-sort", knowledge_keys: ["search-sort", "algo-sort", "sort", "algo-bubble", "algo-selection"], level: "advanced", default_difficulty: 4, summary: "冒泡与选择排序：交换与选最小" },
  { kg_id: "search-stat", label: "统计与去重", domain_key: "search", domain_title: "查找与搜索", star_path_id: "search-stat", knowledge_keys: ["search-stat", "algo-sum", "algo", "sum", "count", "algo-dedup", "dedup"], level: "intermediate", default_difficulty: 3, summary: "求和、计数、找最值与去重" },
]

const BY_ID = new Map(KNOWLEDGE_NODE_REGISTRY.map((e) => [e.kg_id, e]))

const BY_LEGACY_KEY = new Map<string, KnowledgeNodeRegistryEntry>()
for (const entry of KNOWLEDGE_NODE_REGISTRY) {
  for (const key of entry.knowledge_keys) {
    if (!BY_LEGACY_KEY.has(key)) BY_LEGACY_KEY.set(key, entry)
  }
}

export function getKnowledgeNode(kgId: string): KnowledgeNodeRegistryEntry | undefined {
  return BY_ID.get(kgId)
}

/** 把历史 knowledge_key（intro / loop / algo-sum …）解析成新节点 id。 */
export function kgIdFromKey(key: string | null | undefined): string | undefined {
  if (!key) return undefined
  return BY_ID.get(key)?.kg_id ?? BY_LEGACY_KEY.get(key.toLowerCase())?.kg_id
}

/** 星轨 id 与图谱 id 已统一，保留以兼容旧调用。 */
export function kgIdFromStarPath(starPathId: string): string | undefined {
  return BY_ID.get(starPathId)?.kg_id
}

export function starPathIdFromKg(kgId: string): string | undefined {
  return BY_ID.get(kgId)?.kg_id
}
