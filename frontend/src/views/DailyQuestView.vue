<script setup lang="ts">
import { computed, markRaw, onMounted, ref, watch, type Component } from 'vue'
import { NIcon, useMessage } from 'naive-ui'
import { showIncentiveFeedback } from '../utils/incentiveFeedback'
import {
  ArrowForwardOutline,
  BarbellOutline,
  CheckmarkOutline,
  DocumentTextOutline,
  ExtensionPuzzleOutline,
  GiftOutline,
  MoonOutline,
  SparklesOutline,
  SunnyOutline,
  TimeOutline,
} from '@vicons/ionicons5'
import PlexSidebar from '../components/layout/PlexSidebar.vue'
import PlexTopbar from '../components/layout/PlexTopbar.vue'
import {
  advanceDailyQuest,
  claimDailyQuestBonus,
  fetchTodayDailyQuests,
  type DailyQuestTodayResult,
} from '../api/studentOverview'
import { DAILY_BONUS_STAR_KEYS, DAILY_BONUS_XP, DAILY_QUESTS, type QuestAccent } from '../data/dailyQuests'
import TeacherAssignmentPanel from '../components/student/TeacherAssignmentPanel.vue'
import type { TeacherAssignmentsResult } from '../api/studentAssignments'
import { useAuthStore } from '../stores/auth'
import { useNotificationStore } from '../stores/notifications'

type Quest = {
  key: string
  period: string
  time: string
  title: string
  description: string
  icon: Component
  accent: QuestAccent
  current: number
  total: number
  rewardXp: number
  completed: boolean
  rewardClaimed: boolean
}

const message = useMessage()
const auth = useAuthStore()
const notifications = useNotificationStore()
const sidebarCollapsed = ref(false)
const allCompletedNotified = ref(false)
const dailyData = ref<DailyQuestTodayResult | null>(null)
const loading = ref(true)
const errorMessage = ref('')
const savingKey = ref('')
const teacherAssignments = ref<TeacherAssignmentsResult>({ pending_count: 0, total_count: 0, items: [] })


const iconMap: Record<string, Component> = {
  'morning-launch': markRaw(SparklesOutline),
  'fragment-repair': markRaw(ExtensionPuzzleOutline),
  'trial-challenge': markRaw(BarbellOutline),
  'night-summary': markRaw(DocumentTextOutline),
}

const fallbackQuests = DAILY_QUESTS.map((quest) => ({
    ...quest,
    icon: iconMap[quest.key] ?? markRaw(SparklesOutline),
    current: 0,
    completed: false,
    rewardClaimed: false,
  }))

const fallbackByKey = new Map(DAILY_QUESTS.map((quest) => [quest.key, quest]))

const quests = computed<Quest[]>(() => {
  if (!dailyData.value) return fallbackQuests
  return dailyData.value.quests.map((quest, index) => {
    const fallback = fallbackByKey.get(quest.key)
    return {
      key: quest.key,
      period: quest.period || fallback?.period || '',
      time: quest.time || fallback?.time || '',
      title: quest.title || fallback?.title || '',
      description: quest.description || fallback?.description || '',
      icon: iconMap[quest.key] ?? markRaw(SparklesOutline),
      accent: fallback?.accent ?? (['teal', 'amber', 'blue', 'purple'][index % 4] as QuestAccent),
      current: quest.current,
      total: quest.total,
      rewardXp: quest.reward_xp,
      completed: quest.completed,
      rewardClaimed: quest.reward_claimed,
    }
  })
})

const isPersisted = computed(() => Boolean(dailyData.value))

const completedCount = computed(() =>
  dailyData.value?.completed_count ?? quests.value.filter((quest) => quest.current >= quest.total).length,
)

const totalRequired = computed(() => dailyData.value?.total_required ?? quests.value.reduce((sum, quest) => sum + quest.total, 0))
const totalCurrent = computed(() =>
  dailyData.value?.total_current ?? quests.value.reduce((sum, quest) => sum + Math.min(quest.current, quest.total), 0),
)
const explorationIndex = computed(() =>
  totalCurrent.value === 2
    ? 78
    : Math.round((totalCurrent.value / Math.max(1, totalRequired.value)) * 100),
)
const repairedFragments = computed(() => {
  const repairQuest = quests.value.find((quest) => quest.key === 'fragment-repair')
  return repairQuest?.current ?? 0
})
const earnedXp = computed(() =>
  dailyData.value?.earned_xp ?? quests.value.reduce((sum, quest) => (quest.current >= quest.total ? sum + quest.rewardXp : sum), 0),
)
const allCompleted = computed(() => dailyData.value?.all_completed ?? completedCount.value === quests.value.length)
const bonusClaimed = computed(() => Boolean(dailyData.value?.bonus_claimed))
const bonusXp = computed(() => dailyData.value?.bonus_xp ?? DAILY_BONUS_XP)
const pendingQuest = computed(() => quests.value.find((quest) => quest.current < quest.total))

