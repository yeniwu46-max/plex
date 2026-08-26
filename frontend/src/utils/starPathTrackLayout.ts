import dagre from '@dagrejs/dagre'
import type { StarPathNode } from '../data/starPathTrail'

export interface TrackNodePosition {
  x: number
  y: number
  anchor?: 'left' | 'right'
}

/**
 * 八大学域每域 3–4 个知识点，间距按节点数给就够了，不必逐域硬编码。
 * 节点多的域放宽间距，免得连线挤在一起。
 */
function layoutParams(nodeCount: number): { rankdir: 'LR'; nodesep: number; ranksep: number } {
  return nodeCount >= 4
    ? { rankdir: 'LR', nodesep: 88, ranksep: 62 }
    : { rankdir: 'LR', nodesep: 72, ranksep: 48 }
}

/** 用 dagre 计算星轨节点坐标（viewBox 0–100） */
export function computeDagreLayout(
  nodes: Pick<StarPathNode, 'id' | 'title'>[],
): Record<string, TrackNodePosition> {
  if (nodes.length === 0) return {}
  if (nodes.length === 1) {
    return { [nodes[0]!.id]: { x: 50, y: 42 } }
  }

  const params = layoutParams(nodes.length)

  const g = new dagre.graphlib.Graph()
  g.setGraph({
    rankdir: params.rankdir,
    nodesep: params.nodesep,
    ranksep: params.ranksep,
    marginx: 28,
    marginy: 28,
    ranker: 'network-simplex',
  })
  g.setDefaultEdgeLabel(() => ({}))

  const nodeWidth = 96
  const nodeHeight = 72

  for (const node of nodes) {
    g.setNode(node.id, { width: nodeWidth, height: nodeHeight, label: node.title })
  }
  for (let i = 0; i < nodes.length - 1; i += 1) {
    g.setEdge(nodes[i]!.id, nodes[i + 1]!.id)
  }

  dagre.layout(g)

  const graph = g.graph()
  const graphWidth = Math.max(graph.width ?? 400, 1)
  const graphHeight = Math.max(graph.height ?? 200, 1)

  const positions: Record<string, TrackNodePosition> = {}
  for (const node of nodes) {
    const dag = g.node(node.id)
    if (!dag) continue
    const x = ((dag.x - (dag.width ?? nodeWidth) / 2) / graphWidth) * 86 + 7
    const y = ((dag.y - (dag.height ?? nodeHeight) / 2) / graphHeight) * 76 + 12
    const anchor: 'left' | 'right' | undefined =
      x < 20 ? 'left' : x > 80 ? 'right' : undefined
    positions[node.id] = {
      x: Math.min(93, Math.max(7, x)),
      y: Math.min(88, Math.max(12, y)),
      anchor,
    }
  }
  return positions
}

/** 生成平滑贝塞尔连线路径（带方向感） */
export function bezierPath(
  from: { x: number; y: number },
  to: { x: number; y: number },
): string {
  const dx = to.x - from.x
  const dy = to.y - from.y
  const vertical = Math.abs(dy) > Math.abs(dx) * 0.85
  const curve = Math.max(10, Math.abs(dx) * 0.38 + Math.abs(dy) * 0.28)

  if (vertical) {
    const c1x = from.x + (dx >= 0 ? curve * 0.35 : -curve * 0.35)
    const c1y = from.y + dy * 0.35
    const c2x = to.x - (dx >= 0 ? curve * 0.35 : -curve * 0.35)
    const c2y = to.y - dy * 0.35
    return `M ${from.x} ${from.y} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${to.x} ${to.y}`
  }

  const c1x = from.x + dx * 0.42
  const c1y = from.y + (dy >= 0 ? curve * 0.25 : -curve * 0.25)
  const c2x = from.x + dx * 0.68
  const c2y = to.y - (dy >= 0 ? curve * 0.25 : -curve * 0.25)
  return `M ${from.x} ${from.y} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${to.x} ${to.y}`
}

export function lineGradientId(status: string, variant: string) {
  return `track-grad-${status}-${variant}`
}
