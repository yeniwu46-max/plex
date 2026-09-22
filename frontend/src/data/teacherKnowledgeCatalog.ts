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
      { key: "lang-identifier", label: "标识符与命名" },
      { key: "lang-number", label: "数值字面量" },
      { key: "lang-bool", label: "布尔值与 None" },
      { key: "lang-literal-string", label: "字符串字面量" },
      { key: "lang-format", label: "格式化输出" },
      { key: "lang-docstring", label: "注释与文档字符串" },
      { key: "lang-debug", label: "基础调试方法" },
      { key: "lang-errors", label: "错误信息阅读" },
      { key: "lang-style", label: "PEP 8 编码规范" },
    ],
  },
  {
    key: "sequence",
    label: "顺序结构",
    points: [
      { key: "seq-arith", label: "算术运算" },
      { key: "seq-expr", label: "表达式与优先级" },
      { key: "seq-type", label: "数据类型与转换" },
      { key: "seq-assignment", label: "赋值语句" },
      { key: "seq-augmented", label: "复合赋值" },
      { key: "seq-compare", label: "比较运算" },
      { key: "seq-logic", label: "逻辑运算" },
      { key: "seq-rounding", label: "精度与舍入" },
      { key: "seq-math", label: "math 数学函数" },
      { key: "seq-random", label: "随机数基础" },
      { key: "seq-datetime", label: "日期时间基础" },
      { key: "seq-pipeline", label: "输入—处理—输出" },
    ],
  },
  {
    key: "branch",
    label: "分支结构",
    points: [
      { key: "branch-if", label: "单分支与双分支" },
      { key: "branch-elif", label: "多分支 elif" },
      { key: "branch-nested", label: "嵌套与复合条件" },
      { key: "branch-truthy", label: "真值判断" },
      { key: "branch-chain", label: "链式比较" },
      { key: "branch-membership", label: "成员与身份判断" },
      { key: "branch-ternary", label: "条件表达式" },
      { key: "branch-guard", label: "卫语句" },
      { key: "branch-validation", label: "输入校验分支" },
      { key: "branch-state", label: "状态决策" },
      { key: "branch-match", label: "模式匹配 match" },
      { key: "branch-test-design", label: "分支测试设计" },
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
      { key: "loop-range-detail", label: "range 参数与边界" },
      { key: "loop-enumerate", label: "enumerate 遍历" },
      { key: "loop-zip", label: "zip 并行遍历" },
      { key: "loop-accumulator", label: "累加器模式" },
      { key: "loop-counter", label: "计数器模式" },
      { key: "loop-sentinel", label: "哨兵循环" },
      { key: "loop-else", label: "循环 else" },
      { key: "loop-comprehension", label: "列表推导式" },
      { key: "loop-complexity", label: "循环复杂度直觉" },
    ],
  },
  {
    key: "array",
    label: "数组",
    points: [
      { key: "array-basic", label: "列表基础" },
      { key: "array-traverse", label: "遍历与统计" },
      { key: "array-2d", label: "二维列表" },
      { key: "array-slice", label: "列表切片" },
      { key: "array-methods", label: "列表常用方法" },
      { key: "array-copy", label: "浅拷贝与别名" },
      { key: "array-tuple", label: "元组与解包" },
      { key: "array-set", label: "集合运算" },
      { key: "array-dict", label: "字典基础" },
      { key: "array-stack", label: "列表实现栈" },
      { key: "array-queue", label: "队列与 deque" },
      { key: "array-sort-key", label: "按键排序" },
      { key: "array-comprehension", label: "容器推导式" },
    ],
  },
  {
    key: "string",
    label: "字符串",
    points: [
      { key: "string-index", label: "索引与切片" },
      { key: "string-method", label: "常用方法" },
      { key: "string-scan", label: "遍历与统计" },
      { key: "string-immutable", label: "字符串不可变性" },
      { key: "string-format", label: "字符串格式化" },
      { key: "string-split-join", label: "拆分与拼接" },
      { key: "string-search", label: "子串查找" },
      { key: "string-validate", label: "字符分类校验" },
      { key: "string-encoding", label: "字符编码" },
      { key: "string-regex", label: "正则表达式入门" },
      { key: "string-frequency", label: "字符频次统计" },
      { key: "string-palindrome", label: "回文与规范化" },
      { key: "string-file-text", label: "文本文件处理" },
    ],
  },
  {
    key: "function",
    label: "函数与递归",
    points: [
      { key: "func-define", label: "定义与调用" },
      { key: "func-param", label: "参数与返回值" },
      { key: "func-recursion", label: "递归" },
      { key: "func-scope", label: "作用域与生命周期" },
      { key: "func-default", label: "默认参数" },
      { key: "func-keyword", label: "关键字参数" },
      { key: "func-varargs", label: "可变参数" },
      { key: "func-lambda", label: "lambda 表达式" },
      { key: "func-higher-order", label: "高阶函数" },
      { key: "func-contract", label: "函数契约与文档" },
      { key: "func-unit-test", label: "函数单元测试" },
      { key: "func-pure", label: "纯函数与副作用" },
      { key: "func-memoization", label: "递归记忆化" },
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
      { key: "search-complexity", label: "时间复杂度" },
      { key: "search-boundary", label: "二分边界模板" },
      { key: "search-bubble", label: "冒泡排序" },
      { key: "search-selection", label: "选择排序" },
      { key: "search-insertion", label: "插入排序" },
      { key: "search-hash", label: "哈希查找" },
      { key: "search-two-pointer", label: "双指针搜索" },
      { key: "search-bfs", label: "广度优先搜索入门" },
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
