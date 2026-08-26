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

export interface PhaseLearningReport {
  user_id: number
  period: string
  generated_at: string
  cooldown_hours: number
  headline: string
  summary: string[]
  focus_items: Array<{
    label: string
    reason: string
    knowledge_key: string | null
  }>
  recent_evidence: {
    practice_count: number
    active_days: number
    correct_rate: number
    mistake_count: number
    risk_tags: string[]
  }
  next_actions: string[]
}

export interface GeneratedPhaseReportResult {
  status: 'generated' | 'cooldown'
  report: PhaseLearningReport
  next_available_at: string
  remaining_seconds: number
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

export interface LearningEffectSnapshot {
  correct_rate: number
  answered_count: number
  correct_count: number
  mastery_rate: number
  mistake_count: number
  risk_tags: string[]
  evidence_ids: number[]
}

export interface LearningEffectResult {
  status: 'sufficient' | 'insufficient_evidence'
  minimum_samples_per_period: number
  task: {
    task_id: string
    knowledge_key: string
    profile_version: number
    resource_types: string[]
    backend: string
    intervention_at: string | null
  }
  before: LearningEffectSnapshot
  after: LearningEffectSnapshot
  delta: {
    correct_rate: number | null
    answered_count: number | null
    mastery_rate: number | null
    mistake_count: number | null
  }
  evidence_count: number
  student?: { id: number; username: string; real_name: string }
}

export async function fetchStudentLearningReport(period: '7d' | '30d' = '7d') {
  const { data } = await http.get<ApiEnvelope<LearningReportResult>>('/v1/student/learning-report', {
    params: { period },
  })
  if (data.code !== 0) throw new Error(data.message || '学习报告加载失败')
  return data.data
}

function isNotFound(error: unknown) {
  return (error as { response?: { status?: number } })?.response?.status === 404
}

function phaseReportStorageKey(period: '7d' | '30d') {
  return `plex:phase-report:${period}`
}

function buildLocalPhaseReport(report: LearningReportResult, period: '7d' | '30d'): PhaseLearningReport {
  const practiceCounts = report.trend?.practice_count ?? []
  const totalPractice = practiceCounts.reduce((sum, value) => sum + value, 0)
  const activeDays = practiceCounts.filter((value) => value > 0).length
  const weak = report.weak_knowledge.slice(0, 3)
  const weakestDomains = report.domain_mastery
    .filter((item) => item.answered > 0)
    .sort((a, b) => a.mastery_rate - b.mastery_rate)
    .slice(0, 3)
  return {
    user_id: report.student?.id ?? 0,
    period,
    generated_at: new Date().toISOString(),
    cooldown_hours: 12,
    headline: '阶段性薄弱点报告',
    summary: [
      `阶段指数 ${report.summary.index}，状态为「${report.summary.level_label}」。`,
      `近 ${period === '7d' ? 7 : 30} 天完成 ${totalPractice} 次练习，活跃 ${activeDays} 天。`,
      `最近正确率约 ${report.summary.correct_rate}%，累计完成试炼 ${report.summary.completed_trials} 个。`,
      weak.length
        ? `主要薄弱点集中在：${weak.map((item) => item.knowledge_label).join('、')}。`
        : '近期错题证据不足，建议先完成 2-3 道代码试炼以生成更准确诊断。',
    ],
    focus_items: [
      ...weak.map((item) => ({
        label: item.knowledge_label,
        reason: `累计失败 ${item.fail_count} 次，优先修复关联错题。`,
        knowledge_key: item.knowledge_key,
      })),
      ...weakestDomains.map((item) => ({
        label: item.label,
        reason: `本阶段答题 ${item.answered} 次，掌握率 ${item.mastery_rate}%。`,
        knowledge_key: item.key,
      })),
    ].slice(0, 3),
    recent_evidence: {
      practice_count: totalPractice,
      active_days: activeDays,
      correct_rate: report.summary.correct_rate,
      mistake_count: report.mistake_highlights.length,
      risk_tags: report.risk_tags,
    },
    next_actions: report.recommendations.slice(0, 3).map((item) => item.detail || item.title),
  }
}

async function generateLocalPhaseReport(period: '7d' | '30d'): Promise<GeneratedPhaseReportResult> {
  const key = phaseReportStorageKey(period)
  const cachedRaw = localStorage.getItem(key)
  const now = Date.now()
  if (cachedRaw) {
    try {
      const cached = JSON.parse(cachedRaw) as { generatedAt: number; report: PhaseLearningReport }
      const remaining = 12 * 60 * 60 * 1000 - (now - cached.generatedAt)
      if (remaining > 0) {
        return {
          status: 'cooldown',
          report: cached.report,
          next_available_at: new Date(cached.generatedAt + 12 * 60 * 60 * 1000).toISOString(),
          remaining_seconds: Math.ceil(remaining / 1000),
        }
      }
    } catch {
      localStorage.removeItem(key)
    }
  }
  const baseReport = await fetchStudentLearningReport(period)
  const report = buildLocalPhaseReport(baseReport, period)
  localStorage.setItem(key, JSON.stringify({ generatedAt: now, report }))
  return {
    status: 'generated',
    report,
    next_available_at: new Date(now + 12 * 60 * 60 * 1000).toISOString(),
    remaining_seconds: 12 * 60 * 60,
  }
}

export async function generateStudentPhaseReport(
  period: '7d' | '30d' = '7d',
  options?: { force?: boolean },
) {
  try {
    const { data } = await http.post<ApiEnvelope<GeneratedPhaseReportResult>>(
      '/v1/student/learning-report/generate',
      {
        period,
        force: Boolean(options?.force),
      },
    )
    if (data.code !== 0) throw new Error(data.message || '阶段报告生成失败')
    return data.data
  } catch (error) {
    if (isNotFound(error)) {
      if (options?.force) {
        localStorage.removeItem(phaseReportStorageKey(period))
      }
      return generateLocalPhaseReport(period)
    }
    throw error
  }
}

export async function fetchTeacherStudentLearningReport(studentId: number, period: '7d' | '30d' = '7d') {
  const { data } = await http.get<ApiEnvelope<LearningReportResult>>(
    `/v1/teacher/students/${studentId}/learning-report`,
    { params: { period } },
  )
  if (data.code !== 0) throw new Error(data.message || '学情报告加载失败')
  return data.data
}

export async function fetchStudentLearningEffect(taskId?: string) {
  const { data } = await http.get<ApiEnvelope<LearningEffectResult>>('/v1/student/learning-effect', {
    params: taskId ? { task_id: taskId } : undefined,
  })
  if (data.code !== 0) throw new Error(data.message || '学习效果证据加载失败')
  return data.data
}

export async function fetchTeacherStudentLearningEffect(studentId: number, taskId?: string) {
  const { data } = await http.get<ApiEnvelope<LearningEffectResult>>(
    `/v1/teacher/students/${studentId}/learning-effect`,
    { params: taskId ? { task_id: taskId } : undefined },
  )
  if (data.code !== 0) throw new Error(data.message || '学习效果证据加载失败')
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
