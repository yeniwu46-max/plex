import type { DomainMasteryItem } from '../api/learningReport'
import type { KgNode } from '../data/knowledgeGraphData'

export interface KnowledgeRadarData {
  dimensions: string[]
  values: number[]
}

const FALLBACK_DIMENSIONS = ['Python 入门', '条件分支', '循环结构', '列表', '函数', '算法入门']

export function buildKnowledgeRadarFromGraph(
  nodes: KgNode[],
  fallback?: DomainMasteryItem[],
): KnowledgeRadarData {
  const practiced = nodes
    .filter((node) => (node.answered_count ?? 0) > 0 || node.accuracy != null)
    .sort((a, b) => {
      const aScore = (a.answered_count ?? 0) * 10 + (a.accuracy ?? 0)
      const bScore = (b.answered_count ?? 0) * 10 + (b.accuracy ?? 0)
      return bScore - aScore
    })
    .slice(0, 6)

  if (practiced.length >= 3) {
    return {
      dimensions: practiced.map((node) => node.label),
      values: practiced.map((node) => node.accuracy ?? 0),
    }
  }

  const domains = (fallback ?? []).filter((item) => item.answered > 0).slice(0, 6)
  if (domains.length >= 3) {
    return {
      dimensions: domains.map((item) => item.label),
      values: domains.map((item) => item.mastery_rate),
    }
  }

  return {
    dimensions: FALLBACK_DIMENSIONS,
    values: FALLBACK_DIMENSIONS.map(() => 0),
  }
}
