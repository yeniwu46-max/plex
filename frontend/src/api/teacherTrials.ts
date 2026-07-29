import { formatHttpError, http, type ApiEnvelope } from './http'

export interface TeacherTrial {
  id: number
  class_id: number
  teacher_id: number
  title: string
  trial_type: string
  knowledge_key: string | null
  knowledge_keys?: string[]
  difficulty: number
  notify_students?: boolean
  student_count?: number
  duration_minutes: number
  status: 'draft' | 'scheduled' | 'running' | 'ended'
  effective_status?: 'draft' | 'scheduled' | 'running' | 'ended'
  reward_points: number
  starts_at: string | null
  ends_at: string | null
  participant_count?: number
  completed_count?: number
  completion_rate?: number
  progress?: number
}

export interface TeacherTrialSummary {
  running_count: number
  scheduled_count?: number
  draft_count?: number
  participant_count: number
  class_student_count: number
  avg_completion_rate: number
  template_count: number
}

export interface TeacherTrialsResult {
  trials: TeacherTrial[]
  summary: TeacherTrialSummary
}

export type TrialQuestionKind =
  | 'mcq'
  | 'multiple'
  | 'true_false'
  | 'fill_blank'
  | 'short_answer'
  | 'coding'

export interface CustomTrialQuestion {
  question_type?: TrialQuestionKind
  stem: string
  options?: string[]
  correct_index?: number
  /** 多选题正确项索引集合（后端按单选 MCQ 兼容存储，完整数据保留在草稿 JSON） */
  correct_indexes?: number[]
  /** 填空题答案（按空位顺序） */
  blanks?: string[]
  /** 简答题参考答案 */
  reference_answer?: string
  /** 题目解析 */
  analysis?: string
  /** 题目分值 */
  score?: number
  /** 题目难度 0-100 */
  difficulty?: number
  knowledge_key?: string
  starter_code?: string
  run_mode?: 'stdout' | 'expression'
  hint?: string
  test_cases?: Array<{
    id: string
    label: string
    setup?: string
    invoke?: string
    expected: string
  }>
}

export type TrialPaperQuestion =
  | {
      question_type: 'mcq'
      stem: string
      options: string[]
      correct_index: number
      knowledge_key?: string
    }
  | {
      question_type: 'coding'
      stem: string
      starter_code: string
      run_mode: 'stdout' | 'expression'
      hint?: string
      test_cases: Array<{
        id: string
        label: string
        setup?: string
        invoke?: string
        expected: string
      }>
      knowledge_key?: string
    }

export interface CodingBankItem {
  id: string
  stem: string
  knowledge_key?: string
  starter_code: string
  run_mode: string
  hint?: string
  test_cases: CustomTrialQuestion['test_cases']
}

export interface CreateTrialPayload {
  class_id: number
  title?: string
  trial_type?: string
  knowledge_key?: string | null
  knowledge_keys?: string[]
  difficulty?: number
  duration_minutes?: number
  reward_points?: number
  status?: string
  publish_mode?: 'draft' | 'now' | 'scheduled'
  starts_at?: string
  start_delay_minutes?: number
  notify_students?: boolean
  custom_questions?: CustomTrialQuestion[]
  draft_questions?: CustomTrialQuestion[]
}

export interface AiGenerateOptions {
  /** 期望题型：mcq 单选 / multiple 多选 / coding 编程 */
  question_types?: Array<'mcq' | 'multiple' | 'coding'>
  /** @deprecated 单题型兼容字段 */
  question_type?: TrialQuestionKind
  /** 难度 0-100 */
  difficulty?: number
}

export async function aiGenerateTrialQuestions(
  knowledgeKeys: string[],
  count = 3,
  options: AiGenerateOptions = {},
) {
  const { data } = await http.post<ApiEnvelope<{ questions: CustomTrialQuestion[] }>>(
    '/v1/teacher/trials/ai-generate-questions',
    { knowledge_keys: knowledgeKeys, count, ...options },
  )
  if (data.code !== 0) throw new Error(data.message || 'AI 出题失败')
  return data.data.questions
}

export interface PublishTrialResult {
  trial: TeacherTrial
  notify_students: boolean
  student_count: number
}

export async function fetchTeacherTrials(classId: number) {
  const { data } = await http.get<ApiEnvelope<TeacherTrialsResult>>('/v1/teacher/trials', {
    params: { class_id: classId },
  })
  if (data.code !== 0) throw new Error(data.message || '试炼列表加载失败')
  return data.data
}

export async function createTeacherTrial(payload: CreateTrialPayload) {
  const { data } = await http.post<ApiEnvelope<TeacherTrial>>('/v1/teacher/trials', payload)
  if (data.code !== 0) throw new Error(data.message || '创建试炼失败')
  return data.data
}

export async function publishTeacherTrial(trialId: number, notifyStudents = true) {
  const { data } = await http.post<ApiEnvelope<PublishTrialResult>>(
    `/v1/teacher/trials/${trialId}/publish`,
    { notify_students: notifyStudents },
  )
  if (data.code !== 0) throw new Error(data.message || '发布试炼失败')
  return data.data
}

export async function updateTeacherTrial(
  trialId: number,
  payload: {
    status?: string
    title?: string
    draft_questions?: CustomTrialQuestion[]
    custom_questions?: CustomTrialQuestion[]
  },
) {
  const { data } = await http.patch<ApiEnvelope<TeacherTrial>>(`/v1/teacher/trials/${trialId}`, payload)
  if (data.code !== 0) throw new Error(data.message || '更新试炼失败')
  return data.data
}

