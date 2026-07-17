import type { PythonTrialQuestion } from '../data/pythonTrialQuestions'
import type { StudentMistakeItem } from '../api/studentMistakes'
import { fetchStudentMistakes, submitCodeTrialRun } from '../api/studentMistakes'
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

export interface TrialAttemptRecord {
  questionId: string
  submittedAt: string
  durationMs: number
  passed: boolean
  failedCaseLabels: string[]
  errorReason: string | null
}

const ATTEMPT_PREFIX = 'plex:trial-attempts:'

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

function attemptStorageKey(userId: number | string) {
  return `${ATTEMPT_PREFIX}${userId}`
}

function readAttempts(userId: number | string): TrialAttemptRecord[] {
  try {
    const raw = localStorage.getItem(attemptStorageKey(userId))
    if (!raw) return []
    const parsed = JSON.parse(raw) as TrialAttemptRecord[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeAttempts(userId: number | string, records: TrialAttemptRecord[]) {
  localStorage.setItem(attemptStorageKey(userId), JSON.stringify(records.slice(0, 80)))
}

export function getTrialAttemptHistory(
  userId: number | string,
  questionId?: string,
): TrialAttemptRecord[] {
  const rows = readAttempts(userId).sort(
    (a, b) => new Date(b.submittedAt).getTime() - new Date(a.submittedAt).getTime(),
  )
  return questionId ? rows.filter((item) => item.questionId === questionId) : rows
}

function summarizeErrorReason(cases: TrialRunCaseSnapshot[]) {
  const failed = cases.filter((item) => !item.passed)
  if (!failed.length) return null
  const runtime = failed.find((item) => item.error)?.error
  if (runtime) return runtime
  return `未通过：${failed.map((item) => item.label).join('、')}`
}

export function recordTrialAttempt(
  userId: number | string,
  questionId: string,
  cases: TrialRunCaseSnapshot[],
  durationMs: number,
) {
  if (!cases.length) return
  const allPassed = cases.every((item) => item.passed)
  const failed = cases.filter((item) => !item.passed)
  const attempt: TrialAttemptRecord = {
    questionId,
    submittedAt: new Date().toISOString(),
    durationMs: Math.max(0, Math.round(durationMs)),
    passed: allPassed,
    failedCaseLabels: failed.map((item) => item.label),
    errorReason: summarizeErrorReason(cases),
  }
  const records = readAttempts(userId)
  records.unshift(attempt)
  writeAttempts(userId, records)
}

export function getTrialMistakeRecords(userId: number | string): TrialMistakeRecord[] {
  return readAll(userId).sort(
    (a, b) => new Date(b.lastFailedAt).getTime() - new Date(a.lastFailedAt).getTime(),
  )
}

export function mapServerMistakeToRecord(item: StudentMistakeItem): TrialMistakeRecord {
  const rawTypes: string[] = item.error_types?.length
    ? item.error_types
    : item.error_type
      ? [item.error_type]
      : []
  const normalized = rawTypes.map((t) =>
    t === 'wrong_answer' || t === 'wrong_output' ? 'wrong_output' : 'runtime_error',
  ) as TrialMistakeErrorType[]
  return {
    questionId: item.question_id || item.question_ref,
    questionTitle: item.question_title || item.question_ref,
    topic: item.topic || item.knowledge_label || '综合',
    tags: item.tags || [],
    starPathNodeId: item.star_path_node_id,
    starPathNodeTitle: item.star_path_node_title,
    failedCaseLabels: item.failed_case_labels || [],
    errorTypes: normalized.length ? normalized : ['wrong_output'],
    failCount: item.fail_count,
    lastFailedAt: item.last_failed_at,
    lastPassedAt: item.last_passed_at,
  }
}

export async function fetchServerMistakeRecords(userId: number | string): Promise<TrialMistakeRecord[]> {
  if (userId === 'guest') return getActiveMistakeRecords(userId)
  try {
    const data = await fetchStudentMistakes({ active_only: true })
    const server = data.items.map(mapServerMistakeToRecord)
    if (server.length) return server
  } catch {
    /* 离线回退 localStorage */
  }
  return getActiveMistakeRecords(userId)
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
  durationMs = 0,
) {
  if (!cases.length) return

  recordTrialAttempt(userId, question.id, cases, durationMs)

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
    const patch: TrialMistakeRecord = index >= 0
      ? { ...records[index], lastPassedAt: now }
      : {
          questionId: question.id,
          questionTitle: question.title,
          topic: question.topic,
          tags: question.tags,
          starPathNodeId: node?.id ?? null,
          starPathNodeTitle: nodeTitle,
          failedCaseLabels: [],
          errorTypes: [],
          failCount: 0,
          lastFailedAt: now,
          lastPassedAt: now,
        }
    if (index >= 0) {
      records[index] = patch
    } else {
      records.push(patch)
    }
    writeAll(userId, records)
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

  if (userId !== 'guest' && typeof userId === 'number') {
    const node = getStarPathNodeByQuestionId(question.id)
    void submitCodeTrialRun({
      question_id: question.id,
      question_title: question.title,
      knowledge_key: question.tags[0] || 'algo',
      topic: question.topic,
      tags: question.tags,
      star_path_node_id: node?.id ?? null,
      star_path_node_title: nodeTitle,
      cases,
    }).catch(() => undefined)
  }
}
