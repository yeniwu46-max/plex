<script setup lang="ts">
/**
 * 小E 回答附带的简化知识卡片（学生视图）。
 * 只展示：相关知识点 / 推荐下一步 / 参考来源。不展示相似度、rerank 分值等内部信息。
 */
import { computed, ref } from 'vue'
import { NIcon, NModal, NSpin, useMessage } from 'naive-ui'
import { BookOutline, CheckmarkCircleOutline, CompassOutline, SparklesOutline } from '@vicons/ionicons5'
import { useRouter } from 'vue-router'
import { KNOWLEDGE_TYPE_LABELS } from '../../api/knowledge'
import { fetchRagSource, type MessengerKnowledge, type RagRecommendedNext, type RagSourceDetail, type RagSourceView } from '../../api/rag'

const props = defineProps<{ knowledge: MessengerKnowledge }>()

const router = useRouter()
const message = useMessage()

const MASTERY_LABEL: Record<string, string> = {
  weak: '薄弱',
  learning: '学习中',
  mastered: '已掌握',
  unlearned: '未学习',
  recommended: '推荐',
}

const NEXT_LABEL: Record<RagRecommendedNext['type'], string> = {
  prerequisite: '先补前置',
  exercise: '去练一题',
  misconception: '检查误区',
  next: '继续学习',
  review: '巩固复习',
}

const visible = computed(() => {
  const k = props.knowledge
  return Boolean(k && k.knowledge_grounded && (k.sources?.length || k.concepts?.length || k.recommended_next?.length))
})

const focusConcepts = computed(() => (props.knowledge.concepts ?? []).filter((c) => c.role === 'focus'))
const relatedConcepts = computed(() => (props.knowledge.concepts ?? []).filter((c) => c.role !== 'focus').slice(0, 4))
const strategies = computed(() => (props.knowledge.teaching_strategy?.strategies ?? []).slice(0, 2))

const sourceOpen = ref(false)
const sourceLoading = ref(false)
const sourceDetail = ref<RagSourceDetail | null>(null)

async function openSource(source: RagSourceView) {
  sourceOpen.value = true
  sourceLoading.value = true
  sourceDetail.value = null
  try {
    sourceDetail.value = await fetchRagSource(source.chunk_id)
  } catch (error) {
    message.error((error as Error).message)
    sourceOpen.value = false
  } finally {
    sourceLoading.value = false
  }
}

function goNext(item: RagRecommendedNext) {
  if (item.type === 'exercise') {
    void router.push({ path: '/student/trials', query: { concept: item.concept_id } })
    return
  }
  void router.push({ path: '/student/star-path', query: { focus: item.concept_id } })
}
</script>

<template>
  <aside v-if="visible" class="kcard" aria-label="参考知识">
    <header class="kcard__head">
      <n-icon :component="SparklesOutline" />
      <strong>参考知识</strong>
      <small v-if="strategies.length">{{ strategies.map((s) => s.label).join(' · ') }}</small>
    </header>

    <section v-if="focusConcepts.length || relatedConcepts.length" class="kcard__row">
      <span class="kcard__label"><n-icon :component="BookOutline" />相关知识点</span>
      <div class="kcard__chips">
        <span v-for="c in focusConcepts" :key="c.concept_id" class="kchip kchip--focus">
          {{ c.name }}<i v-if="c.mastery_status && MASTERY_LABEL[c.mastery_status]">{{ MASTERY_LABEL[c.mastery_status] }}</i>
        </span>
        <span v-for="c in relatedConcepts" :key="c.concept_id" class="kchip">
          {{ c.name }}<i v-if="c.role === 'prerequisite'">前置</i>
        </span>
      </div>
    </section>

    <section v-if="knowledge.recommended_next?.length" class="kcard__row">
      <span class="kcard__label"><n-icon :component="CompassOutline" />推荐下一步</span>
      <ul class="kcard__next">
        <li v-for="item in knowledge.recommended_next.slice(0, 3)" :key="`${item.type}-${item.concept_id}`">
          <button type="button" @click="goNext(item)">
            <em>{{ NEXT_LABEL[item.type] ?? item.type }}</em>
            <strong>{{ item.name }}</strong>
          </button>
          <small>{{ item.reason }}</small>
        </li>
      </ul>
    </section>

    <section v-if="knowledge.sources?.length" class="kcard__row">
      <span class="kcard__label"><n-icon :component="CheckmarkCircleOutline" />来源</span>
      <ol class="kcard__sources">
        <li v-for="(s, i) in knowledge.sources.slice(0, 4)" :key="s.chunk_id">
          <button type="button" @click="openSource(s)">
            <span class="idx">S{{ i + 1 }}</span>
            <span class="title">{{ s.title || s.document_title }}</span>
            <span class="meta">
              {{ KNOWLEDGE_TYPE_LABELS[s.knowledge_type] ?? s.knowledge_type }}
              <template v-if="s.teacher_verified"> · 教师审核</template>
            </span>
          </button>
        </li>
      </ol>
    </section>

    <n-modal v-model:show="sourceOpen" preset="card" class="kcard__modal" :title="sourceDetail?.title || '参考来源'" style="width: min(720px, 92vw)">
      <n-spin :show="sourceLoading">
        <p v-if="sourceDetail" class="kcard__source-meta">
          {{ sourceDetail.document_title || sourceDetail.document?.title }}
          <template v-if="sourceDetail.teacher_verified"> · 教师审核</template>
          <template v-if="sourceDetail.source_page"> · 第 {{ sourceDetail.source_page }} 页</template>
        </p>
        <pre v-if="sourceDetail" class="kcard__source-body">{{ sourceDetail.content }}</pre>
      </n-spin>
    </n-modal>
  </aside>
