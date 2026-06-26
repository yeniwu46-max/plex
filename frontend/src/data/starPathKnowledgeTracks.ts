import { getKnowledgePointsForDomain, type StarPathKnowledgePoint } from './starPathDomains'
import type { StarPathNode, StarPathNodeStatus } from './starPathTrail'
import type { LearningPathOrderedNode } from '../api/studentProgress'

export const ALL_STAGE_KEYS = ['stage1', 'stage2', 'stage3', 'stage4'] as const

const FOUR_NODE_POSITIONS: StarPathNode['position'][] = ['center', 'n2', 'n4', 'n5']
const FOUR_NODE_ANCHORS: Array<StarPathNode['anchor'] | undefined> = [undefined, 'left', 'right', 'right']

function mockStatus(index: number, total: number): StarPathNodeStatus {
  if (index === 0) return 'current'
  if (index === 1) return 'done'
  if (index < total - 1) return 'progress'
  return 'locked'
}

function mockGems(status: StarPathNodeStatus): StarPathNode['gems'] {
  if (status === 'done') return ['done', 'done', 'done', 'done']
  if (status === 'current' || status === 'progress') return ['done', 'done', 'active', 'pending']
  return ['locked', 'locked', 'pending', 'pending']
}

function statusFromPlan(
  plan: LearningPathOrderedNode | undefined,
  activeNodeId: string | null,
): StarPathNodeStatus {
  if (!plan) return 'locked'
  if (plan.locked) return 'locked'
  if (plan.id === activeNodeId) return 'current'
  if (plan.mastery_score >= 0.8 || plan.status === 'mastered') return 'done'
  if (plan.mastery_score > 0 || plan.status === 'learning' || plan.status === 'weak') return 'progress'
  return 'locked'
}

function kpToNode(
  kp: StarPathKnowledgePoint,
  index: number,
  total: number,
  plan?: LearningPathOrderedNode,
  activeNodeId?: string | null,
): StarPathNode {
  const status = plan
    ? statusFromPlan(plan, activeNodeId ?? null)
    : mockStatus(index, total)
  const questionIds = kp.questionId ? [kp.questionId] : []
  const masteryPct = plan
    ? Math.round((plan.mastery_score ?? 0) * 100)
    : status === 'done'
      ? 100
      : status === 'current'
        ? 65
        : status === 'progress'
          ? 40
          : 0

  return {
    id: kp.id,
    title: kp.title,
    status,
    questionIds,
    position: FOUR_NODE_POSITIONS[index] ?? 'center',
    anchor: FOUR_NODE_ANCHORS[index],
    icon: status === 'locked' ? 'lock' : 'code',
    gems: mockGems(status),
    knowledgeTags: kp.tags,
    advice: plan?.remediation
      ? `补救中：${plan.remediation.steps?.[0] ?? '完成微练习'}`
      : `建议先通读「${kp.title}」要点，再在试炼中验证理解。`,
    mastery: masteryPct,
    rewardCrystal: 1,
    rewardStardust: 10 + index * 3,
    locked: plan?.locked ?? status === 'locked',
    kgId: plan?.id,
  }
}

export function buildKnowledgeTrack(
  domainKey: string,
  orderedNodes?: LearningPathOrderedNode[],
  activeNodeId?: string | null,
): StarPathNode[] {
  const points = getKnowledgePointsForDomain(domainKey)
  const planByStar = new Map<string, LearningPathOrderedNode>()
  const planByKg = new Map<string, LearningPathOrderedNode>()
  for (const node of orderedNodes ?? []) {
    if (node.star_path_id) planByStar.set(node.star_path_id, node)
    planByKg.set(node.id, node)
  }

  return points.map((kp, i) => {
    const plan = planByStar.get(kp.id) ?? planByKg.get(kp.tags[0] ?? '')
    return kpToNode(kp, i, points.length, plan, activeNodeId)
  })
}

export function getStageTrackNodes(
  domainKey: string,
  orderedNodes?: LearningPathOrderedNode[],
  activeNodeId?: string | null,
): StarPathNode[] {
  return buildKnowledgeTrack(domainKey, orderedNodes, activeNodeId)
}

export function getAllStageTrackNodes(
  orderedNodes?: LearningPathOrderedNode[],
  activeNodeId?: string | null,
): StarPathNode[] {
  return ALL_STAGE_KEYS.flatMap((key) => buildKnowledgeTrack(key, orderedNodes, activeNodeId))
}

export function getKnowledgePointIdFromNodeId(nodeId: string): string | null {
  if (nodeId.includes('-')) return nodeId
  return null
}

export function findNodeInTrack(nodes: StarPathNode[], id: string) {
  return nodes.find((n) => n.id === id) ?? null
}
