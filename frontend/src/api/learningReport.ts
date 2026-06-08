import { http, type ApiEnvelope } from './http'
import type { AbilityStatsResult } from './studentProgress'
import type { StudentMistakeItem, WeakKnowledgeItem } from './studentMistakes'

export interface LearningReportSummary {
  index: number
  level_label: string
  correct_rate: number
  quest_completion_rate: number
  completed_trials: number
}

export interface DomainMasteryItem {
  key: string
  label: string
  mastery_rate: number
  answered: number
  delta?: number
}

export interface LearningRecommendation {
  action: string
  title: string
  detail: string
  knowledge_key: string | null
}

export interface LearningReportResult {
  period: string
  summary: LearningReportSummary
  domain_mastery: DomainMasteryItem[]
  mistake_highlights: StudentMistakeItem[]
  weak_knowledge: WeakKnowledgeItem[]
  trend: AbilityStatsResult['trend']
  radar: AbilityStatsResult['radar']
  risk_tags: string[]
  recommendations: LearningRecommendation[]
  student?: { id: number; username: string; real_name: string }
}

export interface ClassEvaluationStudent {
  student_id: number
  username: string
  real_name: string
  learning_index: number
  level_label: string
  risk_tags: string[]
  weak_knowledge: WeakKnowledgeItem[]
}

export interface ClassEvaluationResult {
  class_id: number | null
  class_name?: string
  period: string
  domain_mastery: Array<{ label: string; mastery_rate: number }>
  mistake_types: Array<{ name: string; value: number; color?: string }>
  students: ClassEvaluationStudent[]
  attention_students: ClassEvaluationStudent[]
  avg_learning_index: number
}

export async function fetchStudentLearningReport(period: '7d' | '30d' = '7d') {
  const { data } = await http.get<ApiEnvelope<LearningReportResult>>('/v1/student/learning-report', {
    params: { period },
  })
  if (data.code !== 0) throw new Error(data.message || '学习报告加载失败')
  return data.data
}

export async function fetchTeacherStudentLearningReport(studentId: number, period: '7d' | '30d' = '7d') {
  const { data } = await http.get<ApiEnvelope<LearningReportResult>>(
    `/v1/teacher/students/${studentId}/learning-report`,
    { params: { period } },
  )
  if (data.code !== 0) throw new Error(data.message || '学情报告加载失败')
  return data.data
}

export async function fetchClassEvaluation(classId: number, period: '7d' | '30d' = '7d') {
  const { data } = await http.get<ApiEnvelope<ClassEvaluationResult>>('/v1/teacher/class-evaluation', {
    params: { class_id: classId, period },
  })
  if (data.code !== 0) throw new Error(data.message || '班级学情加载失败')
  return data.data
}

export async function downloadClassEvaluationExport(classId: number) {
  const response = await http.get('/v1/teacher/class-export', {
    params: { class_id: classId },
    responseType: 'blob',
  })
  const blob = response.data instanceof Blob ? response.data : new Blob([response.data])
  const disposition = String(response.headers['content-disposition'] ?? '')
  const match = disposition.match(/filename="?([^";]+)"?/)
  const filename = match?.[1] ?? `class-${classId}-evaluation.csv`
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}
