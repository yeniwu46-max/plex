import { http, type ApiEnvelope, formatHttpError } from './http'
import type {
  LearningPathPlanResult,
  PlanLearningPathPayload,
  StudentDiagnoseResult,
  TeacherSuggestionResult,
} from './agentService'

const AGENT_TIMEOUT_MS = 20_000

async function postAgent<T>(path: string, body: Record<string, unknown> = {}) {
  try {
    const { data } = await http.post<ApiEnvelope<T>>(path, body, { timeout: AGENT_TIMEOUT_MS })
    if (data.code !== 0) throw new Error(data.message || '智能体调用失败')
    return data.data
  } catch (error) {
    throw new Error(formatHttpError(error, '智能体调用失败'))
  }
}

async function getAgent<T>(path: string) {
  try {
    const { data } = await http.get<ApiEnvelope<T>>(path, { timeout: AGENT_TIMEOUT_MS })
    if (data.code !== 0) throw new Error(data.message || '智能体调用失败')
    return data.data
  } catch (error) {
    throw new Error(formatHttpError(error, '智能体调用失败'))
  }
}

export interface ClassDiagnosisAttentionStudent {
  id: number
  name: string
  weakPoints: string[]
  activeCount: number
}

export interface ClassDiagnosisWeakNode {
  id: string
  label: string
  weakCount: number
  studentCount: number
}

export interface ClassDiagnosisResult {
  classId: number
  className: string | null
  studentCount: number
  weakPointStats: Array<{ knowledgePoint: string; count: number }>
  commonErrorTypes: string[]
  attentionStudents: ClassDiagnosisAttentionStudent[]
  weakNodes: ClassDiagnosisWeakNode[]
  suggestion: TeacherSuggestionResult & {
    interventionGroups: Array<{
      groupName: string
      students: string[]
      studentCount?: number
      focus: string
    }>
  }
  backend?: string
  generatedAt?: string
}

/** 教师端 · 班级一键学情诊断 */
export function fetchClassDiagnosis(classId: number) {
  return getAgent<ClassDiagnosisResult>(`/v1/teacher/class-diagnosis?class_id=${classId}`)
}

/** 教师端 · 为单个 Explorer 运行学情诊断（基于其留存错题证据） */
export function diagnoseStudent(studentId: number) {
  return postAgent<StudentDiagnoseResult>(`/v1/teacher/students/${studentId}/diagnose`)
}

/** 教师端 · 为单个 Explorer 规划学习路径 */
export function planStudentPath(studentId: number, payload: PlanLearningPathPayload = {}) {
  return postAgent<LearningPathPlanResult>(
    `/v1/teacher/students/${studentId}/plan-path`,
    payload as Record<string, unknown>,
  )
}

export interface TeacherStudentMistakeItem {
  id: number
  source: string
  knowledge_key: string
  knowledge_label?: string
  question_ref: string
  question_title?: string
  error_type?: string
  fail_count: number
  last_failed_at?: string
  last_passed_at?: string
  meta?: Record<string, unknown>
}

export interface TeacherStudentMistakesResult {
  student_id: number
  username: string
  real_name: string
  items: TeacherStudentMistakeItem[]
  weak_knowledge: Array<{
    knowledge_key: string
    knowledge_label: string
    fail_count: number
    weight: number
  }>
  active_count: number
}

/** 教师端 · 查看某 Explorer 的错题透视 */
export function fetchTeacherStudentMistakes(studentId: number) {
  return getAgent<TeacherStudentMistakesResult>(`/v1/teacher/students/${studentId}/mistakes`)
}

export interface TeacherStudentAdaptation {
  id?: number
  knowledge_key?: string
  knowledge_label?: string
  trigger_node?: string
  status?: string
  steps?: string[]
  created_at?: string
  [key: string]: unknown
}

/** 教师端 · 查看某 Explorer 的补救建议 */
export function fetchTeacherStudentAdaptations(studentId: number) {
  return getAgent<TeacherStudentAdaptation[] | { items?: TeacherStudentAdaptation[] }>(
    `/v1/teacher/students/${studentId}/learning-adaptations`,
  )
}
