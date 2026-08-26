/** 本文件由 backend/scripts/knowledge_rebuild/gen_frontend.py 生成，请勿手改。 */
/** 与 backend/app/data/knowledge_node_registry.py 对齐 · Python 八大学域 26 知识点 */

export interface StarPathKnowledgePoint {
  id: string
  domainKey: string
  title: string
  summary: string
  detail: string
  tags: string[]
  level: '入门' | '进阶' | '挑战'
  /** 初识导引步骤（仅首个知识点） */
  introSteps?: string[]
  /** 关联 Python 试炼题 id（缺省则完全走接口取真题） */
  questionId?: string
}

export interface StarPathDomainMeta {
  key: string
  title: string
  description: string
  focus: string
  knowledgePoints: StarPathKnowledgePoint[]
}

export const STAR_PATH_TAB_ALL = 'all' as const

export const STAR_PATH_TABS: Array<{ key: typeof STAR_PATH_TAB_ALL | string; label: string }> = [
  { key: STAR_PATH_TAB_ALL, label: '全部阶段' },
  { key: "lang-basics", label: "语言入门" },
  { key: "sequence", label: "顺序结构" },
  { key: "branch", label: "分支结构" },
  { key: "loop", label: "循环结构" },
  { key: "array", label: "数组" },
  { key: "string", label: "字符串" },
  { key: "function", label: "函数与递归" },
  { key: "search", label: "查找与搜索" },
]