function notifyDailyAllCompletedIfNeeded() {
  if (!allCompleted.value || allCompletedNotified.value) return
  const id = auth.profile?.id
  if (!id) return
  const pushed = notifications.push(id, 'daily_quest_all_done')
  if (pushed) allCompletedNotified.value = true
}

async function loadTodayQuests() {
  loading.value = true
  errorMessage.value = ''
  try {
    dailyData.value = await fetchTodayDailyQuests()
    teacherAssignments.value = (dailyData.value.teacher_assignments as TeacherAssignmentsResult | undefined) ?? {
      pending_count: 0,
      total_count: 0,
      items: [],
    }
    if (dailyData.value.all_completed) {
      notifyDailyAllCompletedIfNeeded()
    }
  } catch (error) {
    dailyData.value = null
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load daily quests'
  } finally {
    loading.value = false
  }
}

async function claimBonus() {
  if (!isPersisted.value || !allCompleted.value || bonusClaimed.value || savingKey.value) return
  savingKey.value = 'bonus'
  errorMessage.value = ''
  try {
    dailyData.value = await claimDailyQuestBonus()
    showIncentiveFeedback(message, dailyData.value?.incentive)
    if (dailyData.value?.incentive?.total_points !== undefined) {
      auth.syncProfile({ total_points: dailyData.value.incentive.total_points, level: dailyData.value.incentive.level })
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to claim daily quest bonus'
  } finally {
    savingKey.value = ''
  }
}

async function advanceQuest(key: string) {
  const quest = quests.value.find((item) => item.key === key)
  if (!quest || quest.current >= quest.total || !isPersisted.value || savingKey.value) return
  savingKey.value = key
  errorMessage.value = ''
  try {
    dailyData.value = await advanceDailyQuest(key)
    showIncentiveFeedback(message, dailyData.value?.incentive)
    if (dailyData.value?.incentive?.total_points !== undefined) {
      auth.syncProfile({ total_points: dailyData.value.incentive.total_points, level: dailyData.value.incentive.level })
    }
    if (dailyData.value.all_completed && !dailyData.value.bonus_claimed) {
      dailyData.value = await claimDailyQuestBonus()
      showIncentiveFeedback(message, dailyData.value?.incentive)
      if (dailyData.value?.incentive?.total_points !== undefined) {
        auth.syncProfile({ total_points: dailyData.value.incentive.total_points, level: dailyData.value.incentive.level })
      }
    }
    notifyDailyAllCompletedIfNeeded()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to update daily quest'
  } finally {
    savingKey.value = ''
  }
}

watch(allCompleted, (done) => {
  if (done) notifyDailyAllCompletedIfNeeded()
})

function onAssignmentsUpdated(payload: {
  assignments: TeacherAssignmentsResult
  daily: DailyQuestTodayResult | null
}) {
  teacherAssignments.value = payload.assignments
  if (payload.daily) {
    dailyData.value = payload.daily
  }
}

onMounted(loadTodayQuests)
</script>

<template>
  <div class="daily-shell" :class="{ 'daily-shell--collapsed': sidebarCollapsed }">
    <PlexSidebar v-model:collapsed="sidebarCollapsed" active-key="daily" />

    <main class="daily-main">
      <PlexTopbar title="今日委托" subtitle="每一步探索，都是成长的轨迹" />

      <section class="daily-content" aria-label="今日委托">
        <div class="space-scene" aria-hidden="true">
          <span class="space-scene__planet" />
          <span class="space-scene__star space-scene__star--one" />
          <span class="space-scene__star space-scene__star--two" />
          <span class="space-scene__star space-scene__star--three" />
        </div>

        <div v-if="loading || errorMessage" class="quest-state" :class="{ 'quest-state--error': errorMessage }">
          <span>{{ loading ? 'Loading daily quests...' : `${errorMessage}. Showing fallback only.` }}</span>
          <button v-if="errorMessage" type="button" @click="loadTodayQuests">Retry</button>
        </div>

        <div class="daily-content__main">
          <TeacherAssignmentPanel
            :assignments="teacherAssignments"
            :loading="loading"
            @updated="onAssignmentsUpdated"
          />

          <section class="quest-board" aria-labelledby="quest-board-title">
            <div class="quest-board__panel">
              <h2 id="quest-board-title">今日探索航线</h2>
              <div class="quest-timeline">
                <article
                  v-for="quest in quests"
                  :key="quest.key"
                  class="quest-row"
                  :class="[`quest-row--${quest.accent}`, { 'quest-row--done': quest.current >= quest.total, 'quest-row--auto': quest.key === 'morning-launch' || quest.key === 'night-summary' }]"
                >
                  <div class="quest-time">
                    <n-icon :component="quest.key === 'night-summary' ? MoonOutline : quest.key === 'trial-challenge' ? TimeOutline : SunnyOutline" />
                    <strong>{{ quest.period }}</strong>
                    <span>{{ quest.time }}</span>
                  </div>

                  <button
                    type="button"
                    class="quest-node"
                    :disabled="true"
                    :aria-label="`${quest.title} 进度 ${quest.current}/${quest.total}`"
                    @click="quest.key !== 'morning-launch' && quest.key !== 'night-summary' ? advanceQuest(quest.key) : undefined"
                  >
                    <n-icon :component="quest.icon" />
                  </button>

                  <button
                    type="button"
                    class="quest-card"
                    :disabled="loading || !isPersisted || Boolean(savingKey) || quest.current >= quest.total || quest.key === 'morning-launch' || quest.key === 'night-summary'"
                    @click="quest.key !== 'morning-launch' && quest.key !== 'night-summary' ? advanceQuest(quest.key) : undefined"
                  >
                    <span class="quest-card__text">
                      <strong>{{ quest.title }}</strong>
                      <span v-if="quest.key === 'morning-launch'">进入探索舱即可自动完成</span>
                      <span v-else-if="quest.key === 'night-summary'">访问探索档案即可自动完成</span>
                      <span v-else>{{ quest.description }}</span>
                    </span>
                    <span class="quest-card__progress">+{{ quest.rewardXp }} XP · {{ quest.current }}/{{ quest.total }}</span>
                    <span class="quest-card__ring" :style="{ '--quest-ratio': quest.current / quest.total }">
                      <n-icon v-if="quest.current >= quest.total" :component="CheckmarkOutline" />
                    </span>
                  </button>
                </article>
              </div>

              <footer class="quest-reward">
                <span>{{ allCompleted ? '今日委托已全部完成，奖励反馈已解锁' : '完成全部委托可获得额外奖励' }}</span>
                <strong class="reward-chip reward-chip--xp">
                  <span>XP</span>
                  <em>+{{ bonusXp }}</em>
                </strong>
                <strong class="reward-chip reward-chip--star">
                  <span>钥</span>
                  <em>+{{ DAILY_BONUS_STAR_KEYS }}</em>
                </strong>
              </footer>
            </div>
          </section>
        </div>

        <aside class="daily-aside" aria-label="委托概览与奖励">
          <section class="daily-panel daily-overview">
            <h2>今日探索概览</h2>
            <div class="overview-body">
              <div class="progress-orbit" :style="{ '--progress': explorationIndex / 100 }">
                <span class="progress-orbit__value">{{ explorationIndex }}<small>%</small></span>
                <span class="progress-orbit__label">探索指数</span>
              </div>
              <dl class="overview-list">
                <div>
                  <dt>连续探索</dt>
                  <dd>{{ allCompleted ? 6 : 5 }} 天</dd>
                </div>
                <div>
                  <dt>完成委托</dt>
                  <dd>{{ completedCount }}/{{ quests.length }}</dd>
                </div>
                <div>
                  <dt>知识碎片修复</dt>
                  <dd>{{ repairedFragments }} 个</dd>
                </div>
                <div>
                  <dt>今日反馈 XP</dt>
                  <dd>+{{ earnedXp }}</dd>
                </div>
              </dl>
            </div>
          </section>

          <section class="daily-panel daily-tip">
            <span class="daily-tip__icon">
              <n-icon :component="SparklesOutline" />
            </span>
            <div>
              <h2>小贴士</h2>
              <p class="daily-tip__lead">
                {{ pendingQuest ? `建议优先完成“${pendingQuest.title}”` : '今日委托已经清空' }}
              </p>
              <p class="daily-tip__copy">
                {{ pendingQuest ? '完成后会同步更新今日进度反馈。' : '可以前往探索档案查看今日成长记录。' }}
              </p>
            </div>
            <button type="button" class="daily-tip__go" aria-label="查看推荐">
              <n-icon :component="ArrowForwardOutline" />
            </button>
          </section>

          <section class="daily-panel reward-preview">
            <div>
              <h2>奖励预览</h2>
              <p>{{ allCompleted ? '已解锁全部奖励反馈' : '完成全部委托可获得' }}</p>
            </div>
            <n-icon :component="GiftOutline" class="reward-preview__gift" />
            <div class="reward-preview__items">
              <span class="reward-preview__item reward-preview__item--xp">
                <strong>XP</strong>
                <em>{{ bonusXp }}</em>
              </span>
              <span class="reward-preview__item reward-preview__item--gem">
                <strong>钥</strong>
                <em>{{ DAILY_BONUS_STAR_KEYS }}</em>
              </span>
            </div>
            <button
              v-if="allCompleted && !bonusClaimed"
              type="button"
              class="bonus-claim"
              :disabled="!isPersisted || savingKey === 'bonus'"
              @click="claimBonus"
            >
              {{ savingKey === 'bonus' ? '领取中…' : '领取奖励' }}
            </button>
            <span v-else-if="bonusClaimed" class="bonus-claimed">奖励已领取</span>
          </section>

          <section class="daily-panel reset-note" aria-label="委托重置说明">
            <p>每日 00:00 重置委托任务</p>
          </section>
        </aside>
      </section>
    </main>
  </div>
</template>

<style scoped>
.daily-shell {
  display: flex;
  height: 100dvh;
  min-height: 100dvh;
  overflow: hidden;
  background: #020a12;
  color: #edf7ff;
  font-family:
    'Outfit',
    'Noto Sans SC',
    'Microsoft YaHei',
    system-ui,
    sans-serif;
}

.daily-shell--collapsed .daily-sidebar {
  width: 84px;
}

.daily-sidebar {
  position: relative;
  z-index: 4;
  width: 230px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 2.25rem 0 1.5rem;
  background:
    radial-gradient(circle at 22% 8%, rgba(20, 241, 226, 0.08), transparent 26%),
    linear-gradient(180deg, rgba(3, 15, 25, 0.98), rgba(1, 8, 15, 0.99));
  border-right: 1px solid rgba(110, 228, 255, 0.11);
  box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.025);
  transition: width 0.2s ease;
}

