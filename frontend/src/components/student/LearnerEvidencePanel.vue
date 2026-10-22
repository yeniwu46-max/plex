<script setup lang="ts">
import { createRequestId } from '../../utils/browserCrypto'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { NButton, NCard, NTag, NAlert, NInput } from 'naive-ui'
import { useAuthStore } from '../../stores/auth'
import { fetchLearnerState, fetchLearningEvidence, reviewMisconception, type LearnerStateSnapshot,
  type LearnerMisconception, type LearningChange, type MisconceptionReviewAction } from '../../api/learnerState'

const props = defineProps<{ studentId?: number }>()
const auth = useAuthStore()
const state = ref<LearnerStateSnapshot | null>(null)
const loading = ref(false)
const error = ref('')
const reviewing = ref<number | null>(null)
const notes = ref<Record<number, string>>({})
const requests = new Map<string, string>()
const history = ref<LearningChange[]>([])
const historyReady = ref(false)
const historyLoading = ref(false)
const historyError = ref('')
const nextCursor = ref<string | null>(null)
const latestVersion = ref(0)
const changes = computed(() => historyReady.value ? history.value : state.value?.changes || [])
let epoch = 0
const statusNames = { candidate: '待核对', confirmed: '教师已确认', mitigated: '已缓解 · 继续观察', dismissed: '教师已驳回' }
const concepts = computed(() => state.value?.concepts.filter(c => c.independent_count + c.assisted_count > 0) ?? [])
const names: Record<string, string> = {
  syntax: '基础语法', var: '变量', cond: '条件判断', loop: '循环', range: '循环范围',
  list: '列表', func: '函数', recursion: '递归', dict: '字典', algo: '算法', unclassified: '未分类知识点',
  'loop-for': 'for 与 range', 'func-recursion': '递归',
}
function conceptLabel(id: string | null) {
  return state.value?.concepts.find(c => c.concept_id === id)?.label || names[id || ''] || id
}
function date(value: string) {
  return new Date(value.endsWith('Z') ? value : value + 'Z').toLocaleString('zh-CN', { hour12: false })
}
function allowed() {
  return !!auth.profile?.id && auth.profile.role === (props.studentId === undefined ? 'student' : 'teacher')
}
function adopt(value: LearnerStateSnapshot | null) {
  state.value = value
  history.value = []
  historyReady.value = false
  historyLoading.value = false
  historyError.value = ''
  nextCursor.value = null
  latestVersion.value = value?.state_version || 0
}
async function readHistory(run: number, reset: boolean) {
  if (!state.value || run !== epoch || !allowed()) return
  const snapshotVersion = state.value.state_version
  const cursor = reset ? null : nextCursor.value
  historyLoading.value = true
  historyError.value = ''
  try {
    const page = await fetchLearningEvidence(props.studentId, cursor ? { cursor } : { snapshot_version: snapshotVersion })
    if (run !== epoch) return
    if (page.snapshot_version !== snapshotVersion) throw new Error('学习证据版本已变化，请刷新后重新查看。')
    const existing = reset ? [] : history.value
    const ids = new Set(existing.map(item => item.event_id))
    history.value = [...existing, ...page.items.filter(item => !ids.has(item.event_id))]
    nextCursor.value = page.next_cursor
    latestVersion.value = page.latest_version
    historyReady.value = true
  } catch (e) {
    if (run === epoch) historyError.value = (e as Error).message || '历史记录加载失败，请重试；翻页凭据过期时请刷新证据。'
  } finally {
    if (run === epoch) historyLoading.value = false
  }
}
async function load() {
  if (loading.value || reviewing.value !== null || !allowed()) return
  const run = ++epoch
  adopt(null)
  loading.value = true
  error.value = ''
  try {
    const result = await fetchLearnerState(props.studentId)
    if (run !== epoch) return
    adopt(result)
    await readHistory(run, true)
  } catch (e) {
    if (run === epoch) error.value = (e as Error).message || '学习证据加载失败，请重试'
  } finally {
    if (run === epoch) loading.value = false
  }
}
async function loadMore() {
  if (historyLoading.value || loading.value || reviewing.value !== null || !state.value) return
  if (historyReady.value && !nextCursor.value) return
  await readHistory(epoch, !historyReady.value)
}
async function review(item: LearnerMisconception, action: MisconceptionReviewAction) {
  if (props.studentId === undefined || reviewing.value !== null || loading.value || historyLoading.value || !allowed()) return
  const note = notes.value[item.id]?.trim() || ''
  if (!note) { error.value = '请先填写核对说明，再保存审核结果。'; return }
  const key = JSON.stringify([props.studentId, item.id, item.revision, action, note])
  const requestId = requests.get(key) || createRequestId()
  requests.set(key, requestId)
  const run = ++epoch
  reviewing.value = item.id
  error.value = ''
  try {
    const result = await reviewMisconception(props.studentId, item.id, {
      action, expected_revision: item.revision, request_id: requestId, note,
    })
    if (run !== epoch) return
    adopt(result)
    notes.value[item.id] = ''
    await readHistory(run, true)
  } catch (e) {
    if (run === epoch) error.value = (e as Error).message || '审核未保存，请重试或刷新证据。'
  } finally {
    if (run === epoch) reviewing.value = null
  }
}
watch(() => [auth.profile?.id, auth.profile?.role, props.studentId], () => {
  epoch++
  adopt(null)
  loading.value = false
  reviewing.value = null
  error.value = ''
  notes.value = {}
  requests.clear()
  void load()
}, { immediate: true, flush: 'sync' })
onBeforeUnmount(() => { epoch++; requests.clear() })
</script>

