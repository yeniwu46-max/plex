import { getKnowledgePointsForDomain, type StarPathKnowledgePoint } from './starPathDomains'
import { STAR_PATH_ALGO_NODES, type StarPathNode, type StarPathNodeStatus } from './starPathTrail'

const FOUR_NODE_POSITIONS: StarPathNode['position'][] = ['center', 'n2', 'n4', 'n5']
const FOUR_NODE_ANCHORS: Array<StarPathNode['anchor'] | undefined> = [undefined, 'left', 'right', 'right']

/** 算法域 4 个知识点 → 7 星轨节点题目合并 */
const ALGO_KP_QUESTION_IDS: Record<string, string[]> = {
  'algo-01': ['01'],
  'algo-02': ['02'],
  'algo-03': ['03'],
  'algo-04': ['05', '06', '07'],
}

function nodeIdsToQuestionIds(nodeIds: string[]): string[] {
  const ids: string[] = []
  for (const nid of nodeIds) {
    const node = STAR_PATH_ALGO_NODES.find((n) => n.id === nid)
    if (node) ids.push(...node.questionIds)
  }
  return ids
}

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

function kpToNode(kp: StarPathKnowledgePoint, index: number, total: number): StarPathNode {
  const status = mockStatus(index, total)
  const questionIds = kp.questionId
    ? [kp.questionId]
    : ALGO_KP_QUESTION_IDS[kp.id]
      ? nodeIdsToQuestionIds(ALGO_KP_QUESTION_IDS[kp.id])
      : []

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
    advice: `建议先通读「${kp.title}」要点，再在试炼中验证理解。`,
    mastery: status === 'done' ? 100 : status === 'current' ? 65 : status === 'progress' ? 40 : 0,
    rewardCrystal: 1,
    rewardStardust: 10 + index * 3,
  }
}

export function buildKnowledgeTrack(domainKey: string): StarPathNode[] {
  const points = getKnowledgePointsForDomain(domainKey)
  return points.map((kp, i) => kpToNode(kp, i, points.length))
}

export function getKnowledgePointIdFromNodeId(nodeId: string): string | null {
  if (nodeId.includes('-')) return nodeId
  return null
}

export function findNodeInTrack(nodes: StarPathNode[], id: string) {
  return nodes.find((n) => n.id === id) ?? null
}
