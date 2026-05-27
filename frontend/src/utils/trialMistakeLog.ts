import type { PythonTrialQuestion } from '../data/pythonTrialQuestions'
import { getStarPathNodeByQuestionId } from '../data/starPathTrail'

const STORAGE_PREFIX = 'plex:trial-mistakes:'

export type TrialMistakeErrorType = 'wrong_output' | 'runtime_error'

export interface TrialMistakeRecord {
  questionId: string
  questionTitle: string
  topic: string
  tags: string[]
  starPathNodeId: string | null
  starPathNodeTitle: string | null
  failedCaseLabels: string[]
  errorTypes: TrialMistakeErrorType[]
  failCount: number
  lastFailedAt: string
  lastPassedAt: string | null
}

export interface TrialRunCaseSnapshot {
  label: string
  passed: boolean
  error?: string
}

function storageKey(userId: number | string) {
  return `${STORAGE_PREFIX}${userId}`
}

function readAll(userId: number | string): TrialMistakeRecord[] {
  try {
    const raw = localStorage.getItem(storageKey(userId))
    if (!raw) return []
    const parsed = JSON.parse(raw) as TrialMistakeRecord[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeAll(userId: number | string, records: TrialMistakeRecord[]) {
  localStorage.setItem(storageKey(userId), JSON.stringify(records))
}

export function getTrialMistakeRecords(userId: number | string): TrialMistakeRecord[] {
  return readAll(userId).sort(
    (a, b) => new Date(b.lastFailedAt).getTime() - new Date(a.lastFailedAt).getTime(),
  )
}

export function getActiveMistakeRecords(userId: number | string): TrialMistakeRecord[] {
  const now = Date.now()
  const sevenDays = 7 * 24 * 60 * 60 * 1000
  return getTrialMistakeRecords(userId).filter((record) => {
    if (!record.lastPassedAt) return true
    const failedAt = new Date(record.lastFailedAt).getTime()
    const passedAt = new Date(record.lastPassedAt).getTime()
    if (passedAt > failedAt) return false
    return now - failedAt < sevenDays
  })
}

export function recordTrialRun(
  userId: number | string,
  question: PythonTrialQuestion,
  cases: TrialRunCaseSnapshot[],
) {
  if (!cases.length) return

  const allPassed = cases.every((item) => item.passed)
  const failed = cases.filter((item) => !item.passed)
  const now = new Date().toISOString()
  const node = getStarPathNodeByQuestionId(question.id)
  const nodeTitle = node
    ? node.titleLine2
      ? `${node.title}${node.titleLine2}`
      : node.title
    : null

  const records = readAll(userId)
  const index = records.findIndex((item) => item.questionId === question.id)

  if (allPassed) {
    if (index >= 0) {
      records[index] = { ...records[index], lastPassedAt: now }
      writeAll(userId, records)
    }
    return
  }

  const errorTypes: TrialMistakeErrorType[] = []
  if (failed.some((item) => item.error)) errorTypes.push('runtime_error')
  if (failed.some((item) => !item.error)) errorTypes.push('wrong_output')

  const patch: TrialMistakeRecord = {
    questionId: question.id,
    questionTitle: question.title,
    topic: question.topic,
    tags: question.tags,
    starPathNodeId: node?.id ?? null,
    starPathNodeTitle: nodeTitle,
    failedCaseLabels: failed.map((item) => item.label),
    errorTypes: [...new Set(errorTypes)],
    failCount: (index >= 0 ? records[index].failCount : 0) + 1,
    lastFailedAt: now,
    lastPassedAt: index >= 0 ? records[index].lastPassedAt : null,
  }

  if (index >= 0) {
    records[index] = patch
  } else {
    records.push(patch)
  }
  writeAll(userId, records)
}