.daily-sidebar__brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0 2.55rem 2.85rem;
  color: #25f5ee;
}

.daily-sidebar__name {
  color: #ffffff;
  font-size: 1.75rem;
  font-weight: 760;
  letter-spacing: 0.08em;
}

.brand-mark {
  filter: drop-shadow(0 0 12px rgba(37, 245, 238, 0.65));
}

.daily-sidebar__nav {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 0.55rem;
}

.daily-nav {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 76px;
  gap: 0.95rem;
  padding: 0.7rem 1.35rem 0.7rem 2.55rem;
  color: rgba(220, 230, 241, 0.74);
  text-decoration: none;
  transition:
    background 0.18s ease,
    color 0.18s ease;
}

.daily-nav:hover {
  color: #ffffff;
  background: rgba(37, 245, 238, 0.045);
}

.daily-nav--active {
  color: #ffffff;
  background:
    linear-gradient(90deg, rgba(16, 240, 192, 0.22), rgba(16, 240, 192, 0.06) 72%, transparent),
    rgba(6, 182, 212, 0.04);
}

.daily-nav__bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  opacity: 0;
  background: linear-gradient(180deg, #5ffff3, #12d8c8);
  box-shadow: 0 0 18px rgba(37, 245, 238, 0.76);
}

.daily-nav--active .daily-nav__bar {
  opacity: 1;
}

