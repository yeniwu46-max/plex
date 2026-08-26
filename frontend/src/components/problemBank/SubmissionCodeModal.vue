<script setup lang="ts">
/**
 * 提交记录详情弹窗：等宽字体展示完整代码 + 一键复制，附带判题明细。
 * 样式参照 `frontend/src/components/teacher/ExplorerProfileModal.vue`。
 */
import { computed, ref, watch } from 'vue'
import { NModal, NSpin, NTag, NEmpty } from 'naive-ui'
import CopyableBlock from './CopyableBlock.vue'
import { fetchSubmissionDetail, type ProblemSubmissionDetail } from '../../api/problemBank'
import { formatHttpError } from '../../api/http'

const props = defineProps<{
  show: boolean
  submissionId: number | null
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
}>()

const visible = computed({
  get: () => props.show,
  set: (value: boolean) => emit('update:show', value),
})

const detail = ref<ProblemSubmissionDetail | null>(null)
const loading = ref(false)
const error = ref('')

const STATUS_META: Record<string, { label: string; type: 'success' | 'warning' | 'error' | 'default' }> = {
  AC: { label: 'AC 完全通过', type: 'success' },
  TE: { label: '部分通过', type: 'warning' },
  CE: { label: '编译错误', type: 'error' },
  UE: { label: '运行异常', type: 'error' },
}

function statusMeta(status?: string | null) {
  return (status && STATUS_META[status]) || { label: status || '-', type: 'default' as const }
}

async function load(id: number) {
  loading.value = true
  error.value = ''
  detail.value = null
  try {
    detail.value = await fetchSubmissionDetail(id)
  } catch (err) {
    error.value = formatHttpError(err, '提交详情加载失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.show, props.submissionId] as const,
  ([open, id]) => {
    if (open && id) void load(id)
  },
)
</script>

<template>
  <n-modal
    v-model:show="visible"
    preset="card"
    title="提交记录详情"
    class="submission-code-modal"
    :bordered="false"
    :z-index="5300"
    style="width: min(720px, calc(100vw - 32px))"
  >
    <n-spin :show="loading">
      <div v-if="error" class="submission-code-modal__error">{{ error }}</div>
      <div v-else-if="detail" class="submission-detail">
        <div class="submission-detail__meta">
          <n-tag round size="small" :type="statusMeta(detail.status).type">{{ statusMeta(detail.status).label }}</n-tag>
          <span>得分 {{ detail.score_points ?? '-' }} / {{ detail.score_total ?? '-' }}
            <template v-if="detail.score_percent !== null">· {{ detail.score_percent }}%</template>
          </span>
          <span v-if="detail.exec_time_ms !== null">耗时 {{ detail.exec_time_ms }} ms</span>
          <span v-if="detail.exec_memory_kb !== null">内存 {{ detail.exec_memory_kb }} KB</span>
          <span v-if="detail.time_spent_seconds !== null">作答用时 {{ detail.time_spent_seconds }} 秒</span>
        </div>
        <p class="submission-detail__student">
          {{ detail.legacy_student_name || detail.legacy_username || `用户 ${detail.legacy_user_id}` }}
          <span v-if="detail.legacy_group_name">· {{ detail.legacy_group_name }}</span>
        </p>

        <CopyableBlock label="提交代码" :content="detail.code_content" max-height="360px" />

        <div v-if="detail.test_case_results.length" class="submission-detail__cases">
          <h4>测试点明细</h4>
          <ul>
            <li v-for="tc in detail.test_case_results" :key="tc.seq">
              <n-tag size="tiny" :type="tc.passed ? 'success' : 'error'">{{ tc.passed ? '通过' : '未通过' }}</n-tag>
              <span v-if="tc.label" class="submission-detail__case-label">{{ tc.label }}</span>
              <code class="submission-detail__case-output">{{ tc.output }}</code>
            </li>
          </ul>
        </div>
        <div v-else-if="detail.raw_judge_output" class="submission-detail__cases">
          <h4>判题输出 · 编译或运行错误</h4>
          <CopyableBlock :content="detail.raw_judge_output" max-height="200px" />
        </div>
      </div>
      <n-empty v-else description="暂无数据" />
    </n-spin>
  </n-modal>
</template>

<style scoped>
.submission-detail {
  display: flex;
  flex-direction: column;
  gap: 0.9em;
}

.submission-detail__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.9em;
  font-size: 0.88em;
  color: rgba(217, 246, 255, 0.75);
}

.submission-detail__student {
  margin: 0;
  font-size: 0.85em;
  color: rgba(217, 246, 255, 0.55);
}

.submission-detail__cases h4 {
  margin: 0 0 0.5em;
  font-size: 0.92em;
}

.submission-detail__cases ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4em;
  max-height: 220px;
  overflow-y: auto;
}

.submission-detail__cases li {
  display: flex;
  align-items: center;
  gap: 0.6em;
  padding: 0.35em 0.6em;
  border-radius: 8px;
  background: rgba(4, 20, 30, 0.45);
  font-size: 0.85em;
}

.submission-detail__case-label {
  color: rgba(217, 246, 255, 0.6);
}

.submission-detail__case-output {
  font-family: 'JetBrains Mono', Consolas, monospace;
  overflow-x: auto;
  white-space: pre;
}

.submission-code-modal__error {
  color: #ff6b6b;
  padding: 1em 0;
}
</style>
