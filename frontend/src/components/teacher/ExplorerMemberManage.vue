<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  NButton,
  NEmpty,
  NIcon,
  NInput,
  NModal,
  NPagination,
  NSelect,
  NSpin,
  NTag,
  useMessage,
  type SelectOption,
} from 'naive-ui'
import {
  AddOutline,
  CreateOutline,
  PauseCircleOutline,
  PlayCircleOutline,
  SearchOutline,
  TrashOutline,
} from '@vicons/ionicons5'
import {
  createStudent,
  deleteStudent,
  fetchClasses,
  fetchStudents,
  updateStudent,
  updateStudentStatus,
  type ClassSummary,
  type Student,
  type StudentStatus,
} from '../../api/studentManagement'

type FormMode = 'create' | 'edit'

const props = defineProps<{
  defaultClassId?: number | null
}>()

const emit = defineEmits<{
  changed: []
}>()

const message = useMessage()

const students = ref<Student[]>([])
const classes = ref<ClassSummary[]>([])
const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const modalVisible = ref(false)
const confirmVisible = ref(false)
const formMode = ref<FormMode>('create')
const pendingDelete = ref<Student | null>(null)

const pagination = reactive({
  page: 1,
  limit: 10,
  total: 0,
})

const filters = reactive({
  search: '',
  status: 'active,frozen',
  classId: 0,
})

const form = reactive({
  id: 0,
  username: '',
  email: '',
  password: '',
  real_name: '',
  phone: '',
  gender: 'other',
  bio: '',
  class_id: 0,
  status: 'active' as StudentStatus,
})

const statusOptions: SelectOption[] = [
  { label: '在读 + 冻结', value: 'active,frozen' },
  { label: '在读', value: 'active' },
  { label: '冻结', value: 'frozen' },
  { label: '已删除', value: 'deleted' },
]

const genderOptions: SelectOption[] = [
  { label: '未设置', value: 'other' },
  { label: '男', value: 'male' },
  { label: '女', value: 'female' },
]

const studentStatusOptions: SelectOption[] = [
  { label: '在读', value: 'active' },
  { label: '冻结', value: 'frozen' },
]

const classOptions = computed<SelectOption[]>(() => [
  { label: '全部班级', value: 0 },
  ...classes.value.map((item) => ({
    label: item.teacher_name ? `${item.name} · ${item.teacher_name}` : item.name,
    value: item.id,
  })),
])

const formClassOptions = computed<SelectOption[]>(() => [
  { label: '暂不分班', value: 0 },
  ...classes.value.map((item) => ({
    label: item.teacher_name ? `${item.name} · ${item.teacher_name}` : item.name,
    value: item.id,
  })),
])

const totalPages = computed(() => Math.max(1, Math.ceil(pagination.total / pagination.limit)))
const modalTitle = computed(() => (formMode.value === 'create' ? '新增 Explorer' : '编辑 Explorer'))

function statusLabel(status: StudentStatus) {
  return { active: '在读', frozen: '冻结', deleted: '已删除' }[status]
}

function statusTagType(status: StudentStatus) {
  return status === 'active' ? 'success' : status === 'frozen' ? 'warning' : 'error'
}

function formatDate(value: string | null) {
  if (!value) return '-'
  return value.slice(0, 10)
}

function getErrorMessage(error: unknown) {
  const maybe = error as { response?: { data?: { message?: string } }; message?: string }
  return maybe.response?.data?.message || maybe.message || '操作失败'
}

function resetForm() {
  Object.assign(form, {
    id: 0,
    username: '',
    email: '',
    password: '',
    real_name: '',
    phone: '',
    gender: 'other',
    bio: '',
    class_id: props.defaultClassId || 0,
    status: 'active',
  })
}

async function loadClasses() {
  try {
    const result = await fetchClasses()
    if (result.code !== 0) throw new Error(result.message)
    classes.value = result.data.classes
  } catch (error) {
    message.error(getErrorMessage(error))
  }
}

async function loadStudents() {
  loading.value = true
  try {
    const result = await fetchStudents({
      page: pagination.page,
      limit: pagination.limit,
      search: filters.search.trim(),
      status: filters.status,
      class_id: filters.classId || null,
    })
    if (result.code !== 0) throw new Error(result.message)
    students.value = result.data.users
    pagination.total = result.data.total
  } catch (error) {
    message.error(getErrorMessage(error))
  } finally {
    loading.value = false
  }
}

