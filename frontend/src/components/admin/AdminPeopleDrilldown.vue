<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NButton, NModal, NSpin, useMessage } from 'naive-ui'
import {
  fetchAdminClassStudents,
  fetchAdminTeacherClasses,
  fetchAdminTrialTeachers,
  type AdminClassStudentItem,
  type AdminClassStudentsResult,
  type AdminTrialClassItem,
  type AdminTrialTeacherItem,
} from '../../api/adminSettings'

const props = defineProps<{
  show: boolean
  /** students: 教师 → 班级 → 学生；teachers: 教师 → 班级 */
  mode: 'students' | 'teachers'
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
}>()

const message = useMessage()
type Step = 'teachers' | 'classes' | 'students'
const step = ref<Step>('teachers')
const loading = ref(false)
const teachers = ref<AdminTrialTeacherItem[]>([])
const classes = ref<AdminTrialClassItem[]>([])
const studentsPayload = ref<AdminClassStudentsResult | null>(null)
const selectedTeacher = ref<AdminTrialTeacherItem | null>(null)
const selectedClass = ref<AdminTrialClassItem | null>(null)

const modalTitle = computed(() =>
  props.mode === 'students' ? '活跃学习者钻取' : '注册教师钻取',
)

const genderLabel: Record<string, string> = {
  male: '男',
  female: '女',
  other: '其他',
}

async function loadTeachers() {
  loading.value = true
  try {
    teachers.value = await fetchAdminTrialTeachers()
    step.value = 'teachers'
    selectedTeacher.value = null
    selectedClass.value = null
    classes.value = []
    studentsPayload.value = null
  } catch (err) {
    message.error(err instanceof Error ? err.message : '加载教师失败')
  } finally {
    loading.value = false
  }
}

async function openTeacher(teacher: AdminTrialTeacherItem) {
  selectedTeacher.value = teacher
  loading.value = true
  try {
    classes.value = await fetchAdminTeacherClasses(teacher.id)
    step.value = 'classes'
    selectedClass.value = null
    studentsPayload.value = null
  } catch (err) {
    message.error(err instanceof Error ? err.message : '加载班级失败')
  } finally {
    loading.value = false
  }
}

async function openClass(cls: AdminTrialClassItem) {
  if (props.mode !== 'students') return
  selectedClass.value = cls
  loading.value = true
  try {
    studentsPayload.value = await fetchAdminClassStudents(cls.id)
    step.value = 'students'
  } catch (err) {
    message.error(err instanceof Error ? err.message : '加载学生失败')
  } finally {
    loading.value = false
  }
}

function goBack() {
  if (step.value === 'students') {
    step.value = 'classes'
    studentsPayload.value = null
    return
  }
  if (step.value === 'classes') {
    step.value = 'teachers'
    selectedClass.value = null
    classes.value = []
  }
}

function statusLabel(status: string) {
  if (status === 'active') return '正常'
  if (status === 'frozen') return '冻结'
  if (status === 'deleted') return '已删除'
  return status
}

function studentMeta(stu: AdminClassStudentItem) {
  const parts = [
    `Lv${stu.level}`,
    `${stu.total_points} 积分`,
    `连续 ${stu.consecutive_days} 天`,
    statusLabel(stu.status),
  ]
  if (stu.gender) parts.push(genderLabel[stu.gender] || stu.gender)
  return parts.join(' · ')
}

watch(
  () => props.show,
  (visible) => {
    if (visible) void loadTeachers()
  },
)
</script>

