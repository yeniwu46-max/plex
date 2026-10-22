<script setup lang="ts">
import { computed, onActivated, onDeactivated, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NIcon, NModal, NPagination } from 'naive-ui'
import { TrophyOutline, FlaskOutline } from '@vicons/ionicons5'
import { useAuthStore } from '../../stores/auth'
import { fetchStudentTrialStats, fetchStudentTrialRecords, type StudentTrialStatsResult, type StudentTrialRecord } from '../../api/studentTrials'

const router = useRouter(), auth = useAuthStore()
const stats = ref<StudentTrialStatsResult | null>(null), statsBusy = ref(false), statsError = ref('')
const show = ref(false), view = ref<'completed' | 'active' | 'average' | 'all' | 'records'>('records')
const page = ref(1), rows = ref<StudentTrialRecord[]>([]), total = ref(0), busy = ref(false), error = ref('')
let active = true, summaryEpoch = 0, recordsEpoch = 0
const titles = { completed: '已完成的试炼', active: '进行中的试炼', average: '平均成绩', all: '累计参与', records: '战绩记录' }
const title = computed(() => titles[view.value])
const metrics = computed(() => [
  { key: 'completed' as const, label: '已完成', value: stats.value?.summary.completed_count },
  { key: 'active' as const, label: '进行中', value: stats.value?.summary.active_count },
  { key: 'average' as const, label: '均分', value: stats.value?.summary.completed_count ? stats.value.summary.avg_score : '暂无' },
  { key: 'all' as const, label: '累计参与', value: stats.value?.summary.total_participations },
])
async function loadSummary() {
  if (!active || !auth.profile?.id || statsBusy.value) return
  const ticket = ++summaryEpoch
  statsBusy.value = true; statsError.value = ''
  try { const result = await fetchStudentTrialStats(); if (active && ticket === summaryEpoch) stats.value = result }
  catch (e) { if (active && ticket === summaryEpoch) statsError.value = e instanceof Error ? e.message : '战绩加载失败' }
  finally { if (ticket === summaryEpoch) statsBusy.value = false }
}
async function loadRecords() {
  if (!active || !auth.profile?.id || !show.value) return
  const ticket = ++recordsEpoch
  busy.value = true; error.value = ''; rows.value = []
  const status = view.value === 'active' ? 'active' : view.value === 'all' ? 'all' : 'completed'
  try { const result = await fetchStudentTrialRecords(status, page.value); if (active && ticket === recordsEpoch) { rows.value = result.items; total.value = result.total } }
  catch (e) { if (active && ticket === recordsEpoch) error.value = e instanceof Error ? e.message : '战绩明细加载失败' }
  finally { if (ticket === recordsEpoch) busy.value = false }
}
function open(kind: typeof view.value) { view.value = kind; page.value = 1; show.value = true; void loadSummary() }
watch([show, page, view], () => { if (show.value) void loadRecords(); else { ++recordsEpoch; busy.value = false } })
function stop() { active = false; ++summaryEpoch; ++recordsEpoch; statsBusy.value = false; busy.value = false; show.value = false }
function resume() { active = true; void loadSummary() }
watch(() => auth.profile?.id, () => { stop(); stats.value = null; rows.value = []; total.value = 0; resume() })
onMounted(resume); onActivated(resume); onDeactivated(stop); onBeforeUnmount(stop)
const formatDate = (value: string | null) => value ? new Date(value).toLocaleString('zh-CN') : '暂无记录'
</script>