function runSearch() {
  pagination.page = 1
  void loadStudents()
}

function openCreateModal() {
  resetForm()
  formMode.value = 'create'
  modalVisible.value = true
}

function openEditModal(student: Student) {
  Object.assign(form, {
    id: student.id,
    username: student.username,
    email: student.email,
    password: '',
    real_name: student.real_name || '',
    phone: student.phone || '',
    gender: 'other',
    bio: '',
    class_id: student.class_id || 0,
    status: student.status === 'deleted' ? 'active' : student.status,
  })
  formMode.value = 'edit'
  modalVisible.value = true
}

function validateForm() {
  if (!form.username.trim()) return '请填写用户名'
  if (!form.email.trim()) return '请填写邮箱'
  if (!form.real_name.trim()) return '请填写姓名'
  if (formMode.value === 'create' && !form.password) return '请填写初始密码'
  return ''
}

async function submitForm() {
  const validationMessage = validateForm()
  if (validationMessage) {
    message.warning(validationMessage)
    return
  }

  saving.value = true
  try {
    if (formMode.value === 'create') {
      const result = await createStudent({
        username: form.username.trim(),
        email: form.email.trim(),
        password: form.password,
        real_name: form.real_name.trim(),
        phone: form.phone.trim(),
        gender: form.gender,
        bio: form.bio.trim(),
        class_id: form.class_id || null,
      })
      if (result.code !== 0) throw new Error(result.message)
      message.success('Explorer 创建成功')
    } else {
      const result = await updateStudent(form.id, {
        username: form.username.trim(),
        email: form.email.trim(),
        real_name: form.real_name.trim(),
        phone: form.phone.trim(),
        gender: form.gender,
        bio: form.bio.trim(),
        class_id: form.class_id || null,
        status: form.status,
      })
      if (result.code !== 0) throw new Error(result.message)
      message.success('Explorer 信息已更新')
    }
    modalVisible.value = false
    await Promise.all([loadClasses(), loadStudents()])
    emit('changed')
  } catch (error) {
    message.error(getErrorMessage(error))
  } finally {
    saving.value = false
  }
}

async function toggleStatus(student: Student) {
  const nextStatus = student.status === 'active' ? 'frozen' : 'active'
  try {
    const result = await updateStudentStatus(student.id, nextStatus)
    if (result.code !== 0) throw new Error(result.message)
    message.success(nextStatus === 'active' ? 'Explorer 已启用' : 'Explorer 已冻结')
    await loadStudents()
    emit('changed')
  } catch (error) {
    message.error(getErrorMessage(error))
  }
}

function requestDelete(student: Student) {
  pendingDelete.value = student
  confirmVisible.value = true
}

async function confirmDelete() {
  if (!pendingDelete.value) return
  deleting.value = true
  try {
    const result = await deleteStudent(pendingDelete.value.id)
    if (result.code !== 0) throw new Error(result.message)
    message.success('Explorer 已删除')
    confirmVisible.value = false
    await Promise.all([loadClasses(), loadStudents()])
    emit('changed')
  } catch (error) {
    message.error(getErrorMessage(error))
  } finally {
    deleting.value = false
  }
}

watch(
  () => props.defaultClassId,
  (classId) => {
    if (classId) {
      filters.classId = classId
      form.class_id = classId
    }
    pagination.page = 1
    void loadStudents()
  },
)

onMounted(async () => {
  if (props.defaultClassId) {
    filters.classId = props.defaultClassId
    form.class_id = props.defaultClassId
  }
  await loadClasses()
  await loadStudents()
})
</script>

