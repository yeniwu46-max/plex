import {
  labelForModuleCategory,
  resolveModuleCategory,
  type ModuleCategoryValue,
} from '../data/moduleCategories'
import type { StudentMistakeItem } from '../api/studentMistakes'

export type ReviewAnswerValue = 0 | 1 | 2

export interface Sm2ReviewQuestion {
  id: string
  text: string
}

export interface Sm2QuestionnaireAnswer {
  question_id: string
  value: ReviewAnswerValue
}

const CATEGORY_FOCUS: Record<ModuleCategoryValue, string[]> = {
  'lang-basics': ['变量与数据类型', '输入输出与注释', '基本语法规则'],
  sequence: ['语句顺序', '赋值与表达式', '输出格式'],
  branch: ['条件判断', '分支覆盖', '边界情况'],
  loop: ['循环条件', '循环体更新', '终止条件'],
  array: ['下标与长度', '遍历方式', '越界风险'],
  string: ['索引与切片', '常用操作', '格式化输出'],
  function: ['参数与返回值', '调用方式', '递归终止'],
  search: ['查找思路', '复杂度直觉', '边界处理'],
  other: ['题意理解', '关键步骤', '常见易错点'],
}

export function buildSm2ReviewQuestions(item: StudentMistakeItem): Sm2ReviewQuestion[] {
  const category = resolveModuleCategory(item.knowledge_key)
  const theme = labelForModuleCategory(category)
  const label = item.knowledge_label || theme
  const focus = CATEGORY_FOCUS[category]
  const titleHint = item.question_title ? `「${item.question_title}」` : '这道错题'

  return [
    { id: 'concept', text: `你是否清楚 ${label} 在本题中的考查重点？` },
    { id: 'steps', text: `你能否按正确顺序回忆 ${titleHint} 的解题步骤？` },
    { id: 'focus_a', text: `关于${focus[0]}，你现在的掌握程度如何？` },
    { id: 'focus_b', text: `关于${focus[1]}，你现在的掌握程度如何？` },
    { id: 'transfer', text: `遇到同类${theme}题目时，你有信心独立做对吗？` },
  ]
}

export function computeSm2QualityFromAnswers(answers: Sm2QuestionnaireAnswer[]): number {
  if (!answers.length) return 0
  const values = answers.map((row) => row.value).filter((v) => v === 0 || v === 1 || v === 2)
  if (!values.length) return 0
  const avg = values.reduce<number>((sum, v) => sum + v, 0) / (values.length * 2)
  return Math.max(0, Math.min(5, Math.round(avg * 5)))
}

export function isSm2QuestionnaireComplete(
  questions: Sm2ReviewQuestion[],
  answers: Record<string, ReviewAnswerValue | undefined>,
): boolean {
  return questions.every((q) => answers[q.id] === 0 || answers[q.id] === 1 || answers[q.id] === 2)
}

export const REVIEW_ANSWER_OPTIONS: Array<{ label: string; value: ReviewAnswerValue }> = [
  { label: '不清楚', value: 0 },
  { label: '部分清楚', value: 1 },
  { label: '清楚', value: 2 },
]
