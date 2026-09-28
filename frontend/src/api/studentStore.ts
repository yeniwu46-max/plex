import { http, type ApiEnvelope } from './http'

export interface StoreProduct {
  code: string
  name: string
  description: string
  product_type: 'membership' | 'challenge_pack'
  price_cents: number
  duration_days: number | null
  benefits: string[]
  owned: boolean
  active: boolean
  expires_at: string | null
  available: boolean
}

export interface StoreCatalogResult {
  products: StoreProduct[]
  mock_activation_enabled: boolean
}

export interface StudentEntitlementsResult {
  membership_active: boolean
  expires_at: string | null
  active_features: string[]
  challenge_pack_owned: boolean
  challenge_pack_available: boolean
  mock_activation_enabled: boolean
}

export interface StoreGrant {
  id: number
  product_code: string
  product_name: string
  source: 'mock' | string
  starts_at: string | null
  expires_at: string | null
  created_at: string | null
}

export interface StoreChallengeQuestion {
  id: string
  code: string
  title: string
  topic: string
  difficulty: string
  duration_min: number
  question_type: string
}

export interface StoreChallengePack {
  product_code: string
  title: string
  questions: StoreChallengeQuestion[]
  total: number
}

async function unwrap<T>(request: Promise<{ data: ApiEnvelope<T> }>, fallback: string): Promise<T> {
  const { data } = await request
  if (data.code !== 0) throw new Error(data.message || fallback)
  return data.data
}

export function fetchStudentStoreCatalog() {
  return unwrap(http.get<ApiEnvelope<StoreCatalogResult>>('/v1/student/store/catalog'), '商店加载失败')
}

export function fetchStudentEntitlements() {
  return unwrap(http.get<ApiEnvelope<StudentEntitlementsResult>>('/v1/student/entitlements/me'), '权益加载失败')
}

export function fetchStudentStoreHistory() {
  return unwrap(http.get<ApiEnvelope<StoreGrant[]>>('/v1/student/store/history'), '记录加载失败')
}

export function mockActivateProduct(productCode: string) {
  return unwrap(
    http.post<ApiEnvelope<{ grant: StoreGrant; already_owned: boolean }>>('/v1/student/store/mock-activation', {
      product_code: productCode,
    }),
    '模拟开通失败',
  )
}

export function fetchStudentChallengePack(productCode: string) {
  return unwrap(
    http.get<ApiEnvelope<StoreChallengePack>>(`/v1/student/store/challenge-packs/${encodeURIComponent(productCode)}`),
    '挑战包加载失败',
  )
}
