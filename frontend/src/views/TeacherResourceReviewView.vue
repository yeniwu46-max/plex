<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NButton, NEmpty, NInput, NTag, useMessage } from 'naive-ui'
import TeacherDashboardShell from '../components/layout/TeacherDashboardShell.vue'
import { fetchReviewResources, reviewPersonalizedResource, type PersonalizedResource } from '../api/personalizedResources'

const message = useMessage()
const items = ref<PersonalizedResource[]>([])
const reasons = ref<Record<number, string>>({})
async function load() { items.value = (await fetchReviewResources()).items }
async function review(item: PersonalizedResource, status: 'approved' | 'rejected') {
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
      <n-empty v-if="!items.length" description="当前没有待审核资源" />
      <article v-for="item in items" :key="item.id" class="review-card">
        <header><div><n-tag type="warning">{{ item.review_status }}</n-tag><n-tag>{{ item.resource_type }}</n-tag></div><span>置信度 {{ Math.round(item.confidence * 100) }}% · {{ item.backend }}</span></header>
        <h3>{{ item.title }}</h3><p>{{ item.recommendation_reason }}</p><pre>{{ JSON.stringify(item.content, null, 2) }}</pre>
        <ul><li v-for="citation in item.citations" :key="citation.document_id">{{ citation.title }}：{{ citation.snippet }}</li></ul>
        <n-input v-model:value="reasons[item.id]" placeholder="审核说明" />
        <footer><n-button type="error" secondary @click="review(item, 'rejected')">驳回</n-button><n-button type="primary" @click="review(item, 'approved')">批准发布</n-button></footer>
      </article>
    </main>
  </TeacherDashboardShell>
</template>

<style scoped>
.review-page{width:100%;padding:0 var(--plex-page-gutter-x) 2rem;overflow-y:auto}.review-card{margin-bottom:1rem;padding:1.2rem;border:1px solid rgba(255,173,76,.2);border-radius:16px;background:rgba(25,15,7,.72)}.review-card header,.review-card footer{display:flex;align-items:center;justify-content:space-between;gap:.6rem}.review-card header div{display:flex;gap:.5rem}.review-card header span,.review-card p,.review-card li{color:rgba(235,215,194,.7)}.review-card h3{color:#fff7ec}.review-card pre{max-height:260px;overflow:auto;white-space:pre-wrap;color:#e7d4bf;background:rgba(0,0,0,.18);padding:.8rem;border-radius:10px}.review-card footer{justify-content:flex-end;margin-top:.8rem}
</style>
