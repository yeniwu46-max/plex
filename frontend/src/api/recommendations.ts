import { http, type ApiEnvelope } from './http'
import type { LearningRecommendation, LearningReportSummary } from './learningReport'
import type { StudentMistakeItem, WeakKnowledgeItem } from './studentMistakes'
import type { PersonalizedResource } from './personalizedResources'

export interface StudentRecommendationsResult {
  period: string
  summary?: LearningReportSummary
  weak_knowledge: WeakKnowledgeItem[]
  recommendations: LearningRecommendation[]
  mistake_highlights: StudentMistakeItem[]
  risk_tags: string[]
  personalized_resources: PersonalizedResource[]
  profile_version: number
  recommendation_context: {
    weak_knowledge: string[]
    preferred_resource_types: string[]
    daily_minutes?: string | null
  }
  profile_update_suggestion?: {
    dimension: string
    value: string
    source: string
    requires_confirmation: boolean
  } | null
}

export async function fetchStudentRecommendations(period: '7d' | '30d' = '7d') {
  const { data } = await http.get<ApiEnvelope<StudentRecommendationsResult>>('/v1/student/recommendations', {
    params: { period },
  })
  if (data.code !== 0) throw new Error(data.message || '推荐加载失败')
  return data.data
}