.daily-nav__icon {
  flex: 0 0 auto;
  font-size: 1.95rem;
  color: currentColor;
}

.daily-nav__copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.25rem;
  line-height: 1.1;
}

.daily-nav__label {
  font-size: 1rem;
  font-weight: 670;
  white-space: nowrap;
}

.daily-nav__sub {
  color: rgba(221, 230, 239, 0.55);
  font-size: 0.72rem;
  font-weight: 680;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.daily-nav--active .daily-nav__label,
.daily-nav--active .daily-nav__sub {
  color: #52fff1;
  text-shadow: 0 0 14px rgba(37, 245, 238, 0.5);
}

.daily-sidebar__collapse {
  width: 56px;
  height: 56px;
  align-self: center;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 50%;
  background: rgba(12, 27, 40, 0.68);
  color: #d9f4ff;
  cursor: pointer;
  font-size: 1.5rem;
  line-height: 1;
}

.daily-main {
  position: relative;
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
  background:
    radial-gradient(circle at 72% 6%, rgba(37, 245, 238, 0.08), transparent 26%),
    radial-gradient(circle at 35% 36%, rgba(42, 134, 255, 0.08), transparent 34%),
    linear-gradient(180deg, #06121f 0%, #020a12 58%, #01070e 100%);
}

.daily-main::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.48;
  background-image:
    radial-gradient(1px 1px at 12% 24%, rgba(255, 255, 255, 0.42), transparent),
    radial-gradient(1px 1px at 43% 18%, rgba(93, 214, 255, 0.46), transparent),
    radial-gradient(1px 1px at 63% 40%, rgba(255, 255, 255, 0.24), transparent),
    radial-gradient(1px 1px at 87% 22%, rgba(93, 214, 255, 0.24), transparent);
  background-size: 360px 360px;
}

.daily-topbar {
  position: relative;
  z-index: 3;
  display: grid;
  grid-template-columns: minmax(260px, 1fr) minmax(320px, 520px) minmax(260px, 1fr);
  align-items: start;
  gap: 1.5rem;
  padding: 2.15rem 3rem 1.2rem 3.7rem;
}

.daily-heading h1 {
  margin: 0;
  color: #ffffff;
  font-size: clamp(1.7rem, 2.2vw, 2.25rem);
  font-weight: 740;
  line-height: 1.1;
}

.daily-heading p {
  margin: 0.7rem 0 0;
  color: rgba(221, 230, 239, 0.72);
  font-size: 0.98rem;
}

.daily-search {
  align-self: start;
}

.daily-search__input :deep(.n-input) {
  --n-height: 58px !important;
  --n-color: rgba(6, 18, 31, 0.66) !important;
  --n-color-focus: rgba(8, 24, 39, 0.86) !important;
  --n-border: 1px solid rgba(130, 212, 255, 0.12) !important;
  --n-border-hover: 1px solid rgba(37, 245, 238, 0.32) !important;
  --n-border-focus: 1px solid rgba(37, 245, 238, 0.48) !important;
  --n-box-shadow-focus: 0 0 0 2px rgba(37, 245, 238, 0.08) !important;
  --n-text-color: #edf7ff !important;
  --n-placeholder-color: rgba(210, 225, 238, 0.55) !important;
  font-size: 0.96rem;
}

.daily-search__icon {
  color: #e8f9ff;
  font-size: 1.35rem;
}

.daily-userbar {
  justify-self: end;
  display: flex;
  align-items: center;
  gap: 1.8rem;
}

.daily-icon-btn {
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #edf7ff;
  cursor: pointer;
}

.daily-icon-btn:hover {
  background: rgba(255, 255, 255, 0.06);
}

.daily-user {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  border: 0;
  background: transparent;
  color: #ffffff;
  cursor: pointer;
}

.daily-user__avatar {
  border: 1px solid rgba(37, 245, 238, 0.22);
  background:
    radial-gradient(circle, rgba(37, 245, 238, 0.12), transparent 62%),
    #061827 !important;
  box-shadow:
    0 0 0 6px rgba(61, 163, 255, 0.1),
    0 0 22px rgba(37, 245, 238, 0.28);
  color: #31fff2 !important;
  font-size: 1.35rem;
}

.daily-user__copy {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.2rem;
}

.daily-user__copy strong {
  font-size: 0.95rem;
  font-weight: 690;
}

.daily-user__copy em {
  padding: 0.05rem 0.3rem;
  border-radius: 0.3rem;
  background: rgba(37, 245, 238, 0.18);
  color: #57fff2;
  font-size: 0.76rem;
  font-style: normal;
}

.daily-user__chev {
  color: rgba(230, 242, 250, 0.82);
}

.daily-content {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 420px);
  grid-template-areas: 'main aside';
  align-items: stretch;
  gap: 1.5rem;
  flex: 1;
  min-height: 0;
  padding: 0.35rem var(--plex-page-gutter-x) var(--plex-page-gutter-bottom);
}

