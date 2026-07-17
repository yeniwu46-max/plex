import type { PythonTestCase, PythonTrialQuestion } from '../data/pythonTrialQuestions'
import { getPythonTrialQuestion } from '../data/pythonTrialQuestions'
import { getStarPathKnowledgePoint, type StarPathKnowledgePoint } from '../data/starPathDomains'
import { MIN_QUESTIONS_PER_KP } from '../data/starPathKnowledgeTracks'
import { getCachedPracticeQuestionsForKey, getCachedPracticeQuestion } from './practiceQuestionCache'
import { normalizeQuestion } from './questionNaming'
import { wrapEpisodeNarrative } from './explorationNarrative'

const STORAGE_PREFIX = 'starpath-q:'

type QuestionTemplate = Omit<PythonTrialQuestion, 'id' | 'title' | 'topic' | 'tags' | 'description'> & {
  key: string
  titleSuffix: string
  topic: string
  tags: string[]
  /** 不含叙事包装的纯任务描述 */
  task: string
}

/** 从测试用例推导示例（输入/输出格式与 UI 一致） */
export function examplesFromTestCases(
  testCases: PythonTestCase[],
): { input: string; output: string }[] {
  const picked = testCases.slice(0, Math.min(3, testCases.length))
  return picked.map((tc) => {
    let input = '（无输入）'
    if (tc.setup) {
      input = tc.setup.replace(/\n/g, ', ').replace(/,\s*$/, '')
    } else if (tc.invoke) {
      input = tc.invoke.replace(/^str\(/, '').replace(/\)$/, '')
    }
    return { input, output: tc.expected }
  })
}

function enrichTemplate(template: QuestionTemplate): QuestionTemplate {
  const examples =
    template.examples?.length && !template.examples.some((e) => e.input.includes('由测试注入'))
      ? template.examples
      : examplesFromTestCases(template.testCases)
  const testCases =
    template.testCases.length >= 2
      ? template.testCases
      : [
          ...template.testCases,
          {
            id: 't-extra',
            label: '补充',
            setup: template.testCases[0]?.setup,
            invoke: template.testCases[0]?.invoke,
            expected: template.testCases[0]?.expected ?? '',
          },
        ]
  return { ...template, examples, testCases }
}

