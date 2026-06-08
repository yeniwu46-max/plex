<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NIcon, NTag } from 'naive-ui'
import { BookOutline, CloudUploadOutline, GitNetworkOutline, LinkOutline, ServerOutline } from '@vicons/ionicons5'
import PlexFileUploader from '../shared/upload/PlexFileUploader.vue'
import { ADMIN_PRESETS } from '../../config/upload/uploadPresets'
import {
  KNOWLEDGE_POINT_BANK_MAP,
  KNOWLEDGE_PREREQUISITE_EDGES,
  KNOWLEDGE_SYNC_LOG,
} from '../../data/knowledgeGraphAdmin'
import { TEACHER_KNOWLEDGE_UNIVERSE } from '../../data/teacherKnowledgeCatalog'
import { STAR_PATH_DOMAINS } from '../../data/starPathDomains'
import PlexKnowledgeGraph from '../shared/PlexKnowledgeGraph.vue'
import { KG_NODES, KG_EDGES, type KgEdge, type KgNode } from '../../data/knowledgeGraphData'
import { fetchAdminKnowledgeGraph } from '../../api/knowledgeGraph'
import { fetchKbDocuments, fetchKbStatus, type KbDocument, type KbStatus } from '../../api/knowledgeBase'

const kgNodes = ref<KgNode[]>(KG_NODES)
const kgEdges = ref<KgEdge[]>(KG_EDGES)
const kbDocuments = ref<KbDocument[]>([])
const kbStatus = ref<KbStatus | null>(null)

onMounted(async () => {
  try {
    const [graph, docs, status] = await Promise.all([
      fetchAdminKnowledgeGraph(),
      fetchKbDocuments().catch(() => null),
      fetchKbStatus().catch(() => null),
    ])
    kgNodes.value = graph.nodes
    kgEdges.value = graph.edges
    if (docs) kbDocuments.value = docs.documents
    if (status) kbStatus.value = status
  } catch {
    /* keep static fallback */
  }
})

async function onKbDocUploaded() {
  try {
    const docs = await fetchKbDocuments()
    if (docs) kbDocuments.value = docs.documents
  } catch {
    /* ignore refresh errors */
  }
}

const trialPointCount = computed(() =>
  TEACHER_KNOWLEDGE_UNIVERSE.reduce((sum, domain) => sum + domain.points.length, 0),
)

const starPathPointCount = computed(() =>
  STAR_PATH_DOMAINS.reduce((sum, domain) => sum + domain.knowledgePoints.length, 0),
)

const bankBindings = computed(() =>
  TEACHER_KNOWLEDGE_UNIVERSE.flatMap((domain) =>
    domain.points.map((point) => ({
      domain: domain.label,
      point: point.label,
      bank: KNOWLEDGE_POINT_BANK_MAP[point.key] ?? '通用题库',
    })),
  ),
)

const levelTone: Record<string, 'success' | 'warning' | 'error'> = {
  入门: 'success',
  进阶: 'warning',
  挑战: 'error',
}

const syncTone: Record<string, 'success' | 'warning' | 'default'> = {
  完成: 'success',
  进行中: 'warning',
  待审核: 'default',
}
</script>