<template>
  <n-card class="learner-evidence" title="最近学习变化" aria-label="最近学习变化">
    <template #header-extra><n-button size="small" :loading="loading" :disabled="reviewing !== null" @click="load">刷新证据</n-button></template>
    <n-alert v-if="error" type="error" :show-icon="false" role="alert">{{ error }}</n-alert>
    <template v-if="state">
      <div class="evidence-heading"><n-tag size="small">学习状态 v{{ state.state_version }}</n-tag><span>Python · 服务端学习证据</span></div>
      <p class="evidence-note">{{ state.estimate_disclaimer }}</p>
      <n-alert v-if="state.pending_events || state.failed_events" type="info" :show-icon="false" class="evidence-pending">
        <span v-if="state.pending_events">{{ state.pending_events }} 条新证据正在整理，稍后刷新查看。</span>
        <span v-if="state.failed_events">有证据暂未处理成功，当前展示上次已确认状态。</span>
      </n-alert>
      <div v-if="concepts.length" class="evidence-concepts">
        <article v-for="concept in concepts" :key="concept.concept_id" class="evidence-concept">
          <strong>{{ conceptLabel(concept.concept_id) }}</strong>
          <span>独立通过 {{ concept.independent_success }}/{{ concept.independent_count }} · 提示后通过 {{ concept.assisted_success }}/{{ concept.assisted_count }}</span>
          <span v-if="concept.counterexample_count">反例实践 {{ concept.counterexample_success }}/{{ concept.counterexample_count }} · 单独记录边界分析证据</span>
          <small v-if="concept.counterexample_review_due_at">独立迁移练习：{{ date(concept.counterexample_review_due_at) }}</small>
          <small>{{ concept.stale ? '正式作答证据已超过 30 天，建议复核' : '能力估计仅依据正式作答；反例实践、自测与问卷不计成绩' }}</small>
        </article>
      </div>
      <p v-else class="evidence-empty">能力尚待了解，完成正式练习后会在这里积累证据。</p>
      <section v-if="state.misconceptions?.length" class="misconceptions" aria-label="待核对的理解与证据">
        <h3>理解核对</h3>
        <article v-for="item in state.misconceptions" :key="item.id" class="misconception">
          <div class="evidence-heading"><strong>{{ item.label }}</strong><n-tag size="small"
            :type="item.status === 'confirmed' ? 'warning' : item.status === 'mitigated' ? 'success' : 'default'">{{ statusNames[item.status] }}</n-tag></div>
          <p>{{ item.explanation }}</p>
          <ul class="signal-evidence"><li v-for="evidence in item.evidence" :key="evidence.event_id">
            {{ evidence.observation }}<small>题目 #{{ evidence.question_id }} · 证据 #{{ evidence.event_id }} · {{ date(evidence.occurred_at) }}</small>
          </li></ul>
          <p v-if="item.review_note" class="review-note">教师核对：{{ item.review_note }}</p>
          <template v-if="studentId !== undefined">
            <label :for="`review-note-${item.id}`" class="review-label">核对说明（最多 300 字）</label>
            <n-input :id="`review-note-${item.id}`" v-model:value="notes[item.id]" type="textarea" :maxlength="300"
              show-count :autosize="{ minRows: 2, maxRows: 4 }" placeholder="结合代码意图和失败输入，说明确认或驳回的依据"
              :disabled="reviewing !== null" :input-props="{ 'aria-label': `${item.label}的核对说明` }" />
            <div class="review-actions">
              <n-button size="small" :loading="reviewing === item.id" :disabled="reviewing !== null || loading || historyLoading || !notes[item.id]?.trim()" @click="review(item, 'confirm')">确认理解偏差</n-button>
              <n-button size="small" :disabled="reviewing !== null || loading || historyLoading || !notes[item.id]?.trim()" @click="review(item, 'dismiss')">驳回候选</n-button>
              <n-button v-if="item.status !== 'candidate'" size="small" :disabled="reviewing !== null || loading || historyLoading || !notes[item.id]?.trim()" @click="review(item, 'reopen')">重新观察</n-button>
            </div>
          </template>
        </article>
      </section>
      <ol v-if="changes.length" class="evidence-timeline">
        <li v-for="change in changes" :key="change.event_id">
          <div><strong>{{ change.reason }}</strong><span v-if="change.question_title || change.concept_id">{{ change.question_title || conceptLabel(change.concept_id) }}</span></div>
          <small><time :datetime="change.occurred_at + 'Z'">{{ date(change.occurred_at) }}</time> · 证据 #{{ change.event_id }} · v{{ change.version }}</small>
        </li>
      </ol>
      <section class="evidence-history" aria-label="历史学习证据" :aria-busy="historyLoading">
        <p v-if="latestVersion > state.state_version" role="status">已有更新的学习证据，点击“刷新证据”可读取新版本。</p>
        <n-alert v-if="historyError" type="error" :show-icon="false" role="alert">{{ historyError }}</n-alert>
        <p v-if="historyReady">已显示 {{ changes.length }} 条已处理证据，固定于学习状态 v{{ state.state_version }}。<span v-if="!nextCursor">此版本的记录已全部显示。</span></p>
        <n-button v-if="!historyReady || nextCursor" size="small" :loading="historyLoading"
          :disabled="loading || historyLoading || reviewing !== null" @click="loadMore">
          {{ historyError ? '重试历史记录' : historyReady ? '查看更早证据' : '读取历史记录' }}
        </n-button>
      </section>
    </template>
    <p v-else-if="loading" role="status">正在读取学习证据…</p>
  </n-card>
