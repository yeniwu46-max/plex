<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  NButton,
  NCollapse,
  NCollapseItem,
  NEmpty,
  NIcon,
  NInput,
  NModal,
  NProgress,
  NTag,
  useMessage,
} from 'naive-ui'
import { SparklesOutline } from '@vicons/ionicons5'
import TeacherDashboardShell from '../components/layout/TeacherDashboardShell.vue'
import PersonalizedResourceContentViewer from '../components/personalized/PersonalizedResourceContentViewer.vue'
import {
  DIMENSION_LABELS,
  fetchResourceAudit,
  fetchResourceReviewMetrics,
  fetchReviewResources,
  rerunResourceAudit,
  reviewPersonalizedResource,
  runTeacherSmartReview,
  type AuditReport,
  type DimensionScores,
  type PersonalizedResource,
  type ResourceReviewMetrics,
} from '../api/personalizedResources'

defineOptions({ name: 'TeacherResourceReviewView' })

const message = useMessage()
const items = ref<PersonalizedResource[]>([])
const metrics = ref<ResourceReviewMetrics | null>(null)
const reasons = ref<Record<number, string>>({})
const auditReports = ref<Record<number, AuditReport>>({})
const auditLoading = ref<Record<number, boolean>>({})
const detailItem = ref<PersonalizedResource | null>(null)
const detailShow = ref(false)
const smartReviewLoading = ref(false)
const listFilter = ref<'anomaly' | 'all_pending'>('anomaly')

const riskReasonLabels: Record<string, string> = {
  low_confidence: '置信度偏低',
  scope_mismatch: '超出课程范围',
  missing_citation: '缺少知识库引用',
  code_quality: '代码质量存疑',
  factual_risk: '事实准确性风险',
  incomplete_content: '内容不完整',
  ai_anomaly: 'AI 判定异常',
  ai_reject: 'AI 建议驳回',
  safety_blocked: '内容安全拦截',
  schema_invalid: '结构校验提示',
  invalid_citation: '引用无效',
  out_of_scope: '超出课程范围',
  insufficient_exercises: '练习偏少',
  missing_answers: '答案不完整',
}

const typeLabels: Record<string, string> = {
  learning_bundle: '完整资源包',
  lesson_document: '讲解文档',
  mind_map: '思维导图',
  exercise_set: '分层题库',
  extended_reading: '拓展阅读',
  coding_lab: '代码实操',
  audio_explanation: '语音讲解',
  video_lesson: '教学短视频',
}

const verdictTagType: Record<string, 'success' | 'warning' | 'error'> = {
  PASS: 'success',
  NEED_MODIFY: 'warning',
  REJECT: 'error',
}

const reviewStatusLabels: Record<string, string> = {
  pending_review: '生成待审核',
  approved: '已批准',
  rejected: '已驳回',
  draft: '草稿',
}

const verdictLabels: Record<string, string> = {
  PASS: '通过',
  NEED_MODIFY: '需修改',
  REJECT: '驳回',
}

const levelLabels: Record<string, string> = {
  PASS: '通过',
  WARNING: '警告',
  FAIL: '未通过',
}

const levelTagType: Record<string, 'success' | 'warning' | 'error'> = {
  PASS: 'success',
  WARNING: 'warning',
  FAIL: 'error',
}

const pendingCards = computed(() => {
  const filtered =
    listFilter.value === 'anomaly' ? items.value.filter((item) => item.is_anomaly) : items.value
  return [...filtered].sort((a, b) => {
    if (a.is_anomaly !== b.is_anomaly) return a.is_anomaly ? -1 : 1
    return b.id - a.id
  })
})

const anomalyCount = computed(() => items.value.filter((item) => item.is_anomaly).length)

function bundleForTask(taskId: string) {
  return items.value.find(
    (item) => item.generation_task_id === taskId && item.resource_type === 'learning_bundle',
  )
}

async function load() {
  const [resources, reviewMetrics] = await Promise.all([
    fetchReviewResources(),
    fetchResourceReviewMetrics(),
  ])
  items.value = resources.items
  metrics.value = reviewMetrics
  if (listFilter.value === 'anomaly' && !anomalyCount.value && resources.items.length) {
    listFilter.value = 'all_pending'
  }
  await Promise.all(resources.items.map((item) => loadAudit(item.id)))
}

