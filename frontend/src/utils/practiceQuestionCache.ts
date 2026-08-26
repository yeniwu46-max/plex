import { ref } from 'vue'
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

/**
 * 这些 Map 本身不是响应式的，computed 读它们不会在题目到货后重算。
 * 每次批量写入后自增此计数，需要跟随刷新的 computed 读一下它即可建立依赖。
 */
export const practiceCacheVersion = ref(0)

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

const SEARCH_ALIASES: Record<string, string[]> = {
  列表: ['list', '列表', '数组', 'array', '索引'],
  索引: ['index', '索引', '列表', 'list', '下标'],
  循环: ['loop', 'for', 'while', '循环', '迭代'],
  函数: ['function', 'def', '函数', '参数'],
  字典: ['dict', 'dictionary', '字典', '映射'],
  字符串: ['str', 'string', '字符串', '字符'],
  条件: ['if', 'elif', '条件', '分支', '判断'],
  异常: ['except', 'exception', 'try', '异常', '报错'],
  递归: ['recursion', '递归'],
  排序: ['sort', 'sorted', '排序'],
  查找: ['search', '查找', '二分', 'binary'],
}

function expandSearchNeedles(query: string): string[] {
  const raw = query.trim().toLowerCase()
  if (!raw) return []
  const needles = new Set<string>([raw])
  for (const part of raw.split(/[\s,，、]+/).filter((p) => p.length >= 1)) {
    needles.add(part)
    for (const [key, aliases] of Object.entries(SEARCH_ALIASES)) {
      if (part.includes(key) || key.includes(part) || aliases.some((a) => a.toLowerCase() === part || part.includes(a.toLowerCase()))) {
        needles.add(key.toLowerCase())
        aliases.forEach((a) => needles.add(a.toLowerCase()))
      }
    }
  }
  return [...needles]
}

export function searchCachedPracticeQuestions(query: string, limit = 20): PythonTrialQuestion[] {
  const needles = expandSearchNeedles(query)
  if (!needles.length) return []
  const scored: Array<{ score: number; q: PythonTrialQuestion }> = []
  for (const q of byId.values()) {
    const title = (q.title || '').toLowerCase()
    const topic = (q.topic || '').toLowerCase()
    const tags = (q.tags ?? []).join(' ').toLowerCase()
    const hay = [q.code, q.id, q.title, q.topic, q.description, ...(q.tags ?? [])]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
    let score = 0
    for (const needle of needles) {
      if (!needle) continue
      if (needle === (q.code || '').toLowerCase() || needle === q.id.toLowerCase()) score += 100
      else if (title.includes(needle)) score += 40
      else if (topic.includes(needle) || tags.includes(needle)) score += 30
      else if (hay.includes(needle)) score += 10
    }
    if (score > 0) scored.push({ score, q })
  }
  scored.sort((a, b) => b.score - a.score || (a.q.code || a.q.id).localeCompare(b.q.code || b.q.id))
  return scored.slice(0, limit).map((row) => row.q)
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
      if (result.items.length) practiceCacheVersion.value += 1
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
  practiceCacheVersion.value = 0
}
