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
  { kg_id: "lang-identifier", label: "标识符与命名", domain_key: "lang-basics", domain_title: "语言入门", star_path_id: "lang-identifier", knowledge_keys: ["lang-identifier"], level: "basic", default_difficulty: 1, summary: "掌握变量名规则、关键字与可读命名" },
  { kg_id: "lang-number", label: "数值字面量", domain_key: "lang-basics", domain_title: "语言入门", star_path_id: "lang-number", knowledge_keys: ["lang-number"], level: "basic", default_difficulty: 1, summary: "认识整数、浮点数、科学计数法与进制表示" },
  { kg_id: "lang-bool", label: "布尔值与 None", domain_key: "lang-basics", domain_title: "语言入门", star_path_id: "lang-bool", knowledge_keys: ["lang-bool"], level: "basic", default_difficulty: 1, summary: "理解 True、False、None 及其基本用途" },
  { kg_id: "lang-literal-string", label: "字符串字面量", domain_key: "lang-basics", domain_title: "语言入门", star_path_id: "lang-literal-string", knowledge_keys: ["lang-literal-string"], level: "basic", default_difficulty: 1, summary: "掌握引号、转义字符与多行字符串" },
  { kg_id: "lang-format", label: "格式化输出", domain_key: "lang-basics", domain_title: "语言入门", star_path_id: "lang-format", knowledge_keys: ["lang-format"], level: "basic", default_difficulty: 2, summary: "使用 f-string 控制文本、数值精度与对齐" },
  { kg_id: "lang-docstring", label: "注释与文档字符串", domain_key: "lang-basics", domain_title: "语言入门", star_path_id: "lang-docstring", knowledge_keys: ["lang-docstring"], level: "basic", default_difficulty: 1, summary: "用注释和 docstring 解释程序意图" },
  { kg_id: "lang-debug", label: "基础调试方法", domain_key: "lang-basics", domain_title: "语言入门", star_path_id: "lang-debug", knowledge_keys: ["lang-debug"], level: "intermediate", default_difficulty: 2, summary: "通过打印、断点和最小复现定位错误" },
  { kg_id: "lang-errors", label: "错误信息阅读", domain_key: "lang-basics", domain_title: "语言入门", star_path_id: "lang-errors", knowledge_keys: ["lang-errors"], level: "intermediate", default_difficulty: 2, summary: "识别语法错误、类型错误和名称错误" },
  { kg_id: "lang-style", label: "PEP 8 编码规范", domain_key: "lang-basics", domain_title: "语言入门", star_path_id: "lang-style", knowledge_keys: ["lang-style"], level: "intermediate", default_difficulty: 2, summary: "形成缩进、空格、命名与代码布局规范" },
  { kg_id: "seq-assignment", label: "赋值语句", domain_key: "sequence", domain_title: "顺序结构", star_path_id: "seq-assignment", knowledge_keys: ["seq-assignment"], level: "basic", default_difficulty: 1, summary: "理解赋值方向、多重赋值与交换变量" },
  { kg_id: "seq-augmented", label: "复合赋值", domain_key: "sequence", domain_title: "顺序结构", star_path_id: "seq-augmented", knowledge_keys: ["seq-augmented"], level: "basic", default_difficulty: 1, summary: "使用 +=、-=、*= 等更新变量状态" },
  { kg_id: "seq-compare", label: "比较运算", domain_key: "sequence", domain_title: "顺序结构", star_path_id: "seq-compare", knowledge_keys: ["seq-compare"], level: "basic", default_difficulty: 1, summary: "比较数值与文本并得到布尔结果" },
  { kg_id: "seq-logic", label: "逻辑运算", domain_key: "sequence", domain_title: "顺序结构", star_path_id: "seq-logic", knowledge_keys: ["seq-logic"], level: "basic", default_difficulty: 2, summary: "组合 and、or、not 并理解短路求值" },
  { kg_id: "seq-rounding", label: "精度与舍入", domain_key: "sequence", domain_title: "顺序结构", star_path_id: "seq-rounding", knowledge_keys: ["seq-rounding"], level: "intermediate", default_difficulty: 2, summary: "理解浮点误差、round 与格式化精度" },
  { kg_id: "seq-math", label: "math 数学函数", domain_key: "sequence", domain_title: "顺序结构", star_path_id: "seq-math", knowledge_keys: ["seq-math"], level: "intermediate", default_difficulty: 2, summary: "调用常量、开方、三角与取整函数" },
  { kg_id: "seq-random", label: "随机数基础", domain_key: "sequence", domain_title: "顺序结构", star_path_id: "seq-random", knowledge_keys: ["seq-random"], level: "intermediate", default_difficulty: 2, summary: "生成可复现随机数并理解随机种子" },
  { kg_id: "seq-datetime", label: "日期时间基础", domain_key: "sequence", domain_title: "顺序结构", star_path_id: "seq-datetime", knowledge_keys: ["seq-datetime"], level: "intermediate", default_difficulty: 3, summary: "表示时间、计算时间差并格式化日期" },
  { kg_id: "seq-pipeline", label: "输入—处理—输出", domain_key: "sequence", domain_title: "顺序结构", star_path_id: "seq-pipeline", knowledge_keys: ["seq-pipeline"], level: "intermediate", default_difficulty: 2, summary: "把输入、计算、校验和输出组织成顺序流程" },
  { kg_id: "branch-truthy", label: "真值判断", domain_key: "branch", domain_title: "分支结构", star_path_id: "branch-truthy", knowledge_keys: ["branch-truthy"], level: "basic", default_difficulty: 2, summary: "理解空值、零值和容器的真假规则" },
  { kg_id: "branch-chain", label: "链式比较", domain_key: "branch", domain_title: "分支结构", star_path_id: "branch-chain", knowledge_keys: ["branch-chain"], level: "basic", default_difficulty: 2, summary: "用链式比较清晰表达数值区间" },
  { kg_id: "branch-membership", label: "成员与身份判断", domain_key: "branch", domain_title: "分支结构", star_path_id: "branch-membership", knowledge_keys: ["branch-membership"], level: "intermediate", default_difficulty: 2, summary: "正确使用 in、not in、is 与 ==" },
  { kg_id: "branch-ternary", label: "条件表达式", domain_key: "branch", domain_title: "分支结构", star_path_id: "branch-ternary", knowledge_keys: ["branch-ternary"], level: "intermediate", default_difficulty: 2, summary: "用条件表达式完成简单二选一赋值" },
  { kg_id: "branch-guard", label: "卫语句", domain_key: "branch", domain_title: "分支结构", star_path_id: "branch-guard", knowledge_keys: ["branch-guard"], level: "intermediate", default_difficulty: 3, summary: "通过提前返回减少分支嵌套" },
  { kg_id: "branch-validation", label: "输入校验分支", domain_key: "branch", domain_title: "分支结构", star_path_id: "branch-validation", knowledge_keys: ["branch-validation"], level: "intermediate", default_difficulty: 3, summary: "为范围、格式和缺失值设计校验逻辑" },
  { kg_id: "branch-state", label: "状态决策", domain_key: "branch", domain_title: "分支结构", star_path_id: "branch-state", knowledge_keys: ["branch-state"], level: "intermediate", default_difficulty: 3, summary: "根据离散状态组织互斥业务规则" },
  { kg_id: "branch-match", label: "模式匹配 match", domain_key: "branch", domain_title: "分支结构", star_path_id: "branch-match", knowledge_keys: ["branch-match"], level: "advanced", default_difficulty: 4, summary: "使用 match-case 表达结构化多分支" },
  { kg_id: "branch-test-design", label: "分支测试设计", domain_key: "branch", domain_title: "分支结构", star_path_id: "branch-test-design", knowledge_keys: ["branch-test-design"], level: "advanced", default_difficulty: 4, summary: "为每条分支设计边界与反例测试" },
  { kg_id: "loop-range-detail", label: "range 参数与边界", domain_key: "loop", domain_title: "循环结构", star_path_id: "loop-range-detail", knowledge_keys: ["loop-range-detail"], level: "basic", default_difficulty: 2, summary: "掌握起点、终点、步长和反向区间" },
  { kg_id: "loop-enumerate", label: "enumerate 遍历", domain_key: "loop", domain_title: "循环结构", star_path_id: "loop-enumerate", knowledge_keys: ["loop-enumerate"], level: "intermediate", default_difficulty: 2, summary: "同时获取序列下标与元素" },
  { kg_id: "loop-zip", label: "zip 并行遍历", domain_key: "loop", domain_title: "循环结构", star_path_id: "loop-zip", knowledge_keys: ["loop-zip"], level: "intermediate", default_difficulty: 2, summary: "同步遍历多个序列并处理长度差异" },
  { kg_id: "loop-accumulator", label: "累加器模式", domain_key: "loop", domain_title: "循环结构", star_path_id: "loop-accumulator", knowledge_keys: ["loop-accumulator"], level: "basic", default_difficulty: 2, summary: "用循环完成求和、连乘与状态聚合" },
  { kg_id: "loop-counter", label: "计数器模式", domain_key: "loop", domain_title: "循环结构", star_path_id: "loop-counter", knowledge_keys: ["loop-counter"], level: "basic", default_difficulty: 2, summary: "按条件累计次数并避免重复计数" },
  { kg_id: "loop-sentinel", label: "哨兵循环", domain_key: "loop", domain_title: "循环结构", star_path_id: "loop-sentinel", knowledge_keys: ["loop-sentinel"], level: "intermediate", default_difficulty: 3, summary: "用特殊输入或状态控制未知次数循环" },
  { kg_id: "loop-else", label: "循环 else", domain_key: "loop", domain_title: "循环结构", star_path_id: "loop-else", knowledge_keys: ["loop-else"], level: "advanced", default_difficulty: 3, summary: "理解自然结束与 break 退出的差异" },
  { kg_id: "loop-comprehension", label: "列表推导式", domain_key: "loop", domain_title: "循环结构", star_path_id: "loop-comprehension", knowledge_keys: ["loop-comprehension"], level: "intermediate", default_difficulty: 3, summary: "把映射和筛选循环写成清晰推导式" },
  { kg_id: "loop-complexity", label: "循环复杂度直觉", domain_key: "loop", domain_title: "循环结构", star_path_id: "loop-complexity", knowledge_keys: ["loop-complexity"], level: "advanced", default_difficulty: 4, summary: "根据嵌套层数估算运行次数" },
  { kg_id: "array-slice", label: "列表切片", domain_key: "array", domain_title: "数组", star_path_id: "array-slice", knowledge_keys: ["array-slice"], level: "basic", default_difficulty: 2, summary: "使用切片复制、截取、步进和反转列表" },
  { kg_id: "array-methods", label: "列表常用方法", domain_key: "array", domain_title: "数组", star_path_id: "array-methods", knowledge_keys: ["array-methods"], level: "basic", default_difficulty: 2, summary: "掌握 append、extend、insert、pop 与 remove" },
  { kg_id: "array-copy", label: "浅拷贝与别名", domain_key: "array", domain_title: "数组", star_path_id: "array-copy", knowledge_keys: ["array-copy"], level: "intermediate", default_difficulty: 3, summary: "区分同一对象、浅拷贝与嵌套可变对象" },
  { kg_id: "array-tuple", label: "元组与解包", domain_key: "array", domain_title: "数组", star_path_id: "array-tuple", knowledge_keys: ["array-tuple"], level: "basic", default_difficulty: 2, summary: "使用不可变序列和结构化解包" },
  { kg_id: "array-set", label: "集合运算", domain_key: "array", domain_title: "数组", star_path_id: "array-set", knowledge_keys: ["array-set"], level: "intermediate", default_difficulty: 2, summary: "完成去重、交并差与成员测试" },
  { kg_id: "array-dict", label: "字典基础", domain_key: "array", domain_title: "数组", star_path_id: "array-dict", knowledge_keys: ["array-dict"], level: "intermediate", default_difficulty: 3, summary: "用键值映射完成查找、更新与遍历" },
  { kg_id: "array-stack", label: "列表实现栈", domain_key: "array", domain_title: "数组", star_path_id: "array-stack", knowledge_keys: ["array-stack"], level: "intermediate", default_difficulty: 3, summary: "用后进先出结构处理撤销与括号问题" },
  { kg_id: "array-queue", label: "队列与 deque", domain_key: "array", domain_title: "数组", star_path_id: "array-queue", knowledge_keys: ["array-queue"], level: "intermediate", default_difficulty: 3, summary: "用先进先出结构组织待处理任务" },
  { kg_id: "array-sort-key", label: "按键排序", domain_key: "array", domain_title: "数组", star_path_id: "array-sort-key", knowledge_keys: ["array-sort-key"], level: "intermediate", default_difficulty: 3, summary: "使用 sort、sorted、key 与 reverse" },
  { kg_id: "array-comprehension", label: "容器推导式", domain_key: "array", domain_title: "数组", star_path_id: "array-comprehension", knowledge_keys: ["array-comprehension"], level: "advanced", default_difficulty: 4, summary: "生成列表、集合和字典并添加筛选条件" },
  { kg_id: "string-immutable", label: "字符串不可变性", domain_key: "string", domain_title: "字符串", star_path_id: "string-immutable", knowledge_keys: ["string-immutable"], level: "basic", default_difficulty: 2, summary: "理解修改字符串实际会创建新对象" },
  { kg_id: "string-format", label: "字符串格式化", domain_key: "string", domain_title: "字符串", star_path_id: "string-format", knowledge_keys: ["string-format"], level: "basic", default_difficulty: 2, summary: "使用 f-string 表达式、宽度、精度与填充" },
  { kg_id: "string-split-join", label: "拆分与拼接", domain_key: "string", domain_title: "字符串", star_path_id: "string-split-join", knowledge_keys: ["string-split-join"], level: "basic", default_difficulty: 2, summary: "用 split 和 join 处理结构化文本" },
  { kg_id: "string-search", label: "子串查找", domain_key: "string", domain_title: "字符串", star_path_id: "string-search", knowledge_keys: ["string-search"], level: "intermediate", default_difficulty: 2, summary: "使用 find、index、in 与 startswith" },
  { kg_id: "string-validate", label: "字符分类校验", domain_key: "string", domain_title: "字符串", star_path_id: "string-validate", knowledge_keys: ["string-validate"], level: "intermediate", default_difficulty: 2, summary: "用 isdigit、isalpha 等检查输入格式" },
  { kg_id: "string-encoding", label: "字符编码", domain_key: "string", domain_title: "字符串", star_path_id: "string-encoding", knowledge_keys: ["string-encoding"], level: "intermediate", default_difficulty: 3, summary: "理解 Unicode、UTF-8、编码与解码" },
  { kg_id: "string-regex", label: "正则表达式入门", domain_key: "string", domain_title: "字符串", star_path_id: "string-regex", knowledge_keys: ["string-regex"], level: "advanced", default_difficulty: 4, summary: "用模式完成文本匹配、提取与替换" },
  { kg_id: "string-frequency", label: "字符频次统计", domain_key: "string", domain_title: "字符串", star_path_id: "string-frequency", knowledge_keys: ["string-frequency"], level: "intermediate", default_difficulty: 3, summary: "结合字典统计词频和字符频率" },
  { kg_id: "string-palindrome", label: "回文与规范化", domain_key: "string", domain_title: "字符串", star_path_id: "string-palindrome", knowledge_keys: ["string-palindrome"], level: "intermediate", default_difficulty: 3, summary: "在忽略空格和大小写后判断回文" },
  { kg_id: "string-file-text", label: "文本文件处理", domain_key: "string", domain_title: "字符串", star_path_id: "string-file-text", knowledge_keys: ["string-file-text"], level: "advanced", default_difficulty: 4, summary: "安全读写文本并逐行清洗数据" },
  { kg_id: "func-scope", label: "作用域与生命周期", domain_key: "function", domain_title: "函数与递归", star_path_id: "func-scope", knowledge_keys: ["func-scope"], level: "intermediate", default_difficulty: 3, summary: "理解局部、全局、nonlocal 与名称查找" },
  { kg_id: "func-default", label: "默认参数", domain_key: "function", domain_title: "函数与递归", star_path_id: "func-default", knowledge_keys: ["func-default"], level: "intermediate", default_difficulty: 3, summary: "设计默认值并规避可变默认参数陷阱" },
  { kg_id: "func-keyword", label: "关键字参数", domain_key: "function", domain_title: "函数与递归", star_path_id: "func-keyword", knowledge_keys: ["func-keyword"], level: "intermediate", default_difficulty: 2, summary: "用参数名提升函数调用可读性" },
  { kg_id: "func-varargs", label: "可变参数", domain_key: "function", domain_title: "函数与递归", star_path_id: "func-varargs", knowledge_keys: ["func-varargs"], level: "advanced", default_difficulty: 4, summary: "使用 *args 与 **kwargs 接收不定参数" },
  { kg_id: "func-lambda", label: "lambda 表达式", domain_key: "function", domain_title: "函数与递归", star_path_id: "func-lambda", knowledge_keys: ["func-lambda"], level: "intermediate", default_difficulty: 3, summary: "为排序与映射编写短小匿名函数" },
  { kg_id: "func-higher-order", label: "高阶函数", domain_key: "function", domain_title: "函数与递归", star_path_id: "func-higher-order", knowledge_keys: ["func-higher-order"], level: "advanced", default_difficulty: 4, summary: "把函数作为参数或返回值组织行为" },
  { kg_id: "func-contract", label: "函数契约与文档", domain_key: "function", domain_title: "函数与递归", star_path_id: "func-contract", knowledge_keys: ["func-contract"], level: "intermediate", default_difficulty: 3, summary: "明确输入、输出、异常和副作用" },
  { kg_id: "func-unit-test", label: "函数单元测试", domain_key: "function", domain_title: "函数与递归", star_path_id: "func-unit-test", knowledge_keys: ["func-unit-test"], level: "advanced", default_difficulty: 4, summary: "用正常、边界和异常用例验证函数" },
  { kg_id: "func-pure", label: "纯函数与副作用", domain_key: "function", domain_title: "函数与递归", star_path_id: "func-pure", knowledge_keys: ["func-pure"], level: "advanced", default_difficulty: 4, summary: "区分返回结果与修改外部状态" },
  { kg_id: "func-memoization", label: "递归记忆化", domain_key: "function", domain_title: "函数与递归", star_path_id: "func-memoization", knowledge_keys: ["func-memoization"], level: "advanced", default_difficulty: 5, summary: "缓存重复子问题以优化递归计算" },
  { kg_id: "search-complexity", label: "时间复杂度", domain_key: "search", domain_title: "查找与搜索", star_path_id: "search-complexity", knowledge_keys: ["search-complexity"], level: "advanced", default_difficulty: 4, summary: "比较 O(1)、O(log n)、O(n) 与 O(n²)" },
  { kg_id: "search-boundary", label: "二分边界模板", domain_key: "search", domain_title: "查找与搜索", star_path_id: "search-boundary", knowledge_keys: ["search-boundary"], level: "advanced", default_difficulty: 5, summary: "处理左闭右闭、左闭右开与重复元素边界" },
  { kg_id: "search-bubble", label: "冒泡排序", domain_key: "search", domain_title: "查找与搜索", star_path_id: "search-bubble", knowledge_keys: ["search-bubble"], level: "intermediate", default_difficulty: 3, summary: "通过相邻交换逐轮确定最大元素" },
  { kg_id: "search-selection", label: "选择排序", domain_key: "search", domain_title: "查找与搜索", star_path_id: "search-selection", knowledge_keys: ["search-selection"], level: "intermediate", default_difficulty: 3, summary: "每轮选择最值并放到已排序区" },
  { kg_id: "search-insertion", label: "插入排序", domain_key: "search", domain_title: "查找与搜索", star_path_id: "search-insertion", knowledge_keys: ["search-insertion"], level: "advanced", default_difficulty: 4, summary: "维护已排序区并插入新元素" },
  { kg_id: "search-hash", label: "哈希查找", domain_key: "search", domain_title: "查找与搜索", star_path_id: "search-hash", knowledge_keys: ["search-hash"], level: "advanced", default_difficulty: 4, summary: "利用集合和字典实现近似常数时间查找" },
  { kg_id: "search-two-pointer", label: "双指针搜索", domain_key: "search", domain_title: "查找与搜索", star_path_id: "search-two-pointer", knowledge_keys: ["search-two-pointer"], level: "advanced", default_difficulty: 5, summary: "用左右或快慢指针缩小搜索空间" },
  { kg_id: "search-bfs", label: "广度优先搜索入门", domain_key: "search", domain_title: "查找与搜索", star_path_id: "search-bfs", knowledge_keys: ["search-bfs"], level: "advanced", default_difficulty: 5, summary: "使用队列按层搜索最短步数" },
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
