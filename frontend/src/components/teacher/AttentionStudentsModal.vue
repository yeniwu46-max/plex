<script setup lang="ts">
import { computed } from 'vue'
import { NEmpty, NModal, NTag } from 'naive-ui'

export interface AttentionStudentListItem {
  id: number
  username?: string | null
  real_name?: string | null
  class_name?: string | null
  reasons?: string[]
  risk?: string
  learning_index?: number | null
  level_label?: string | null
  weak_domain?: string | null
}

const props = withDefaults(
  defineProps<{
    show: boolean
    students: AttentionStudentListItem[]
    className?: string | null
    title?: string
  }>(),
  {
    className: null,
    title: '需跟进学生',
  },
)

const emit = defineEmits<{
  'update:show': [value: boolean]
  select: [student: AttentionStudentListItem]
}>()

const visible = computed({
  get: () => props.show,
  set: (value: boolean) => emit('update:show', value),
})

function displayName(student: AttentionStudentListItem) {
  return student.real_name || student.username || `学员 #${student.id}`
}

function reasonText(student: AttentionStudentListItem) {
  if (student.reasons?.length) return student.reasons.join(' · ')
  if (student.weak_domain) return `薄弱：${student.weak_domain}`
  if (student.level_label) return student.level_label
  return '近期表现偏弱，建议跟进'
}

function riskType(risk?: string): 'error' | 'warning' | 'default' {
  if (risk?.includes('高')) return 'error'
  if (risk?.includes('中')) return 'warning'
  return 'default'
}
</script>

<template>
  <n-modal
    v-model:show="visible"
    preset="card"
    :title="title"
    class="attention-modal"
    :bordered="false"
    :z-index="5200"
    style="width: min(560px, calc(100vw - 32px))"
  >
    <p class="attention-modal__hint">
      {{ className ? `${className} · ` : '' }}近期表现不佳，建议优先关注薄弱点与活跃度。
    </p>
    <n-empty v-if="!students.length" description="暂无需要跟进的学生" />
    <ul v-else class="attention-modal__list">
      <li v-for="student in students" :key="student.id">
        <button type="button" class="attention-modal__row" @click="emit('select', student)">
          <span class="attention-modal__avatar">{{ displayName(student).slice(0, 1) }}</span>
          <div class="attention-modal__body">
            <strong>{{ displayName(student) }}</strong>
            <small>
              {{ student.class_name || className || '未分班' }}
              <template v-if="student.username"> · {{ student.username }}</template>
            </small>
            <span>{{ reasonText(student) }}</span>
          </div>
          <n-tag v-if="student.risk" size="small" :type="riskType(student.risk)" :bordered="false">
            {{ student.risk }}
          </n-tag>
        </button>
      </li>
    </ul>
  </n-modal>
</template>

<style scoped>
.attention-modal__hint {
  margin: 0 0 0.85rem;
  color: rgba(255, 237, 213, 0.62);
  font-size: 0.84rem;
}

.attention-modal__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.55rem;
  max-height: min(58vh, 480px);
  overflow: auto;
}

.attention-modal__row {
  width: 100%;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 0.75rem;
  align-items: center;
  padding: 0.75rem 0.85rem;
  border: 1px solid rgba(251, 146, 60, 0.18);
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.55);
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.attention-modal__row:hover {
  border-color: rgba(251, 146, 60, 0.42);
  background: rgba(67, 20, 7, 0.28);
}

.attention-modal__avatar {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  border: 1px solid rgba(251, 146, 60, 0.35);
  background: linear-gradient(145deg, #4f1616, #ff8a7d);
  color: #0b1422;
  font-weight: 800;
}

.attention-modal__body {
  display: grid;
  gap: 0.18rem;
  min-width: 0;
}

.attention-modal__body strong {
  color: #fff7ed;
  font-size: 0.92rem;
}

.attention-modal__body small,
.attention-modal__body span {
  color: rgba(255, 237, 213, 0.62);
  font-size: 0.78rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attention-modal__body span {
  white-space: normal;
  line-height: 1.4;
}
</style>

<style>
.attention-modal.n-card {
  background: rgba(8, 14, 22, 0.98) !important;
  border: 1px solid rgba(251, 146, 60, 0.22) !important;
}

.attention-modal .n-card-header__main {
  color: #fff7ed !important;
}
</style>
