<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NButton, NInput, NTag, useMessage } from 'naive-ui'
import { formatHttpError } from '../../api/http'
import {
  applyToClass,
  fetchMyEnrollmentRequests,
  lookupClassByCode,
  type ClassEnrollmentRequest,
  type ClassLookupResult,
} from '../../api/classEnrollments'

const props = defineProps<{
  hasClass?: boolean
}>()

const emit = defineEmits<{
  joined: []
}>()

const message = useMessage()
const joinCode = ref('')
const applyMessage = ref('')
const preview = ref<ClassLookupResult | null>(null)
const requests = ref<ClassEnrollmentRequest[]>([])
const loading = ref(false)
const lookingUp = ref(false)
const submitting = ref(false)

const pendingRequest = computed(() => requests.value.find((r) => r.status === 'pending'))

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

async function loadRequests() {
  loading.value = true
  try {
    requests.value = await fetchMyEnrollmentRequests()
  } catch (error) {
    message.error(formatHttpError(error, '申请记录加载失败'))
  } finally {
    loading.value = false
  }
}

async function lookupClass() {
  const code = joinCode.value.trim()
  if (!code) {
    message.warning('请输入班级编号')
    return
  }
  lookingUp.value = true
  preview.value = null
  try {
    preview.value = await lookupClassByCode(code)
  } catch (error) {
    message.error(formatHttpError(error, '班级编号无效'))
  } finally {
    lookingUp.value = false
  }
}

async function submitApply() {
  const code = joinCode.value.trim()
  if (!code) {
    message.warning('请输入班级编号')
    return
  }
  submitting.value = true
  try {
    await applyToClass(code, applyMessage.value.trim() || undefined)
    message.success('入班申请已提交，请等待教师审核')
    joinCode.value = ''
    applyMessage.value = ''
    preview.value = null
    await loadRequests()
  } catch (error) {
    message.error(formatHttpError(error, '提交失败'))
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  void loadRequests()
})
</script>

<template>
  <article class="join-class" aria-label="申请加入班级">
    <header>
      <h3>加入班级</h3>
      <p v-if="hasClass">你已在班级中；申请通过后将会转入新班级。</p>
      <p v-else>向教师索取班级编号，提交申请后由教师审核通过即可入班。</p>
    </header>

    <div v-if="pendingRequest" class="join-class__pending">
      <strong>待审核申请</strong>
      <p>
        {{ pendingRequest.class_name }}（编号 {{ pendingRequest.join_code }}）
        <n-tag size="small" type="warning">待审核</n-tag>
      </p>
      <small>{{ pendingRequest.created_at?.slice(0, 16).replace('T', ' ') }}</small>
    </div>

    <label class="join-class__field">
      <span>班级编号</span>
      <div class="join-class__code-row">
        <n-input
          v-model:value="joinCode"
          placeholder="例如：ABC123"
          maxlength="8"
          :disabled="!!pendingRequest"
          @keyup.enter="lookupClass"
        />
        <n-button secondary :loading="lookingUp" :disabled="!!pendingRequest" @click="lookupClass">验证</n-button>
      </div>
    </label>

    <div v-if="preview" class="join-class__preview">
      <strong>{{ preview.class_name }}</strong>
      <p>负责教师：{{ preview.teacher_name || '—' }}</p>
      <p>当前成员：{{ preview.student_count }} 人</p>
    </div>

    <label class="join-class__field">
      <span>申请留言（可选）</span>
      <n-input
        v-model:value="applyMessage"
        type="textarea"
        placeholder="简单介绍自己或说明加入原因…"
        :autosize="{ minRows: 2, maxRows: 3 }"
        maxlength="200"
        show-count
        :disabled="!!pendingRequest"
      />
    </label>

    <n-button
      type="primary"
      class="join-class__submit"
      :loading="submitting"
      :disabled="!!pendingRequest"
      @click="submitApply"
    >
      提交入班申请
    </n-button>

    <section v-if="requests.length" class="join-class__history">
      <h4>申请记录</h4>
      <ul>
        <li v-for="row in requests" :key="row.id">
          <div>
            <strong>{{ row.class_name || `班级 #${row.class_id}` }}</strong>
            <p v-if="row.message">{{ row.message }}</p>
            <small>{{ row.created_at?.slice(0, 16).replace('T', ' ') }}</small>
          </div>
          <n-tag size="small" :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</n-tag>
        </li>
      </ul>
    </section>
    <p v-else-if="!loading" class="join-class__empty">暂无申请记录</p>
  </article>
</template>

<style scoped>
.join-class {
  display: grid;
  gap: 0.85rem;
}

.join-class header h3 {
  margin: 0 0 0.35rem;
  font-size: 1.05rem;
}

.join-class header p {
  margin: 0;
  color: rgba(214, 230, 244, 0.72);
  font-size: 0.86rem;
  line-height: 1.5;
}

.join-class__pending {
  padding: 0.75rem 0.85rem;
  border: 1px solid rgba(251, 191, 36, 0.35);
  border-radius: 12px;
  background: rgba(251, 191, 36, 0.08);
}

.join-class__pending p {
  margin: 0.35rem 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.join-class__field {
  display: grid;
  gap: 0.4rem;
}

.join-class__field > span {
  font-size: 0.84rem;
  color: rgba(214, 230, 244, 0.78);
}

.join-class__code-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.5rem;
}

.join-class__preview {
  padding: 0.75rem 0.85rem;
  border: 1px solid rgba(56, 189, 248, 0.25);
  border-radius: 12px;
  background: rgba(56, 189, 248, 0.08);
}

.join-class__preview p {
  margin: 0.25rem 0 0;
  font-size: 0.84rem;
  color: rgba(214, 230, 244, 0.78);
}

.join-class__submit {
  width: 100%;
}

.join-class__history h4 {
  margin: 0.5rem 0 0.65rem;
  font-size: 0.92rem;
}

.join-class__history ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.55rem;
}

.join-class__history li {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: flex-start;
  padding: 0.65rem 0.75rem;
  border: 1px solid rgba(130, 212, 255, 0.1);
  border-radius: 10px;
  background: rgba(4, 12, 20, 0.45);
}

.join-class__history p {
  margin: 0.2rem 0;
  font-size: 0.84rem;
  color: rgba(214, 230, 244, 0.72);
}

.join-class__history small {
  color: rgba(214, 230, 244, 0.55);
  font-size: 0.78rem;
}

.join-class__empty {
  margin: 0;
  font-size: 0.84rem;
  color: rgba(214, 230, 244, 0.55);
}
</style>
