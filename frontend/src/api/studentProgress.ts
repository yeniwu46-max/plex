import { http, type ApiEnvelope } from './http'

export interface LearningDomain {
  key: string
  title: string
  progress: number
  state: string
  locked?: boolean
  active?: boolean
}

export interface LearningPathResult {
  domains: LearningDomain[]
  active_domain_key: string
}

export interface ArchiveSkill {
  key: string
  label: string
  percent: number
}

export type { EmergencyMissionArchiveRecord } from './emergencyMission'
import type { EmergencyMissionArchiveRecord } from './emergencyMission'

export interface ArchiveInsightsResult {
  tendency: { label: string; description: string }
  skills: ArchiveSkill[]
  stats: {
    completed_trials: number
    completed_daily_quests: number
    total_points: number
  }
  emergency_missions?: EmergencyMissionArchiveRecord[]
}

export interface DashboardExtras {
  running_trials: number
}

export async function fetchLearningPath() {
  const { data } = await http.get<ApiEnvelope<LearningPathResult>>('/v1/student/learning-path')
  if (data.code !== 0) throw new Error(data.message || '加载星轨失败')
  return data.data
}

export async function fetchArchiveInsights() {
  const { data } = await http.get<ApiEnvelope<ArchiveInsightsResult>>('/v1/student/archive-insights')
  if (data.code !== 0) throw new Error(data.message || '加载档案洞察失败')
  return data.data
}

export async function fetchDashboardExtras() {
  const { data } = await http.get<ApiEnvelope<DashboardExtras>>('/v1/student/dashboard-extras')
  if (data.code !== 0) throw new Error(data.message || '加载概览扩展失败')
  return data.data
}

export interface AbilityStatsResult {
  radar: { dimensions: string[]; values: number[] }
  trend: { x_data: string[]; correct_rate: number[]; practice_count: number[] }
}

export async function fetchAbilityStats() {
  const { data } = await http.get<ApiEnvelope<AbilityStatsResult>>('/v1/student/ability-stats')
  if (data.code !== 0) throw new Error(data.message || '能力统计加载失败')
  return data.data
}
