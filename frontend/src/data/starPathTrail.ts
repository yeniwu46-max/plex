import { getPythonTrialQuestion, type PythonTrialQuestion } from './pythonTrialQuestions'
import { getAllStageTrackNodes } from './starPathKnowledgeTracks'

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
  gems: [StarPathGem, StarPathGem, StarPathGem, StarPathGem]
  knowledgeTags: string[]
  advice: string
  mastery: number
  rewardCrystal: number
  rewardStardust: number
}

/** 旧星轨 01–07 深链映射到四阶段节点 */
const LEGACY_NODE_MAP: Record<string, string> = {
  '01': 'stage1-intro',
  '02': 'stage1-var',
  '03': 'stage2-cond',
  '04': 'stage2-loop',
  '05': 'stage3-list',
  '06': 'stage3-func',
  '07': 'stage4-algo-search',
}

export function resolveStarPathNodeId(id: string): string {
  return LEGACY_NODE_MAP[id] ?? id
}

export function getStarPathNode(id: string) {
  const resolved = resolveStarPathNodeId(id)
  return getAllStageTrackNodes().find((node) => node.id === resolved) ?? null
}

export function getStarPathNodeByQuestionId(questionId: string) {
  return getAllStageTrackNodes().find((node) => node.questionIds.includes(questionId)) ?? null
}

export function getPrimaryQuestionId(node: StarPathNode) {
  return node.questionIds[0] ?? ''
}

export function getStarPathQuestionsForNode(nodeId: string): PythonTrialQuestion[] {
  const node = getStarPathNode(nodeId)
  if (!node) return []
  return node.questionIds
    .map((id) => getPythonTrialQuestion(id))
    .filter((item): item is PythonTrialQuestion => item !== null)
}

export function getUnlockedStarPathNodes() {
  return getAllStageTrackNodes().filter(isStarPathNodeUnlocked)
}

export function formatStarPathGems(gems: StarPathNode['gems']) {
  return gems
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
  return node != null && node.status !== 'locked'
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
