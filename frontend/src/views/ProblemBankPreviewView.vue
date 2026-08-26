<script setup lang="ts">
/**
 * 题库预览页（新增入口，尚未挂载到正式导航，见交付说明）。
 * 路由：/teacher/problem-bank
 *
 * 左侧题目列表（按 concept_group 分组筛选 + 关键词搜索），右侧展示所选题目的
 * 标准化详情（ProblemDetailView）与提交记录列表；点击一条提交记录弹出
 * SubmissionCodeModal 查看完整代码。
 */
import { computed, onMounted, ref, watch } from 'vue'
import { NButton, NEmpty, NInput, NSpin, NTag, useMessage } from 'naive-ui'
import TeacherDashboardShell from '../components/layout/TeacherDashboardShell.vue'
import ProblemDetailView from '../components/problemBank/ProblemDetailView.vue'
import SubmissionCodeModal from '../components/problemBank/SubmissionCodeModal.vue'
import StarRating from '../components/problemBank/StarRating.vue'
import {
  fetchProblemBankList,
  fetchProblemBankTags,
  fetchProblemSubmissions,
  type ConceptGroupOption,
  type ProblemSubmissionSummary,
  type ProblemSummary,
  type ProblemTag,
} from '../api/problemBank'
import { formatHttpError } from '../api/http'

const message = useMessage()

const problems = ref<ProblemSummary[]>([])
const conceptGroups = ref<ConceptGroupOption[]>([])
const loadingList = ref(false)
const keyword = ref('')
const activeGroup = ref<string | null>(null)
const selectedProblemId = ref<number | null>(null)
const activeTag = ref<string | null>(null)
const allTags = ref<ProblemTag[]>([])

const submissions = ref<ProblemSubmissionSummary[]>([])
const loadingSubmissions = ref(false)

const modalVisible = ref(false)
const activeSubmissionId = ref<number | null>(null)

const STATUS_META: Record<string, { label: string; type: 'success' | 'warning' | 'error' | 'default' }> = {
  AC: { label: 'AC', type: 'success' },
  TE: { label: '部分通过', type: 'warning' },
  CE: { label: '编译错误', type: 'error' },
  UE: { label: '运行异常', type: 'error' },
}

function statusMeta(status?: string | null) {
  return (status && STATUS_META[status]) || { label: status || '-', type: 'default' as const }
}

async function loadProblems() {
  loadingList.value = true
  try {
    const result = await fetchProblemBankList({
      concept_group: activeGroup.value || undefined,
      keyword: keyword.value || undefined,
      tag: activeTag.value || undefined,
    })
    problems.value = result.items
    conceptGroups.value = result.concept_groups
    if ((!selectedProblemId.value || !result.items.some((p) => p.id === selectedProblemId.value)) && result.items.length) {
      selectedProblemId.value = result.items[0].id
    }
  } catch (err) {
    message.error(formatHttpError(err, '题库列表加载失败'))
  } finally {
    loadingList.value = false
  }
}

async function loadTags() {
  try {
    const result = await fetchProblemBankTags()
    allTags.value = result.items
  } catch {
    // 标签名称展示是锦上添花的功能，静默失败不影响主流程
  }
}

function tagLabel(code: string) {
  return allTags.value.find((t) => t.code === code)?.label || code
}

function onTagClick(code: string) {
  activeTag.value = code
}

function clearTagFilter() {
  activeTag.value = null
}

async function loadSubmissions(problemId: number) {
  loadingSubmissions.value = true
  submissions.value = []
  try {
    const result = await fetchProblemSubmissions(problemId, { limit: 100 })
    submissions.value = result.items
  } catch (err) {
    message.error(formatHttpError(err, '提交记录加载失败'))
  } finally {
    loadingSubmissions.value = false
  }
}

function selectProblem(id: number) {
  selectedProblemId.value = id
}

function openSubmission(id: number) {
  activeSubmissionId.value = id
  modalVisible.value = true
}

function formatDate(value?: string | null) {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 19)
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(keyword, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => void loadProblems(), 300)
})

watch(activeGroup, () => void loadProblems())
watch(activeTag, () => void loadProblems())

watch(selectedProblemId, (id) => {
  if (id) void loadSubmissions(id)
})

onMounted(() => {
  void loadProblems()
  void loadTags()
})

const groupTabs = computed(() => [{ group: '', label: '全部' }, ...conceptGroups.value])
</script>

