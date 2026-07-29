<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NButton, NModal, NSpin, useMessage } from 'naive-ui'
import {
  fetchAdminClassTrialStats,
  fetchAdminTeacherClasses,
  fetchAdminTrialTeachers,
  type AdminClassTrialStats,
  type AdminTrialClassItem,
  type AdminTrialTeacherItem,
} from '../../api/adminSettings'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
}>()

const message = useMessage()
type Step = 'teachers' | 'classes' | 'trials'
const step = ref<Step>('teachers')
const loading = ref(false)
const teachers = ref<AdminTrialTeacherItem[]>([])
const classes = ref<AdminTrialClassItem[]>([])
const stats = ref<AdminClassTrialStats | null>(null)
const selectedTeacher = ref<AdminTrialTeacherItem | null>(null)
const selectedClass = ref<AdminTrialClassItem | null>(null)

async function loadTeachers() {
  loading.value = true
  try {
    teachers.value = await fetchAdminTrialTeachers()
    step.value = 'teachers'
    selectedTeacher.value = null
    selectedClass.value = null
    stats.value = null
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
    stats.value = null
  } catch (err) {
    message.error(err instanceof Error ? err.message : '加载班级失败')
  } finally {
    loading.value = false
  }
}

async function openClass(cls: AdminTrialClassItem) {
  selectedClass.value = cls
  loading.value = true
  try {
    stats.value = await fetchAdminClassTrialStats(cls.id)
    step.value = 'trials'
  } catch (err) {
    message.error(err instanceof Error ? err.message : '加载试炼失败')
  } finally {
    loading.value = false
  }
}

function goBack() {
  if (step.value === 'trials') {
    step.value = 'classes'
    stats.value = null
    return
  }
  if (step.value === 'classes') {
    step.value = 'teachers'
    selectedClass.value = null
    classes.value = []
  }
}

onMounted(() => {
  if (props.show) void loadTeachers()
})
</script>

<template>
  <n-modal
    :show="show"
    preset="card"
    title="运行试炼钻取"
    style="width: min(920px, 94vw)"
    :bordered="false"
    @update:show="emit('update:show', $event)"
    @after-enter="loadTeachers"
  >
    <div class="drill-head">
      <n-button v-if="step !== 'teachers'" size="small" quaternary @click="goBack">返回上一级</n-button>
      <p>
        <template v-if="step === 'teachers'">选择教师，查看其名下班级试炼</template>
        <template v-else-if="step === 'classes'">
          {{ selectedTeacher?.name }} · 选择班级
        </template>
        <template v-else>
          {{ selectedTeacher?.name }} / {{ selectedClass?.name }} · 试炼作答情况
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
          <em>{{ teacher.running_trials }} 场运行中 · 共 {{ teacher.total_trials }} 场 · {{ teacher.class_count }} 个班</em>
        </button>
        <p v-if="!teachers.length" class="drill-empty">暂无教师数据</p>
      </div>

      <div v-else-if="step === 'classes'" class="drill-grid">
        <button
          v-for="cls in classes"
          :key="cls.id"
          type="button"
          class="drill-card"
          @click="openClass(cls)"
        >
          <strong>{{ cls.name }}</strong>
          <span>{{ cls.student_count }} 名学生 · {{ cls.trial_count }} 场试炼</span>
          <em>运行中 {{ cls.running_trials }} · 完成率 {{ cls.completion_rate }}% · 均分 {{ cls.avg_score }}</em>
        </button>
        <p v-if="!classes.length" class="drill-empty">该教师暂无班级</p>
      </div>

      <div v-else-if="stats" class="drill-trials">
        <article v-for="trial in stats.trials" :key="trial.id" class="trial-block">
          <header>
            <div>
              <strong>{{ trial.title }}</strong>
              <small>{{ trial.status }} · 参与 {{ trial.participant_count }} · 完成率 {{ trial.completion_rate }}% · 均分 {{ trial.avg_score }}</small>
            </div>
          </header>
          <section>
            <h4>题目正确率</h4>
            <ul>
              <li v-for="q in trial.question_stats" :key="q.question_id">
                <span>{{ q.label }}</span>
                <em>{{ q.correct_rate }}%（{{ q.correct }}/{{ q.total }}）</em>
              </li>
              <li v-if="!trial.question_stats.length">暂无作答明细</li>
            </ul>
          </section>
          <section>
            <h4>学生进度</h4>
            <ul>
              <li v-for="stu in trial.student_progress" :key="stu.user_id">
                <span>{{ stu.name }}</span>
                <em>答题 {{ stu.answered }} · 得分 {{ stu.score }} · {{ stu.status }}</em>
              </li>
              <li v-if="!trial.student_progress.length">暂无学生进度</li>
            </ul>
          </section>
        </article>
        <p v-if="!stats.trials.length" class="drill-empty">该班级暂无试炼</p>
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

.drill-trials {
  display: grid;
  gap: 0.85rem;
  max-height: 60vh;
  overflow: auto;
}

.trial-block {
  padding: 0.9rem 1rem;
  border-radius: 12px;
  border: 1px solid rgba(167, 139, 250, 0.22);
  background: rgba(20, 14, 40, 0.7);
}

.trial-block header small,
.trial-block li em {
  color: rgba(196, 181, 253, 0.72);
}

.trial-block h4 {
  margin: 0.75rem 0 0.4rem;
  font-size: 0.86rem;
}

.trial-block ul {
  margin: 0;
  padding: 0;
  list-style: none;
}

.trial-block li {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.28rem 0;
  font-size: 0.84rem;
}
</style>
