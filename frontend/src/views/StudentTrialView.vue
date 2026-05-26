<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { NButton, useMessage } from 'naive-ui'
import DashboardShell from '../components/layout/DashboardShell.vue'
import {
  completeStudentTrial,
  fetchStudentTrials,
  joinStudentTrial,
  type StudentTrial,
} from '../api/studentTrials'
import { useAuthStore } from '../stores/auth'
import { showIncentiveFeedback } from '../utils/incentiveFeedback'

const message = useMessage()
const auth = useAuthStore()
const route = useRoute()
const highlightTrialId = computed(() => {
  const raw = route.query.trialId
  const parsed = raw ? Number(raw) : NaN
  return Number.isNaN(parsed) ? null : parsed
})

const loading = ref(true)
const errorMessage = ref('')
const trials = ref<StudentTrial[]>([])
const actingId = ref<number | null>(null)

const displayName = computed(() => auth.profile?.real_name || auth.profile?.username || 'Explorer')

async function loadTrials() {
  loading.value = true
  errorMessage.value = ''
  try {
    const data = await fetchStudentTrials()
    trials.value = data.trials
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载失败'
    trials.value = []
  } finally {
    loading.value = false
  }
}

async function onJoin(trial: StudentTrial) {
  actingId.value = trial.id
  try {
    await joinStudentTrial(trial.id)
    message.success(`已参与「${trial.title}」`)
    await loadTrials()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '参与失败')
  } finally {
    actingId.value = null
  }
}

async function onComplete(trial: StudentTrial) {
  actingId.value = trial.id
  try {
    const result = await completeStudentTrial(trial.id, trial.difficulty)
    showIncentiveFeedback(message, result.incentive)
    if (!result.incentive?.points_gained) {
      message.success(`完成试炼，获得 ${result.trial.reward_points} XP`)
    }
    if (auth.profile) {
      auth.profile.total_points = result.total_points
      if (result.incentive?.level) auth.profile.level = result.incentive.level
    }
    await loadTrials()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '完成失败')
  } finally {
    actingId.value = null
  }
}

onMounted(() => {
  void loadTrials()
})
</script>

<template>
  <DashboardShell
    active-nav="trial"
    page-title="试炼关卡"
    page-subtitle="参与班级试炼，赢取探索积分"
    search-placeholder="搜索试炼或知识点…"
    hide-search
  >
    <section class="student-trial" aria-label="学生试炼关卡">
      <p class="student-trial__welcome">你好，{{ displayName }} — 以下为班级进行中的试炼。</p>

      <div v-if="loading" class="student-trial__state">正在同步试炼列表…</div>
      <div v-else-if="errorMessage" class="student-trial__state student-trial__state--error">
        <span>{{ errorMessage }}</span>
        <n-button secondary size="small" @click="loadTrials()">重试</n-button>
      </div>
      <p v-else-if="!trials.length" class="student-trial__state">当前没有进行中的试炼，请稍后再来或联系教师发布任务。</p>

      <ul v-else class="student-trial__list">
        <li
          v-for="trial in trials"
          :key="trial.id"
          class="student-trial__card"
          :class="{ 'student-trial__card--highlight': highlightTrialId === trial.id }"
        >
          <header>
            <h2>{{ trial.title }}</h2>
            <span class="student-trial__badge">{{ trial.reward_points }} XP</span>
          </header>
          <p class="student-trial__meta">
            难度 {{ trial.difficulty }} · 约 {{ trial.duration_minutes }} 分钟 ·
            {{ trial.participant_count ?? 0 }} 人已参与
          </p>
          <p v-if="trial.my_status === 'completed'" class="student-trial__done">已完成（得分 {{ trial.my_score }}）</p>
          <div v-else class="student-trial__actions">
            <n-button
              v-if="!trial.my_status"
              type="primary"
              :loading="actingId === trial.id"
              @click="onJoin(trial)"
            >
              参与试炼
            </n-button>
            <n-button
              v-else
              type="primary"
              :loading="actingId === trial.id"
              @click="onComplete(trial)"
            >
              提交完成
            </n-button>
          </div>
        </li>
      </ul>
    </section>
  </DashboardShell>
</template>

<style scoped>
.student-trial {
  padding: 0 var(--plex-page-gutter-x, 1.25rem) 2rem;
  max-width: 720px;
}

.student-trial__welcome {
  margin: 0 0 1.25rem;
  color: rgba(226, 232, 240, 0.75);
  font-size: 0.92rem;
}

.student-trial__state {
  padding: 2rem 1rem;
  border-radius: 14px;
  background: rgba(5, 17, 29, 0.72);
  color: rgba(226, 232, 240, 0.8);
  text-align: center;
}

.student-trial__state--error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  color: #fecaca;
}

.student-trial__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 1rem;
}

.student-trial__card--highlight {
  border-color: rgba(251, 146, 60, 0.55);
  box-shadow: 0 0 0 1px rgba(251, 146, 60, 0.2), 0 12px 32px rgba(251, 146, 60, 0.12);
}

.student-trial__card {
  padding: 1.15rem 1.25rem;
  border: 1px solid rgba(130, 212, 255, 0.14);
  border-radius: 16px;
  background: linear-gradient(145deg, rgba(5, 18, 30, 0.92), rgba(3, 12, 20, 0.78));
}

.student-trial__card header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.student-trial__card h2 {
  margin: 0;
  color: #fff7ed;
  font-size: 1.1rem;
  font-weight: 650;
}

.student-trial__badge {
  flex-shrink: 0;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  background: rgba(251, 146, 60, 0.18);
  color: #fb923c;
  font-size: 0.78rem;
  font-weight: 700;
}

.student-trial__meta {
  margin: 0.5rem 0 0.85rem;
  color: rgba(221, 230, 239, 0.62);
  font-size: 0.84rem;
}

.student-trial__done {
  margin: 0;
  color: #34d399;
  font-size: 0.88rem;
  font-weight: 600;
}

.student-trial__actions {
  display: flex;
  gap: 0.5rem;
}
</style>