</template>

<style scoped>
.kcard {
  margin: 0.7rem 0 0;
  padding: 0.7rem 0.85rem;
  border-radius: 12px;
  border: 1px solid rgba(110, 228, 255, 0.18);
  background: linear-gradient(160deg, rgba(6, 26, 40, 0.78), rgba(4, 18, 30, 0.7));
  display: grid;
  gap: 0.6rem;
  font-size: 0.8rem;
}
.kcard__head { display: flex; align-items: center; gap: 0.4rem; color: #7dd3fc; }
.kcard__head strong { color: #e0f2fe; font-size: 0.82rem; }
.kcard__head small { margin-left: auto; color: rgba(186, 230, 253, 0.6); font-size: 0.72rem; }
.kcard__row { display: grid; gap: 0.35rem; }
.kcard__label { display: inline-flex; align-items: center; gap: 0.3rem; color: rgba(186, 230, 253, 0.7); font-size: 0.72rem; }
.kcard__chips { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.kchip {
  display: inline-flex; align-items: center; gap: 0.3rem;
  padding: 0.18rem 0.6rem; border-radius: 999px;
  border: 1px solid rgba(110, 228, 255, 0.22); background: rgba(56, 189, 248, 0.08);
  color: #bae6fd; font-size: 0.74rem;
}
.kchip--focus { border-color: rgba(37, 245, 238, 0.45); background: rgba(37, 245, 238, 0.1); color: #ccfbf1; }
.kchip i { font-style: normal; color: rgba(186, 230, 253, 0.55); font-size: 0.68rem; }
.kcard__next { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.35rem; }
.kcard__next button {
  display: inline-flex; align-items: center; gap: 0.45rem;
  padding: 0.25rem 0.55rem; border-radius: 8px; border: 1px solid rgba(37, 245, 238, 0.2);
  background: rgba(37, 245, 238, 0.06); color: #e0f2fe; cursor: pointer; font-size: 0.76rem;
}
.kcard__next button:hover { background: rgba(37, 245, 238, 0.14); }
.kcard__next em { font-style: normal; color: #25f5ee; font-size: 0.7rem; }
.kcard__next small { display: block; margin: 0.15rem 0 0 0.2rem; color: rgba(186, 230, 253, 0.55); font-size: 0.72rem; }
.kcard__sources { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.25rem; }
.kcard__sources button {
  display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 0.5rem; align-items: center; width: 100%;
  padding: 0.3rem 0.5rem; border-radius: 8px; border: 1px solid transparent; background: transparent;
  color: rgba(224, 242, 254, 0.85); text-align: left; cursor: pointer; font-size: 0.76rem;
}
.kcard__sources button:hover { border-color: rgba(110, 228, 255, 0.22); background: rgba(56, 189, 248, 0.06); }
.kcard__sources .idx { color: #25f5ee; font-size: 0.7rem; font-family: Consolas, monospace; }
.kcard__sources .title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kcard__sources .meta { color: rgba(186, 230, 253, 0.5); font-size: 0.7rem; white-space: nowrap; }
.kcard__source-meta { margin: 0 0 0.5rem; color: rgba(186, 230, 253, 0.65); font-size: 0.76rem; }
.kcard__source-body { margin: 0; padding: 0.7rem; border-radius: 8px; background: rgba(4, 14, 24, 0.85); color: rgba(224, 242, 254, 0.9); font-size: 0.8rem; line-height: 1.55; white-space: pre-wrap; word-break: break-word; max-height: 60vh; overflow: auto; }
</style>
