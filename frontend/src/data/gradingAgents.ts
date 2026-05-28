/** 教师端「学生做题检查」智能体目录 — 供智能体编排勾选与去重校验 */

export type GradingAgentCategory = 'correctness' | 'code' | 'logic' | 'feedback' | 'integrity'

export interface GradingAgentDefinition {
  id: string
  name: string
  nameEn: string
  description: string
  category: GradingAgentCategory
  /** 唯一检查维度，各智能体互不重叠 */
  checkType: string
  status: 'ready' | 'beta'
}

export const GRADING_AGENT_CATEGORY_LABELS: Record<GradingAgentCategory, string> = {
  correctness: '答案校验',
  code: '代码检查',
  logic: '逻辑分析',
  feedback: '反馈生成',
  integrity: '诚信检测',
}

/** 教师可用于学生做题检查的智能体预设（checkType 互不重叠） */
export const TEACHER_GRADING_AGENTS: GradingAgentDefinition[] = [
  {
    id: 'answer-correctness',
    name: '标准答案比对智能体',
    nameEn: 'Answer Correctness Agent',
    description: '对照参考答案与评分要点，判定客观题与填空题正误。',
    category: 'correctness',
    checkType: 'answer_match',
    status: 'ready',
  },
  {
    id: 'code-syntax',
    name: '代码语法审查智能体',
    nameEn: 'Code Syntax Agent',
    description: '静态分析 Python 代码语法、缩进与命名规范，标记可修复问题。',
    category: 'code',
    checkType: 'syntax_check',
    status: 'ready',
  },
  {
    id: 'sandbox-runtime',
    name: '沙箱运行验证智能体',
    nameEn: 'Sandbox Runtime Agent',
    description: '在隔离沙箱执行学生代码，比对输出与边界用例。',
    category: 'code',
    checkType: 'runtime_verify',
    status: 'ready',
  },
  {
    id: 'logic-step',
    name: '解题步骤逻辑智能体',
    nameEn: 'Logic Step Agent',
    description: '逐步审查推导链是否完整，识别跳步与逻辑漏洞。',
    category: 'logic',
    checkType: 'logic_chain',
    status: 'ready',
  },
  {
    id: 'knowledge-coverage',
    name: '知识点覆盖检查智能体',
    nameEn: 'Knowledge Coverage Agent',
    description: '核对作答是否覆盖试炼关联知识点与能力项。',
    category: 'logic',
    checkType: 'knowledge_coverage',
    status: 'ready',
  },
  {
    id: 'rubric-alignment',
    name: '评分细则对齐智能体',
    nameEn: 'Rubric Alignment Agent',
    description: '按教师配置的评分量表逐项打分并给出扣分依据。',
    category: 'feedback',
    checkType: 'rubric_scoring',
    status: 'ready',
  },
  {
    id: 'feedback-coach',
    name: '个性化反馈教练智能体',
    nameEn: 'Feedback Coach Agent',
    description: '基于错因生成可操作建议与下一道巩固题推荐。',
    category: 'feedback',
    checkType: 'student_feedback',
    status: 'ready',
  },
  {
    id: 'plagiarism-guard',
    name: '抄袭相似度检测智能体',
    nameEn: 'Plagiarism Guard Agent',
    description: '比对同班历史提交与公开题解，标记异常相似片段。',
    category: 'integrity',
    checkType: 'plagiarism_scan',
    status: 'beta',
  },
]

export const GRADING_AGENT_MAP = new Map(TEACHER_GRADING_AGENTS.map((agent) => [agent.id, agent]))
