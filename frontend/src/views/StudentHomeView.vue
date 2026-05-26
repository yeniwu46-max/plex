<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { NIcon } from 'naive-ui'
import {
  ArchiveOutline,
  BarbellOutline,
  CalendarOutline,
  FlameOutline,
  RibbonOutline,
  RocketOutline,
  TrophyOutline,
} from '@vicons/ionicons5'
import DashboardShell from '../components/layout/DashboardShell.vue'
import { useAuthStore } from '../stores/auth'
import { fetchStudentOverview, type StudentOverview } from '../api/studentOverview'
import { fetchDashboardExtras } from '../api/studentProgress'
import { DAILY_QUESTS } from '../data/dailyQuests'

const auth = useAuthStore()
const overview = ref<StudentOverview | null>(null)
const runningTrials = ref(0)
const loading = ref(true)
const errorMessage = ref('')

const profile = computed(() => overview.value?.profile)
const displayName = computed(() => profile.value?.real_name || profile.value?.username || auth.profile?.real_name || '同学')
const level = computed(() => profile.value?.level ?? auth.profile?.level ?? 1)
const totalPoints = computed(() => profile.value?.total_points ?? auth.profile?.total_points ?? 0)
const levelProfile = computed(() => profile.value?.level_profile ?? profile.value?.incentive?.level_profile)
const xpTarget = computed(
  () => levelProfile.value?.next_threshold ?? Math.max(500, level.value * 500),
)
const xpRatio = computed(
  () => levelProfile.value?.progress_percent ?? Math.min(100, Math.round((totalPoints.value / xpTarget.value) * 100)),
)
const rankTitle = computed(() => profile.value?.title || profile.value?.level_profile?.title || `Lv.${level.value}`)
const weekPoints = computed(() => profile.value?.incentive?.week_points ?? 0)
const nextAchievement = computed(() => profile.value?.incentive?.next_achievements?.[0])
const daily = computed(() => overview.value?.daily)
const completedQuests = computed(() => daily.value?.completed_count ?? 0)
const totalQuests = computed(() => daily.value?.total_count ?? DAILY_QUESTS.length)
const totalQuestReward = computed(
  () => daily.value?.quests.reduce((sum, quest) => sum + quest.reward_xp, 0) ?? DAILY_QUESTS.reduce((sum, quest) => sum + quest.rewardXp, 0),
)
const dailyQuestItems = computed(() => {
  if (!daily.value) {
    return DAILY_QUESTS.map((quest) => ({
      key: quest.key,
      time: quest.time,
      title: quest.title,
      description: quest.description,
      rewardXp: quest.rewardXp,
      current: 0,
      total: quest.total,
      completed: false,
    }))
  }
  return daily.value.quests.map((quest) => ({
    key: quest.key,
    time: quest.time,
    title: quest.title,
    description: quest.description ?? '',
    rewardXp: quest.reward_xp,
    current: quest.current,
    total: quest.total,
    completed: quest.completed,
  }))
})
const classRankLabel = computed(() => {
  if (!profile.value?.class) return '暂未加入班级'
  return profile.value.class_rank ? `第 ${profile.value.class_rank} 名` : '暂无排名'
})

const statCards = computed(() => [
  { key: 'level', label: '当前等级', value: `Lv.${level.value}`, icon: RocketOutline, tone: 'teal' },
  { key: 'points', label: '累计 XP', value: String(totalPoints.value), icon: FlameOutline, tone: 'amber' },
  { key: 'streak', label: '连续探索', value: `${profile.value?.consecutive_days ?? 0} 天`, icon: CalendarOutline, tone: 'blue' },
  { key: 'rank', label: '班级排名', value: classRankLabel.value, icon: TrophyOutline, tone: 'purple' },
  { key: 'quests', label: '今日委托', value: `${completedQuests.value}/${totalQuests.value}`, icon: CalendarOutline, tone: 'blue' },
])

