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
import { DAILY_QUESTS } from '../data/dailyQuests'

const auth = useAuthStore()
const overview = ref<StudentOverview | null>(null)
const loading = ref(true)
const errorMessage = ref('')

const profile = computed(() => overview.value?.profile)
const displayName = computed(() => profile.value?.real_name || profile.value?.username || auth.profile?.real_name || '同学')
const level = computed(() => profile.value?.level ?? auth.profile?.level ?? 1)
const totalPoints = computed(() => profile.value?.total_points ?? auth.profile?.total_points ?? 0)
const xpTarget = computed(() => Math.max(500, level.value * 500))
const xpRatio = computed(() => Math.min(100, Math.round((totalPoints.value / xpTarget.value) * 100)))
const completedQuests = computed(() => 1)
const totalQuestReward = computed(() => DAILY_QUESTS.reduce((sum, quest) => sum + quest.rewardXp, 0))
const classRankLabel = computed(() => {
  if (!profile.value?.class) return '暂未加入班级'
  return profile.value.class_rank ? `第 ${profile.value.class_rank} 名` : '暂无排名'
})

const statCards = computed(() => [
  { key: 'level', label: '当前等级', value: `Lv.${level.value}`, icon: RocketOutline, tone: 'teal' },
  { key: 'points', label: '累计 XP', value: String(totalPoints.value), icon: FlameOutline, tone: 'amber' },
  { key: 'streak', label: '连续探索', value: `${profile.value?.consecutive_days ?? 0} 天`, icon: CalendarOutline, tone: 'blue' },
  { key: 'rank', label: '班级排名', value: classRankLabel.value, icon: TrophyOutline, tone: 'purple' },
])

const quickLinks = [
  { title: '探索舱', desc: '查看学习星域与资源状态', to: '/discovery', icon: RocketOutline },
  { title: '今日委托', desc: '完成今日任务并领取反馈', to: '/daily', icon: CalendarOutline },
  { title: '探索档案', desc: '查看成长轨迹与成就收藏', to: '/archives', icon: ArchiveOutline },
  { title: '试炼关卡', desc: '选择适合你的挑战入口', to: '/trial-arena', icon: BarbellOutline },
]

async function loadOverview() {
  loading.value = true
  errorMessage.value = ''
  try {
    overview.value = await fetchStudentOverview()
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
              <RouterLink to="/daily" class="primary-link">继续今日委托</RouterLink>
              <RouterLink to="/discovery" class="ghost-link">进入探索舱</RouterLink>
            </div>
          </div>
          <div class="hero-band__meter" aria-label="等级进度">
            <span class="meter-ring" :style="{ '--progress': `${xpRatio}%` }">
              <strong>{{ xpRatio }}</strong>
              <em>%</em>
            </span>
            <p>Lv.{{ level }} 进度</p>
            <small>{{ totalPoints }} / {{ xpTarget }} XP</small>
          </div>
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
              <RouterLink to="/daily">查看全部</RouterLink>
            </div>
            <div class="quest-mini-list">
              <article v-for="quest in DAILY_QUESTS" :key="quest.key" class="quest-mini">
                <span class="quest-mini__time">{{ quest.time }}</span>
                <div>
                  <strong>{{ quest.title }}</strong>
                  <p>{{ quest.description }}</p>
                </div>
                <em>+{{ quest.rewardXp }} XP</em>
              </article>
            </div>
          </div>

          <div class="mission-panel">
            <div class="section-head">
              <h2>成长摘要</h2>
              <RouterLink to="/archives">打开档案</RouterLink>
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
