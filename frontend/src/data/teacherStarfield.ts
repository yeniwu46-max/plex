import type { TeacherClassStatsResult, TeacherOverview } from '../api/teacherOverview'
import { STAR_PATH_TABS } from './starPathDomains'
import { TEACHER_KNOWLEDGE_UNIVERSE } from './teacherKnowledgeCatalog'

export type OrbitNodeTone = 'amber' | 'gold' | 'teal' | 'red'

export interface OrbitNode {
  label: string
  tone: OrbitNodeTone
  x: number
  y: number
  score: number
  delta: '上升' | '下降' | '稳定'
  domainKey?: string
}

const ORBIT_LAYOUT: Record<string, Pick<OrbitNode, 'tone' | 'x' | 'y'>> = {
  stage1: { tone: 'teal', x: 11, y: 30 },
  stage2: { tone: 'amber', x: 34, y: 10 },
  stage3: { tone: 'gold', x: 72, y: 18 },
  stage4: { tone: 'teal', x: 86, y: 62 },
  algo: { tone: 'amber', x: 43, y: 16 },
  fe: { tone: 'gold', x: 72, y: 26 },
  be: { tone: 'red', x: 73, y: 70 },
  cs: { tone: 'teal', x: 50, y: 78 },
  db: { tone: 'amber', x: 21, y: 66 },
  ds: { tone: 'red', x: 12, y: 39 },
}

/** 知识宇宙六大学域（与 knowledge_catalog / 全景图一致） */
export const STARFIELD_DOMAINS: Omit<OrbitNode, 'score' | 'delta'>[] = TEACHER_KNOWLEDGE_UNIVERSE.map(
  (domain) => {
    const layout = ORBIT_LAYOUT[domain.key] ?? { tone: 'amber' as const, x: 50, y: 50 }
    return {
      label: domain.label,
      domainKey: domain.key,
      ...layout,
    }
  },
)

const DELTA_CYCLE: OrbitNode['delta'][] = ['上升', '稳定', '下降']

const STUDENT_DOMAIN_LAYOUT: Record<string, Pick<OrbitNode, 'tone' | 'x' | 'y'>> = {
  stage1: { tone: 'teal', x: 11, y: 30 },
  stage2: { tone: 'amber', x: 34, y: 10 },
  stage3: { tone: 'gold', x: 72, y: 18 },
  stage4: { tone: 'teal', x: 86, y: 62 },
  lang: { tone: 'teal', x: 18, y: 28 },
  algo: { tone: 'amber', x: 43, y: 16 },
  dp: { tone: 'gold', x: 68, y: 24 },
  geom: { tone: 'teal', x: 78, y: 52 },
  graph: { tone: 'red', x: 58, y: 76 },
  ds: { tone: 'amber', x: 24, y: 72 },
  'data-vars': { tone: 'teal', x: 12, y: 26 },
  operators: { tone: 'amber', x: 30, y: 10 },
  'flow-control': { tone: 'gold', x: 52, y: 8 },
  strings: { tone: 'teal', x: 74, y: 22 },
  'lists-dicts': { tone: 'amber', x: 88, y: 48 },
  functions: { tone: 'gold', x: 70, y: 74 },
  'recursion-iter': { tone: 'red', x: 26, y: 76 },
}

const ORBIT_TONE_CYCLE: OrbitNodeTone[] = ['teal', 'amber', 'gold', 'teal', 'amber', 'red', 'gold']

/** 将节点均匀分布在椭圆轨道上，避免默认 (50,50) 堆叠 */
export function layoutOrbitPosition(index: number, total: number): Pick<OrbitNode, 'x' | 'y'> {
  if (total <= 0) return { x: 50, y: 52 }
  const angle = (2 * Math.PI * index) / total - Math.PI / 2
  const ring = index % 2 === 0 ? 1 : 0.82
  return {
    x: Math.round((50 + 36 * ring * Math.cos(angle)) * 10) / 10,
    y: Math.round((52 + 30 * ring * Math.sin(angle)) * 10) / 10,
  }
}

export function resolveOrbitLayout(
  domainKey: string,
  index: number,
  total: number,
): Pick<OrbitNode, 'tone' | 'x' | 'y'> {
  const preset = STUDENT_DOMAIN_LAYOUT[domainKey] ?? ORBIT_LAYOUT[domainKey]
  if (preset) return preset
  const pos = layoutOrbitPosition(index, total)
  return { ...pos, tone: ORBIT_TONE_CYCLE[index % ORBIT_TONE_CYCLE.length] ?? 'amber' }
}

/** 与学生端六大学域标签一致的星域节点（有 class-stats 时优先） */
export function buildStudentDomainStarfieldNodes(
  overview: TeacherOverview | null,
  classStats: TeacherClassStatsResult | null,
): OrbitNode[] {
  const avg = overview?.metrics?.avg_today_completion ?? 72
  const attention = overview?.metrics?.attention_count ?? 0
  const masteryMap = new Map(
    (classStats?.domain_mastery ?? []).map((item) => [item.label, item.mastery_rate]),
  )
  const tabs = STAR_PATH_TABS.filter((tab) => tab.key !== 'all')
  return tabs.map((tab, index) => {
    const layout = resolveOrbitLayout(tab.key, index, tabs.length)
    const score = masteryMap.get(tab.label) ?? Math.max(42, Math.min(98, Math.round(avg + index * 2)))
    let delta: OrbitNode['delta'] = score >= 75 ? '上升' : score < 50 ? '下降' : '稳定'
    if (attention > 2 && layout.tone === 'red') delta = '下降'
    return {
      label: tab.label,
      domainKey: tab.key,
      ...layout,
      score,
      delta,
    }
  })
}

