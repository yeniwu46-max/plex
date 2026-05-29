<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { advanceDailyQuest } from '../api/studentOverview'
import ArchiveProfileCard from '../components/archives/ArchiveProfileCard.vue'
import ExplorationTendencyCard from '../components/archives/ExplorationTendencyCard.vue'
import GrowthTrajectory from '../components/archives/GrowthTrajectory.vue'
import SkillDistribution from '../components/archives/SkillDistribution.vue'
import AchievementCollection from '../components/archives/AchievementCollection.vue'
import EmergencyMissionRecords from '../components/archives/EmergencyMissionRecords.vue'
import PlexSidebar from '../components/layout/PlexSidebar.vue'
import PlexTopbar from '../components/layout/PlexTopbar.vue'
import { fetchStudentOverview, type StudentOverview } from '../api/studentOverview'
import { fetchArchiveInsights, type EmergencyMissionArchiveRecord } from '../api/studentProgress'
import type { AchievementItem, GrowthEvent, SkillItem } from '../data/archivesMock'

const auth = useAuthStore()
const sidebarCollapsed = ref(false)
const overview = ref<StudentOverview | null>(null)
const tendencyLabel = ref('探索起步型')
const tendencyDescription = ref('完成试炼与今日委托后，这里会展示你的探索倾向分析。')
const skillItemsFromApi = ref<SkillItem[]>([])
const emergencyRecords = ref<EmergencyMissionArchiveRecord[]>([])
const loading = ref(true)
const errorMessage = ref('')

const displayName = computed(
  () => overview.value?.profile.real_name || auth.profile?.real_name || auth.profile?.username || 'Explorer',
)
const userLevel = computed(() => overview.value?.profile.level ?? auth.profile?.level ?? 1)

const profile = computed(() => ({
  displayName: displayName.value,
  level: userLevel.value,
  explorerId: overview.value?.profile.id
    ? `PX-${String(overview.value.profile.id).padStart(4, '0')}`
    : auth.profile?.id
      ? `PX-${String(auth.profile.id).padStart(4, '0')}`
      : 'PX-0000',
  rankTitle: overview.value?.profile.title || '见习 Explorer',
  streakDays: overview.value?.profile.consecutive_days ?? 0,
}))

const achievementItems = computed<AchievementItem[]>(() => {
  const apiItems = overview.value?.achievements?.achievements ?? []
  const tones: AchievementItem['tone'][] = ['teal', 'gold', 'blue']
  const mapped: AchievementItem[] = apiItems.slice(0, 4).map((item, index) => ({
    id: String(item.id),
    title: item.achievement?.name || `成就 ${item.achievement_id}`,
    date: item.unlocked_at?.slice(0, 10),
    tone: tones[index % tones.length],
  }))
  while (mapped.length < 4) {
    mapped.push({ id: `locked-${mapped.length}`, title: '待解锁', tone: 'locked', locked: true })
  }
  return mapped
})

const skillItems = computed(() => skillItemsFromApi.value)

const growthEvents = computed<GrowthEvent[]>(() => {
  const tones: GrowthEvent['tone'][] = ['teal', 'gold', 'blue', 'purple']
  const fromEmergency = emergencyRecords.value.slice(0, 2).map((record, index) => ({
    id: `em-${record.id}`,
    title: record.title,
    date: record.date?.slice(0, 10) || '近期',
    description: record.all_correct
      ? `全对 ${record.total_count}/${record.total_count}，获得 +${record.reward_points} XP（${record.focus_label}）`
      : `答对 ${record.correct_count}/${record.total_count}，未获奖励（${record.focus_label}）`,
    tone: (record.all_correct ? 'gold' : 'purple') as GrowthEvent['tone'],
    _sort: record.date || '',
    _prio: index,
  }))

  const logs = overview.value?.pointsLog?.logs ?? []
  const fromLogs = logs.slice(0, 4).map((log, index) => ({
    id: String(log.id),
    title: log.reason || '学习反馈',
    date: log.created_at?.slice(0, 10) || '今日',
    description: `获得 ${log.points} XP，累计推进个人成长进度。`,
    tone: tones[index % tones.length],
    _sort: log.created_at || '',
    _prio: 10 + index,
  }))

  const merged = [...fromEmergency, ...fromLogs].sort((a, b) => {
    if (a._sort !== b._sort) return b._sort.localeCompare(a._sort)
    return a._prio - b._prio
  })

  return merged.slice(0, 5).map(({ id, title, date, description, tone }) => ({
    id,
    title,
    date,
    description,
    tone,
  }))
})