const TEMPLATE_REGISTRY: Record<string, QuestionTemplate> = Object.fromEntries(
  [
    {
      key: 'hello-greet',
      titleSuffix: '星际问候广播',
      topic: 'print 输出',
      tags: ['intro', 'print'],
      task: '使用 print() 输出 Hello, PLEX!（区分大小写）。',
      difficulty: '入门' as const,
      rewardXp: 28,
      durationMin: 8,
      constraints: ['使用 print 输出结果'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: '样例 1', expected: 'Hello, PLEX!' },
        { id: 't2', label: '样例 2', expected: 'Hello, PLEX!' },
      ],
      starterCode: '# 向宇宙发出第一束信号\n',
      hint: 'print("Hello, PLEX!")',
    },
    {
      key: 'name-greet',
      titleSuffix: '命名信标签名',
      topic: 'print 与变量',
      tags: ['print', 'var'],
      task: '变量 name 已写入探险队呼号，请输出 Hello, PLEX!。',
      difficulty: '入门' as const,
      rewardXp: 28,
      durationMin: 8,
      constraints: ['使用 print 输出结果'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: '样例 1', setup: 'name = "PLEX"', expected: 'Hello, PLEX!' },
        { id: 't2', label: '样例 2', setup: 'name = "Explorer"', expected: 'Hello, PLEX!' },
      ],
      starterCode: '# name 已给定\n',
      hint: 'print("Hello, PLEX!")',
    },
    {
      key: 'dual-beacon',
      titleSuffix: '双行信标信号',
      topic: 'print 多行',
      tags: ['print', '多行'],
      task: '依次输出 PLEX 与 Ready，两行之间不要空行。',
      difficulty: '入门' as const,
      rewardXp: 28,
      durationMin: 8,
      constraints: ['使用 print 输出结果'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: '样例 1', expected: 'PLEX\nReady' },
        { id: 't2', label: '样例 2', expected: 'PLEX\nReady' },
      ],
      starterCode: '# 输出两行信标\n',
      hint: '两次 print()',
    },
    {
      key: 'calc-power',
      titleSuffix: '算力表达式',
      topic: 'print 与表达式',
      tags: ['ops', '算术'],
      task: '请 print 输出 6 * 7 的计算结果（只输出数字）。',
      difficulty: '入门' as const,
      rewardXp: 28,
      durationMin: 8,
      constraints: ['使用 print 输出结果'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: '样例 1', expected: '42' },
        { id: 't2', label: '样例 2', expected: '42' },
      ],
      starterCode: '# 输出算力结果\n',
      hint: 'print(6 * 7)',
    },
    {
      key: 'energy-sum',
      titleSuffix: '能量读数求和',
      topic: '变量与算术',
      tags: ['var', 'print'],
      task: '计算 a 与 b 的和并用 print 输出（只输出数字）。',
      difficulty: '入门' as const,
      rewardXp: 28,
      durationMin: 8,
      constraints: ['使用 print 输出结果'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: '样例 1', setup: 'a = 4\nb = 6', expected: '10' },
        { id: 't2', label: '样例 2', setup: 'a = 15\nb = 27', expected: '42' },
        { id: 't3', label: '隐藏', setup: 'a = 100\nb = 234', expected: '334' },
      ],
      starterCode: '# a、b 已给定\n',
      hint: 'print(a + b)',
    },
    {
      key: 'var-product',
      titleSuffix: '变量乘积换算',
      topic: '变量与乘法',
      tags: ['var', '乘法'],
      task: '计算 a 与 b 的乘积并 print 输出总件数。',
      difficulty: '入门' as const,
      rewardXp: 28,
      durationMin: 8,
      constraints: ['使用 print 输出结果'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: '样例 1', setup: 'a = 4\nb = 5', expected: '20' },
        { id: 't2', label: '样例 2', setup: 'a = 7\nb = 8', expected: '56' },
      ],
      starterCode: '# a、b 已给定\n',
      hint: 'print(a * b)',
    },
    {
      key: 'var-diff',
      titleSuffix: '能量差值监测',
      topic: '减法运算',
      tags: ['ops', '减法'],
      task: '输出 a 与 b 的差值 a - b。',
      difficulty: '入门' as const,
      rewardXp: 28,
      durationMin: 8,
      constraints: ['使用 print 输出结果'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: '样例 1', setup: 'a = 10\nb = 3', expected: '7' },
        { id: 't2', label: '样例 2', setup: 'a = 2\nb = 8', expected: '-6' },
      ],
      starterCode: '# a、b 已给定\n',
      hint: 'print(a - b)',
    },
    {
      key: 'var-quotient',
      titleSuffix: '整除步数计算',
      topic: '整除运算',
      tags: ['ops', '整除'],
      task: '给定 a 与 b（b≠0），输出 a // b。',
      difficulty: '入门' as const,
      rewardXp: 28,
      durationMin: 8,
      constraints: ['使用 print 输出结果'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: '样例 1', setup: 'a = 17\nb = 5', expected: '3' },
        { id: 't2', label: '样例 2', setup: 'a = 20\nb = 4', expected: '5' },
      ],
      starterCode: '# a、b 已给定\n',
      hint: 'print(a // b)',
    },
    {
      key: 'ops-expr',
      titleSuffix: '表达式求值',
      topic: '运算符',
      tags: ['ops', '算术'],
      task: '输出 a + b 的结果（只输出数字）。',
      difficulty: '入门' as const,
      rewardXp: 28,
      durationMin: 8,
      constraints: ['使用 print 输出结果'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: '样例 1', setup: 'a = 3\nb = 4', expected: '7' },
        { id: 't2', label: '样例 2', setup: 'a = 12\nb = 30', expected: '42' },
      ],
      starterCode: '# a、b 已给定\n',
      hint: 'print(a + b)',
    },
    {
      key: 'if-parity',
      titleSuffix: '奇偶探测器',
      topic: '条件分支',
      tags: ['cond', '分支'],
      task: '若为偶数输出「偶数」，否则输出「奇数」。',
      difficulty: '基础' as const,
      rewardXp: 30,
      durationMin: 10,
      constraints: ['使用 if/else'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: '偶数', setup: 'n = 4', expected: '偶数' },
        { id: 't2', label: '奇数', setup: 'n = 7', expected: '奇数' },
        { id: 't3', label: '零', setup: 'n = 0', expected: '偶数' },
      ],
      starterCode: '# n 已给定\n',
      hint: 'n % 2 == 0',
    },
    {
      key: 'if-max',
      titleSuffix: '双信号取强',
      topic: '条件分支',
      tags: ['cond', '比较'],
      task: '输出 a 与 b 中的较大值，使用 if/else。',
      difficulty: '基础' as const,
      rewardXp: 30,
      durationMin: 10,
      constraints: ['使用 if/else'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: '样例 1', setup: 'a = 3\nb = 9', expected: '9' },
        { id: 't2', label: '样例 2', setup: 'a = 12\nb = 5', expected: '12' },
      ],
      starterCode: '# a、b 已给定\n',
      hint: 'if a >= b',
    },
    {
      key: 'if-pass',
      titleSuffix: '及格判定',
      topic: '条件分支',
      tags: ['cond', '比较'],
      task: '若 score >= 60 输出「及格」，否则输出「不及格」。',
      difficulty: '基础' as const,
      rewardXp: 30,
      durationMin: 10,
      constraints: ['使用 if/else'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: '及格', setup: 'score = 75', expected: '及格' },
        { id: 't2', label: '不及格', setup: 'score = 59', expected: '不及格' },
      ],
      starterCode: '# score 已给定\n',
      hint: 'if score >= 60',
    },
    {
      key: 'if-sign',
      titleSuffix: '正负零判别',
      topic: '条件分支',
      tags: ['cond', 'elif'],
      task: 'n>0 输出「正数」，n<0 输出「负数」，n=0 输出「零」。',
      difficulty: '基础' as const,
      rewardXp: 32,
      durationMin: 11,
      constraints: ['使用 if/elif/else'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: '负', setup: 'n = -3', expected: '负数' },
        { id: 't2', label: '正', setup: 'n = 5', expected: '正数' },
        { id: 't3', label: '零', setup: 'n = 0', expected: '零' },
      ],
      starterCode: '# n 已给定\n',
      hint: '先判断 n > 0',
    },
    {
      key: 'for-sum',
      titleSuffix: '星轨区间求和',
      topic: 'for 循环',
      tags: ['loop', '累加'],
      task: '给定正整数 n，用 for 循环输出 1 到 n 的和。',
      difficulty: '基础' as const,
      rewardXp: 32,
      durationMin: 11,
      constraints: ['使用 for 循环'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: 'n=5', setup: 'n = 5', expected: '15' },
        { id: 't2', label: 'n=10', setup: 'n = 10', expected: '55' },
      ],
      starterCode: '# n 已给定\n',
      hint: 'for i in range(1, n+1)',
    },
    {
      key: 'for-evens',
      titleSuffix: '偶数星体计数',
      topic: 'for 循环',
      tags: ['loop', '计数'],
      task: '统计 1..n 中偶数天体的个数并输出。',
      difficulty: '基础' as const,
      rewardXp: 34,
      durationMin: 12,
      constraints: ['使用 for 循环'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: 'n=6', setup: 'n = 6', expected: '3' },
        { id: 't2', label: 'n=10', setup: 'n = 10', expected: '5' },
      ],
      starterCode: '# n 已给定\n',
      hint: 'if i % 2 == 0: count += 1',
    },
    {
      key: 'for-factorial',
      titleSuffix: '阶乘引擎',
      topic: 'for 循环',
      tags: ['loop', '累乘'],
      task: '用 for 循环计算 n 的阶乘并输出。',
      difficulty: '基础' as const,
      rewardXp: 36,
      durationMin: 12,
      constraints: ['使用 for 循环'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: 'n=5', setup: 'n = 5', expected: '120' },
        { id: 't2', label: 'n=4', setup: 'n = 4', expected: '24' },
      ],
      starterCode: '# n 已给定\n',
      hint: 'result = 1，循环中 result *= i',
    },
    {
      key: 'for-mult',
      titleSuffix: '乘法星轨表',
      topic: 'range 循环',
      tags: ['range', '循环'],
      task: '输出一行 n*1 n*2 n*3 n*4 n*5，空格分隔。',
      difficulty: '基础' as const,
      rewardXp: 36,
      durationMin: 13,
      constraints: ['使用 for 循环'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: 'n=3', setup: 'n = 3', expected: '3 6 9 12 15' },
        { id: 't2', label: 'n=2', setup: 'n = 2', expected: '2 4 6 8 10' },
      ],
      starterCode: '# n 已给定\n',
      hint: 'for i in range(1, 6)',
    },
    {
      key: 'str-strip',
      titleSuffix: '电文去噪 strip',
      topic: '字符串',
      tags: ['str', 'strip'],
      task: '输出去掉首尾空格后的内容，使用 strip。',
      difficulty: '入门' as const,
      rewardXp: 28,
      durationMin: 8,
      constraints: ['使用 strip'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: '样例 1', setup: 's = " hello "', expected: 'hello' },
        { id: 't2', label: '样例 2', setup: 's = "  PLEX  "', expected: 'PLEX' },
      ],
      starterCode: '# s 已给定\n',
      hint: 's.strip()',
    },
    {
      key: 'list-max',
      titleSuffix: '样本峰值扫描',
      topic: '列表',
      tags: ['list', 'max'],
      task: '输出列表 nums 中的最大值。',
      difficulty: '基础' as const,
      rewardXp: 34,
      durationMin: 12,
      constraints: ['列表非空'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: '样例 1', setup: 'nums = [1, 3, 2]', expected: '3' },
        { id: 't2', label: '样例 2', setup: 'nums = [3, 9, 1]', expected: '9' },
      ],
      starterCode: '# nums 已给定\n',
      hint: 'max(nums)',
    },
    {
      key: 'list-min',
      titleSuffix: '样本谷值扫描',
      topic: '列表',
      tags: ['list', 'min'],
      task: '输出列表 nums 中的最小值。',
      difficulty: '基础' as const,
      rewardXp: 34,
      durationMin: 12,
      constraints: ['列表非空'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: '样例 1', setup: 'nums = [3, 9, 1]', expected: '1' },
        { id: 't2', label: '样例 2', setup: 'nums = [-2, 0, 5]', expected: '-2' },
      ],
      starterCode: '# nums 已给定\n',
      hint: 'min(nums)',
    },
    {
      key: 'list-sum-loop',
      titleSuffix: '样本总量统计',
      topic: '列表与循环',
      tags: ['list', '循环'],
      task: '用 for 循环求 nums 所有元素之和并输出。',
      difficulty: '基础' as const,
      rewardXp: 36,
      durationMin: 12,
      constraints: ['使用 for 循环'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: '样例 1', setup: 'nums = [1, 2, 3]', expected: '6' },
        { id: 't2', label: '样例 2', setup: 'nums = [10, -2, 5]', expected: '13' },
      ],
      starterCode: '# nums 已给定\n',
      hint: '循环累加',
    },
    {
      key: 'list-ends',
      titleSuffix: '首尾样本求和',
      topic: '列表索引',
      tags: ['list', '索引'],
      task: '输出 nums 第一个与最后一个元素之和。',
      difficulty: '基础' as const,
      rewardXp: 34,
      durationMin: 11,
      constraints: ['列表非空'],
      runMode: 'stdout' as const,
      testCases: [
        { id: 't1', label: '样例 1', setup: 'nums = [4, 7, 2, 9]', expected: '13' },
        { id: 't2', label: '样例 2', setup: 'nums = [5]', expected: '10' },
      ],
      starterCode: '# nums 已给定\n',
      hint: 'nums[0] + nums[-1]',
    },
    {
      key: 'count-positive',
      titleSuffix: '正数样本计数',
      topic: '列表统计',
      tags: ['list', 'dict'],
      task: '实现 count_positive(nums)，返回大于 0 的元素个数。',
      difficulty: '进阶' as const,
      rewardXp: 38,
      durationMin: 14,
      constraints: ['使用 for 循环'],
      runMode: 'expression' as const,
      testCases: [
        { id: 't1', label: '样例 1', invoke: 'str(count_positive([1, -2, 3, 0]))', expected: '2' },
        { id: 't2', label: '样例 2', invoke: 'str(count_positive([-1, -2]))', expected: '0' },
      ],
      starterCode: 'def count_positive(nums):\n    pass\n',
      hint: 'if x > 0: count += 1',
    },
    {
      key: 'rect-area',
      titleSuffix: '矩形星域面积',
      topic: '函数',
      tags: ['func', 'return'],
      task: '定义 rect_area(w, h) 返回宽×高。',
      difficulty: '进阶' as const,
      rewardXp: 36,
      durationMin: 14,
      constraints: ['定义函数并 return'],
      runMode: 'expression' as const,
      testCases: [
        { id: 't1', label: '样例 1', invoke: 'str(rect_area(4, 5))', expected: '20' },
        { id: 't2', label: '样例 2', invoke: 'str(rect_area(10, 3))', expected: '30' },
      ],
      starterCode: 'def rect_area(w, h):\n    pass\n',
      hint: 'return w * h',
    },
    {
      key: 'rect-perimeter',
      titleSuffix: '矩形周长星环',
      topic: '函数',
      tags: ['func', 'return'],
      task: '定义 rect_perimeter(w, h) 返回 2*(w+h)。',
      difficulty: '进阶' as const,
      rewardXp: 38,
      durationMin: 14,
      constraints: ['函数名必须正确'],
      runMode: 'expression' as const,
      testCases: [
        { id: 't1', label: '样例 1', invoke: 'str(rect_perimeter(4, 5))', expected: '18' },
        { id: 't2', label: '样例 2', invoke: 'str(rect_perimeter(3, 3))', expected: '12' },
      ],
      starterCode: 'def rect_perimeter(w, h):\n    pass\n',
      hint: 'return 2 * (w + h)',
    },
    {
      key: 'double',
      titleSuffix: '双倍增幅模块',
      topic: '函数',
      tags: ['func', 'return'],
      task: '定义 double(x) 返回 x 的两倍。',
      difficulty: '进阶' as const,
      rewardXp: 38,
      durationMin: 14,
      constraints: ['函数名 double'],
      runMode: 'expression' as const,
      testCases: [
        { id: 't1', label: '样例 1', invoke: 'str(double(3))', expected: '6' },
        { id: 't2', label: '样例 2', invoke: 'str(double(7))', expected: '14' },
      ],
      starterCode: 'def double(x):\n    pass\n',
      hint: 'return x * 2',
    },
    {
      key: 'max-two-func',
      titleSuffix: '双值择优函数',
      topic: '函数',
      tags: ['func', 'return'],
      task: '定义 max_two(a, b) 返回较大值。',
      difficulty: '进阶' as const,
      rewardXp: 40,
      durationMin: 15,
      constraints: ['函数名 max_two'],
      runMode: 'expression' as const,
      testCases: [
        { id: 't1', label: '样例 1', invoke: 'str(max_two(3, 9))', expected: '9' },
        { id: 't2', label: '样例 2', invoke: 'str(max_two(12, 5))', expected: '12' },
      ],
      starterCode: 'def max_two(a, b):\n    pass\n',
      hint: 'if a >= b: return a',
    },
    {
      key: 'list-total',
      titleSuffix: '星链样本聚合',
      topic: '函数与循环',
      tags: ['func', 'list'],
      task: '定义 list_total(nums)，用 for 循环返回元素之和。',
      difficulty: '进阶' as const,
      rewardXp: 42,
      durationMin: 16,
      constraints: ['函数名 list_total', '使用 for'],
      runMode: 'expression' as const,
      testCases: [
        { id: 't1', label: '样例 1', invoke: 'str(list_total([1, 2, 3]))', expected: '6' },
        { id: 't2', label: '样例 2', invoke: 'str(list_total([10, -2, 5]))', expected: '13' },
      ],
      starterCode: 'def list_total(nums):\n    pass\n',
      hint: '循环累加后 return',
    },
    {
      key: 'sum-range',
      titleSuffix: '区间求和',
      topic: '函数与循环',
      tags: ['func', '循环'],
      task: '定义 sum_range(a, b)，返回 a 到 b（含）所有整数之和。',
      difficulty: '进阶' as const,
      rewardXp: 44,
      durationMin: 17,
      constraints: ['函数名 sum_range', '使用 for 循环'],
      runMode: 'expression' as const,
      testCases: [
        { id: 't1', label: '样例 1', invoke: 'str(sum_range(1, 5))', expected: '15' },
        { id: 't2', label: '样例 2', invoke: 'str(sum_range(4, 4))', expected: '4' },
      ],
      starterCode: 'def sum_range(a, b):\n    pass\n',
      hint: 'for i in range(a, b + 1)',
    },
    {
      key: 'bubble-sort',
      titleSuffix: '冒泡升序排列',
      topic: '冒泡排序',
      tags: ['排序', '算法'],
      task: '实现 bubble_sort(nums)，返回升序新列表。',
      difficulty: '进阶' as const,
      rewardXp: 40,
      durationMin: 16,
      constraints: ['函数名 bubble_sort'],
      runMode: 'expression' as const,
      testCases: [
        { id: 't1', label: '样例 1', invoke: 'str(bubble_sort([3, 1, 2]))', expected: '[1, 2, 3]' },
        { id: 't2', label: '样例 2', invoke: 'str(bubble_sort([5, 4, 3, 2, 1]))', expected: '[1, 2, 3, 4, 5]' },
      ],
      starterCode: 'def bubble_sort(nums):\n    pass\n',
      hint: '相邻比较交换',
    },
    {
      key: 'bubble-pass',
      titleSuffix: '冒泡一轮',
      topic: '冒泡排序',
      tags: ['排序', '列表'],
      task: '实现 bubble_pass(nums)，执行一轮冒泡后返回列表。',
      difficulty: '基础' as const,
      rewardXp: 40,
      durationMin: 15,
      constraints: ['函数名 bubble_pass'],
      runMode: 'expression' as const,
      testCases: [
        { id: 't1', label: '样例 1', invoke: 'str(bubble_pass([3, 1, 2]))', expected: '[1, 2, 3]' },
        { id: 't2', label: '样例 2', invoke: 'str(bubble_pass([1, 2, 3]))', expected: '[1, 2, 3]' },
      ],
      starterCode: 'def bubble_pass(nums):\n    pass\n',
      hint: '内层循环到 len(nums)-1',
    },
    {
      key: 'bubble-swaps',
      titleSuffix: '冒泡交换次数',
      topic: '冒泡排序',
      tags: ['排序', '计数'],
      task: '实现 count_bubble_swaps(nums)，统计冒泡排序中的交换次数。',
      difficulty: '进阶' as const,
      rewardXp: 44,
      durationMin: 18,
      constraints: ['函数名 count_bubble_swaps'],
      runMode: 'expression' as const,
      testCases: [
        { id: 't1', label: '样例 1', invoke: 'str(count_bubble_swaps([3, 1, 2]))', expected: '2' },
        { id: 't2', label: '样例 2', invoke: 'str(count_bubble_swaps([1, 2, 3]))', expected: '0' },
      ],
      starterCode: 'def count_bubble_swaps(nums):\n    pass\n',
      hint: '每次交换 swaps += 1',
    },
    {
      key: 'selection-sort',
      titleSuffix: '选择升序排列',
      topic: '选择排序',
      tags: ['排序', '算法'],
      task: '实现 selection_sort(nums)，返回升序新列表。',
      difficulty: '进阶' as const,
      rewardXp: 40,
      durationMin: 16,
      constraints: ['函数名 selection_sort'],
      runMode: 'expression' as const,
      testCases: [
        { id: 't1', label: '样例 1', invoke: 'str(selection_sort([4, 2, 3]))', expected: '[2, 3, 4]' },
        { id: 't2', label: '样例 2', invoke: 'str(selection_sort([3, 2, 1]))', expected: '[1, 2, 3]' },
      ],
      starterCode: 'def selection_sort(nums):\n    pass\n',
      hint: '每轮找最小放前面',
    },
    {
      key: 'selection-min-index',
      titleSuffix: '最小索引',
      topic: '选择排序',
      tags: ['排序', '索引'],
      task: '实现 min_index(nums, start)，返回 start 到末尾最小元素索引。',
      difficulty: '基础' as const,
      rewardXp: 38,
      durationMin: 14,
      constraints: ['函数名 min_index'],
      runMode: 'expression' as const,
      testCases: [
        { id: 't1', label: '样例 1', invoke: 'str(min_index([5, 2, 8, 1], 1))', expected: '3' },
        { id: 't2', label: '样例 2', invoke: 'str(min_index([3, 1, 2], 0))', expected: '1' },
      ],
      starterCode: 'def min_index(nums, start):\n    pass\n',
      hint: '从 start 遍历找最小值索引',
    },
    {
      key: 'selection-step',
      titleSuffix: '选择一步',
      topic: '选择排序',
      tags: ['排序', '交换'],
      task: '实现 selection_step(nums, i)，将 i 到末尾最小元素交换到 i，返回 nums。',
      difficulty: '基础' as const,
      rewardXp: 40,
      durationMin: 15,
      constraints: ['函数名 selection_step'],
      runMode: 'expression' as const,
      testCases: [
        { id: 't1', label: '样例 1', invoke: 'str(selection_step([4, 2, 3], 0))', expected: '[2, 4, 3]' },
        { id: 't2', label: '样例 2', invoke: 'str(selection_step([2, 4, 3], 1))', expected: '[2, 3, 4]' },
      ],
      starterCode: 'def selection_step(nums, i):\n    pass\n',
      hint: '先找 min_index 再交换',
    },
    {
      key: 'binary-search',
      titleSuffix: '二分目标定位',
      topic: '二分查找',
      tags: ['查找', '算法'],
      task: '实现 binary_search(nums, target)，找到返回索引，否则 -1。',
      difficulty: '进阶' as const,
      rewardXp: 44,
      durationMin: 18,
      constraints: ['函数名 binary_search'],
      runMode: 'expression' as const,
      testCases: [
        { id: 't1', label: '命中', invoke: 'str(binary_search([1, 3, 5, 7], 5))', expected: '2' },
        { id: 't2', label: '未命中', invoke: 'str(binary_search([1, 3, 5, 7], 4))', expected: '-1' },
      ],
      starterCode: 'def binary_search(nums, target):\n    pass\n',
      hint: '维护 left、right、mid',
    },
    {
      key: 'binary-check',
      titleSuffix: '二分判定',
      topic: '二分查找',
      tags: ['查找', '算法'],
      task: '实现 contains_sorted(nums, target)，包含输出 yes，否则 no。',
      difficulty: '基础' as const,
      rewardXp: 42,
      durationMin: 16,
      constraints: ['函数名 contains_sorted'],
      runMode: 'expression' as const,
      testCases: [
        { id: 't1', label: '存在', invoke: 'contains_sorted([1, 4, 9], 4)', expected: 'yes' },
        { id: 't2', label: '不存在', invoke: 'contains_sorted([1, 4, 9], 3)', expected: 'no' },
      ],
      starterCode: 'def contains_sorted(nums, target):\n    pass\n',
      hint: '可调用 binary_search 或自行二分',
    },
    {
      key: 'binary-first',
      titleSuffix: '首次出现',
      topic: '二分查找',
      tags: ['查找', '边界'],
      task: '实现 first_ge(nums, x)，返回第一个大于等于 x 的索引；不存在返回 len(nums)。',
      difficulty: '进阶' as const,
      rewardXp: 46,
      durationMin: 18,
      constraints: ['函数名 first_ge'],
      runMode: 'expression' as const,
      testCases: [
        { id: 't1', label: '样例 1', invoke: 'str(first_ge([1, 3, 3, 5], 3))', expected: '1' },
        { id: 't2', label: '样例 2', invoke: 'str(first_ge([1, 2, 3], 10))', expected: '3' },
      ],
      starterCode: 'def first_ge(nums, x):\n    pass\n',
      hint: '二分找左边界',
    },
  ].map((t) => [t.key, enrichTemplate(t as QuestionTemplate)]),
)