export async function deleteTeacherTrial(trialId: number) {
  const { data } = await http.delete<ApiEnvelope<{ deleted: boolean; trial_id: number }>>(
    `/v1/teacher/trials/${trialId}`,
  )
  if (data.code !== 0) throw new Error(data.message || '删除试炼失败')
  return data.data
}

export async function fetchCodingQuestionBank() {
  const { data } = await http.get<ApiEnvelope<{ items: CodingBankItem[] }>>('/v1/teacher/coding-question-bank')
  if (data.code !== 0) throw new Error(data.message || '编程题库加载失败')
  return data.data.items
}

export interface StudentTrialParticipation {
  id: number
  trial_id: number
  user_id: number
  status: string
  score: number
  joined_at: string | null
  completed_at: string | null
  trial: TeacherTrial
}

export interface StudentTrialHistoryResult {
  student_id: number
  participations: StudentTrialParticipation[]
  summary: {
    total: number
    completed: number
    joined: number
    avg_score: number
  }
}

export async function fetchStudentTrialHistory(studentId: number) {
  const { data } = await http.get<ApiEnvelope<StudentTrialHistoryResult>>(
    `/v1/teacher/students/${studentId}/trials`,
  )
  if (data.code !== 0) throw new Error(data.message || '试炼记录加载失败')
  return data.data
}

export interface TrialQuestionStat {
  question_id: number
  sort_order: number
  stem: string
  knowledge_key: string | null
  knowledge_label: string
  answered_count: number
  correct_count: number
  correct_rate: number
  avg_time_spent_sec?: number
}

export interface TrialStudentAnswerRecord {
  question_id: number
  sort_order: number
  stem: string
  knowledge_key: string | null
  knowledge_label: string
  status: string
  selected_index: number | null
  selected_label: string | null
  selected_text: string | null
  correct_index: number
  correct_label: string | null
  is_correct: boolean | null
  started_at: string | null
  answered_at: string | null
  time_spent_sec: number | null
  agent_trace?: AgentTraceRecord[]
}

export interface AgentTraceRecord {
  agentId: string
  name?: string
  status?: string
  summary?: string
  latencyMs?: number
  backend?: string
}

export interface TrialStudentProgressRow {
  user_id: number
  username: string
  real_name: string
  participation_status: string | null
  score: number
  answered_count: number
  correct_count: number
  question_total: number
  total_time_spent_sec: number
  joined_at: string | null
  completed_at: string | null
  answers: TrialStudentAnswerRecord[]
}

export interface TeacherTrialDetailResult {
  trial: TeacherTrial
  class_name: string
  teacher_name: string
  draft_questions?: CustomTrialQuestion[]
  questions: Array<{
    id: number
    trial_id: number
    sort_order: number
    question_type?: string
    stem: string
    options: string[]
    knowledge_key: string | null
    correct_index: number
    coding_meta?: Record<string, unknown>
  }>
  students: TrialStudentProgressRow[]
  summary: {
    question_count: number
    avg_score: number
    completion_rate: number
    question_stats: TrialQuestionStat[]
  }
}

export async function fetchTeacherTrialDetail(trialId: number) {
  const { data } = await http.get<ApiEnvelope<TeacherTrialDetailResult>>(`/v1/teacher/trials/${trialId}`)
  if (data.code !== 0) throw new Error(data.message || '试炼详情加载失败')
  return data.data
}

export interface TrialAiAnalyzeResult {
  trial_id: number
  backend: string
  overview: string
  weak_points: string[]
  strong_points: string[]
  suggestions: string[]
  question_notes: Array<{ sort_order?: number; note?: string }>
  stats_snapshot?: Record<string, unknown>
}

export async function analyzeTeacherTrial(trialId: number) {
  try {
    const { data } = await http.post<ApiEnvelope<TrialAiAnalyzeResult>>(
      `/v1/teacher/trials/${trialId}/ai-analyze`,
      {},
      { timeout: 45000 },
    )
    if (data.code !== 0) throw new Error(data.message || '小E 分析失败')
    return data.data
  } catch (error) {
    throw new Error(formatHttpError(error, '小E 分析失败，请稍后重试'))
  }
}

export interface ClassTrialAnswerBoardTrial {
  trial: TeacherTrial
  summary: TeacherTrialDetailResult['summary']
  students: TrialStudentProgressRow[]
  has_activity: boolean
}

export interface ClassTrialAnswerBoardResult {
  class_id: number
  class_name: string
  student_count: number
  trial_count: number
  active_trial_count: number
  submitted_total: number
  sync_note: string
  trials: ClassTrialAnswerBoardTrial[]
}

export interface StudentTrialAnswerBoardItem {
  trial: TeacherTrial
  participation_status: string | null
  score: number
  answered_count: number
  correct_count: number
  question_total: number
  total_time_spent_sec: number
  joined_at: string | null
  completed_at: string | null
  answers: TrialStudentAnswerRecord[]
}

export interface StudentTrialAnswerBoardResult {
  student_id: number
  username: string
  real_name: string
  class_id: number
  trials: StudentTrialAnswerBoardItem[]
}

export async function fetchClassTrialAnswerBoard(classId: number) {
  const { data } = await http.get<ApiEnvelope<ClassTrialAnswerBoardResult>>(
    `/v1/teacher/classes/${classId}/trial-answers`,
  )
  if (data.code !== 0) throw new Error(data.message || '班级作答数据加载失败')
  return data.data
}

export async function fetchStudentTrialAnswerBoard(studentId: number) {
  const { data } = await http.get<ApiEnvelope<StudentTrialAnswerBoardResult>>(
    `/v1/teacher/students/${studentId}/trial-answers`,
  )
  if (data.code !== 0) throw new Error(data.message || '学生作答数据加载失败')
  return data.data
}
