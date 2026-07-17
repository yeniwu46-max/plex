import { http, type ApiEnvelope } from './http'
import type { LearningRecommendation } from './learningReport'

/** 驿站对话 5 秒超时，超时后提示用户重试 */
const MESSENGER_CHAT_TIMEOUT_MS = 5_000

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