/** 每个知识点 5 个槽位对应的题目模板（保证各不相同） */
const KP_TEMPLATE_PLANS: Record<string, string[]> = {
  'stage1-intro': ['hello-greet', 'dual-beacon', 'calc-power', 'name-greet', 'energy-sum'],
  'stage1-comment': ['name-greet', 'hello-greet', 'dual-beacon', 'calc-power', 'energy-sum'],
  'stage1-var': ['energy-sum', 'var-product', 'var-diff', 'var-quotient', 'ops-expr'],
  'stage1-io': ['var-product', 'var-quotient', 'energy-sum', 'var-diff', 'calc-power'],
  'stage2-ops': ['ops-expr', 'calc-power', 'var-quotient', 'var-diff', 'energy-sum'],
  'stage2-cond': ['if-parity', 'if-max', 'if-pass', 'if-sign', 'if-parity'],
  'stage2-loop': ['for-sum', 'for-evens', 'for-factorial', 'for-mult', 'for-evens'],
  'stage2-range': ['for-mult', 'for-sum', 'for-evens', 'for-factorial', 'for-sum'],
  'stage3-str': ['str-strip', 'dual-beacon', 'hello-greet', 'calc-power', 'name-greet'],
  'stage3-list': ['list-max', 'list-min', 'list-sum-loop', 'list-ends', 'list-total'],
  'stage3-dict': ['list-sum-loop', 'list-ends', 'count-positive', 'list-max', 'list-min'],
  'stage3-func': ['rect-area', 'rect-perimeter', 'double', 'max-two-func', 'list-total'],
  'stage4-algo-sum': ['list-sum-loop', 'count-positive', 'for-sum', 'list-total', 'sum-range'],
  'stage4-bubble': ['bubble-sort', 'bubble-pass', 'bubble-swaps', 'bubble-pass', 'bubble-sort'],
  'stage4-selection': ['selection-sort', 'selection-min-index', 'selection-step', 'selection-step', 'selection-sort'],
  'stage4-binary': ['binary-search', 'binary-check', 'binary-first', 'binary-check', 'binary-search'],
}

