<script setup lang="ts">
import { computed, onActivated, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { RouterLink } from 'vue-router'
import { NIcon } from 'naive-ui'
import {
  FlameOutline,
  CalendarOutline,
  RibbonOutline,
  RocketOutline,
  TrophyOutline,
} from '@vicons/ionicons5'
import DashboardShell from '../components/layout/DashboardShell.vue'
import { useAuthStore } from '../stores/auth'
import { claimDailyQuestBonus, type StudentOverview } from '../api/studentOverview'
import { DAILY_QUESTS } from '../data/dailyQuests'
import TeacherAssignmentPanel from '../components/student/TeacherAssignmentPanel.vue'
import { useStudentWorkspaceStore } from '../stores/studentWorkspace'
import { useMessage } from 'naive-ui'
import { scrollToHashAnchor } from '../utils/navigation'

const route = useRoute()

const auth = useAuthStore()
const workspace = useStudentWorkspaceStore()
const message = useMessage()
const overview = ref<StudentOverview | null>(null)
const loading = ref(true)
const errorMessage = ref('')

const profile = computed(() => overview.value?.profile)
const displayName = computed(() => profile.value?.real_name || profile.value?.username || auth.profile?.real_name || '同学')
const level = computed(() => profile.value?.level ?? auth.profile?.level ?? 1)
const totalPoints = computed(() => profile.value?.total_points ?? auth.profile?.total_points ?? 0)
const levelProfile = computed(() => profile.value?.level_profile ?? profile.value?.incentive?.level_profile)
const atMaxLevel = computed(
  () => Boolean(levelProfile.value?.at_max_level) || level.value >= (levelProfile.value?.max_level ?? 10),
)
const xpFloor = computed(() => levelProfile.value?.current_threshold ?? 0)
const xpTarget = computed(() => {
  const lp = levelProfile.value
  if (!lp) return Math.max(500, level.value * 500)
  if (lp.next_threshold != null) return lp.next_threshold
  return lp.current_threshold + Math.max(500, level.value * 200)
})
const xpDisplayCurrent = computed(() => {
  const points = totalPoints.value
  if (atMaxLevel.value) return Math.min(points, xpTarget.value)
  return points
})
const xpRatio = computed(() => {
  if (levelProfile.value?.progress_percent != null) {
    return Math.min(100, Math.max(0, levelProfile.value.progress_percent))
  }
  const span = xpTarget.value - xpFloor.value
  if (span <= 0) return 100
  return Math.min(100, Math.round(((xpDisplayCurrent.value - xpFloor.value) / span) * 100))
})
const rankTitle = computed(() => profile.value?.title || profile.value?.level_profile?.title || `Lv.${level.value}`)
const weekPoints = computed(() => profile.value?.incentive?.week_points ?? 0)
const nextAchievement = computed(() => profile.value?.incentive?.next_achievements?.[0])
const daily = computed(() => overview.value?.daily)
const teacherAssignments = computed(() => daily.value?.teacher_assignments ?? { pending_count: 0, total_count: 0, items: [] })
const completedQuests = computed(() => daily.value?.completed_count ?? 0)
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
const classDisplayLabel = computed(() => {
  const cls = profile.value?.class
  if (!cls) return '暂未加入班级'
  const code = cls.join_code ? ` · 编号 ${cls.join_code}` : ''
  return `${cls.name || `班级 #${cls.id}`}${code}`
})

const statCards = computed(() => [
  { key: 'level', label: '当前等级', value: `Lv.${level.value}`, icon: RocketOutline, tone: 'teal' },
  { key: 'points', label: '累计 XP', value: String(totalPoints.value), icon: FlameOutline, tone: 'amber' },
  { key: 'streak', label: '连续探索', value: `${profile.value?.consecutive_days ?? 0} 天`, icon: CalendarOutline, tone: 'blue' },
  { key: 'rank', label: '班级排名', value: classRankLabel.value, icon: TrophyOutline, tone: 'purple' },
])

async function loadOverview(opts?: { soft?: boolean }) {
  const soft = Boolean(opts?.soft && overview.value)
  if (!soft) loading.value = true
  errorMessage.value = ''
  try {
    overview.value = await workspace.loadOverview(false)
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
    if (!soft) loading.value = false
  }
}

async function claimBonus() {
  try {
    const result = await claimDailyQuestBonus()
    if (overview.value) overview.value.daily = result
    workspace.invalidateOverview()
    message.success('今日委托奖励已领取')
  } catch (error) {
    message.error(error instanceof Error ? error.message : '领取奖励失败')
  }
}

function onAssignmentsUpdated(payload: { daily: StudentOverview['daily'] }) {
  if (overview.value && payload.daily) overview.value.daily = payload.daily
  workspace.invalidateOverview()
}

onMounted(() => {
  void loadOverview()
  if (route.hash) void scrollToHashAnchor(route.hash)
})

onActivated(() => {
  // KeepAlive 回跳：尊重 30s TTL，且不闪 loading
  if (overview.value) void loadOverview({ soft: true })
  if (route.hash) void scrollToHashAnchor(route.hash)
})

watch(
  () => route.hash,
  (hash) => {
    if (hash) void scrollToHashAnchor(hash)
  },
)
</script>

<template>
  <DashboardShell
    active-nav="home"
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
              <RouterLink to="/student/discovery" class="primary-link">进入探索舱</RouterLink>
            </div>
          </div>
          <div class="hero-band__meter" aria-label="等级进度">
            <div class="meter-hud" :style="{ '--progress': `${xpRatio}%` }">
              <span class="meter-hud__glow" aria-hidden="true" />
              <span class="meter-hud__ticks" aria-hidden="true" />
              <span class="meter-ring">
                <span class="meter-ring__inner">
                  <strong>{{ xpRatio }}</strong>
                  <em>%</em>
                </span>
              </span>
              <span class="meter-hud__scan" aria-hidden="true" />
            </div>
            <p>{{ rankTitle }}</p>
            <small>{{ xpDisplayCurrent }} / {{ xpTarget }} XP · 本周 +{{ weekPoints }}</small>
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
          <div id="daily" class="mission-panel">
            <div class="section-head">
              <h2>今日委托</h2>
              <button
                v-if="daily?.all_completed && !daily?.bonus_claimed"
                type="button"
                class="section-action"
                @click="claimBonus"
              >
                领取全部完成奖励
              </button>
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
              <RouterLink to="/student/me/growth">打开档案</RouterLink>
            </div>
            <dl class="summary-list">
              <div>
                <dt>所属班级</dt>
                <dd>{{ classDisplayLabel }}</dd>
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

        <TeacherAssignmentPanel
          :assignments="teacherAssignments"
          :loading="loading"
          @updated="onAssignmentsUpdated"
        />
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

.section-action {
  border: 0;
  background: transparent;
  color: #52fff1;
  cursor: pointer;
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

.meter-hud {
  --progress: 0%;
  position: relative;
  display: grid;
  place-items: center;
  width: 168px;
  aspect-ratio: 1;
}

.meter-hud__glow {
  position: absolute;
  inset: -8%;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(35, 255, 222, 0.22), transparent 68%);
  filter: blur(6px);
  animation: meter-pulse 2.8s ease-in-out infinite;
}

.meter-hud__ticks {
  position: absolute;
  inset: 4%;
  border-radius: 50%;
  background: repeating-conic-gradient(
    from -90deg,
    rgba(123, 248, 255, 0.55) 0deg 2deg,
    transparent 2deg 12deg
  );
  mask: radial-gradient(circle, transparent 62%, #000 63%);
  opacity: 0.75;
}

.meter-ring {
  position: relative;
  z-index: 1;
  display: grid;
  width: 142px;
  aspect-ratio: 1;
  place-items: center;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, #071625 54%, transparent 55%),
    conic-gradient(from -90deg, #23ffde 0%, #7bf8ff var(--progress), rgba(75, 128, 160, 0.18) var(--progress));
  box-shadow:
    0 0 0 1px rgba(123, 248, 255, 0.35),
    0 0 28px rgba(35, 255, 222, 0.28),
    inset 0 0 24px rgba(35, 255, 222, 0.08);
}

.meter-ring::before {
  content: '';
  position: absolute;
  inset: 10%;
  border-radius: 50%;
  border: 1px dashed rgba(123, 248, 255, 0.28);
}

.meter-ring__inner {
  display: grid;
  place-items: center;
  text-align: center;
}

.meter-ring strong {
  color: #ffffff;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 2.15rem;
  font-weight: 800;
  letter-spacing: -0.04em;
  text-shadow: 0 0 18px rgba(123, 248, 255, 0.55);
}

.meter-ring em {
  margin-top: -0.15rem;
  color: rgba(123, 248, 255, 0.82);
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 0.72rem;
  font-style: normal;
  letter-spacing: 0.22em;
}

.meter-hud__scan {
  position: absolute;
  inset: 8%;
  border-radius: 50%;
  background: conic-gradient(from 0deg, transparent 0deg, rgba(123, 248, 255, 0.14) 40deg, transparent 80deg);
  animation: meter-scan 4s linear infinite;
  pointer-events: none;
}

@keyframes meter-pulse {
  0%,
  100% {
    opacity: 0.55;
    transform: scale(0.96);
  }
  50% {
    opacity: 1;
    transform: scale(1.04);
  }
}

@keyframes meter-scan {
  to {
    transform: rotate(360deg);
  }
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

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.9rem;
  margin-top: 1rem;
}

.stat-card,
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

.quest-mini strong {
  color: #ffffff;
}

.quest-mini p,
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

@media (max-width: 1100px) {
  .student-home {
    padding-inline: 1rem;
  }

  .hero-band,
  .home-grid {
    grid-template-columns: 1fr;
  }

  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .stat-grid,
  .quest-mini {
    grid-template-columns: 1fr;
  }

  .hero-band {
    padding: 1.1rem;
  }
}

html[data-theme='light'] .state-panel,
html[data-theme='light'] .hero-band,
html[data-theme='light'] .achievement-hint,
html[data-theme='light'] .stat-card,
html[data-theme='light'] .mission-panel {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(240, 248, 252, 0.92));
  border-color: rgba(8, 145, 178, 0.18);
  box-shadow: 0 4px 24px rgba(15, 23, 42, 0.06);
}

html[data-theme='light'] .hero-band h2,
html[data-theme='light'] .stat-card strong,
html[data-theme='light'] .quest-mini strong,
html[data-theme='light'] .summary-list dd {
  color: #0f172a;
}

html[data-theme='light'] .hero-band p,
html[data-theme='light'] .stat-card span,
html[data-theme='light'] .quest-mini p {
  color: #475569;
}

html[data-theme='light'] .hero-band__eyebrow,
html[data-theme='light'] .section-head h2,
html[data-theme='light'] .quest-mini__time,
html[data-theme='light'] .quest-mini em {
  color: #0891b2;
}

html[data-theme='light'] .meter-ring {
  background:
    radial-gradient(circle at center, #f8fafc 54%, transparent 55%),
    conic-gradient(from -90deg, #0891b2 0%, #22d3ee var(--progress), rgba(148, 163, 184, 0.2) var(--progress));
  box-shadow:
    0 0 0 1px rgba(8, 145, 178, 0.25),
    0 0 20px rgba(8, 145, 178, 0.12);
}

html[data-theme='light'] .meter-ring strong {
  color: #0f172a;
  text-shadow: none;
}

html[data-theme='light'] .primary-link {
  background: linear-gradient(90deg, #0891b2, #06b6d4);
  color: #ffffff;
}
</style>
