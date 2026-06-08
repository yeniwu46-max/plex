<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import type { LearningReportResult } from '../../api/learningReport'
import type { UserAchievementRecord } from '../../api/studentOverview'
import PlexKnowledgeGraph from '../shared/PlexKnowledgeGraph.vue'
import { KG_NODES, KG_EDGES, type KgEdge, type KgNode } from '../../data/knowledgeGraphData'
import { fetchStudentKnowledgeGraphById } from '../../api/knowledgeGraph'

const props = defineProps<{
  loading: boolean
  error: string
  achievements: UserAchievementRecord[]
  report?: LearningReportResult | null
  reportLoading?: boolean
  reportError?: string
  studentId?: number | null
}>()

const kgNodes = ref<KgNode[]>(KG_NODES)
const kgEdges = ref<KgEdge[]>(KG_EDGES)
const kgLoading = ref(false)

async function loadGraph() {
  if (!props.studentId) return
  kgLoading.value = true
  try {
    const data = await fetchStudentKnowledgeGraphById(props.studentId)
    kgNodes.value = data.nodes
    kgEdges.value = data.edges
  } catch {
    kgNodes.value = KG_NODES
    kgEdges.value = KG_EDGES
  } finally {
    kgLoading.value = false
  }
}

onMounted(() => {
  void loadGraph()
})

watch(
  () => props.studentId,
  () => {
    void loadGraph()
  },
)

const rarityLabel: Record<string, string> = {
  common: '普通',
  rare: '稀有',
  epic: '史诗',
  legendary: '传说',
}
</script>

<template>
  <section class="explorer-knowledge" aria-label="知识掌握与成就">
    <div v-if="studentId" class="explorer-knowledge__graph">
      <h4>个人知识地图</h4>
      <p v-if="kgLoading" class="explorer-knowledge__state">正在加载知识图谱…</p>
      <plex-knowledge-graph v-else :nodes="kgNodes" :edges="kgEdges" mode="teacher" height="320px" />
    </div>

    <div v-if="reportLoading" class="explorer-knowledge__state">正在加载学情报告…</div>
    <div v-else-if="report" class="explorer-knowledge__report">
      <h4>学习评估（{{ report.period }}）</h4>
      <p>
        探索指数 <strong>{{ report.summary.index }}</strong> · {{ report.summary.level_label }}
        <span v-if="report.risk_tags.length"> · {{ report.risk_tags.join(' · ') }}</span>
      </p>
      <ul v-if="report.domain_mastery.length" class="explorer-knowledge__mastery">
        <li v-for="domain in report.domain_mastery" :key="domain.key">
          <span>{{ domain.label }}</span>
          <em>{{ domain.mastery_rate }}%</em>
          <small v-if="domain.delta">Δ {{ domain.delta > 0 ? '+' : '' }}{{ domain.delta }}</small>
        </li>
      </ul>
      <p v-if="report.mistake_highlights.length" class="explorer-knowledge__mistakes">
        活跃错题 {{ report.mistake_highlights.length }} 条
      </p>
    </div>
    <p v-else-if="reportError" class="explorer-knowledge__state explorer-knowledge__state--error">
      {{ reportError }}
    </p>

    <div v-if="loading" class="explorer-knowledge__state">正在加载成就数据…</div>
    <div v-else-if="error" class="explorer-knowledge__state explorer-knowledge__state--error">{{ error }}</div>
    <ul v-else-if="achievements.length" class="explorer-knowledge__list">
      <li v-for="item in achievements" :key="item.id">
        <span class="explorer-knowledge__badge" aria-hidden="true">🏅</span>
        <div>
          <strong>{{ item.achievement?.name ?? '未命名成就' }}</strong>
          <p>{{ item.achievement?.description || '暂无描述' }}</p>
          <small>
            {{ rarityLabel[item.achievement?.rarity ?? 'common'] ?? item.achievement?.rarity }}
            <template v-if="item.unlocked_at"> · {{ item.unlocked_at.slice(0, 10) }}</template>
          </small>
        </div>
      </li>
    </ul>
    <p v-else class="explorer-knowledge__state">该 Explorer 尚未解锁成就勋章。</p>
  </section>
</template>

<style scoped>
.explorer-knowledge__graph {
  margin-bottom: 1rem;
}

.explorer-knowledge__graph h4 {
  margin: 0 0 0.5rem;
  font-size: 0.9rem;
  color: var(--teacher-text);
}

.explorer-knowledge__state {
  margin: 0;
  padding: 1.5rem 0;
  color: var(--teacher-muted);
  font-size: 0.9rem;
  text-align: center;
}

.explorer-knowledge__state--error {
  color: #fecaca;
}

.explorer-knowledge__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.65rem;
  max-height: 320px;
  overflow: auto;
}

.explorer-knowledge__list li {
  display: flex;
  gap: 0.75rem;
  padding: 0.65rem 0.75rem;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(219, 235, 249, 0.08);
}

.explorer-knowledge__badge {
  font-size: 1.5rem;
  line-height: 1;
}

.explorer-knowledge__list strong {
  color: var(--teacher-text);
  font-size: 0.9rem;
}

.explorer-knowledge__report {
  margin-bottom: 1rem;
  padding: 0.85rem 1rem;
  border-radius: 12px;
  background: rgba(251, 146, 60, 0.08);
  border: 1px solid rgba(251, 146, 60, 0.2);
}

.explorer-knowledge__report h4 {
  margin: 0 0 0.5rem;
  font-size: 0.9rem;
  color: var(--teacher-text);
}

.explorer-knowledge__report p {
  margin: 0 0 0.65rem;
  font-size: 0.85rem;
  color: var(--teacher-muted);
}

.explorer-knowledge__mastery {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.35rem;
  font-size: 0.82rem;
}

.explorer-knowledge__mastery li {
  display: flex;
  gap: 0.5rem;
  align-items: baseline;
}

.explorer-knowledge__mastery em {
  color: #fdba74;
  font-style: normal;
}

.explorer-knowledge__mistakes {
  margin: 0.5rem 0 0;
  font-size: 0.8rem;
  color: #fecaca;
}

.explorer-knowledge__list p {
  margin: 0.2rem 0 0;
  color: var(--teacher-muted);
  font-size: 0.8rem;
  line-height: 1.4;
}

.explorer-knowledge__list small {
  color: var(--teacher-orange);
  font-size: 0.72rem;
}
</style>