async function loadAudit(resourceId: number) {
  auditLoading.value[resourceId] = true
  try {
    const result = await fetchResourceAudit(resourceId)
    auditReports.value[resourceId] = result.audit_report
  } catch {
    // 旧资源可能尚无报告
  } finally {
    auditLoading.value[resourceId] = false
  }
}

async function rerunAudit(item: PersonalizedResource) {
  auditLoading.value[item.id] = true
  try {
    const result = await rerunResourceAudit(item.id)
    auditReports.value[item.id] = result.audit_report
    message.success('审核已重新执行')
  } catch (error) {
    message.error(error instanceof Error ? error.message : '重新审核失败')
  } finally {
    auditLoading.value[item.id] = false
  }
}

async function review(item: PersonalizedResource, status: 'approved' | 'rejected') {
  if (status === 'approved' && !reasons.value[item.id]?.trim()) {
    message.warning('批准资源前必须填写审核说明')
    return
  }
  try {
    await reviewPersonalizedResource(item.id, status, reasons.value[item.id] || '')
    message.success(status === 'approved' ? '资源已批准' : '资源已驳回')
    detailShow.value = false
    detailItem.value = null
    await load()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '审核失败')
  }
}

function openDetail(item: PersonalizedResource, event?: Event) {
  event?.preventDefault()
  event?.stopPropagation()
  detailItem.value = item
  detailShow.value = true
  if (!auditReports.value[item.id] && !auditLoading.value[item.id]) {
    void loadAudit(item.id)
  }
}

function closeDetail() {
  detailShow.value = false
  detailItem.value = null
}

function dimensionEntries(report: AuditReport) {
  return Object.entries(report.dimensions) as Array<[keyof DimensionScores, number]>
}

function formatRiskReason(reason: string) {
  return riskReasonLabels[reason] ?? reason.replace(/_/g, ' ')
}

function topRisks(item: PersonalizedResource, limit = 3) {
  return (item.risk_reasons || []).slice(0, limit)
}

async function runSmartReview() {
  if (!items.value.length || smartReviewLoading.value) return
  smartReviewLoading.value = true
  try {
    const result = await runTeacherSmartReview()
    message.success(
      `智能审核完成：自动通过 ${result.approved_count} 项，${result.flagged_count} 项异常待人工复核`,
    )
    listFilter.value = result.flagged_count > 0 ? 'anomaly' : 'all_pending'
    closeDetail()
    await load()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '智能审核失败')
  } finally {
    smartReviewLoading.value = false
  }
}

watch(detailShow, (open) => {
  if (!open) detailItem.value = null
})

onMounted(() => void load())
</script>

