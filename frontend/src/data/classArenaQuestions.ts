import type { PythonTrialQuestion } from './pythonTrialQuestions'

/** 班级试炼场 · 高难度编程题池 */
export const CLASS_HARD_QUESTIONS: PythonTrialQuestion[] = [
  {
    id: 'class-hard-sum-two',
    title: '双星求和',
    topic: '班级试炼 · 输入输出',
    difficulty: '挑战',
    rewardXp: 80,
    durationMin: 25,
    tags: ['班级', 'I/O', '限时'],
    description:
      '给定两个整数 a、b（由测试注入）。请输出它们的和。教师试炼场题目，要求一次通过全部隐藏用例。',
    constraints: ['使用 print 输出', '不要额外输出'],
    examples: [
      { input: 'a = 3, b = 5', output: '8' },
      { input: 'a = -12, b = 7', output: '-5' },
    ],
    testCases: [
      { id: 't1', label: '样例 1', setup: 'a = 3\nb = 5', expected: '8' },
      { id: 't2', label: '样例 2', setup: 'a = -12\nb = 7', expected: '-5' },
      { id: 't3', label: '隐藏 1', setup: 'a = 100000\nb = 234567', expected: '334567' },
      { id: 't4', label: '隐藏 2', setup: 'a = 0\nb = 0', expected: '0' },
    ],
    starterCode: `# a、b 已由测试数据提供\n# 输出两数之和\n`,
    runMode: 'stdout',
    hint: 'print(a + b)',
  },
  {
    id: 'class-hard-max-two',
    title: '双峰对决',
    topic: '班级试炼 · 函数',
    difficulty: '挑战',
    rewardXp: 90,
    durationMin: 30,
    tags: ['班级', '函数', '逻辑'],
    description: '实现函数 `max_two(a, b)`，返回 a 与 b 中的较大值。函数名必须正确。',
    constraints: ['函数名 max_two', '使用 return'],
    examples: [
      { input: 'a=9, b=3', output: '9' },
      { input: 'a=-1, b=-5', output: '-1' },
    ],
    testCases: [
      { id: 't1', label: '样例 1', invoke: 'str(max_two(9, 3))', expected: '9' },
      { id: 't2', label: '负数', invoke: 'str(max_two(-1, -5))', expected: '-1' },
      { id: 't3', label: '相等', invoke: 'str(max_two(42, 42))', expected: '42' },
      { id: 't4', label: '隐藏', invoke: 'str(max_two(-100, 88))', expected: '88' },
    ],
    starterCode: `def max_two(a, b):\n    # 返回较大值\n    pass\n`,
    runMode: 'expression',
    hint: 'if a >= b: return a else: return b',
  },
  {
    id: 'class-hard-positive-sum',
    title: '正数星链',
    topic: '班级试炼 · 循环',
    difficulty: '挑战',
    rewardXp: 95,
    durationMin: 35,
    tags: ['班级', '循环', '列表'],
    description:
      '实现 `sum_positive(nums)`，返回整数列表中所有大于 0 的元素之和。请使用 for 循环。',
    constraints: ['函数名 sum_positive', '使用 for 循环'],
    examples: [{ input: 'nums = [1, -2, 3, 0, 4]', output: '8' }],
    testCases: [
      { id: 't1', label: '样例', invoke: 'str(sum_positive([1, -2, 3, 0, 4]))', expected: '8' },
      { id: 't2', label: '全负', invoke: 'str(sum_positive([-1, -2]))', expected: '0' },
      { id: 't3', label: '全正', invoke: 'str(sum_positive([2, 3, 5]))', expected: '10' },
      { id: 't4', label: '隐藏', invoke: 'str(sum_positive([10, -10, 20, -5, 7]))', expected: '37' },
    ],
    starterCode: `def sum_positive(nums):\n    # 累加所有正数\n    pass\n`,
    runMode: 'expression',
    hint: 'total = 0，遍历时 if x > 0: total += x',
  },
]

export const GLADIATOR_DUEL_TIME_SEC = 300

