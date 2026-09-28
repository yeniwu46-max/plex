<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NButton, NTag, useMessage } from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import { fetchAdminStoreOverview, type AdminStoreOverview } from '../../api/adminStore'

const message = useMessage()
const overview = ref<AdminStoreOverview | null>(null)
const loading = ref(false)
const error = ref('')

const paidOrders = computed(() => overview.value?.recent_orders.filter((order) => order.status === 'paid') ?? [])

function money(cents: number) {
  return `¥${(cents / 100).toFixed(2)}`
}

function dateTime(value: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  }).format(date)
}

function orderStatus(status: string) {
  return ({ paid: '已支付', pending: '待支付', expired: '已过期', closed: '已关闭', failed: '失败' } as Record<string, string>)[status] ?? status
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    overview.value = await fetchAdminStoreOverview()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '商店运营数据加载失败'
    message.error(error.value)
  } finally {
    loading.value = false
  }
}

onMounted(() => void load())
</script>

<template>
  <section class="admin-store" aria-label="权益商店运营数据">
    <header class="admin-store__heading">
      <div><span>PLEX · COMMERCE</span><h2>权益订单与用户升级记录</h2><p>付款以支付宝服务端通知为准，权益发放记录和订单状态分开保存。</p></div>
      <n-button secondary :loading="loading" @click="load"><template #icon><RefreshOutline /></template>刷新数据</n-button>
    </header>

    <div v-if="overview" class="admin-store__metrics">
      <article><small>累计已支付订单</small><strong>{{ overview.summary.paid_orders }}</strong></article>
      <article><small>累计支付金额</small><strong>{{ money(overview.summary.gross_paid_cents) }}</strong></article>
      <article><small>待支付订单</small><strong>{{ overview.summary.pending_orders }}</strong></article>
      <article><small>当前有效权益</small><strong>{{ overview.summary.active_entitlements }}</strong></article>
    </div>

    <div v-if="error && !overview" class="admin-store__empty">{{ error }}</div>
    <div v-else-if="loading && !overview" class="admin-store__empty">正在读取订单与权益…</div>
    <template v-else-if="overview">
      <section class="admin-store__section">
        <header><div><h3>近期支付订单</h3><span>展示最近 {{ overview.recent_orders.length }} 笔</span></div></header>
        <div v-if="!overview.recent_orders.length" class="admin-store__empty">还没有支付订单。</div>
        <div v-else class="admin-store__table-wrap">
          <table><thead><tr><th>用户</th><th>商品</th><th>金额</th><th>状态</th><th>创建时间</th><th>支付宝交易号</th></tr></thead>
            <tbody><tr v-for="order in overview.recent_orders" :key="order.order_no">
              <td><strong>{{ order.real_name || order.username || `用户 ${order.user_id}` }}</strong><small>{{ order.username }}</small></td>
              <td>{{ order.product_name }}</td><td>{{ money(order.amount_cents) }}</td>
              <td><n-tag size="small" round :type="order.status === 'paid' ? 'success' : order.status === 'pending' ? 'warning' : 'default'">{{ orderStatus(order.status) }}</n-tag></td>
              <td>{{ dateTime(order.created_at) }}</td><td class="mono">{{ order.provider_trade_no || '—' }}</td>
            </tr></tbody>
          </table>
        </div>
      </section>

      <section class="admin-store__section">
        <header><div><h3>已获得权益的用户</h3><span>显示最近 {{ overview.recent_entitlements.length }} 条开通记录</span></div></header>
        <div v-if="!overview.recent_entitlements.length" class="admin-store__empty">付款确认后，用户权益会显示在这里。</div>
        <div v-else class="admin-store__entitlements">
          <article v-for="grant in overview.recent_entitlements" :key="grant.id">
            <span class="grant-dot" :class="{ 'grant-dot--inactive': !grant.is_active }" />
            <div><strong>{{ grant.real_name || grant.username || `用户 ${grant.user_id}` }}</strong><small>@{{ grant.username }} · {{ grant.product_name }}</small></div>
            <div class="grant-source"><n-tag size="small" round :bordered="false" type="info">{{ grant.source === 'alipay' ? '支付宝订单' : grant.source === 'mock' ? '开发模拟' : grant.source }}</n-tag><small>{{ grant.expires_at ? `至 ${dateTime(grant.expires_at)}` : '永久权益' }}</small></div>
            <n-tag size="small" round :type="grant.is_active ? 'success' : 'default'">{{ grant.is_active ? '生效中' : '已到期' }}</n-tag>
          </article>
        </div>
      </section>
    </template>

    <section v-if="paidOrders.length" class="admin-store__note">所有已支付订单均由支付宝回调验签后自动发放权益；重复回调不会重复延长或重复授予。</section>
  </section>