async function loadArchive() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [overviewResult, insights] = await Promise.all([
      fetchStudentOverview(),
      fetchArchiveInsights(),
    ])
    overview.value = overviewResult
    tendencyLabel.value = insights.tendency.label
    tendencyDescription.value = insights.tendency.description
    skillItemsFromApi.value = insights.skills.map((skill) => ({
      key: skill.key,
      label: skill.label,
      percent: skill.percent,
    }))
    emergencyRecords.value = (insights.emergency_missions ?? []) as EmergencyMissionArchiveRecord[]
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
    errorMessage.value = error instanceof Error ? error.message : '探索档案加载失败'
  } finally {
    loading.value = false
  }
}

async function triggerNightSummary() {
  try {
    await advanceDailyQuest('night-summary')
  } catch {
    /* 幂等 */
  }
}

onMounted(() => {
  void loadArchive()
  void triggerNightSummary()
})

</script>

<template>
  <div class="shell" :class="{ 'shell--collapsed': sidebarCollapsed }">
    <PlexSidebar v-model:collapsed="sidebarCollapsed" active-key="archive" />

    <div class="main">
      <PlexTopbar title="探索档案" subtitle="你的成长，被记录在每一段星轨里" />

      <div class="content">
        <div v-if="loading" class="archive-state">正在整理你的探索档案…</div>
        <div v-else-if="errorMessage" class="archive-state archive-state--error">
          <span>{{ errorMessage }}</span>
          <button type="button" @click="loadArchive">重试</button>
        </div>
        <div v-else class="archives-grid">
          <archive-profile-card class="archives-grid__profile" :profile="profile" />
          <exploration-tendency-card
            class="archives-grid__tendency"
            :label="tendencyLabel"
            :description="tendencyDescription"
          />
          <growth-trajectory class="archives-grid__timeline" :events="growthEvents" />
          <skill-distribution class="archives-grid__skills" :skills="skillItems" />
          <achievement-collection class="archives-grid__achievements" :items="achievementItems" />
          <emergency-mission-records
            class="archives-grid__emergency"
            :records="emergencyRecords"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  height: 100dvh;
  min-height: 100dvh;
  max-height: 100dvh;
  overflow: hidden;
  background: var(--plex-bg);
  color: var(--plex-text);
  font-family:
    'Outfit',
    'Noto Sans SC',
    system-ui,
    sans-serif;
}

.shell--collapsed .sidebar {
  width: 72px;
}

.sidebar {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 1.25rem 0.75rem;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(2, 6, 23, 0.98) 100%);
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  transition: width 0.2s ease;
}

.sidebar__brand {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0 0.65rem 1.25rem;
  color: var(--plex-accent);
}

.sidebar__name {
  font-weight: 700;
  letter-spacing: 0.18em;
  font-size: 0.95rem;
  color: #f8fafc;
}

.sidebar__nav {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  flex: 1;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.7rem 0.85rem;
  border-radius: 0.65rem;
  color: rgba(226, 232, 240, 0.72);
  text-decoration: none;
  font-size: 0.9rem;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #f1f5f9;
}

.nav-item--active {
  color: var(--plex-accent);
  background: rgba(16, 240, 192, 0.08);
  box-shadow: inset 0 0 24px rgba(16, 240, 192, 0.06);
}

.nav-item__accent {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 0;
  border-radius: 0 2px 2px 0;
  background: transparent;
}

.nav-item--active .nav-item__accent {
  height: 60%;
  background: linear-gradient(180deg, var(--plex-accent), var(--plex-node-blue));
  box-shadow: 0 0 12px rgba(16, 240, 192, 0.6);
}

.nav-item__icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.nav-item__label {
  white-space: nowrap;
  overflow: hidden;
}

.sidebar__collapse {
  align-self: center;
  margin-top: 0.5rem;
  border: none;
  background: transparent;
  color: rgba(148, 163, 184, 0.8);
  cursor: pointer;
  padding: 0.5rem;
}

.sidebar__chev {
  font-size: 1rem;
  letter-spacing: -0.1em;
}

.main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-inline: var(--plex-page-gutter-x);
  position: relative;
  background:
    radial-gradient(ellipse 80% 50% at 50% -10%, rgba(16, 240, 192, 0.07), transparent),
    radial-gradient(ellipse 60% 40% at 90% 60%, rgba(139, 92, 246, 0.06), transparent),
    linear-gradient(180deg, #030712 0%, #020617 100%);
}

