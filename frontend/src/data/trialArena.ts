import type { Component } from 'vue'
import {
  HardwareChipOutline,
  TrophyOutline,
  TimerOutline,
  DiamondOutline,
  PeopleOutline,
  SparklesOutline,
} from '@vicons/ionicons5'
import type { StudentTrial } from '../api/studentTrials'

export type TrialPosition = 'tl' | 'tr' | 'bl' | 'br'
export type TrialTheme = 'teal' | 'purple' | 'orange' | 'pink'

const POSITIONS: TrialPosition[] = ['tl', 'tr', 'bl', 'br']
const THEMES: TrialTheme[] = ['teal', 'purple', 'orange', 'pink']

/** 卡片中心锚点（百分比），与 TrialArenaMap 连线 SVG 一致 */
export const TRIAL_ANCHORS: Record<TrialPosition, { x: number; y: number }> = {
  tl: { x: 19, y: 28 },
  tr: { x: 81, y: 28 },
  bl: { x: 19, y: 72 },
  br: { x: 81, y: 72 },
}

export interface TrialMode {
  key: string
  number: string
  title: string
  titleEn: string
  description: string
  icon: Component
  theme: TrialTheme
  position: TrialPosition
  requiredLevel: number
  durationMin: number
  difficulty: number
  rewardCrystal: number
  tags?: string[]
  /** 后端试炼 ID（API 数据时有值） */
  trialId?: number
  effectiveStatus?: string
}

const TYPE_ICONS: Record<string, Component> = {
  solo: TimerOutline,
  team: PeopleOutline,
  timed: SparklesOutline,
  abyss: DiamondOutline,
}

const TYPE_EN: Record<string, string> = {
  solo: 'SOLO RUN',
  team: 'TEAM TRIAL',
  timed: 'TIMED RUSH',
  abyss: 'ABYSS GATE',
}

export const TRIAL_MODES: TrialMode[] = [
  {
    key: 'ai-duel',
    number: '01',
    title: 'AI 对抗试炼',
    titleEn: 'AI DUEL',
    description: '与驿站 AI 实时对战，挑战最高难度。',
    icon: HardwareChipOutline,
    theme: 'teal',
    position: 'tl',
    requiredLevel: 1,
    durationMin: 15,
    difficulty: 3,
    rewardCrystal: 12,
    tags: ['推荐', '实时'],
  },
  {
    key: 'star-arena',
    number: '02',
    title: '星域竞技',
    titleEn: 'STAR ARENA',
    description: '匹配真实玩家，进行时间限制对决。',
    icon: TrophyOutline,
    theme: 'purple',
    position: 'tr',
    requiredLevel: 5,
    durationMin: 20,
    difficulty: 4,
    rewardCrystal: 18,
    tags: ['PVP'],
  },
  {
    key: 'echo-run',
    number: '03',
    title: '自我突破',
    titleEn: 'ECHO RUN',
    description: '挑战过去的自己，刷新最佳记录。',
    icon: TimerOutline,
    theme: 'orange',
    position: 'bl',
    requiredLevel: 3,
    durationMin: 10,
    difficulty: 2,
    rewardCrystal: 8,
    tags: ['单人'],
  },
  {
    key: 'abyss-trial',
    number: '04',
    title: '深渊试炼',
    titleEn: 'ABYSS TRIAL',
    description: '迎战深空的星域 Boss，赢取稀有奖励。',
    icon: DiamondOutline,
    theme: 'pink',
    position: 'br',
    requiredLevel: 20,
    durationMin: 45,
    difficulty: 5,
    rewardCrystal: 50,
    tags: ['Boss', '稀有'],
  },
]

export function mapApiTrialsToArenaModes(trials: StudentTrial[], userLevel = 1): TrialMode[] {
  if (!trials.length) return []

  return trials.slice(0, 4).map((trial, index) => {
    const position = POSITIONS[index % POSITIONS.length]
    const theme = THEMES[index % THEMES.length]
    const icon = TYPE_ICONS[trial.trial_type] ?? HardwareChipOutline
    const effective = (trial as StudentTrial & { effective_status?: string }).effective_status ?? trial.status
    const statusTag =
      effective === 'scheduled' ? '即将开始' : trial.my_status === 'completed' ? '已完成' : '可参与'

    return {
      key: `trial-${trial.id}`,
      trialId: trial.id,
      effectiveStatus: effective,
      number: String(index + 1).padStart(2, '0'),
      title: trial.title,
      titleEn: TYPE_EN[trial.trial_type] ?? 'CLASS TRIAL',
      description: `班级试炼 · 难度 ${trial.difficulty} · 奖励 ${trial.reward_points} XP`,
      icon,
      theme,
      position,
      requiredLevel: effective === 'running' ? 1 : Math.max(userLevel, 1),
      durationMin: trial.duration_minutes,
      difficulty: Math.min(5, Math.max(1, Math.round(trial.difficulty / 20))),
      rewardCrystal: trial.reward_points,
      tags: [statusTag],
    }
  })
}

export function isTrialUnlocked(trial: TrialMode, userLevel: number) {
  if (trial.trialId) {
    return trial.effectiveStatus === 'running'
  }
  return userLevel >= trial.requiredLevel
}

export function filterTrials(query: string, trials: TrialMode[] = TRIAL_MODES) {
  const q = query.trim().toLowerCase()
  if (!q) return trials
  return trials.filter(
    (t) =>
      t.title.toLowerCase().includes(q) ||
      t.titleEn.toLowerCase().includes(q) ||
      t.description.toLowerCase().includes(q) ||
      t.tags?.some((tag) => tag.toLowerCase().includes(q)),
  )
}
