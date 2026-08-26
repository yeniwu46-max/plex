import { getPythonTrialQuestion, type PythonTrialQuestion } from './pythonTrialQuestions'
import { getAllStageTrackNodes } from './starPathKnowledgeTracks'
import { getStarPathKnowledgePoint } from './starPathDomains'
import { resolveQuestionById } from '../utils/starPathQuestionGenerator'
import { getCachedPracticeQuestionsForKey } from '../utils/practiceQuestionCache'

export type StarPathNodeStatus = 'current' | 'done' | 'progress' | 'locked'
export type StarPathGem = 'done' | 'active' | 'locked' | 'pending'
export type StarPathNodeIcon = 'code' | 'server' | 'lock'

export interface StarPathNode {
  id: string
  title: string
  titleLine2?: string
  status: StarPathNodeStatus
  questionIds: string[]
  position: 'center' | 'n2' | 'n3' | 'n4' | 'n5' | 'n6' | 'n7'
  anchor?: 'left' | 'right'
  icon: StarPathNodeIcon
  gems: StarPathGem[]
  knowledgeTags: string[]
  advice: string
  mastery: number
  rewardCrystal: number
  rewardStardust: number
  locked?: boolean
  kgId?: string
}

/** 历史深链兼容：旧星轨 01–07 编号，以及重构前的 stageN-* 节点 id */
const LEGACY_NODE_MAP: Record<string, string> = {
  '01': 'lang-print',
  '02': 'lang-var',
  '03': 'branch-if',
  '04': 'loop-for',
  '05': 'array-basic',
  '06': 'func-define',
  '07': 'search-binary',
  'stage1-intro': 'lang-print',
  'stage1-comment': 'lang-print',
  'stage1-var': 'lang-var',
  'stage1-io': 'lang-input',
  'stage2-ops': 'seq-arith',
  'stage2-cond': 'branch-if',
  'stage2-loop': 'loop-for',
  'stage2-range': 'loop-for',
  'stage3-str': 'string-index',
  'stage3-list': 'array-basic',
  'stage3-dict': 'array-traverse',
  'stage3-func': 'func-define',
  'stage4-algo-sum': 'search-stat',
  'stage4-bubble': 'search-sort',
  'stage4-selection': 'search-sort',
  'stage4-binary': 'search-binary',
}

export function resolveStarPathNodeId(id: string): string {
  return LEGACY_NODE_MAP[id] ?? id
}

export function getStarPathNode(id: string, acceptedQuestionIds?: Set<string>) {
  const resolved = resolveStarPathNodeId(id)
  return getAllStageTrackNodes(undefined, undefined, acceptedQuestionIds).find((node) => node.id === resolved) ?? null
}

export function getStarPathNodeByQuestionId(questionId: string, acceptedQuestionIds?: Set<string>) {
  return getAllStageTrackNodes(undefined, undefined, acceptedQuestionIds).find((node) =>
    node.questionIds.includes(questionId),
  ) ?? null
}

export function getPrimaryQuestionId(node: StarPathNode) {
  return node.questionIds[0] ?? ''
}

export function getStarPathQuestionsForNode(nodeId: string): PythonTrialQuestion[] {
  return resolveQuestionsForNode(nodeId)
}

/**
 * 优先返回接口下发的真题（practiceQuestionCache 已按 kg_node_id 建好索引），
 * 只有缓存尚未加载或该节点确实没有真题时，才回落到静态题与离线生成题。
 * 调用方应先 await ensurePracticeQuestionsLoaded()，否则本函数只能给到兜底题。
 */
export function resolveQuestionsForNode(nodeId: string): PythonTrialQuestion[] {
  const node = getStarPathNode(nodeId)
  if (!node) return []

  const resolvedId = resolveStarPathNodeId(nodeId)
  const fromApi = getCachedPracticeQuestionsForKey(resolvedId)
  if (fromApi.length) return fromApi

  const kp = getStarPathKnowledgePoint(resolvedId)?.point
  return node.questionIds
    .map((id) => {
      const staticQuestion = getPythonTrialQuestion(id)
      if (staticQuestion) return staticQuestion
      if (kp) {
        const resolved = resolveQuestionById(id, kp)
        if (resolved) return resolved
      }
      return null
    })
    .filter((item): item is PythonTrialQuestion => item !== null)
}

export function getUnlockedStarPathNodes(acceptedQuestionIds?: Set<string>) {
  return getAllStageTrackNodes(undefined, undefined, acceptedQuestionIds).filter(isStarPathNodeUnlocked)
}

export function formatStarPathGems(gems: StarPathNode['gems']) {
  return (gems ?? [])
    .map((gem) => {
      if (gem === 'done' || gem === 'active') return '◆'
      return '◇'
    })
    .join(' ')
}

export function starPathNodeTrackClass(node: StarPathNode) {
  if (node.status === 'current') return 'current'
  if (node.status === 'locked') return 'locked'
  if (node.status === 'progress') return 'progress'
  return 'done'
}

export function isStarPathNodeUnlocked(node: StarPathNode | null | undefined) {
  if (node == null) return false
  if (node.locked) return false
  return node.status !== 'locked'
}

export function formatStarPathNodeLabel(node: StarPathNode) {
  if (node.titleLine2) return `${node.title} · ${node.titleLine2}`
  return node.title
}

export function getNodeOrderBonus(nodeId: string, questionId: string) {
  const node = getStarPathNode(nodeId)
  if (!node) return 0
  const index = node.questionIds.indexOf(questionId)
  if (index < 0) return 0
  return Math.max(10, 90 - index * 18)
}
