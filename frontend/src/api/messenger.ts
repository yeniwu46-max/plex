import { createRequestId } from '../utils/browserCrypto'
import { http, type ApiEnvelope } from './http'
import { postSseStream } from './sse'
import type { LearningRecommendation } from './learningReport'
import type { AgentTraceStep } from './agentService'
import type { MessengerKnowledge } from './rag'
import type { TutorResponse } from './tutoring'
import type { TutorContextRequest } from './tutorContext'

/** 驿站对话超时（LLM 生成通常 2–8 秒） */
const MESSENGER_CHAT_TIMEOUT_MS = 90_000
const MESSENGER_STREAM_TIMEOUT_MS = 90_000

export interface MessengerChatRequest extends TutorContextRequest {
  message: string
  request_id?: string
  session_id?: string
}
export interface MessengerChatResult {
  tutor?: TutorResponse
  question_pick?: TutorResponse['question_pick']
  reply: string
  source: string
  recommendations?: LearningRecommendation[]
  rag_used?: boolean
  rag_sources?: Array<{ doc_id: string; score: number; snippet?: string }>
  /** Graph-enhanced RAG 知识卡片（学生安全视图） */
  knowledge?: MessengerKnowledge | null
}

export interface MessengerChatHistoryItem {
  role: 'user' | 'assistant'
  content: string
}

export async function postMessengerChat(input: string | MessengerChatRequest, _history: MessengerChatHistoryItem[] = []) {
  const { data } = await http.post<ApiEnvelope<MessengerChatResult>>(
    '/v1/student/messenger/chat',
    typeof input === 'string' ? { message: input, request_id: createRequestId() } : { ...input },
    { timeout: MESSENGER_CHAT_TIMEOUT_MS },
  )
  if (data.code !== 0) throw new Error(data.message || '对话失败')
  return data.data
}

export interface MessengerStreamResult {
  tutor?: TutorResponse
  question_pick?: TutorResponse['question_pick']
  reply: string
  source: string
  recommendations?: LearningRecommendation[]
  rag_used?: boolean
  knowledge?: MessengerKnowledge | null
  illustration?: { url: string; caption?: string }
  thinking?: AgentTraceStep[]
  latency?: {
    context_ms: number | null
    first_token_ms: number | null
    generation_ms: number | null
    target_first_token_ms?: number
    degraded?: boolean
  }
}

export interface MessengerStreamHandlers {
  onDelta?: (text: string) => void
  onStage?: (stage: string, label: string) => void
  onDone?: (result: MessengerStreamResult) => void
  onIllustration?: (illustration: { url: string; caption?: string }) => void
  signal?: AbortSignal
}

function mapThinking(raw: unknown): AgentTraceStep[] | undefined {
  if (!Array.isArray(raw)) return undefined
  const steps: AgentTraceStep[] = []
  raw.forEach((item, index) => {
    if (!item || typeof item !== 'object') return
    const row = item as Record<string, unknown>
    const id = String(row.id ?? row.agentId ?? `step-${index}`)
    steps.push({
      agentId: id,
      name: String(row.label ?? row.name ?? id),
      status: 'success',
      latencyMs: Number(row.latencyMs ?? row.latency_ms ?? 0),
      summary: String(row.summary ?? ''),
    })
  })
  return steps.length ? steps : undefined
}

function mapKnowledge(raw: unknown): MessengerKnowledge | null {
  if (!raw || typeof raw !== 'object') return null
  const row = raw as Partial<MessengerKnowledge>
  if (typeof row.knowledge_grounded !== 'boolean') return null
  return row as MessengerKnowledge
}