<template>
  <section class="knowledge-layout" aria-label="知识图谱面板">
    <article class="panel section-panel">
      <header class="section-head">
        <n-icon :component="BookOutline" />
        <div>
          <h2>试炼知识宇宙</h2>
          <p>教师发布试炼时可选的知识点目录，共 {{ trialPointCount }} 个节点 · {{ TEACHER_KNOWLEDGE_UNIVERSE.length }} 大学域</p>
        </div>
      </header>
      <div class="domain-grid">
        <section v-for="domain in TEACHER_KNOWLEDGE_UNIVERSE" :key="domain.key" class="domain-card">
          <header class="domain-head">
            <strong>{{ domain.label }}</strong>
            <em>{{ domain.points.length }} 节点</em>
          </header>
          <ul class="point-list">
            <li v-for="point in domain.points" :key="point.key">
              <span>{{ point.label }}</span>
              <code>{{ point.key }}</code>
            </li>
          </ul>
        </section>
      </div>
    </article>

    <article class="panel section-panel">
      <header class="section-head">
        <n-icon :component="GitNetworkOutline" />
        <div>
          <h2>计算思维知识图谱</h2>
          <p>基于 AntV G6 的可视化知识图谱，支持点击查看节点详情与学习路径推荐</p>
        </div>
      </header>
      <plex-knowledge-graph :nodes="kgNodes" :edges="kgEdges" mode="admin" height="480px" />
    </article>

    <article v-if="kbStatus" class="panel section-panel kb-status-panel">
      <header class="section-head">
        <n-icon :component="ServerOutline" />
        <div>
          <h2>RAG 知识库服务</h2>
          <p>
            后端 {{ kbStatus.backend }} · 已索引 {{ kbStatus.indexed_documents }}/{{ kbStatus.total_documents }} 文档 ·
            {{ kbStatus.total_chunks }} 切块
          </p>
        </div>
      </header>
      <ul v-if="kbDocuments.length" class="kb-doc-list">
        <li v-for="doc in kbDocuments" :key="doc.id">
          <strong>{{ doc.name }}</strong>
          <span>{{ doc.status }}</span>
          <em>{{ doc.chunk_count }} chunks</em>
        </li>
      </ul>
    </article>

    <!-- 管理员资料上传 -->
    <article class="panel section-panel">
      <header class="section-head">
        <n-icon :component="CloudUploadOutline" />
        <div>
          <h2>资料上传中心</h2>
          <p>上传知识库文档、系统配置与图谱数据，为平台提供结构化数据入口</p>
        </div>
      </header>
      <div class="admin-upload-grid">
        <div class="admin-upload-card">
          <plex-file-uploader
            role="admin"
            v-bind="ADMIN_PRESETS.knowledgeDoc"
            @upload-success="onKbDocUploaded"
          />
        </div>
        <div class="admin-upload-card">
          <plex-file-uploader
            role="admin"
            v-bind="ADMIN_PRESETS.systemConfig"
          />
        </div>
        <div class="admin-upload-card">
          <plex-file-uploader
            role="admin"
            v-bind="ADMIN_PRESETS.graphData"
          />
        </div>
      </div>
    </article>

    <article class="panel section-panel">
      <header class="section-head">
        <n-icon :component="GitNetworkOutline" />
        <div>
          <h2>星轨学域图谱</h2>
          <p>学生星轨路径导航中的学域与知识点，共 {{ starPathPointCount }} 个节点 · {{ STAR_PATH_DOMAINS.length }} 大学域</p>
        </div>
      </header>
      <div class="starpath-grid">
        <section v-for="domain in STAR_PATH_DOMAINS" :key="domain.key" class="starpath-card">
          <header class="starpath-head">
            <div>
              <strong>{{ domain.title }}</strong>
              <small>{{ domain.focus }}</small>
            </div>
            <em>{{ domain.knowledgePoints.length }} 节点</em>
          </header>
          <p class="starpath-desc">{{ domain.description }}</p>
          <ul class="kp-list">
            <li v-for="kp in domain.knowledgePoints" :key="kp.id">
              <div class="kp-title">
                <span>{{ kp.title }}</span>
                <n-tag size="small" :type="levelTone[kp.level]">{{ kp.level }}</n-tag>
              </div>
              <small>{{ kp.summary }}</small>
              <div class="kp-tags">
                <n-tag v-for="tag in kp.tags" :key="tag" size="tiny" :bordered="false">{{ tag }}</n-tag>
              </div>
            </li>
          </ul>
        </section>
      </div>
    </article>

    <div class="knowledge-bottom-row">
      <article class="panel side-panel">
        <header class="section-head section-head--compact">
          <n-icon :component="LinkOutline" />
          <div>
            <h2>知识点前置关系</h2>
            <p>共 {{ KNOWLEDGE_PREREQUISITE_EDGES.length }} 条关联边</p>
          </div>
        </header>
        <ul class="relation-list">
          <li v-for="(edge, index) in KNOWLEDGE_PREREQUISITE_EDGES" :key="`${edge.from}-${edge.to}-${index}`">
            <span class="relation-from">{{ edge.from }}</span>
            <em>{{ edge.relation }}</em>
            <span class="relation-to">{{ edge.to }}</span>
          </li>
        </ul>
      </article>

      <article class="panel side-panel">
        <header class="section-head section-head--compact">
          <n-icon :component="ServerOutline" />
          <div>
            <h2>题库绑定映射</h2>
            <p>试炼知识点 → 出题题库</p>
          </div>
        </header>
        <ul class="bank-list">
          <li v-for="item in bankBindings" :key="item.point">
            <div>
              <strong>{{ item.point }}</strong>
              <small>{{ item.domain }}</small>
            </div>
            <n-tag size="small" :bordered="false">{{ item.bank }}</n-tag>
          </li>
        </ul>
      </article>

      <article class="panel side-panel">
        <header class="section-head section-head--compact">
          <n-icon :component="GitNetworkOutline" />
          <div>
            <h2>同步与维护日志</h2>
            <p>近期图谱变更记录</p>
          </div>
        </header>
        <ul class="sync-list">
          <li v-for="item in KNOWLEDGE_SYNC_LOG" :key="`${item.time}-${item.target}`">
            <time>{{ item.time }}</time>
            <div>
              <strong>{{ item.action }}</strong>
              <small>{{ item.target }}</small>
            </div>
            <n-tag size="small" :type="syncTone[item.status]">{{ item.status }}</n-tag>
          </li>
        </ul>
      </article>
    </div>
  </section>