.main :deep(.plex-topbar) {
  padding-inline: 0;
}

.topbar {
  position: relative;
  z-index: 2;
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 0.85rem 1.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  flex-wrap: wrap;
}

.topbar__left {
  flex: 1;
  min-width: 200px;
}

.topbar__crumb {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.35rem 0.75rem;
}

.topbar__crumb-sep {
  color: var(--plex-muted);
  font-size: 0.9rem;
}

.topbar__titles {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
}

.topbar__title {
  font-size: 1.15rem;
  font-weight: 600;
}

.topbar__subtitle-en {
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  color: var(--plex-muted);
}

.topbar__tagline {
  flex: 1 1 100%;
  margin: 0.15rem 0 0 1.25rem;
  font-size: 0.78rem;
  color: var(--plex-muted);
}

.topbar__search {
  flex: 1;
  min-width: 200px;
  max-width: 420px;
  margin-top: 0.15rem;
}

.topbar__input :deep(.n-input) {
  --n-color: rgba(15, 23, 42, 0.55) !important;
  --n-border: 1px solid rgba(255, 255, 255, 0.08) !important;
  --n-border-hover: 1px solid rgba(16, 240, 192, 0.25) !important;
  --n-text-color: #e2e8f0 !important;
  --n-placeholder-color: rgba(148, 163, 184, 0.65) !important;
}

.topbar__search-icon {
  color: rgba(148, 163, 184, 0.85);
}

.topbar__right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-left: auto;
  margin-top: 0.15rem;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 0.65rem;
  background: rgba(255, 255, 255, 0.04);
  color: #cbd5e1;
  cursor: pointer;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.5rem 0.25rem 0.35rem;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  cursor: pointer;
  color: inherit;
}

.user-chip__avatar {
  background: linear-gradient(135deg, #0f172a, #1e293b) !important;
  color: var(--plex-accent) !important;
  font-size: 0.85rem;
}

.user-chip__text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.15;
}

.user-chip__name {
  font-size: 0.85rem;
  font-weight: 500;
}

.user-chip__lv {
  font-size: 0.7rem;
  color: var(--plex-accent);
  font-weight: 600;
}

.user-chip__arrow {
  color: rgba(148, 163, 184, 0.8);
}

.content {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 1.15rem 0 var(--plex-page-gutter-bottom);
}

.archive-state {
  display: flex;
  min-height: 260px;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  border: 1px solid var(--plex-border);
  border-radius: 1rem;
  background: rgba(11, 22, 40, 0.72);
  color: rgba(226, 232, 240, 0.82);
}

.archive-state--error {
  color: #fecaca;
}

.archive-state button {
  min-height: 38px;
  border: 1px solid rgba(16, 240, 192, 0.34);
  border-radius: 999px;
  padding: 0 1rem;
  background: rgba(16, 240, 192, 0.1);
  color: #eaffff;
  cursor: pointer;
}

.archives-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(0, 0.85fr);
  grid-template-rows: auto auto 1fr auto;
  gap: 0.85rem;
  min-height: min(100%, 720px);
  grid-template-areas:
    'profile tendency'
    'timeline skills'
    'timeline achievements'
    'emergency emergency';
}

.archives-grid__profile {
  grid-area: profile;
}

.archives-grid__tendency {
  grid-area: tendency;
}

.archives-grid__timeline {
  grid-area: timeline;
  align-self: stretch;
  min-height: 0;
}

.archives-grid__skills {
  grid-area: skills;
}

.archives-grid__achievements {
  grid-area: achievements;
}

.archives-grid__emergency {
  grid-area: emergency;
}

@media (max-width: 1100px) {
  .archives-grid {
    grid-template-columns: 1fr;
    grid-template-areas:
      'profile'
      'tendency'
      'timeline'
      'skills'
      'achievements'
      'emergency';
  }
}

@media (max-width: 768px) {
  .shell {
    flex-direction: column;
  }

  .sidebar {
    width: 100% !important;
    flex-direction: row;
    flex-wrap: wrap;
    padding: 0.75rem;
  }

  .sidebar__nav {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .sidebar__collapse {
    display: none;
  }

  .topbar__search {
    order: 3;
    flex: 1 1 100%;
    max-width: none;
  }
}
</style>
