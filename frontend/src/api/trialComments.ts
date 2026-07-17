import { formatHttpError, http, type ApiEnvelope } from './http'

export interface TrialCommentItem {
  id: number
  user_id: number
  author_name: string
  author_avatar_url?: string | null
  question_ref: string
  parent_id: number | null
  content: string
  like_count: number
  liked_by_me: boolean
  created_at: string | null
  replies: TrialCommentItem[]
}

export interface TrialCommentsResult {
  items: TrialCommentItem[]
}

export async function fetchTrialComments(questionRef: string) {
  try {
    const { data } = await http.get<ApiEnvelope<TrialCommentsResult>>('/v1/trial-comments', {
      params: { question_ref: questionRef },
    })
    if (data.code !== 0) throw new Error(data.message || '评论加载失败')
    return data.data
  } catch (error) {
    throw new Error(formatHttpError(error, '评论加载失败'))
  }
}

export async function createTrialComment(payload: {
  question_ref: string
  content: string
  parent_id?: number | null
}) {
  const body: Record<string, unknown> = {
    question_ref: payload.question_ref,
    content: payload.content,
  }
  if (payload.parent_id != null) {
    body.parent_id = payload.parent_id
  }
  try {
    const { data } = await http.post<ApiEnvelope<TrialCommentItem>>('/v1/trial-comments', body)
    if (data.code !== 0) throw new Error(data.message || '评论发布失败')
    return data.data
  } catch (error) {
    throw new Error(formatHttpError(error, '评论发布失败'))
  }
}

export async function toggleTrialCommentLike(commentId: number) {
  const { data } = await http.post<ApiEnvelope<{ comment_id: number; liked: boolean; like_count: number }>>(
    `/v1/trial-comments/${commentId}/like`,
  )
  if (data.code !== 0) throw new Error(data.message || '点赞失败')
  return data.data
}