const DOMAIN_FALLBACK_PLANS: Record<string, string[]> = {
  'data-vars': ['hello-greet', 'dual-beacon', 'calc-power', 'name-greet', 'energy-sum'],
  operators: ['ops-expr', 'calc-power', 'var-quotient', 'var-diff', 'energy-sum'],
  'flow-control': ['if-parity', 'if-max', 'for-sum', 'for-evens', 'for-mult'],
  strings: ['str-strip', 'dual-beacon', 'hello-greet', 'calc-power', 'name-greet'],
  'lists-dicts': ['list-max', 'list-min', 'list-sum-loop', 'list-ends', 'count-positive'],
  functions: ['rect-area', 'rect-perimeter', 'double', 'max-two-func', 'list-total'],
  'recursion-iter': ['list-sum-loop', 'bubble-sort', 'selection-sort', 'binary-search', 'count-positive'],
}

const GEN_SLOT_RE = /^gen-(.+)-s(\d+)$/
const GEN_LEGACY_RE = /^gen-(.+)-v(\d+)$/

function planForKnowledgePoint(kp: StarPathKnowledgePoint): string[] {
  return (
    KP_TEMPLATE_PLANS[kp.id] ??
    DOMAIN_FALLBACK_PLANS[kp.domainKey] ??
    DOMAIN_FALLBACK_PLANS['data-vars']!
  )
}

