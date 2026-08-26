<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NButton, NInput, NTag, useMessage } from 'naive-ui'
import {
  fetchClassRequests,
  reviewClassRequest,
  type ClassChangeRequest,
} from '../../api/classRequests'

const emit = defineEmits<{ reviewed: [] }>()

const message = useMessage()
const loading = ref(false)
const reviewingId = ref<number | null>(null)
const pending = ref<ClassChangeRequest[]>([])
const recent = ref<ClassChangeRequest[]>([])
const reviewNote = ref('')

async function load() {
  loading.value = true
  try {
    pending.value = await fetchClassRequests('pending')
    recent.value = (await fetchClassRequests()).filter((r) => r.status !== 'pending').slice(0, 12)
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载申请失败')
  } finally {
    loading.value = false
  }
}

function actionLabel(action: ClassChangeRequest['action']) {
  if (action === 'create') return '新建班级'
  if (action === 'delete') return '删除班级'
  return '修改班级'
}

const PAYLOAD_FIELD_LABELS: Record<string, string> = {
  name: '班级名称',
  grade_level: '年级',
  teacher_id: '负责教师',
  description: '备注说明',
}

function formatPayloadSummary(payload: Record<string, unknown> | null | undefined) {
  if (!payload || !Object.keys(payload).length) return []
  const lines: string[] = []
  const seen = new Set<string>()

  for (const key of ['name', 'grade_level', 'teacher_id', 'description']) {
    if (!(key in payload)) continue
    seen.add(key)
    const raw = payload[key]
    const label = PAYLOAD_FIELD_LABELS[key] ?? key
    if (raw == null || raw === '') {
      lines.push(`${label}：未设置`)
    } else {
      lines.push(`${label}：${String(raw)}`)
    }
  }

  for (const [key, raw] of Object.entries(payload)) {
    if (seen.has(key) || raw == null || raw === '') continue
    lines.push(`${PAYLOAD_FIELD_LABELS[key] ?? key}：${String(raw)}`)
  }

  return lines
}

async function review(row: ClassChangeRequest, approve: boolean) {
  reviewingId.value = row.id
  try {
    await reviewClassRequest(row.id, approve, reviewNote.value.trim() || undefined)
    message.success(approve ? '已通过申请' : '已驳回申请')
    reviewNote.value = ''
    await load()
    emit('reviewed')
  } catch (error) {
    message.error(error instanceof Error ? error.message : '审批失败')
  } finally {
    reviewingId.value = null
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <article class="gov-class-panel panel" aria-label="班级变更审批" data-tour="admin-class-approval">
    <header class="panel-head">
      <h2>班级变更审批</h2>
      <n-button quaternary size="small" class="gov-refresh-btn" :loading="loading" @click="load()">刷新</n-button>
    </header>
    <p class="governance-hint">
      教师提交的新建/删除班级申请在此处理；通过后系统自动执行。教师可直接编辑本班信息，无需审批。
    </p>

    <label class="gov-field">
      <span>审批备注，可选</span>
      <n-input v-model:value="reviewNote" placeholder="请输入审批备注" />
    </label>

    <div v-if="loading" class="governance-empty">加载中…</div>
    <div v-else-if="!pending.length" class="governance-empty">暂无待审申请</div>
    <ul v-else class="gov-request-list">
      <li v-for="row in pending" :key="row.id">
        <div>
          <strong>{{ actionLabel(row.action) }}</strong>
          <span v-if="row.class_name"> · {{ row.class_name }}</span>
          <p>申请人：{{ row.requester_name || `#${row.requester_id}` }}</p>
          <p v-if="row.reason">理由：{{ row.reason }}</p>
          <ul v-if="formatPayloadSummary(row.payload).length" class="gov-request-summary">
            <li v-for="line in formatPayloadSummary(row.payload)" :key="line">{{ line }}</li>
          </ul>
          <small>{{ row.created_at?.slice(0, 16).replace('T', ' ') }}</small>
        </div>
        <div class="gov-request-actions">
          <n-button
            type="primary"
            size="small"
            :loading="reviewingId === row.id"
            @click="review(row, true)"
          >
            通过
          </n-button>
          <n-button size="small" secondary :loading="reviewingId === row.id" @click="review(row, false)">
            驳回
          </n-button>
        </div>
      </li>
    </ul>

    <h3 class="gov-recent-title">近期已处理</h3>
    <div v-if="!recent.length" class="governance-empty">暂无记录</div>
    <ul v-else class="gov-request-list gov-request-list--compact">
      <li v-for="row in recent" :key="row.id">
        <div>
          <strong>{{ actionLabel(row.action) }}</strong>
          <span v-if="row.class_name"> · {{ row.class_name }}</span>
          <small>{{ row.reviewed_at?.slice(0, 16).replace('T', ' ') }}</small>
        </div>
        <n-tag size="small" :type="row.status === 'approved' ? 'success' : 'error'">
          {{ row.status === 'approved' ? '已通过' : '已驳回' }}
        </n-tag>
      </li>
    </ul>
  </article>
</template>

<style scoped>
.gov-class-panel {
  grid-column: 1 / -1;
}

.gov-request-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.75rem;
}

.gov-request-list li {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.85rem 0;
  border-bottom: 1px solid rgba(167, 139, 250, 0.12);
}

.gov-request-list strong {
  color: #f5f3ff;
}

.gov-request-list p {
  margin: 0.3rem 0 0;
  color: rgba(221, 214, 254, 0.72);
  font-size: 0.84rem;
}

.gov-request-list small {
  display: block;
  margin-top: 0.35rem;
  color: rgba(196, 181, 253, 0.5);
  font-size: 0.75rem;
}

.gov-request-summary {
  margin: 0.45rem 0 0;
  padding: 0.55rem 0.75rem;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.22);
  list-style: none;
  display: grid;
  gap: 0.25rem;
}

.gov-request-summary li {
  color: rgba(221, 214, 254, 0.85);
  font-size: 0.82rem;
  line-height: 1.45;
}

.gov-request-actions {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  flex-shrink: 0;
}

.gov-recent-title {
  margin: 1.25rem 0 0.65rem;
  color: rgba(221, 214, 254, 0.85);
  font-size: 0.92rem;
  font-weight: 650;
}

.gov-request-list--compact li {
  padding: 0.55rem 0;
}
</style>
