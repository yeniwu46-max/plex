<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { PythonTrialQuestion } from '../../data/pythonTrialQuestions'
import { openPracticeQuestion, searchPracticeQuestions } from '../../utils/practiceQuestionNav'

const props = defineProps<{
  query: string
  visible?: boolean
}>()

const router = useRouter()
const loading = ref(false)
const hits = ref<PythonTrialQuestion[]>([])

watch(
  () => props.query,
  (value) => {
    void runSearch(value)
  },
  { immediate: true },
)

async function runSearch(raw: string) {
  const q = raw.trim()
  if (!q) {
    hits.value = []
    return
  }
  loading.value = true
  try {
    hits.value = await searchPracticeQuestions(q, 10)
  } finally {
    loading.value = false
  }
}

function openHit(question: PythonTrialQuestion) {
  void openPracticeQuestion(router, question)
}
</script>

<template>
  <div v-if="visible && query.trim()" class="question-search-popover" data-question-search-popover>
    <header>
      <strong>题目匹配</strong>
      <span>{{ loading ? '搜索中…' : hits.length ? `${hits.length} 条结果` : '无结果' }}</span>
    </header>
    <ul v-if="hits.length" class="question-search-popover__list">
      <li v-for="item in hits" :key="item.id">
        <button type="button" @click="openHit(item)">
          <em>{{ item.code || item.id }}</em>
          <span class="question-search-popover__title">{{ item.title }}</span>
          <small>{{ item.topic }}</small>
        </button>
      </li>
    </ul>
    <p v-else-if="!loading" class="question-search-popover__empty">试试题号（如 P0042）或关键词</p>
  </div>
</template>

<style scoped>
.question-search-popover {
  position: absolute;
  top: calc(100% + 0.45rem);
  left: 0;
  right: 0;
  z-index: 30;
  padding: 0.65rem 0.75rem;
  border: 1px solid rgba(16, 240, 192, 0.22);
  border-radius: 14px;
  background: rgba(4, 14, 24, 0.96);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
}

.question-search-popover header {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.45rem;
  color: rgba(224, 237, 247, 0.82);
  font-size: 0.82rem;
}

.question-search-popover header strong {
  color: #22ffde;
}

.question-search-popover__list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 280px;
  overflow-y: auto;
}

.question-search-popover__list li + li {
  margin-top: 0.35rem;
}

.question-search-popover__list button {
  width: 100%;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.15rem 0.65rem;
  padding: 0.55rem 0.65rem;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 10px;
  background: rgba(8, 22, 36, 0.72);
  color: #edf7ff;
  text-align: left;
  cursor: pointer;
}

.question-search-popover__list button:hover {
  border-color: rgba(16, 240, 192, 0.35);
  background: rgba(16, 240, 192, 0.08);
}

.question-search-popover__list em {
  grid-row: span 2;
  align-self: center;
  padding: 0.2rem 0.45rem;
  border-radius: 999px;
  background: rgba(16, 240, 192, 0.14);
  color: #22ffde;
  font-style: normal;
  font-size: 0.78rem;
  font-weight: 700;
}

.question-search-popover__title {
  font-size: 0.88rem;
  font-weight: 650;
}

.question-search-popover__list small {
  color: rgba(190, 208, 224, 0.72);
  font-size: 0.76rem;
}

.question-search-popover__empty {
  margin: 0.35rem 0 0;
  color: rgba(190, 208, 224, 0.68);
  font-size: 0.82rem;
}
</style>