export function buildClassStarfieldNodes(
  overview: TeacherOverview | null,
  classStats?: TeacherClassStatsResult | null,
): OrbitNode[] {
  if (classStats?.domain_mastery?.length) {
    return buildStudentDomainStarfieldNodes(overview, classStats)
  }
  const avg = overview?.metrics?.avg_today_completion ?? 72
  const attention = overview?.metrics?.attention_count ?? 0
  return STARFIELD_DOMAINS.map((item, index) => {
    const domainKey = item.domainKey ?? `domain-${index}`
    const layout = resolveOrbitLayout(domainKey, index, STARFIELD_DOMAINS.length)
    const baseScore = [78, 85, 69, 90, 74, 63][index] ?? 70
    const score = Math.max(42, Math.min(98, Math.round((baseScore + avg + index * 2) / 2)))
    let delta: OrbitNode['delta'] = DELTA_CYCLE[index % 3]
    if (item.tone === 'red' || attention > 2) {
      delta = index % 2 === 0 ? '下降' : '稳定'
    } else if (score >= 80) {
      delta = '上升'
    }
    return { ...item, ...layout, score, delta }
  })
}

export function buildRiskTrend(overview: TeacherOverview | null): number[] {
  const rows = overview?.heatmap?.rows ?? []
  const dayCount = overview?.heatmap?.days?.length ?? 0
  if (!rows.length || !dayCount) {
    return [42, 48, 44, 52, 58, 72, 68, 64, 70]
  }
  return Array.from({ length: Math.min(dayCount, 9) }, (_, idx) => {
    const rates = rows.map((row) => row.cells[idx]?.rate ?? 0)
    return Math.round(rates.reduce((sum, value) => sum + value, 0) / Math.max(1, rates.length))
  })
}

export function buildStarfieldKpis(overview: TeacherOverview | null) {
  const activity = overview?.metrics?.avg_today_completion ?? 0
  const repair = Math.max(0, Math.min(100, Math.round(activity * 0.92 + 8)))
  const trial = Math.max(0, Math.min(100, Math.round(activity * 0.85 + 5)))
  const trend = buildRiskTrend(overview)
  return [
    { key: 'activity', label: '探索活跃度', value: `${activity}%`, delta: '+6%', points: trend },
    { key: 'repair', label: '知识修复率', value: `${repair}%`, delta: '+4%', points: trend.map((v) => Math.max(20, v - 6)) },
    { key: 'trial', label: '试炼完成率', value: `${trial}%`, delta: '+3%', points: trend.map((v) => Math.max(18, v - 12)) },
  ]
}

export function buildStarfieldInsight(overview: TeacherOverview | null, nodes: OrbitNode[]) {
  const risky = nodes.find((node) => node.tone === 'red' || node.delta === '下降')
  const subject = risky?.label ?? '递归边界条件'
  const attention = overview?.attention_students?.[0]
  const studentHint = attention
    ? `${attention.real_name || attention.username} 等学生需要跟进。`
    : '建议对低活跃学生追加可视化训练。'
  return {
    subject,
    copy: `班级在「${subject}」相关路径波动明显，${studentHint}`,
    rate: Math.max(0, Math.min(100, 100 - (overview?.metrics?.attention_count ?? 0) * 9)),
  }
}

export function buildRiskCopy(overview: TeacherOverview | null, riskPoints: number[]): string {
  const attention = overview?.metrics?.attention_count ?? 0
  if (!riskPoints.length) {
    return attention > 0
      ? `班级有 ${attention} 名 Explorer 需要跟进，建议优先处理委托完成率偏低的学生。`
      : '班级委托完成率整体稳定，可继续推进挑战任务。'
  }
  const latest = riskPoints[riskPoints.length - 1] ?? 0
  const prev = riskPoints.length > 1 ? riskPoints[riskPoints.length - 2]! : latest
  const delta = latest - prev
  const risky = buildClassStarfieldNodes(overview).find((n) => n.delta === '下降') ?? buildClassStarfieldNodes(overview)[0]
  const subject = risky?.label ?? '核心星域'
  if (delta >= 8) {
    return `「${subject}」相关委托完成率近期上升 ${Math.abs(delta)}%，班级活跃度改善。`
  }
  if (delta <= -8) {
    return `「${subject}」相关委托完成率近期下降 ${Math.abs(delta)}%，建议对低活跃学生追加辅导。`
  }
  return `「${subject}」波动较小（约 ${latest}% 完成率），${attention} 名学生仍需跟进。`
}

export function polylineFromPoints(points: number[], width = 290, height = 100): string {
  const max = Math.max(100, ...points)
  return points
    .map((value, idx) => {
      const x = points.length <= 1 ? 0 : (idx / (points.length - 1)) * (width - 2)
      const y = height - Math.round((value / max) * (height - 18))
      return `${x},${y}`
    })
    .join(' ')
}
