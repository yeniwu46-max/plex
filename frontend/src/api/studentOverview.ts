import { http, type ApiEnvelope } from './http'

export interface LevelProfile {
  level: number
  title: string
  total_points: number
  current_threshold: number
  next_threshold: number | null
  points_to_next_level: number
  progress_percent: number
  max_level: number
}

export interface IncentiveSummary {
  level_profile: LevelProfile
  class_rank: number | null
  achievements_unlocked: number
  achievements_total: number
  week_key: string
  week_points: number
  next_achievements: Array<{
    id: number
    name: string
    description: string | null
    rarity: string
    current_value: number
    target_value: number
    progress_percent: number
  }>
}

export interface CurrentStudent {
  id: number
  username: string
  email: string
  real_name: string | null
  avatar_url: string | null
  phone: string | null
  gender: string | null
  bio: string | null
  role: string | null
  status: string
  level: number
  title?: string
  total_points: number
  consecutive_days: number
  achievements_count: number
  class_rank: number | null
  level_profile?: LevelProfile
  incentive?: IncentiveSummary
  class: {
    id: number
    name: string
  } | null
}

export interface UserAchievementRecord {
  id: number
  user_id: number
  achievement_id: number
  achievement?: {
    id: number
    name: string
    description: string | null
    icon_url: string | null
    rarity: string
    condition_type: string | null
    condition_value: number | null
    created_at: string | null
  } | null
  unlocked_at: string | null
}

export interface UserAchievementsResult {
  user_id: number
  achievements: UserAchievementRecord[]
  count: number
}

export interface PointsLogRecord {
  id: number
  user_id: number
  points: number
  reason: string | null
  related_id: number | null
  created_at: string | null
}

export interface PointsLogResult {
  total: number
  page: number
  limit: number
  logs: PointsLogRecord[]
}

export interface RankingRecord {
  id: number
  class_id: number
  user_id: number
  user_name?: string | null
  rank: number
  points: number
  week: string
  created_at?: string | null
  updated_at?: string | null
}

export interface ClassRankingResult {
  class_id: number
  week: string | null
  rankings: RankingRecord[]
}

export interface DailyQuestRecord {
  id: number
  user_id?: number
  quest_id?: number
  quest_date?: string | null
  key: string
  title: string
  description: string | null
  period: string
  time: string
  total: number
  reward_xp: number
  bonus_eligible: boolean
  sort_order?: number
  current: number
  completed: boolean
  completed_at: string | null
  reward_claimed: boolean
  reward_claimed_at: string | null
}

export interface IncentiveFeedbackPayload {
  level_up?: boolean
  level?: number
  title?: string
  points_gained?: number
  class_rank?: number | null
  unlocked_achievements?: Array<{ name: string; rarity?: string }>
}

export interface DailyQuestTodayResult {
  date: string
  quests: DailyQuestRecord[]
  completed_count: number
  total_count: number
  total_required: number
  total_current: number
  earned_xp: number
  bonus_xp: number
  bonus_claimed: boolean
  all_completed: boolean
  incentive?: IncentiveFeedbackPayload
}

export interface StudentOverview {
  profile: CurrentStudent
  achievements: UserAchievementsResult | null
  pointsLog: PointsLogResult | null
  ranking: ClassRankingResult | null
  daily: DailyQuestTodayResult | null
}

function resolvedOrNull<T>(result: PromiseSettledResult<T>) {
  return result.status === 'fulfilled' ? result.value : null
}

export async function fetchCurrentStudent() {
  const { data } = await http.get<ApiEnvelope<CurrentStudent>>('/v1/users/me')
  if (data.code !== 0) {
    throw new Error(data.message || '获取学生信息失败')
  }
  return data.data
}

export async function fetchUserAchievements(userId: number) {
  const { data } = await http.get<ApiEnvelope<UserAchievementsResult>>(`/v1/achievements/user/${userId}`)
  if (data.code !== 0) {
    throw new Error(data.message || '获取成就失败')
  }
  return data.data
}

export async function fetchPointsLog(userId: number, limit = 6) {
  const { data } = await http.get<ApiEnvelope<PointsLogResult>>(`/v1/achievements/points-log/${userId}`, {
    params: { page: 1, limit },
  })
  if (data.code !== 0) {
    throw new Error(data.message || '获取积分日志失败')
  }
  return data.data
}

export async function fetchClassRanking(classId: number) {
  const { data } = await http.get<ApiEnvelope<ClassRankingResult>>(`/v1/classes/${classId}/ranking`)
  if (data.code !== 0) {
    throw new Error(data.message || '获取班级排名失败')
  }
  return data.data
}

export async function fetchTodayDailyQuests() {
  const { data } = await http.get<ApiEnvelope<DailyQuestTodayResult>>('/v1/daily-quests/today')
  if (data.code !== 0) {
    throw new Error(data.message || 'Failed to load daily quests')
  }
  return data.data
}

export async function advanceDailyQuest(key: string) {
  const { data } = await http.post<ApiEnvelope<DailyQuestTodayResult>>(
    `/v1/daily-quests/${encodeURIComponent(key)}/progress`,
  )
  if (data.code !== 0) {
    throw new Error(data.message || 'Failed to update daily quest')
  }
  return data.data
}

export async function claimDailyQuestBonus() {
  const { data } = await http.post<ApiEnvelope<DailyQuestTodayResult>>('/v1/daily-quests/claim-bonus')
  if (data.code !== 0) {
    throw new Error(data.message || 'Failed to claim daily quest bonus')
  }
  return data.data
}

export async function fetchStudentOverview(): Promise<StudentOverview> {
  const profile = await fetchCurrentStudent()
  const [achievements, pointsLog, ranking, daily] = await Promise.allSettled([
    fetchUserAchievements(profile.id),
    fetchPointsLog(profile.id),
    profile.class?.id ? fetchClassRanking(profile.class.id) : Promise.resolve(null),
    fetchTodayDailyQuests(),
  ])

  return {
    profile,
    achievements: resolvedOrNull(achievements),
    pointsLog: resolvedOrNull(pointsLog),
    ranking: resolvedOrNull(ranking),
    daily: resolvedOrNull(daily),
  }
}
