<script setup lang="ts">
import { computed } from 'vue'
import { NInput, NSelect, type SelectOption } from 'naive-ui'
import type { TeacherStudentRow } from '../../api/teacherOverview'
import { explorerDisplayId, studentStatusLabel } from '../../data/teacherExplorerProfile'

const props = defineProps<{
  students: TeacherStudentRow[]
  selectedId: number | null
  search: string
  statusFilter: string | null
  domainFilter: string | null
  sortBy: string
}>()

const emit = defineEmits<{
  'update:selectedId': [id: number]
  'update:search': [value: string]
  'update:statusFilter': [value: string | null]
  'update:domainFilter': [value: string | null]
  'update:sortBy': [value: string]
}>()

const statusOptions: SelectOption[] = [
  { label: '全部状态', value: 'all' },
  { label: '在线', value: 'online' },
  { label: '探索中', value: 'exploring' },
  { label: '需关注', value: 'attention' },
]

const domainOptions: SelectOption[] = [
  { label: '全部星域', value: 'all' },
  { label: '算法基础', value: 'algo' },
  { label: '数据结构', value: 'ds' },
  { label: '数据库', value: 'db' },
]

const sortOptions: SelectOption[] = [
  { label: '按最新活动', value: 'activity' },
  { label: '按积分', value: 'points' },
  { label: '按等级', value: 'level' },
]

const filteredStudents = computed(() => {
  let rows = [...props.students]
  const q = props.search.trim().toLowerCase()
  if (q) {
    rows = rows.filter(
      (s) =>
        (s.real_name || '').toLowerCase().includes(q) ||
        s.username.toLowerCase().includes(q) ||
        explorerDisplayId(s).toLowerCase().includes(q),
    )
  }
  if (props.statusFilter === 'attention') {
    rows = rows.filter((s) => (s.reasons?.length ?? 0) > 0 || s.is_inactive_7d)
  } else if (props.statusFilter === 'exploring') {
    rows = rows.filter((s) => (s.today_completion_rate ?? 0) > 0)
  } else if (props.statusFilter === 'online') {
    rows = rows.filter((s) => !s.is_inactive_7d && s.status === 'active')
  }
  if (props.sortBy === 'points') {
    rows.sort((a, b) => (b.total_points ?? 0) - (a.total_points ?? 0))
  } else if (props.sortBy === 'level') {
    rows.sort((a, b) => (b.level ?? 0) - (a.level ?? 0))
  } else {
    rows.sort((a, b) => {
      const ta = a.last_activity_at ? new Date(a.last_activity_at).getTime() : 0
      const tb = b.last_activity_at ? new Date(b.last_activity_at).getTime() : 0
      return tb - ta
    })
  }
  return rows
})

const avatarTones = ['orange', 'teal', 'amber', 'red', 'gold'] as const

function selectStudent(id: number) {
  emit('update:selectedId', id)
}
</script>

<template>
  <section class="list-panel teacher-panel" aria-label="Explorer 列表">
    <div class="list-panel__tabs">
      <button type="button" class="is-active">Explorer 列表</button>
    </div>

    <n-input
      :value="search"
      placeholder="搜索 Explorer 名称 / ID"
      class="list-panel__search"
      @update:value="emit('update:search', $event)"
    />

    <div class="list-panel__filters">
      <n-select
        :value="statusFilter ?? 'all'"
        :options="statusOptions"
        size="small"
        @update:value="emit('update:statusFilter', $event === 'all' ? null : String($event))"
      />
      <n-select
        :value="domainFilter ?? 'all'"
        :options="domainOptions"
        size="small"
        @update:value="emit('update:domainFilter', $event === 'all' ? null : String($event))"
      />
      <n-select :value="sortBy" :options="sortOptions" size="small" @update:value="emit('update:sortBy', String($event))" />
    </div>

    <ul class="list-panel__list">
      <li v-for="(student, index) in filteredStudents" :key="student.id">
        <button
          type="button"
          class="explorer-card"
          :class="{ 'explorer-card--active': student.id === selectedId }"
          @click="selectStudent(student.id)"
        >
          <span class="explorer-card__avatar" :class="`explorer-card__avatar--${avatarTones[index % avatarTones.length]}`">
            {{ (student.real_name || student.username || '?').slice(0, 1) }}
          </span>
          <span class="explorer-card__body">
            <strong>{{ student.real_name || student.username }}</strong>
            <small>{{ explorerDisplayId(student) }} · Lv.{{ student.level }}</small>
          </span>
          <span class="explorer-card__status" :class="{ 'is-warn': student.reasons?.length }">
            {{ studentStatusLabel(student) }}
          </span>
        </button>
      </li>
      <li v-if="!filteredStudents.length" class="list-panel__empty">暂无匹配的 Explorer</li>
    </ul>
  </section>
</template>

<style scoped>
.list-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  padding: 1rem;
}

.list-panel__tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.85rem;
}

.list-panel__tabs button {
  flex: 1;
  padding: 0.55rem 0.75rem;
  border: 1px solid rgba(130, 212, 255, 0.1);
  border-radius: 10px;
  background: rgba(4, 12, 20, 0.5);
  color: var(--teacher-muted);
  cursor: pointer;
  font-size: 0.82rem;
}

.list-panel__tabs .is-active {
  border-color: rgba(251, 146, 60, 0.45);
  color: var(--teacher-text);
  background: rgba(251, 146, 60, 0.12);
}

.list-panel__tabs .is-disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.list-panel__search {
  margin-bottom: 0.75rem;
}

.list-panel__filters {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.45rem;
  margin-bottom: 0.85rem;
}

.list-panel__list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1;
}

.explorer-card {
  display: grid;
  grid-template-columns: 48px 1fr auto;
  gap: 0.65rem;
  align-items: center;
  width: 100%;
  padding: 0.65rem 0.75rem;
  border: 1px solid rgba(130, 212, 255, 0.1);
  border-radius: 12px;
  background: rgba(4, 12, 20, 0.45);
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.explorer-card--active {
  border-color: rgba(251, 146, 60, 0.55);
  box-shadow: 0 0 24px rgba(251, 146, 60, 0.12);
}

.explorer-card__avatar {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.35);
  font-weight: 800;
  color: #0b1422;
  background: linear-gradient(145deg, #172034, #f8c59f);
}

.explorer-card__avatar--teal {
  background: linear-gradient(145deg, #124e4b, #8cffef);
}

.explorer-card__avatar--red {
  background: linear-gradient(145deg, #4f1616, #ff8a7d);
}

.explorer-card__avatar--amber,
.explorer-card__avatar--gold {
  background: linear-gradient(145deg, #613f10, #ffd68a);
}

.explorer-card__body strong {
  display: block;
  color: var(--teacher-text);
  font-size: 0.9rem;
}

.explorer-card__body small {
  color: var(--teacher-muted);
  font-size: 0.72rem;
}

.explorer-card__status {
  font-size: 0.72rem;
  font-weight: 700;
  color: #34d399;
}

.explorer-card__status.is-warn {
  color: var(--teacher-orange);
}

.list-panel__empty {
  padding: 2rem 1rem;
  text-align: center;
  color: var(--teacher-muted);
  font-size: 0.88rem;
}
</style>