.daily-content__main {
  grid-area: main;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.daily-content__main :deep(.teacher-assign) {
  flex-shrink: 0;
  margin-bottom: 0;
  max-height: min(38vh, 320px);
  overflow-y: auto;
}

.space-scene {
  position: absolute;
  z-index: 0;
  inset: auto auto 0 0;
  width: min(56vw, 740px);
  height: min(48vh, 520px);
  pointer-events: none;
  overflow: hidden;
}

.space-scene__planet {
  position: absolute;
  left: -18%;
  bottom: -54%;
  width: 82%;
  aspect-ratio: 1;
  border-radius: 50%;
  background:
    radial-gradient(circle at 34% 28%, rgba(168, 224, 255, 0.34), transparent 13%),
    radial-gradient(circle at 52% 20%, rgba(91, 188, 255, 0.28), transparent 24%),
    radial-gradient(circle at 58% 62%, rgba(7, 18, 31, 0.95), rgba(3, 12, 22, 0.98) 55%),
    #030a12;
  box-shadow:
    inset 34px 28px 90px rgba(129, 207, 255, 0.16),
    -10px -8px 42px rgba(148, 220, 255, 0.36);
}

.space-scene__planet::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(27deg, transparent 43%, rgba(143, 216, 255, 0.36) 48%, transparent 53%);
  opacity: 0.46;
}

.space-scene__star {
  position: absolute;
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #86f9ff;
  box-shadow: 0 0 13px rgba(134, 249, 255, 0.9);
}

.space-scene__star--one {
  left: 35%;
  top: 13%;
}

.space-scene__star--two {
  left: 49%;
  top: 40%;
}

.space-scene__star--three {
  left: 22%;
  top: 72%;
}

.quest-board {
  position: relative;
  z-index: 2;
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}

.quest-state {
  position: absolute;
  z-index: 5;
  top: 0.9rem;
  left: var(--plex-page-gutter-x);
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  max-width: min(680px, calc(100% - (var(--plex-page-gutter-x) * 2)));
  padding: 0.7rem 0.9rem;
  border: 1px solid rgba(90, 208, 255, 0.22);
  border-radius: 0.65rem;
  background: rgba(4, 14, 24, 0.9);
  color: rgba(237, 247, 255, 0.86);
  font-size: 0.86rem;
}

.quest-state--error {
  border-color: rgba(251, 191, 36, 0.32);
  color: #fde68a;
}

.quest-state button,
.bonus-claim {
  min-height: 34px;
  border: 1px solid rgba(46, 255, 241, 0.34);
  border-radius: 999px;
  padding: 0 0.85rem;
  background: rgba(46, 255, 241, 0.12);
  color: #eaffff;
  cursor: pointer;
  font-weight: 700;
}

.quest-state button:disabled,
.bonus-claim:disabled {
  cursor: default;
  opacity: 0.6;
}