export const STAR_PATH_DOMAINS: StarPathDomainMeta[] = [
  {
    key: "lang-basics",
    title: "语言入门",
    description: "你与小E 降落「启航星」，写下第一行 print，给变量命名，再让程序听懂人的输入。",
    focus: "输出、注释、变量、输入",
    knowledgePoints: [
      {
        id: "lang-print",
        domainKey: "lang-basics",
        title: "print 输出与注释",
        summary: "小E 的探测器需要发出第一束信号——用 print 向宇宙问好。",
        detail: "print 输出、字符串字面量、换行与逗号分隔，以及用 # 写注释。",
        introSteps: [
          "在编辑器里写 print(\"Hello\")，点击运行测试确认输出。",
          "尝试用逗号连接多个内容：print(\"XP\", 100)。",
          "在代码上方用 # 写一行注释，说明这段程序做什么。",
          "完成左侧示例后，点击「开始编程试炼」进入第一题。",
        ],
        tags: ["lang-print", "intro", "print", "python"],
        level: "入门",
        questionId: "hello-print",
      },
      {
        id: "lang-var",
        domainKey: "lang-basics",
        title: "变量与类型",
        summary: "把探测器读数存进变量舱，认识 int / float / str / bool。",
        detail: "赋值与命名、四种基础类型、type() 查看类型、不要覆盖内置名。",
        tags: ["lang-var", "var", "syntax", "basic"],
        level: "入门",
        questionId: "var-sum",
      },
      {
        id: "lang-input",
        domainKey: "lang-basics",
        title: "输入 input",
        summary: "接收地面站传来的指令，用 input 读进来再转成需要的类型。",
        detail: "input 永远返回字符串、int()/float() 转换、非法输入的异常处理。",
        tags: ["lang-input", "io", "input", "file"],
        level: "入门",
        questionId: "var-product",
      },
    ],
  },
  {
    key: "sequence",
    title: "顺序结构",
    description: "「运算星云」里所有指令按书写顺序逐条执行，小E 教你校准算术、表达式与类型转换。",
    focus: "算术运算、表达式、类型转换",
    knowledgePoints: [
      {
        id: "seq-arith",
        domainKey: "sequence",
        title: "算术运算",
        summary: "校准飞船的计算核心：加减乘除、整除、取余与幂运算。",
        detail: "+ - * / 与 // % **，除法结果恒为浮点，除零会报错。",
        tags: ["seq-arith", "ops", "arith"],
        level: "入门",
        questionId: "print-calc",
      },
      {
        id: "seq-expr",
        domainKey: "sequence",
        title: "表达式与优先级",
        summary: "把多个运算拼成一条表达式，先算谁后算谁要心里有数。",
        detail: "比较运算、and / or / not、优先级、链式比较与短路求值。",
        tags: ["seq-expr", "expr", "operator-priority"],
        level: "入门",
      },
      {
        id: "seq-type",
        domainKey: "sequence",
        title: "数据类型与转换",
        summary: "数据在舱段之间流转，需要在整数、小数与文本之间来回转换。",
        detail: "int()/float()/str()/bool() 转换、round 与截断的差别、转换失败的 ValueError。",
        tags: ["seq-type", "datatype", "cast", "hightype"],
        level: "入门",
      },
    ],
  },
  {
    key: "branch",
    title: "分支结构",
    description: "「分支峡谷」的岔路要靠条件判断来选，if / elif / else 决定飞船走哪一条。",
    focus: "if / elif / else 与复合条件",
    knowledgePoints: [
      {
        id: "branch-if",
        domainKey: "branch",
        title: "单分支与双分支",
        summary: "峡谷前的第一个岔路口：条件成立走这边，否则走那边。",
        detail: "if 与 if-else、条件表达式的真假、冒号与缩进。",
        tags: ["branch-if", "cond", "condition", "if"],
        level: "入门",
        questionId: "max-of-two",
      },
      {
        id: "branch-elif",
        domainKey: "branch",
        title: "多分支 elif",
        summary: "三条以上的岔路要用 elif 串起来，顺序决定结果。",
        detail: "if-elif-else 链、区间判断的书写顺序、else 兜底。",
        tags: ["branch-elif", "elif", "multi-branch"],
        level: "入门",
      },
      {
        id: "branch-nested",
        domainKey: "branch",
        title: "嵌套与复合条件",
        summary: "岔路里还有岔路，或者用 and / or 把条件合成一条。",
        detail: "嵌套分支、复合条件、两种写法的相互改写、避免过深嵌套。",
        tags: ["branch-nested", "nested-condition", "nested_condition"],
        level: "进阶",
        questionId: "capstone-fizz",
      },
    ],
  },
  {
    key: "loop",
    title: "循环结构",
    description: "「循环环带」上重复的事交给循环去做，for、while、嵌套与跳出各有各的用法。",
    focus: "for、while、嵌套与循环控制",
    knowledgePoints: [
      {
        id: "loop-for",
        domainKey: "loop",
        title: "for 与 range",
        summary: "沿着环带跑固定圈数，for 配合 range 最省力。",
        detail: "for 遍历序列、range 的左闭右开、累加求和模式。",
        tags: ["loop-for", "loop", "for", "range"],
        level: "入门",
        questionId: "sum-1-to-n",
      },
      {
        id: "loop-while",
        domainKey: "loop",
        title: "while 循环",
        summary: "条件成立就一直转，关键是想清楚什么时候停。",
        detail: "while 的循环条件、计数器与哨兵值、死循环的成因。",
        tags: ["loop-while", "while"],
        level: "入门",
        questionId: "loop-sum",
      },
      {
        id: "loop-nested",
        domainKey: "loop",
        title: "嵌套循环",
        summary: "一层环带套一层，外层管行内层管列。",
        detail: "双重循环、打印图形与乘法表、循环次数的量级直觉。",
        tags: ["loop-nested", "nested", "nested_loop"],
        level: "进阶",
      },
      {
        id: "loop-control",
        domainKey: "loop",
        title: "break 与 continue",
        summary: "找到目标就提前跳出，遇到杂质就跳过这一轮。",
        detail: "break 与 continue、只影响最内层循环、for...else 的含义。",
        tags: ["loop-control", "break", "continue"],
        level: "进阶",
        questionId: "fizz-n",
      },
    ],
  },
  {
    key: "array",
    title: "数组",
    description: "「货舱区」用列表把一批数据装在一起，遍历、统计，再堆成二维的货架。",
    focus: "列表创建、遍历统计、二维列表",
    knowledgePoints: [
      {
        id: "array-basic",
        domainKey: "array",
        title: "列表基础",
        summary: "货舱用列表装货：按位置取、切一段、随时增删。",
        detail: "创建列表、正负索引、切片、append / insert / pop / remove 与 len。",
        tags: ["array-basic", "list", "array", "tuple"],
        level: "入门",
        questionId: "list-max",
      },
      {
        id: "array-traverse",
        domainKey: "array",
        title: "遍历与统计",
        summary: "清点整舱货物：遍历一遍就能求和、计数、找出最值。",
        detail: "for 遍历列表、enumerate 取下标、sum / max / min 内置函数。",
        tags: ["array-traverse", "list-traverse"],
        level: "进阶",
      },
      {
        id: "array-2d",
        domainKey: "array",
        title: "二维列表",
        summary: "把货架堆成两层，用行列坐标定位每一格。",
        detail: "嵌套列表表示表格与矩阵、grid[i][j]、二维列表的正确创建方式。",
        tags: ["array-2d", "list-2d", "matrix"],
        level: "进阶",
      },
    ],
  },
  {
    key: "string",
    title: "字符串",
    description: "「语符卫星」上的信息都是文本，逐字取用、切片截取、方法加工。",
    focus: "索引切片、常用方法、字符统计",
    knowledgePoints: [
      {
        id: "string-index",
        domainKey: "string",
        title: "索引与切片",
        summary: "卫星传来的电文可以逐字取用，也能整段截取。",
        detail: "按下标取字符、负索引、切片 s[a:b:c]、反转与字符串不可变。",
        tags: ["string-index", "str", "string"],
        level: "入门",
      },
      {
        id: "string-method",
        domainKey: "string",
        title: "常用方法",
        summary: "电文需要清洗：拆分、拼接、替换、去空白、改大小写。",
        detail: "split / join / replace / strip / upper / lower / find，方法返回新串。",
        tags: ["string-method", "str-method", "string_ops"],
        level: "进阶",
      },
      {
        id: "string-scan",
        domainKey: "string",
        title: "遍历与统计",
        summary: "逐字扫描整段电文，数出每个字符出现了几次。",
        detail: "遍历字符串、count 统计、回文判断、大小写与空格归一化。",
        tags: ["string-scan", "str-scan"],
        level: "进阶",
      },
    ],
  },
  {
    key: "function",
    title: "函数与递归",
    description: "在「封装空间站」把一段逻辑打包成函数反复调用，再让它调用自己完成递归。",
    focus: "定义调用、参数返回、递归",
    knowledgePoints: [
      {
        id: "func-define",
        domainKey: "function",
        title: "定义与调用",
        summary: "把常用的一段逻辑封进函数，之后一句话就能调用。",
        detail: "def 定义、函数名与调用、函数体缩进、docstring。",
        tags: ["func-define", "func", "function", "def"],
        level: "进阶",
      },
      {
        id: "func-param",
        domainKey: "function",
        title: "参数与返回值",
        summary: "给函数递进去参数，让它把结果交回来。",
        detail: "位置参数与默认参数、return 与 None、局部变量与作用域。",
        tags: ["func-param", "parameter", "return"],
        level: "进阶",
      },
      {
        id: "func-recursion",
        domainKey: "function",
        title: "递归",
        summary: "让函数调用它自己，但一定要留好出口。",
        detail: "递归出口与递推、阶乘与斐波那契、递归深度与重复计算。",
        tags: ["func-recursion", "recursion"],
        level: "挑战",
      },
    ],
  },
  {
    key: "search",
    title: "查找与搜索",
    description: "「算法深空」里数据浩瀚，顺序查找、二分查找、排序与统计帮你精准定位。",
    focus: "顺序查找、二分查找、排序、统计",
    knowledgePoints: [
      {
        id: "search-linear",
        domainKey: "search",
        title: "顺序查找",
        summary: "从头到尾一个个比对，找到目标就停下。",
        detail: "顺序查找、返回下标或 -1、in 运算符、O(n) 的代价。",
        tags: ["search-linear", "algo-search", "search"],
        level: "入门",
      },
      {
        id: "search-binary",
        domainKey: "search",
        title: "二分查找",
        summary: "数据排好序后，每次砍掉一半，定位快得多。",
        detail: "二分查找的有序前提、low / high / mid、循环边界与死循环。",
        tags: ["search-binary", "algo-binary", "binary-search"],
        level: "挑战",
        questionId: "algo-binary-search",
      },
      {
        id: "search-sort",
        domainKey: "search",
        title: "排序思想",
        summary: "把货物按大小排好：相邻交换，或每轮挑出最小的。",
        detail: "冒泡排序与选择排序、双重循环结构、与内置 sorted 的关系。",
        tags: ["search-sort", "algo-sort", "sort", "algo-bubble"],
        level: "挑战",
        questionId: "algo-bubble-sort",
      },
      {
        id: "search-stat",
        domainKey: "search",
        title: "统计与去重",
        summary: "给整批数据做一次体检：求和、计数、找最值、去掉重复。",
        detail: "累加与计数、max / min、set 去重与保序去重、字典计数。",
        tags: ["search-stat", "algo-sum", "algo", "sum"],
        level: "进阶",
      },
    ],
  },
]

export function getStarPathDomain(key: string): StarPathDomainMeta | undefined {
  return STAR_PATH_DOMAINS.find((d) => d.key === key)
}

export function getKnowledgePointsForDomain(domainKey: string): StarPathKnowledgePoint[] {
  return getStarPathDomain(domainKey)?.knowledgePoints ?? []
}

export function getStarPathKnowledgePoint(id: string) {
  for (const domain of STAR_PATH_DOMAINS) {
    const point = domain.knowledgePoints.find((p) => p.id === id)
    if (point) return { domain, point }
  }
  return null
}
