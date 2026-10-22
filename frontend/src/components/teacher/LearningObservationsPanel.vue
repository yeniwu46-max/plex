<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { fetchLearningObservations, type LearningObservations } from '../../api/learningObservations'

const props = defineProps<{ classId: number }>()
const auth = useAuthStore()
const open = ref(false)
const days = ref<7 | 14 | 30>(14)
const loading = ref(false)
const error = ref('')
const observations = ref<LearningObservations | null>(null)
let version = 0
const stateLabels: Record<string, string> = { complete: '生成完成', processing: '处理中', failed: '失败', cancelled: '已取消', expired: '租约已过期' }
const modelLabels: Record<string, string> = { succeeded: '模型成功返回', failed: '模型调用失败', interrupted: '模型传输中断' }
const latencyRows = computed(() => observations.value ? [
  { label: '生成完成请求（含重试等待）', ...observations.value.latency_ms.completed_request },
  { label: '已结束服务端尝试（含失败）', ...observations.value.latency_ms.finished_attempt },
  { label: '已结束模型调用（含失败）', ...observations.value.latency_ms.finished_model_call },
  ...Object.entries(observations.value.latency_ms.model_by_status).map(([key, value]) => ({ label: modelLabels[key] || key, ...value })),
] : [])
const milliseconds = (value: number | null) => value === null ? '暂无样本' : `${value.toLocaleString()} ms`

async function refresh() {
  const run = ++version
  observations.value = null
  error.value = ''
  loading.value = false
  if (!auth.profile?.id || auth.profile.role !== 'teacher' || !props.classId) return
  loading.value = true
  try {
    const result = await fetchLearningObservations(props.classId, days.value)
    if (run === version) observations.value = result
  } catch (err) {
    if (run === version) error.value = (err as Error).message || '暂时无法读取学习观察'
  } finally {
    if (run === version) loading.value = false
  }
}
function toggle() {
  open.value = !open.value
  if (open.value) void refresh()
}
watch(() => [auth.profile?.id, auth.profile?.role, props.classId, days.value], () => {
  version++
  observations.value = null
  loading.value = false
  error.value = ''
  if (open.value) void refresh()
}, { flush: 'sync' })
onBeforeUnmount(() => { version++ })
</script>