<template>
  <section class="member-manage" aria-label="Explorer 成员管理">
    <section class="member-manage__toolbar teacher-panel">
      <n-input
        v-model:value="filters.search"
        clearable
        placeholder="搜索姓名、账号或邮箱"
        class="member-manage__search"
        @keydown.enter="runSearch"
      >
        <template #prefix>
          <n-icon :component="SearchOutline" />
        </template>
      </n-input>
      <n-select v-model:value="filters.status" :options="statusOptions" class="member-manage__filter" />
      <n-select v-model:value="filters.classId" :options="classOptions" class="member-manage__filter member-manage__filter--wide" />
      <n-button secondary class="member-manage__btn" @click="runSearch">查询</n-button>
      <n-button type="primary" class="member-manage__btn member-manage__btn--primary" @click="openCreateModal">
        <template #icon>
          <n-icon :component="AddOutline" />
        </template>
        新增 Explorer
      </n-button>
    </section>

    <section class="member-manage__board teacher-panel">
      <header class="member-manage__head">
        <div>
          <h2>Explorer 成员列表</h2>
          <p>共 {{ pagination.total }} 名，当前第 {{ pagination.page }} / {{ totalPages }} 页</p>
        </div>
      </header>

      <n-spin :show="loading">
        <div v-if="students.length" class="member-manage__table-wrap">
          <table class="member-manage__table">
            <thead>
              <tr>
                <th>姓名</th>
                <th>账号</th>
                <th>邮箱</th>
                <th>电话</th>
                <th>班级</th>
                <th>等级</th>
                <th>积分</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="student in students" :key="student.id">
                <td><strong>{{ student.real_name || '-' }}</strong></td>
                <td>{{ student.username }}</td>
                <td>{{ student.email }}</td>
                <td>{{ student.phone || '-' }}</td>
                <td>{{ student.class_name || '未分班' }}</td>
                <td>Lv.{{ student.level }}</td>
                <td>{{ student.total_points }}</td>
                <td>
                  <n-tag round size="small" :type="statusTagType(student.status)">
                    {{ statusLabel(student.status) }}
                  </n-tag>
                </td>
                <td>{{ formatDate(student.created_at) }}</td>
                <td>
                  <div class="member-manage__actions">
                    <n-button size="small" quaternary :disabled="student.status === 'deleted'" @click="openEditModal(student)">
                      <template #icon>
                        <n-icon :component="CreateOutline" />
                      </template>
                      编辑
                    </n-button>
                    <n-button
                      size="small"
                      quaternary
                      :disabled="student.status === 'deleted'"
                      @click="toggleStatus(student)"
                    >
                      <template #icon>
                        <n-icon :component="student.status === 'active' ? PauseCircleOutline : PlayCircleOutline" />
                      </template>
                      {{ student.status === 'active' ? '冻结' : '启用' }}
                    </n-button>
                    <n-button
                      size="small"
                      quaternary
                      type="error"
                      :disabled="student.status === 'deleted'"
                      @click="requestDelete(student)"
                    >
                      <template #icon>
                        <n-icon :component="TrashOutline" />
                      </template>
                      删除
                    </n-button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <n-empty v-else description="暂无 Explorer 数据" class="member-manage__empty" />
      </n-spin>

      <footer class="member-manage__foot">
        <n-pagination
          v-model:page="pagination.page"
          :page-size="pagination.limit"
          :item-count="pagination.total"
          @update:page="loadStudents"
        />
      </footer>
    </section>

    <n-modal v-model:show="modalVisible" preset="card" :title="modalTitle" class="explorer-member-modal" :bordered="false">
      <div class="member-manage__form">
        <label>
          <span>姓名</span>
          <n-input v-model:value="form.real_name" placeholder="例如：张三" />
        </label>
        <label>
          <span>用户名</span>
          <n-input v-model:value="form.username" placeholder="例如：student006" />
        </label>
        <label>
          <span>邮箱</span>
          <n-input v-model:value="form.email" placeholder="student@example.com" />
        </label>
        <label v-if="formMode === 'create'">
          <span>初始密码</span>
          <n-input v-model:value="form.password" type="password" show-password-on="click" placeholder="请输入初始密码" />
        </label>
        <label>
          <span>电话</span>
          <n-input v-model:value="form.phone" placeholder="可选" />
        </label>
        <label>
          <span>性别</span>
          <n-select v-model:value="form.gender" :options="genderOptions" />
        </label>
        <label>
          <span>班级</span>
          <n-select v-model:value="form.class_id" :options="formClassOptions" />
        </label>
        <label v-if="formMode === 'edit'">
          <span>状态</span>
          <n-select v-model:value="form.status" :options="studentStatusOptions" />
        </label>
        <label class="member-manage__form-wide">
          <span>备注</span>
          <n-input v-model:value="form.bio" type="textarea" placeholder="可选" />
        </label>
      </div>
      <template #footer>
        <div class="member-manage__modal-actions">
          <n-button @click="modalVisible = false">取消</n-button>
          <n-button type="primary" class="member-manage__btn--primary" :loading="saving" @click="submitForm">保存</n-button>
        </div>
      </template>
    </n-modal>

    <n-modal v-model:show="confirmVisible" preset="dialog" title="删除 Explorer" positive-text="确认删除" negative-text="取消">
      <p class="member-manage__delete-copy">
        确认删除 Explorer「{{ pendingDelete?.real_name || pendingDelete?.username }}」？该操作会将学生标记为已删除，并从班级中移出。
      </p>
      <template #action>
        <n-button @click="confirmVisible = false">取消</n-button>
        <n-button type="error" :loading="deleting" @click="confirmDelete">确认删除</n-button>
      </template>
    </n-modal>
  </section>
