import type { PythonTrialQuestion } from '../data/pythonTrialQuestions'
import { getPythonTrialQuestion } from '../data/pythonTrialQuestions'
import type { StarPathKnowledgePoint } from '../data/starPathDomains'

const STORAGE_PREFIX = 'starpath-q:'

type QuestionTemplate = Omit<PythonTrialQuestion, 'id' | 'title' | 'topic' | 'tags'> & {
  titleSuffix: string
  topic: string
  tags: string[]
}

function seededIndex(seed: string, length: number, salt = '') {
  let h = 0
  const s = seed + salt
  for (let i = 0; i < s.length; i += 1) {
    h = (h << 5) - h + s.charCodeAt(i)
    h |= 0
  }
  return Math.abs(h) % length
}

function templatesForDomain(domainKey: string): QuestionTemplate[] {
  const common = {
    difficulty: '入门' as const,
    rewardXp: 30,
    durationMin: 10,
    constraints: ['使用 print 输出结果', '不要额外输入'],
    runMode: 'stdout' as const,
    examples: [{ input: '（由测试注入）', output: '见题目说明' }],
  }

  const pools: Record<string, QuestionTemplate[]> = {
    lang: [
      {
        ...common,
        titleSuffix: '变量求和',
        topic: '变量与算术',
        tags: ['变量', 'print'],
        description:
          '测试数据已提供整数 `a` 与 `b`。请计算它们的和并用 `print` 输出（只输出数字）。',
        testCases: [
          { id: 't1', label: '样例 1', setup: 'a = 4\nb = 6', expected: '10' },
          { id: 't2', label: '样例 2', setup: 'a = 15\nb = 27', expected: '42' },
        ],
        starterCode: '# a、b 已给定\n',
        hint: '使用 print(a + b)',
      },
      {
        ...common,
        titleSuffix: '奇偶判断',
        topic: '条件分支',
        tags: ['if', '分支'],
        description: '给定整数 `n`，若 `n` 为偶数输出 `even`，否则输出 `odd`。',
        testCases: [
          { id: 't1', label: '偶数', setup: 'n = 8', expected: 'even' },
          { id: 't2', label: '奇数', setup: 'n = 7', expected: 'odd' },
        ],
        starterCode: '# n 已给定\n',
        hint: 'n % 2 == 0',
      },
      {
        ...common,
        titleSuffix: '循环累加',
        topic: 'for 循环',
        tags: ['循环', '累加'],
        description: '给定正整数 `n`，输出 1 到 n 的和（只输出数字）。',
        testCases: [
          { id: 't1', label: 'n=5', setup: 'n = 5', expected: '15' },
          { id: 't2', label: 'n=10', setup: 'n = 10', expected: '55' },
        ],
        starterCode: '# n 已给定\n',
        hint: '用 for 循环累加',
      },
    ],
    dp: [
      {
        ...common,
        titleSuffix: '爬楼梯',
        topic: '线性 DP',
        tags: ['DP', '斐波那契'],
        description: '给定 `n`（台阶数），每次可爬 1 或 2 阶，输出到达顶部的方案数（n≤10 时直接循环即可）。',
        testCases: [
          { id: 't1', label: 'n=3', setup: 'n = 3', expected: '3' },
          { id: 't2', label: 'n=5', setup: 'n = 5', expected: '8' },
        ],
        starterCode: '# n 已给定\n',
        hint: 'dp[i]=dp[i-1]+dp[i-2]',
      },
      {
        ...common,
        titleSuffix: '最大子段和',
        topic: 'Kadane',
        tags: ['DP', '数组'],
        description: '给定列表 `nums`（已注入），输出其连续子数组的最大和。',
        testCases: [
          { id: 't1', label: '样例', setup: 'nums = [-2, 1, -3, 4, -1, 2, 1, -5, 4]', expected: '6' },
          { id: 't2', label: '全负', setup: 'nums = [-5, -2, -8]', expected: '-2' },
        ],
        starterCode: '# nums 已给定\n',
        hint: '维护当前和与最大值',
      },
    ],
    geom: [
      {
        ...common,
        titleSuffix: '向量点积',
        topic: '向量运算',
        tags: ['向量', '点积'],
        description: '给定 `ax, ay, bx, by`，输出二维向量 (ax,ay) 与 (bx,by) 的点积。',
        testCases: [
          { id: 't1', label: '样例', setup: 'ax, ay, bx, by = 1, 2, 3, 4', expected: '11' },
          { id: 't2', label: '垂直', setup: 'ax, ay, bx, by = 1, 0, 0, 1', expected: '0' },
        ],
        starterCode: '# 分量已给定\n',
        hint: 'ax*bx + ay*by',
      },
      {
        ...common,
        titleSuffix: '叉积符号',
        topic: '叉积',
        tags: ['叉积', '转向'],
        description:
          '给定平面上三点 O(0,0)、A(ax,ay)、B(bx,by)（坐标已注入为 ax,ay,bx,by）。若叉积 >0 输出 `left`，<0 输出 `right`，=0 输出 `collinear`。',
        testCases: [
          { id: 't1', label: '左转', setup: 'ax, ay, bx, by = 1, 0, 0, 1', expected: 'left' },
          { id: 't2', label: '共线', setup: 'ax, ay, bx, by = 2, 4, 4, 8', expected: 'collinear' },
        ],
        starterCode: '# 坐标已给定\n',
        hint: 'cross = ax*by - ay*bx',
      },
    ],
    graph: [
      {
        ...common,
        titleSuffix: '邻接度统计',
        topic: '图的表示',
        tags: ['图', '度数'],
        description:
          '给定无向图边列表 `edges`（已注入为列表的列表）与顶点 `v`，输出顶点 v 的度数（只输出数字）。',
        testCases: [
          {
            id: 't1',
            label: '样例',
            setup: 'edges = [[1,2],[1,3],[2,3]]\nv = 1',
            expected: '2',
          },
          {
            id: 't2',
            label: '孤立',
            setup: 'edges = [[1,2]]\nv = 3',
            expected: '0',
          },
        ],
        starterCode: '# edges, v 已给定\n',
        hint: '统计与 v 相连的边',
      },
      {
        ...common,
        titleSuffix: 'BFS 层数',
        topic: 'BFS',
        tags: ['BFS', '最短路'],
        description:
          '给定 `n` 个结点（编号 1..n）的邻接表 `adj` 与起点 `start`、终点 `goal`（已注入），边权均为 1，输出最短距离；不可达输出 `-1`。',
        testCases: [
          {
            id: 't1',
            label: '可达',
            setup:
              'adj = {1: [2], 2: [1, 3], 3: [2]}\nstart, goal, n = 1, 3, 3',
            expected: '2',
          },
          {
            id: 't2',
            label: '同点',
            setup: 'adj = {1: [2]}\nstart, goal, n = 1, 1, 2',
            expected: '0',
          },
        ],
        starterCode: '# adj, start, goal, n 已给定\n',
        hint: '用队列 BFS',
      },
    ],
    ds: [
      {
        ...common,
        titleSuffix: '栈顶求值',
        topic: '栈',
        tags: ['栈', 'LIFO'],
        description: '给定列表 `ops`：数字表示 push，字符串 `"pop"` 表示弹出栈顶。输出最终栈顶元素（保证栈非空）。',
        testCases: [
          { id: 't1', label: '样例', setup: 'ops = [1, 2, "pop", 3]', expected: '3' },
          { id: 't2', label: '多次', setup: 'ops = [5, "pop", 7, 8]', expected: '8' },
        ],
        starterCode: '# ops 已给定\n',
        hint: '用 list 模拟栈',
      },
      {
        ...common,
        titleSuffix: '二叉树深度',
        topic: '树遍历',
        tags: ['二叉树', '递归'],
        description:
          '给定二叉树嵌套字典 `root`（`None` 表示空，`left`/`right` 为子结点），输出树的最大深度。',
        testCases: [
          {
            id: 't1',
            label: '链',
            setup: 'root = {"val": 1, "left": {"val": 2, "left": None, "right": None}, "right": None}',
            expected: '2',
          },
          {
            id: 't2',
            label: '单点',
            setup: 'root = {"val": 0, "left": None, "right": None}',
            expected: '1',
          },
        ],
        starterCode: '# root 已给定\n',
        hint: '1 + max(左深度, 右深度)',
      },
    ],
    algo: [
      {
        ...common,
        titleSuffix: '枚举优化',
        topic: '暴力与优化',
        tags: ['枚举', '建模'],
        description: '给定正整数 `n`，输出 1..n 中能被 3 整除但不能被 5 整除的整数个数。',
        testCases: [
          { id: 't1', label: 'n=15', setup: 'n = 15', expected: '4' },
          { id: 't2', label: 'n=30', setup: 'n = 30', expected: '8' },
        ],
        starterCode: '# n 已给定\n',
        hint: '循环计数',
      },
    ],
  }

  return pools[domainKey] ?? pools.lang
}

