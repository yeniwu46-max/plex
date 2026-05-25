import { http, type ApiEnvelope } from './http'

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

export interface StudentOverview {
  profile: CurrentStudent
  achievements: UserAchievementsResult | null
  pointsLog: PointsLogResult | null
  ranking: ClassRankingResult | null
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

export async function fetchStudentOverview(): Promise<StudentOverview> {
  const profile = await fetchCurrentStudent()
  const [achievements, pointsLog, ranking] = await Promise.allSettled([
    fetchUserAchievements(profile.id),
    fetchPointsLog(profile.id),
    profile.class?.id ? fetchClassRanking(profile.class.id) : Promise.resolve(null),
  ])

  return {
    profile,
    achievements: resolvedOrNull(achievements),
    pointsLog: resolvedOrNull(pointsLog),
    ranking: resolvedOrNull(ranking),
  }
}
