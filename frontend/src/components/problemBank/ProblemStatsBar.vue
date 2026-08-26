<script setup lang="ts">
/**
 * 标题右侧统计信息条（增强#5）：提交数 / 通过数 / 时间限制。
 *
 * 口径说明：旧题库导入的 70 道题、2.6 万+ 条提交记录里的 legacy_user_id 并不
 * 对应当前 PLEX 账号体系（脱敏后的旧账号无法与真实师生账号建立映射），因此
 * "提交/通过数按班级口径统计"这里如实采用数据中真实存在的"旧系统班级"
 * （`group` 表，8 个班级）维度，而不是伪造一份"当前登录教师所在班级"的假
 * 关联。下拉框展示的是有该题提交记录的旧系统班级列表，默认选中第一个。
 * 完整取舍说明见 REPORT.md 增强篇5。
 */
import { onMounted, ref, watch } from 'vue'
import { NSelect, NSpin, NTooltip } from 'naive-ui'
import { fetchProblemStats, type ProblemStats } from '../../api/problemBank'

const props = defineProps<{
  problemId: number
}>()

const stats = ref<ProblemStats | null>(null)
const loading = ref(false)
const selectedGroupId = ref<number | null>(null)

async function load(groupId?: number | null) {
  loading.value = true
  try {
    stats.value = await fetchProblemStats(props.problemId, groupId ?? undefined)
    selectedGroupId.value = stats.value.legacy_group_id
  } catch {
    stats.value = null
  } finally {
    loading.value = false
  }
}

function onGroupChange(value: number | null) {
  selectedGroupId.value = value
  void load(value)
}

watch(
  () => props.problemId,
  () => void load(),
)

onMounted(() => void load())

function formatTimeLimit(ms: number) {
  return `${(ms / 1000).toFixed(2)}s`
}
</script>

<template>
  <n-spin :show="loading" size="small">
    <div v-if="stats" class="problem-stats-bar">
      <div class="problem-stats-bar__metric">
        <span class="problem-stats-bar__value">{{ stats.submission_count }}</span>
        <span class="problem-stats-bar__label">提交</span>
      </div>
      <div class="problem-stats-bar__metric">
        <span class="problem-stats-bar__value">{{ stats.accepted_count }}</span>
        <span class="problem-stats-bar__label">通过</span>
      </div>
      <div class="problem-stats-bar__metric">
        <n-tooltip v-if="stats.time_limit_is_default" trigger="hover">
          <template #trigger>
            <span class="problem-stats-bar__value problem-stats-bar__value--dashed">{{ formatTimeLimit(stats.time_limit_ms) }}</span>
          </template>
          原始数据无逐题时间限制字段，此为平台统一默认值
        </n-tooltip>
        <span v-else class="problem-stats-bar__value">{{ formatTimeLimit(stats.time_limit_ms) }}</span>
        <span class="problem-stats-bar__label">时间限制</span>
      </div>
      <n-select
        v-if="stats.groups.length > 1"
        class="problem-stats-bar__group-select"
        size="tiny"
        :value="selectedGroupId"
        :options="stats.groups.map((g) => ({ label: g.legacy_group_name || `班级${g.legacy_group_id}`, value: g.legacy_group_id }))"
        @update:value="onGroupChange"
      />
      <n-tooltip v-else-if="stats.groups.length === 1" trigger="hover">
        <template #trigger>
          <span class="problem-stats-bar__scope-badge">{{ stats.groups[0].legacy_group_name || `班级${stats.groups[0].legacy_group_id}` }}</span>
        </template>
        统计范围：历史题库中的班级提交数据
      </n-tooltip>
    </div>
  </n-spin>
</template>

<style scoped>
.problem-stats-bar {
  display: flex;
  align-items: center;
  gap: 1.4em;
  flex-wrap: wrap;
}

.problem-stats-bar__metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 1.3;
}

.problem-stats-bar__value {
  font-size: 1.05em;
  font-weight: 600;
  color: #d9f6ff;
}

.problem-stats-bar__value--dashed {
  border-bottom: 1px dashed rgba(217, 246, 255, 0.4);
  cursor: help;
}

.problem-stats-bar__label {
  font-size: 0.72em;
  color: rgba(217, 246, 255, 0.5);
}

.problem-stats-bar__group-select {
  width: 160px;
}

.problem-stats-bar__scope-badge {
  font-size: 0.75em;
  color: rgba(217, 246, 255, 0.5);
  border: 1px solid rgba(110, 228, 255, 0.2);
  border-radius: 999px;
  padding: 0.15em 0.7em;
  cursor: help;
}
</style>
