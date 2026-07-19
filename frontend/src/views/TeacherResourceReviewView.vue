<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  NButton,
  NCollapse,
  NCollapseItem,
  NEmpty,
  NIcon,
  NInput,
  NProgress,
  NTag,
  useMessage,
} from 'naive-ui'
import { SparklesOutline } from '@vicons/ionicons5'
import TeacherDashboardShell from '../components/layout/TeacherDashboardShell.vue'
import ClassFileExchangePanel from '../components/student/ClassFileExchangePanel.vue'
import PersonalizedResourceContentViewer from '../components/personalized/PersonalizedResourceContentViewer.vue'
import { useTeacherOverviewInjected } from '../composables/useTeacherOverview'
import {
  DIMENSION_LABELS,
  fetchResourceAudit,
  fetchResourceReviewMetrics,
  fetchReviewResources,
  rerunResourceAudit,
  reviewPersonalizedResource,
  type AuditReport,
  type DimensionScores,
  type PersonalizedResource,
  type ResourceReviewMetrics,
} from '../api/personalizedResources'

const message = useMessage()
const { selectedClassId } = useTeacherOverviewInjected()
const items = ref<PersonalizedResource[]>([])
const metrics = ref<ResourceReviewMetrics | null>(null)
const reasons = ref<Record<number, string>>({})
const auditReports = ref<Record<number, AuditReport>>({})
const auditLoading = ref<Record<number, boolean>>({})
const expandedId = ref<number | null>(null)
const smartReviewLoading = ref(false)
const manualReviewTags = ref<Record<number, string>>({})

const riskReasonLabels: Record<string, string> = {
  low_confidence: '置信度偏低',
  scope_mismatch: '超出课程范围',
  missing_citation: '缺少知识库引用',
  code_quality: '代码质量存疑',
  factual_risk: '事实准确性风险',
  incomplete_content: '内容不完整',
}

const typeLabels: Record<string, string> = {
  learning_bundle: '完整资源包',
  lesson_document: '讲解文档',
  mind_map: '思维导图',
  exercise_set: '分层题库',
  extended_reading: '拓展阅读',
  coding_lab: '代码实操',
  audio_explanation: '语音讲解',
}

const verdictTagType: Record<string, 'success' | 'warning' | 'error'> = {
  PASS: 'success',
  NEED_MODIFY: 'warning',
  REJECT: 'error',
}

const reviewStatusLabels: Record<string, string> = {
  pending_review: '待审核',
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

const groupedItems = computed(() => {
  const groups = new Map<string, PersonalizedResource[]>()
  for (const item of items.value) {
    const key = item.generation_task_id
    const bucket = groups.get(key) ?? []
    bucket.push(item)
    groups.set(key, bucket)
  }
  return [...groups.entries()].map(([taskId, groupItems]) => ({
    taskId,
    items: [...groupItems].sort((a, b) => a.id - b.id),
  }))
})

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
  if (resources.items.length && expandedId.value === null) {
    expandedId.value = resources.items[0].id
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
    expandedId.value = null
    await load()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '审核失败')
  }
}

function toggleDetail(item: PersonalizedResource) {
  expandedId.value = expandedId.value === item.id ? null : item.id
}

function dimensionEntries(report: AuditReport) {
  return Object.entries(report.dimensions) as Array<[keyof DimensionScores, number]>
}

function formatRiskReason(reason: string) {
  return riskReasonLabels[reason] ?? reason.replace(/_/g, ' ')
}

function shouldAutoApprove(item: PersonalizedResource, report: AuditReport | undefined) {
  if (!report) return false
  if (report.verdict !== 'PASS' || !report.suggested_publish) return false
  if (item.confidence < 0.72) return false
  if (item.risk_reasons.length > 0) return false
  const minDimension = Math.min(...Object.values(report.dimensions))
  return minDimension >= 70
}

async function runSmartReview() {
  if (!items.value.length || smartReviewLoading.value) return
  smartReviewLoading.value = true
  let approved = 0
  let flagged = 0
  const nextTags: Record<number, string> = { ...manualReviewTags.value }
  try {
    for (const item of items.value) {
      if (!auditReports.value[item.id]) {
        await loadAudit(item.id)
      }
      let report = auditReports.value[item.id]
      if (!report) {
        try {
          const result = await rerunResourceAudit(item.id)
          auditReports.value[item.id] = result.audit_report
          report = result.audit_report
        } catch {
          nextTags[item.id] = 'AI 审核报告缺失'
          flagged += 1
          continue
        }
      }
      if (shouldAutoApprove(item, report)) {
        await reviewPersonalizedResource(
          item.id,
          'approved',
          'AI 智能审核：六步审核通过，内容符合正常发布标准',
        )
        delete nextTags[item.id]
        approved += 1
      } else {
        const verdictLabel = verdictLabels[report.verdict] ?? '需复核'
        const hint =
          report.verdict === 'PASS'
            ? '建议通过但需人工确认'
            : report.verdict === 'NEED_MODIFY'
              ? '建议修改后再发布'
              : '建议驳回'
        nextTags[item.id] = `需人工复核 · ${verdictLabel} · ${hint}`
        flagged += 1
      }
    }
    manualReviewTags.value = nextTags
    message.success(`智能审核完成：自动通过 ${approved} 项，${flagged} 项已打标待人工复核`)
    await load()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '智能审核失败')
  } finally {
    smartReviewLoading.value = false
  }
}

