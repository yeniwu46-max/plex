import { http, type ApiEnvelope } from './http'

export type ClassRequestAction = 'create' | 'update' | 'delete'
export type ClassRequestStatus = 'pending' | 'approved' | 'rejected'

export interface ClassChangeRequest {
  id: number
  requester_id: number
  requester_name: string | null
  action: ClassRequestAction
  status: ClassRequestStatus
  class_id: number | null
  class_name: string | null
  payload: Record<string, unknown>
  reason: string | null
  reviewer_id: number | null
  review_note: string | null
  created_at: string | null
  reviewed_at: string | null
}

export async function fetchClassRequests(status?: ClassRequestStatus) {
  const { data } = await http.get<ApiEnvelope<ClassChangeRequest[]>>('/v1/class-requests', {
    params: status ? { status } : undefined,
  })
  if (data.code !== 0) throw new Error(data.message || '加载申请失败')
  return data.data
}

export async function submitClassRequest(body: {
  action: ClassRequestAction
  class_id?: number
  payload: Record<string, unknown>
  reason?: string
}) {
  const { data } = await http.post<ApiEnvelope<ClassChangeRequest>>('/v1/class-requests', body)
  if (data.code !== 0) throw new Error(data.message || '提交申请失败')
  return data.data
}

export async function reviewClassRequest(requestId: number, approve: boolean, note?: string) {
  const { data } = await http.post<ApiEnvelope<ClassChangeRequest>>(
    `/v1/class-requests/${requestId}/review`,
    { approve, note },
  )
  if (data.code !== 0) throw new Error(data.message || '审批失败')
  return data.data
}
