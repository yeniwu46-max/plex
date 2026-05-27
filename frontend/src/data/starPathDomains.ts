/** 星轨路径 · 六大学域与知识点目录 */

export interface StarPathKnowledgePoint {
  id: string
  domainKey: string
  title: string
  summary: string
  detail: string
  tags: string[]
  level: '入门' | '进阶' | '挑战'
  /** 关联 Python 试炼题 id（算法基础域） */
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
  { key: STAR_PATH_TAB_ALL, label: '全部星域' },
  { key: 'lang', label: '语言基础' },
  { key: 'algo', label: '算法基础' },
  { key: 'dp', label: '动态规划' },
  { key: 'geom', label: '计算几何' },
  { key: 'graph', label: '图论' },
  { key: 'ds', label: '数据结构' },
]

export const STAR_PATH_DOMAINS: StarPathDomainMeta[] = [
  {
    key: 'lang',
    title: '语言基础',
    description: '掌握编程语言的语法、类型与运行模型，为算法与工程实践打底。',
    focus: '变量 · 控制流 · 函数 · 模块',
    knowledgePoints: [
      {
        id: 'lang-01',
        domainKey: 'lang',
        title: '变量与数据类型',
        summary: '理解基本类型、赋值与内存中的表示。',
        detail: '整型、浮点、布尔与字符串的声明；类型转换规则；不可变对象与引用。',
        tags: ['变量', '类型', '赋值'],
        level: '入门',
      },
      {
        id: 'lang-02',
        domainKey: 'lang',
        title: '条件与循环',
        summary: '用分支与迭代描述程序行为。',
        detail: 'if/elif/else 嵌套；for 与 while 的适用场景；break/continue 与循环不变量。',
        tags: ['分支', '循环', '控制流'],
        level: '入门',
      },
      {
        id: 'lang-03',
        domainKey: 'lang',
        title: '函数与作用域',
        summary: '封装逻辑并管理名字可见性。',
        detail: '形参与实参、返回值；局部/全局/闭包；递归函数的基本写法。',
        tags: ['函数', '作用域', '封装'],
        level: '进阶',
      },
      {
        id: 'lang-04',
        domainKey: 'lang',
        title: '集合与推导式',
        summary: '高效处理一组数据。',
        detail: '列表、元组、字典、集合的操作；列表推导与生成器入门。',
        tags: ['列表', '字典', '推导式'],
        level: '进阶',
      },
    ],
  },
  {
    key: 'algo',
    title: '算法基础',
    description: '建立算法思维：建模、复杂度分析与常见策略。',
    focus: '复杂度 · 枚举 · 贪心 · 分治',
    knowledgePoints: [
      {
        id: 'algo-01',
        domainKey: 'algo',
        title: '算法思维入门',
        summary: '从问题到步骤：抽象、建模与正确性直觉。',
        detail: '输入输出约定；暴力与优化思路；用样例验证算法。',
        tags: ['建模', '流程', '伪代码'],
        level: '入门',
        questionId: 'hello-print',
      },
      {
        id: 'algo-02',
        domainKey: 'algo',
        title: '时间复杂度',
        summary: '用大 O 记号比较算法效率。',
        detail: '常见阶 O(1)、O(log n)、O(n)、O(n log n)、O(n²)；最坏与平均情形。',
        tags: ['大 O', '复杂度', '规模'],
        level: '入门',
        questionId: 'var-sum',
      },
      {
        id: 'algo-03',
        domainKey: 'algo',
        title: '递归与分治',
        summary: '把问题拆成相似子问题。',
        detail: '基准情形与递推关系；分治三步：分、治、合；主定理直觉。',
        tags: ['递归', '分治', '子问题'],
        level: '进阶',
      },
      {
        id: 'algo-04',
        domainKey: 'algo',
        title: '贪心策略',
        summary: '每步做局部最优，期望得到全局解。',
        detail: '活动选择、区间调度；证明贪心选择性质与最优子结构。',
        tags: ['贪心', '局部最优', '证明'],
        level: '挑战',
      },
    ],
  },
  {
    key: 'dp',
    title: '动态规划',
    description: '重叠子问题 + 最优子结构，用表格记住状态。',
    focus: '状态 · 转移 · 空间优化',
    knowledgePoints: [
      {
        id: 'dp-01',
        domainKey: 'dp',
        title: 'DP 三要素',
        summary: '定义状态、转移方程与边界条件。',
        detail: '自顶向下记忆化与自底向上填表；何时适用 DP。',
        tags: ['状态', '转移', '边界'],
        level: '入门',
      },
      {
        id: 'dp-02',
        domainKey: 'dp',
        title: '线性 DP',
        summary: '一维状态的经典模型。',
        detail: '斐波那契、爬楼梯；最大子数组（Kadane）；打家劫舍。',
        tags: ['一维', '线性', '经典'],
        level: '入门',
      },
      {
        id: 'dp-03',
        domainKey: 'dp',
        title: '背包问题',
        summary: '0-1 与完全背包的表格写法。',
        detail: 'dp[i][w] 含义；滚动数组降维；物品与容量循环顺序。',
        tags: ['背包', '0-1', '完全背包'],
        level: '进阶',
      },
      {
        id: 'dp-04',
        domainKey: 'dp',
        title: '区间 DP',
        summary: '在区间上合并或切分的最优解。',
        detail: '矩阵链乘、石子合并；枚举分割点更新区间状态。',
        tags: ['区间', '合并', '分割'],
        level: '挑战',
      },
    ],
  },
  {
    key: 'geom',
    title: '计算几何',
    description: '点线面关系、向量运算与几何算法。',
    focus: '向量 · 凸包 · 扫描线',
    knowledgePoints: [
      {
        id: 'geom-01',
        domainKey: 'geom',
        title: '向量与点积',
        summary: '用向量描述方向、长度与夹角。',
        detail: '二维向量加减、数乘；点积判断垂直与投影；叉积判断转向。',
        tags: ['向量', '点积', '叉积'],
        level: '入门',
      },
      {
        id: 'geom-02',
        domainKey: 'geom',
        title: '线段相交',
        summary: '判断两线段是否相交及交点。',
        detail: '跨立实验；快速排斥实验；参数方程求交。',
        tags: ['线段', '相交', '判定'],
        level: '进阶',
      },
      {
        id: 'geom-03',
        domainKey: 'geom',
        title: '凸包',
        summary: '包含点集的最小凸多边形。',
        detail: 'Andrew 单调链；Graham 扫描；时间复杂度 O(n log n)。',
        tags: ['凸包', '单调链', '扫描'],
        level: '进阶',
      },
      {
        id: 'geom-04',
        domainKey: 'geom',
        title: '最近点对',
        summary: '平面上最近两点距离的分治求法。',
        detail: '按 x 排序分治；合并时检查条带内候选点。',
        tags: ['分治', '最近点', '平面'],
        level: '挑战',
      },
    ],
  },
  {
    key: 'graph',
    title: '图论',
    description: '顶点与边的结构，路径、连通性与流。',
    focus: '遍历 · 最短路 · 生成树',
    knowledgePoints: [
      {
        id: 'graph-01',
        domainKey: 'graph',
        title: '图的表示',
        summary: '邻接矩阵与邻接表的选择。',
        detail: '稀疏图用邻接表；稠密图可用矩阵；带权边的存储。',
        tags: ['邻接表', '邻接矩阵', '存储'],
        level: '入门',
      },
      {
        id: 'graph-02',
        domainKey: 'graph',
        title: 'BFS 与 DFS',
        summary: '图的两种基本遍历。',
        detail: '队列实现 BFS 层次遍历；栈/递归 DFS；连通分量计数。',
        tags: ['BFS', 'DFS', '遍历'],
        level: '入门',
      },
      {
        id: 'graph-03',
        domainKey: 'graph',
        title: '最短路径',
        summary: 'Dijkstra 与 Bellman-Ford 的适用场景。',
        detail: '非负权用 Dijkstra + 堆优化；负权边用 Bellman-Ford。',
        tags: ['最短路', 'Dijkstra', '负权'],
        level: '进阶',
      },
      {
        id: 'graph-04',
        domainKey: 'graph',
        title: '拓扑排序',
        summary: '有向无环图的线性序。',
        detail: 'Kahn 算法（入度）；DFS 后序逆序；判环。',
        tags: ['DAG', '拓扑', '入度'],
        level: '挑战',
      },
    ],
  },
  {
    key: 'ds',
    title: '数据结构',
    description: '组织数据以支持高效查询与更新。',
    focus: '线性表 · 树 · 堆 · 哈希',
    knowledgePoints: [
      {
        id: 'ds-01',
        domainKey: 'ds',
        title: '栈与队列',
        summary: 'LIFO 与 FIFO 的基本操作。',
        detail: '数组/链表实现；表达式求值；BFS 队列应用。',
        tags: ['栈', '队列', '线性'],
        level: '入门',
      },
      {
        id: 'ds-02',
        domainKey: 'ds',
        title: '二叉树遍历',
        summary: '前序、中序、后序与层序。',
        detail: '递归与迭代写法；由遍历序列重建树。',
        tags: ['二叉树', '遍历', '递归'],
        level: '入门',
      },
      {
        id: 'ds-03',
        domainKey: 'ds',
        title: '二叉搜索树',
        summary: '有序性支撑查找与插入。',
        detail: 'BST 性质；平均 O(log n)；退化链与平衡树动机。',
        tags: ['BST', '查找', '插入'],
        level: '进阶',
      },
      {
        id: 'ds-04',
        domainKey: 'ds',
        title: '堆与优先队列',
        summary: '动态维护最值。',
        detail: '大根堆/小根堆；heapify 与 push/pop；Top K 问题。',
        tags: ['堆', '优先队列', 'Top K'],
        level: '挑战',
      },
    ],
  },
]

export function getStarPathDomain(key: string) {
  return STAR_PATH_DOMAINS.find((d) => d.key === key)
}

export function getStarPathKnowledgePoint(id: string) {
  for (const domain of STAR_PATH_DOMAINS) {
    const found = domain.knowledgePoints.find((kp) => kp.id === id)
    if (found) return { point: found, domain }
  }
  return null
}

export function getKnowledgePointsForDomain(domainKey: string) {
  return getStarPathDomain(domainKey)?.knowledgePoints ?? []
}

export function domainMetaFromApi(domain: { key: string; title: string; progress: number; state: string }) {
  const meta = getStarPathDomain(domain.key)
  return {
    ...domain,
    description: meta?.description ?? '',
    focus: meta?.focus ?? '',
  }
}
