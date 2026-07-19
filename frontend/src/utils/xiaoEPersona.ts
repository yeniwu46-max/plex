/** 学生可见文案：将后端/流水线术语映射为小E 口吻，不暴露智能体架构。 */

export const XIAO_E_PERSONA_INTRO =
  '我是小E，你的 Python 学习搭档。我会根据你最近的练习和错题给建议，不用重复描述学习情况。'

/** 去除 AI 味标点与多余装饰符号 */
export function xiaoEStripDash(text: string): string {
  return text
    .replace(/[—–]{1,2}/g, '，')
    .replace(/▮+/g, '')
    .replace(/[·•]{2,}/g, '·')
    .trim()
}

export function xiaoENormalizeReply(text: string): string {
  return xiaoEStripDash(xiaoEStripAsterisks(text))
    .replace(/智能体/g, '小E')
    .replace(/Agent/gi, '小E')
}

/** @alias xiaoENormalizeReply */
export const xiaoECleanProse = xiaoENormalizeReply

const RESOURCE_STEP_LABELS: Record<string, string> = {
  profile_interpreter: '了解你的学习情况',
  knowledge_retrieval: '查找相关知识点',
  instructional_design: '设计讲解方式',
  resource_generation: '整理学习材料',
  quality_audit: '检查内容质量',
}

export function xiaoEResourceStepLabel(agentId: string, fallbackName?: string): string {
  return RESOURCE_STEP_LABELS[agentId] ?? fallbackName ?? '准备学习材料'
}

export function xiaoEResourceProgressHint(
  status: string,
  progress: number,
  currentAgent?: string | null,
): string {
  if (status === 'completed') return '学习资源包已经准备好啦，快去看看吧～'
  if (status === 'failed') return '这次准备过程遇到了一点问题，你可以稍后重试。'
  if (status === 'pending') return '小E 已收到你的请求，马上开始准备…'
  if (currentAgent) {
    return `小E 正在${xiaoEResourceStepLabel(currentAgent)}…（${Math.round(progress)}%）`
  }
  if (progress > 0) return `小E 正在为你定制学习资源…（${Math.round(progress)}%）`
  return '小E 正在为你准备个性化学习资源…'
}

export function xiaoEThinkingMessage(context: 'trial' | 'resource' | 'chat' | 'diagnosis' = 'trial'): string {
  const messages: Record<typeof context, string> = {
    trial: '小E 正在看你的代码，稍等一下…',
    resource: '小E 正在整理适合你的学习材料…',
    chat: '小E 正在思考怎么回答你…',
    diagnosis: '小E 正在分析你的学习情况…',
  }
  return messages[context]
}

export function xiaoETimeoutMessage(): string {
  return '小E 这次思考有点久，稍后再试一次吧～'
}

const BACKEND_LABELS: Record<string, string> = {
  local_rules: '快速准备',
  iflytek_spark: '云端讲解',
  deepseek: '智能讲解',
  llm: '智能讲解',
  spark: '智能讲解',
  rag: '知识库参考',
  rules: '学习建议',
}

export function xiaoEResourceBackendLabel(backend?: string | null): string {
  const key = (backend || '').trim().toLowerCase()
  if (!key) return '学习资源'
  return BACKEND_LABELS[key] || '学习资源'
}

export function xiaoEStripAsterisks(text: string): string {
  return xiaoEStripDash(
    text
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/\*([^*\n]+)\*/g, '$1'),
  )
}

export function xiaoESubmitCheckSummary(rawSummary: string): string {
  const trimmed = rawSummary.trim()
  if (!trimmed) return '小E 已收到你的提交，继续加油！'
  return trimmed.replace(/智能体/g, '小E').replace(/Agent/gi, '小E')
}
