<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { NDrawer, NDrawerContent, NButton } from 'naive-ui'
import type { TeacherStudentRow } from '../../api/teacherOverview'
import type { OrbitNode } from '../../data/teacherStarfield'
import { TEACHER_KNOWLEDGE_UNIVERSE } from '../../data/teacherKnowledgeCatalog'

const props = defineProps<{
  show: boolean
  node: OrbitNode | null
  classAvgScore: number
  attentionStudents: TeacherStudentRow[]
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
}>()

const router = useRouter()

const deltaLabel = computed(() => {
  if (!props.node) return ''
  if (props.node.delta === '上升') return '较上周上升'
  if (props.node.delta === '下降') return '较上周下降'
  return '整体稳定'
})

const comparedToClass = computed(() => {
  if (!props.node) return ''
  const diff = props.node.score - props.classAvgScore
  if (diff >= 5) return `高于班级均值 ${diff}%`
  if (diff <= -5) return `低于班级均值 ${Math.abs(diff)}%`
  return '与班级均值接近'
})

const domainKnowledgePoints = computed(() => {
  if (!props.node?.domainKey) return []
  return TEACHER_KNOWLEDGE_UNIVERSE.find((d) => d.key === props.node?.domainKey)?.points ?? []
})

function close() {
  emit('update:show', false)
}

function goExplorer(studentId: number) {
  close()
  void router.push({ path: '/teacher/explorers', query: { studentId: String(studentId) } })
}
</script>

<template>
  <n-drawer :show="show" :width="400" placement="right" @update:show="emit('update:show', $event)">
    <n-drawer-content v-if="node" :title="node.label" closable>
      <p class="domain-drawer__note">
        星域为教学视图分组，掌握分为基于班级委托与活跃数据的推演值，非课表知识点成绩。
      </p>

      <dl class="domain-drawer__stats">
        <div>
          <dt>掌握分</dt>
          <dd>{{ node.score }}%</dd>
        </div>
        <div>
          <dt>趋势</dt>
          <dd>{{ deltaLabel }}</dd>
        </div>
        <div>
          <dt>班级对比</dt>
          <dd>{{ comparedToClass }}</dd>
        </div>
        <div>
          <dt>班级均值</dt>
          <dd>{{ classAvgScore }}%</dd>
        </div>
      </dl>

      <section v-if="domainKnowledgePoints.length" class="domain-drawer__knowledge">
        <h3>知识宇宙 · 本域知识点</h3>
        <ul>
          <li v-for="point in domainKnowledgePoints" :key="point.key">{{ point.label }}</li>
        </ul>
      </section>

      <section class="domain-drawer__attention">
        <h3>需关注 Explorer</h3>
        <ul v-if="attentionStudents.length">
          <li v-for="student in attentionStudents" :key="student.id">
            <button type="button" @click="goExplorer(student.id)">
              <strong>{{ student.real_name || student.username }}</strong>
              <span v-if="student.reasons?.length">{{ student.reasons.join(' · ') }}</span>
              <span v-else>今日完成率 {{ student.today_completion_rate ?? 0 }}%</span>
            </button>
          </li>
        </ul>
        <p v-else class="domain-drawer__empty">该星域暂无高风险学生，班级整体稳定。</p>
      </section>

      <n-button v-if="attentionStudents[0]" type="primary" block class="domain-drawer__cta" @click="goExplorer(attentionStudents[0].id)">
        在 Explorer 档案中查看
      </n-button>
    </n-drawer-content>
  </n-drawer>
</template>

<style scoped>
.domain-drawer__knowledge {
  margin: 0 0 1.1rem;
}

.domain-drawer__knowledge h3,
.domain-drawer__attention h3 {
  margin: 0 0 0.55rem;
  color: #fff7ed;
  font-size: 0.88rem;
}

.domain-drawer__knowledge ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.domain-drawer__knowledge li {
  padding: 0.28rem 0.55rem;
  border-radius: 0.35rem;
  border: 1px solid rgba(251, 146, 60, 0.22);
  background: rgba(15, 23, 42, 0.55);
  color: rgba(255, 237, 213, 0.88);
  font-size: 0.78rem;
}

.domain-drawer__note {
  margin: 0 0 1rem;
  padding: 0.65rem 0.75rem;
  border-radius: 10px;
  background: rgba(251, 146, 60, 0.1);
  color: rgba(255, 237, 213, 0.82);
  font-size: 0.78rem;
  line-height: 1.45;
}

.domain-drawer__stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  margin: 0 0 1.25rem;
}

.domain-drawer__stats div {
  padding: 0.65rem 0.75rem;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
}

.domain-drawer__stats dt {
  margin: 0;
  color: rgba(221, 230, 239, 0.62);
  font-size: 0.72rem;
}

.domain-drawer__stats dd {
  margin: 0.25rem 0 0;
  color: #fff7ed;
  font-size: 1rem;
  font-weight: 650;
}

.domain-drawer__attention h3 {
  margin: 0 0 0.65rem;
  color: #fff7ed;
  font-size: 0.92rem;
}

.domain-drawer__attention ul {
  margin: 0;
  padding: 0;
  list-style: none;
}

.domain-drawer__attention button {
  display: grid;
  gap: 0.2rem;
  width: 100%;
  padding: 0.55rem 0;
  border: none;
  border-bottom: 1px solid rgba(219, 235, 249, 0.08);
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.domain-drawer__attention button:hover strong {
  color: #fb923c;
}

.domain-drawer__attention strong {
  color: #fff7ed;
  font-size: 0.88rem;
}

.domain-drawer__attention span {
  color: rgba(221, 230, 239, 0.62);
  font-size: 0.76rem;
}

.domain-drawer__empty {
  margin: 0;
  color: rgba(221, 230, 239, 0.62);
  font-size: 0.85rem;
}

.domain-drawer__cta {
  margin-top: 1.25rem;
}
</style>
