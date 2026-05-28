import {
  GRADING_AGENT_MAP,
  type GradingAgentDefinition,
} from '../data/gradingAgents'

export interface GradingAgentDuplicateConflict {
  checkType: string
  agentIds: string[]
  agentNames: string[]
  message: string
}

export interface GradingAgentValidationResult {
  valid: boolean
  selectedCount: number
  duplicates: GradingAgentDuplicateConflict[]
  warnings: string[]
}

function resolveAgents(ids: string[]): GradingAgentDefinition[] {
  return ids
    .map((id) => GRADING_AGENT_MAP.get(id))
    .filter((agent): agent is GradingAgentDefinition => Boolean(agent))
}

/** 多智能体重复校验：同一 checkType 不可被多个已选智能体覆盖 */
export function validateGradingAgentSelection(selectedIds: string[]): GradingAgentValidationResult {
  const uniqueIds = [...new Set(selectedIds.filter(Boolean))]
  const agents = resolveAgents(uniqueIds)
  const warnings: string[] = []

  if (agents.length === 0) {
    return {
      valid: false,
      selectedCount: 0,
      duplicates: [],
      warnings: ['请至少勾选一个检查智能体'],
    }
  }

  if (agents.length !== uniqueIds.length) {
    warnings.push('存在无效的智能体 ID，已忽略')
  }

  const byCheckType = new Map<string, GradingAgentDefinition[]>()

  for (const agent of agents) {
    const bucket = byCheckType.get(agent.checkType) ?? []
    bucket.push(agent)
    byCheckType.set(agent.checkType, bucket)
  }

  const duplicates: GradingAgentDuplicateConflict[] = []

  for (const [checkType, bucket] of byCheckType.entries()) {
    if (bucket.length <= 1) continue
    duplicates.push({
      checkType,
      agentIds: bucket.map((agent) => agent.id),
      agentNames: bucket.map((agent) => agent.name),
      message: `检查维度「${checkType}」被 ${bucket.map((agent) => agent.name).join('、')} 重复覆盖`,
    })
  }

  return {
    valid: duplicates.length === 0,
    selectedCount: agents.length,
    duplicates,
    warnings,
  }
}

export function canSelectGradingAgent(
  selectedIds: string[],
  candidateId: string,
): { allowed: boolean; reason?: string } {
  if (selectedIds.includes(candidateId)) {
    return { allowed: true }
  }

  const candidate = GRADING_AGENT_MAP.get(candidateId)
  if (!candidate) {
    return { allowed: false, reason: '未知智能体' }
  }

  const alreadyUsed = selectedIds
    .map((id) => GRADING_AGENT_MAP.get(id))
    .find((agent) => agent?.checkType === candidate.checkType)

  if (alreadyUsed) {
    return {
      allowed: false,
      reason: `「${alreadyUsed.name}」已占用该检查维度，请勿重复勾选`,
    }
  }

  return { allowed: true }
}