export function generatedQuestionId(kpId: string, slot: number): string {
  return `gen-${kpId}-s${slot}`
}

export function getQuestionIdsForKnowledgePoint(kpId: string): string[] {
  return Array.from({ length: MIN_QUESTIONS_PER_KP }, (_, i) => generatedQuestionId(kpId, i))
}

function buildFromTemplate(
  kp: StarPathKnowledgePoint,
  template: QuestionTemplate,
  slot: number,
): PythonTrialQuestion {
  const enriched = enrichTemplate(template)
  return {
    id: generatedQuestionId(kp.id, slot),
    title: enriched.titleSuffix,
    topic: enriched.topic,
    difficulty: enriched.difficulty,
    rewardXp: enriched.rewardXp,
    durationMin: enriched.durationMin,
    tags: [...enriched.tags, ...kp.tags.slice(0, 2)],
    description: wrapEpisodeNarrative(kp.id, kp.domainKey, slot, enriched.task),
    constraints: enriched.constraints,
    examples: enriched.examples,
    testCases: enriched.testCases,
    starterCode: enriched.starterCode,
    runMode: enriched.runMode,
    hint: enriched.hint,
  }
}

export function generateQuestionForSlot(kp: StarPathKnowledgePoint, slot: number): PythonTrialQuestion {
  const plan = planForKnowledgePoint(kp)
  const templateKey = plan[slot] ?? plan[slot % plan.length]!
  const template = TEMPLATE_REGISTRY[templateKey] ?? TEMPLATE_REGISTRY['hello-greet']!
  return normalizeQuestion(buildFromTemplate(kp, template, slot))
}

