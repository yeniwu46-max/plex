import type { PythonTrialQuestion } from '../data/pythonTrialQuestions'
import { fetchPracticeQuestions, type PracticeQuestionPayload } from '../api/practiceQuestions'
import {
  ensurePracticeQuestionsLoaded,
  getCachedPracticeQuestion,
  searchCachedPracticeQuestions,
} from './practiceQuestionCache'
import { normalizeQuestion } from './questionNaming'

function payloadToQuestion(item: PracticeQuestionPayload): PythonTrialQuestion {
  return normalizeQuestion({
    id: item.id,
    code: item.code,
    title: item.title,
    topic: item.topic,
    difficulty: item.difficulty,
    rewardXp: item.reward_xp,
    durationMin: item.duration_min,
    tags: item.tags,
    description: item.description,
    constraints: item.constraints,
    examples: item.examples,
    testCases: item.test_cases,
    starterCode: item.starter_code,
    runMode: item.run_mode,
    hint: item.hint,
  })
}

export async function searchPracticeQuestions(query: string, limit = 20): Promise<PythonTrialQuestion[]> {
  const q = query.trim()
  if (!q) return []
  await ensurePracticeQuestionsLoaded()
  const cached = searchCachedPracticeQuestions(q, limit)
  if (cached.length) return cached
  try {
    const result = await fetchPracticeQuestions(undefined, q)
    return result.items.slice(0, limit).map(payloadToQuestion)
  } catch {
    return []
  }
}

export function stashActivePracticeQuestion(question: PythonTrialQuestion) {
  if (typeof sessionStorage === 'undefined') return
  sessionStorage.setItem('plex:active-practice-question', JSON.stringify(question))
}

export async function openPracticeQuestion(
  router: { push: (path: string) => unknown },
  question: PythonTrialQuestion,
) {
  stashActivePracticeQuestion(question)
  await router.push(`/student/trials/practice/${encodeURIComponent(question.id)}`)
}

export async function openPracticeQuestionByRef(
  router: { push: (path: string) => unknown },
  ref: string,
): Promise<PythonTrialQuestion | null> {
  await ensurePracticeQuestionsLoaded()
  const cached = getCachedPracticeQuestion(ref)
  if (cached) {
    await openPracticeQuestion(router, cached)
    return cached
  }
  try {
    const { fetchPracticeQuestionByRef } = await import('../api/practiceQuestions')
    const item = await fetchPracticeQuestionByRef(ref)
    const question = payloadToQuestion(item)
    await openPracticeQuestion(router, question)
    return question
  } catch {
    return null
  }
}