</template>

<style scoped>
.knowledge-layout {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1.05rem;
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.panel {
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 9px;
  background:
    radial-gradient(circle at 50% 0%, rgba(139, 92, 246, 0.11), transparent 42%),
    linear-gradient(145deg, rgba(19, 20, 43, 0.88), rgba(8, 11, 26, 0.82));
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.04), 0 18px 50px rgba(0, 0, 0, 0.22);
  min-width: 0;
  padding: 1.15rem 1.25rem;
}

.section-head {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 0.65rem;
  align-items: start;
  margin-bottom: 1rem;
  color: #c4b5fd;
  font-size: 1.35rem;
}

.section-head--compact {
  margin-bottom: 0.85rem;
}

.section-head h2 {
  margin: 0;
  color: #fff;
  font-size: 1.05rem;
}

.section-head p {
  margin: 0.3rem 0 0;
  color: rgba(226, 232, 240, 0.58);
  font-size: 0.76rem;
}

.domain-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
}

.domain-card {
  padding: 0.75rem 0.85rem;
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 8px;
  background: rgba(8, 10, 24, 0.45);
}

.domain-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.55rem;
  padding-bottom: 0.45rem;
  border-bottom: 1px solid rgba(167, 139, 250, 0.1);
}

.domain-head strong {
  color: rgba(255, 255, 255, 0.92);
  font-size: 0.88rem;
}

.domain-head em {
  color: rgba(167, 139, 250, 0.75);
  font-size: 0.72rem;
  font-style: normal;
}

.point-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.4rem;
}

.point-list li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  color: rgba(226, 232, 240, 0.78);
  font-size: 0.8rem;
}

.point-list code {
  flex-shrink: 0;
  color: rgba(167, 139, 250, 0.6);
  font-size: 0.65rem;
}

.starpath-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.starpath-card {
  padding: 0.85rem;
  border: 1px solid rgba(167, 139, 250, 0.12);
  border-radius: 8px;
  background: rgba(8, 10, 24, 0.45);
}

.starpath-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.65rem;
  margin-bottom: 0.45rem;
}

.starpath-head strong {
  display: block;
  color: rgba(255, 255, 255, 0.92);
  font-size: 0.9rem;
}

.starpath-head small {
  display: block;
  margin-top: 0.2rem;
  color: rgba(167, 139, 250, 0.7);
  font-size: 0.72rem;
}

.starpath-head em {
  flex-shrink: 0;
  color: rgba(167, 139, 250, 0.75);
  font-size: 0.72rem;
  font-style: normal;
}

