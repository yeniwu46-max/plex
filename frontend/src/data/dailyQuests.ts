export type QuestAccent = 'teal' | 'amber' | 'blue' | 'purple'

export interface DailyQuestDefinition {
  key: string
  period: string
  time: string
  title: string
  description: string
  accent: QuestAccent
  total: number
  rewardXp: number
}

export const DAILY_QUESTS: DailyQuestDefinition[] = [
  {
    key: 'morning-launch',
    period: '晨间',
    time: '08:00',
    title: '晨间启动',
    description: '查看今日推荐路线，开启探索之旅',
    accent: 'teal',
    total: 1,
    rewardXp: 20,
  },
  {
    key: 'fragment-repair',
    period: '上午',
    time: '10:00',
    title: '修复知识碎片',
    description: '修复 2 个知识碎片，填补认知缺口',
    accent: 'amber',
    total: 2,
    rewardXp: 40,
  },
  {
    key: 'trial-challenge',
    period: '下午',
    time: '14:00',
    title: '试炼挑战',
    description: '完成 1 次试炼关卡挑战',
    accent: 'blue',
    total: 1,
    rewardXp: 35,
  },
  {
    key: 'night-summary',
    period: '夜晚',
    time: '21:00',
    title: '夜间总结',
    description: '生成今日成长报告，记录进步',
    accent: 'purple',
    total: 1,
    rewardXp: 25,
  },
]

export const DAILY_BONUS_XP = 120
export const DAILY_BONUS_STAR_KEYS = 1
