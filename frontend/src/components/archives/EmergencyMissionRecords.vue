<script setup lang="ts">
import { computed, ref } from 'vue'
import type { EmergencyMissionArchiveRecord } from '../../api/emergencyMission'

const props = defineProps<{
  records: EmergencyMissionArchiveRecord[]
}>()

const expandedId = ref<number | null>(null)

const groupedRecords = computed(() => {
  const groups = new Map<string, EmergencyMissionArchiveRecord[]>()
  for (const record of props.records) {
    const day = record.date?.slice(0, 10) ?? '未记录日期'
    const label = `${day} · ${record.focus_label}`
    const list = groups.get(label) ?? []
    list.push(record)
    groups.set(label, list)
  }
  return Array.from(groups, ([label, items]) => ({ label, items }))
})

function isExpanded(record: EmergencyMissionArchiveRecord) {
  return expandedId.value === record.id
}

function toggleRecord(record: EmergencyMissionArchiveRecord) {
  expandedId.value = isExpanded(record) ? null : record.id
}
</script>

<template>
  <section class="card emergency-log" aria-label="紧急任务记录">
    <h2 class="card__title">补给站紧急任务</h2>
    <p v-if="!records.length" class="emergency-log__empty">暂无记录。在探索舱「边界条件补给站」完成紧急任务后会显示在这里。</p>
    <ul v-else class="emergency-log__list">
      <li v-for="group in groupedRecords" :key="group.label" class="emergency-log__group">
        <h3>{{ group.label }}</h3>
        <article v-for="record in group.items" :key="record.id" class="emergency-log__item">
          <div class="emergency-log__head">
            <strong>{{ record.title }}</strong>
            <span :class="record.all_correct ? 'tag tag--ok' : 'tag tag--miss'">
              {{ record.all_correct ? '全对' : `${record.correct_count}/${record.total_count}` }}
            </span>
          </div>
          <p class="emergency-log__meta">
            {{ record.date?.slice(0, 10) ?? '—' }}
            <template v-if="record.reward_points"> · +{{ record.reward_points }} XP</template>
          </p>
          <button
            type="button"
            class="emergency-log__toggle"
            :aria-expanded="isExpanded(record)"
            @click="toggleRecord(record)"
          >
            {{ isExpanded(record) ? '收起作答与解析' : '查看作答与解析' }}
          </button>
          <div v-if="isExpanded(record)" class="emergency-log__details">
            <div v-for="q in record.questions" :key="q.id" class="emergency-log__q">
              <p class="emergency-log__stem">{{ q.sort_order }}. {{ q.stem }}</p>
              <p class="emergency-log__ans">
                你的选择：{{ q.selected_index !== null ? String.fromCharCode(65 + q.selected_index) : '—' }}
                · 正确答案：{{ String.fromCharCode(65 + (q.correct_index ?? 0)) }}
                · {{ q.is_correct ? '正确' : '错误' }}
              </p>
            </div>
          </div>
        </article>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.card {
  border-radius: 1rem;
  border: 1px solid var(--plex-border);
  background: rgba(11, 22, 40, 0.72);
  backdrop-filter: blur(12px);
  padding: 1.65rem 1.5rem 1.5rem;
}

.card__title {
  margin: 0 0 1rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--plex-accent);
}

.emergency-log__empty {
  margin: 0;
  font-size: 0.85rem;
  color: rgba(142, 163, 184, 0.9);
  line-height: 1.5;
}

.emergency-log__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.emergency-log__group {
  padding: 0.85rem 0 0;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.emergency-log__group:first-child {
  border-top: none;
  padding-top: 0;
}

.emergency-log__group h3 {
  margin: 0 0 0.55rem;
  color: rgba(225, 238, 247, 0.72);
  font-size: 0.78rem;
  font-weight: 650;
}

.emergency-log__item {
  padding: 0.65rem 0;
}

.emergency-log__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}

.emergency-log__head strong {
  font-size: 0.88rem;
  color: rgba(255, 255, 255, 0.92);
}

.tag {
  font-size: 0.72rem;
  padding: 0.15rem 0.45rem;
  border-radius: 6px;
}

.tag--ok {
  background: rgba(16, 240, 192, 0.15);
  color: #10f0c0;
}

.tag--miss {
  background: rgba(232, 128, 128, 0.12);
  color: #e8a0a0;
}

.emergency-log__meta {
  margin: 0.35rem 0 0;
  font-size: 0.78rem;
  color: rgba(142, 163, 184, 0.95);
}

.emergency-log__toggle {
  display: inline-flex;
  margin-top: 0.5rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: rgba(16, 240, 192, 0.85);
  cursor: pointer;
  font-size: 0.8rem;
}

.emergency-log__details {
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: rgba(200, 220, 235, 0.9);
}

.emergency-log__q {
  margin-top: 0.45rem;
  padding-left: 0.25rem;
}

.emergency-log__stem {
  margin: 0;
  line-height: 1.4;
}

.emergency-log__ans {
  margin: 0.2rem 0 0;
  font-size: 0.76rem;
  color: rgba(142, 163, 184, 0.95);
}
</style>