onMounted(() => void load())
</script>

<template>
  <TeacherDashboardShell
    active-nav="resources"
    page-title="资源审核"
    page-subtitle="点击资源查看完整内容 · 六步审核建议仅供参考"
    hide-search
    hide-toolbar
  >
    <main class="review-page">
      <header v-if="items.length" class="review-page__toolbar">
        <p>接入六步 AI 审核：符合标准的资源可一键通过，存疑项将打标供教师继续审核。</p>
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
        <article><span>已批准</span><strong>{{ metrics.status_counts.approved }}</strong></article>
        <article><span>已驳回</span><strong>{{ metrics.status_counts.rejected }}</strong></article>
        <article>
          <span>平均审核时长</span>
          <strong>{{ metrics.average_review_minutes ?? '—' }} 分钟</strong>
        </article>
        <article v-if="metrics.verdict_distribution?.length" class="risk-summary">
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
        <article v-if="metrics.risk_reason_distribution?.length" class="risk-summary">
          <span>风险原因</span>
          <div>
            <n-tag v-for="risk in metrics.risk_reason_distribution" :key="risk.reason" type="warning">
              {{ formatRiskReason(risk.reason) }} × {{ risk.count }}
            </n-tag>
          </div>
        </article>
      </section>

      <n-empty v-if="!items.length" description="当前没有待审核资源" />

      <section v-for="group in groupedItems" :key="group.taskId" class="task-group">
        <header class="task-group__header">
          <div>
            <h2>{{ group.items[0]?.knowledge_label }} · 生成任务</h2>
            <p>任务 ID：{{ group.taskId }} · {{ group.items.length }} 项待审</p>
          </div>
        </header>

        <article v-for="item in group.items" :key="item.id" class="review-card">
          <header>
            <button type="button" class="review-card__title-btn" @click="toggleDetail(item)">
              <h3>{{ item.title }}</h3>
              <span class="review-card__hint">
                {{ expandedId === item.id ? '点击收起' : '点击查看详细内容' }}
              </span>
            </button>
            <div class="review-card__tags">
              <n-tag v-if="manualReviewTags[item.id]" type="error">{{ manualReviewTags[item.id] }}</n-tag>
              <n-tag type="warning">{{ reviewStatusLabels[item.review_status] ?? '待审核' }}</n-tag>
              <n-tag>{{ typeLabels[item.resource_type] ?? item.resource_type }}</n-tag>
              <n-tag
                v-if="auditReports[item.id]"
                :type="verdictTagType[auditReports[item.id].verdict] ?? 'default'"
              >
                建议 {{ verdictLabels[auditReports[item.id].verdict] ?? auditReports[item.id].verdict }}
              </n-tag>
              <span>置信度 {{ Math.round(item.confidence * 100) }}%</span>
            </div>
          </header>

          <div class="risks">
            <n-tag v-for="risk in item.risk_reasons" :key="risk" type="error">{{ formatRiskReason(risk) }}</n-tag>
          </div>
          <p>{{ item.recommendation_reason }}</p>

          <section v-if="expandedId === item.id" class="resource-detail">
            <section v-if="auditReports[item.id]" class="audit-panel">
              <div class="audit-summary">
                <p>{{ auditReports[item.id].summary }}</p>
                <n-button
                  size="small"
                  secondary
                  :loading="auditLoading[item.id]"
                  @click="rerunAudit(item)"
                >
                  重新审核
                </n-button>
              </div>

              <div class="dimension-grid">
                <div
                  v-for="[key, score] in dimensionEntries(auditReports[item.id])"
                  :key="key"
                  class="dimension-row"
                >
                  <span>{{ DIMENSION_LABELS[key] }}</span>
                  <n-progress type="line" :percentage="score" :height="8" :show-indicator="true" />
                </div>
              </div>

              <n-collapse>
                <n-collapse-item
                  v-for="step in auditReports[item.id].steps"
                  :key="step.step"
                  :title="`第${step.step}步 · ${step.name}（${step.score} 分）`"
                  :name="String(step.step)"
                >
                  <p class="step-summary">{{ step.summary }}</p>
                  <ul v-if="step.checks.length" class="check-list">
                    <li v-for="check in step.checks" :key="check.id">
                      <n-tag size="small" :type="levelTagType[check.level] ?? 'default'">{{ levelLabels[check.level] ?? check.level }}</n-tag>
                      <strong>{{ check.label }}</strong>
                      <span>{{ check.detail }}</span>
                    </li>
                  </ul>
                </n-collapse-item>
              </n-collapse>

              <p v-if="auditReports[item.id].metadata?.crewai_notes" class="crew-note">
                <strong>AI 审核备注：</strong>{{ auditReports[item.id].metadata?.crewai_notes }}
              </p>
            </section>
            <p v-else-if="auditLoading[item.id]" class="audit-loading">正在加载六步审核报告…</p>

            <h4 class="detail-heading">资源内容</h4>
            <PersonalizedResourceContentViewer
              :item="item"
              :bundle-item="bundleForTask(item.generation_task_id)"
              theme="teacher"
            />

            <h4 class="detail-heading">知识库引用</h4>
            <ul class="citation-list">
              <li v-for="citation in item.citations" :key="citation.document_id">
                {{ citation.title }} · {{ citation.section }}：{{ citation.snippet }}
              </li>
            </ul>

            <n-input v-model:value="reasons[item.id]" placeholder="审核说明（批准时必填）" />
            <footer>
              <n-button type="error" secondary @click="review(item, 'rejected')">驳回</n-button>
              <n-button type="primary" @click="review(item, 'approved')">批准发布</n-button>
            </footer>
          </section>
        </article>
      </section>

      <section class="review-page__files" aria-label="学生提交文件审核">
        <header class="review-page__files-head">
          <h2>学生提交文件</h2>
          <p>班级学生上传的学习报告、代码与学习截图，独立于 AI 个性化资源审核。</p>
        </header>
        <class-file-exchange-panel
          role="teacher"
          submissions-only
          :class-id="selectedClassId"
        />
      </section>
    </main>
  </TeacherDashboardShell>
