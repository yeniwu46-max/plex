import { STAR_PATH_MASTERY_THRESHOLD } from '../utils/starPathProgress'
import { NODE_UNLOCK_MIN_AC } from '../constants/starPathUnlock'
import { getKnowledgePointsForDomain, STAR_PATH_DOMAINS, type StarPathKnowledgePoint } from './starPathDomains'
import type { StarPathGem, StarPathNode, StarPathNodeStatus } from './starPathTrail'
import type { LearningPathOrderedNode } from '../api/studentProgress'

export const ALL_STAGE_KEYS = [
  'data-vars',
  'operators',
  'flow-control',
  'strings',
  'lists-dicts',
  'functions',
  'recursion-iter',
] as const

/** 每个知识点至少 5 道试炼题 */
export const MIN_QUESTIONS_PER_KP = 5

function generatedIdsForKnowledgePoint(kpId: string): string[] {
  return Array.from({ length: MIN_QUESTIONS_PER_KP }, (_, slot) => `gen-${kpId}-s${slot}`)
}

/** 各知识点 5 道生成题 ID（与 starPathQuestionGenerator 槽位一致） */
export const KP_QUESTION_IDS: Record<string, string[]> = Object.fromEntries(
  STAR_PATH_DOMAINS.flatMap((domain) =>
    domain.knowledgePoints.map((kp) => [kp.id, generatedIdsForKnowledgePoint(kp.id)]),
  ),
)

type NodeLayout = Pick<StarPathNode, 'position' | 'anchor'>

/** 各星域串联轨道布局：节点按学习顺序依次连接（dagre 会覆盖坐标，此处保留 position 兼容） */
const DOMAIN_NODE_LAYOUTS: Record<string, NodeLayout[]> = {
  'data-vars': [
    { position: 'n6', anchor: 'left' },
    { position: 'n2', anchor: 'left' },
    { position: 'center' },
    { position: 'n4', anchor: 'right' },
  ],
  operators: [{ position: 'center' }],
  'flow-control': [
    { position: 'n6', anchor: 'left' },
    { position: 'center' },
    { position: 'n4', anchor: 'right' },
  ],
  strings: [{ position: 'center' }],
  'lists-dicts': [
    { position: 'n2', anchor: 'left' },
    { position: 'center' },
    { position: 'n4', anchor: 'right' },
  ],
  functions: [{ position: 'center' }],
  'recursion-iter': [
    { position: 'n6', anchor: 'left' },
    { position: 'n2', anchor: 'left' },
    { position: 'center' },
    { position: 'n4', anchor: 'right' },
  ],
}

const DEFAULT_LAYOUT: NodeLayout[] = [
  { position: 'center' },
  { position: 'n2', anchor: 'left' },
  { position: 'n4', anchor: 'right' },
  { position: 'n5', anchor: 'right' },
]

export function getDomainTrackLayout(domainKey: string): NodeLayout[] {
  return DOMAIN_NODE_LAYOUTS[domainKey] ?? DEFAULT_LAYOUT
}

function gemsFromAcStatus(
  status: StarPathNodeStatus,
  questionIds: string[],
  acceptedQuestionIds: Set<string>,
  activeNodeId: string | null,
  nodeId: string,
): StarPathNode['gems'] {
  const isCurrent = status !== 'locked' && nodeId === activeNodeId
  let activeAssigned = false

  return questionIds.map((qid, index) => {
    if (status === 'locked') {
      return index < 2 ? ('locked' as const) : ('pending' as const)
    }
    if (acceptedQuestionIds.has(qid)) {
      return 'done' as const
    }
    if (isCurrent && !activeAssigned) {
      activeAssigned = true
      return 'active' as const
    }
    return 'pending' as const
  }) as StarPathGem[]
}

function statusFromPlan(
  plan: LearningPathOrderedNode | undefined,
  activeNodeId: string | null,
  masteryPct: number,
): StarPathNodeStatus {
  if (plan?.locked) return 'locked'
  if (plan?.id === activeNodeId) return 'current'
  if (masteryPct >= 100 || (plan?.mastery_score ?? 0) >= STAR_PATH_MASTERY_THRESHOLD || plan?.status === 'mastered') {
    return 'done'
  }
  if (masteryPct > 0 || (plan?.mastery_score ?? 0) > 0 || plan?.status === 'learning' || plan?.status === 'weak') {
    return 'progress'
  }
  return 'progress'
}

