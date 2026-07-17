import type { CustomTrialQuestion, TrialQuestionKind } from '../api/teacherTrials'

export type ComposerQuestionType =
  | 'single'
  | 'multiple'
  | 'true_false'
  | 'fill_blank'
  | 'short_answer'
  | 'coding'

export interface ComposerTestCase {
  id: string
  label: string
  setup?: string
  invoke?: string
  expected: string
}

export interface ComposerQuestion {
  uid: string
  type: ComposerQuestionType
  stem: string
  options: string[]
  correctIndex: number
  correctIndexes: number[]
  blankAnswers: string[]
  referenceAnswer: string
  analysis: string
  score: number
  difficulty: number
  knowledgeKey?: string
  starterCode: string
  runMode: 'stdout' | 'expression'
  hint: string
  testCases: ComposerTestCase[]
}

export const QUESTION_TYPE_LABELS: Record<ComposerQuestionType, string> = {
  single: '单选题',
  multiple: '多选题',
  true_false: '判断题',
  fill_blank: '填空题',
  short_answer: '简答题',
  coding: '编程题',
}

let seq = 0
export function nextComposerUid() {
  seq += 1
  return `q-${Date.now().toString(36)}-${seq}`
}

export function createComposerQuestion(
  type: ComposerQuestionType,
  knowledgeKey?: string,
): ComposerQuestion {
  const base: ComposerQuestion = {
    uid: nextComposerUid(),
    type,
    stem: '',
    options: ['', '', '', ''],
    correctIndex: 0,
    correctIndexes: [],
    blankAnswers: [''],
    referenceAnswer: '',
    analysis: '',
    score: 5,
    difficulty: 60,
    knowledgeKey,
    starterCode: '# 在此编写代码\n',
    runMode: 'stdout',
    hint: '',
    testCases: [{ id: 't1', label: '样例 1', expected: '' }],
  }
  if (type === 'true_false') {
    base.options = ['正确', '错误']
    base.correctIndex = 0
  }
  if (type === 'coding') {
    base.score = 10
  }
  return base
}

/** 将草稿/后端题目结构还原为编辑模型，便于编辑既有草稿。 */
export function composerQuestionsFromCustom(
  list: CustomTrialQuestion[],
  fallbackKey?: string,
): ComposerQuestion[] {
  return list.map((q) => {
    const kind = (q.question_type || 'mcq') as TrialQuestionKind
    const base = createComposerQuestion('single', q.knowledge_key || fallbackKey)
    base.stem = q.stem || ''
    base.analysis = q.analysis || ''
    base.score = typeof q.score === 'number' ? q.score : base.score
    base.difficulty = typeof q.difficulty === 'number' ? q.difficulty : base.difficulty
    base.knowledgeKey = q.knowledge_key || fallbackKey
    if (kind === 'coding') {
      base.type = 'coding'
      base.starterCode = q.starter_code || '# 在此编写代码\n'
      base.runMode = (q.run_mode as 'stdout' | 'expression') || 'stdout'
      base.hint = q.hint || ''
      base.testCases = (q.test_cases?.length
        ? q.test_cases.map((tc) => ({ ...tc }))
        : [{ id: 't1', label: '样例 1', expected: '' }]) as ComposerTestCase[]
      return base
    }
    if (kind === 'fill_blank') {
      base.type = 'fill_blank'
      base.blankAnswers = q.blanks?.length ? [...q.blanks] : ['']
      return base
    }
    if (kind === 'short_answer') {
      base.type = 'short_answer'
      base.referenceAnswer = q.reference_answer || ''
      return base
    }
    const options = q.options?.length ? [...q.options] : ['', '', '', '']
    base.options = options
    if (kind === 'multiple') {
      base.type = 'multiple'
      base.correctIndexes = q.correct_indexes?.length
        ? [...q.correct_indexes]
        : [q.correct_index ?? 0]
    } else if (kind === 'true_false' || (options.length === 2 && options[0] === '正确')) {
      base.type = 'true_false'
      base.options = options.length === 2 ? options : ['正确', '错误']
      base.correctIndex = q.correct_index ?? 0
    } else {
      base.type = 'single'
      base.correctIndex = q.correct_index ?? 0
    }
    return base
  })
}

/** 序列化为后端 custom_questions 结构；MCQ / 编程题与既有提交流程完全兼容。 */
export function serializeComposerQuestions(list: ComposerQuestion[]): CustomTrialQuestion[] {
  return list.map((q) => {
    const common = {
      stem: q.stem.trim(),
      knowledge_key: q.knowledgeKey,
      analysis: q.analysis || undefined,
      score: q.score,
      difficulty: q.difficulty,
    }
    if (q.type === 'coding') {
      return {
        ...common,
        question_type: 'coding' as const,
        starter_code: q.starterCode,
        run_mode: q.runMode,
        hint: q.hint || undefined,
        test_cases: q.testCases.map((tc) => ({ ...tc })),
      }
    }
    if (q.type === 'fill_blank') {
      return {
        ...common,
        question_type: 'fill_blank' as const,
        blanks: q.blankAnswers.filter((b) => b.trim().length > 0),
      }
    }
    if (q.type === 'short_answer') {
      return {
        ...common,
        question_type: 'short_answer' as const,
        reference_answer: q.referenceAnswer,
      }
    }
    if (q.type === 'multiple') {
      const indexes = [...q.correctIndexes].sort((a, b) => a - b)
      return {
        ...common,
        question_type: 'multiple' as const,
        options: [...q.options],
        correct_index: indexes[0] ?? 0,
        correct_indexes: indexes,
      }
    }
    return {
      ...common,
      question_type: q.type === 'true_false' ? ('true_false' as const) : ('mcq' as const),
      options: [...q.options],
      correct_index: q.correctIndex,
    }
  })
}
