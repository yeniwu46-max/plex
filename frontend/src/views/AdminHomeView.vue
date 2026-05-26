<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
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
import DashboardShell from '../components/layout/DashboardShell.vue'
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
} from '../api/studentManagement'

type FormMode = 'create' | 'edit'

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
const modalTitle = computed(() => (formMode.value === 'create' ? '新增学生' : '编辑学生'))

function statusLabel(status: StudentStatus) {
  return {
    active: '在读',
    frozen: '冻结',
    deleted: '已删除',
  }[status]
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
    class_id: 0,
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
      message.success('学生创建成功')
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
      message.success('学生信息已更新')
    }
    modalVisible.value = false
    await Promise.all([loadClasses(), loadStudents()])
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
    message.success(nextStatus === 'active' ? '学生已启用' : '学生已冻结')
    await loadStudents()
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
    message.success('学生已删除')
    confirmVisible.value = false
    await Promise.all([loadClasses(), loadStudents()])
  } catch (error) {
    message.error(getErrorMessage(error))
  } finally {
    deleting.value = false
  }
}

onMounted(async () => {
  await loadClasses()
  await loadStudents()
})
</script>

<template>
  <DashboardShell
    active-nav="admin"
    page-title="学生管理"
    page-subtitle="管理学生账号、状态与班级归属"
    search-placeholder="搜索学生、账号或邮箱"
  >
    <template #toolbar>
      <section class="student-toolbar glass" aria-label="学生筛选">
        <n-input
          v-model:value="filters.search"
          clearable
          placeholder="搜索姓名、账号、邮箱"
          class="filter-input"
          @keydown.enter="runSearch"
        >
          <template #prefix>
            <n-icon :component="SearchOutline" />
          </template>
        </n-input>
        <n-select v-model:value="filters.status" :options="statusOptions" class="filter-select" />
        <n-select v-model:value="filters.classId" :options="classOptions" class="filter-select filter-select--wide" />
        <n-button secondary class="toolbar-btn" @click="runSearch">查询</n-button>
        <n-button type="primary" class="create-btn" @click="openCreateModal">
          <template #icon>
            <n-icon :component="AddOutline" />
          </template>
          新增学生
        </n-button>
      </section>
    </template>

    <section class="student-board glass" aria-label="学生列表">
      <header class="student-board__head">
        <div>
          <h2>学生列表</h2>
          <p>共 {{ pagination.total }} 名学生，当前第 {{ pagination.page }} / {{ totalPages }} 页</p>
        </div>
      </header>

      <n-spin :show="loading">
        <div v-if="students.length" class="table-wrap">
          <table class="student-table">
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
                <td>
                  <strong>{{ student.real_name || '-' }}</strong>
                </td>
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
                  <div class="row-actions">
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
        <n-empty v-else description="暂无学生数据" class="empty-state" />
      </n-spin>

      <footer class="student-board__foot">
        <n-pagination
          v-model:page="pagination.page"
          :page-size="pagination.limit"
          :item-count="pagination.total"
          @update:page="loadStudents"
        />
      </footer>
    </section>

    <n-modal v-model:show="modalVisible" preset="card" :title="modalTitle" class="student-modal" :bordered="false">
      <div class="student-form">
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
        <label class="student-form__wide">
          <span>备注</span>
          <n-input v-model:value="form.bio" type="textarea" placeholder="可选" />
        </label>
      </div>
      <template #footer>
        <div class="modal-actions">
          <n-button @click="modalVisible = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="submitForm">保存</n-button>
        </div>
      </template>
    </n-modal>

    <n-modal v-model:show="confirmVisible" preset="dialog" title="删除学生" positive-text="确认删除" negative-text="取消">
      <p class="delete-copy">
        确认删除学生「{{ pendingDelete?.real_name || pendingDelete?.username }}」？该操作会将学生标记为已删除，并从班级中移出。
      </p>
      <template #action>
        <n-button @click="confirmVisible = false">取消</n-button>
        <n-button type="error" :loading="deleting" @click="confirmDelete">确认删除</n-button>
      </template>
    </n-modal>
  </DashboardShell>
</template>

<style scoped>
.student-toolbar {
  position: relative;
  z-index: 2;
  display: grid;
  grid-template-columns: minmax(240px, 1fr) 150px 220px auto auto;
  gap: 0.8rem;
  align-items: center;
  margin: 0 2.8rem 1rem 3.7rem;
  padding: 1rem;
  border: 1px solid rgba(37, 245, 238, 0.18);
  border-radius: 14px;
  background: rgba(5, 17, 29, 0.72);
}

.filter-input,
.filter-select {
  min-width: 0;
}

.filter-select--wide {
  min-width: 180px;
}

.toolbar-btn,
.create-btn {
  min-width: 86px;
}

.student-board {
  position: relative;
  z-index: 1;
  margin: 0 2.8rem 2rem 3.7rem;
  padding: 1.2rem;
  border: 1px solid rgba(37, 245, 238, 0.18);
  border-radius: 16px;
  background: rgba(5, 17, 29, 0.76);
  box-shadow: 0 22px 70px rgba(0, 0, 0, 0.24);
}

.student-board__head,
.student-board__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.student-board__head {
  margin-bottom: 1rem;
}

.student-board__head h2 {
  margin: 0;
  color: #f4fbff;
  font-size: 1.2rem;
}

.student-board__head p {
  margin: 0.35rem 0 0;
  color: rgba(221, 230, 239, 0.66);
  font-size: 0.86rem;
}

.table-wrap {
  overflow-x: auto;
}

.student-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 1060px;
  color: #eaf7ff;
}

.student-table th,
.student-table td {
  padding: 0.9rem 0.75rem;
  border-bottom: 1px solid rgba(224, 237, 247, 0.08);
  text-align: left;
  white-space: nowrap;
}

.student-table th {
  color: rgba(221, 230, 239, 0.66);
  font-size: 0.78rem;
  font-weight: 700;
}

.student-table td {
  color: rgba(235, 247, 255, 0.86);
  font-size: 0.86rem;
}

.student-table td strong {
  color: #ffffff;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 0.2rem;
}

.empty-state {
  padding: 4rem 0;
}

.student-board__foot {
  justify-content: flex-end;
  padding-top: 1rem;
}

.student-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.student-form label {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.45rem;
}

.student-form label span {
  color: rgba(221, 230, 239, 0.76);
  font-size: 0.82rem;
  font-weight: 700;
}

.student-form__wide {
  grid-column: 1 / -1;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.delete-copy {
  margin: 0;
  color: rgba(221, 230, 239, 0.82);
  line-height: 1.7;
}

:global(.student-modal) {
  width: min(720px, calc(100vw - 48px));
  background: rgba(5, 17, 29, 0.96);
}

@media (max-width: 980px) {
  .student-toolbar {
    grid-template-columns: 1fr 1fr;
  }

  .create-btn {
    grid-column: span 2;
  }
}

@media (max-width: 720px) {
  .student-toolbar,
  .student-board {
    margin-right: 1rem;
    margin-left: 1rem;
  }

  .student-toolbar,
  .student-form {
    grid-template-columns: 1fr;
  }

  .create-btn {
    grid-column: auto;
  }
}
</style>
