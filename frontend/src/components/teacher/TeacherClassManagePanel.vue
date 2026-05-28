<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { NButton, NInput, NSelect, NTag, useMessage, type SelectOption } from 'naive-ui'
import { fetchClassRequests, submitClassRequest, type ClassChangeRequest } from '../../api/classRequests'
import { updateClass } from '../../api/classManagement'
import { fetchClasses, type ClassSummary } from '../../api/studentManagement'
import { useAuthStore } from '../../stores/auth'

const props = defineProps<{
  defaultClassId?: number | null
}>()

const emit = defineEmits<{
  changed: []
}>()

const message = useMessage()
const auth = useAuthStore()

const classes = ref<ClassSummary[]>([])
const myRequests = ref<ClassChangeRequest[]>([])
const loading = ref(false)
const saving = ref(false)
const submitting = ref(false)

const editClassId = ref<number | null>(null)
const editForm = reactive({
  name: '',
  description: '',
  grade_level: null as number | null,
})

const createForm = reactive({
  name: '',
  description: '',
  grade_level: null as number | null,
})

const deleteClassId = ref<number | null>(null)
const deleteReason = ref('')

const isAdmin = computed(() => auth.profile?.role === 'admin')

const classOptions = computed<SelectOption[]>(() =>
  classes.value.map((c) => ({ label: c.name, value: c.id })),
)

const myClasses = computed(() => {
  const uid = auth.profile?.id
  if (!uid || isAdmin.value) return classes.value
  return classes.value.filter((c) => c.teacher_id === uid)
})

const pendingRequests = computed(() => myRequests.value.filter((r) => r.status === 'pending'))

function statusTagType(status: ClassChangeRequest['status']) {
  if (status === 'approved') return 'success'
  if (status === 'rejected') return 'error'
  return 'warning'
}

function statusLabel(status: ClassChangeRequest['status']) {
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
    myRequests.value = await fetchClassRequests()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '班级数据加载失败')
  } finally {
    loading.value = false
  }
}

function selectClassForEdit(classId: number) {
  const row = myClasses.value.find((c) => c.id === classId)
  if (!row) return
  editClassId.value = classId
  editForm.name = row.name
  editForm.description = row.description ?? ''
  editForm.grade_level = row.grade_level
}

async function saveClassEdit() {
  if (!editClassId.value) {
    message.warning('请选择要编辑的班级')
    return
  }
  if (!editForm.name.trim()) {
    message.warning('班级名称不能为空')
    return
  }
  saving.value = true
  try {
    await updateClass(editClassId.value, {
      name: editForm.name.trim(),
      description: editForm.description.trim() || undefined,
      grade_level: editForm.grade_level,
    })
    message.success('班级信息已更新')
    await load()
    emit('changed')
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function requestCreateClass() {
  const uid = auth.profile?.id
  if (!uid) return
  if (!createForm.name.trim()) {
    message.warning('请填写班级名称')
    return
  }
  submitting.value = true
  try {
    await submitClassRequest({
      action: 'create',
      payload: {
        name: createForm.name.trim(),
        description: createForm.description.trim() || undefined,
        grade_level: createForm.grade_level,
        teacher_id: uid,
      },
      reason: '教师申请新建班级',
    })
    message.success('已提交新建班级申请，请等待管理员审核')
    createForm.name = ''
    createForm.description = ''
    createForm.grade_level = null
    await load()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '提交失败')
  } finally {
    submitting.value = false
  }
}

async function requestDeleteClass() {
  if (!deleteClassId.value) {
    message.warning('请选择要删除的班级')
    return
  }
  submitting.value = true
  try {
    await submitClassRequest({
      action: 'delete',
      class_id: deleteClassId.value,
      payload: {},
      reason: deleteReason.value.trim() || '教师申请删除班级',
    })
    message.success('已提交删除申请，请等待管理员审核')
    deleteClassId.value = null
    deleteReason.value = ''
    await load()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '提交失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  if (props.defaultClassId) {
    selectClassForEdit(props.defaultClassId)
  }
  void load()
})
</script>