<template>
  <TeacherDashboardShell
    active-nav="problem-bank"
    page-title="题库管理"
    page-subtitle="统一查看标准化题目、知识标签与学生提交记录"
    hide-search
    :show-activity="false"
    :show-refresh="false"
  >
    <section class="problem-bank teacher-page" aria-label="题库管理">
      <aside class="problem-bank__list">
        <n-input v-model:value="keyword" placeholder="搜索题号或标题" clearable size="small" />
        <div class="problem-bank__groups">
          <button
            v-for="g in groupTabs"
            :key="g.group || 'all'"
            type="button"
            class="problem-bank__group-tab"
            :class="{ 'is-active': activeGroup === (g.group || null) }"
            @click="activeGroup = g.group || null"
          >
            {{ g.label }}
          </button>
        </div>
        <div v-if="activeTag" class="problem-bank__tag-filter">
          <span>按标签筛选：</span>
          <n-tag closable size="small" round type="info" @close="clearTagFilter">{{ tagLabel(activeTag) }}</n-tag>
        </div>
        <n-spin :show="loadingList">
          <ul class="problem-bank__items">
            <li
              v-for="p in problems"
              :key="p.id"
              class="problem-bank__item"
              :class="{ 'is-active': p.id === selectedProblemId }"
              @click="selectProblem(p.id)"
            >
              <n-tag size="tiny" round type="primary">{{ p.problem_no }}</n-tag>
              <span class="problem-bank__item-title">{{ p.title_cn }}</span>
              <StarRating class="problem-bank__item-star" :value="p.star_difficulty" compact />
            </li>
          </ul>
          <n-empty v-if="!loadingList && !problems.length" description="没有匹配的题目" />
        </n-spin>
      </aside>

      <div class="problem-bank__detail teacher-panel">
        <ProblemDetailView :problem-id="selectedProblemId" @tag-click="onTagClick" />

        <section v-if="selectedProblemId" class="problem-bank__submissions">
          <h3>提交记录 · {{ submissions.length }} 条 · 按时间倒序</h3>
          <n-spin :show="loadingSubmissions">
            <div v-if="submissions.length" class="problem-bank__submission-table">
              <div class="problem-bank__submission-row problem-bank__submission-row--head">
                <span>学生</span>
                <span>状态</span>
                <span>得分</span>
                <span>用时</span>
                <span>执行耗时</span>
                <span>提交时间</span>
                <span></span>
              </div>
              <div
                v-for="s in submissions"
                :key="s.id"
                class="problem-bank__submission-row"
                @click="openSubmission(s.id)"
              >
                <span>{{ s.legacy_student_name || s.legacy_username || `用户${s.legacy_user_id}` }}</span>
                <span><n-tag size="tiny" :type="statusMeta(s.status).type">{{ statusMeta(s.status).label }}</n-tag></span>
                <span>{{ s.score_points ?? '-' }}/{{ s.score_total ?? '-' }}<template v-if="s.score_percent !== null"> ({{ s.score_percent }}%)</template></span>
                <span>{{ s.time_spent_seconds !== null ? `${s.time_spent_seconds}s` : '-' }}</span>
                <span>{{ s.exec_time_ms !== null ? `${s.exec_time_ms}ms` : '-' }}</span>
                <span>{{ formatDate(s.submitted_at) }}</span>
                <span><n-button size="tiny" quaternary type="primary" @click.stop="openSubmission(s.id)">查看代码</n-button></span>
              </div>
            </div>
            <n-empty v-else-if="!loadingSubmissions" description="该题暂无提交记录" />
          </n-spin>
        </section>
      </div>
    </section>

    <SubmissionCodeModal v-model:show="modalVisible" :submission-id="activeSubmissionId" />
  </TeacherDashboardShell>
</template>

<style scoped>
.problem-bank {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 1.2em;
  align-items: start;
}

.problem-bank__list {
  display: flex;
  flex-direction: column;
  gap: 0.7em;
  padding: 1em;
  border-radius: 12px;
  background: rgba(4, 20, 30, 0.5);
  border: 1px solid rgba(110, 228, 255, 0.14);
  position: sticky;
  top: 1em;
}

.problem-bank__groups {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4em;
}

.problem-bank__group-tab {
  border: 1px solid rgba(110, 228, 255, 0.2);
  background: transparent;
  color: rgba(217, 246, 255, 0.7);
  border-radius: 999px;
  padding: 0.2em 0.75em;
  font-size: 0.78em;
  cursor: pointer;
}

.problem-bank__group-tab.is-active {
  background: rgba(37, 245, 238, 0.16);
  border-color: #25f5ee;
  color: #d9f6ff;
}

.problem-bank__tag-filter {
  display: flex;
  align-items: center;
  gap: 0.4em;
  font-size: 0.78em;
  color: rgba(217, 246, 255, 0.6);
}

.problem-bank__items {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.3em;
  max-height: 60vh;
  overflow-y: auto;
}

.problem-bank__item {
  display: flex;
  align-items: center;
  gap: 0.6em;
  padding: 0.45em 0.6em;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.88em;
}

.problem-bank__item:hover {
  background: rgba(110, 228, 255, 0.08);
}

.problem-bank__item.is-active {
  background: rgba(37, 245, 238, 0.14);
  border: 1px solid rgba(37, 245, 238, 0.4);
}

.problem-bank__item-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.problem-bank__item-star {
  flex-shrink: 0;
}

.problem-bank__detail {
  padding: 1.2em;
  border-radius: 12px;
  min-height: 400px;
}

.problem-bank__submissions {
  margin-top: 1.6em;
  padding-top: 1.2em;
  border-top: 1px solid rgba(110, 228, 255, 0.14);
}

.problem-bank__submissions h3 {
  margin: 0 0 0.7em;
  font-size: 0.95em;
}

.problem-bank__submission-table {
  display: flex;
  flex-direction: column;
  gap: 0.25em;
  max-height: 360px;
  overflow-y: auto;
}

.problem-bank__submission-row {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr 1fr 0.7fr 0.8fr 1.3fr 0.9fr;
  align-items: center;
  gap: 0.5em;
  padding: 0.4em 0.6em;
  border-radius: 8px;
  font-size: 0.82em;
  cursor: pointer;
}

.problem-bank__submission-row:not(.problem-bank__submission-row--head):hover {
  background: rgba(110, 228, 255, 0.08);
}

.problem-bank__submission-row--head {
  font-weight: 600;
  color: rgba(217, 246, 255, 0.55);
  cursor: default;
  font-size: 0.76em;
  text-transform: uppercase;
}

@media (max-width: 900px) {
  .problem-bank {
    grid-template-columns: 1fr;
  }
}
</style>