.starpath-desc {
  margin: 0 0 0.65rem;
  color: rgba(226, 232, 240, 0.58);
  font-size: 0.76rem;
  line-height: 1.45;
}

.kp-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.55rem;
}

.kp-list li {
  padding: 0.55rem 0.65rem;
  border-radius: 6px;
  background: rgba(12, 14, 32, 0.55);
  border: 1px solid rgba(167, 139, 250, 0.08);
}

.kp-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.kp-title span {
  color: rgba(255, 255, 255, 0.88);
  font-size: 0.82rem;
}

.kp-list small {
  display: block;
  color: rgba(226, 232, 240, 0.6);
  font-size: 0.74rem;
  line-height: 1.4;
}

.kp-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-top: 0.35rem;
}

.knowledge-bottom-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
  align-items: stretch;
}

.side-panel {
  display: flex;
  flex-direction: column;
  min-height: 280px;
}

.relation-list,
.bank-list,
.sync-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.45rem;
  flex: 1;
}

.relation-list li {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  gap: 0.4rem;
  align-items: center;
  padding: 0.45rem 0;
  border-bottom: 1px solid rgba(167, 139, 250, 0.08);
  font-size: 0.78rem;
}

.relation-list li:last-child {
  border-bottom: none;
}

.relation-from,
.relation-to {
  color: rgba(226, 232, 240, 0.78);
}

.relation-list em {
  color: #a78bfa;
  font-size: 0.68rem;
  font-style: normal;
  white-space: nowrap;
}

.bank-list li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.55rem;
  padding: 0.45rem 0;
  border-bottom: 1px solid rgba(167, 139, 250, 0.08);
}

.bank-list li:last-child {
  border-bottom: none;
}

.bank-list strong {
  display: block;
  color: rgba(255, 255, 255, 0.88);
  font-size: 0.8rem;
}

.bank-list small {
  display: block;
  margin-top: 0.15rem;
  color: rgba(226, 232, 240, 0.52);
  font-size: 0.7rem;
}

.sync-list li {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  gap: 0.45rem;
  align-items: start;
  padding: 0.45rem 0;
  border-bottom: 1px solid rgba(167, 139, 250, 0.08);
}

.sync-list li:last-child {
  border-bottom: none;
}

.sync-list time {
  color: rgba(167, 139, 250, 0.75);
  font-size: 0.72rem;
}

.sync-list strong {
  display: block;
  color: rgba(255, 255, 255, 0.88);
  font-size: 0.78rem;
}

.sync-list small {
  display: block;
  margin-top: 0.15rem;
  color: rgba(226, 232, 240, 0.55);
  font-size: 0.72rem;
  line-height: 1.35;
}

.kb-doc-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.5rem;
}

.kb-doc-list li {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 0.75rem;
  align-items: center;
  padding: 0.55rem 0.75rem;
  border-radius: 8px;
  background: rgba(129, 140, 248, 0.08);
  border: 1px solid rgba(129, 140, 248, 0.15);
  font-size: 0.82rem;
}

.kb-doc-list strong {
  color: rgba(255, 255, 255, 0.9);
}

.kb-doc-list span {
  color: #a5b4fc;
  text-transform: capitalize;
}

.kb-doc-list em {
  color: rgba(226, 232, 240, 0.55);
  font-style: normal;
  font-size: 0.75rem;
}

@media (max-width: 1280px) {
  .domain-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .starpath-grid,
  .knowledge-bottom-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .domain-grid {
    grid-template-columns: 1fr;
  }

  .relation-list li {
    grid-template-columns: 1fr;
    gap: 0.2rem;
  }
}

.admin-upload-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.85rem;
}

.admin-upload-card {
  padding: 1rem;
  border-radius: 10px;
  background: var(--plex-bg-elevated, var(--plex-bg-card));
  border: 1px solid var(--plex-border-subtle);
}

@media (max-width: 1280px) {
  .admin-upload-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .admin-upload-grid {
    grid-template-columns: 1fr;
  }
}
</style>
