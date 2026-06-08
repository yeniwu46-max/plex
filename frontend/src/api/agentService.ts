import { http, type ApiEnvelope } from './http'

/** 学生端 · 单题诊断完整结果 */
export interface StudentDiagnoseResult {
  diagnosis: {
    weakPoints: string[]
    errorType: string
    diagnosis: string
    confidence: number
  }
  codeAnalysis: {
    codeIssueSummary: string
    possibleCause: string
    fixDirection: string
    relatedConcepts: string[]
  }
  graphInsight: {
    relatedNodes: string[]
    prerequisiteNodes: string[]
    recommendedReviewNodes: string[]
    graphReason: string
  }
  recommendation: {
    nextKnowledgePoint: string
    recommendedExercises: string[]
    reviewPlan: string[]
    estimatedDifficulty: string
  }
  feedback: {
    shortFeedback: string
    stepHints: string[]
    encouragement: string
    nextAction: string
  }
  backend?: string
  completedAt?: string
}

export interface TeacherSuggestionResult {
  classSummary: string
  teachingSuggestions: string[]
  interventionGroups: Array<{
    groupName: string
    students: string[]
    focus: string
  }>
  backend?: string
  generatedAt?: string
}

export interface AgentStatusItem {
  id: string
  name: string
  role: string
  status: 'idle' | 'running' | 'success' | 'error'
  lastRunAt?: string
  avgLatency?: number
}

export interface AgentsStatusResult {
  agents: AgentStatusItem[]
  backend: string
  service?: string
  version?: string
  checked_at?: string
}

export interface StudentDiagnosePayload {
  studentId?: string
  exerciseId: string
  code: string
  stdin?: string
  stdout?: string
  stderr?: string
  expectedOutput?: string
  knowledgePoints: string[]
  attemptCount: number
  answerStatus?: 'correct' | 'wrong' | 'partial'
}

export interface TeacherSuggestionPayload {
  classId: string
  weakPointStats?: Array<{ knowledgePoint: string; count: number }>
  commonErrorTypes?: string[]
  recentExercises?: string[]
}

const AGENT_TIMEOUT_MS = 15_000

async function postAgent<T>(path: string, body: Record<string, unknown> = {}) {
  const { data } = await http.post<ApiEnvelope<T>>(path, body, { timeout: AGENT_TIMEOUT_MS })
  if (data.code !== 0) throw new Error(data.message || '智能体调用失败')
  return data.data
}

async function getAgent<T>(path: string) {
  const { data } = await http.get<ApiEnvelope<T>>(path, { timeout: AGENT_TIMEOUT_MS })
  if (data.code !== 0) throw new Error(data.message || '智能体状态获取失败')
  return data.data
}

/** 学生端 · 多智能体单题诊断（诊断→分析→图谱→路径→反馈） */
export function studentDiagnose(payload: StudentDiagnosePayload) {
  return postAgent<StudentDiagnoseResult>('/v1/agents/student-diagnose', payload as unknown as Record<string, unknown>)
}

/** 教师端 · 班级教学建议 */
export function teacherAgentSuggestion(payload: TeacherSuggestionPayload) {
  return postAgent<TeacherSuggestionResult>('/v1/agents/teacher-suggestion', payload as unknown as Record<string, unknown>)
}

/** 管理员端 · 智能体运行状态 */
export function fetchAgentsStatus() {
  return getAgent<AgentsStatusResult>('/v1/agents/status')
}

// ---- 兼容旧版分散接口（管理员 Flow 演示等） ----

export interface AgentDiagnoseResult {
  agent: string
  status: string
  weak_points: string[]
  error_types: Array<{ type: string; explanation: string }>
  overall_assessment: string
  diagnosed_at: string
}

export function diagnoseAgent(payload: { code_errors?: string[]; mistake_count?: number } = {}) {
  return postAgent<AgentDiagnoseResult>('/v1/agent/diagnose', payload)
}

export function recommendPathAgent(payload: { weak_points?: string[] } = {}) {
  return postAgent<Record<string, unknown>>('/v1/agent/recommend-path', payload)
}

export function analyzeCodeAgent(payload: { code?: string; error_message?: string }) {
  return postAgent<Record<string, unknown>>('/v1/agent/analyze-code', payload)
}

export function generateFeedbackAgent(payload: { diagnosis?: Record<string, unknown> } = {}) {
  return postAgent<Record<string, unknown>>('/v1/agent/generate-feedback', payload)
}

export function teacherSuggestionAgent() {
  return postAgent<Record<string, unknown>>('/v1/agent/teacher-suggestion')
}

export async function runAgentPipeline(sampleCode = 'for i in range(len(items)):\n    print(items[i])') {
  const diagnosis = await diagnoseAgent({ code_errors: ['IndexError'] })
  const [path, codeAnalysis] = await Promise.all([
    recommendPathAgent({ weak_points: diagnosis.weak_points }),
    analyzeCodeAgent({ code: sampleCode, error_message: 'IndexError: list index out of range' }),
  ])
  const feedbackResult = await generateFeedbackAgent({ diagnosis: diagnosis as unknown as Record<string, unknown> })
  const teacherResult = await teacherSuggestionAgent()
  return { diagnosis, path, codeAnalysis, feedback: feedbackResult, teacher: teacherResult }
}
