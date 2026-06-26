<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NButton, NEmpty, NInput, NTag, useMessage } from 'naive-ui'
import TeacherDashboardShell from '../components/layout/TeacherDashboardShell.vue'
import {
  fetchResourceReviewMetrics,
  fetchReviewResources,
  reviewPersonalizedResource,
  type PersonalizedResource,
  type ResourceReviewMetrics,
} from '../api/personalizedResources'

const message = useMessage()
const items = ref<PersonalizedResource[]>([])
const metrics = ref<ResourceReviewMetrics | null>(null)
const reasons = ref<Record<number, string>>({})
async function load() {
  const [resources, reviewMetrics] = await Promise.all([
    fetchReviewResources(),
    fetchResourceReviewMetrics(),
  ])
  items.value = resources.items
  metrics.value = reviewMetrics
}
async function review(item: PersonalizedResource, status: 'approved' | 'rejected') {
  if (status === 'approved' && !reasons.value[item.id]?.trim()) {
    message.warning('批准资源前必须填写审核说明')
    return
  }
  try {
    await reviewPersonalizedResource(item.id, status, reasons.value[item.id] || '')
    message.success(status === 'approved' ? '资源已批准' : '资源已驳回')
    await load()
  } catch (error) { message.error(error instanceof Error ? error.message : '审核失败') }
}
onMounted(() => void load())
</script>

<template>
  <TeacherDashboardShell active-nav="resources" page-title="资源审核" page-subtitle="核验低置信度或引用异常的个性化资源" hide-search hide-toolbar>
    <main class="review-page">
      <section v-if="metrics" class="metric-grid" aria-label="资源审核指标">
        <article><span>待审核</span><strong>{{ metrics.pending_review_count }}</strong></article>
        <article><span>已批准</span><strong>{{ metrics.status_counts.approved }}</strong></article>
        <article><span>已驳回</span><strong>{{ metrics.status_counts.rejected }}</strong></article>
        <article><span>平均审核时长</span><strong>{{ metrics.average_review_minutes ?? '—' }} 分钟</strong></article>
        <article class="risk-summary">
          <span>风险原因</span>
          <div><n-tag v-for="risk in metrics.risk_reason_distribution" :key="risk.reason" type="warning">{{ risk.reason }} × {{ risk.count }}</n-tag></div>
        </article>
      </section>
      <n-empty v-if="!items.length" description="当前没有待审核资源" />
      <article v-for="item in items" :key="item.id" class="review-card">
        <header><div><n-tag type="warning">{{ item.review_status }}</n-tag><n-tag>{{ item.resource_type }}</n-tag></div><span>置信度 {{ Math.round(item.confidence * 100) }}% · {{ item.backend }}</span></header>
        <h3>{{ item.title }}</h3><div class="risks"><n-tag v-for="risk in item.risk_reasons" :key="risk" type="error">{{ risk }}</n-tag></div><p>{{ item.recommendation_reason }}</p><pre>{{ JSON.stringify(item.content, null, 2) }}</pre>
        <ul><li v-for="citation in item.citations" :key="citation.document_id">{{ citation.title }}：{{ citation.snippet }}</li></ul>
        <n-input v-model:value="reasons[item.id]" placeholder="审核说明" />
        <footer><n-button type="error" secondary @click="review(item, 'rejected')">驳回</n-button><n-button type="primary" @click="review(item, 'approved')">批准发布</n-button></footer>
      </article>
    </main>
  </TeacherDashboardShell>
</template>

<style scoped>
.review-page{width:100%;padding:0 var(--plex-page-gutter-x) 2rem;overflow-y:auto}.review-card{margin-bottom:1rem;padding:1.2rem;border:1px solid rgba(255,173,76,.2);border-radius:16px;background:rgba(25,15,7,.72)}.review-card header,.review-card footer{display:flex;align-items:center;justify-content:space-between;gap:.6rem}.review-card header div{display:flex;gap:.5rem}.review-card header span,.review-card p,.review-card li{color:rgba(235,215,194,.7)}.review-card h3{color:#fff7ec}.review-card pre{max-height:260px;overflow:auto;white-space:pre-wrap;color:#e7d4bf;background:rgba(0,0,0,.18);padding:.8rem;border-radius:10px}.review-card footer{justify-content:flex-end;margin-top:.8rem}
.risks{display:flex;flex-wrap:wrap;gap:.4rem}
.metric-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.8rem;margin-bottom:1rem}.metric-grid article{padding:1rem;border:1px solid rgba(255,173,76,.2);border-radius:14px;background:rgba(25,15,7,.72)}.metric-grid span{display:block;color:rgba(235,215,194,.68)}.metric-grid strong{display:block;margin-top:.35rem;color:#fff7ec;font-size:1.35rem}.metric-grid .risk-summary{grid-column:1/-1}.risk-summary div{display:flex;flex-wrap:wrap;gap:.45rem;margin-top:.55rem}@media(max-width:800px){.metric-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
