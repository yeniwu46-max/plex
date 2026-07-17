import type { TrialMistakeRecord } from './trialMistakeLog'
import { MASTERY_THRESHOLD, DOMAIN_UNLOCK_PROGRESS, NODE_UNLOCK_MIN_AC } from '../constants/starPathUnlock'

/** 与 backend learning_path.MASTERY_THRESHOLD 对齐 */
export const STAR_PATH_MASTERY_THRESHOLD = MASTERY_THRESHOLD

export { DOMAIN_UNLOCK_PROGRESS, NODE_UNLOCK_MIN_AC }

export function isQuestionAccepted(record: Pick<TrialMistakeRecord, 'lastFailedAt' | 'lastPassedAt'>): boolean {
  if (!record.lastPassedAt) return false
  if (!record.lastFailedAt) return true
  return new Date(record.lastPassedAt).getTime() >= new Date(record.lastFailedAt).getTime()
}

export function buildAcceptedQuestionSet(records: TrialMistakeRecord[]): Set<string> {
  const accepted = new Set<string>()
  for (const record of records) {
    if (isQuestionAccepted(record)) {
      accepted.add(record.questionId)
    }
  }
  return accepted
}

export function mergeAcceptedQuestionIds(
  serverIds: string[] | undefined,
  localRecords: TrialMistakeRecord[],
): Set<string> {
  const merged = buildAcceptedQuestionSet(localRecords)
  for (const id of serverIds ?? []) {
    merged.add(id)
  }
  return merged
}

export function countAcceptedForQuestionIds(questionIds: string[], accepted: Set<string>): number {
  return questionIds.filter((id) => accepted.has(id)).length
}

export function masteryPercentFromAc(questionIds: string[], accepted: Set<string>): number {
  if (!questionIds.length) return 0
  return Math.round((countAcceptedForQuestionIds(questionIds, accepted) / questionIds.length) * 100)
}
