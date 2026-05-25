/** 探索档案页展示数据（后端未上线前使用，日后可改由 MSW / API 提供） */

export interface ArchiveProfile {
  displayName: string
  explorerId: string
  level: number
  rankTitle: string
  streakDays: number
}

export interface GrowthEvent {
  id: string
  title: string
  date: string
  description: string
  tone: 'teal' | 'gold' | 'blue' | 'purple'
}

export interface SkillItem {
  key: string
  label: string
  percent: number
}

export interface AchievementItem {
  id: string
  title: string
  date?: string
  tone: 'teal' | 'gold' | 'blue' | 'locked'
  locked?: boolean
}

export const archiveProfile: ArchiveProfile = {
  displayName: '张子轩',
  explorerId: 'PX-2037-AX',
  level: 18,
  rankTitle: '深空 Explorer',
  streakDays: 5,
}

export const explorationTendency = {
  label: '算法探索型',
  description: '善于拆解复杂问题，在抽象建模与逻辑推演中突破思维边界。',
}

export const growthTimeline: GrowthEvent[] = [
  {
    id: '1',
    title: '加入 PLEX 宇宙',
    date: '2025-09-01',
    description: '开启你的第一段星轨探索之旅。',
    tone: 'teal',
  },
  {
    id: '2',
    title: '完成首个星域',
    date: '2025-10-12',
    description: '通过算法基础星域全部核心节点。',
    tone: 'gold',
  },
  {
    id: '3',
    title: '试炼连胜纪录',
    date: '2026-01-08',
    description: '连续 5 次试炼挑战获得 A 评级。',
    tone: 'blue',
  },
  {
    id: '4',
    title: '解锁深空称号',
    date: '2026-03-20',
    description: '总积分突破 3000，晋升深空 Explorer。',
    tone: 'purple',
  },
]

export const skillDistribution: SkillItem[] = [
  { key: 'algo', label: '算法', percent: 88 },
  { key: 'ds', label: '数据结构', percent: 76 },
  { key: 'fe', label: '前端', percent: 62 },
  { key: 'be', label: '后端', percent: 54 },
  { key: 'db', label: '数据库', percent: 48 },
]

export const achievements: AchievementItem[] = [
  { id: 'a1', title: '初心探索', date: '2025-09-15', tone: 'teal' },
  { id: 'a2', title: '连续学习', date: '2025-11-02', tone: 'gold' },
  { id: 'a3', title: '试炼达人', date: '2026-01-20', tone: 'blue' },
  { id: 'a4', title: '待解锁', tone: 'locked', locked: true },
]
