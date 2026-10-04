<script setup lang="ts">
import { computed, onActivated, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NCard, NIcon, NModal, NTag, useMessage } from 'naive-ui'
import { ArrowForwardOutline, CheckmarkCircleOutline, SparklesOutline } from '@vicons/ionicons5'
import DashboardShell from '../components/layout/DashboardShell.vue'
import {
  fetchStudentEntitlements,
  fetchStudentChallengePack,
  fetchStudentStoreCatalog,
  fetchStudentStoreHistory,
  createStudentStoreOrder,
  fetchStudentStoreOrder,
  mockActivateProduct,
  type StoreOrder,
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
const challengeProgress = ref<{ completed_count: number; total: number; percent: number } | null>(null)
const paymentEnabled = ref(false)
const checkoutOrder = ref<StoreOrder | null>(null)
const checkoutVisible = ref(false)
const checkoutLoading = ref(false)
let orderPollTimer: ReturnType<typeof setInterval> | undefined
const particles = Array.from({ length: 22 }, (_, index) => ({
  left: `${7 + ((index * 37) % 86)}%`,
  top: `${8 + ((index * 53) % 78)}%`,
  delay: `${(index % 8) * -0.9}s`,
  duration: `${7 + (index % 6) * 1.4}s`,
  radius: index % 6 === 0 ? 2 : 1.3,
}))

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
  if (source === 'mock') return '体验开通'
  if (source === 'alipay') return '支付宝'
  return source
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
    paymentEnabled.value = catalog.payment_enabled
    entitlements.value = myEntitlements
    history.value = grants
    challengeProgress.value = null
    if (myEntitlements.membership_active || myEntitlements.challenge_pack_owned) {
      try {
        challengeProgress.value = (await fetchStudentChallengePack('challenge_pack_algorithms_01')).progress
      } catch {
        challengeProgress.value = null
      }
    }
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

function clearOrderPolling() {
  if (orderPollTimer) clearInterval(orderPollTimer)
  orderPollTimer = undefined
}

async function pollOrder() {
  const current = checkoutOrder.value
  if (!current || current.status !== 'pending') {
    clearOrderPolling()
    return
  }
  try {
    const updated = await fetchStudentStoreOrder(current.order_no)
    checkoutOrder.value = { ...current, ...updated }
    if (updated.status === 'paid') {
      clearOrderPolling()
      message.success('支付宝已确认付款，权益已开通')
      await load()
    } else if (updated.status !== 'pending') {
      clearOrderPolling()
    }
  } catch {
    // A temporary status query failure must not erase the open QR order.
  }
}

function beginOrderPolling() {
  clearOrderPolling()
  orderPollTimer = setInterval(() => void pollOrder(), 3000)
}

async function purchase(product: StoreProduct) {
  if (paymentEnabled.value) {
    if (checkoutLoading.value) return
    checkoutLoading.value = true
    try {
      checkoutOrder.value = await createStudentStoreOrder(product.code)
      checkoutVisible.value = true
      beginOrderPolling()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '订单创建失败')
    } finally {
      checkoutLoading.value = false
    }
  } else {
    await activate(product)
  }
}

function closeCheckout() {
  checkoutVisible.value = false
  clearOrderPolling()
  if (checkoutOrder.value?.status === 'paid') void load()
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
  if (paymentEnabled.value || entitlements.value?.mock_activation_enabled) void purchase(product)
}

onMounted(() => void load())
onUnmounted(clearOrderPolling)
onActivated(() => {
  if (!loading.value) void load()
})
</script>

