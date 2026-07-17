import type { PythonTrialQuestion } from '../data/pythonTrialQuestions'
import {
  fetchPracticeQuestions,
  type PracticeQuestionPayload,
} from '../api/practiceQuestions'
import { normalizeQuestion } from './questionNaming'
import { wrapEpisodeNarrative, wrapExploration } from './explorationNarrative'
import { sanitizeQuestionContent, stripMarkdownAsterisks } from './questionStemSanitizer'
import { STAR_PATH_DOMAINS } from '../data/starPathDomains'

const KNOWLEDGE_KEY_TO_KP: Record<string, { kpId: string; domainKey: string }> = Object.fromEntries(
  STAR_PATH_DOMAINS.flatMap((domain) =>
    domain.knowledgePoints.flatMap((kp) =>
      kp.tags.map((tag) => [tag, { kpId: kp.id, domainKey: domain.key }]),
    ),
  ),
)

function ensureNarrativeDescription(description: string, knowledgeKey?: string, slot = 0): string {
  const cleaned = stripMarkdownAsterisks(description)
  if (cleaned.includes('星球探险') || cleaned.includes('🛸')) return cleaned
  const mapped = knowledgeKey ? KNOWLEDGE_KEY_TO_KP[knowledgeKey] : undefined
  const task = cleaned.trim()
  if (!task) return description
  if (mapped) {
    return wrapEpisodeNarrative(mapped.kpId, mapped.domainKey, slot, task.split('\n').pop()?.trim() || task)
  }
  return wrapExploration('任务现场收到一条加密指令', task)
}

function normalizeExamples(examples: PracticeQuestionPayload['examples']) {
  return (examples ?? []).map((ex) => ({
    ...ex,
    input: stripMarkdownAsterisks(ex.input),
    output: stripMarkdownAsterisks(ex.output),
  }))
}

/** 清理 legacy 题库标记（{[...]}、**...**）为纯文本 */
export function cleanLegacyQuestionMarkup(text: string): string {
  return stripMarkdownAsterisks(text)
}

function toTrialQuestion(item: PracticeQuestionPayload): PythonTrialQuestion {
  const normalized = normalizeQuestion({
    id: item.id,
    code: item.code,
    title: item.title,
    topic: item.topic,
    difficulty: item.difficulty,
    rewardXp: item.reward_xp,
    durationMin: item.duration_min,
    tags: item.tags,
    description: ensureNarrativeDescription(item.description, item.knowledge_key),
    constraints: item.constraints,
    examples: normalizeExamples(item.examples),
    testCases: item.test_cases,
    starterCode: item.starter_code,
    runMode: item.run_mode,
    hint: item.hint,
  })
  return sanitizeQuestionContent(normalized)
}

let cacheLoaded = false
let loadPromise: Promise<void> | null = null
const byId = new Map<string, PythonTrialQuestion>()
const byCode = new Map<string, PythonTrialQuestion>()
const byKnowledgeKey = new Map<string, PythonTrialQuestion[]>()

function indexQuestion(question: PythonTrialQuestion, knowledgeKey?: string) {
  byId.set(question.id, question)
  if (question.code) byCode.set(question.code.toLowerCase(), question)
  const key = knowledgeKey || question.tags[0]
  if (!key) return
  const list = byKnowledgeKey.get(key) ?? []
  if (!list.some((item) => item.id === question.id)) {
    list.push(question)
    byKnowledgeKey.set(key, list)
  }
}

export function getCachedPracticeQuestion(id: string): PythonTrialQuestion | null {
  return byId.get(id) ?? byCode.get(id.toLowerCase()) ?? null
}

export function searchCachedPracticeQuestions(query: string, limit = 20): PythonTrialQuestion[] {
  const needle = query.trim().toLowerCase()
  if (!needle) return []
  const results: PythonTrialQuestion[] = []
  const seen = new Set<string>()
  for (const q of byId.values()) {
    const hay = [q.code, q.id, q.title, q.topic, q.description, ...(q.tags ?? [])]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
    if (hay.includes(needle) && !seen.has(q.id)) {
      results.push(q)
      seen.add(q.id)
    }
    if (results.length >= limit) break
  }
  return results
}

export function getCachedPracticeQuestionsForKey(knowledgeKey: string): PythonTrialQuestion[] {
  return byKnowledgeKey.get(knowledgeKey) ?? []
}

export function isPracticeQuestionCacheReady() {
  return cacheLoaded
}

export async function ensurePracticeQuestionsLoaded(knowledgeKey?: string) {
  if (cacheLoaded && !knowledgeKey) return
  if (loadPromise && !knowledgeKey) {
    await loadPromise
    return
  }
  const task = (async () => {
    try {
      const result = await fetchPracticeQuestions(knowledgeKey)
      for (const item of result.items) {
        indexQuestion(toTrialQuestion(item), item.knowledge_key)
      }
      if (!knowledgeKey) cacheLoaded = true
    } catch {
      if (!knowledgeKey) cacheLoaded = true
    }
  })()
  if (!knowledgeKey) loadPromise = task
  await task
}

export function resetPracticeQuestionCacheForTests() {
  cacheLoaded = false
  loadPromise = null
  byId.clear()
  byCode.clear()
  byKnowledgeKey.clear()
}