function buildFromTemplate(kp: StarPathKnowledgePoint, template: QuestionTemplate, variant: number): PythonTrialQuestion {
  return {
    id: `gen-${kp.id}-v${variant}`,
    title: `${kp.title} · ${template.titleSuffix}`,
    topic: template.topic,
    difficulty: template.difficulty,
    rewardXp: template.rewardXp,
    durationMin: template.durationMin,
    tags: [...template.tags, ...kp.tags.slice(0, 2)],
    description: template.description,
    constraints: template.constraints,
    examples: template.examples,
    testCases: template.testCases,
    starterCode: template.starterCode,
    runMode: template.runMode,
    hint: template.hint,
  }
}

export function generateStarPathQuestion(kp: StarPathKnowledgePoint, reroll = false): PythonTrialQuestion {
  const templates = templatesForDomain(kp.domainKey)
  const cacheKey = STORAGE_PREFIX + kp.id

  if (!reroll && typeof sessionStorage !== 'undefined') {
    const cached = sessionStorage.getItem(cacheKey)
    if (cached) {
      try {
        return JSON.parse(cached) as PythonTrialQuestion
      } catch {
        sessionStorage.removeItem(cacheKey)
      }
    }
  }

  const variant = seededIndex(kp.id, templates.length, reroll ? String(Date.now()) : '')
  const question = buildFromTemplate(kp, templates[variant]!, variant)

  if (typeof sessionStorage !== 'undefined') {
    sessionStorage.setItem(cacheKey, JSON.stringify(question))
  }

  return question
}

