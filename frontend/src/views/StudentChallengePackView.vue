<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NTag } from 'naive-ui'
import DashboardShell from '../components/layout/DashboardShell.vue'
import { fetchStudentChallengePack, type StoreChallengePack } from '../api/studentStore'

defineOptions({ name: 'StudentChallengePackView' })

const route = useRoute()
const router = useRouter()
const pack = ref<StoreChallengePack | null>(null)
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  const code = String(route.params.productCode || '')
  try {
    pack.value = await fetchStudentChallengePack(code)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '挑战包加载失败'
  } finally {
    loading.value = false
  }
}

function start(questionId: string) {
  const packCode = pack.value?.product_code
  if (!packCode) return
  void router.push({
    path: `/student/trials/practice/${encodeURIComponent(questionId)}`,
    query: { pack_code: packCode },
  })
}

onMounted(() => void load())
</script>

<template>
  <DashboardShell active-nav="store" :page-title="pack?.title || '星轨挑战包'" page-subtitle="完成额外挑战，继续推进你的探索记录" search-placeholder="" hide-search>
    <main class="challenge-page">
      <header class="challenge-header">
        <div><span>PLEX · EXTRA MISSION</span><h1>{{ pack?.title || '算法基础 · 星轨挑战包' }}</h1><p>本挑战包为额外内容；主学习路径和基础练习仍然免费开放。</p></div>
        <n-button secondary round @click="router.push('/student/store')">返回星港补给站</n-button>
      </header>
      <section v-if="loading" class="challenge-state">正在载入挑战内容…</section>
      <section v-else-if="error" class="challenge-state challenge-state--error">
        <p>{{ error }}</p>
        <n-button type="primary" round @click="router.push('/student/store')">查看开通方式</n-button>
      </section>
      <section v-else-if="pack" class="challenge-list">
        <article v-for="(question, index) in pack.questions" :key="question.id" class="challenge-card">
          <div class="challenge-card__number">{{ String(index + 1).padStart(2, '0') }}</div>
          <div class="challenge-card__content">
            <span>{{ question.code }} · {{ question.topic || '算法基础' }}</span>
            <h2>{{ question.title }}</h2>
            <div class="challenge-card__meta"><n-tag size="small" round :bordered="false">{{ question.difficulty }}</n-tag><small>约 {{ question.duration_min }} 分钟</small></div>
          </div>
          <n-button type="primary" round @click="start(question.id)">开始挑战</n-button>
        </article>
      </section>
      <p v-if="pack" class="challenge-count">{{ pack.total }} 道精选挑战 · XP 和成绩规则与免费练习一致</p>
    </main>
  </DashboardShell>
</template>

<style scoped>
.challenge-page { width: min(1040px, 100%); margin: 0 auto; padding: 2rem clamp(1rem, 3vw, 2.5rem) 4rem; color: #e7f4fa; }
.challenge-header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 1.6rem; border: 1px solid rgba(61,236,221,.17); border-radius: 24px; background: radial-gradient(circle at 85% 20%, rgba(42,208,197,.18), transparent 34%), #0b1b2b; }
.challenge-header span { color: #73eadd; font-size: .74rem; font-weight: 800; letter-spacing: .12em; }
.challenge-header h1 { margin: .5rem 0; color: #f4fbff; font-size: clamp(1.6rem, 4vw, 2.4rem); }
.challenge-header p { margin: 0; color: rgba(219,235,244,.66); }
.challenge-list { display: grid; gap: .8rem; margin-top: 1.3rem; }
.challenge-card { display: grid; grid-template-columns: 54px 1fr auto; align-items: center; gap: 1rem; padding: 1rem 1.2rem; border: 1px solid rgba(124,209,221,.12); border-radius: 18px; background: linear-gradient(120deg, rgba(14,34,50,.96), rgba(8,18,31,.96)); }
.challenge-card__number { display: grid; place-items: center; width: 48px; height: 48px; border: 1px solid rgba(86,227,215,.2); border-radius: 15px; color: #79ecdc; font-weight: 800; }
.challenge-card__content > span { color: rgba(219,235,244,.48); font-size: .78rem; }
.challenge-card h2 { margin: .2rem 0 .45rem; color: #effaff; font-size: 1.05rem; }
.challenge-card__meta { display: flex; align-items: center; gap: .6rem; color: rgba(219,235,244,.54); }
.challenge-count { margin: 1rem 0; color: rgba(219,235,244,.5); text-align: center; font-size: .85rem; }
.challenge-state { padding: 3rem 1rem; color: rgba(219,235,244,.65); text-align: center; }
.challenge-state--error { color: #ffd083; }
@media (max-width: 640px) { .challenge-header { align-items: stretch; flex-direction: column; } .challenge-card { grid-template-columns: 42px 1fr; } .challenge-card__number { width: 40px; height: 40px; } .challenge-card > .n-button { grid-column: 2; justify-self: start; } }
</style>