<template>
  <TeacherDashboardShell
    active-nav="resources"
    page-title="资源审核"
    page-subtitle="每个待审资源一张卡片 · 点击查看 AI 分析结果"
    hide-search
    hide-toolbar
  >
    <main class="review-page">
      <header v-if="items.length" class="review-page__toolbar">
        <p>
          OpenAI 审核智能体可自动批准正常内容；异常资源单独列出，需教师人工复核。
        </p>
        <n-button
          type="warning"
          :loading="smartReviewLoading"
          :disabled="!items.length"
          @click="runSmartReview"
        >
          <template #icon><n-icon :component="SparklesOutline" /></template>
          智能审核
        </n-button>
      </header>

      <section v-if="metrics" class="metric-grid" aria-label="资源审核指标">
        <article><span>待审核</span><strong>{{ metrics.pending_review_count }}</strong></article>
        <article>
          <span>异常待审</span>
          <strong>{{ metrics.anomaly_pending_count ?? anomalyCount }}</strong>
        </article>
        <article><span>已批准</span><strong>{{ metrics.status_counts.approved }}</strong></article>
        <article><span>已驳回</span><strong>{{ metrics.status_counts.rejected }}</strong></article>
        <article class="metric-grid__wide">
          <span>平均审核时长</span>
          <strong>{{ metrics.average_review_minutes ?? '—' }} 分钟</strong>
        </article>
        <article v-if="metrics.verdict_distribution?.length" class="metric-grid__wide risk-summary">
          <span>AI 建议结论</span>
          <div>
            <n-tag
              v-for="row in metrics.verdict_distribution"
              :key="row.verdict"
              :type="verdictTagType[row.verdict] ?? 'default'"
            >
              {{ verdictLabels[row.verdict] ?? row.verdict }} × {{ row.count }}
            </n-tag>
          </div>
        </article>
      </section>

      <div v-if="items.length" class="review-page__filters">
        <n-button
          size="small"
          :type="listFilter === 'anomaly' ? 'error' : 'default'"
          secondary
          @click="listFilter = 'anomaly'"
        >
          异常内容（{{ anomalyCount }}）
        </n-button>
        <n-button
          size="small"
          :type="listFilter === 'all_pending' ? 'warning' : 'default'"
          secondary
          @click="listFilter = 'all_pending'"
        >
          全部待审（{{ items.length }}）
        </n-button>
      </div>

      <n-empty
        v-if="!items.length"
        description="当前没有待审核资源（正常内容已由 AI 自动批准）"
      />
      <n-empty
        v-else-if="!pendingCards.length"
        :description="listFilter === 'anomaly' ? '暂无异常内容，可切换查看全部待审' : '当前没有待审核资源'"
      />

      <section v-else class="resource-card-grid" aria-label="生成待审核资源">
        <article
          v-for="item in pendingCards"
          :key="item.id"
          class="resource-card"
          :class="{ 'resource-card--anomaly': item.is_anomaly }"
          role="button"
          tabindex="0"
          @click="openDetail(item, $event)"
          @keydown.enter.prevent="openDetail(item)"
        >
          <header class="resource-card__head">
            <div>
              <p class="resource-card__eyebrow">{{ item.knowledge_label || '知识点' }}</p>
              <h3>{{ item.title }}</h3>
            </div>
            <n-tag v-if="item.is_anomaly" type="error" size="small">异常待审</n-tag>
            <n-tag v-else type="warning" size="small">
              {{ reviewStatusLabels[item.review_status] ?? '生成待审核' }}
            </n-tag>
          </header>

          <div class="resource-card__meta">
            <n-tag size="small">{{ typeLabels[item.resource_type] ?? item.resource_type }}</n-tag>
            <n-tag
              v-if="auditReports[item.id]"
              size="small"
              :type="verdictTagType[auditReports[item.id].verdict] ?? 'default'"
            >
              AI {{ verdictLabels[auditReports[item.id].verdict] ?? auditReports[item.id].verdict }}
            </n-tag>
            <span>置信度 {{ Math.round(item.confidence * 100) }}%</span>
          </div>

          <p v-if="item.ai_review?.teacher_summary" class="resource-card__summary">
            {{ String(item.ai_review.teacher_summary) }}
          </p>
          <p v-else class="resource-card__summary resource-card__summary--muted">
            {{ item.recommendation_reason || '点击查看 AI 六步审核与资源内容' }}
          </p>

          <div v-if="topRisks(item).length" class="resource-card__risks">
            <n-tag v-for="risk in topRisks(item)" :key="risk" size="small" type="warning">
              {{ formatRiskReason(risk) }}
            </n-tag>
            <span v-if="(item.risk_reasons?.length || 0) > 3" class="resource-card__more">
              +{{ (item.risk_reasons?.length || 0) - 3 }}
            </span>
          </div>

          <footer class="resource-card__foot">
            <span>任务 {{ (item.generation_task_id || '').slice(0, 8) || '—' }}…</span>
            <button
              type="button"
              class="resource-card__action"
              @click="openDetail(item, $event)"
            >
              查看 AI 分析 →
            </button>
          </footer>
        </article>
      </section>

      <n-modal
        v-model:show="detailShow"
        preset="card"
        :title="detailItem?.title || '资源详情'"
        class="resource-detail-modal"
        :bordered="false"
        :z-index="5200"
        style="width: min(920px, calc(100vw - 32px))"
        @after-leave="closeDetail"
      >
        <template v-if="detailItem">
          <div class="detail-tags">
            <n-tag v-if="detailItem.is_anomaly" type="error">异常内容</n-tag>
            <n-tag type="warning">{{ reviewStatusLabels[detailItem.review_status] ?? '待审核' }}</n-tag>
            <n-tag>{{ typeLabels[detailItem.resource_type] ?? detailItem.resource_type }}</n-tag>
            <n-tag
              v-if="auditReports[detailItem.id]"
              :type="verdictTagType[auditReports[detailItem.id].verdict] ?? 'default'"
            >
              建议 {{ verdictLabels[auditReports[detailItem.id].verdict] ?? auditReports[detailItem.id].verdict }}
            </n-tag>
          </div>

          <p v-if="detailItem.ai_review?.teacher_summary" class="ai-summary">
            <strong>AI 审核：</strong>{{ String(detailItem.ai_review.teacher_summary) }}
          </p>
          <p v-if="detailItem.student_warning" class="student-warning-preview">
            <strong>学生端警示：</strong>{{ detailItem.student_warning }}
          </p>

          <section v-if="auditReports[detailItem.id]" class="audit-panel">
            <div class="audit-summary">
              <p>{{ auditReports[detailItem.id].summary }}</p>
              <n-button
                size="small"
                secondary
                :loading="auditLoading[detailItem.id]"
                @click="rerunAudit(detailItem)"
              >
                重新审核
              </n-button>
            </div>

            <div class="dimension-grid">
              <div
                v-for="[key, score] in dimensionEntries(auditReports[detailItem.id])"
                :key="key"
                class="dimension-row"
              >
                <span>{{ DIMENSION_LABELS[key] }}</span>
                <n-progress type="line" :percentage="score" :height="8" :show-indicator="true" />
              </div>
            </div>

            <n-collapse>
              <n-collapse-item
                v-for="step in auditReports[detailItem.id].steps"
                :key="step.step"
                :title="`第${step.step}步 · ${step.name}（${step.score} 分）`"
                :name="String(step.step)"
              >
                <p class="step-summary">{{ step.summary }}</p>
                <ul v-if="step.checks.length" class="check-list">
                  <li v-for="check in step.checks" :key="check.id">
                    <n-tag size="small" :type="levelTagType[check.level] ?? 'default'">
                      {{ levelLabels[check.level] ?? check.level }}
                    </n-tag>
                    <strong>{{ check.label }}</strong>
                    <span>{{ check.detail }}</span>
                  </li>
                </ul>
              </n-collapse-item>
            </n-collapse>

            <p v-if="auditReports[detailItem.id].metadata?.crewai_notes" class="crew-note">
              <strong>AI 审核备注：</strong>{{ auditReports[detailItem.id].metadata?.crewai_notes }}
            </p>
          </section>
          <p v-else-if="auditLoading[detailItem.id]" class="audit-loading">正在加载六步审核报告…</p>

          <h4 class="detail-heading">资源内容</h4>
          <PersonalizedResourceContentViewer
            :item="detailItem"
            :bundle-item="bundleForTask(detailItem.generation_task_id)"
            theme="teacher"
          />

          <h4 class="detail-heading">知识库引用</h4>
          <ul class="citation-list">
            <li v-for="citation in detailItem.citations" :key="citation.document_id">
              {{ citation.title }} · {{ citation.section }}：{{ citation.snippet }}
            </li>
          </ul>

          <n-input v-model:value="reasons[detailItem.id]" placeholder="审核说明（批准时必填）" />
          <footer class="detail-actions">
            <n-button type="error" secondary @click="review(detailItem, 'rejected')">驳回</n-button>
            <n-button type="primary" @click="review(detailItem, 'approved')">批准发布</n-button>
          </footer>
        </template>
      </n-modal>
    </main>
  </TeacherDashboardShell>