export function clearStarPathQuestionCache(kpId: string) {
  if (typeof sessionStorage !== 'undefined') {
    sessionStorage.removeItem(STORAGE_PREFIX + kpId)
  }
}

export function resolveStarPathQuestion(
  kp: StarPathKnowledgePoint,
  options?: { reroll?: boolean },
): PythonTrialQuestion | null {
  if (kp.questionId) {
    const staticQ = getPythonTrialQuestion(kp.questionId)
    if (staticQ) return staticQ
  }
  return generateStarPathQuestion(kp, options?.reroll ?? false)
}

export function resolveQuestionById(
  questionId: string,
  kp?: StarPathKnowledgePoint | null,
): PythonTrialQuestion | null {
  const staticQ = getPythonTrialQuestion(questionId)
  if (staticQ) return staticQ
  if (kp && typeof sessionStorage !== 'undefined') {
    const cached = sessionStorage.getItem(STORAGE_PREFIX + kp.id)
    if (cached) {
      try {
        const parsed = JSON.parse(cached) as PythonTrialQuestion
        if (parsed.id === questionId) return parsed
      } catch {
        sessionStorage.removeItem(STORAGE_PREFIX + kp.id)
      }
    }
  }
  if (kp) return generateStarPathQuestion(kp)
  return null
}
