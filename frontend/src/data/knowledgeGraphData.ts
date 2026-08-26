/** 本文件由 backend/scripts/knowledge_rebuild/gen_frontend.py 生成，请勿手改。 */
/** 静态拓扑，与 backend/app/data/kg_topology.py 对齐，接口失败时作轻量回退。 */

export type KgNodeStatus = 'mastered' | 'learning' | 'weak' | 'unlearned' | 'recommended'

export interface KgNode {
  id: string
  label: string
  domain: string
  status: KgNodeStatus
  description: string
  level: 'basic' | 'intermediate' | 'advanced'
  answered_count?: number
  correct_count?: number
  wrong_count?: number
  accuracy?: number | null
  fail_count?: number
  weak_score?: number
  affected_student_count?: number
  student_count?: number
  weak_count?: number
  not_mastered_percent?: number
  top_error_types?: Array<{ error_type: string; count: number }>
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
  { id: "lang-print", label: "print 输出与注释", domain: "语言入门", status: 'unlearned', level: "basic", description: "用 print 输出信息，用注释解释代码", x: 90, y: 120 },
  { id: "lang-var", label: "变量与类型", domain: "语言入门", status: 'unlearned', level: "basic", description: "给数据起名字，认识整数、小数、字符串和布尔值", x: 90, y: 250 },
  { id: "lang-input", label: "输入 input", domain: "语言入门", status: 'unlearned', level: "basic", description: "用 input 读取用户输入，并处理读入时的异常", x: 90, y: 380 },
  { id: "seq-arith", label: "算术运算", domain: "顺序结构", status: 'unlearned', level: "basic", description: "加减乘除、整除、取余与幂运算", x: 290, y: 120 },
  { id: "seq-expr", label: "表达式与优先级", domain: "顺序结构", status: 'unlearned', level: "basic", description: "把多个运算组合起来，理解谁先算谁后算", x: 290, y: 250 },
  { id: "seq-type", label: "数据类型与转换", domain: "顺序结构", status: 'unlearned', level: "basic", description: "int / float / str 之间的相互转换与取整", x: 290, y: 380 },
  { id: "branch-if", label: "单分支与双分支", domain: "分支结构", status: 'unlearned', level: "basic", description: "if 与 if-else：让程序二选一", x: 490, y: 120 },
  { id: "branch-elif", label: "多分支 elif", domain: "分支结构", status: 'unlearned', level: "basic", description: "用 elif 串起三条以上的分支，如成绩等第", x: 490, y: 250 },
  { id: "branch-nested", label: "嵌套与复合条件", domain: "分支结构", status: 'unlearned', level: "intermediate", description: "分支里再套分支，以及 and / or / not 复合判断", x: 490, y: 380 },
  { id: "loop-for", label: "for 与 range", domain: "循环结构", status: 'unlearned', level: "basic", description: "用 for 配合 range 重复固定次数", x: 690, y: 120 },
  { id: "loop-while", label: "while 循环", domain: "循环结构", status: 'unlearned', level: "basic", description: "条件成立就一直做，重点是想清楚终止条件", x: 690, y: 250 },
  { id: "loop-nested", label: "嵌套循环", domain: "循环结构", status: 'unlearned', level: "intermediate", description: "双重循环打印图形、遍历组合", x: 690, y: 380 },
  { id: "loop-control", label: "break 与 continue", domain: "循环结构", status: 'unlearned', level: "intermediate", description: "提前跳出循环或跳过本轮", x: 690, y: 510 },
  { id: "array-basic", label: "列表基础", domain: "数组", status: 'unlearned', level: "basic", description: "创建列表、索引取值、切片与增删改", x: 890, y: 120 },
  { id: "array-traverse", label: "遍历与统计", domain: "数组", status: 'unlearned', level: "intermediate", description: "遍历列表求和、计数、找最值", x: 890, y: 250 },
  { id: "array-2d", label: "二维列表", domain: "数组", status: 'unlearned', level: "intermediate", description: "用嵌套列表表示表格与矩阵", x: 890, y: 380 },
  { id: "string-index", label: "索引与切片", domain: "字符串", status: 'unlearned', level: "basic", description: "按下标取字符、用切片截取子串与反转", x: 1090, y: 120 },
  { id: "string-method", label: "常用方法", domain: "字符串", status: 'unlearned', level: "intermediate", description: "split / join / replace / strip / upper 等", x: 1090, y: 250 },
  { id: "string-scan", label: "遍历与统计", domain: "字符串", status: 'unlearned', level: "intermediate", description: "逐字符遍历，统计字符出现次数与回文判断", x: 1090, y: 380 },
  { id: "func-define", label: "定义与调用", domain: "函数与递归", status: 'unlearned', level: "intermediate", description: "用 def 把一段逻辑打包，然后反复调用", x: 1290, y: 120 },
  { id: "func-param", label: "参数与返回值", domain: "函数与递归", status: 'unlearned', level: "intermediate", description: "传入参数、返回结果，理解作用域", x: 1290, y: 250 },
  { id: "func-recursion", label: "递归", domain: "函数与递归", status: 'unlearned', level: "advanced", description: "函数调用自己，关键是找到出口条件", x: 1290, y: 380 },
  { id: "search-linear", label: "顺序查找", domain: "查找与搜索", status: 'unlearned', level: "basic", description: "从头到尾逐个比对，找到目标就停", x: 1490, y: 120 },
  { id: "search-binary", label: "二分查找", domain: "查找与搜索", status: 'unlearned', level: "advanced", description: "在有序数据里每次砍掉一半", x: 1490, y: 250 },
  { id: "search-sort", label: "排序思想", domain: "查找与搜索", status: 'unlearned', level: "advanced", description: "冒泡与选择排序：交换与选最小", x: 1490, y: 380 },
  { id: "search-stat", label: "统计与去重", domain: "查找与搜索", status: 'unlearned', level: "intermediate", description: "求和、计数、找最值与去重", x: 1490, y: 510 },
]

