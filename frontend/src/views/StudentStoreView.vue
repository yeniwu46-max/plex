<script setup lang="ts">
import { computed, onActivated, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NIcon, NTag, useMessage } from 'naive-ui'
import { ArrowForwardOutline, CheckmarkCircleOutline, SparklesOutline } from '@vicons/ionicons5'
import DashboardShell from '../components/layout/DashboardShell.vue'
import {
  fetchStudentEntitlements,
  fetchStudentStoreCatalog,
  fetchStudentStoreHistory,
  mockActivateProduct,
  type StoreGrant,
  type StoreProduct,
  type StudentEntitlementsResult,
} from '../api/studentStore'

defineOptions({ name: 'StudentStoreView' })

const router = useRouter()
const message = useMessage()
const products = ref<StoreProduct[]>([])
const history = ref<StoreGrant[]>([])
const entitlements = ref<StudentEntitlementsResult | null>(null)
const loading = ref(true)
const activatingCode = ref('')
const errorMessage = ref('')

const membershipEndLabel = computed(() => formatDate(entitlements.value?.expires_at))

function formatPrice(cents: number) {
  return `¥${(cents / 100).toFixed(2)}`
}

function formatDate(value: string | null | undefined) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(date)
}

function grantSourceLabel(source: string) {
  return source === 'mock' ? '开发模拟权益' : source
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [catalog, myEntitlements, grants] = await Promise.all([
      fetchStudentStoreCatalog(),
      fetchStudentEntitlements(),
      fetchStudentStoreHistory(),
    ])
    products.value = catalog.products
    entitlements.value = myEntitlements
    history.value = grants
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '商店加载失败'
  } finally {
    loading.value = false
  }
}

async function activate(product: StoreProduct) {
  if (!entitlements.value?.mock_activation_enabled || !product.available || activatingCode.value) return
  activatingCode.value = product.code
  try {
    const result = await mockActivateProduct(product.code)
    message.success(result.already_owned ? '挑战包已在你的收藏中' : '模拟权益已开通，没有扣款')
    await load()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '模拟开通失败')
  } finally {
    activatingCode.value = ''
  }
}

function openChallenge(product: StoreProduct) {
  void router.push(`/student/store/challenges/${encodeURIComponent(product.code)}`)
}

function primaryAction(product: StoreProduct) {
  if (product.product_type === 'challenge_pack' && (product.active || entitlements.value?.membership_active)) {
    openChallenge(product)
    return
  }
  if (!product.available) return
  if (entitlements.value?.mock_activation_enabled) void activate(product)
}

onMounted(() => void load())
onActivated(() => {
  if (!loading.value) void load()
})
</script>

