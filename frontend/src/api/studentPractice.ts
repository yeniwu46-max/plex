import { http, type ApiEnvelope } from './http'
import type { PracticeQuestionPayload } from './practiceQuestions'
export interface Attempt { id: string; question_ref: string; question_version: string; title: string; code: string; created_at: string; source: string; result: { all_passed?: boolean; code_passed?: boolean } }
export interface Exam { id: string; status: string; questions: PracticeQuestionPayload[]; answers: Record<string,string>; results: Record<string,{all_passed: boolean; attempt_id: string}>; revision: number; deadline: string; server_time: string; score: number | null }
export async function practiceRequest<T>(method: string, url: string, data?: unknown, params?: unknown): Promise<T> {
  const response = await http.request<ApiEnvelope<T>>({method, url: '/v1/student' + url, data, params})
  if (response.data.code !== 0) throw new Error(response.data.message)
  return response.data.data
}
export const fetchPracticeHistory = (page=1) => practiceRequest<{items: Attempt[]; total: number}>('get','/practice-history',undefined,{page})
export const setQuestionFavorite = (ref: string, enabled: boolean) => practiceRequest(enabled?'put':'delete',`/question-favorites/${encodeURIComponent(ref)}`)
export const submitPractice = (ref: string, code: string, request_id: string) => practiceRequest<Attempt>('post',`/practice-submissions/${encodeURIComponent(ref)}`,{code,request_id})
