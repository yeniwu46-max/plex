import { http, type ApiEnvelope } from './http'

/** 错因层级（四层错因模型） */
export type ErrorLayer = 'syntax' | 'rule' | 'logic' | 'transfer' | 'none'

/** 掌握度判别 */
export type ProficiencyLevel = 'cannot' | 'can_but_wrong' | 'transfer_gap' | 'mastered'

/** 补救策略类型 */
export type StrategyType =
  | 'trace_variables'
  | 'micro_fix'
  | 'concept_explain'
  | 'pattern_compare'
  | 'syntax_checklist'
  | 'consolidate'

export interface DiagnosisKnowledgePoint {
  node: string
  mastery: string
  reason: string
}

export interface RemediationStrategy {
  type: StrategyType
  title: string
  detail: string
  steps: string[]
  microExercise: string
}

/** 单步智能体执行轨迹 */
export interface AgentTraceStep {
  agentId: string
  name: string
  role?: string
  status?: 'success' | 'error' | 'running'
  latencyMs: number
  summary: string
  source?: string
  backend?: string
}

export interface LearningPathPlanResult {
  ordered_nodes: Array<{
    id: string
    star_path_id?: string | null
    label: string
    order_index: number
    status: string
    mastery_score: number
    locked: boolean
    prerequisites_met: boolean
    difficulty?: string
    recommended_resources?: Array<{ id: number; title?: string; type?: string; difficulty?: string | number }>
    recommended_trials?: Array<{ question_id: string; title?: string; difficulty?: number }>
    remediation?: { trigger_node: string; steps: string[]; adaptation_id?: number; knowledge_key?: string } | null
  }>
  active_node_id?: string | null
  next_best_action?: { node_id: string | null; reason: string; action: string }
  remediation_paths?: Array<{ trigger_node: string; steps: string[]; adaptation_id?: number }>
  graph_backend?: string
  topology_source?: string
  rationale?: string
  agent_trace?: { backend: string; steps: AgentTraceStep[] }
  nextKnowledgePoint?: string
  reviewPlan?: string[]
  estimatedDifficulty?: string
}

export interface PlanLearningPathPayload {
  focus_node?: string
  focus_node_id?: string
  diagnosis?: Record<string, unknown>
}

/** 学生端 · 单题诊断完整结果 */
export interface StudentDiagnoseResult {
  diagnosis: {
    // 兼容旧字段
    weakPoints: string[]
    errorType: string
    diagnosis: string
    confidence: number
    // 四层错因模型新增字段
    errorLayer?: ErrorLayer
    errorLayerLabel?: string
    errorSubtype?: string
    proficiency?: ProficiencyLevel
    proficiencyLabel?: string
    proficiencyReason?: string
    relatedKnowledgePoints?: DiagnosisKnowledgePoint[]
    remediationStrategy?: RemediationStrategy
    evidence?: string[]
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
    masteryByNode?: Record<string, string>
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
    microExercise?: string
    strategyType?: StrategyType
  }
  pipelineTrace?: AgentTraceStep[]
  backend?: string
  completedAt?: string
}

/** 单次代码提交的完整协同闭环；沙箱结果是所有智能体决策的唯一证据源。 */
export interface LearningCycleResult extends StudentDiagnoseResult {
  execution: {
    all_passed: boolean
    passed_count: number
    total: number
    backend?: string
    results: Array<{
      case_id: string
      label: string
      passed: boolean
      expected: string
      actual: string
      status: { id: number; description: string }
      time?: string
      memory?: number
      error?: string | null
    }>
  }
  learningProfile: {
    explanationPreference: string
    visualPreferenceConfirmed: boolean
    interventionPresentation: string
    loopMastery: string
    loopMasteryScore?: number
    evidence: string[]
  }
  learningPath: StudentDiagnoseResult['recommendation'] & { reason: string }
  resources: {
    executionDiagram: { title: string; description: string; steps: Array<{ round: number; condition: string; i: number; action: string }> }
    microFix: { title: string; prompt: string; starterCode: string; expectedOutcome: string; answerPolicy: string }
    backend: string
  }
  tutor: { mode: 'socratic' | 'reflection'; question: string; nextAction: string }
  knowledgeGraphUpdate: { nodeId: string; nodeLabel: string; status: string; action: 'reinforce' | 'consolidated'; evidence: string }
  learningReport: { headline: string; outcome: 'passed' | 'needs_remediation'; diagnosis: string; nextActions: string[]; riskTags: string[] }
}

