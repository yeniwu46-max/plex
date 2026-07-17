import { http, type ApiEnvelope } from './http'

export interface AgentRegistryItem {
  id: string
  name: string
  nameEn: string
  description: string
  role: string
  category?: string
  checkType?: string
  status?: string
  flowNodeId?: string
}

export interface AgentOrchestrationConfig {
  enabled: boolean
  grading_agents: string[]
  learning_pipeline: string[]
}

export interface AgentRuntimeStatus {
  id: string
  name: string
  role: string
  status: string
  lastRunAt: string | null
  avgLatency: number | null
}

export interface AgentRuntimeInfo {
  crewai_venv: boolean
  api_key_configured: boolean
  llm_available: boolean
  enabled_grading_count: number
  enabled_learning_count: number
  avg_latency_ms: number | null
  success_rate: number
  registered_agent_count: number
  ready_for_llm: boolean
  degraded_reason: 'missing_crewai_venv' | 'missing_api_key' | null
}

export interface AgentOrchestrationResult {
  grading_agents: AgentRegistryItem[]
  learning_pipeline_agents: AgentRegistryItem[]
  defaults: AgentOrchestrationConfig
  config: AgentOrchestrationConfig
  agent_backend: string
  runtime_status: AgentRuntimeStatus[]
  runtime: AgentRuntimeInfo
}

export interface AgentTraceSummaryItem {
  agentId: string
  name?: string
  status: string
  summary: string
  backend?: string
}

export interface AgentTraceSummary {
  count: number
  items: AgentTraceSummaryItem[]
  has_error: boolean
}

export async function fetchAgentOrchestration() {
  const { data } = await http.get<ApiEnvelope<AgentOrchestrationResult>>('/v1/admin/agent-orchestration')
  if (data.code !== 0) throw new Error(data.message || '加载智能体编排失败')
  return data.data
}

export async function saveAgentOrchestration(config: AgentOrchestrationConfig) {
  const { data } = await http.put<ApiEnvelope<AgentOrchestrationResult>>('/v1/admin/agent-orchestration', config)
  if (data.code !== 0) throw new Error(data.message || '保存智能体编排失败')
  return data.data
}
