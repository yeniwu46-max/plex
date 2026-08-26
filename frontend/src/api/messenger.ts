import { http, type ApiEnvelope } from './http'
import { postSseStream } from './sse'
import type { LearningRecommendation } from './learningReport'
import type { AgentTraceStep } from './agentService'

/** 驿站对话超时（LLM 生成通常 2–8 秒） */
const MESSENGER_CHAT_TIMEOUT_MS = 25_000
const MESSENGER_STREAM_TIMEOUT_MS = 35_000

export interface MessengerChatResult {
  reply: string
  source: 'xfyun_agent' | 'spark' | 'llm' | 'rules' | 'rag'
  recommendations?: LearningRecommendation[]
  rag_used?: boolean
  rag_sources?: Array<{ doc_id: string; score: number; snippet?: string }>
}

export interface MessengerChatHistoryItem {
  role: 'user' | 'assistant'
  content: string
}

export async function postMessengerChat(message: string, history: MessengerChatHistoryItem[] = []) {
  const { data } = await http.post<ApiEnvelope<MessengerChatResult>>(
    '/v1/student/messenger/chat',
    { message, history: history.slice(-18) },
    { timeout: MESSENGER_CHAT_TIMEOUT_MS },
  )
  if (data.code !== 0) throw new Error(data.message || '对话失败')
  return data.data
}

export interface MessengerStreamResult {
  reply: string
  source: string
  recommendations?: LearningRecommendation[]
  rag_used?: boolean
  illustration?: { url: string; caption?: string }
  thinking?: AgentTraceStep[]
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

/** SSE 流式驿站对话：收到 done 立即返回，图解可稍后到达。 */
export async function streamMessengerChat(
  message: string,
  history: MessengerChatHistoryItem[] = [],
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
  external?.addEventListener('abort', onExternalAbort)
  const timer = window.setTimeout(() => controller.abort(), MESSENGER_STREAM_TIMEOUT_MS)

  let illustration: { url: string; caption?: string } | undefined
  let thinking: AgentTraceStep[] | undefined
  const earlyHolder: { value: MessengerStreamResult | null } = { value: null }

  try {
    const doneEvent = await postSseStream(
      '/v1/student/messenger/chat/stream',
      { message, history: history.slice(-18) },
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
            reply: String(event.reply ?? ''),
            source: String(event.source ?? 'llm_stream'),
            recommendations: (event.recommendations as LearningRecommendation[] | undefined) ?? [],
            rag_used: Boolean(event.rag_used),
            illustration,
            thinking,
          }
          // 文字先落地，不等待后续 illustration 帧
          handlers.onDone?.(earlyHolder.value)
        },
        signal: controller.signal,
      },
    )
    const result = earlyHolder.value ?? (doneEvent
      ? {
          reply: String(doneEvent.reply ?? ''),
          source: String(doneEvent.source ?? 'llm_stream'),
          recommendations: (doneEvent.recommendations as LearningRecommendation[] | undefined) ?? [],
          rag_used: Boolean(doneEvent.rag_used),
          illustration:
            illustration
            ?? (doneEvent.illustration as { url: string; caption?: string } | undefined),
          thinking: thinking ?? mapThinking(doneEvent.thinking),
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

export interface MessengerKnowledgeGraphResult {
  topic: string
  mermaid: string
  illustration?: { url: string; caption?: string } | null
  backend: string
}

export interface MessengerLearningDocumentResult {
  title: string
  markdown: string
  backend: string
}

export async function postMessengerKnowledgeGraph(topic: string) {
  const { data } = await http.post<ApiEnvelope<MessengerKnowledgeGraphResult>>(
    '/v1/student/messenger/tools/knowledge-graph',
    { topic },
    { timeout: 35_000 },
  )
  if (data.code !== 0) throw new Error(data.message || '知识图生成失败')
  return data.data
}

export async function postMessengerLearningDocument(topic: string) {
  const { data } = await http.post<ApiEnvelope<MessengerLearningDocumentResult>>(
    '/v1/student/messenger/tools/learning-document',
    { topic },
    { timeout: 35_000 },
  )
  if (data.code !== 0) throw new Error(data.message || '文档生成失败')
  return data.data
}