</template>

<style scoped>
.admin-store { display: grid; gap: 1rem; padding: clamp(1rem,2.2vw,1.8rem); color: var(--text-primary,#eaf4ff); }
.admin-store__heading,.admin-store__section>header { display:flex; align-items:center; justify-content:space-between; gap:1rem; }
.admin-store__heading>div>span { color:#83dacc; font-size:.7rem; letter-spacing:.13em; font-weight:750; }
.admin-store__heading h2 { margin:.35rem 0; font-size:1.4rem; }
.admin-store__heading p,.admin-store__section>header span { margin:0; color:var(--text-muted,rgba(220,232,245,.55)); font-size:.8rem; }
.admin-store__metrics { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.8rem; }
.admin-store__metrics article,.admin-store__section { border:1px solid rgba(147,177,204,.14); border-radius:16px; background:rgba(9,22,37,.66); }
.admin-store__metrics article { display:grid; gap:.45rem; padding:1rem; }
.admin-store__metrics small { color:rgba(220,232,245,.55); font-size:.77rem; }
.admin-store__metrics strong { color:#a4eee0; font-size:1.45rem; }
.admin-store__section { overflow:hidden; }
.admin-store__section>header { padding:1rem 1.15rem; border-bottom:1px solid rgba(147,177,204,.1); }
.admin-store__section h3 { margin:0 0 .25rem; font-size:1rem; }
.admin-store__table-wrap { overflow:auto; }
table { width:100%; border-collapse:collapse; text-align:left; font-size:.8rem; white-space:nowrap; }
th,td { padding:.78rem .9rem; border-bottom:1px solid rgba(147,177,204,.08); }
th { color:rgba(220,232,245,.5); font-size:.72rem; font-weight:600; }
td { color:rgba(228,239,249,.76); }
td:first-child { display:grid; gap:.18rem; }
td:first-child strong { color:#eef7ff; }
td small,.grant-source small { color:rgba(220,232,245,.45); font-size:.7rem; }
.mono { font-family:ui-monospace,monospace; font-size:.73rem; }
.admin-store__entitlements { display:grid; }
.admin-store__entitlements article { display:grid; grid-template-columns:10px minmax(160px,1fr) auto auto; align-items:center; gap:.8rem; padding:.85rem 1.15rem; border-bottom:1px solid rgba(147,177,204,.08); }
.admin-store__entitlements article>div:nth-child(2),.grant-source { display:grid; gap:.2rem; }
.admin-store__entitlements article>div:nth-child(2) strong { font-size:.85rem; }
.admin-store__entitlements article>div:nth-child(2) small { color:rgba(220,232,245,.5); font-size:.72rem; }
.grant-source { justify-items:end; }
.grant-dot { width:8px; height:8px; border-radius:50%; background:#5ee1ad; box-shadow:0 0 10px rgba(94,225,173,.45); }
.grant-dot--inactive { background:#6e8294; box-shadow:none; }
.admin-store__empty { padding:1.4rem; color:rgba(220,232,245,.55); font-size:.83rem; }
.admin-store__note { padding:.8rem 1rem; border-left:2px solid #69cebd; background:rgba(33,95,88,.15); color:rgba(220,240,235,.7); font-size:.78rem; }
@media (max-width: 760px) { .admin-store__metrics { grid-template-columns:repeat(2,minmax(0,1fr)); } .admin-store__entitlements article { grid-template-columns:10px minmax(0,1fr) auto; } .grant-source { justify-items:start; grid-column:2; } .admin-store__entitlements article> :last-child { grid-column:3; grid-row:1; } .admin-store__heading { align-items:flex-start; flex-direction:column; } }
</style>
