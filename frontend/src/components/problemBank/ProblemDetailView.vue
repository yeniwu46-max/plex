<script setup lang="ts">
/**
 * 题目详情展示组件：按 背景 → 标签 → 描述 → 输入格式 → 输出格式 → 样例 → 说明/提示
 * 的顺序渲染一道清洗后的标准化题目（见 backend/scripts/problem_bank_import/REPORT.md）。
 *
 * 2026-07-30 增强：
 * - 标题右侧统计条（提交/通过/时间限制，按旧系统班级口径，见 ProblemStatsBar）
 * - 1-5 星难度（StarRating）
 * - 洛谷风格标签 chips（ProblemTagChips），点击标签向上 emit 供父级做筛选跳转
 * - 中/EN 切换：仅当 has_english 为真时展示切换按钮，切换标题+描述+输入输出格式；
 *   题目背景故事目前只生成了中文版本（见 REPORT.md 增强#1 的取舍说明），不随语言切换变化。
 */
import { computed, ref, watch } from 'vue'
import { NEmpty, NSpin, NTag } from 'naive-ui'
import MarkdownRenderer from '../common/MarkdownRenderer.vue'
import CopyableBlock from './CopyableBlock.vue'
import StarRating from './StarRating.vue'
import ProblemTagChips from './ProblemTagChips.vue'
import ProblemStatsBar from './ProblemStatsBar.vue'
import { fetchProblemBankDetail, type ProblemDetail } from '../../api/problemBank'
import { formatHttpError } from '../../api/http'

const props = defineProps<{
  problemId: number | null
}>()

const emit = defineEmits<{
  (e: 'tag-click', code: string): void
}>()

const detail = ref<ProblemDetail | null>(null)
const loading = ref(false)
const error = ref('')
const lang = ref<'cn' | 'en'>('cn')

async function load(id: number) {
  loading.value = true
  error.value = ''
  detail.value = null
  lang.value = 'cn'
  try {
    detail.value = await fetchProblemBankDetail(id)
  } catch (err) {
    error.value = formatHttpError(err, '题目详情加载失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => props.problemId,
  (id) => {
    if (id) void load(id)
  },
  { immediate: true },
)

const displayTitle = computed(() => {
  if (!detail.value) return ''
  return lang.value === 'en' && detail.value.title_en ? detail.value.title_en : detail.value.title_cn
})
const displayDescription = computed(() => {
  if (!detail.value) return ''
  if (lang.value === 'en') return detail.value.description_en || ''
  return detail.value.description_cn || detail.value.description_en || ''
})
const displayInputFormat = computed(() => {
  if (!detail.value) return ''
  if (lang.value === 'en') return detail.value.input_format_en || ''
  return detail.value.input_format_cn || detail.value.input_format_en || ''
})
const displayOutputFormat = computed(() => {
  if (!detail.value) return ''
  if (lang.value === 'en') return detail.value.output_format_en || ''
  return detail.value.output_format_cn || detail.value.output_format_en || ''
})

function toggleLang() {
  lang.value = lang.value === 'cn' ? 'en' : 'cn'
}
</script>

<template>
  <n-spin :show="loading">
    <div v-if="error" class="problem-detail__error">{{ error }}</div>
    <div v-else-if="detail" class="problem-detail">
      <header class="problem-detail__header">
        <div class="problem-detail__title-row">
          <n-tag round type="primary" size="small">{{ detail.problem_no }}</n-tag>
          <h2>{{ displayTitle }}</h2>
          <StarRating :value="detail.star_difficulty" />
          <n-tag v-if="detail.concept" size="small" round>{{ detail.concept }}</n-tag>
          <button v-if="detail.has_english" type="button" class="problem-detail__lang-toggle" @click="toggleLang">
            {{ lang === 'cn' ? '中 / EN' : 'EN / 中' }}
          </button>
        </div>
        <ProblemStatsBar :problem-id="detail.id" />
      </header>

      <ProblemTagChips :tags="detail.tags" @tag-click="(code) => emit('tag-click', code)" />

      <section v-if="detail.background" class="problem-detail__section">
        <h3>题目背景</h3>
        <MarkdownRenderer :content="detail.background" />
      </section>

      <section v-if="displayDescription" class="problem-detail__section">
        <h3>题目描述</h3>
        <div class="problem-detail__lang-block">
          <MarkdownRenderer :content="displayDescription" />
        </div>
      </section>

      <section v-if="displayInputFormat" class="problem-detail__section">
        <h3>输入格式</h3>
        <MarkdownRenderer :content="displayInputFormat" />
      </section>

      <section v-if="displayOutputFormat" class="problem-detail__section">
        <h3>输出格式</h3>
        <MarkdownRenderer :content="displayOutputFormat" />
      </section>

      <section v-if="detail.samples.length" class="problem-detail__section">
        <h3>输入输出样例</h3>
        <div v-for="(sample, index) in detail.samples" :key="index" class="problem-detail__sample">
          <span class="problem-detail__sample-index">样例 {{ index + 1 }}</span>
          <div class="problem-detail__sample-pair">
            <CopyableBlock label="输入" :content="sample.input" max-height="140px" />
            <CopyableBlock label="输出" :content="sample.output" max-height="140px" />
          </div>
        </div>
      </section>

      <section v-if="detail.notes.length" class="problem-detail__section">
        <h3>说明 / 提示</h3>
        <ul class="problem-detail__notes">
          <li v-for="(note, index) in detail.notes" :key="index">{{ note }}</li>
        </ul>
      </section>
    </div>
    <n-empty v-else description="请选择一道题目查看详情" />
  </n-spin>
</template>

<style scoped>
.problem-detail {
  display: flex;
  flex-direction: column;
  gap: 1.2em;
}

.problem-detail__header {
  display: flex;
  flex-direction: column;
  gap: 0.6em;
  padding-bottom: 0.8em;
  border-bottom: 1px solid rgba(110, 228, 255, 0.14);
}

.problem-detail__title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6em;
}

.problem-detail__title-row h2 {
  margin: 0;
  font-size: 1.15em;
}

.problem-detail__lang-toggle {
  margin-left: auto;
  border: 1px solid rgba(110, 228, 255, 0.3);
  background: rgba(37, 245, 238, 0.08);
  color: #5ad9ff;
  border-radius: 999px;
  padding: 0.2em 0.85em;
  font-size: 0.78em;
  cursor: pointer;
}

.problem-detail__lang-toggle:hover {
  background: rgba(37, 245, 238, 0.18);
}

.problem-detail__section h3 {
  margin: 0 0 0.5em;
  font-size: 0.98em;
  color: #5ad9ff;
}

.problem-detail__lang-block {
  padding: 0.75em 0.9em;
  border-radius: 10px;
  background: rgba(4, 20, 30, 0.4);
  border: 1px solid rgba(110, 228, 255, 0.1);
}

.problem-detail__sample {
  margin-bottom: 0.9em;
}

.problem-detail__sample-index {
  display: inline-block;
  margin-bottom: 0.4em;
  font-size: 0.85em;
  color: rgba(217, 246, 255, 0.6);
}

.problem-detail__sample-pair {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.8em;
}

.problem-detail__notes {
  margin: 0;
  padding-left: 1.3em;
  font-size: 0.9em;
  color: rgba(217, 246, 255, 0.8);
  line-height: 1.7;
}

.problem-detail__error {
  color: #ff6b6b;
  padding: 1em 0;
}
</style>
