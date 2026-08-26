/** 本文件由 backend/scripts/knowledge_rebuild/gen_frontend.py 生成，请勿手改。 */
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
    key: "lang-basics",
    label: "语言入门",
    points: [
      { key: "lang-print", label: "print 输出与注释" },
      { key: "lang-var", label: "变量与类型" },
      { key: "lang-input", label: "输入 input" },
    ],
  },
  {
    key: "sequence",
    label: "顺序结构",
    points: [
      { key: "seq-arith", label: "算术运算" },
      { key: "seq-expr", label: "表达式与优先级" },
      { key: "seq-type", label: "数据类型与转换" },
    ],
  },
  {
    key: "branch",
    label: "分支结构",
    points: [
      { key: "branch-if", label: "单分支与双分支" },
      { key: "branch-elif", label: "多分支 elif" },
      { key: "branch-nested", label: "嵌套与复合条件" },
    ],
  },
  {
    key: "loop",
    label: "循环结构",
    points: [
      { key: "loop-for", label: "for 与 range" },
      { key: "loop-while", label: "while 循环" },
      { key: "loop-nested", label: "嵌套循环" },
      { key: "loop-control", label: "break 与 continue" },
    ],
  },
  {
    key: "array",
    label: "数组",
    points: [
      { key: "array-basic", label: "列表基础" },
      { key: "array-traverse", label: "遍历与统计" },
      { key: "array-2d", label: "二维列表" },
    ],
  },
  {
    key: "string",
    label: "字符串",
    points: [
      { key: "string-index", label: "索引与切片" },
      { key: "string-method", label: "常用方法" },
      { key: "string-scan", label: "遍历与统计" },
    ],
  },
  {
    key: "function",
    label: "函数与递归",
    points: [
      { key: "func-define", label: "定义与调用" },
      { key: "func-param", label: "参数与返回值" },
      { key: "func-recursion", label: "递归" },
    ],
  },
  {
    key: "search",
    label: "查找与搜索",
    points: [
      { key: "search-linear", label: "顺序查找" },
      { key: "search-binary", label: "二分查找" },
      { key: "search-sort", label: "排序思想" },
      { key: "search-stat", label: "统计与去重" },
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
