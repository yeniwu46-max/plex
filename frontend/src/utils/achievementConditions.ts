export interface AchievementConditionSource {
  condition_type?: string | null
  condition_value?: number | null
  description?: string | null
}

const CONDITION_FORMATTERS: Record<string, (target: number) => string> = {
  total_points: (target) => `累计获得 ${target} XP`,
  level: (target) => `达到 Lv.${target}`,
  consecutive_days: (target) => `连续探索 ${target} 天`,
  trials_completed: (target) => `完成 ${target} 次班级试炼`,
  daily_quests_completed: (target) => `累计完成 ${target} 条每日委托`,
  complete_course: (target) => (target <= 1 ? '完成第一条每日委托' : `完成 ${target} 项课程目标`),
}

export function formatAchievementCondition(achievement: AchievementConditionSource): string {
  if (achievement.description?.trim()) {
    return achievement.description.trim()
  }
  const type = achievement.condition_type
  const target = achievement.condition_value ?? 0
  if (type && CONDITION_FORMATTERS[type]) {
    return CONDITION_FORMATTERS[type](target)
  }
  if (type && target > 0) {
    return `达成条件：${type} ≥ ${target}`
  }
  return '继续探索以解锁此徽章'
}

export function formatAchievementProgress(current: number, target: number): string {
  if (target <= 0) return '进度未知'
  return `${Math.min(current, target)} / ${target}`
}