<template>
  <section class="learning-observations">
    <button class="learning-observations__toggle" type="button" :aria-expanded="open" @click="toggle">
      <span>当前班级 · 学习与辅导观察</span><span aria-hidden="true">{{ open ? '−' : '+' }}</span>
    </button>
    <div v-if="open" class="learning-observations__body" :aria-busy="loading">
      <div class="learning-observations__controls">
        <label>统计范围 <select v-model="days"><option :value="7">最近 7 天</option><option :value="14">最近 14 天</option><option :value="30">最近 30 天</option></select></label>
        <button type="button" :disabled="loading" @click="refresh">{{ error ? '重试' : '刷新观察' }}</button>
      </div>
      <p v-if="loading" role="status">正在读取班级观察…</p>
      <p v-if="error" role="alert">{{ error }}</p>
      <template v-if="observations">
        <p>截至 {{ new Date(observations.window.as_of).toLocaleString() }}，当前有效学生 {{ observations.current_students }} 人，其中有纳入统计的辅导请求 {{ observations.tutoring_students }} 人。</p>
        <p v-if="observations.flow.requests === 0">本窗口暂无符合统计范围的辅导记录。旧记录和自由聊天不回填，不能据此判断学生没有使用小 E。</p>
        <dl class="learning-observations__metrics">
          <div><dt>已接纳请求</dt><dd>{{ observations.flow.requests }}</dd></div>
          <div><dt>可计数帮助</dt><dd>{{ observations.flow.published_help }}</dd></div>
          <div><dt>页面已回执展示</dt><dd>{{ observations.flow.display_confirmed }}</dd></div>
          <div><dt>尚无展示回执</dt><dd>{{ observations.flow.not_display_confirmed }}</dd></div>
        </dl>
        <ul class="learning-observations__states"><li v-for="(label, key) in stateLabels" :key="key">{{ label }} {{ observations.flow.states[key] || 0 }}</li></ul>
        <p>可计数帮助是服务端允许记录的辅导输出，不包括补充上下文提示或一般会话。展示回执不证明学生阅读、理解或获得了有效帮助。</p>
        <h3>七天后续练习观察</h3>
        <p>以每位学生、每个知识点在本窗口的首次帮助展示为一组，共 {{ observations.followup.exposures }} 组。仅匹配七天内另一题的首次、平台内未展示该题提示的正式判题。</p>
        <dl class="learning-observations__metrics">
          <div><dt>首次判题通过</dt><dd>{{ observations.followup.first_correct }}</dd></div>
          <div><dt>首次判题未通过</dt><dd>{{ observations.followup.first_incorrect }}</dd></div>
          <div><dt>尚在七天观察期</dt><dd>{{ observations.followup.window_open }}</dd></div>
          <div><dt>到期无后续记录</dt><dd>{{ observations.followup.window_closed_without_observation }}</dd></div>
        </dl>
        <p>无后续记录不计为失败；平台外帮助无法排除。这是时间上的关联观察，不能作为学习提升的因果证据。</p>
        <details><summary>本窗口正式判题记录</summary>
          <p>共 {{ observations.formal_practice.total }} 条。未展示该题提示 {{ observations.formal_practice.independent }} 条，其中通过 {{ observations.formal_practice.independent_correct }} 条；已展示提示 {{ observations.formal_practice.assisted }} 条，其中通过 {{ observations.formal_practice.assisted_correct }} 条。不含浏览器自测或复习自评。</p>
        </details>
        <h3>耗时与样本范围</h3>
        <div class="learning-observations__table" tabindex="0" role="region" aria-label="辅导耗时统计，可横向滚动">
          <table><thead><tr><th scope="col">口径</th><th scope="col">有效样本</th><th scope="col">耗时缺失</th><th scope="col">P50</th><th scope="col">P95</th></tr></thead>
            <tbody><tr v-for="row in latencyRows" :key="row.label"><th scope="row">{{ row.label }}</th><td>{{ row.samples }}</td><td>{{ row.missing }}</td><td>{{ milliseconds(row.p50) }}</td><td>{{ milliseconds(row.p95) }}</td></tr></tbody>
          </table>
        </div>
        <p>共 {{ observations.latency_ms.attempts }} 次服务端尝试、{{ observations.latency_ms.model_calls }} 次模型调用；其中 {{ observations.latency_ms.unfinished_attempts }} 次尝试、{{ observations.latency_ms.unfinished_model_calls }} 次调用尚无结束记录，未计入耗时分位数。</p>
        <p>P50、P95 是本次已有样本的中位与第 95 百分位耗时，不是性能保证，也不是首字或浏览器端到端延迟。</p>
        <details><summary>查看统计边界</summary><ul><li v-for="note in observations.limitations" :key="note">{{ note }}</li></ul></details>
      </template>
    </div>
  </section>
</template>

<style scoped>
.learning-observations { color: var(--plex-text); background: var(--plex-bg-card); border: 1px solid var(--plex-border, #526378); border-radius: 12px; min-width: 0; }
.learning-observations__toggle { width: 100%; display: flex; justify-content: space-between; gap: 12px; padding: 14px 16px; border: 0; text-align: left; }
.learning-observations button, .learning-observations select { font: inherit; color: inherit; background: var(--plex-bg-card); cursor: pointer; }
.learning-observations__body { padding: 0 16px 16px; font-size: 13px; line-height: 1.7; overflow-wrap: anywhere; }
.learning-observations__controls { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; }
.learning-observations__controls button, .learning-observations select { border: 1px solid var(--plex-border, #526378); border-radius: 6px; padding: 6px 10px; }
.learning-observations button:disabled { opacity: .5; cursor: wait; }
.learning-observations__metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.learning-observations__metrics div { padding: 12px; border: 1px solid var(--plex-border, #526378); border-radius: 8px; }
.learning-observations__metrics dd { margin: 4px 0 0; font-size: 24px; font-weight: 700; }
.learning-observations__states { display: flex; flex-wrap: wrap; gap: 8px 20px; list-style: none; padding: 0; }
.learning-observations h3 { font-size: 15px; margin: 24px 0 8px; }
.learning-observations__table { overflow-x: auto; }
.learning-observations table { border-collapse: collapse; width: 100%; min-width: 560px; text-align: left; }
.learning-observations th, .learning-observations td { padding: 8px; border-bottom: 1px solid var(--plex-border, #526378); }
.learning-observations :is(button, select, summary, [tabindex]):focus-visible { outline: 2px solid currentColor; outline-offset: 3px; }
.learning-observations summary { cursor: pointer; }
@media (max-width: 767px) { .learning-observations__metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