<template>
  <DashboardShell
    active-nav="store"
    page-title="星港补给站"
    page-subtitle="按需解锁额外挑战与进阶成长体验"
    search-placeholder=""
    hide-search
  >
    <main class="store-page">
      <header class="store-hero">
        <div class="store-hero__copy">
          <span class="store-eyebrow"><n-icon :component="SparklesOutline" /> PLEX · 星港补给</span>
          <h1>为下一次跃迁，补充一点新装备</h1>
          <p>精选算法挑战与进阶权益，按需选择。</p>
          <div class="hero-pills"><span>自主选择</span><span>不自动续费</span></div>
        </div>
        <aside class="membership-status" :class="{ 'membership-status--active': entitlements?.membership_active }">
          <span class="status-orbit" aria-hidden="true"><i /></span>
          <small>会员状态</small>
          <strong>{{ entitlements?.membership_active ? '探索会员' : '未开通' }}</strong>
          <span v-if="entitlements?.membership_active" class="status-expiry">有效至 {{ membershipEndLabel }}</span>
        </aside>
      </header>

      <section v-if="loading" class="store-state">正在整理商品…</section>
      <section v-else-if="errorMessage" class="store-state store-state--error">
        <p>{{ errorMessage }}</p>
        <n-button secondary @click="load">重新加载</n-button>
      </section>
      <template v-else>
        <section class="mission-section">
          <div class="section-heading">
            <div><span class="section-kicker">额外探索内容</span><h2>星际挑战包</h2></div>
            <p>10 道算法编程挑战</p>
          </div>
          <article v-for="product in products.filter((item) => item.product_type === 'challenge_pack')" :key="product.code" class="mission-offer">
            <div class="mission-art" aria-hidden="true">
              <svg class="mission-planet" viewBox="0 0 520 390" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <radialGradient id="planetSurface" cx="34%" cy="27%" r="76%">
                    <stop offset="0" stop-color="#a9f3dc" />
                    <stop offset=".3" stop-color="#4ab9ae" />
                    <stop offset=".68" stop-color="#236881" />
                    <stop offset="1" stop-color="#101e3b" />
                  </radialGradient>
                  <linearGradient id="planetRing" x1="0" x2="1" y1="0" y2="1">
                    <stop stop-color="#b5fff0" stop-opacity=".08" />
                    <stop offset=".48" stop-color="#8bf4e3" stop-opacity=".8" />
                    <stop offset="1" stop-color="#82b8f3" stop-opacity=".12" />
                  </linearGradient>
                  <filter id="planetGlow" x="-60%" y="-60%" width="220%" height="220%">
                    <feGaussianBlur stdDeviation="16" />
                  </filter>
                  <clipPath id="planetClip"><circle cx="260" cy="190" r="91" /></clipPath>
                </defs>
                <circle cx="260" cy="190" r="115" fill="#48c8bd" opacity=".12" filter="url(#planetGlow)" />
                <ellipse cx="260" cy="190" rx="181" ry="51" fill="none" stroke="url(#planetRing)" stroke-width="2" transform="rotate(-19 260 190)" />
                <ellipse cx="260" cy="190" rx="153" ry="85" fill="none" stroke="#9ac9e5" stroke-opacity=".24" stroke-width="1" transform="rotate(48 260 190)" />
                <circle cx="260" cy="190" r="91" fill="url(#planetSurface)" />
                <g clip-path="url(#planetClip)" fill="#b0f1d8" opacity=".32">
                  <path d="M181 140l25-13 17 7 6 18-15 9-4 17-17 7-13-13-14-2 4-18zM247 113l24 7 11 18-8 14 12 11-5 20-16 6-3 22-18 14-15-10 6-25-10-14 8-15-9-14zM293 160l26-10 21 8 13 20-10 13-3 21-23 9-12-12-17-2-10-19zM225 222l19-8 18 8 5 18-17 13-21-7-12-13z" />
                </g>
                <circle cx="260" cy="190" r="91" fill="none" stroke="#c3fff0" stroke-opacity=".48" />
                <circle cx="391" cy="126" r="7" fill="#f2d89a" />
                <circle cx="123" cy="278" r="4" fill="#b8d8ff" />
                <circle v-for="(particle, index) in particles" :key="index" class="mission-particle" :cx="particle.left" :cy="particle.top" :r="particle.radius" :style="{ animationDelay: particle.delay, animationDuration: particle.duration }" />
              </svg>
            </div>
            <div class="mission-copy">
              <div class="mission-overline"><n-tag size="small" round type="info">算法基础</n-tag><span>永久解锁</span></div>
              <h3>{{ product.name }}</h3>
              <div class="mission-facts">
                <div><strong>10</strong><span>道挑战</span></div>
                <div><strong>分关</strong><span>循序渐进</span></div>
                <div><strong>不限</strong><span>练习次数</span></div>
              </div>
              <ul class="mission-benefits">
                <li v-for="benefit in product.benefits.slice(0, 3)" :key="benefit"><n-icon :component="CheckmarkCircleOutline" />{{ benefit }}</li>
              </ul>
              <div v-if="challengeProgress" class="mission-progress">
                <div><span>你的挑战进度</span><strong>{{ challengeProgress.completed_count }} / {{ challengeProgress.total }} 关</strong></div>
                <div class="progress-track"><i :style="{ width: `${challengeProgress.percent}%` }" /></div>
              </div>
              <div class="mission-actions">
                <div><strong>{{ formatPrice(product.price_cents) }}</strong></div>
                <n-button
                  v-if="product.active || entitlements?.membership_active"
                  type="primary" round size="large" @click="openChallenge(product)"
                >{{ challengeProgress?.completed_count ? '继续挑战' : '进入挑战' }} <n-icon :component="ArrowForwardOutline" /></n-button>
                <n-button v-else-if="product.available && (paymentEnabled || entitlements?.mock_activation_enabled)"
                  type="primary" round size="large"
                  :loading="activatingCode === product.code || (checkoutLoading && !checkoutOrder)"
                  @click="primaryAction(product)"
                >{{ paymentEnabled ? '立即开通' : '体验开通' }}</n-button>
              </div>
            </div>
          </article>
        </section>

        <section class="membership-section">
          <div class="section-heading section-heading--membership">
            <div><span class="section-kicker">探索会员</span><h2>会员方案</h2></div>
            <p>进阶报告与主题挑战包</p>
          </div>
          <div class="membership-layout">
            <article v-for="product in products.filter((item) => item.product_type === 'membership')" :key="product.code" class="membership-card" :class="{ 'membership-card--annual': product.duration_days === 365, 'membership-card--active': product.active }">
              <div class="membership-card__head">
                <span class="membership-glyph"><n-icon :component="product.duration_days === 30 ? SparklesOutline : CheckmarkCircleOutline" /></span>
                <n-tag v-if="product.active" round size="small" type="success">当前有效</n-tag>
                <n-tag v-else-if="product.duration_days === 365" round size="small" type="warning">年付更省</n-tag>
              </div>
              <h3>{{ product.name }}</h3>
              <div class="membership-price"><strong>{{ formatPrice(product.price_cents) }}</strong><span> / {{ product.duration_days === 30 ? '30 天' : '365 天' }}</span></div>
              <ul class="benefit-list">
                <li v-for="benefit in product.benefits.slice(0, 3)" :key="benefit"><n-icon :component="CheckmarkCircleOutline" />{{ benefit }}</li>
              </ul>
              <n-button v-if="product.available && (paymentEnabled || entitlements?.mock_activation_enabled)"
                type="primary" round block size="large"
                :loading="activatingCode === product.code || checkoutLoading"
                @click="purchase(product)"
              >{{ paymentEnabled ? '立即开通' : '体验开通' }}</n-button>
            </article>
          </div>
        </section>

        <section class="store-history">
          <header><div><span class="section-kicker">航行记录</span><h2>开通记录</h2></div><n-tag round :bordered="false">{{ history.length }} 条</n-tag></header>
          <div v-if="!history.length" class="history-empty">暂无记录</div>
          <ul v-else class="history-list">
            <li v-for="grant in history" :key="grant.id">
              <span class="history-dot" />
              <div><strong>{{ grant.product_name }}</strong><small>{{ formatDate(grant.created_at) }} · {{ grantSourceLabel(grant.source) }}</small></div>
              <span>{{ grant.expires_at ? `有效至 ${formatDate(grant.expires_at)}` : '永久拥有' }}</span>
            </li>
          </ul>
        </section>
      </template>
      <n-modal v-model:show="checkoutVisible" @after-leave="clearOrderPolling">
        <n-card class="checkout-card" :bordered="false" role="dialog" aria-modal="true" title="支付宝安全收银" closable @close="closeCheckout">
          <div v-if="checkoutOrder" class="checkout-content">
            <div class="checkout-product"><strong>{{ checkoutOrder.product_name }}</strong></div>
            <strong class="checkout-amount">¥{{ (checkoutOrder.amount_cents / 100).toFixed(2) }}</strong>
            <img v-if="checkoutOrder.qr_image_data_url && checkoutOrder.status === 'pending'" class="checkout-qr" :src="checkoutOrder.qr_image_data_url" alt="支付宝订单二维码" />
            <div class="checkout-status" :class="`checkout-status--${checkoutOrder.status}`">
              <template v-if="checkoutOrder.status === 'paid'">付款已确认，权益已经开通。</template>
              <template v-else-if="checkoutOrder.status === 'pending'">请使用支付宝扫描二维码；完成后页面会自动确认。</template>
              <template v-else-if="checkoutOrder.status === 'expired'">二维码已过期，请关闭窗口后重新下单。</template>
              <template v-else-if="checkoutOrder.status === 'failed'">二维码创建失败，请关闭窗口后重试。</template>
              <template v-else>此订单已关闭。</template>
            </div>
            <n-button v-if="checkoutOrder.status !== 'pending'" block type="primary" round @click="closeCheckout">完成</n-button>
          </div>
        </n-card>
      </n-modal>
    </main>
  </DashboardShell>
