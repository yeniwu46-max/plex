<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton } from 'naive-ui'
import DashboardShell from '../components/layout/DashboardShell.vue'
import PythonTrialWorkspace from '../components/trial/PythonTrialWorkspace.vue'
import { getPythonTrialQuestion } from '../data/pythonTrialQuestions'
import { getStarPathNodeByQuestionId } from '../data/starPathTrail'

const route = useRoute()
const router = useRouter()

const questionId = computed(() => String(route.params.questionId ?? ''))
const question = computed(() => getPythonTrialQuestion(questionId.value))
const starPathNode = computed(() => getStarPathNodeByQuestionId(questionId.value))
const pageSubtitle = computed(() => {
  if (!question.value) return 'Python 入门 · 代码试炼'
  if (starPathNode.value) {
    return `星轨 ${starPathNode.value.id} ${starPathNode.value.title} · ${question.value.title}`
  }
  return `${question.value.topic} · ${question.value.title}`
})
</script>

<template>
  <DashboardShell
    active-nav="trial"
    page-title="试炼关卡"
    :page-subtitle="pageSubtitle"
    search-placeholder="搜索题目…"
    hide-search
  >
    <PythonTrialWorkspace v-if="question" :question="question" />
    <section v-else class="practice-missing" aria-label="题目不存在">
      <p>未找到该题目，可能已被移除或链接有误。</p>
      <n-button type="primary" @click="router.push('/student/trials')">返回题目列表</n-button>
    </section>
  </DashboardShell>
</template>

<style scoped>
.practice-missing {
  display: flex;
  min-height: 280px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin: 0 var(--plex-page-gutter-x, 1.25rem);
  padding: 2rem;
  border-radius: 16px;
  background: rgba(5, 17, 29, 0.72);
  color: rgba(226, 232, 240, 0.78);
  text-align: center;
}
</style>
