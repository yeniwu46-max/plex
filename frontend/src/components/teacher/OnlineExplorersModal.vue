<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { NButton, NEmpty, NModal, NSpin } from 'naive-ui'
import { fetchOnlineStudents, type OnlineStudentItem } from '../../api/teacherPresence'

const props = defineProps<{
  show: boolean
  classId?: number | null
  className?: string | null
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
}>()

const loading = ref(false)
const students = ref<OnlineStudentItem[]>([])
const updatedAt = ref('')
const source = ref('empty')
const errorText = ref('')

const sourceHint = computed(() =>
  source.value === 'class_roster'
    ? '暂无实时在线状态，当前展示班级成员名单'
    : '当前暂无在线学员，可点击刷新',
)

async function load() {
  loading.value = true
  errorText.value = ''
  try {
    const result = await fetchOnlineStudents(props.classId)
    students.value = result.students
    updatedAt.value = result.updated_at
    source.value = (result as { source?: string }).source || 'heartbeat'
  } catch (error) {
    errorText.value = error instanceof Error ? error.message : '加载失败'
    students.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => props.show,
  (open) => {
    if (open) void load()
  },
)

function displayName(student: OnlineStudentItem) {
  return student.real_name || student.username || `学员 #${student.id}`
}
</script>

<template>
  <n-modal
    :show="show"
    preset="card"
    title="活跃 Explorer · 实时在线"
    class="online-modal"
    :bordered="false"
    style="width: min(520px, calc(100vw - 32px))"
    @update:show="emit('update:show', $event)"
  >
    <header class="online-modal__toolbar">
      <p>
        {{ className || '当前班级' }}
        <template v-if="updatedAt"> · 更新于 {{ updatedAt.replace('T', ' ').slice(0, 19) }}</template>
      </p>
      <n-button size="small" secondary :loading="loading" @click="load">刷新</n-button>
    </header>

    <div v-if="loading && !students.length" class="online-modal__state">
      <n-spin size="small" />
      <span>正在同步在线名单…</span>
    </div>
    <p v-else-if="errorText" class="online-modal__error">{{ errorText }}</p>
    <n-empty
      v-else-if="!students.length"
      :description="sourceHint"
    />
    <ul v-else class="online-modal__list">
      <li v-for="student in students" :key="student.id">
        <span class="online-modal__avatar">{{ displayName(student).slice(0, 1) }}</span>
        <div>
          <strong>{{ displayName(student) }}</strong>
          <small>
            学号/账号 {{ student.student_no || student.username || '—' }}
            <template v-if="student.last_seen_at">
              · {{ student.last_seen_at.replace('T', ' ').slice(11, 19) }}
            </template>
          </small>
        </div>
        <em>{{ source === 'heartbeat' ? '在线' : '班级成员' }}</em>
      </li>
    </ul>
  </n-modal>
</template>

<style scoped>
.online-modal__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.85rem;
}

.online-modal__toolbar p {
  margin: 0;
  color: rgba(214, 230, 244, 0.72);
  font-size: 0.84rem;
}

.online-modal__state,
.online-modal__error {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  color: rgba(214, 230, 244, 0.78);
}

.online-modal__error {
  color: #ff9da5;
}

.online-modal__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.55rem;
  max-height: min(52vh, 420px);
  overflow: auto;
}

.online-modal__list li {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 0.75rem;
  align-items: center;
  padding: 0.7rem 0.8rem;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 12px;
  background: rgba(4, 14, 24, 0.55);
}

.online-modal__avatar {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: rgba(251, 146, 60, 0.2);
  color: #fdba74;
  font-weight: 700;
}

.online-modal__list strong {
  display: block;
  color: #fff7ed;
}

.online-modal__list small {
  color: rgba(214, 230, 244, 0.62);
  font-size: 0.78rem;
}

.online-modal__list em {
  font-style: normal;
  color: #34d399;
  font-size: 0.78rem;
}
</style>
