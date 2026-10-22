<script setup lang="ts">
import { computed, onActivated, onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
import { useAuthStore } from '../../stores/auth'
import AiCostEstimate from './AiCostEstimate.vue'
import { fetchModelUsage, fetchResourceQuota, fetchRagQuota, type RagQuota, type ModelUsage, type ResourceQuota } from '../../api/aiUsage'

const props = defineProps<{ classId?: number | null }>()
const auth = useAuthStore()
const open = ref(false)
const loading = ref(false)
const error = ref('')
const usage = ref<ModelUsage | null>(null)
const resourceQuota = ref<ResourceQuota | null>(null)
const ragQuota = ref<RagQuota | null>(null)
let version = 0
let active = true
const title = computed(() => props.classId == null ? '我的 AI 用量' : '当前班级 AI 用量')
const labels = { tutor: '小 E 辅导', resource: '学习资源', rag: '课程问答', counterexample: '反例出题' }
const resetTime = computed(() => usage.value ? new Date(usage.value.reset_at).toLocaleString() : '')

async function refresh() {
  const run = ++version
  usage.value = null
  resourceQuota.value = null
  ragQuota.value = null
  error.value = ''
  loading.value = false
  if (!active || !auth.profile?.id) return
  loading.value = true
  try {
    const [result, quota, rag] = await Promise.all([fetchModelUsage(props.classId),
      props.classId != null || auth.profile?.role === 'student' ? fetchResourceQuota(props.classId) : Promise.resolve(null),
      props.classId == null && ['teacher', 'admin'].includes(auth.profile?.role || '') ? fetchRagQuota() : Promise.resolve(null)])
    if (run === version) { usage.value = result; resourceQuota.value = quota; ragQuota.value = rag }
  } catch (err) {
    if (run === version) error.value = (err as Error).message || '暂时无法读取用量'
  } finally {
    if (run === version) loading.value = false
  }
}
function toggle() {
  open.value = !open.value
  if (open.value) void refresh()
}
watch(() => [auth.profile?.id, auth.profile?.role, props.classId], () => {
  version++
  usage.value = null
  resourceQuota.value = null
  ragQuota.value = null
  error.value = ''
  loading.value = false
  if (open.value) void refresh()
}, { flush: 'sync' })
function deactivate() {
  active = false; version++
  usage.value = null; resourceQuota.value = null; ragQuota.value = null
  error.value = ''; loading.value = false
}
onDeactivated(deactivate)
onActivated(() => { active = true; if (open.value) void refresh() })
onBeforeUnmount(deactivate)
</script>

<template>
  <section class="ai-usage">
    <button class="ai-usage__toggle" type="button" :aria-expanded="open" @click="toggle">
      <span>{{ title }}</span><span aria-hidden="true">{{ open ? '−' : '+' }}</span>
    </button>
    <div v-if="open" class="ai-usage__body" :aria-busy="loading">
      <p v-if="loading" role="status">正在读取用量…</p>
      <p v-if="error" role="alert">{{ error }}</p>
      <template v-if="usage">
        <p v-if="ragQuota">课程问答：本周期剩余 <strong>{{ ragQuota.requests_remaining }} / {{ ragQuota.request_limit }}</strong> 次 · 处理中 {{ ragQuota.active_requests }} / {{ ragQuota.concurrency_limit }} 项。每个请求最多 {{ ragQuota.attempt_limit }} 次尝试；恢复已完成回答不占新额度，失败重试会占额度。</p>
        <p v-if="resourceQuota">资源生成：本周期剩余 <strong>{{ resourceQuota.requests_remaining }} / {{ resourceQuota.request_limit }}</strong> 次 · 排队或生成中 {{ resourceQuota.active_tasks }} / {{ resourceQuota.active_limit }} 项。每条任务链最多 {{ resourceQuota.attempt_limit }} 次尝试，失败重试也占用新额度。</p>
        <p>本周期调用 <strong>{{ usage.totals.calls }}</strong> 次 · 已报告 <strong>{{ usage.totals.reported_total_tokens.toLocaleString() }}</strong> tokens</p>
        <p>用量未报告 {{ usage.totals.unknown_usage_calls }} 次 · 失败 {{ usage.totals.failed_calls }} 次 · 未结束或已中断 {{ usage.totals.unfinished_calls }} 次</p>
        <ul>
          <li v-for="(label, key) in labels" :key="key">{{ label }} <strong>{{ usage.workflows[key].calls }}</strong> 次</li>
        </ul>
        <p class="ai-usage__note">按 UTC 日统计，本周期于 {{ resetTime }} 结束。tokens 是模型处理的文本单位；未报告部分不计入已报告总量。</p>
        <AiCostEstimate :estimate="usage.cost_estimate" />
        <p class="ai-usage__note">仅含已接入统计的文本模型，生成、审核、备用模型及重试分别计次；不含语音、图像、视频与向量检索。</p>
        <p v-if="classId != null" class="ai-usage__note">班级统计仅包含任务创建时已绑定本班的学习资源和反例任务；未绑定班级的辅导、问答及旧记录不计入。</p>
      </template>
      <button class="ai-usage__refresh" type="button" :disabled="loading" @click="refresh">{{ error ? '重试' : '刷新用量' }}</button>
    </div>
  </section>
</template>

<style scoped>
.ai-usage { color: var(--plex-text); background: var(--plex-bg-card); border: 1px solid var(--plex-border, #526378); border-radius: 12px; min-width: 0; }
.ai-usage__toggle { display: flex; justify-content: space-between; gap: 16px; width: 100%; padding: 12px 16px; border: 0; background: transparent; color: inherit; font: inherit; cursor: pointer; text-align: left; }
.ai-usage__body { padding: 0 16px 16px; font-size: 13px; line-height: 1.7; overflow-wrap: anywhere; }
.ai-usage__body p { margin: 8px 0; }
.ai-usage__body ul { display: flex; gap: 8px 24px; flex-wrap: wrap; list-style: none; padding: 0; }
.ai-usage__note { opacity: .8; }
.ai-usage__refresh { color: inherit; background: transparent; border: 1px solid currentColor; border-radius: 6px; padding: 5px 12px; font: inherit; cursor: pointer; }
.ai-usage__refresh:disabled { opacity: .5; cursor: wait; }
.ai-usage button:focus-visible { outline: 2px solid currentColor; outline-offset: 3px; }
</style>