<template>
  <DashboardShell
    active-nav="store"
    page-title="星港商店"
    page-subtitle="按需解锁额外挑战与进阶成长体验"
    search-placeholder=""
    hide-search
  >
    <main class="store-page">
      <header class="store-hero">
        <div class="store-hero__copy">
          <span class="store-eyebrow"><n-icon :component="SparklesOutline" /> PLEX EXPLORER STORE</span>
          <h1>把下一段探索装进行囊</h1>
          <p>主线学习、基础练习和成长值始终开放。商店内容是额外体验，按需选择即可。</p>
        </div>
        <aside class="membership-status" :class="{ 'membership-status--active': entitlements?.membership_active }">
          <span>当前状态</span>
          <strong>{{ entitlements?.membership_active ? '探索会员生效中' : '免费探索者' }}</strong>
          <small v-if="entitlements?.membership_active">权益有效至 {{ membershipEndLabel }}</small>
          <small v-else>核心学习内容持续免费</small>
        </aside>
      </header>

      <section v-if="entitlements?.mock_activation_enabled" class="store-notice" role="status">
        模拟开通 · 不会扣款 · 不会生成真实付款记录
      </section>
      <section v-else class="store-notice store-notice--quiet" role="status">
        商品可预览，购买功能当前不可用。
      </section>

      <section v-if="loading" class="store-state">正在整理商品…</section>
      <section v-else-if="errorMessage" class="store-state store-state--error">
        <p>{{ errorMessage }}</p>
        <n-button secondary @click="load">重新加载</n-button>
      </section>
      <template v-else>
        <section class="store-section">
          <div class="store-section__heading">
            <div><span class="store-eyebrow">EXTRA MISSIONS</span><h2>主题挑战</h2></div>
            <span>一次购买，永久收藏</span>
          </div>
          <div class="product-grid product-grid--challenge">
            <article v-for="product in products.filter((item) => item.product_type === 'challenge_pack')" :key="product.code" class="product-card product-card--challenge">
              <div class="product-card__art"><span>01</span><i aria-hidden="true">✦</i></div>
              <div class="product-card__body">
                <div class="product-card__title-row"><h3>{{ product.name }}</h3><n-tag round size="small" type="info">额外内容</n-tag></div>
                <p>{{ product.description }}</p>
                <small v-if="product.available">10 道精选编程题 · 不影响免费主线</small>
                <small v-else class="product-unavailable">题库准备中，暂不可开通</small>
                <div class="product-card__footer">
                  <strong>{{ formatPrice(product.price_cents) }}</strong>
                  <n-button
                    v-if="product.active || entitlements?.membership_active"
                    type="primary" secondary round
                    @click="openChallenge(product)"
                  >进入挑战 <n-icon :component="ArrowForwardOutline" /></n-button>
                  <n-button
                    v-else
                    type="primary" round
                    :disabled="!product.available || !entitlements?.mock_activation_enabled"
                    :loading="activatingCode === product.code"
                    @click="primaryAction(product)"
                  >{{ entitlements?.mock_activation_enabled ? '模拟开通' : '当前不可购买' }}</n-button>
                </div>
              </div>
            </article>
          </div>
        </section>

        <section class="store-section">
          <div class="store-section__heading">
            <div><span class="store-eyebrow">EXPLORER MEMBERSHIP</span><h2>探索会员</h2></div>
            <span>手动开通，不自动续费</span>
          </div>
          <div class="product-grid">
            <article v-for="product in products.filter((item) => item.product_type === 'membership')" :key="product.code" class="product-card">
              <div class="membership-icon"><n-icon :component="product.duration_days === 30 ? SparklesOutline : CheckmarkCircleOutline" /></div>
              <div class="product-card__title-row"><h3>{{ product.name }}</h3><n-tag v-if="product.active" round size="small" type="success">已开通</n-tag></div>
              <p>{{ product.description }}</p>
              <ul class="benefit-list">
                <li><n-icon :component="CheckmarkCircleOutline" /> 当前主题挑战包</li>
                <li><n-icon :component="CheckmarkCircleOutline" /> 进阶阶段报告</li>
              </ul>
              <div class="product-card__footer">
                <div><strong>{{ formatPrice(product.price_cents) }}</strong><small> / {{ product.duration_days === 30 ? '30 天' : '365 天' }}</small></div>
                <n-button
                  type="primary" round
                  :disabled="!entitlements?.mock_activation_enabled"
                  :loading="activatingCode === product.code"
                  @click="activate(product)"
                >{{ entitlements?.mock_activation_enabled ? '模拟开通' : '当前不可购买' }}</n-button>
              </div>
            </article>
          </div>
        </section>

        <section class="store-history">
          <header><div><span class="store-eyebrow">MY EXPLORATION</span><h2>我的权益记录</h2></div><n-tag round :bordered="false">{{ history.length }} 条</n-tag></header>
          <div v-if="!history.length" class="history-empty">开通的挑战包和会员权益会显示在这里。</div>
          <ul v-else class="history-list">
            <li v-for="grant in history" :key="grant.id">
              <span class="history-dot" />
              <div><strong>{{ grant.product_name }}</strong><small>{{ formatDate(grant.created_at) }} · {{ grantSourceLabel(grant.source) }}</small></div>
              <span>{{ grant.expires_at ? `有效至 ${formatDate(grant.expires_at)}` : '永久拥有' }}</span>
            </li>
          </ul>
        </section>
      </template>
    </main>
  </DashboardShell>
</template>