export function generateQuestionsForKnowledgePoint(kp: StarPathKnowledgePoint): PythonTrialQuestion[] {
  return Array.from({ length: MIN_QUESTIONS_PER_KP }, (_, slot) => generateQuestionForSlot(kp, slot))
}

export function generateStarPathQuestion(kp: StarPathKnowledgePoint, reroll = false): PythonTrialQuestion {
  const cacheKey = STORAGE_PREFIX + kp.id

  if (!reroll && typeof sessionStorage !== 'undefined') {
    const cached = sessionStorage.getItem(cacheKey)
    if (cached) {
      try {
        return normalizeQuestion(JSON.parse(cached) as PythonTrialQuestion)
      } catch {
        sessionStorage.removeItem(cacheKey)
      }
    }
  }

  const slot = reroll ? Math.floor(Date.now() / 1000) % MIN_QUESTIONS_PER_KP : 0
  const question = generateQuestionForSlot(kp, slot)

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

function parseGeneratedQuestionRef(
  questionId: string,
  kp?: StarPathKnowledgePoint | null,
): { kpId: string; slot: number } | null {
  const slotMatch = GEN_SLOT_RE.exec(questionId)
  if (slotMatch) {
    return { kpId: slotMatch[1]!, slot: Number(slotMatch[2]) }
  }
  const legacyMatch = GEN_LEGACY_RE.exec(questionId)
  if (legacyMatch) {
    return { kpId: legacyMatch[1]!, slot: Number(legacyMatch[2]) % MIN_QUESTIONS_PER_KP }
  }
  if (kp) {
    const plan = planForKnowledgePoint(kp)
    const index = plan.indexOf(questionId)
    if (index >= 0) return { kpId: kp.id, slot: index }
  }
  return null
}

export function resolveStarPathQuestion(
  kp: StarPathKnowledgePoint,
  options?: { reroll?: boolean; slot?: number },
): PythonTrialQuestion | null {
  if (options?.slot != null) {
    return generateQuestionForSlot(kp, options.slot)
  }

  for (const tag of kp.tags) {
    const imported = getCachedPracticeQuestionsForKey(tag)
    if (imported.length >= MIN_QUESTIONS_PER_KP) {
      if (options?.reroll) {
        return imported[Math.floor(Math.random() * imported.length)] ?? imported[0]
      }
      return imported[0]
    }
  }
  const knowledgeKey = kp.tags[0]
  if (knowledgeKey) {
    const imported = getCachedPracticeQuestionsForKey(knowledgeKey)
    if (imported.length >= MIN_QUESTIONS_PER_KP) {
      if (options?.reroll) {
        return imported[Math.floor(Math.random() * imported.length)] ?? imported[0]
      }
      return imported[0]
    }
  }
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
  const cached = getCachedPracticeQuestion(questionId)
  if (cached) return cached

  const parsed = parseGeneratedQuestionRef(questionId, kp)
  if (parsed) {
    const point = kp ?? getStarPathKnowledgePoint(parsed.kpId)?.point ?? null
    if (point) return generateQuestionForSlot(point, parsed.slot)
  }

  const staticQ = getPythonTrialQuestion(questionId)
  if (staticQ) return staticQ

  if (kp && typeof sessionStorage !== 'undefined') {
    const cachedRaw = sessionStorage.getItem(STORAGE_PREFIX + kp.id)
    if (cachedRaw) {
      try {
        const parsedCache = JSON.parse(cachedRaw) as PythonTrialQuestion
        if (parsedCache.id === questionId) return parsedCache
      } catch {
        sessionStorage.removeItem(STORAGE_PREFIX + kp.id)
      }
    }
  }
  if (kp) return generateQuestionForSlot(kp, 0)
  return null
}
