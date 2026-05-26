import type { HeatmapRow } from '../api/teacherOverview'
import type { TeacherStudentRow } from '../api/teacherOverview'
import type { UserAchievementRecord } from '../api/studentOverview'

export interface RadarDimension {
  key: string
  label: string
  value: number
}

export interface GrowthPoint {
  label: string
  value: number
}

export interface ExplorerStatCard {
  key: string
  label: string
  value: string
  delta: string
}

export interface RiskTodoItem {
  id: string
  text: string
  level: '高风险' | '中风险' | '低风险'
}

const RADAR_LABELS = [
  '知识掌握',
  '逻辑思维',
  '问题解决',
  '试炼表现',
  '探索活跃',
  '知识应用',
]

function seededValue(seed: number, min: number, max: number) {
  const x = Math.sin(seed * 12.9898) * 43758.5453
  const frac = x - Math.floor(x)
  return Math.round(min + frac * (max - min))
}

export function buildExplorerRadar(studentId: number): RadarDimension[] {
  return RADAR_LABELS.map((label, index) => ({
    key: `d${index}`,
    label,
    value: seededValue(studentId * 17 + index * 3, 58, 95),
  }))
}

function clampScore(value: number) {
  return Math.max(42, Math.min(98, Math.round(value)))
}

export function buildExplorerRadarFromStudent(
  student: TeacherStudentRow,
  achievements: UserAchievementRecord[] = [],
): RadarDimension[] {
  const levelScore = clampScore(((student.level ?? 1) / 10) * 100)
  const pointsScore = clampScore(Math.min(100, (student.total_points ?? 0) / 30))
  const questScore = clampScore(student.today_completion_rate ?? 0)
  const streakScore = clampScore(Math.min(100, (student.consecutive_days ?? 0) * 12))
  const achievementScore = clampScore(Math.min(100, (student.achievements_count ?? 0) * 14 + achievements.length * 4))
  const activeScore = clampScore(student.is_inactive_7d ? 38 : 88 - (student.inactive_days ?? 0) * 6)
  const values = [questScore, levelScore, pointsScore, activeScore, streakScore, achievementScore]
  return RADAR_LABELS.map((label, index) => ({
    key: `d${index}`,
    label,
    value: values[index] ?? 70,
  }))
}

export function buildGrowthSeries(student: TeacherStudentRow, period: 'week' | 'month'): GrowthPoint[] {
  const days = period === 'month' ? 14 : 7
  const base = Math.max(800, student.total_points - 120)
  const labels =
    period === 'month'
      ? ['04.05', '04.08', '04.11', '04.14', '04.17', '04.20', '04.23']
      : ['05.12', '05.13', '05.14', '05.15', '05.16', '05.17', '05.18']
  return Array.from({ length: Math.min(days, labels.length) }, (_, idx) => ({
    label: labels[idx] ?? `D${idx + 1}`,
    value: base + seededValue(student.id + idx, 0, 80) + idx * 12,
  }))
}

export function buildGrowthSeriesFromHeatmap(
  heatmapRow: HeatmapRow | null,
  period: 'week' | 'month',
  student: TeacherStudentRow,
): GrowthPoint[] {
  if (!heatmapRow?.cells?.length) {
    return buildGrowthSeries(student, period)
  }
  const maxCells = period === 'month' ? 14 : 7
  const cells = heatmapRow.cells.slice(-maxCells)
  return cells.map((cell) => ({
    label: cell.date.slice(5).replace('-', '.'),
    value: cell.rate,
  }))
}

export function buildExplorerStats(student: TeacherStudentRow): ExplorerStatCard[] {
  const todayRate = student.today_completion_rate ?? 0
  return [
    { key: 'points', label: '探索积分', value: String(student.total_points ?? 0), delta: `Lv${student.level ?? 1}` },
    {
      key: 'quests',
      label: '今日委托',
      value: `${student.today_completed ?? 0}/${student.today_total ?? 0}`,
      delta: `${todayRate}%`,
    },
    {
      key: 'achievements',
      label: '成就勋章',
      value: String(student.achievements_count ?? 0),
      delta: `${student.consecutive_days ?? 0} 天连续`,
    },
    { key: 'trials', label: '试炼完成', value: '—', delta: '待试炼系统' },
  ]
}

export function buildOverallStatus(student: TeacherStudentRow): number {
  const completion = student.today_completion_rate ?? 0
  const base = seededValue(student.id, 68, 88)
  return Math.max(55, Math.min(96, Math.round((base + completion) / 2)))
}

export function buildRiskTodos(student: TeacherStudentRow): RiskTodoItem[] {
  const items: RiskTodoItem[] = (student.reasons ?? []).slice(0, 3).map((text, index) => ({
    id: `reason-${index}`,
    text,
    level: text.includes('冻结') || text.includes('无积分') ? '高风险' : '中风险',
  }))
  const fallbacks: RiskTodoItem[] = [
    { id: 'f1', text: '递归边界条件理解波动较大', level: '中风险' },
    { id: 'f2', text: '最近 2 次深渊试炼失败', level: '高风险' },
    { id: 'f3', text: '知识修复速度下降', level: '中风险' },
  ]
  while (items.length < 3) {
    const next = fallbacks[items.length]
    if (next) items.push(next)
  }
  return items
}

export function buildAiObservation(student: TeacherStudentRow, radar: RadarDimension[]): string {
  const top = [...radar].sort((a, b) => b.value - a.value)[0]
  const name = student.real_name || student.username
  return `${name} 在「${top?.label ?? '动态规划'}」领域表现突出，建议挑战更高难度试炼。`
}

export function explorerDisplayId(student: TeacherStudentRow): string {
  return `EXP-${new Date().getFullYear()}${String(student.id).padStart(4, '0')}`
}

export function formatLastActive(iso: string | null): string {
  if (!iso) return '暂无记录'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '暂无记录'
  return date.toLocaleString('zh-CN', { hour: '2-digit', minute: '2-digit', month: '2-digit', day: '2-digit' })
}

export function studentStatusLabel(student: TeacherStudentRow): string {
  if (student.status === 'frozen') return '冻结'
  if (student.is_inactive_7d) return '离线'
  if ((student.today_completion_rate ?? 0) > 0) return '探索中'
  return '在线'
}
