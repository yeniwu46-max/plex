import dagre from '@dagrejs/dagre'
import type { StarPathNode } from '../data/starPathTrail'

export interface TrackNodePosition {
  x: number
  y: number
  anchor?: 'left' | 'right'
}

const DOMAIN_LAYOUT_PARAMS: Record<
  string,
  { rankdir: 'LR' | 'TB'; nodesep: number; ranksep: number; custom?: boolean }
> = {
  'data-vars': { rankdir: 'LR', nodesep: 88, ranksep: 58 },
  operators: { rankdir: 'LR', nodesep: 72, ranksep: 48 },
  'flow-control': { rankdir: 'LR', nodesep: 82, ranksep: 62 },
  strings: { rankdir: 'LR', nodesep: 68, ranksep: 44 },
  'lists-dicts': { rankdir: 'LR', nodesep: 78, ranksep: 56 },
  functions: { rankdir: 'LR', nodesep: 68, ranksep: 44 },
  'recursion-iter': { rankdir: 'TB', nodesep: 96, ranksep: 78, custom: true },
}

/** 递归与迭代域：宽松垂直阶梯，避免 S 形挤压 */
function layoutRecursionIterVertical(
  nodes: Pick<StarPathNode, 'id' | 'title'>[],
): Record<string, TrackNodePosition> {
  const count = nodes.length
  if (count === 0) return {}
  if (count === 1) return { [nodes[0]!.id]: { x: 50, y: 38 } }

  const positions: Record<string, TrackNodePosition> = {}
  const xStops = [22, 78, 22, 78, 50, 72]
  const yStart = 10
  const yStep = Math.min(16, 78 / Math.max(count - 1, 1))

  nodes.forEach((node, index) => {
    const x = xStops[index % xStops.length] ?? 50
    const y = yStart + index * yStep
    positions[node.id] = {
      x,
      y: Math.min(90, y),
      anchor: x < 30 ? 'left' : x > 70 ? 'right' : undefined,
    }
  })
  return positions
}

/** 用 dagre 计算星轨节点坐标（viewBox 0–100） */
export function computeDagreLayout(
  nodes: Pick<StarPathNode, 'id' | 'title'>[],
  domainKey: string,
): Record<string, TrackNodePosition> {
  if (nodes.length === 0) return {}
  if (nodes.length === 1) {
    return { [nodes[0]!.id]: { x: 50, y: 42 } }
  }

  const params = DOMAIN_LAYOUT_PARAMS[domainKey] ?? { rankdir: 'LR' as const, nodesep: 64, ranksep: 52 }
  if (params.custom && domainKey === 'recursion-iter') {
    return layoutRecursionIterVertical(nodes)
  }

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

  const nodeWidth = domainKey === 'recursion-iter' ? 108 : 96
  const nodeHeight = domainKey === 'recursion-iter' ? 80 : 72

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