function resolveNodeLocked(
  index: number,
  plan: LearningPathOrderedNode | undefined,
  previousAcCount: number,
): boolean {
  if (index === 0) return false
  if (previousAcCount >= NODE_UNLOCK_MIN_AC) return false
  if (plan?.locked) return true
  if (plan && plan.prerequisites_met === false) return true
  return false
}

function questionIdsForKnowledgePoint(kp: StarPathKnowledgePoint): string[] {
  const mapped = KP_QUESTION_IDS[kp.id]
  if (mapped?.length >= MIN_QUESTIONS_PER_KP) return mapped
  return generatedIdsForKnowledgePoint(kp.id)
}

function kpToNode(
  kp: StarPathKnowledgePoint,
  index: number,
  layout: NodeLayout[],
  plan: LearningPathOrderedNode | undefined,
  activeNodeId: string | null,
  acceptedQuestionIds: Set<string>,
  previousAcCount: number,
): StarPathNode {
  const questionIds = questionIdsForKnowledgePoint(kp)
  const acCount = questionIds.filter((id) => acceptedQuestionIds.has(id)).length
  const masteryPct = questionIds.length
    ? Math.round((acCount / questionIds.length) * 100)
    : Math.round((plan?.mastery_score ?? 0) * 100)

  const nodeLocked = resolveNodeLocked(index, plan, previousAcCount)
  const status: StarPathNodeStatus = nodeLocked
    ? 'locked'
    : statusFromPlan(plan, activeNodeId, masteryPct)

  const slot = layout[index] ?? layout[layout.length - 1] ?? { position: 'center' as const }
  const gemCount = Math.max(MIN_QUESTIONS_PER_KP, questionIds.length)

  return {
    id: kp.id,
    title: kp.title,
    status,
    questionIds,
    position: slot.position,
    anchor: slot.anchor,
    icon: status === 'locked' ? 'lock' : 'code',
    gems: gemsFromAcStatus(status, questionIds.slice(0, gemCount), acceptedQuestionIds, activeNodeId, kp.id),
    knowledgeTags: kp.tags,
    advice: plan?.remediation
      ? `补救中：${plan.remediation.steps?.[0] ?? '完成微练习'}`
      : `小E 建议：先通读「${kp.title}」要点，再完成 ${gemCount} 道星球试炼验证理解。`,
    mastery: masteryPct,
    rewardCrystal: 1,
    rewardStardust: 10 + index * 3,
    locked: nodeLocked,
    kgId: plan?.id,
  }
}

export function buildKnowledgeTrack(
  domainKey: string,
  orderedNodes?: LearningPathOrderedNode[],
  activeNodeId?: string | null,
  acceptedQuestionIds: Set<string> = new Set(),
): StarPathNode[] {
  const points = getKnowledgePointsForDomain(domainKey)
  const layout = getDomainTrackLayout(domainKey)
  const planByStar = new Map<string, LearningPathOrderedNode>()
  const planByKg = new Map<string, LearningPathOrderedNode>()
  for (const node of orderedNodes ?? []) {
    if (node.star_path_id) planByStar.set(node.star_path_id, node)
    planByKg.set(node.id, node)
  }

  const nodes: StarPathNode[] = []
  let previousAcCount = NODE_UNLOCK_MIN_AC

  for (let i = 0; i < points.length; i += 1) {
    const kp = points[i]!
    const plan = planByStar.get(kp.id) ?? planByKg.get(kp.tags[0] ?? '')
    const node = kpToNode(kp, i, layout, plan, activeNodeId ?? null, acceptedQuestionIds, previousAcCount)
    nodes.push(node)
    previousAcCount = node.questionIds.filter((id) => acceptedQuestionIds.has(id)).length
  }

  return nodes
}

export function getStageTrackNodes(
  domainKey: string,
  orderedNodes?: LearningPathOrderedNode[],
  activeNodeId?: string | null,
  acceptedQuestionIds?: Set<string>,
): StarPathNode[] {
  return buildKnowledgeTrack(domainKey, orderedNodes, activeNodeId, acceptedQuestionIds)
}

export function getAllStageTrackNodes(
  orderedNodes?: LearningPathOrderedNode[],
  activeNodeId?: string | null,
  acceptedQuestionIds?: Set<string>,
): StarPathNode[] {
  return ALL_STAGE_KEYS.flatMap((key) => buildKnowledgeTrack(key, orderedNodes, activeNodeId, acceptedQuestionIds))
}

export function getKnowledgePointIdFromNodeId(nodeId: string): string | null {
  if (nodeId.includes('-')) return nodeId
  return null
}

export function findNodeInTrack(nodes: StarPathNode[], id: string) {
  return nodes.find((n) => n.id === id) ?? null
}
