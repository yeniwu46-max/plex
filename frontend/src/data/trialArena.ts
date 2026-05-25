import type { Component } from 'vue'
import {
  HardwareChipOutline,
  TrophyOutline,
  TimerOutline,
  DiamondOutline,
} from '@vicons/ionicons5'

export type TrialPosition = 'tl' | 'tr' | 'bl' | 'br'
export type TrialTheme = 'teal' | 'purple' | 'orange' | 'pink'

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
  /** 占位：预估时长（分钟） */
  durationMin: number
  /** 占位：难度 1–5 */
  difficulty: number
  /** 占位：奖励结晶 */
  rewardCrystal: number
  tags?: string[]
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

export function isTrialUnlocked(trial: TrialMode, userLevel: number) {
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