<template>
  <n-modal
    :show="show"
    preset="card"
    :title="modalTitle"
    style="width: min(920px, 94vw)"
    :bordered="false"
    @update:show="emit('update:show', $event)"
  >
    <div class="drill-head">
      <n-button v-if="step !== 'teachers'" size="small" quaternary @click="goBack">返回上一级</n-button>
      <p>
        <template v-if="step === 'teachers'">
          {{ mode === 'students' ? '先选择教师，再进入其管理班级与学生' : '选择教师，查看其管理的班级' }}
        </template>
        <template v-else-if="step === 'classes'">
          {{ selectedTeacher?.name }} ·
          {{ mode === 'students' ? '选择班级查看学生' : '管理班级列表' }}
        </template>
        <template v-else>
          {{ selectedTeacher?.name }} / {{ selectedClass?.name }} · 学生信息
          <span v-if="studentsPayload">· {{ studentsPayload.student_count }} 人</span>
        </template>
      </p>
    </div>

    <n-spin :show="loading">
      <div v-if="step === 'teachers'" class="drill-grid">
        <button
          v-for="teacher in teachers"
          :key="teacher.id"
          type="button"
          class="drill-card"
          @click="openTeacher(teacher)"
        >
          <strong>{{ teacher.name }}</strong>
          <span>{{ teacher.username }}</span>
          <em>{{ teacher.class_count }} 个班级 · 试炼 {{ teacher.total_trials }} 场</em>
        </button>
        <p v-if="!teachers.length" class="drill-empty">暂无教师数据</p>
      </div>

      <div v-else-if="step === 'classes'" class="drill-grid">
        <button
          v-for="cls in classes"
          :key="cls.id"
          type="button"
          class="drill-card"
          :class="{ 'drill-card--static': mode === 'teachers' }"
          @click="openClass(cls)"
        >
          <strong>{{ cls.name }}</strong>
          <span>{{ cls.student_count }} 名学生 · {{ cls.trial_count }} 场试炼</span>
          <em>运行中 {{ cls.running_trials }} · 完成率 {{ cls.completion_rate }}%</em>
        </button>
        <p v-if="!classes.length" class="drill-empty">该教师暂无班级</p>
      </div>

      <div v-else class="student-list">
        <article v-for="stu in studentsPayload?.items || []" :key="stu.id" class="student-card">
          <header>
            <strong>{{ stu.name }}</strong>
            <small>{{ stu.username }}</small>
          </header>
          <p>{{ studentMeta(stu) }}</p>
          <dl>
            <div><dt>邮箱</dt><dd>{{ stu.email || '—' }}</dd></div>
            <div><dt>电话</dt><dd>{{ stu.phone || '—' }}</dd></div>
            <div><dt>最近学习</dt><dd>{{ stu.last_learn_date || '—' }}</dd></div>
            <div><dt>注册时间</dt><dd>{{ stu.created_at?.slice(0, 10) || '—' }}</dd></div>
          </dl>
        </article>
        <p v-if="!(studentsPayload?.items?.length)" class="drill-empty">该班级暂无学生</p>
      </div>
    </n-spin>
  </n-modal>
</template>

<style scoped>
.drill-head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.85rem;
}

.drill-head p {
  margin: 0;
  color: rgba(214, 200, 255, 0.78);
  font-size: 0.86rem;
}

.drill-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0.75rem;
  min-height: 180px;
}

.drill-card {
  display: grid;
  gap: 0.35rem;
  padding: 0.95rem 1rem;
  border-radius: 12px;
  border: 1px solid rgba(167, 139, 250, 0.28);
  background: rgba(24, 16, 48, 0.72);
  color: #f5f3ff;
  text-align: left;
  cursor: pointer;
}

.drill-card:hover {
  border-color: rgba(196, 181, 253, 0.55);
}

.drill-card--static {
  cursor: default;
}

.drill-card--static:hover {
  border-color: rgba(167, 139, 250, 0.28);
}

.drill-card span,
.drill-card em {
  color: rgba(196, 181, 253, 0.72);
  font-size: 0.8rem;
  font-style: normal;
}

.drill-empty {
  grid-column: 1 / -1;
  color: rgba(196, 181, 253, 0.65);
}

.student-list {
  display: grid;
  gap: 0.7rem;
  max-height: 60vh;
  overflow: auto;
}

.student-card {
  padding: 0.85rem 1rem;
  border-radius: 12px;
  border: 1px solid rgba(167, 139, 250, 0.22);
  background: rgba(20, 14, 40, 0.7);
}

.student-card header {
  display: flex;
  align-items: baseline;
  gap: 0.55rem;
}

.student-card strong {
  color: #f5f3ff;
}

.student-card small,
.student-card p {
  color: rgba(196, 181, 253, 0.72);
  font-size: 0.82rem;
}

.student-card p {
  margin: 0.35rem 0 0.55rem;
}

.student-card dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.35rem 0.85rem;
  margin: 0;
}

.student-card dl > div {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  font-size: 0.8rem;
}

.student-card dt {
  color: rgba(196, 181, 253, 0.58);
}

.student-card dd {
  margin: 0;
  color: rgba(245, 243, 255, 0.9);
}
</style>