const quickLinks = computed(() => [
  { title: '探索舱', desc: '查看学习星域与资源状态', to: '/student/discovery', icon: RocketOutline },
  { title: '今日委托', desc: '完成今日任务并领取反馈', to: '/student/daily', icon: CalendarOutline },
  { title: '探索档案', desc: '查看成长轨迹与成就收藏', to: '/student/archives', icon: ArchiveOutline },
  {
    title: '试炼关卡',
    desc:
      runningTrials.value > 0
        ? `班级有 ${runningTrials.value} 场试炼进行中，点击参与`
        : '选择适合你的挑战入口',
    to: '/student/trials',
    icon: BarbellOutline,
  },
])

async function loadOverview() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [overviewResult, extras] = await Promise.all([
      fetchStudentOverview(),
      fetchDashboardExtras().catch(() => ({ running_trials: 0 })),
    ])
    overview.value = overviewResult
    runningTrials.value = extras.running_trials
    auth.syncProfile({
      id: overview.value.profile.id,
      username: overview.value.profile.username,
      email: overview.value.profile.email,
      real_name: overview.value.profile.real_name ?? overview.value.profile.username,
      role: overview.value.profile.role ?? 'student',
      level: overview.value.profile.level,
      total_points: overview.value.profile.total_points,
    })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '学生端数据加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadOverview)
</script>

<template>
  <DashboardShell
    active-nav="cabin"
    page-title="学生首页"
    page-subtitle="今日主线总览，连接探索、委托、档案与试炼"
    search-placeholder="搜索课程、任务、知识点…"
  >
    <section class="student-home" aria-label="学生端总览">
      <div v-if="loading" class="state-panel">正在同步你的探索数据…</div>
      <div v-else-if="errorMessage" class="state-panel state-panel--error">
        <span>{{ errorMessage }}</span>
        <button type="button" @click="loadOverview">重试</button>
      </div>
      <template v-else>
        <section class="hero-band">
          <div class="hero-band__copy">
            <p class="hero-band__eyebrow">Explorer · {{ displayName }}</p>
            <h2>今天从一条清晰的学习主线开始</h2>
            <p>
              你当前累计 {{ totalPoints }} XP，今日委托已开启 {{ completedQuests }}/{{ DAILY_QUESTS.length }}，
              完成全部可获得 {{ totalQuestReward }} XP 反馈。
            </p>
            <div class="hero-band__actions">
              <RouterLink to="/student/daily" class="primary-link">继续今日委托</RouterLink>
              <RouterLink to="/student/discovery" class="ghost-link">进入探索舱</RouterLink>
            </div>
          </div>
          <div class="hero-band__meter" aria-label="等级进度">
            <span class="meter-ring" :style="{ '--progress': `${xpRatio}%` }">
              <strong>{{ xpRatio }}</strong>
              <em>%</em>
            </span>
            <p>{{ rankTitle }}</p>
            <small>{{ totalPoints }} / {{ xpTarget }} XP · 本周 +{{ weekPoints }}</small>
          </div>
        </section>

        <section v-if="nextAchievement" class="achievement-hint" aria-label="下一成就">
          <span>下一成就 · {{ nextAchievement.name }}</span>
          <div class="achievement-hint__bar">
            <i :style="{ width: `${nextAchievement.progress_percent}%` }" />
          </div>
          <small>{{ nextAchievement.current_value }} / {{ nextAchievement.target_value }}</small>
        </section>

        <section class="stat-grid" aria-label="学习状态">
          <article v-for="item in statCards" :key="item.key" class="stat-card" :class="`stat-card--${item.tone}`">
            <n-icon :component="item.icon" class="stat-card__icon" />
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </article>
        </section>

        <section class="home-grid">
          <div class="mission-panel">
            <div class="section-head">
              <h2>今日委托</h2>
              <RouterLink to="/student/daily">查看全部</RouterLink>
            </div>
            <div class="quest-mini-list">
              <article v-for="quest in dailyQuestItems" :key="quest.key" class="quest-mini">
                <span class="quest-mini__time">{{ quest.time }}</span>
                <div>
                  <strong>{{ quest.title }}</strong>
                  <p>{{ quest.description }}</p>
                </div>
                <em>+{{ quest.rewardXp }} XP {{ quest.current }}/{{ quest.total }}</em>
              </article>
            </div>
          </div>

          <div class="mission-panel">
            <div class="section-head">
              <h2>成长摘要</h2>
              <RouterLink to="/student/archives">打开档案</RouterLink>
            </div>
            <dl class="summary-list">
              <div>
                <dt>所属班级</dt>
                <dd>{{ profile?.class?.name || '暂未加入班级' }}</dd>
              </div>
              <div>
                <dt>已解锁成就</dt>
                <dd>{{ overview?.achievements?.count ?? profile?.achievements_count ?? 0 }} 枚</dd>
              </div>
              <div>
                <dt>最近积分记录</dt>
                <dd>{{ overview?.pointsLog?.total ? `${overview.pointsLog.total} 条` : '暂无记录' }}</dd>
              </div>
            </dl>
            <div class="archive-badge">
              <n-icon :component="RibbonOutline" />
              <span>{{ profile?.title || `Lv${level}` }}</span>
            </div>
          </div>
        </section>

        <section class="quick-entry" aria-label="快捷入口">
          <RouterLink v-for="item in quickLinks" :key="item.to" :to="item.to" class="entry-tile">
            <n-icon :component="item.icon" />
            <span>
              <strong>{{ item.title }}</strong>
              <small>{{ item.desc }}</small>
            </span>
            <em aria-hidden="true">›</em>
          </RouterLink>
        </section>
      </template>
    </section>
  </DashboardShell>