</template>

<style scoped>
.review-page {
  width: 100%;
  padding: 0 var(--plex-page-gutter-x) 2rem;
}

.review-page__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
  padding: 0.85rem 1rem;
  border: 1px solid rgba(251, 146, 60, 0.22);
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(67, 20, 7, 0.35), rgba(15, 23, 42, 0.45));
}

.review-page__toolbar p {
  margin: 0;
  color: rgba(254, 215, 170, 0.78);
  font-size: 0.86rem;
  line-height: 1.5;
}

.review-page__filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-bottom: 1rem;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.8rem;
  margin-bottom: 1rem;
}

.metric-grid article {
  padding: 1rem;
  border: 1px solid rgba(255, 173, 76, 0.2);
  border-radius: 14px;
  background: rgba(25, 15, 7, 0.72);
}

.metric-grid__wide {
  grid-column: span 2;
}

.metric-grid span {
  display: block;
  color: rgba(235, 215, 194, 0.68);
}

.metric-grid strong {
  display: block;
  margin-top: 0.35rem;
  color: #fff7ec;
  font-size: 1.35rem;
}

.risk-summary div {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-top: 0.55rem;
}

.resource-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 0.9rem;
  margin-bottom: 1.25rem;
}

.resource-card {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  padding: 1.05rem 1.1rem;
  border: 1px solid rgba(255, 173, 76, 0.22);
  border-radius: 16px;
  background:
    radial-gradient(circle at 90% 0%, rgba(251, 146, 60, 0.12), transparent 42%),
    rgba(25, 15, 7, 0.78);
  cursor: pointer;
  pointer-events: auto;
  transition: border-color 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease;
}