/** SSE 流式驿站对话：收到 done 立即返回，图解可稍后到达。 */
export async function streamMessengerChat(
  input: string | MessengerChatRequest,
  _history: MessengerChatHistoryItem[] = [],
  onDeltaOrHandlers: ((text: string) => void) | MessengerStreamHandlers = {},
  signal?: AbortSignal,
): Promise<MessengerStreamResult> {
  const handlers: MessengerStreamHandlers =
    typeof onDeltaOrHandlers === 'function'
      ? { onDelta: onDeltaOrHandlers, signal }
      : { ...onDeltaOrHandlers, signal: onDeltaOrHandlers.signal ?? signal }

  const controller = new AbortController()
  const external = handlers.signal
  const onExternalAbort = () => controller.abort()
  if (external?.aborted) controller.abort()
  external?.addEventListener('abort', onExternalAbort)
  const timer = window.setTimeout(() => controller.abort(), MESSENGER_STREAM_TIMEOUT_MS)

  let illustration: { url: string; caption?: string } | undefined
  let thinking: AgentTraceStep[] | undefined
  const earlyHolder: { value: MessengerStreamResult | null } = { value: null }

  try {
    const doneEvent = await postSseStream(
      '/v1/student/messenger/chat/stream',
      typeof input === 'string' ? { message: input, request_id: createRequestId() } : { ...input },
      {
        settleOnDone: true,
        onDelta: handlers.onDelta,
        onStage: handlers.onStage,
        onIllustration: (payload) => {
          illustration = payload
          handlers.onIllustration?.(payload)
        },
        onDone: (event) => {
          thinking = mapThinking(event.thinking)
          if (event.illustration && typeof event.illustration === 'object') {
            illustration = event.illustration as { url: string; caption?: string }
          }
          earlyHolder.value = {
            tutor: event.tutor as TutorResponse | undefined,
            question_pick: event.question_pick as TutorResponse['question_pick'],
            reply: String(event.reply ?? ''),
            source: String(event.source ?? 'llm_stream'),
            recommendations: (event.recommendations as LearningRecommendation[] | undefined) ?? [],
            rag_used: Boolean(event.rag_used),
            knowledge: mapKnowledge(event.knowledge),
            illustration,
            thinking,
            latency: event.latency as MessengerStreamResult['latency'],
          }
          // 文字先落地，不等待后续 illustration 帧
          handlers.onDone?.(earlyHolder.value)
        },
        signal: controller.signal,
      },
    )
    const result = earlyHolder.value ?? (doneEvent
      ? {
          tutor: doneEvent.tutor as TutorResponse | undefined,
          question_pick: doneEvent.question_pick as TutorResponse['question_pick'],
          reply: String(doneEvent.reply ?? ''),
          source: String(doneEvent.source ?? 'llm_stream'),
          recommendations: (doneEvent.recommendations as LearningRecommendation[] | undefined) ?? [],
          rag_used: Boolean(doneEvent.rag_used),
          knowledge: mapKnowledge(doneEvent.knowledge),
          illustration:
            illustration
            ?? (doneEvent.illustration as { url: string; caption?: string } | undefined),
          thinking: thinking ?? mapThinking(doneEvent.thinking),
          latency: doneEvent.latency as MessengerStreamResult['latency'],
        }
      : null)
    if (!result) throw new Error('对话流意外结束，请重试')
    if (illustration) result.illustration = illustration
    return result
  } catch (error) {
    if (earlyHolder.value?.reply) return { ...earlyHolder.value, illustration }
    if (controller.signal.aborted && !external?.aborted) {
      throw new Error('对话超时，请重试')
    }
    throw error
  } finally {
    window.clearTimeout(timer)
    external?.removeEventListener('abort', onExternalAbort)
  }
}

export interface MessengerArtifactResult {
  artifact_id: string
  request_id: string
  session_id: string
  kind: 'document' | 'graph'
  status: 'ok' | 'safe_fallback' | 'needs_context'
  title: string
  topic: string
  markdown: string
  mermaid: string
  backend: string
  evidence_status: string
  evidence_notice: string
  knowledge: MessengerKnowledge
}
export type MessengerKnowledgeGraphResult = MessengerArtifactResult
export type MessengerLearningDocumentResult = MessengerArtifactResult

async function postArtifact(kind: string, topic: string, requestId: string, signal?: AbortSignal) {
  const { data } = await http.post<ApiEnvelope<MessengerArtifactResult>>(
    `/v1/student/messenger/tools/${kind}`, { topic, request_id: requestId }, { timeout: 90_000, signal },
  )
  if (data.code !== 0) throw new Error(data.message || '学习材料暂未生成')
  return data.data
}
export function postMessengerKnowledgeGraph(topic: string, requestId = createRequestId(), signal?: AbortSignal) {
  return postArtifact('knowledge-graph', topic, requestId, signal)
}
export function postMessengerLearningDocument(topic: string, requestId = createRequestId(), signal?: AbortSignal) {
  return postArtifact('learning-document', topic, requestId, signal)
}
export async function fetchMessengerArtifact(id: string, signal?: AbortSignal): Promise<MessengerArtifactResult> {
  const { data } = await http.get<ApiEnvelope<MessengerArtifactResult>>(
    `/v1/student/messenger/tools/artifacts/${encodeURIComponent(id)}`, { signal },
  )
  if (data.code !== 0) throw new Error(data.message || '学习材料暂不可用')
  return data.data
}
