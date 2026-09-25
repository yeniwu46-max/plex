import dagre from '@dagrejs/dagre'
import type { StarPathNode } from '../data/starPathTrail'

export interface TrackNodePosition {
  /** 轨道画布内的像素坐标（左上角锚点由 CSS transform 居中） */
  x: number
  y: number
  anchor?: 'left' | 'right'
}

export interface DagreTrackLayout {
  positions: Record<string, TrackNodePosition>
  width: number
  height: number
}

/**
 * 链式 LR 布局：节点越多 ranksep 越大，避免 10+ 知识点挤在同一视口宽度里。
 */
function layoutParams(nodeCount: number): {
  rankdir: 'LR'
  nodesep: number
  ranksep: number
  nodeWidth: number
  nodeHeight: number
} {
  if (nodeCount >= 12) {
    return { rankdir: 'LR', nodesep: 96, ranksep: 220, nodeWidth: 132, nodeHeight: 108 }
  }
  if (nodeCount >= 8) {
    return { rankdir: 'LR', nodesep: 88, ranksep: 180, nodeWidth: 128, nodeHeight: 100 }
  }
  if (nodeCount >= 6) {
    return { rankdir: 'LR', nodesep: 82, ranksep: 148, nodeWidth: 124, nodeHeight: 96 }
  }
  if (nodeCount >= 4) {
    return { rankdir: 'LR', nodesep: 118, ranksep: 112, nodeWidth: 118, nodeHeight: 92 }
  }
  return { rankdir: 'LR', nodesep: 96, ranksep: 88, nodeWidth: 112, nodeHeight: 88 }
}

/** 用 dagre 计算星轨节点坐标（像素坐标系，轨道容器按 graph 尺寸撑开） */
export function computeDagreLayout(
  nodes: Pick<StarPathNode, 'id' | 'title'>[],
): DagreTrackLayout {
  if (nodes.length === 0) {
    return { positions: {}, width: 400, height: 280 }
  }
  if (nodes.length === 1) {
    return {
      positions: { [nodes[0]!.id]: { x: 220, y: 140 } },
      width: 440,
      height: 280,
    }
  }

  const params = layoutParams(nodes.length)

  const g = new dagre.graphlib.Graph()
  g.setGraph({
    rankdir: params.rankdir,
    nodesep: params.nodesep,
    ranksep: params.ranksep,
    marginx: 48,
    marginy: 56,
    ranker: 'network-simplex',
  })
  g.setDefaultEdgeLabel(() => ({}))

  const { nodeWidth, nodeHeight } = params

  for (const node of nodes) {
    g.setNode(node.id, { width: nodeWidth, height: nodeHeight, label: node.title })
  }
  for (let i = 0; i < nodes.length - 1; i += 1) {
    g.setEdge(nodes[i]!.id, nodes[i + 1]!.id)
  }

  dagre.layout(g)

  const graph = g.graph()
  const graphWidth = Math.max(Math.ceil(graph.width ?? 400), 320)
  const graphHeight = Math.max(Math.ceil(graph.height ?? 200), 220)

  const positions: Record<string, TrackNodePosition> = {}
  for (const node of nodes) {
    const dag = g.node(node.id)
    if (!dag) continue
    const x = dag.x ?? graphWidth / 2
    const y = dag.y ?? graphHeight / 2
    const anchor: 'left' | 'right' | undefined =
      x < graphWidth * 0.12 ? 'left' : x > graphWidth * 0.88 ? 'right' : undefined
    positions[node.id] = {
      x: Math.min(graphWidth - 24, Math.max(24, x)),
      y: Math.min(graphHeight - 32, Math.max(32, y)),
      anchor,
    }
  }
  return { positions, width: graphWidth, height: graphHeight }
}

/** 生成平滑贝塞尔连线路径（带方向感，与节点同像素坐标系） */
export function bezierPath(
  from: { x: number; y: number },
  to: { x: number; y: number },
): string {
  const dx = to.x - from.x
  const dy = to.y - from.y
  const vertical = Math.abs(dy) > Math.abs(dx) * 0.85
  const curve = Math.max(18, Math.abs(dx) * 0.38 + Math.abs(dy) * 0.28)

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
