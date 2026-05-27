import { getPythonTrialQuestion } from '../data/pythonTrialQuestions'
import { getStarPathNodeByQuestionId, getUnlockedStarPathNodes } from '../data/starPathTrail'
import type { TrialMistakeErrorType, TrialMistakeRecord } from './trialMistakeLog'

const STORAGE_PREFIX = 'plex:mock-mistakes:'

const CASE_LABEL_POOL = ['样例 1', '样例 2', '隐藏用例', '边界用例', '基础输出']

function seededRandom(seed: number) {
  let state = Math.abs(Math.floor(seed)) % 2147483646 || 1
  return () => {
    state = (state * 16807) % 2147483647
    return (state - 1) / 2147483646
  }
}

function hashUserId(userId: number | string) {
  const text = String(userId)
  let hash = 0
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash << 5) - hash + text.charCodeAt(i)
    hash |= 0
  }
  return Math.abs(hash) || 1
}

function pickErrorTypes(rand: () => number): TrialMistakeErrorType[] {
  const roll = rand()
  if (roll < 0.35) return ['runtime_error']
  if (roll < 0.7) return ['wrong_output']
  return ['wrong_output', 'runtime_error']
}

function generateMockMistakes(userId: number | string): TrialMistakeRecord[] {
  const rand = seededRandom(hashUserId(userId))
  const questionIds = new Set<string>()

  for (const node of getUnlockedStarPathNodes()) {
    for (const qid of node.questionIds) {
      questionIds.add(qid)
    }
  }

  const pool = [...questionIds]
  if (!pool.length) return []

  const mistakeCount = Math.min(pool.length, 2 + Math.floor(rand() * 3))
  const records: TrialMistakeRecord[] = []
  const now = Date.now()

  for (let i = 0; i < mistakeCount && pool.length; i += 1) {
    const index = Math.floor(rand() * pool.length)
    const questionId = pool.splice(index, 1)[0]!
    const question = getPythonTrialQuestion(questionId)
    if (!question) continue

    const node = getStarPathNodeByQuestionId(questionId)
    const failCount = 1 + Math.floor(rand() * 4)
    const caseCount = 1 + Math.floor(rand() * 3)
    const failedCaseLabels = CASE_LABEL_POOL.slice(0, caseCount)
    const hoursAgo = Math.floor(rand() * 72)

    records.push({
      questionId,
      questionTitle: question.title,
      topic: question.topic,
      tags: question.tags,
      starPathNodeId: node?.id ?? null,
      starPathNodeTitle: node
        ? node.titleLine2
          ? `${node.title}${node.titleLine2}`
          : node.title
        : null,
      failedCaseLabels,
      errorTypes: pickErrorTypes(rand),
      failCount,
      lastFailedAt: new Date(now - hoursAgo * 60 * 60 * 1000).toISOString(),
      lastPassedAt: null,
    })
  }

  return records.sort(
    (a, b) => new Date(b.lastFailedAt).getTime() - new Date(a.lastFailedAt).getTime(),
  )
}

function readMockMistakes(userId: number | string): TrialMistakeRecord[] {
  const key = `${STORAGE_PREFIX}${userId}`
  try {
    const raw = localStorage.getItem(key)
    if (raw) {
      const parsed = JSON.parse(raw) as TrialMistakeRecord[]
      if (Array.isArray(parsed)) return parsed
    }
  } catch {
    /* 重新生成 */
  }
  const generated = generateMockMistakes(userId)
  localStorage.setItem(key, JSON.stringify(generated))
  return generated
}

/** 获取该学生的模拟错题（首次按账号种子随机生成并保存） */
export function getStudentMockMistakes(userId: number | string): TrialMistakeRecord[] {
  return readMockMistakes(userId)
}

/** 真实错题优先，其余用模拟错题补全 */
export function mergeMistakesForRecommendation(
  userId: number | string,
  realMistakes: TrialMistakeRecord[],
): TrialMistakeRecord[] {
  const mock = getStudentMockMistakes(userId)
  const realIds = new Set(realMistakes.map((item) => item.questionId))
  const merged = [...realMistakes, ...mock.filter((item) => !realIds.has(item.questionId))]
  return merged.sort(
    (a, b) => new Date(b.lastFailedAt).getTime() - new Date(a.lastFailedAt).getTime(),
  )
}

export function filterMistakesByQuestionIds(
  records: TrialMistakeRecord[],
  questionIds: string[],
) {
  const set = new Set(questionIds)
  return records.filter((item) => set.has(item.questionId))
}
