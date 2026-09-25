/**
 * 将 Knowledge Intelligence Layer 的概念图（concept / relation）映射为
 * PlexKnowledgeGraph 可渲染的 KgNode / KgEdge。
 */
import type { KgEdge, KgEdgeType, KgNode, KgNodeStatus } from '../data/knowledgeGraphData'
import type { KnowledgeConceptNode, KnowledgeRelationEdge, RelationType } from '../api/knowledge'

const RELATION_TO_EDGE: Partial<Record<RelationType, KgEdgeType>> = {
  PREREQUISITE_OF: 'prerequisite',
  RELATED_TO: 'related',
  NEXT_RECOMMENDED: 'path',
  PART_OF: 'related',
  REMEDIATES: 'advanced',
  MISCONCEPTION_OF: 'advanced',
  EXAMPLE_OF: 'related',
  EXERCISE_FOR: 'related',
}

const EDGE_LABEL: Partial<Record<RelationType, string>> = {
  PREREQUISITE_OF: '前置',
  NEXT_RECOMMENDED: '推荐',
  MISCONCEPTION_OF: '误区',
  REMEDIATES: '补救',
  PART_OF: '属于',
}

export function difficultyLevel(difficulty: number): KgNode['level'] {
  if (difficulty >= 4) return 'advanced'
  if (difficulty >= 3) return 'intermediate'
  return 'basic'
}

export interface ConceptGraphMapOptions {
  /** concept_id -> 掌握状态；缺省时按节点类型着色 */
  statusOf?: (node: KnowledgeConceptNode) => KgNodeStatus
  /** 高亮的 concept_id（标记为 recommended） */
  highlightIds?: string[]
  /** 章节标题映射，用于 domain 显示 */
  chapterTitles?: Record<string, string>
}

export function mapConceptNodes(nodes: KnowledgeConceptNode[], options: ConceptGraphMapOptions = {}): KgNode[] {
  const highlight = new Set(options.highlightIds ?? [])
  return nodes.map((node) => {
    let status: KgNodeStatus = options.statusOf ? options.statusOf(node) : 'unlearned'
    if (highlight.has(node.concept_id)) status = 'recommended'
    else if (!options.statusOf && node.node_type === 'misconception') status = 'weak'
    else if (!options.statusOf && node.node_type === 'skill') status = 'learning'
    return {
      id: node.concept_id,
      label: node.name,
      domain: options.chapterTitles?.[node.chapter] ?? node.chapter ?? node.node_type,
      status,
      description: node.description || '',
      level: difficultyLevel(node.difficulty),
    }
  })
}

export function mapConceptEdges(edges: KnowledgeRelationEdge[], nodeIds?: Set<string>): KgEdge[] {
  const out: KgEdge[] = []
  for (const edge of edges) {
    if (nodeIds && (!nodeIds.has(edge.source) || !nodeIds.has(edge.target))) continue
    const type = RELATION_TO_EDGE[edge.relation_type]
    if (!type) continue
    out.push({
      id: `rel-${edge.id}`,
      source: edge.source,
      target: edge.target,
      type,
      label: edge.teacher_verified ? EDGE_LABEL[edge.relation_type] : EDGE_LABEL[edge.relation_type] ? `${EDGE_LABEL[edge.relation_type]}·待审` : undefined,
    })
  }
  return out
}