.quest-board h2,
.daily-panel h2 {
  margin: 0;
  color: #30fff1;
  font-size: 1.18rem;
  font-weight: 720;
  letter-spacing: 0.01em;
}

.quest-board__panel > h2 {
  flex-shrink: 0;
  margin-bottom: 1.45rem;
}

.quest-board__panel {
  position: relative;
  z-index: 2;
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  padding: 1.65rem 2rem 1.65rem;
  border: 1px solid rgba(90, 208, 255, 0.11);
  border-radius: 0.85rem;
  background:
    linear-gradient(180deg, rgba(9, 24, 39, 0.5), rgba(5, 15, 27, 0.42)),
    rgba(4, 14, 24, 0.38);
  box-shadow: inset 0 0 40px rgba(63, 207, 255, 0.025);
}

.quest-timeline {
  --quest-time-col: 10.5rem;
  --quest-node-col: 5.75rem;
  position: relative;
  display: grid;
  flex: 1;
  gap: clamp(0.95rem, 1.8vh, 1.45rem);
  min-height: 0;
  overflow-y: auto;
  padding-right: 0.35rem;
}

.quest-timeline::before {
  content: '';
  position: absolute;
  left: calc(var(--quest-time-col) + var(--quest-node-col) / 2);
  top: 0;
  bottom: 0;
  width: 2px;
  transform: translateX(-50%);
  background: linear-gradient(180deg, rgba(37, 245, 238, 0.65), rgba(71, 149, 255, 0.74), rgba(183, 83, 255, 0.7));
  box-shadow: 0 0 16px rgba(37, 245, 238, 0.2);
}

.quest-row {
  position: relative;
  display: grid;
  grid-template-columns: var(--quest-time-col) var(--quest-node-col) minmax(0, 1fr);
  align-items: center;
  gap: 0 0.85rem;
  min-height: 92px;
}

.quest-time {
  display: grid;
  grid-template-columns: 1.5rem 1fr;
  gap: 0.3rem 0.55rem;
  align-items: center;
  color: rgba(211, 225, 236, 0.66);
}

.quest-time .n-icon {
  grid-row: span 2;
  color: rgba(220, 235, 246, 0.78);
  font-size: 1.45rem;
}

.quest-time strong {
  color: var(--quest-color);
  font-size: 1.05rem;
  font-weight: 680;
}

.quest-time span {
  font-size: 0.9rem;
}

.quest-node {
  position: relative;
  z-index: 1;
  justify-self: center;
  display: grid;
  width: 80px;
  height: 80px;
  place-items: center;
  border: 1px solid color-mix(in srgb, var(--quest-color) 72%, transparent);
  border-radius: 50%;
  background:
    radial-gradient(circle, color-mix(in srgb, var(--quest-color) 32%, transparent) 0 32%, transparent 58%),
    rgba(6, 17, 29, 0.86);
  box-shadow:
    0 0 0 7px color-mix(in srgb, var(--quest-color) 10%, transparent),
    0 0 32px color-mix(in srgb, var(--quest-color) 28%, transparent);
  color: #ffffff;
  cursor: pointer;
}

.quest-node:disabled,
.quest-card:disabled {
  cursor: default;
}

.quest-node .n-icon {
  font-size: 2rem;
  filter: drop-shadow(0 0 12px color-mix(in srgb, var(--quest-color) 88%, transparent));
}

.quest-node::before,
.quest-node::after {
  content: '';
  position: absolute;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--quest-color) 92%, #ffffff 8%);
  box-shadow: 0 0 13px color-mix(in srgb, var(--quest-color) 75%, transparent);
}

.quest-node::before {
  left: -3px;
  top: 43%;
}

.quest-node::after {
  right: 43%;
  bottom: -4px;
}

.quest-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto 44px;
  align-items: center;
  gap: 0.85rem 1rem;
  min-height: 88px;
  padding: 1rem 1.15rem;
  border: 1px solid rgba(125, 205, 255, 0.12);
  border-radius: 0.85rem;
  background:
    linear-gradient(90deg, rgba(13, 31, 49, 0.76), rgba(8, 22, 36, 0.68)),
    rgba(6, 18, 31, 0.72);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.quest-card:hover {
  border-color: color-mix(in srgb, var(--quest-color) 42%, rgba(125, 205, 255, 0.12));
  transform: translateY(-1px);
}

.quest-card__text {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.55rem;
}

.quest-card__text strong {
  color: #ffffff;
  font-size: 1.08rem;
  font-weight: 720;
}

.quest-card__text span {
  color: rgba(212, 225, 237, 0.66);
  font-size: 0.88rem;
}

.quest-card__progress {
  color: rgba(221, 232, 242, 0.72);
  font-size: 1.02rem;
  font-weight: 560;
}

.quest-card__ring {
  --ring-fill: calc(var(--quest-ratio) * 100%);
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, #091827 57%, transparent 58%),
    conic-gradient(var(--quest-color) var(--ring-fill), rgba(90, 130, 160, 0.26) 0);
  color: #30fff1;
  font-size: 1.5rem;
}