</template>

<style scoped>
.student-home {
  height: 100%;
  overflow: auto;
  padding: 0.6rem 2.8rem 2.4rem 3.7rem;
}

.state-panel {
  display: flex;
  min-height: 260px;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  border: 1px solid rgba(90, 208, 255, 0.12);
  border-radius: 0.85rem;
  background: rgba(5, 17, 29, 0.72);
  color: rgba(226, 232, 240, 0.82);
}

.state-panel--error {
  color: #fecaca;
}

.state-panel button,
.primary-link,
.ghost-link {
  min-height: 42px;
  border: 1px solid rgba(46, 255, 241, 0.32);
  border-radius: 999px;
  padding: 0 1rem;
  background: rgba(46, 255, 241, 0.1);
  color: #eaffff;
  text-decoration: none;
  cursor: pointer;
  font-weight: 700;
}

.hero-band {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 220px;
  gap: 1.5rem;
  align-items: center;
  padding: 1.6rem;
  border: 1px solid rgba(90, 208, 255, 0.12);
  border-radius: 0.9rem;
  background:
    radial-gradient(circle at 82% 12%, rgba(194, 97, 255, 0.12), transparent 30%),
    linear-gradient(135deg, rgba(8, 28, 46, 0.88), rgba(5, 17, 29, 0.78));
}

.hero-band__eyebrow {
  margin: 0 0 0.65rem;
  color: #31ffef;
  font-size: 0.85rem;
  font-weight: 700;
}

.hero-band h2 {
  margin: 0;
  color: #ffffff;
  font-size: clamp(1.7rem, 2.4vw, 2.55rem);
  line-height: 1.12;
}

.hero-band p {
  max-width: 680px;
  margin: 0.85rem 0 0;
  color: rgba(226, 232, 240, 0.76);
  line-height: 1.7;
}

.hero-band__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.8rem;
  margin-top: 1.25rem;
}