</template>

<style scoped>
.store-page { width: min(1220px, 100%); margin: 0 auto; padding: 1.8rem clamp(1rem, 3vw, 2.8rem) 4.5rem; color: #e9f7fb; }
.store-hero { position: relative; display: grid; grid-template-columns: 1fr 275px; align-items: center; gap: 2rem; min-height: 275px; overflow: hidden; padding: clamp(1.6rem, 4vw, 3.2rem); border: 1px solid rgba(83, 231, 222, .2); border-radius: 30px 30px 30px 8px; background: radial-gradient(ellipse at 70% 110%, rgba(38, 196, 189, .16), transparent 38%), linear-gradient(118deg, #0c2637 0%, #0a1827 63%, #111d37 100%); box-shadow: 0 28px 65px rgba(0, 0, 0, .23); }
.store-hero::after { content: ''; position: absolute; width: 300px; height: 300px; right: 210px; top: -220px; border: 1px solid rgba(112, 232, 223, .13); border-radius: 50%; box-shadow: 0 0 0 32px rgba(112,232,223,.025), 0 0 0 74px rgba(112,232,223,.02); pointer-events: none; }
.store-hero__copy { position: relative; z-index: 1; max-width: 720px; }
.store-eyebrow, .section-kicker { display: inline-flex; align-items: center; gap: .45rem; color: #79e9dd; font-size: .78rem; font-weight: 760; letter-spacing: .04em; }
.store-hero h1 { max-width: 680px; margin: .85rem 0 .65rem; color: #f4fbff; font-size: clamp(1.9rem, 4vw, 3rem); line-height: 1.14; letter-spacing: -.035em; }
.store-hero p { max-width: 610px; margin: 0; color: rgba(219, 235, 244, .7); line-height: 1.75; }
.hero-pills { display: flex; flex-wrap: wrap; gap: .55rem; margin-top: 1.15rem; }
.hero-pills span { padding: .38rem .72rem; border: 1px solid rgba(137,222,222,.16); border-radius: 999px; background: rgba(13,40,53,.68); color: #c8e5e9; font-size: .77rem; }
.membership-status { position: relative; z-index: 1; display: flex; min-height: 190px; flex-direction: column; justify-content: center; gap: .52rem; padding: 1.35rem; border: 1px solid rgba(169,200,219,.17); border-radius: 20px 20px 6px 20px; background: rgba(4, 17, 29, .73); box-shadow: inset 0 1px rgba(255,255,255,.04); }
.membership-status > small { color: rgba(219,235,244,.57); font-size: .78rem; }
.membership-status strong { color: #f4fbff; font-size: 1.2rem; }
.membership-status--active { border-color: rgba(85, 233, 179, .36); background: linear-gradient(145deg, rgba(10,48,48,.8), rgba(4,17,29,.82)); }
.membership-status--active strong { color: #90f0cb; }
.status-expiry { color: rgba(219,235,244,.62); font-size: .82rem; }
.status-orbit { position: relative; display: block; width: 28px; height: 28px; margin-bottom: .1rem; border: 1px solid rgba(106,230,215,.58); border-radius: 50%; }
.status-orbit::before { content: ''; position: absolute; inset: 6px; border-radius: 50%; background: #6de9d6; box-shadow: 0 0 14px rgba(109,233,214,.75); }
.status-orbit i { position: absolute; width: 5px; height: 5px; right: -3px; top: 4px; border-radius: 50%; background: #edcb83; }
.mission-section, .membership-section { margin-top: 3.1rem; }
.section-heading { display: flex; align-items: end; justify-content: space-between; gap: 1.5rem; margin-bottom: 1rem; }
.section-heading h2, .store-history h2 { margin: .3rem 0 0; color: #effaff; font-size: clamp(1.35rem, 2vw, 1.7rem); letter-spacing: -.02em; }
.section-heading > p { max-width: 410px; margin: 0; color: rgba(219,235,244,.53); font-size: .88rem; line-height: 1.6; text-align: right; }
.mission-offer { display: grid; grid-template-columns: minmax(240px, .72fr) 1.28fr; min-height: 360px; overflow: hidden; border: 1px solid rgba(80,221,216,.19); border-radius: 8px 26px 26px 26px; background: linear-gradient(110deg, rgba(8,25,41,.98), rgba(12,28,43,.98)); }
.mission-art { position: relative; min-height: 100%; overflow: hidden; background: radial-gradient(ellipse at 50% 50%, rgba(22,134,153,.2), transparent 57%), linear-gradient(165deg, #0d2940, #0b1729 75%); }
.mission-art::before { content: ''; position: absolute; inset: 13% 9%; border: 1px solid rgba(83,204,211,.15); border-radius: 49% 51% 43% 57%; transform: rotate(-22deg); }
.mission-planet { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; }
.mission-particle { fill: #b4fff1; opacity: .12; filter: drop-shadow(0 0 4px rgba(123,245,222,.9)); transform-box: fill-box; transform-origin: center; animation: particle-drift 8s ease-in-out infinite; }
@keyframes particle-drift { 0%, 100% { opacity: .12; transform: translateY(4px); } 50% { opacity: .9; transform: translateY(-7px); } }
.mission-copy { padding: clamp(1.35rem, 3vw, 2.3rem); }
.mission-overline { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.mission-overline > span { color: rgba(205,230,234,.52); font-size: .76rem; }
.mission-copy h3 { margin: .8rem 0 .5rem; color: #f2fbff; font-size: 1.55rem; letter-spacing: -.02em; }
.mission-copy > p { margin: 0; color: rgba(219,235,244,.62); font-size: .9rem; line-height: 1.65; }
.mission-facts { display: grid; grid-template-columns: repeat(3, 1fr); gap: .5rem; margin: 1.25rem 0 .9rem; padding: .9rem 0; border-top: 1px solid rgba(149,196,211,.1); border-bottom: 1px solid rgba(149,196,211,.1); }
.mission-facts div { display: grid; gap: .17rem; }
.mission-facts strong { color: #94e9dd; font-size: 1rem; }
.mission-facts span { color: rgba(219,235,244,.5); font-size: .72rem; }
.mission-benefits { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: .55rem .8rem; padding: 0; margin: .9rem 0 0; list-style: none; }
.mission-benefits li { display: flex; align-items: flex-start; gap: .42rem; color: rgba(219,235,244,.72); font-size: .78rem; line-height: 1.45; }
.mission-benefits .n-icon { flex: 0 0 auto; margin-top: .05rem; color: #79e8c4; }
.mission-progress { margin-top: 1rem; }
.mission-progress > div:first-child { display: flex; justify-content: space-between; gap: .8rem; color: rgba(219,235,244,.6); font-size: .78rem; }
.mission-progress strong { color: #a8f1df; font-weight: 650; }
.progress-track { height: 5px; overflow: hidden; margin-top: .5rem; border-radius: 999px; background: rgba(150,198,207,.15); }
.progress-track i { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg,#43c9b2,#b5e89f); box-shadow: 0 0 12px rgba(91,223,190,.4); transition: width .3s ease; }
.mission-actions { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-top: 1.15rem; }
.mission-actions > div { display: grid; gap: .14rem; }
.mission-actions strong { color: #9af1de; font-size: 1.65rem; }
.membership-section { padding-top: .1rem; }
.membership-layout { display: grid; grid-template-columns: minmax(0,.87fr) minmax(0,1.13fr); align-items: stretch; gap: 1rem; }
.membership-card { position: relative; display: flex; flex-direction: column; min-height: 370px; padding: 1.5rem; border: 1px solid rgba(130,181,205,.16); border-radius: 22px 8px 22px 22px; background: linear-gradient(152deg, rgba(15,34,51,.97), rgba(8,19,32,.98)); }
.membership-card--annual { border-color: rgba(229,189,104,.35); border-radius: 8px 22px 22px 22px; background: radial-gradient(ellipse at 85% 0%, rgba(173,126,44,.17), transparent 45%), linear-gradient(145deg, #18293b, #0c1929 78%); box-shadow: inset 0 1px rgba(255,231,180,.05), 0 16px 40px rgba(0,0,0,.16); }
.membership-card--active { border-color: rgba(88,232,174,.5); }
.membership-card__head { display: flex; min-height: 44px; align-items: center; justify-content: space-between; }
.membership-glyph { display: grid; place-items: center; width: 40px; height: 40px; border: 1px solid rgba(105,218,219,.22); border-radius: 12px 12px 12px 3px; background: rgba(53,151,165,.14); color: #99eee3; font-size: 1.25rem; }
.membership-card--annual .membership-glyph { border-color: rgba(229,189,104,.25); background: rgba(177,127,47,.15); color: #f1d48f; }
.membership-card h3 { margin: .9rem 0 .4rem; color: #f0f8fc; font-size: 1.28rem; }
.membership-price { display: flex; align-items: baseline; gap: .35rem; margin-top: .7rem; }
.membership-price strong { color: #9af1de; font-size: 2rem; letter-spacing: -.04em; }
.membership-card--annual .membership-price strong { color: #f3d68e; }
.membership-price span { color: rgba(219,235,244,.5); font-size: .8rem; }
.benefit-list { display: grid; flex: 1; align-content: start; gap: .58rem; padding: 1rem 0 1.1rem; margin: 0; list-style: none; color: rgba(219,235,244,.75); font-size: .82rem; }
.benefit-list li { display: flex; align-items: flex-start; gap: .48rem; line-height: 1.45; }
.benefit-list .n-icon { flex: 0 0 auto; margin-top: .03rem; color: #80e5c2; }
.membership-card--annual .benefit-list .n-icon { color: #e4c779; }
.store-history { margin-top: 2.6rem; padding: 1.35rem 1.5rem; border-top: 1px solid rgba(129,181,201,.17); border-bottom: 1px solid rgba(129,181,201,.1); background: rgba(8,20,33,.35); }
.store-history header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: .6rem; }
.store-history h2 { font-size: 1.22rem; }
.history-empty, .store-state { padding: 1.8rem .4rem; color: rgba(219,235,244,.53); font-size: .86rem; }
.history-list { display: grid; padding: 0; margin: 0; list-style: none; }
.history-list li { display: grid; grid-template-columns: 12px 1fr auto; align-items: center; gap: .8rem; padding: .85rem .15rem; border-top: 1px solid rgba(255,255,255,.055); color: rgba(219,235,244,.62); font-size: .82rem; }
.history-list li > div { display: grid; gap: .2rem; }
.history-list strong { color: #eaf8fc; font-size: .91rem; }
.history-list small { color: rgba(219,235,244,.45); }
.history-dot { width: 8px; height: 8px; border-radius: 50%; background: #6ce9d2; box-shadow: 0 0 12px rgba(108,233,210,.55); }
.store-state { text-align: center; }
.store-state--error { color: #ffb4ae; }
.checkout-card { width: min(430px, calc(100vw - 2rem)); border-radius: 22px; background: #0c1d2b; color: #e9f7fb; }
.checkout-content { display: grid; justify-items: center; gap: .9rem; text-align: center; }
.checkout-product { display: grid; gap: .3rem; }
.checkout-product strong { color: #effaff; font-size: 1.1rem; }
.checkout-product span, .checkout-content small { color: rgba(219,235,244,.55); font-size: .76rem; overflow-wrap: anywhere; }
.checkout-amount { color: #9af1de; font-size: 2rem; }
.checkout-qr { width: 220px; height: 220px; padding: 10px; border-radius: 14px; background: #fff; }
.checkout-status { color: #dcecf2; font-size: .9rem; line-height: 1.55; }
.checkout-status--paid { color: #91f0c6; }
.checkout-status--expired, .checkout-status--failed, .checkout-status--closed { color: #ffd298; }
@media (max-width: 820px) { .store-hero { grid-template-columns: 1fr; gap: 1.3rem; } .membership-status { min-height: 140px; } .mission-offer { grid-template-columns: minmax(170px,.65fr) 1.35fr; } .membership-layout { grid-template-columns: 1fr 1fr; } }
@media (max-width: 620px) { .store-page { padding-top: 1rem; } .store-hero { border-radius: 22px 22px 22px 6px; } .section-heading { align-items: flex-start; flex-direction: column; gap: .45rem; } .section-heading > p { text-align: left; } .mission-offer { grid-template-columns: 1fr; } .mission-art { min-height: 205px; } .mission-copy { padding: 1.15rem; } .mission-overline { align-items: flex-start; flex-direction: column; } .mission-benefits { grid-template-columns: 1fr; } .membership-layout { grid-template-columns: 1fr; } .membership-card { min-height: 0; } .history-list li { grid-template-columns: 12px 1fr; } .history-list li > span:last-child { grid-column: 2; } }
@media (prefers-reduced-motion: reduce) { .progress-track i { transition: none; } .mission-particle { animation: none; } }
</style>
