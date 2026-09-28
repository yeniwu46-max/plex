import { http, type ApiEnvelope } from './http'

export interface AdminStoreOrder {
  order_no: string
  user_id: number
  username: string | null
  real_name: string | null
  product_code: string | null
  product_name: string
  amount_cents: number
  provider: string
  status: 'pending' | 'paid' | 'expired' | 'closed' | 'failed'
  provider_trade_no: string | null
  expires_at: string | null
  paid_at: string | null
  created_at: string | null
}

export interface AdminStoreEntitlement {
  id: number
  user_id: number
  username: string | null
  real_name: string | null
  product_code: string
  product_name: string
  source: string
  starts_at: string | null
  expires_at: string | null
  created_at: string | null
  is_active: boolean
}

export interface AdminStoreOverview {
  summary: {
    paid_orders: number
    pending_orders: number
    gross_paid_cents: number
    active_entitlements: number
  }
  recent_orders: AdminStoreOrder[]
  recent_entitlements: AdminStoreEntitlement[]
}

export async function fetchAdminStoreOverview() {
  const { data } = await http.get<ApiEnvelope<AdminStoreOverview>>('/v1/admin/store/overview')
  if (data.code !== 0) throw new Error(data.message || '商店运营数据加载失败')
  return data.data
}