<style scoped>
.store-page { width: min(1160px, 100%); margin: 0 auto; padding: 2rem clamp(1rem, 3vw, 2.5rem) 4rem; color: #e7f4fa; }
.store-hero { display: flex; justify-content: space-between; align-items: center; gap: 2rem; padding: clamp(1.5rem, 4vw, 3rem); border: 1px solid rgba(61, 236, 221, .18); border-radius: 28px; background: radial-gradient(circle at 78% 12%, rgba(31, 190, 195, .2), transparent 36%), linear-gradient(135deg, rgba(9, 31, 48, .95), rgba(9, 17, 32, .96)); box-shadow: 0 24px 80px rgba(0, 0, 0, .24); }
.store-hero__copy { max-width: 680px; }
.store-eyebrow { display: inline-flex; align-items: center; gap: .4rem; color: #73eadd; font-size: .73rem; font-weight: 800; letter-spacing: .14em; }
.store-hero h1 { margin: .8rem 0 .65rem; color: #f4fbff; font-size: clamp(1.8rem, 4vw, 3rem); }
.store-hero p, .product-card p { color: rgba(219, 235, 244, .72); line-height: 1.7; }
.membership-status { min-width: 220px; padding: 1.1rem 1.25rem; border: 1px solid rgba(255,255,255,.1); border-radius: 18px; background: rgba(3, 13, 24, .58); display: flex; flex-direction: column; gap: .45rem; }
.membership-status span, .membership-status small { color: rgba(219,235,244,.62); }
.membership-status strong { color: #f3fcff; }
.membership-status--active { border-color: rgba(69, 230, 173, .35); }
.membership-status--active strong { color: #73efc0; }
.store-notice { margin: 1.2rem 0 2rem; padding: .85rem 1rem; border: 1px solid rgba(244, 197, 94, .24); border-radius: 14px; background: rgba(124, 82, 11, .14); color: #f7d996; font-size: .9rem; }
.store-notice--quiet { border-color: rgba(105, 169, 193, .16); background: rgba(17, 37, 53, .45); color: rgba(219,235,244,.68); }
.store-section { margin-top: 2.3rem; }
.store-section__heading, .store-history header { display: flex; align-items: end; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; }
.store-section__heading h2, .store-history h2 { margin: .25rem 0 0; color: #f1fbff; font-size: 1.5rem; }
.store-section__heading > span { color: rgba(219,235,244,.56); font-size: .86rem; }
.product-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
.product-grid--challenge { grid-template-columns: minmax(0, 1fr); }
.product-card { position: relative; overflow: hidden; padding: 1.45rem; border: 1px solid rgba(124, 209, 221, .14); border-radius: 22px; background: linear-gradient(145deg, rgba(14, 34, 50, .95), rgba(8, 18, 31, .95)); }
.product-card--challenge { display: grid; grid-template-columns: minmax(180px, .7fr) 1.3fr; gap: 1.5rem; align-items: center; }
.product-card__art { min-height: 200px; display: grid; place-items: center; position: relative; overflow: hidden; border-radius: 17px; background: radial-gradient(circle at 50% 40%, rgba(63, 244, 210, .28), transparent 33%), linear-gradient(135deg, #102d4a, #0a1728); color: #8efbed; }
.product-card__art::before, .product-card__art::after { content: ''; position: absolute; width: 180px; height: 180px; border: 1px solid rgba(103, 240, 223, .27); border-radius: 50%; transform: rotateX(68deg); }
.product-card__art::after { width: 125px; height: 125px; transform: rotateX(68deg) rotateZ(55deg); }
.product-card__art span { position: absolute; top: 1rem; left: 1rem; font-size: .78rem; letter-spacing: .14em; }
.product-card__art i { z-index: 1; font-size: 4.5rem; font-style: normal; text-shadow: 0 0 35px rgba(73,255,226,.8); }
.product-card__title-row { display: flex; justify-content: space-between; align-items: center; gap: .6rem; }
.product-card h3 { margin: 0; color: #effaff; font-size: 1.2rem; }
.product-card p { min-height: 3rem; margin: .7rem 0; font-size: .92rem; }
.product-card__body > small { color: rgba(219,235,244,.55); }
.product-unavailable { color: #f3c773 !important; }
.product-card__footer { display: flex; align-items: center; justify-content: space-between; gap: .8rem; margin-top: 1.2rem; }
.product-card__footer strong { color: #80f4dd; font-size: 1.6rem; }
.product-card__footer small { color: rgba(219,235,244,.55); }
.membership-icon { display: grid; place-items: center; width: 44px; height: 44px; margin-bottom: 1rem; border: 1px solid rgba(92, 230, 218, .28); border-radius: 14px; background: rgba(47, 188, 181, .12); color: #80f4dd; font-size: 1.4rem; }
.benefit-list { display: grid; gap: .55rem; padding: 0; margin: .9rem 0 0; list-style: none; color: rgba(219,235,244,.77); font-size: .9rem; }
.benefit-list li { display: flex; align-items: center; gap: .45rem; }
.benefit-list .n-icon { color: #72eac2; }
.store-history { margin-top: 2.5rem; padding: 1.4rem; border: 1px solid rgba(124, 209, 221, .12); border-radius: 20px; background: rgba(8, 20, 33, .76); }
.store-history header { align-items: center; margin-bottom: .6rem; }
.history-empty, .store-state { padding: 2rem; color: rgba(219,235,244,.6); text-align: center; }
.history-list { display: grid; gap: .2rem; padding: 0; margin: 0; list-style: none; }
.history-list li { display: grid; grid-template-columns: 12px 1fr auto; align-items: center; gap: .8rem; padding: .8rem .25rem; border-top: 1px solid rgba(255,255,255,.06); color: rgba(219,235,244,.65); font-size: .85rem; }
.history-list li > div { display: grid; gap: .2rem; }
.history-list strong { color: #eaf8fc; font-size: .95rem; }
.history-list small { color: rgba(219,235,244,.48); }
.history-dot { width: 8px; height: 8px; border-radius: 50%; background: #6ce9d2; box-shadow: 0 0 12px rgba(108,233,210,.55); }
.store-state--error { color: #ffb4ae; }
@media (max-width: 760px) { .store-hero { align-items: stretch; flex-direction: column; } .product-grid { grid-template-columns: 1fr; } .product-card--challenge { grid-template-columns: 1fr; } .product-card__art { min-height: 150px; } .history-list li { grid-template-columns: 12px 1fr; } .history-list li > span:last-child { grid-column: 2; } }
</style>
