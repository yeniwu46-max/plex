import type { MessageApi } from 'naive-ui'

export interface IncentiveFeedback {
  level_up?: boolean
  previous_level?: number
  level?: number
  title?: string
  points_gained?: number
  class_rank?: number | null
  unlocked_achievements?: Array<{ name: string; rarity?: string }>
}

export function showIncentiveFeedback(message: MessageApi, feedback?: IncentiveFeedback | null) {
  if (!feedback) return
  if (feedback.level_up && feedback.level) {
    message.success(`恭喜升级至 Lv.${feedback.level} · ${feedback.title ?? ''}`.trim())
  }
  if (feedback.unlocked_achievements?.length) {
    const names = feedback.unlocked_achievements.map((item) => item.name).join('、')
    message.info(`解锁成就：${names}`)
  }
  if (feedback.class_rank && (feedback.points_gained ?? 0) > 0) {
    message.success(`获得 ${feedback.points_gained} XP，班级排名第 ${feedback.class_rank} 名`)
  } else if ((feedback.points_gained ?? 0) > 0 && !feedback.level_up) {
    message.success(`获得 ${feedback.points_gained} XP`)
  }
}
