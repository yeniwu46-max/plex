import type { PointsLogRecord } from '../api/studentOverview'

const DAILY_QUEST_LABELS: Record<string, string> = {
  'morning-launch': '晨间启动',
  'fragment-repair': '修复知识碎片',
  'trial-challenge': '试炼挑战',
  'night-summary': '夜间总结',
}

const REASON_TITLE_MAP: Record<string, string> = {
  daily_quest_bonus: '领取今日委托全完成奖励',
  trial_completed: '完成班级试炼',
  trial_join: '参与班级试炼',
  level_up: '等级提升',
  achievement_unlock: '解锁成就',
  emergency_mission: '完成补给站紧急任务',
  personalized_resource: '完成个性化学习资源',
  star_path_progress: '星轨节点推进',
}

export interface GrowthEventDisplay {
  title: string
  description: string
}

export function formatGrowthEvent(log: PointsLogRecord): GrowthEventDisplay {
  const reason = (log.reason || '').trim()
  const points = log.points

  if (reason.startsWith('daily_quest:')) {
    const key = reason.slice('daily_quest:'.length)
    const questTitle = DAILY_QUEST_LABELS[key] || key.replace(/-/g, ' ')
    return {
      title: `完成今日委托「${questTitle}」`,
      description: `委托奖励 +${points} XP，已写入成长轨迹`,
    }
  }

  if (REASON_TITLE_MAP[reason]) {
    return {
      title: REASON_TITLE_MAP[reason],
      description: `本次获得 ${points} XP`,
    }
  }

  if (reason.includes(':')) {
    const [prefix, suffix] = reason.split(':', 2)
    const prefixLabels: Record<string, string> = {
      daily_quest: '今日委托',
      trial: '试炼',
      quest: '委托',
      achievement: '成就',
    }
    const prefixLabel = prefixLabels[prefix] || prefix
    const suffixLabel = DAILY_QUEST_LABELS[suffix] || suffix.replace(/-/g, ' ')
    return {
      title: `${prefixLabel} · ${suffixLabel}`,
      description: `获得 ${points} XP`,
    }
  }

  return {
    title: reason || '学习反馈',
    description: `获得 ${points} XP`,
  }
}
