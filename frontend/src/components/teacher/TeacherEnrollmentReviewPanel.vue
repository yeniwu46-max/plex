<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NButton, NInput, NSelect, NTag, useMessage, type SelectOption } from 'naive-ui'
import {
  fetchEnrollmentRequests,
  reviewEnrollmentRequest,
  type ClassEnrollmentRequest,
} from '../../api/classEnrollments'
import { fetchClasses, type ClassSummary } from '../../api/studentManagement'

const props = defineProps<{
  defaultClassId?: number | null
}>()

const emit = defineEmits<{
  changed: []
}>()

const message = useMessage()
const classes = ref<ClassSummary[]>([])
const requests = ref<ClassEnrollmentRequest[]>([])
const loading = ref(false)
const reviewingId = ref<number | null>(null)
const filterClassId = ref<number | null>(props.defaultClassId ?? null)
const reviewNote = ref('')

const classOptions = computed<SelectOption[]>(() =>
  classes.value.map((c) => ({ label: c.name, value: c.id })),
)

const pendingRequests = computed(() => requests.value.filter((r) => r.status === 'pending'))
const recentRequests = computed(() => requests.value.filter((r) => r.status !== 'pending').slice(0, 10))

function statusTagType(status: ClassEnrollmentRequest['status']) {
  if (status === 'approved') return 'success'
  if (status === 'rejected') return 'error'
  return 'warning'
}

function statusLabel(status: ClassEnrollmentRequest['status']) {
  if (status === 'approved') return '已通过'
  if (status === 'rejected') return '已驳回'
  return '待审核'
}

async function load() {
  loading.value = true
  try {
    const classRes = await fetchClasses()
    if (classRes.code === 0) {
      classes.value = classRes.data.classes
    }
    requests.value = await fetchEnrollmentRequests({
      class_id: filterClassId.value ?? undefined,
    })
  } catch (error) {
    message.error(error instanceof Error ? error.message : '入班申请加载失败')
  } finally {
    loading.value = false
  }
}

async function handleReview(row: ClassEnrollmentRequest, approve: boolean) {
  reviewingId.value = row.id
  try {
    await reviewEnrollmentRequest(row.id, approve, reviewNote.value.trim() || undefined)
    message.success(approve ? '已通过入班申请' : '已驳回入班申请')
    reviewNote.value = ''
    await load()
    emit('changed')
  } catch (error) {
    message.error(error instanceof Error ? error.message : '审核失败')
  } finally {
    reviewingId.value = null
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="enrollment-review" aria-label="入班申请审核">
    <p class="enrollment-review__intro">
      学生通过<strong>班级编号</strong>提交入班申请后，需在本页审核通过才会加入班级。班级编号可在「班级管理」中查看。
    </p>

    <label class="enrollment-review__filter">
      <span>筛选班级</span>
      <n-select
        v-model:value="filterClassId"
        :options="classOptions"
        placeholder="全部班级"
        clearable
        @update:value="load"
      />
    </label>

    <div v-if="loading" class="teacher-state-panel">加载中…</div>
    <template v-else>
      <article class="enrollment-review__card">
        <h3>待审核 · {{ pendingRequests.length }}</h3>
        <div v-if="!pendingRequests.length" class="teacher-state-panel">暂无待审核的入班申请</div>
        <ul v-else class="enrollment-review__list">
          <li v-for="row in pendingRequests" :key="row.id">
            <div class="enrollment-review__main">
              <strong>{{ row.student_name || row.student_username }}</strong>
              <span class="enrollment-review__meta">申请加入 · {{ row.class_name }}</span>
              <p v-if="row.message" class="enrollment-review__message">{{ row.message }}</p>
              <small>{{ row.created_at?.slice(0, 16).replace('T', ' ') }}</small>
            </div>
            <div class="enrollment-review__actions">
              <n-input
                v-model:value="reviewNote"
                placeholder="填写审核备注，可选"
                size="small"
                style="margin-bottom: 0.5rem"
              />
              <div class="enrollment-review__buttons">
                <n-button
                  type="primary"
                  size="small"
                  :loading="reviewingId === row.id"
                  @click="handleReview(row, true)"
                >
                  通过
                </n-button>
                <n-button
                  size="small"
                  secondary
                  :loading="reviewingId === row.id"
                  @click="handleReview(row, false)"
                >
                  驳回
                </n-button>
              </div>
            </div>
          </li>
        </ul>
      </article>

      <article v-if="recentRequests.length" class="enrollment-review__card">
        <h3>近期处理记录</h3>
        <ul class="enrollment-review__list enrollment-review__list--compact">
          <li v-for="row in recentRequests" :key="row.id">
            <div>
              <strong>{{ row.student_name || row.student_username }}</strong>
              <span> · {{ row.class_name }}</span>
              <p v-if="row.review_note">{{ row.review_note }}</p>
              <small>{{ row.reviewed_at?.slice(0, 16).replace('T', ' ') }}</small>
            </div>
            <n-tag size="small" :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</n-tag>
          </li>
        </ul>
      </article>
    </template>
  </div>
</template>

<style scoped>
.enrollment-review {
  display: grid;
  gap: 1rem;
}

.enrollment-review__intro {
  margin: 0;
  padding: 0.75rem 1rem;
  border: 1px solid rgba(130, 212, 255, 0.15);
  border-radius: 12px;
  background: rgba(4, 14, 24, 0.65);
  color: rgba(214, 230, 244, 0.78);
  font-size: 0.86rem;
  line-height: 1.55;
}

.enrollment-review__intro strong {
  color: #fcd34d;
}

.enrollment-review__filter {
  display: grid;
  gap: 0.4rem;
  max-width: 280px;
}

.enrollment-review__filter > span {
  font-size: 0.84rem;
  color: rgba(214, 230, 244, 0.78);
}

.enrollment-review__card {
  padding: 1rem 1.1rem;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 14px;
  background: rgba(3, 16, 28, 0.78);
}

.enrollment-review__card h3 {
  margin: 0 0 0.85rem;
  font-size: 1rem;
}

.enrollment-review__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.75rem;
}

.enrollment-review__list li {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 1rem;
  align-items: start;
  padding: 0.75rem 0.85rem;
  border: 1px solid rgba(130, 212, 255, 0.1);
  border-radius: 12px;
  background: rgba(4, 12, 20, 0.45);
}

.enrollment-review__list--compact li {
  grid-template-columns: minmax(0, 1fr) auto;
}

.enrollment-review__meta {
  display: block;
  margin-top: 0.15rem;
  font-size: 0.84rem;
  color: rgba(214, 230, 244, 0.72);
}

.enrollment-review__message {
  margin: 0.35rem 0 0;
  font-size: 0.86rem;
  color: rgba(214, 230, 244, 0.82);
}

.enrollment-review__actions {
  min-width: 160px;
}

.enrollment-review__buttons {
  display: flex;
  gap: 0.5rem;
}

.enrollment-review small {
  display: block;
  margin-top: 0.35rem;
  color: rgba(214, 230, 244, 0.55);
  font-size: 0.78rem;
}
</style>