export const GLADIATOR_DUEL_QUESTIONS: PythonTrialQuestion[] = [
  {
    id: 'arena-gladiator-sum',
    title: '两数之和',
    topic: '竞速对决 · 同题 PK',
    difficulty: '挑战',
    rewardXp: 40,
    durationMin: 5,
    tags: ['角斗士', '竞速'],
    description: '给定 a、b，输出 a + b。',
    constraints: ['仅 print 结果', '不要多余输出'],
    examples: [
      { input: 'a = 3, b = 5', output: '8' },
      { input: 'a = 99, b = 1', output: '100' },
    ],
    testCases: [
      { id: 't1', label: '样例 1', setup: 'a = 3\nb = 5', expected: '8' },
      { id: 't2', label: '样例 2', setup: 'a = 99\nb = 1', expected: '100' },
      { id: 't3', label: '隐藏', setup: 'a = 12345\nb = 67890', expected: '80235' },
    ],
    starterCode: `# 输出 a + b\n`,
    runMode: 'stdout',
    hint: 'print(a + b)',
  },
  {
    id: 'arena-gladiator-max',
    title: '两数较大值',
    topic: '竞速对决 · 同题 PK',
    difficulty: '挑战',
    rewardXp: 45,
    durationMin: 5,
    tags: ['角斗士', '竞速'],
    description: '给定 a、b，输出两者中的较大值。',
    constraints: ['仅 print 结果', '不要多余输出'],
    examples: [
      { input: 'a = 3, b = 9', output: '9' },
      { input: 'a = -1, b = -5', output: '-1' },
    ],
    testCases: [
      { id: 't1', label: '样例 1', setup: 'a = 3\nb = 9', expected: '9' },
      { id: 't2', label: '样例 2', setup: 'a = -1\nb = -5', expected: '-1' },
      { id: 't3', label: '相等', setup: 'a = 7\nb = 7', expected: '7' },
    ],
    starterCode: `# 输出 a、b 中的较大值\n`,
    runMode: 'stdout',
    hint: 'print(max(a, b))',
  },
  {
    id: 'arena-gladiator-product',
    title: '两数之积',
    topic: '竞速对决 · 同题 PK',
    difficulty: '挑战',
    rewardXp: 50,
    durationMin: 5,
    tags: ['角斗士', '竞速'],
    description: '给定 a、b，输出 a × b 的结果。',
    constraints: ['仅 print 结果', '不要多余输出'],
    examples: [
      { input: 'a = 4, b = 5', output: '20' },
      { input: 'a = -3, b = 6', output: '-18' },
    ],
    testCases: [
      { id: 't1', label: '样例 1', setup: 'a = 4\nb = 5', expected: '20' },
      { id: 't2', label: '样例 2', setup: 'a = -3\nb = 6', expected: '-18' },
      { id: 't3', label: '隐藏', setup: 'a = 12\nb = 11', expected: '132' },
    ],
    starterCode: `# 输出 a * b\n`,
    runMode: 'stdout',
    hint: 'print(a * b)',
  },
]

/** @deprecated 使用 GLADIATOR_DUEL_QUESTIONS */
export const GLADIATOR_DUEL_QUESTION = GLADIATOR_DUEL_QUESTIONS[0]

export const RPS_STRATEGY_QUESTION: PythonTrialQuestion = {
  id: 'arena-rps-move',
  title: '代码攻防 · 出招策略',
  topic: '猜拳对决 · 策略代码',
  difficulty: '挑战',
  rewardXp: 60,
  durationMin: 10,
  tags: ['猜拳', '策略', 'stdout'],
  description:
    '编写 Python，输出 rock、paper 或 scissors 之一（小写）。系统会拿你的出招与对手策略多轮对战。',
  constraints: ['输出必须是 rock / paper / scissors', '仅一行输出', '禁止 input'],
  examples: [
    { input: '（无输入）', output: 'rock' },
    { input: '（无输入）', output: 'paper' },
  ],
  testCases: [
    {
      id: 't1',
      label: '合法出招',
      invoke: "str(__import__('sys').stdout.getvalue().strip().lower() in ('rock', 'paper', 'scissors'))",
      expected: 'True',
    },
  ],
  starterCode: `# 输出你的出招：rock / paper / scissors\nprint("rock")\n`,
  runMode: 'expression',
  hint: '可固定出招，或用 random.choice([...]) 干扰对手。',
}

const ALL_CLASS_ARENA_QUESTIONS = [
  ...CLASS_HARD_QUESTIONS,
  ...GLADIATOR_DUEL_QUESTIONS,
  RPS_STRATEGY_QUESTION,
]

export function getClassArenaQuestion(id: string) {
  return ALL_CLASS_ARENA_QUESTIONS.find((item) => item.id === id) ?? null
}

export function pickClassTrialQuestionId(trialId: number) {
  return CLASS_HARD_QUESTIONS[trialId % CLASS_HARD_QUESTIONS.length]?.id ?? CLASS_HARD_QUESTIONS[0].id
}

export function buildTrialWorkspaceQuestion(
  trialId: number,
  trialTitle: string,
): PythonTrialQuestion {
  const base = getClassArenaQuestion(pickClassTrialQuestionId(trialId))
  if (!base) throw new Error('未找到班级试炼题目')
  return {
    ...base,
    title: `${trialTitle} · ${base.title}`,
    description: `【教师试炼】${trialTitle}\n\n${base.description}`,
    tags: [...base.tags, '教师发布'],
  }
}