.quest-row--teal {
  --quest-color: #2efff1;
}

.quest-row--amber {
  --quest-color: #ffc56d;
}

.quest-row--blue {
  --quest-color: #58a9ff;
}

.quest-row--purple {
  --quest-color: #c261ff;
}

.quest-row--done .quest-card {
  border-color: rgba(46, 255, 241, 0.21);
}

.quest-row--auto .quest-card {
  cursor: default;
  opacity: 0.88;
}

.quest-row--auto .quest-card__text span {
  font-style: italic;
  color: rgba(226, 232, 240, 0.55);
}

.quest-reward {
  display: flex;
  flex-shrink: 0;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem 1.6rem;
  margin-top: auto;
  padding-top: 1.35rem;
  color: rgba(220, 231, 241, 0.65);
  font-size: 0.88rem;
}

.reward-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  color: #37fff1;
  font-size: 0.92rem;
  font-weight: 650;
}

.reward-chip span {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border: 1px solid currentColor;
  clip-path: polygon(50% 0, 92% 25%, 92% 75%, 50% 100%, 8% 75%, 8% 25%);
  background: rgba(37, 245, 238, 0.08);
  font-size: 0.7rem;
}

.reward-chip--star span {
  width: 34px;
  height: 34px;
  border: 0;
  clip-path: none;
  background: radial-gradient(circle, rgba(167, 100, 255, 0.48), transparent 66%);
  font-size: 1.15rem;
}

.reward-chip em {
  font-style: normal;
}

.daily-aside {
  grid-area: aside;
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-self: stretch;
  min-height: 0;
  gap: 1rem;
  min-width: 0;
  overflow-y: auto;
}

.daily-panel {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(90, 208, 255, 0.11);
  border-radius: 0.85rem;
  background:
    linear-gradient(180deg, rgba(9, 26, 43, 0.58), rgba(5, 16, 29, 0.48)),
    rgba(4, 14, 24, 0.52);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.025),
    0 14px 40px rgba(0, 0, 0, 0.1);
}

.daily-overview {
  padding: 1.65rem 1.8rem 1.9rem;
}

.overview-body {
  display: grid;
  grid-template-columns: minmax(140px, 180px) minmax(0, 1fr);
  gap: 1.25rem;
  align-items: center;
  margin-top: 1.35rem;
}