.primary-link {
  display: inline-flex;
  align-items: center;
  border-color: transparent;
  background: linear-gradient(90deg, #19f0c9, #54f9ef);
  color: #02111f;
}

.ghost-link {
  display: inline-flex;
  align-items: center;
  background: transparent;
  color: #52fff1;
}

.hero-band__meter {
  display: grid;
  justify-items: center;
  gap: 0.45rem;
}

.meter-ring {
  --progress: 0%;
  display: grid;
  width: 150px;
  aspect-ratio: 1;
  place-items: center;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, #071625 57%, transparent 58%),
    conic-gradient(#7bf8ff var(--progress), rgba(75, 128, 160, 0.24) 0);
}

.meter-ring strong {
  color: #ffffff;
  font-size: 2rem;
}

.meter-ring em {
  margin-top: -2.8rem;
  color: rgba(226, 232, 240, 0.68);
  font-style: normal;
}

.achievement-hint {
  margin-bottom: 1rem;
  padding: 0.9rem 1.1rem;
  border-radius: 14px;
  border: 1px solid rgba(130, 212, 255, 0.14);
  background: rgba(5, 17, 29, 0.72);
}

.achievement-hint__bar {
  height: 6px;
  margin: 0.55rem 0 0.35rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.achievement-hint__bar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #2efff1, #ffc86b);
}

.hero-band__meter p,
.hero-band__meter small {
  margin: 0;
  color: rgba(226, 232, 240, 0.72);
}

.stat-grid,
.quick-entry {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.9rem;
  margin-top: 1rem;
}

.stat-card,
.entry-tile,
.mission-panel {
  border: 1px solid rgba(90, 208, 255, 0.12);
  border-radius: 0.85rem;
  background: rgba(5, 17, 29, 0.72);
}

.stat-card {
  display: grid;
  gap: 0.45rem;
  padding: 1rem;
}

.stat-card__icon {
  color: var(--card-color);
  font-size: 1.6rem;
}

.stat-card span {
  color: rgba(226, 232, 240, 0.62);
  font-size: 0.8rem;
}

.stat-card strong {
  color: #ffffff;
  font-size: 1.2rem;
}

.stat-card--teal {
  --card-color: #2efff1;
}

.stat-card--amber {
  --card-color: #ffc56d;
}

.stat-card--blue {
  --card-color: #58a9ff;
}

.stat-card--purple {
  --card-color: #c261ff;
}

.home-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
  gap: 1rem;
  margin-top: 1rem;
}

.mission-panel {
  padding: 1.2rem;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.section-head h2 {
  margin: 0;
  color: #31ffef;
  font-size: 1rem;
}

.section-head a {
  color: rgba(82, 255, 241, 0.8);
  font-size: 0.82rem;
  text-decoration: none;
}

.quest-mini-list,
.summary-list {
  display: grid;
  gap: 0.72rem;
}

.quest-mini {
  display: grid;
  grid-template-columns: 4.2rem minmax(0, 1fr) auto;
  gap: 0.8rem;
  align-items: center;
  padding: 0.75rem;
  border-radius: 0.65rem;
  background: rgba(255, 255, 255, 0.04);
}

.quest-mini__time,
.quest-mini em {
  color: #52fff1;
  font-style: normal;
  font-weight: 700;
}

.quest-mini strong,
.entry-tile strong {
  color: #ffffff;
}

.quest-mini p,
.entry-tile small,
.summary-list dt {
  margin: 0.25rem 0 0;
  color: rgba(226, 232, 240, 0.62);
  font-size: 0.78rem;
}

.summary-list {
  margin: 0;
}

.summary-list div {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding-bottom: 0.7rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.summary-list dd {
  margin: 0;
  color: #ffffff;
  font-weight: 700;
  text-align: right;
}

.archive-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
  color: #ffc56d;
  font-weight: 700;
}

.quick-entry {
  padding-bottom: 0.2rem;
}

.entry-tile {
  display: grid;
  grid-template-columns: 2rem minmax(0, 1fr) auto;
  gap: 0.75rem;
  align-items: center;
  min-height: 92px;
  padding: 1rem;
  color: inherit;
  text-decoration: none;
}

.entry-tile > .n-icon {
  color: #52fff1;
  font-size: 1.6rem;
}

.entry-tile em {
  color: rgba(82, 255, 241, 0.78);
  font-size: 1.5rem;
  font-style: normal;
}

@media (max-width: 1100px) {
  .student-home {
    padding-inline: 1rem;
  }

  .hero-band,
  .home-grid {
    grid-template-columns: 1fr;
  }

  .stat-grid,
  .quick-entry {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .stat-grid,
  .quick-entry,
  .quest-mini {
    grid-template-columns: 1fr;
  }

  .hero-band {
    padding: 1.1rem;
  }
}
</style>