</template>

<style scoped>
.member-manage {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}

.member-manage__toolbar {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 140px 200px auto auto;
  gap: 0.75rem;
  align-items: center;
  padding: 1rem 1.1rem;
  flex-shrink: 0;
}

.member-manage__search,
.member-manage__filter {
  min-width: 0;
}

.member-manage__filter--wide {
  min-width: 180px;
}

.member-manage__btn--primary {
  --n-color: #ea580c !important;
  --n-color-hover: #fb923c !important;
  --n-color-pressed: #c2410c !important;
  --n-color-focus: #fb923c !important;
}

.member-manage__board {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  padding: 1.1rem 1.15rem;
  overflow: hidden;
}

.member-manage__head {
  flex-shrink: 0;
  margin-bottom: 0.85rem;
}

.member-manage__head h2 {
  margin: 0;
  color: var(--teacher-text, #fff7ed);
  font-size: 1.15rem;
}

.member-manage__head p {
  margin: 0.3rem 0 0;
  color: var(--teacher-muted);
  font-size: 0.84rem;
}

.member-manage__table-wrap {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.member-manage__table {
  width: 100%;
  border-collapse: collapse;
  min-width: 1060px;
}

.member-manage__table th,
.member-manage__table td {
  padding: 0.85rem 0.7rem;
  border-bottom: 1px solid rgba(251, 146, 60, 0.1);
  text-align: left;
  white-space: nowrap;
}

.member-manage__table th {
  color: var(--teacher-muted);
  font-size: 0.76rem;
  font-weight: 700;
}

.member-manage__table td {
  color: rgba(255, 247, 237, 0.86);
  font-size: 0.84rem;
}

.member-manage__table td strong {
  color: var(--teacher-text);
}

.member-manage__actions {
  display: flex;
  align-items: center;
  gap: 0.15rem;
}

.member-manage__actions :deep(.n-button) {
  color: rgba(255, 237, 213, 0.82);
}

.member-manage__actions :deep(.n-button:hover) {
  color: var(--teacher-orange, #fb923c);
}

.member-manage__empty {
  padding: 3rem 0;
}

.member-manage__foot {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  padding-top: 0.85rem;
}

.member-manage__foot :deep(.n-pagination-item--active) {
  background: rgba(251, 146, 60, 0.22) !important;
  border-color: rgba(251, 146, 60, 0.45) !important;
  color: #fff7ed !important;
}

.member-manage__form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.member-manage__form label {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 0;
}

.member-manage__form label span {
  color: var(--teacher-muted);
  font-size: 0.8rem;
  font-weight: 700;
}

.member-manage__form-wide {
  grid-column: 1 / -1;
}

.member-manage__modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.65rem;
}

.member-manage__delete-copy {
  margin: 0;
  color: rgba(255, 247, 237, 0.82);
  line-height: 1.65;
}

@media (max-width: 980px) {
  .member-manage__toolbar {
    grid-template-columns: 1fr 1fr;
  }

  .member-manage__btn--primary {
    grid-column: span 2;
  }
}

@media (max-width: 720px) {
  .member-manage__toolbar,
  .member-manage__form {
    grid-template-columns: 1fr;
  }

  .member-manage__btn--primary {
    grid-column: auto;
  }
}
</style>

<style>
.explorer-member-modal.n-card {
  width: min(720px, calc(100vw - 48px));
  background: rgba(8, 14, 22, 0.98) !important;
  border: 1px solid rgba(251, 146, 60, 0.2) !important;
}

.explorer-member-modal .n-card-header__main {
  color: #fff7ed !important;
}
</style>