.progress-orbit {
  --progress-deg: calc(var(--progress) * 360deg);
  position: relative;
  display: grid;
  width: min(100%, 160px);
  aspect-ratio: 1;
  place-items: center;
  justify-self: center;
  border-radius: 50%;
  background:
    radial-gradient(circle, rgba(7, 19, 31, 0.94) 0 55%, transparent 56%),
    conic-gradient(#80f9f7 var(--progress-deg), rgba(87, 138, 165, 0.22) 0);
  box-shadow:
    0 0 28px rgba(48, 255, 241, 0.16),
    inset 0 0 24px rgba(48, 255, 241, 0.06);
}

.progress-orbit::before {
  content: '';
  position: absolute;
  inset: 18px;
  border-radius: inherit;
  border: 8px solid rgba(43, 216, 218, 0.24);
}

.progress-orbit__value {
  color: #ffffff;
  font-size: 2.1rem;
  font-weight: 740;
  line-height: 1;
}

.progress-orbit__value small {
  font-size: 1rem;
}

.progress-orbit__label {
  position: absolute;
  top: calc(50% + 1.35rem);
  color: rgba(230, 239, 248, 0.72);
  font-size: 0.86rem;
}

.overview-list {
  display: grid;
  gap: 1.55rem;
  margin: 0;
}

.overview-list div {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  color: rgba(222, 232, 241, 0.68);
  font-size: 0.95rem;
}

.overview-list dd {
  margin: 0;
  color: #ffffff;
  font-weight: 620;
}

.daily-tip {
  display: grid;
  grid-template-columns: 82px 1fr 36px;
  gap: 1.05rem;
  align-items: center;
  padding: 1.65rem 1.8rem;
}

.daily-tip__icon {
  display: grid;
  width: 68px;
  aspect-ratio: 1;
  place-items: center;
  border-radius: 50%;
  background:
    radial-gradient(circle, rgba(255, 197, 109, 0.32), transparent 62%),
    rgba(35, 24, 11, 0.75);
  color: #ffd589;
  font-size: 2.1rem;
  box-shadow: 0 0 28px rgba(255, 197, 109, 0.14);
}

.daily-tip__lead {
  margin: 0.7rem 0 0;
  color: #ffffff;
  font-size: 1.02rem;
  font-weight: 650;
}

.daily-tip__copy,
.reward-preview p {
  margin: 0.45rem 0 0;
  color: rgba(221, 232, 241, 0.62);
  font-size: 0.88rem;
}

.daily-tip__go {
  display: grid;
  place-items: center;
  border: 0;
  background: transparent;
  color: #2efff1;
  cursor: pointer;
  font-size: 1.6rem;
}

.reward-preview {
  min-height: 208px;
  padding: 1.65rem 1.8rem;
}

.reward-preview__gift {
  position: absolute;
  right: 2rem;
  top: 2.7rem;
  color: rgba(58, 255, 241, 0.54);
  font-size: 4.1rem;
  filter: drop-shadow(0 0 20px rgba(37, 245, 238, 0.22));
}

.reward-preview__items {
  display: flex;
  gap: 2.1rem;
  margin-top: 2.15rem;
}

.reward-preview__item {
  display: grid;
  gap: 0.65rem;
  justify-items: center;
  color: #41fff1;
}

.reward-preview__item strong {
  display: grid;
  width: 56px;
  aspect-ratio: 1;
  place-items: center;
  clip-path: polygon(50% 0, 92% 25%, 92% 75%, 50% 100%, 8% 75%, 8% 25%);
  background: rgba(37, 245, 238, 0.12);
  border: 1px solid rgba(37, 245, 238, 0.38);
  font-size: 0.96rem;
}

.reward-preview__item--gem {
  color: #ba67ff;
}

.reward-preview__item--gem strong {
  clip-path: none;
  border: 0;
  background: radial-gradient(circle, rgba(186, 103, 255, 0.72), rgba(72, 31, 126, 0.3) 68%, transparent);
  font-size: 2.4rem;
}

.reward-preview__item em {
  color: #50fff2;
  font-style: normal;
  font-size: 0.88rem;
}

.bonus-claim,
.bonus-claimed {
  display: inline-flex;
  align-items: center;
  margin-top: 1.3rem;
}

.bonus-claimed {
  color: #52fff1;
  font-size: 0.9rem;
  font-weight: 700;
}

.reset-note {
  flex-shrink: 0;
  margin-top: auto;
  padding: 1rem 1.25rem;
  text-align: center;
}

.reset-note p {
  margin: 0;
  color: rgba(221, 232, 241, 0.58);
  font-size: 0.9rem;
}

@media (max-width: 1280px) {
  .daily-content {
    grid-template-columns: 1fr;
    grid-template-areas:
      'main'
      'aside';
    overflow-y: auto;
  }

  .daily-content__main {
    overflow: visible;
  }

  .daily-content__main :deep(.teacher-assign) {
    max-height: none;
  }

  .quest-board {
    min-height: 420px;
  }

  .daily-aside {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    overflow: visible;
  }

  .reset-note {
    grid-column: 1 / -1;
    margin-top: 0;
  }
}

@media (max-width: 900px) {
  .daily-shell {
    flex-direction: column;
    overflow: auto;
  }

  .daily-sidebar,
  .daily-shell--collapsed .daily-sidebar {
    width: 100%;
    min-height: auto;
    padding: 0.75rem;
  }

  .daily-sidebar__brand {
    padding: 0.25rem 0.65rem 0.75rem;
  }

  .daily-sidebar__nav {
    flex-direction: row;
    overflow-x: auto;
    padding-bottom: 0.25rem;
  }

  .daily-nav {
    min-width: 132px;
    min-height: 64px;
    padding: 0.6rem 0.85rem;
  }

  .daily-sidebar__collapse {
    display: none;
  }

  .daily-main {
    overflow: visible;
  }

  .daily-topbar,
  .daily-content {
    padding-inline: var(--plex-page-gutter-x);
  }

  .daily-content {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    overflow: visible;
  }

  .daily-content__main,
  .daily-aside {
    width: 100%;
  }

  .quest-board__panel {
    padding: 1.15rem 0.95rem;
  }

  .quest-timeline {
    --quest-time-col: 100%;
    --quest-node-col: 4.5rem;
  }

  .quest-timeline::before {
    left: calc(var(--quest-node-col) / 2 + 0.25rem);
  }

  .quest-row {
    grid-template-columns: var(--quest-node-col) minmax(0, 1fr);
    grid-template-rows: auto 1fr;
    gap: 0.55rem 0.75rem;
    align-items: start;
    min-height: 0;
    padding-left: 0.15rem;
  }

  .quest-time {
    grid-column: 1 / -1;
    grid-template-columns: 1.25rem 1fr auto;
    margin-bottom: 0;
  }

  .quest-time .n-icon {
    grid-row: auto;
  }

  .quest-node {
    grid-row: 2;
    grid-column: 1;
    width: 56px;
    height: 56px;
  }

  .quest-card {
    grid-row: 2;
    grid-column: 2;
    min-height: 76px;
    grid-template-columns: minmax(0, 1fr);
    gap: 0.45rem;
    padding: 0.85rem 0.95rem;
  }

  .quest-card__progress {
    font-size: 0.88rem;
  }

  .quest-card__ring {
    display: none;
  }

  .quest-reward {
    flex-wrap: wrap;
    justify-content: flex-start;
  }

  .daily-aside {
    grid-template-columns: 1fr;
    margin-top: 1rem;
  }

  .overview-body,
  .daily-tip {
    grid-template-columns: 1fr;
  }
}
</style>