</template>

<style scoped>
.learner-evidence { margin: 20px 0; min-width: 0; }
.evidence-heading { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.evidence-note { opacity: .75; line-height: 1.7; font-size: 13px; }
.evidence-pending { margin-bottom: 16px; }
.evidence-concepts { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(240px, 100%), 1fr)); gap: 12px; }
.evidence-concept { display: flex; flex-direction: column; gap: 8px; padding: 16px; border: 1px solid currentColor; border-radius: 10px; }
.evidence-concept small { opacity: .7; }
.evidence-empty { padding: 24px 0; text-align: center; line-height: 1.7; }
.evidence-timeline { padding: 0; margin: 20px 0 0; list-style: none; }
.evidence-timeline li { padding: 13px 0; border-top: 1px solid color-mix(in srgb, currentColor 18%, transparent); overflow-wrap: anywhere; }
.evidence-timeline li div { display: flex; flex-wrap: wrap; gap: 8px 16px; margin-bottom: 4px; }
.evidence-timeline small { opacity: .7; }
.evidence-history { margin-top: 16px; line-height: 1.7; overflow-wrap: anywhere; }
.misconceptions { margin-top: 24px; }
.misconceptions h3 { font-size: 16px; }
.misconception { margin-top: 12px; padding: 16px; border: 1px solid color-mix(in srgb, currentColor 25%, transparent); border-radius: 10px; overflow-wrap: anywhere; }
.misconception p { line-height: 1.7; }
.signal-evidence { padding-left: 20px; }
.signal-evidence li { line-height: 1.7; margin-bottom: 10px; }
.signal-evidence small { display: block; opacity: .75; }
.review-note { border-left: 3px solid currentColor; padding-left: 12px; }
.review-label { display: block; margin: 12px 0 8px; }
.review-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
:global(html[data-plex-style="comic"] .learner-evidence) { border-width: 2px; box-shadow: 3px 3px 0 color-mix(in srgb, currentColor 25%, transparent); }
:global(html[data-plex-style="comic"] .learner-evidence .evidence-concept) { border-width: 2px; border-radius: 4px 12px 4px 12px; }
</style>