<template>
  <div class="class-manage" aria-label="班级管理">
    <p class="class-manage__intro">
      教师可直接修改本班名称与说明；<strong>新建或删除班级</strong>需提交管理员审批。学生账号的增删改请在下方「Explorer 成员」中操作。
    </p>

    <div v-if="loading" class="teacher-state-panel">加载中…</div>
    <template v-else>
      <article class="class-manage__card">
        <h3>编辑班级（即时生效）</h3>
        <label class="class-manage__field">
          <span>选择班级</span>
          <n-select
            :value="editClassId"
            :options="classOptions"
            placeholder="选择班级"
            @update:value="(v) => v != null && selectClassForEdit(Number(v))"
          />
        </label>
        <label class="class-manage__field">
          <span>班级名称</span>
          <n-input v-model:value="editForm.name" placeholder="班级名称" />
        </label>
        <label class="class-manage__field">
          <span>说明</span>
          <n-input v-model:value="editForm.description" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" />
        </label>
        <n-button type="primary" :loading="saving" @click="saveClassEdit">保存修改</n-button>
      </article>

      <article v-if="!isAdmin" class="class-manage__card">
        <h3>申请新建班级</h3>
        <label class="class-manage__field">
          <span>班级名称</span>
          <n-input v-model:value="createForm.name" placeholder="例如：2024 级 Python 探索班" />
        </label>
        <label class="class-manage__field">
          <span>说明（可选）</span>
          <n-input v-model:value="createForm.description" placeholder="班级简介" />
        </label>
        <n-button type="primary" :loading="submitting" @click="requestCreateClass">提交新建申请</n-button>
      </article>

      <article v-if="!isAdmin" class="class-manage__card">
        <h3>申请删除班级</h3>
        <label class="class-manage__field">
          <span>目标班级</span>
          <n-select v-model:value="deleteClassId" :options="classOptions" placeholder="选择班级" clearable />
        </label>
        <label class="class-manage__field">
          <span>申请理由</span>
          <n-input v-model:value="deleteReason" placeholder="请简要说明原因" />
        </label>
        <n-button type="error" secondary :loading="submitting" @click="requestDeleteClass">提交删除申请</n-button>
      </article>

      <article class="class-manage__card">
        <h3>我的班级变更申请</h3>
        <div v-if="!myRequests.length" class="teacher-state-panel">暂无申请记录</div>
        <ul v-else class="class-manage__requests">
          <li v-for="row in myRequests" :key="row.id">
            <div>
              <strong>{{ row.action === 'create' ? '新建' : row.action === 'delete' ? '删除' : '修改' }}班级</strong>
              <span v-if="row.class_name"> · {{ row.class_name }}</span>
              <p v-if="row.reason">{{ row.reason }}</p>
              <small>{{ row.created_at?.slice(0, 16).replace('T', ' ') }}</small>
            </div>
            <n-tag size="small" :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</n-tag>
          </li>
        </ul>
        <p v-if="pendingRequests.length" class="class-manage__pending">
          当前有 {{ pendingRequests.length }} 条待审申请，请等待管理员在控制中枢处理。
        </p>
      </article>
    </template>
  </div>
</template>

<style scoped>
.class-manage {
  display: grid;
  gap: 1rem;
}

.class-manage__intro {
  margin: 0;
  padding: 0.75rem 1rem;
  border: 1px solid rgba(130, 212, 255, 0.15);
  border-radius: 12px;
  background: rgba(4, 14, 24, 0.65);
  color: rgba(214, 230, 244, 0.78);
  font-size: 0.86rem;
  line-height: 1.55;
}

.class-manage__intro strong {
  color: #fcd34d;
  font-weight: 650;
}

.class-manage__card {
  padding: 1rem 1.1rem;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 14px;
  background: rgba(3, 16, 28, 0.78);
}

.class-manage__card h3 {
  margin: 0 0 0.85rem;
  color: #eef8ff;
  font-size: 1rem;
}

.class-manage__field {
  display: grid;
  gap: 0.35rem;
  margin-bottom: 0.75rem;
}

.class-manage__field > span {
  color: rgba(198, 214, 230, 0.68);
  font-size: 0.82rem;
}

.class-manage__requests {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.65rem;
}

.class-manage__requests li {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.65rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.class-manage__requests strong {
  color: #edf7ff;
}

.class-manage__requests p {
  margin: 0.25rem 0 0;
  color: rgba(198, 214, 230, 0.72);
  font-size: 0.82rem;
}

.class-manage__requests small {
  color: rgba(160, 180, 200, 0.55);
  font-size: 0.75rem;
}

.class-manage__pending {
  margin: 0.75rem 0 0;
  color: rgba(252, 211, 77, 0.9);
  font-size: 0.82rem;
}
</style>