<template>
  <section class="trial-overview" aria-label="班级试炼战绩">
    <div class="trial-overview__metrics">
      <button v-for="metric in metrics" :key="metric.key" type="button" class="trial-metric" @click="open(metric.key)">
        <span>{{ metric.label }}</span><strong>{{ statsBusy ? '…' : statsError ? '—' : metric.value ?? '—' }}</strong>
      </button>
    </div>
    <div class="trial-overview__actions">
      <n-button class="plex-action-button" @click="open('records')"><template #icon><n-icon :component="TrophyOutline" /></template>战绩记录</n-button>
      <n-button class="plex-action-button" @click="router.push('/student/trials/counterexamples')"><template #icon><n-icon :component="FlaskOutline" /></template>反例挑战</n-button>
    </div>
    <p v-if="statsError" role="alert">{{ statsError }} <n-button text @click="loadSummary">重试</n-button></p>
  </section>
  <n-modal v-model:show="show" preset="card" :title="title" class="plex-reading-modal trial-record-modal" :style="{ width: 'min(680px,94vw)', maxHeight: '76dvh' }">
    <p class="trial-record-scope">班级试炼 · {{ view === 'average' ? '均分为全部已完成试炼成绩的算术平均值，取整显示。' : '仅统计本人参与的教师发布试炼。' }}</p>
    <p v-if="view === 'average' && stats && !statsError" class="trial-record-average">{{ stats.summary.completed_count ? `${stats.summary.avg_score} 分 · 共 ${stats.summary.completed_count} 场` : '暂无已完成的试炼' }}</p>
    <p v-if="busy" role="status">正在读取战绩…</p>
    <p v-else-if="error" role="alert">{{ error }} <n-button @click="loadRecords">重试</n-button></p>
    <p v-else-if="!rows.length">暂无相关试炼记录</p>
    <ul v-else class="trial-record-list">
      <li v-for="row in rows" :key="row.id"><div><strong>{{ row.title }}</strong><small>{{ row.status === 'completed' ? '完成于' : '参与于' }} {{ formatDate(row.completed_at || row.joined_at) }}</small></div><span>{{ row.status === 'completed' ? `${row.score ?? '待判定'}${row.score === null ? '' : ' 分'}` : row.status === 'joined' ? '进行中' : '已退出' }}</span></li>
    </ul>
    <template #footer><n-pagination v-model:page="page" :item-count="total" :page-size="10" :disabled="busy" :page-slot="5" /></template>
  </n-modal>
</template>

<style scoped>
.trial-overview{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:20px;color:var(--plex-text)}
.trial-overview__metrics{display:grid;grid-template-columns:repeat(4,minmax(88px,1fr));flex:1;gap:10px}
.trial-metric{display:flex;align-items:center;justify-content:space-between;gap:12px;min-width:0;min-height:52px;padding:10px 14px;color:inherit;background:var(--plex-bg-card);border:1px solid var(--plex-border);border-radius:12px;cursor:pointer}
.trial-metric span{font-size:12px;color:var(--plex-text-muted);white-space:nowrap}.trial-metric strong{font-size:21px;white-space:nowrap}
.trial-metric:hover{border-color:var(--plex-primary,#55eee9)}.trial-metric:focus-visible{outline:2px solid var(--plex-primary,#55eee9);outline-offset:3px}
.trial-overview__actions{display:flex;gap:10px;flex-wrap:wrap}.trial-overview>p{flex-basis:100%;margin:0}
.trial-record-scope{color:var(--plex-text-muted);font-size:13px;line-height:1.7}.trial-record-average{font-size:20px;font-weight:650}.trial-record-list{padding:0;margin:0;list-style:none}
.trial-record-list li{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:16px 0;border-bottom:1px solid var(--plex-border)}.trial-record-list li>div{min-width:0}.trial-record-list strong{overflow-wrap:anywhere}.trial-record-list small{display:block;margin-top:6px;color:var(--plex-text-muted)}.trial-record-list li>span{white-space:nowrap;color:var(--plex-text);font-weight:650}
:global(html[data-plex-style='comic'][data-plex-persona='student'] .trial-metric){border:2px solid var(--comic-line);box-shadow:3px 3px 0 var(--comic-ink);border-radius:8px 14px 8px 14px;background:var(--comic-panel)}
@media(max-width:700px){.trial-overview__metrics{flex-basis:100%;grid-template-columns:repeat(2,minmax(0,1fr))}.trial-overview__actions{margin-left:auto}.trial-metric{padding:10px 14px}}
</style>