export const KG_EDGES: KgEdge[] = [
  { id: "e1", source: "lang-print", target: "lang-var", type: "prerequisite", label: "前置" },
  { id: "e2", source: "lang-var", target: "lang-input", type: "prerequisite", label: "前置" },
  { id: "e3", source: "seq-arith", target: "seq-expr", type: "prerequisite", label: "前置" },
  { id: "e4", source: "seq-expr", target: "seq-type", type: "prerequisite", label: "前置" },
  { id: "e5", source: "branch-if", target: "branch-elif", type: "prerequisite", label: "前置" },
  { id: "e6", source: "branch-elif", target: "branch-nested", type: "prerequisite", label: "前置" },
  { id: "e7", source: "loop-for", target: "loop-while", type: "prerequisite", label: "前置" },
  { id: "e8", source: "loop-while", target: "loop-nested", type: "prerequisite", label: "前置" },
  { id: "e9", source: "loop-nested", target: "loop-control", type: "prerequisite", label: "前置" },
  { id: "e10", source: "array-basic", target: "array-traverse", type: "prerequisite", label: "前置" },
  { id: "e11", source: "array-traverse", target: "array-2d", type: "prerequisite", label: "前置" },
  { id: "e12", source: "string-index", target: "string-method", type: "prerequisite", label: "前置" },
  { id: "e13", source: "string-method", target: "string-scan", type: "prerequisite", label: "前置" },
  { id: "e14", source: "func-define", target: "func-param", type: "prerequisite", label: "前置" },
  { id: "e15", source: "func-param", target: "func-recursion", type: "prerequisite", label: "前置" },
  { id: "e16", source: "search-linear", target: "search-binary", type: "prerequisite", label: "前置" },
  { id: "e17", source: "search-binary", target: "search-sort", type: "prerequisite", label: "前置" },
  { id: "e18", source: "search-sort", target: "search-stat", type: "prerequisite", label: "前置" },
  { id: "e19", source: "lang-print", target: "seq-arith", type: "prerequisite", label: "前置" },
  { id: "e20", source: "seq-arith", target: "branch-if", type: "prerequisite", label: "前置" },
  { id: "e21", source: "branch-if", target: "loop-for", type: "prerequisite", label: "前置" },
  { id: "e22", source: "loop-for", target: "array-basic", type: "prerequisite", label: "前置" },
  { id: "e23", source: "array-basic", target: "string-index", type: "prerequisite", label: "前置" },
  { id: "e24", source: "string-index", target: "func-define", type: "prerequisite", label: "前置" },
  { id: "e25", source: "func-define", target: "search-linear", type: "prerequisite", label: "前置" },
  { id: "e26", source: "loop-for", target: "array-traverse", type: "related", label: "相关" },
  { id: "e27", source: "loop-nested", target: "array-2d", type: "related", label: "相关" },
  { id: "e28", source: "loop-for", target: "string-scan", type: "related", label: "相关" },
  { id: "e29", source: "array-basic", target: "search-linear", type: "prerequisite", label: "前置" },
  { id: "e30", source: "array-traverse", target: "search-stat", type: "prerequisite", label: "前置" },
  { id: "e31", source: "func-define", target: "func-recursion", type: "related", label: "相关" },
  { id: "e32", source: "search-linear", target: "search-binary", type: "path", label: "推荐路径" },
  { id: "e33", source: "search-sort", target: "search-binary", type: "path", label: "推荐路径" },
  { id: "e34", source: "string-method", target: "array-basic", type: "related", label: "相关" },
  { id: "e35", source: "branch-if", target: "loop-while", type: "related", label: "相关" },
]

export function getStudentNodes(masteredIds: string[] = []): KgNode[] {
  return KG_NODES.map((node) => ({
    ...node,
    status: masteredIds.includes(node.id) ? 'mastered' : node.status,
  }))
}
