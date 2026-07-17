import type { PythonTestCase } from '../data/pythonTrialQuestions'

/** 去除 Markdown 星号、标题与嵌入的测试样例块 */
export function stripMarkdownAsterisks(text: string): string {
  return (text || '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*\n]+)\*/g, '$1')
    .replace(/\{\[([^\]]*)\]\}/g, '$1')
    .trim()
}

const EMBEDDED_TEST_BLOCK =
  /(?:^|\n)\s*#{1,3}\s*测试样例[\s\S]*?(?=\n\s*#{1,3}\s|\n\s*要求|\n\s*提示|$)/gi

const INLINE_IO_PATTERN =
  /(?:输入数据|输入)\s*[:：]?\s*([\s\S]+?)\s*(?:输出结果|输出)\s*[:：]?\s*([^\n#]+)/gi

function parseInlineIoPairs(text: string): Array<{ input: string; output: string }> {
  const examples: Array<{ input: string; output: string }> = []
  let match: RegExpExecArray | null
  const re = new RegExp(INLINE_IO_PATTERN.source, 'gi')
  while ((match = re.exec(text)) !== null) {
    examples.push({
      input: match[1]?.trim() || '（无输入）',
      output: match[2]?.trim() || '',
    })
  }
  return examples
}

export function extractEmbeddedTests(text: string): {
  stem: string
  examples: Array<{ input: string; output: string }>
  testCases: PythonTestCase[]
} {
  let stem = stripMarkdownAsterisks(text)
  const examples: Array<{ input: string; output: string }> = []
  const testCases: PythonTestCase[] = []

  const inlineExamples = parseInlineIoPairs(stem)
  if (inlineExamples.length) {
    examples.push(...inlineExamples)
    stem = stem.replace(INLINE_IO_PATTERN, '')
  }

  stem = stem.replace(EMBEDDED_TEST_BLOCK, '\n')

  stem = stem
    .replace(/(?:^|\n)\s*#{1,6}\s[^\n]*/g, '\n')
    .replace(/那个兔子又对你说：[^\n]*/g, '')
    .replace(/兔子期末考试[^\n]*/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()

  examples.forEach((ex, index) => {
    testCases.push({
      id: `embedded-${index + 1}`,
      label: `样例 ${index + 1}`,
      setup: ex.input === '（无输入）' ? undefined : ex.input.replace(/,/g, '\n'),
      expected: ex.output,
    })
  })

  return { stem, examples, testCases }
}

export function sanitizeQuestionContent<
  T extends {
    description: string
    examples?: Array<{ input: string; output: string }>
    testCases?: PythonTestCase[]
  },
>(question: T): T {
  const { stem, examples, testCases } = extractEmbeddedTests(question.description)
  const mergedExamples =
    question.examples?.length && !question.examples.every((e) => !e.input && !e.output)
      ? question.examples.map((e) => ({
          input: stripMarkdownAsterisks(e.input),
          output: stripMarkdownAsterisks(e.output),
        }))
      : examples

  const mergedTests =
    question.testCases?.length && question.testCases.some((t) => t.expected)
      ? question.testCases
      : testCases.length
        ? testCases
        : question.testCases

  return {
    ...question,
    description: stem,
    examples: mergedExamples,
    testCases: mergedTests ?? [],
  }
}
