<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NButton, NModal, NSpin, NTag } from 'naive-ui'
import {
  fetchStudentTrialHistory,
  type StudentTrialHistoryResult,
} from '../../api/teacherTrials'

export interface ExplorerProfilePayload {
  id: number
  username?: string | null
  real_name?: string | null
  class_name?: string | null
  level?: number | null
  total_points?: number | null
  status?: string | null
  email?: string | null
  phone?: string | null
  created_at?: string | null
}

const props = defineProps<{
  show: boolean
  student: ExplorerProfilePayload | null
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
}>()

const visible = computed({
  get: () => props.show,
  set: (value: boolean) => emit('update:show', value),
})

const history = ref<StudentTrialHistoryResult | null>(null)
const loading = ref(false)

function statusLabel(status?: string | null) {
  if (!status) return '在读'
  return ({ active: '在读', frozen: '冻结', deleted: '已删除' } as Record<string, string>)[status] ?? status
}

function statusTagType(status?: string | null): 'success' | 'warning' | 'error' | 'default' {
  if (status === 'active') return 'success'
  if (status === 'frozen') return 'warning'
  if (status === 'deleted') return 'error'
  return 'default'
}

function participationLabel(status: string) {
  return ({ joined: '进行中', completed: '已完成', abandoned: '已放弃' } as Record<string, string>)[status] ?? status
}

function formatDate(value?: string | null) {
  if (!value) return '-'
  return value.slice(0, 10)
}

async function loadHistory(studentId: number) {
  loading.value = true
  history.value = null
  try {
    history.value = await fetchStudentTrialHistory(studentId)
  } catch {
    history.value = null
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.show, props.student?.id] as const,
  ([open, studentId]) => {
    if (open && studentId) void loadHistory(studentId)
  },
)
</script>

<template>
  <n-modal
    v-model:show="visible"
    preset="card"
    :title="student?.real_name || student?.username || 'Explorer 资料'"
    class="explorer-profile-card"
    :bordered="false"
    :z-index="5300"
    style="width: min(420px, calc(100vw - 32px))"
  >
    <div v-if="student" class="profile-card">
      <div class="profile-card__identity">
        <div class="profile-card__avatar" aria-hidden="true">
          {{ (student.real_name || student.username || '?').slice(0, 1) }}
        </div>
        <div>
          <strong>{{ student.real_name || '-' }}</strong>
          <p>@{{ student.username || student.id }}</p>
        </div>
      </div>
      <dl class="profile-card__meta">
        <div><dt>班级</dt><dd>{{ student.class_name || '未分班' }}</dd></div>
        <div><dt>等级</dt><dd>Lv.{{ student.level ?? '—' }}</dd></div>
        <div><dt>积分</dt><dd>{{ student.total_points ?? '—' }}</dd></div>
        <div>
          <dt>状态</dt>
          <dd>
            <n-tag round size="small" :type="statusTagType(student.status)">
              {{ statusLabel(student.status) }}
            </n-tag>
          </dd>
        </div>
        <div v-if="student.email"><dt>邮箱</dt><dd>{{ student.email }}</dd></div>
        <div v-if="student.phone"><dt>电话</dt><dd>{{ student.phone }}</dd></div>
        <div v-if="student.created_at"><dt>加入</dt><dd>{{ formatDate(student.created_at) }}</dd></div>
      </dl>

      <section class="profile-card__practice">
        <h3>最近练习</h3>
        <n-spin :show="loading">
          <template v-if="history">
            <p class="profile-card__practice-summary">
              共 {{ history.summary.total }} 次试炼 ·
              完成 {{ history.summary.completed }} ·
              平均分 {{ history.summary.avg_score }}
            </p>
            <ul v-if="history.participations.length" class="profile-card__practice-list">
              <li v-for="row in history.participations.slice(0, 5)" :key="row.id">
                <strong>{{ row.trial?.title || `试炼 #${row.trial_id}` }}</strong>
                <span>{{ participationLabel(row.status) }} · 得分 {{ row.score }}</span>
              </li>
            </ul>
            <p v-else class="profile-card__empty">暂无试炼练习记录</p>
          </template>
          <p v-else-if="!loading" class="profile-card__empty">练习数据暂不可用</p>
        </n-spin>
      </section>

      <footer class="profile-card__actions">
        <n-button size="small" @click="visible = false">关闭</n-button>
      </footer>
    </div>
  </n-modal>
</template>

<style scoped>
.profile-card__identity {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  margin-bottom: 1rem;
}

.profile-card__avatar {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(251, 146, 60, 0.35), rgba(15, 23, 42, 0.9));
  border: 1px solid rgba(251, 146, 60, 0.35);
  color: #fed7aa;
  font-weight: 700;
}

.profile-card__identity strong {
  display: block;
  color: #fff7ed;
  font-size: 1.05rem;
}

.profile-card__identity p {
  margin: 0.15rem 0 0;
  color: rgba(203, 213, 225, 0.65);
  font-size: 0.82rem;
}

.profile-card__meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.55rem;
  margin: 0 0 1rem;
}

.profile-card__meta div {
  padding: 0.45rem 0.55rem;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.45);
  border: 1px solid rgba(251, 146, 60, 0.12);
}

.profile-card__meta dt {
  margin: 0 0 0.2rem;
  color: rgba(253, 186, 116, 0.72);
  font-size: 0.72rem;
}

.profile-card__meta dd {
  margin: 0;
  color: #fff7ed;
  font-size: 0.88rem;
  word-break: break-all;
}

.profile-card__practice h3 {
  margin: 0 0 0.55rem;
  color: #fed7aa;
  font-size: 0.92rem;
}

.profile-card__practice-summary {
  margin: 0 0 0.65rem;
  color: rgba(203, 213, 225, 0.7);
  font-size: 0.8rem;
}

.profile-card__practice-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.45rem;
}

.profile-card__practice-list li {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  padding: 0.5rem 0.6rem;
  border-radius: 10px;
  background: rgba(2, 8, 16, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.profile-card__practice-list strong {
  color: #fff7ed;
  font-size: 0.86rem;
}

.profile-card__practice-list span {
  color: rgba(203, 213, 225, 0.62);
  font-size: 0.76rem;
}

.profile-card__empty {
  margin: 0;
  color: rgba(148, 163, 184, 0.72);
  font-size: 0.84rem;
}

.profile-card__actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 1rem;
}
</style>

<style>
.explorer-profile-card.n-card {
  background: rgba(8, 14, 22, 0.98) !important;
  border: 1px solid rgba(251, 146, 60, 0.22) !important;
}

.explorer-profile-card .n-card-header__main {
  color: #fff7ed !important;
}
</style>