export interface LearningCyclePayload {
  language: 'python'
  code: string
  run_mode: 'stdout' | 'expression'
  test_cases: Array<{ id: string; label: string; input?: string; expected?: string; setup?: string; invoke?: string }>
  exerciseId: string
  questionTitle?: string
  questionPrompt?: string
  topic?: string
  knowledgePoints: string[]
  attemptCount: number
}

export interface TeacherSuggestionResult {
  classSummary: string
  teachingSuggestions: string[]
  interventionGroups: Array<{
    groupName: string
    students: string[]
    studentCount?: number
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
  questionTitle?: string
  questionPrompt?: string
  conversationHistory?: Array<{ role: string; content: string }>
}

export interface TeacherSuggestionPayload {
  classId: string
  weakPointStats?: Array<{ knowledgePoint: string; count: number }>
  commonErrorTypes?: string[]
  recentExercises?: string[]
}

export interface CodeHintPayload {
  exerciseId: string
  questionTitle?: string
  topic?: string
  code: string
  stdout?: string
  stderr?: string
  expectedOutput?: string
  failedCases?: Array<{
    label: string
    expected: string
    actual: string
    error?: string
  }>
}

export interface CodeHintResult {
  annotated_code: string
  comments: string[]
  policy: 'hint_only_no_direct_answer'
  backend?: string
}

export type TrialCoachIntent = 'error_diagnosis' | 'code_quality' | 'optimization' | 'custom'

export interface TrialCoachPayload {
  intent: TrialCoachIntent
  exerciseId: string
  questionTitle?: string
  questionPrompt?: string
  topic?: string
  constraints?: string[]
  code: string
  stderr?: string
  stdout?: string
  expectedOutput?: string
  failedCases?: Array<{ label: string; expected: string; actual: string; error?: string }>
  caseResults?: Array<{ passed: boolean }>
  allPassed?: boolean
  answerStatus?: 'correct' | 'wrong' | 'partial' | 'not_run'
  userQuestion?: string
  conversationHistory?: Array<{ role: 'user' | 'assistant'; content: string }>
}

export interface TrialCoachResult {
  agentId: string
  agentName: string
  intent: TrialCoachIntent
  contextSummary: string
  response: string
  guidingQuestions?: string[]
  strengths?: string[]
  improvements?: string[]
  policy: 'no_direct_answer'
  backend?: string
}

const AGENT_TIMEOUT_MS = 15_000
const MESSENGER_TIMEOUT_MS = 8_000
const TRIAL_COACH_TIMEOUT_MS = 45_000

async function postAgent<T>(path: string, body: Record<string, unknown> = {}, timeout = AGENT_TIMEOUT_MS) {
  const { data } = await http.post<ApiEnvelope<T>>(path, body, { timeout })
  if (data.code !== 0) throw new Error(data.message || '智能体调用失败')
  return data.data
}

async function getAgent<T>(path: string) {
  const { data } = await http.get<ApiEnvelope<T>>(path, { timeout: AGENT_TIMEOUT_MS })
  if (data.code !== 0) throw new Error(data.message || '智能体状态获取失败')
  return data.data
}

/** 学习路径智能体 · 主动规划（星轨页） */
export function planLearningPath(payload: PlanLearningPathPayload = {}) {
  return postAgent<LearningPathPlanResult>('/v1/agents/plan-learning-path', payload as Record<string, unknown>)
}

/** 学生端 · 多智能体单题诊断（诊断→分析→图谱→路径→反馈） */
export function studentDiagnose(payload: StudentDiagnosePayload) {
  return postAgent<StudentDiagnoseResult>('/v1/agents/student-diagnose', payload as unknown as Record<string, unknown>)
}

/** 根据服务端留存的错题与运行证据执行一次学习诊断，供小E快捷操作使用。 */
export function diagnoseLearning() {
  return postAgent<StudentDiagnoseResult>('/v1/agents/diagnose-learning')
}

export type MessengerQuickAction = 'weak_points' | 'next_trial' | 'repair_path' | 'recent_growth'

export interface MessengerQuickActionResult {
  action: MessengerQuickAction
  reply: string
  question_pick?: {
    code: string
    id: string
    title: string
    topic?: string
    knowledge_key?: string
    practice_path?: string
  } | null
}

/** 驿站快捷按钮 · 上下文化小E 回复（DeepSeek，8s 超时） */
export function messengerQuickAction(action: MessengerQuickAction) {
  return postAgent<MessengerQuickActionResult>('/v1/agents/messenger-quick-action', { action }, MESSENGER_TIMEOUT_MS)
}

/** 试炼页按需请求小E 反馈（不在运行测试时自动触发） */
export function requestTrialFeedback(payload: StudentDiagnosePayload) {
  return postAgent<StudentDiagnoseResult>('/v1/agents/trial-feedback', payload as unknown as Record<string, unknown>)
}

/** 学生端主闭环：提交代码后一次性获得沙箱、诊断、资源、辅导、图谱和报告。 */
export function runCodeLearningCycle(payload: LearningCyclePayload) {
  return postAgent<LearningCycleResult>('/v1/agents/code-learning-cycle', payload as unknown as Record<string, unknown>)
}

/** 教师端 · 班级教学建议 */
export function teacherAgentSuggestion(payload: TeacherSuggestionPayload) {
  return postAgent<TeacherSuggestionResult>('/v1/agents/teacher-suggestion', payload as unknown as Record<string, unknown>)
}

function isNotFound(error: unknown) {
  return (error as { response?: { status?: number } })?.response?.status === 404
}

function localCodeHint(payload: CodeHintPayload): CodeHintResult {
  const comments: string[] = []
  if (payload.stderr) {
    comments.push('先定位报错行附近的变量名、缩进、类型或函数调用是否正确。')
  } else if (payload.expectedOutput || payload.stdout) {
    comments.push('对比实际输出和预期输出，优先检查输出格式、循环范围和边界条件。')
  } else {
    comments.push('先把核心处理步骤写完整，再运行测试观察差异。')
  }
  const firstFailed = payload.failedCases?.[0]
  if (firstFailed) comments.push(`重点复查「${firstFailed.label}」这个未通过用例覆盖的输入场景。`)
  if (payload.topic) comments.push(`本题关联「${payload.topic}」，确认代码中有对应的处理逻辑。`)
  comments.push('不要写固定输出，要让代码能处理同类输入。')

  const lines = payload.code.replace(/\s+$/g, '').split('\n')
  const annotated: string[] = [
    '# AI 提示（不会直接给答案）',
    `# 题目：${payload.questionTitle || payload.exerciseId}`,
    ...comments.slice(0, 4).map((item) => `# - ${item}`),
    '',
  ]
  let inserted = false
  for (const line of lines.length ? lines : ['']) {
    const stripped = line.trim()
    if (!inserted && stripped && !stripped.startsWith('#')) {
      annotated.push('# TODO: 从这里开始检查变量、条件和输出是否符合题意')
      inserted = true
    }
    annotated.push(line)
  }
  if (!inserted) annotated.push('# TODO: 在这里补充解题逻辑，再运行测试观察差异')
  return {
    annotated_code: `${annotated.join('\n').trimEnd()}\n`,
    comments: comments.slice(0, 4),
    policy: 'hint_only_no_direct_answer',
    backend: 'local_rules',
  }
}

/** 试炼编程页 · 三类辅导智能体（报错/质量/优化），禁止直接给答案 */
export function trialCoach(payload: TrialCoachPayload) {
  return postAgent<TrialCoachResult>('/v1/agents/trial-coach', payload as unknown as Record<string, unknown>, TRIAL_COACH_TIMEOUT_MS)
}

/** 学生端 · 代码题提示，只返回注释式提示，不直接给答案 */
export async function codeHint(payload: CodeHintPayload) {
  try {
    return await postAgent<CodeHintResult>('/v1/agents/code-hint', payload as unknown as Record<string, unknown>)
  } catch (error) {
    if (isNotFound(error)) return localCodeHint(payload)
    throw error
  }
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