.resource-card:hover,
.resource-card:focus-visible {
  border-color: rgba(251, 146, 60, 0.55);
  transform: translateY(-2px);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.28);
  outline: none;
}

.resource-card--anomaly {
  border-color: rgba(248, 113, 113, 0.42);
  background:
    radial-gradient(circle at 90% 0%, rgba(248, 113, 113, 0.14), transparent 42%),
    rgba(69, 10, 10, 0.55);
}

.resource-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.65rem;
}

.resource-card__eyebrow {
  margin: 0 0 0.25rem;
  color: rgba(251, 146, 60, 0.78);
  font-size: 0.72rem;
  letter-spacing: 0.06em;
}

.resource-card__head h3 {
  margin: 0;
  color: #fff7ec;
  font-size: 1.05rem;
  line-height: 1.35;
}

.resource-card__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  color: rgba(235, 215, 194, 0.65);
  font-size: 0.82rem;
}

.resource-card__summary {
  margin: 0;
  color: rgba(254, 215, 170, 0.88);
  font-size: 0.86rem;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.resource-card__summary--muted {
  color: rgba(235, 215, 194, 0.58);
}

.resource-card__risks {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  align-items: center;
}

.resource-card__more {
  color: rgba(235, 215, 194, 0.55);
  font-size: 0.78rem;
}

.resource-card__foot {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  margin-top: auto;
  padding-top: 0.35rem;
  color: rgba(235, 215, 194, 0.5);
  font-size: 0.78rem;
}

.resource-card__action {
  margin: 0;
  padding: 0;
  border: none;
  background: transparent;
  color: #fb923c;
  font: inherit;
  font-weight: 650;
  font-size: 0.78rem;
  cursor: pointer;
  pointer-events: auto;
}

.resource-card__action:hover {
  color: #fdba74;
  text-decoration: underline;
}

.detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-bottom: 0.85rem;
}

.ai-summary,
.student-warning-preview {
  margin: 0.35rem 0;
  font-size: 0.88rem;
  line-height: 1.5;
}

.ai-summary {
  color: rgba(254, 215, 170, 0.88);
}

.student-warning-preview {
  color: rgba(252, 165, 165, 0.92);
}

.detail-heading {
  margin: 1rem 0 0.5rem;
  color: #fff7ec;
  font-size: 0.95rem;
}

.citation-list {
  margin: 0 0 1rem;
  padding-left: 1.2rem;
  color: rgba(235, 215, 194, 0.7);
}

.detail-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
  margin-top: 0.8rem;
}

.audit-panel {
  margin: 1rem 0;
  padding: 1rem;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(255, 173, 76, 0.12);
}

.audit-summary {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.8rem;
  margin-bottom: 0.8rem;
  color: rgba(235, 215, 194, 0.78);
}

.dimension-grid {
  display: grid;
  gap: 0.55rem;
  margin-bottom: 0.8rem;
}

.dimension-row {
  display: grid;
  grid-template-columns: 6.5rem 1fr;
  align-items: center;
  gap: 0.6rem;
}

.dimension-row span {
  font-size: 0.85rem;
  color: rgba(235, 215, 194, 0.75);
}

.step-summary {
  margin-bottom: 0.5rem;
  color: rgba(235, 215, 194, 0.7);
}

.check-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 0.45rem;
}

.check-list li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  color: rgba(235, 215, 194, 0.7);
}

.check-list strong {
  color: #fff7ec;
}

.crew-note,
.audit-loading {
  margin-top: 0.6rem;
  font-size: 0.9rem;
  color: rgba(235, 215, 194, 0.65);
}

@media (max-width: 800px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .metric-grid__wide {
    grid-column: 1 / -1;
  }

  .dimension-row {
    grid-template-columns: 1fr;
  }
}
</style>

<style>
.resource-detail-modal.n-card {
  background: rgba(8, 14, 22, 0.98) !important;
  border: 1px solid rgba(251, 146, 60, 0.22) !important;
}

.resource-detail-modal .n-card-header__main {
  color: #fff7ed !important;
}
</style>
