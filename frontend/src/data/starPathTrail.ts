import { getPythonTrialQuestion, type PythonTrialQuestion } from './pythonTrialQuestions'

export type StarPathNodeStatus = 'current' | 'done' | 'progress' | 'locked'
export type StarPathGem = 'done' | 'active' | 'locked' | 'pending'
export type StarPathNodeIcon = 'code' | 'server' | 'lock'

export interface StarPathNode {
  /** 节点编号，如 01 */
  id: string
  title: string
  /** 第二行标题（如「应用」） */
  titleLine2?: string
  status: StarPathNodeStatus
  /** 该板块下的全部试炼题目 id（按推荐顺序） */
  questionIds: string[]
  position: 'center' | 'n2' | 'n3' | 'n4' | 'n5' | 'n6' | 'n7'
  anchor?: 'left' | 'right'
  icon: StarPathNodeIcon
  gems: [StarPathGem, StarPathGem, StarPathGem, StarPathGem]
  knowledgeTags: string[]
  advice: string
  mastery: number
  rewardCrystal: number
  rewardStardust: number
}

/** 算法基础星域 · 星轨 01–07，每板块含多道试炼 */
export const STAR_PATH_ALGO_NODES: StarPathNode[] = [
  {
    id: '01',
    title: '算法思维入门',
    status: 'current',
    questionIds: ['hello-print', 'print-name', 'print-calc', 'print-lines'],
    position: 'center',
    icon: 'code',
    gems: ['done', 'done', 'done', 'done'],
    knowledgeTags: ['抽象', '建模', '算法流程', '伪代码'],
    advice: '你已掌握算法基本流程，建议继续学习时间复杂度分析，为后续学习打下基础。',
    mastery: 85,
    rewardCrystal: 1,
    rewardStardust: 10,
  },
  {
    id: '02',
    title: '时间复杂度',
    titleLine2: '分析',
    status: 'done',
    questionIds: ['var-sum', 'var-product', 'var-diff', 'var-quotient'],
    position: 'n2',
    anchor: 'left',
    icon: 'code',
    gems: ['done', 'done', 'done', 'done'],
    knowledgeTags: ['大 O 记号', '常数时间', '输入规模', '运算次数'],
    advice: '变量与算术是估算运行步数的基础，可在试炼中反复对比不同写法。',
    mastery: 100,
    rewardCrystal: 1,
    rewardStardust: 12,
  },
  {
    id: '03',
    title: '递归与分治',
    status: 'locked',
    questionIds: ['if-parity', 'if-max-two', 'if-pass', 'if-sign'],
    position: 'n3',
    anchor: 'left',
    icon: 'lock',
    gems: ['locked', 'locked', 'locked', 'pending'],
    knowledgeTags: ['分支', '子问题', '基准情形', '递推'],
    advice: '完成「时间复杂度分析」试炼后解锁；先熟练条件分支，再进入递归专题。',
    mastery: 0,
    rewardCrystal: 1,
    rewardStardust: 15,
  },
  {
    id: '04',
    title: '动态规划',
    titleLine2: '基础',
    status: 'locked',
    questionIds: ['for-sum', 'for-factorial', 'for-count-evens', 'for-mult-table'],
    position: 'n4',
    anchor: 'right',
    icon: 'lock',
    gems: ['locked', 'locked', 'pending', 'pending'],
    knowledgeTags: ['状态', '转移方程', '最优子结构', '累加'],
    advice: '解锁后通过 for 循环累加试炼，理解「重复子问题」与表格化思路。',
    mastery: 0,
    rewardCrystal: 2,
    rewardStardust: 18,
  },
  {
    id: '05',
    title: '贪心算法',
    status: 'progress',
    questionIds: ['list-max', 'list-min', 'list-sum-loop', 'list-ends'],
    position: 'n5',
    anchor: 'right',
    icon: 'server',
    gems: ['done', 'done', 'done', 'pending'],
    knowledgeTags: ['局部最优', '选择策略', '列表遍历', '比较'],
    advice: '峰值扫描试炼对应「每步取当前最优」的贪心直觉，完成全部测试即可点亮节点。',
    mastery: 72,
    rewardCrystal: 1,
    rewardStardust: 15,
  },
  {
    id: '06',
    title: '图论基础',
    status: 'locked',
    questionIds: ['def-rect-area', 'def-perimeter', 'def-double', 'def-max-two'],
    position: 'n6',
    anchor: 'left',
    icon: 'lock',
    gems: ['pending', 'pending', 'pending', 'pending'],
    knowledgeTags: ['顶点', '边', '邻接', '函数封装'],
    advice: '函数试炼帮助你把「图上的操作」封装成可复用模块，解锁后继续探索。',
    mastery: 0,
    rewardCrystal: 2,
    rewardStardust: 20,
  },
  {
    id: '07',
    title: '算法综合',
    titleLine2: '应用',
    status: 'locked',
    questionIds: ['list-total', 'capstone-positive-count', 'capstone-range-sum', 'capstone-fizz'],
    position: 'n7',
    anchor: 'left',
    icon: 'lock',
    gems: ['pending', 'pending', 'pending', 'pending'],
    knowledgeTags: ['函数', '循环', '列表', '综合调试'],
    advice: '通关前置节点后挑战综合试炼：组合函数与循环，完成星轨毕业关卡。',
    mastery: 0,
    rewardCrystal: 3,
    rewardStardust: 25,
  },
]

export function getStarPathNode(id: string) {
  return STAR_PATH_ALGO_NODES.find((node) => node.id === id) ?? null
}

export function getStarPathNodeByQuestionId(questionId: string) {
  return STAR_PATH_ALGO_NODES.find((node) => node.questionIds.includes(questionId)) ?? null
}

export function getPrimaryQuestionId(node: StarPathNode) {
  return node.questionIds[0] ?? ''
}

export function getStarPathQuestionsForNode(nodeId: string): PythonTrialQuestion[] {
  const node = getStarPathNode(nodeId)
  if (!node) return []
  return node.questionIds
    .map((id) => getPythonTrialQuestion(id))
    .filter((item): item is PythonTrialQuestion => item !== null)
}

export function getUnlockedStarPathNodes() {
  return STAR_PATH_ALGO_NODES.filter(isStarPathNodeUnlocked)
}

export function formatStarPathGems(gems: StarPathNode['gems']) {
  return gems
    .map((gem) => {
      if (gem === 'done' || gem === 'active') return '◆'
      return '◇'
    })
    .join(' ')
}

export function starPathNodeTrackClass(node: StarPathNode) {
  if (node.status === 'current') return 'current'
  if (node.status === 'locked') return 'locked'
  if (node.status === 'progress') return 'progress'
  return 'done'
}

export function isStarPathNodeUnlocked(node: StarPathNode) {
  return node.status !== 'locked'
}

export function formatStarPathNodeLabel(node: StarPathNode) {
  return node.titleLine2 ? `${node.id} ${node.title}${node.titleLine2}` : `${node.id} ${node.title}`
}

export function getNodeOrderBonus(nodeId: string, questionId: string) {
  const node = STAR_PATH_ALGO_NODES.find((item) => item.id === nodeId)
  if (!node) return 0
  const index = node.questionIds.indexOf(questionId)
  if (index < 0) return 0
  return Math.max(10, 90 - index * 18)
}
