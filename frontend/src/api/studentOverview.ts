import { http, type ApiEnvelope } from './http'
import type { TeacherAssignmentsResult } from './studentAssignments'

export interface LevelProfile {
  level: number
  title: string
  total_points: number
  current_threshold: number
  next_threshold: number | null
  points_to_next_level: number
  progress_percent: number
  max_level: number
  at_max_level?: boolean
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
    join_code?: string | null
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
  total_points?: number
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
  teacher_assignments?: TeacherAssignmentsResult
  incentive?: IncentiveFeedbackPayload
}

export interface StudentOverview {
  profile: CurrentStudent
  achievements: UserAchievementsResult | null
  pointsLog: PointsLogResult | null
  ranking: ClassRankingResult | null
  daily: DailyQuestTodayResult | null
  running_trials: number
  class_online_count?: number
}

export async function fetchCurrentStudent() {
  const { data } = await http.get<ApiEnvelope<CurrentStudent>>('/v1/users/me')
  if (data.code !== 0) {
    throw new Error(data.message || '获取学生信息失败')
  }
  return data.data
}

export interface AchievementCatalogItem {
  id: number
  name: string
  description: string | null
  icon_url: string | null
  rarity: string
  condition_type: string | null
  condition_value: number | null
  created_at?: string | null
}

export async function fetchAchievementsCatalog() {
  const { data } = await http.get<ApiEnvelope<AchievementCatalogItem[]>>('/v1/achievements')
  if (data.code !== 0) {
    throw new Error(data.message || '获取成就目录失败')
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
  const { data } = await http.get<ApiEnvelope<StudentOverview>>('/v1/student/overview')
  if (data.code !== 0) {
    throw new Error(data.message || '获取学生总览失败')
  }
  return data.data
}

export interface StatDetailsLevelHistoryItem {
  level: number
  title: string
  total_points: number
  reached_at: string | null
}

export interface StatDetailsHeatmapCell {
  date: string
  count: number
  level: number
  in_current_month: boolean
  month?: string
  weekday?: number
  weekday_label?: string
  day?: number
}

export interface ClassmateRankItem {
  user_id?: number
  user_name?: string | null
  real_name?: string | null
  username?: string | null
  rank: number
  points: number
  week_points?: number
  level?: number
  title?: string | null
  total_points?: number
  win_count?: number
  win_rank?: number
  online?: boolean
}

export interface StatDetailsResult {
  level_profile: LevelProfile
  level_history: StatDetailsLevelHistoryItem[]
  practice_heatmap: {
    month: string
    months?: string[]
    cells: StatDetailsHeatmapCell[]
    weekday_headers?: string[]
    legend: Array<{ level: number; label: string; min: number; max: number | null }>
  }
  class_rank_detail: {
    rank: number | null
    level: number
    title: string | null
    total_solved: number
    total_points: number
    consecutive_days: number
    class_name: string | null
    classmates: ClassmateRankItem[]
    win_leaderboard?: ClassmateRankItem[]
  }
}

export async function fetchStatDetails() {
  const { data } = await http.get<ApiEnvelope<StatDetailsResult>>('/v1/student/stat-details')
  if (data.code !== 0) {
    throw new Error(data.message || '获取统计详情失败')
  }
  return data.data
}

export interface StudentPresenceResult {
  class_id: number | null
  online_count: number
  ttl_seconds: number
  updated_at: string
}

export async function heartbeatStudentPresence() {
  const { data } = await http.post<ApiEnvelope<StudentPresenceResult>>('/v1/student/presence/heartbeat')
  if (data.code !== 0) {
    throw new Error(data.message || '在线状态更新失败')
  }
  return data.data
}

export interface DuelWinResult {
  user_id: number
  opponent_id: number | null
  win_count: number
  total_points: number
  level: number
}

export async function recordDuelWin(opponentId?: number | null) {
  const { data } = await http.post<ApiEnvelope<DuelWinResult>>('/v1/student/duel/win', {
    opponent_id: opponentId ?? null,
  })
  if (data.code !== 0) {
    throw new Error(data.message || '对战胜局记录失败')
  }
  return data.data
}

export interface OnlineClassmateItem {
  id: number
  username: string | null
  real_name: string | null
  avatar_url?: string | null
  last_seen_at?: string | null
}

export interface OnlineClassmatesResult {
  class_id: number | null
  online_count: number
  ttl_seconds: number
  updated_at: string
  students: OnlineClassmateItem[]
}

export async function fetchOnlineClassmates() {
  const { data } = await http.get<ApiEnvelope<OnlineClassmatesResult>>('/v1/student/online-classmates')
  if (data.code !== 0) throw new Error(data.message || '在线同学加载失败')
  return data.data
}

export type DuelMatchDifficulty = 'entry' | 'advanced'

export interface DuelMatchResult {
  status: 'idle' | 'waiting' | 'matched'
  match_id?: string
  difficulty?: DuelMatchDifficulty
  difficulty_label?: string
  time_sec?: number
  question_ids?: string[]
  opponent?: {
    user_id: number
    display_name: string
    username?: string | null
    real_name?: string | null
  }
  online_rivals?: number
  message?: string
  created_at?: string
}

export async function joinDuelMatch(options?: {
  difficulty?: DuelMatchDifficulty
  opponentId?: number | null
}) {
  const { data } = await http.post<ApiEnvelope<DuelMatchResult>>('/v1/student/duel/match', {
    difficulty: options?.difficulty ?? 'entry',
    opponent_id: options?.opponentId ?? null,
  })
  if (data.code !== 0) throw new Error(data.message || '匹配失败')
  return data.data
}

export async function fetchDuelMatchStatus() {
  const { data } = await http.get<ApiEnvelope<DuelMatchResult>>('/v1/student/duel/match')
  if (data.code !== 0) throw new Error(data.message || '匹配状态加载失败')
  return data.data
}

export async function cancelDuelMatch() {
  const { data } = await http.post<ApiEnvelope<DuelMatchResult>>('/v1/student/duel/match/cancel')
  if (data.code !== 0) throw new Error(data.message || '取消匹配失败')
  return data.data
}
