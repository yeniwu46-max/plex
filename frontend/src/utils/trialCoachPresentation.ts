import type { MessengerKnowledge } from '../api/rag'

type TrialCoachSliceContext = {
  topic?: string
  stderr?: string
  failedCases?: Array<{ label?: string; error?: string }>
  answerStatus?: 'correct' | 'wrong' | 'partial' | 'not_run'
}

function topicTokens(topic?: string) {
  if (!topic?.trim()) return [] as string[]
  return topic
    .split(/[\s、,，/]+/)
    .map((t) => t.trim().toLowerCase())
    .filter(Boolean)
}

function conceptMatchesTopic(name: string, tokens: string[]) {
  if (!tokens.length) return true
  const lower = name.toLowerCase()
  return tokens.some((t) => lower.includes(t) || t.includes(lower))
}

/** 试炼浮球场景：弱化泛化推荐，只保留与当前错题/报错强相关的知识卡片内容。 */
export function trimTrialCoachKnowledge(
  knowledge: MessengerKnowledge | null | undefined,
  ctx: TrialCoachSliceContext,
): MessengerKnowledge | null {
  if (!knowledge?.knowledge_grounded) return null

  const hasRunIssue =
    Boolean(ctx.stderr?.trim()) ||
    Boolean(ctx.failedCases?.length) ||
    ctx.answerStatus === 'wrong' ||
    ctx.answerStatus === 'partial'

  const tokens = topicTokens(ctx.topic)
  const concepts = (knowledge.concepts ?? []).filter((c) => {
    if (c.role === 'focus') return true
    if (c.role === 'prerequisite' && hasRunIssue) return conceptMatchesTopic(c.name, tokens)
    return hasRunIssue && conceptMatchesTopic(c.name, tokens)
  })

  const recommended = hasRunIssue
    ? (knowledge.recommended_next ?? []).filter((item) => item.type === 'misconception').slice(0, 1)
    : []

  const sources = (knowledge.sources ?? []).slice(0, hasRunIssue ? 3 : 2)

  if (!concepts.length && !recommended.length && !sources.length) {
    return null
  }

  return {
    ...knowledge,
    concepts,
    recommended_next: recommended,
    sources,
  }
}