</template>

<style scoped>
.review-page {
  width: 100%;
  padding: 0 var(--plex-page-gutter-x) 2rem;
  overflow-y: auto;
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

.task-group {
  margin-bottom: 1.2rem;
}

.task-group__header {
  margin-bottom: 0.65rem;
}

.task-group__header h2 {
  margin: 0;
  color: #fff7ec;
  font-size: 1.1rem;
}

.task-group__header p {
  margin: 0.25rem 0 0;
  color: rgba(235, 215, 194, 0.6);
  font-size: 0.88rem;
}

.review-card {
  margin-bottom: 0.75rem;
  padding: 1.2rem;
  border: 1px solid rgba(255, 173, 76, 0.2);
  border-radius: 16px;
  background: rgba(25, 15, 7, 0.72);
}

.review-card header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.8rem;
}

.review-card__title-btn {
  flex: 1;
  min-width: 0;
  border: none;
  padding: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.review-card__title-btn h3 {
  margin: 0;
  color: #fff7ec;
}

.review-card__hint {
  display: block;
  margin-top: 0.25rem;
  font-size: 0.82rem;
  color: rgba(255, 173, 76, 0.75);
}

.review-card__tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem;
  color: rgba(235, 215, 194, 0.65);
  font-size: 0.85rem;
}

.review-card p,
.review-card li {
  color: rgba(235, 215, 194, 0.7);
}

.review-card footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
  margin-top: 0.8rem;
}

.risks {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin: 0.5rem 0;
}

.resource-detail {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 173, 76, 0.15);
}

.detail-heading {
  margin: 1rem 0 0.5rem;
  color: #fff7ec;
  font-size: 0.95rem;
}

.citation-list {
  margin: 0 0 1rem;
  padding-left: 1.2rem;
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

.metric-grid .risk-summary {
  grid-column: 1 / -1;
}

.risk-summary div {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-top: 0.55rem;
}

.audit-panel {
  margin-bottom: 1rem;
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

.review-page__files {
  margin-top: 1.25rem;
}

.review-page__files-head h2 {
  margin: 0;
  color: #fff7ec;
  font-size: 1.1rem;
}

.review-page__files-head p {
  margin: 0.35rem 0 0.75rem;
  color: rgba(235, 215, 194, 0.62);
  font-size: 0.88rem;
}

@media (max-width: 800px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dimension-row {
    grid-template-columns: 1fr;
  }

  .review-card header {
    flex-direction: column;
  }
}
</style>
