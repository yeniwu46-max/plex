import { http, type ApiEnvelope } from './http'
import type { LearningRecommendation } from './learningReport'

export interface MessengerChatResult {
  reply: string
  source: 'xfyun_agent' | 'spark' | 'llm' | 'rules' | 'rag'
  recommendations?: LearningRecommendation[]
  rag_used?: boolean
  rag_sources?: Array<{ doc_id: string; score: number; snippet?: string }>
}

export async function postMessengerChat(message: string) {
  const { data } = await http.post<ApiEnvelope<MessengerChatResult>>('/v1/student/messenger/chat', {
    message,
  })
  if (data.code !== 0) throw new Error(data.message || '对话失败')
  return data.data
}
