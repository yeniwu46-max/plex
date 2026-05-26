<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  NIcon,
  NButton,
  NModal,
  NTag,
  useMessage,
} from 'naive-ui'
import { useAuthStore } from '../stores/auth'
import {
  ChevronForwardOutline,
  DiamondOutline,
  ExtensionPuzzleOutline,
  FlashOutline,
  KeyOutline,
  RibbonOutline,
  SparklesOutline,
  TimeOutline,
  TrophyOutline,
} from '@vicons/ionicons5'
import TrialArenaMap from '../components/discovery/TrialArenaMap.vue'
import PlexSidebar from '../components/layout/PlexSidebar.vue'
import PlexTopbar from '../components/layout/PlexTopbar.vue'
import {
  TRIAL_MODES,
  filterTrials,
  isTrialUnlocked,
  type TrialMode,
} from '../data/trialArena'

const auth = useAuthStore()
const message = useMessage()
const sidebarCollapsed = ref(false)
const searchText = ref('')
const selectedTrialKey = ref<string | null>('ai-duel')
const enterModalOpen = ref(false)
const pendingTrial = ref<TrialMode | null>(null)

const displayName = computed(
  () => auth.profile?.real_name || auth.profile?.username || 'Explorer',
)
const userLevel = computed(() => auth.profile?.level ?? 1)
const xpCurrent = computed(() => auth.profile?.total_points ?? 0)
const xpTarget = computed(() => Math.max(500, userLevel.value * 500))
const xpRatio = computed(() => Math.min(1, xpCurrent.value / xpTarget.value))

const selectedTrial = computed(
  () => TRIAL_MODES.find((t) => t.key === selectedTrialKey.value) ?? null,
)

const unlockedCount = computed(
  () => TRIAL_MODES.filter((t) => isTrialUnlocked(t, userLevel.value)).length,
)

const filteredCount = computed(() => filterTrials(searchText.value).length)

const mascotHint = computed(() => {
  const trial = selectedTrial.value
  if (!trial) return '点击四角试炼卡片，查看详情并准备出发。'
  if (!isTrialUnlocked(trial, userLevel.value)) {
    return `「${trial.title}」需要 Lv.${trial.requiredLevel}，继续探索舱积累 XP 即可解锁。`
  }
  return `「${trial.title}」预计 ${trial.durationMin} 分钟，难度 ${'★'.repeat(trial.difficulty)}，完成可获得约 ${trial.rewardCrystal} 试炼结晶。`
})


const resources = computed(() => {
  const pts = xpCurrent.value
  return [
    { key: 'xp', label: '能量', value: String(pts), icon: 'XP' as const, color: '#2efff1' },
    { key: 'dust', label: '星尘', value: String(Math.floor(pts * 0.4)), icon: SparklesOutline, color: '#61f7ff' },
    { key: 'key', label: '星钥', value: String(Math.max(1, Math.floor(userLevel.value / 2))), icon: KeyOutline, color: '#58d7ff' },
    { key: 'frag', label: '修复碎片', value: '2', icon: ExtensionPuzzleOutline, color: '#ffc86b' },
    { key: 'core', label: '修复核心', value: '1', icon: DiamondOutline, color: '#ffd47a' },
    { key: 'crystal', label: '试炼结晶', value: String(Math.floor(pts / 90) + 12), icon: TrophyOutline, color: '#c765ff' },
  ]
})

const panelItems = [
  { key: 'history', title: '最近战绩', desc: '查看你在近期表现', icon: '⏱' },
  { key: 'rank', title: '全球排行', desc: '看看你在全球的位置', icon: '🏆' },
  { key: 'recommend', title: '智能推荐', desc: '为你推荐合适的试炼', icon: '✦' },
] as const


function onPanelAction(key: (typeof panelItems)[number]['key']) {
  const labels = { history: '最近战绩', rank: '全球排行', recommend: '智能推荐' }
  message.info(`${labels[key]}功能开发中，敬请期待`)
}

function openEnterModal(trial: TrialMode) {
  if (!isTrialUnlocked(trial, userLevel.value)) {
    message.warning(`需要达到 Lv.${trial.requiredLevel} 才能进入「${trial.title}」`)
    return
  }
  pendingTrial.value = trial
  enterModalOpen.value = true
}

function confirmEnter() {
  const trial = pendingTrial.value
  if (!trial) return
  enterModalOpen.value = false
  message.success(`「${trial.title}」入口即将开放，已为你记录选择`)
  pendingTrial.value = null
}

function onRecommendTrial() {
  const unlocked = TRIAL_MODES.filter((t) => isTrialUnlocked(t, userLevel.value))
  const pick = unlocked.sort((a, b) => a.difficulty - b.difficulty)[0]
  if (!pick) {
    message.warning('暂无可用试炼，请先提升等级')
    return
  }
  selectedTrialKey.value = pick.key
  message.success(`小E 推荐：${pick.title}`)
}
</script>

<template>
  <div class="shell" :class="{ 'shell--collapsed': sidebarCollapsed }">
    <PlexSidebar v-model:collapsed="sidebarCollapsed" active-key="trial" />

    <div class="main">
      <PlexTopbar
        v-model:search="searchText"
        title="试炼关卡"
        subtitle="选择适合你的挑战，验证并巩固知识掌握"
      />

      <div class="arena-wrap">
          <div class="arena-toolbar glass">
            <div class="arena-toolbar__stats">
              <span class="arena-stat">
                <n-icon :component="FlashOutline" :size="16" />
                已解锁 {{ unlockedCount }}/{{ TRIAL_MODES.length }}
              </span>
              <span v-if="searchText.trim()" class="arena-stat arena-stat--muted">
                匹配 {{ filteredCount }} 个
              </span>
            </div>
            <div class="arena-toolbar__actions">
              <n-button
                v-if="selectedTrial && isTrialUnlocked(selectedTrial, userLevel)"
                type="primary"
                round
                size="small"
                class="arena-enter-btn"
                @click="openEnterModal(selectedTrial)"
              >
                进入试炼
              </n-button>
              <n-button quaternary round size="small" @click="onRecommendTrial">智能推荐</n-button>
            </div>
          </div>

          <trial-arena-map
            v-model="selectedTrialKey"
            :search-query="searchText"
            :user-level="userLevel"
            @enter="openEnterModal"
          />
        </div>

        <aside class="info-panel" aria-label="试炼信息面板">
          <div class="mascot">
            <svg viewBox="0 0 140 160" width="120" height="140" aria-hidden="true">
              <defs>
                <filter id="mascotGlow" x="-40%" y="-40%" width="180%" height="180%">
                  <feGaussianBlur stdDeviation="3" result="b" />
                  <feMerge>
                    <feMergeNode in="b" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>
              <ellipse cx="70" cy="148" rx="48" ry="10" fill="rgba(0,245,212,0.12)" />
              <rect x="32" y="78" width="76" height="58" rx="18" fill="#f1f5f9" />
              <circle cx="54" cy="104" r="6" fill="#0f172a" />
              <circle cx="86" cy="104" r="6" fill="#0f172a" />
              <circle cx="54" cy="104" r="2.5" fill="#00f5d4" filter="url(#mascotGlow)" />
              <circle cx="86" cy="104" r="2.5" fill="#00f5d4" filter="url(#mascotGlow)" />
              <path d="M62 118h16" stroke="#0f172a" stroke-width="3" stroke-linecap="round" />
              <rect x="52" y="48" width="36" height="36" rx="12" fill="#e2e8f0" />
              <circle cx="70" cy="62" r="8" fill="#cbd5e1" />
              <path
                d="M22 88 Q8 58 18 32 Q28 12 48 8"
                fill="none"
                stroke="#00f5d4"
                stroke-width="5"
                stroke-linecap="round"
              />
              <path
                d="M118 88 Q132 58 122 32 Q112 12 92 8"
                fill="none"
                stroke="#00f5d4"
                stroke-width="5"
                stroke-linecap="round"
              />
            </svg>
          </div>

          <div class="info-bubble glass">
            <header class="info-bubble__head">
              <p class="info-bubble__title">驿站使者 · 小E</p>
              <span class="info-bubble__role">试炼向导</span>
            </header>

            <blockquote class="info-bubble__quote">
              <p class="info-bubble__text">{{ mascotHint }}</p>
            </blockquote>

            <section v-if="selectedTrial" class="trial-detail" aria-label="当前试炼">
              <div class="trial-detail__head">
                <h3 class="trial-detail__name">{{ selectedTrial.title }}</h3>
                <p class="trial-detail__en">{{ selectedTrial.titleEn }}</p>
              </div>
              <div class="trial-detail__meta">
                <span class="trial-detail__chip">
                  <n-icon :component="TimeOutline" :size="14" />
                  {{ selectedTrial.durationMin }} 分钟
                </span>
                <span class="trial-detail__chip">
                  <n-icon :component="RibbonOutline" :size="14" />
                  +{{ selectedTrial.rewardCrystal }} 结晶
                </span>
              </div>
              <div v-if="selectedTrial.tags?.length" class="trial-detail__tags">
                <n-tag
                  v-for="tag in selectedTrial.tags"
                  :key="tag"
                  size="small"
                  round
                  :bordered="false"
                >
                  {{ tag }}
                </n-tag>
              </div>
            </section>

            <section class="info-bubble__tools" aria-label="快捷入口">
              <h3 class="info-bubble__section-title">快捷入口</h3>
              <div class="info-bubble__items">
                <button
                  v-for="item in panelItems"
                  :key="item.key"
                  type="button"
                  class="info-item"
                  @click="onPanelAction(item.key)"
                >
                  <span class="info-item__icon" aria-hidden="true">{{ item.icon }}</span>
                  <div class="info-item__text">
                    <span class="info-item__title">{{ item.title }}</span>
                    <span class="info-item__desc">{{ item.desc }}</span>
                  </div>
                  <span class="info-item__arrow" aria-hidden="true">›</span>
                </button>
              </div>
            </section>

            <p class="info-bubble__footer">更多功能，敬请期待</p>
          </div>
        </aside>

      <footer class="status" aria-label="探索者资源">
        <section class="status__user">
          <div class="level-ring" :style="{ '--level-progress': xpRatio }">
            <span>Lv.{{ userLevel }}</span>
          </div>
          <div class="status-profile__copy">
            <strong>Explorer · {{ displayName }}</strong>
            <div class="status__xpbar-wrap">
              <div class="status__xpbar">
                <div class="status__xpbar-fill" :style="{ width: `${xpRatio * 100}%` }" />
              </div>
              <span class="status__xpnums">{{ xpCurrent }} / {{ xpTarget }} XP</span>
            </div>
            <p class="status__reward">下一等级奖励 <span>星钥</span> x1</p>
          </div>
        </section>

        <section class="status__res">
          <span class="status__res-title">| 我的资源</span>
          <div class="status__res-list">
            <div
              v-for="r in resources"
              :key="r.key"
              class="res-item"
              :style="{ '--res-color': r.color }"
            >
              <span class="res-item__dot" />
              <span class="res-item__label">{{ r.label }}</span>
              <span class="res-item__val">{{ r.value }}</span>
            </div>
          </div>
          <a href="#" class="status__more" @click.prevent>更多 &gt;</a>
        </section>
      </footer>
    </div>

    <n-modal
      v-model:show="enterModalOpen"
      preset="card"
      class="enter-modal"
      :title="pendingTrial ? `进入 · ${pendingTrial.title}` : '进入试炼'"
      style="max-width: 420px"
      :bordered="false"
      @after-leave="pendingTrial = null"
    >
      <template v-if="pendingTrial">
        <p class="enter-modal__desc">{{ pendingTrial.description }}</p>
        <ul class="enter-modal__facts">
          <li>预计时长：{{ pendingTrial.durationMin }} 分钟</li>
          <li>难度：{{ '★'.repeat(pendingTrial.difficulty) }}</li>
          <li>完成奖励：约 {{ pendingTrial.rewardCrystal }} 试炼结晶</li>
        </ul>
        <p class="enter-modal__note">对战与匹配逻辑将在后续版本接入，当前为试炼入口占位</p>
      </template>
      <template #footer>
        <n-button quaternary @click="enterModalOpen = false">取消</n-button>
        <n-button type="primary" @click="confirmEnter">确认进入</n-button>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  min-height: 100%;
  height: 100dvh;
  overflow: hidden;
  background: var(--plex-bg);
  color: var(--plex-text);
  font-family:
    'Outfit',
    'Noto Sans SC',
    'Microsoft YaHei',
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
  color: rgba(148, 163, 184, 0.8) !important;
}

.sidebar__chev {
  font-size: 1rem;
  letter-spacing: -0.1em;
}

.main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-areas:
    'topbar topbar'
    'arena panel'
    'footer panel';
  grid-template-columns: minmax(0, 1fr) min(280px, 28vw);
  grid-template-rows: auto minmax(0, 1fr) auto;
  column-gap: 0.75rem;
  padding: 0 var(--plex-page-gutter-x);
  overflow: hidden;
  position: relative;
  background:
    radial-gradient(ellipse 80% 50% at 50% -10%, rgba(0, 245, 212, 0.07), transparent),
    radial-gradient(ellipse 60% 40% at 90% 60%, rgba(139, 92, 246, 0.06), transparent),
    linear-gradient(180deg, #030712 0%, #020617 50%, #020617 100%);
}

.main :deep(.plex-topbar) {
  grid-area: topbar;
  padding-inline: 0;
}

.main::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.35;
  background-image: radial-gradient(1px 1px at 10% 20%, rgba(255, 255, 255, 0.2), transparent),
    radial-gradient(1px 1px at 80% 40%, rgba(255, 255, 255, 0.15), transparent);
  background-size: 320px 320px;
}

.topbar {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.85rem 1.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  flex-wrap: wrap;
}

.topbar__left {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.topbar__crumb {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.topbar__crumb-sep {
  color: rgba(148, 163, 184, 0.5);
}

.topbar__title {
  font-size: 1.15rem;
  font-weight: 600;
  color: #f1f5f9;
}

.topbar__subtitle {
  font-size: 0.75rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(148, 163, 184, 0.7);
  font-weight: 500;
}

.topbar__search {
  flex: 1;
  min-width: 200px;
  max-width: 480px;
  margin: 0 auto;
}

.topbar__input :deep(.n-input) {
  --n-color: rgba(15, 23, 42, 0.55) !important;
  --n-border: 1px solid rgba(255, 255, 255, 0.08) !important;
  --n-border-hover: 1px solid rgba(0, 245, 212, 0.25) !important;
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

.icon-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #f1f5f9;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.5rem 0.25rem 0.35rem;
  border: none;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  cursor: pointer;
  color: inherit;
}

.user-chip:hover {
  border-color: rgba(0, 245, 212, 0.25);
}

.user-chip__avatar {
  background: linear-gradient(135deg, #0f172a, #1e293b) !important;
  color: #00f5d4 !important;
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
  margin-left: 0.15rem;
}


.arena-wrap {
  grid-area: arena;
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  padding-top: 0.5rem;
}

.arena-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.55rem 0.85rem;
  border-radius: 0.75rem;
  flex-wrap: wrap;
}

.arena-toolbar__stats {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  flex-wrap: wrap;
}

.arena-stat {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.94rem;
  font-weight: 600;
  color: #e2e8f0;
}

.arena-stat--muted {
  color: rgba(148, 163, 184, 0.85);
  font-weight: 500;
}

.arena-toolbar__actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.arena-wrap :deep(.arena) {
  flex: 1;
  min-height: 0;
}

.trial-detail {
  padding: 0.75rem 0.85rem;
  border-radius: 0.75rem;
  background: rgba(0, 245, 212, 0.06);
  border: 1px solid rgba(0, 245, 212, 0.15);
}

.trial-detail__head {
  margin-bottom: 0.55rem;
}

.trial-detail__name {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 650;
  line-height: 1.35;
  color: #f8fafc;
}

.trial-detail__en {
  margin: 0.2rem 0 0;
  font-size: 0.68rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(148, 163, 184, 0.85);
}

.trial-detail__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.trial-detail__chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.28rem 0.55rem;
  border-radius: 99px;
  font-size: 0.78rem;
  color: rgba(226, 232, 240, 0.92);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.trial-detail__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-top: 0.55rem;
  padding-top: 0.55rem;
  border-top: 1px solid rgba(0, 245, 212, 0.12);
}

.enter-modal__desc {
  margin: 0 0 0.75rem;
  color: rgba(226, 232, 240, 0.9);
  line-height: 1.5;
  font-size: 0.9rem;
}

.enter-modal__facts {
  margin: 0 0 0.75rem;
  padding-left: 1.1rem;
  color: rgba(203, 213, 225, 0.95);
  font-size: 0.85rem;
  line-height: 1.6;
}

.enter-modal__note {
  margin: 0;
  font-size: 0.78rem;
  color: rgba(148, 163, 184, 0.85);
}

.info-panel {
  grid-area: panel;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  width: 100%;
  min-height: 0;
  overflow: hidden;
  padding-top: 0.5rem;
  padding-bottom: var(--plex-page-gutter-bottom);
  gap: 0.75rem;
  align-self: stretch;
}

.mascot {
  flex-shrink: 0;
  align-self: center;
  filter: drop-shadow(0 8px 24px rgba(0, 245, 212, 0.2));
  animation: float 5s ease-in-out infinite;
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-6px);
  }
}

.glass {
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}

.info-bubble {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  overflow-y: auto;
  padding: 1.05rem 1.15rem 1rem;
  border-radius: 1rem;
  max-width: 100%;
}

.info-bubble__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
  padding-bottom: 0.65rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.info-bubble__title {
  margin: 0;
  font-size: 0.94rem;
  font-weight: 740;
  color: #31ffef;
}

.info-bubble__role {
  flex-shrink: 0;
  font-size: 0.72rem;
  font-weight: 500;
  color: rgba(148, 163, 184, 0.75);
  letter-spacing: 0.04em;
}

.info-bubble__quote {
  margin: 0;
  padding: 0.65rem 0 0.65rem 0.75rem;
  border-left: 3px solid rgba(0, 245, 212, 0.45);
  background: rgba(0, 245, 212, 0.04);
  border-radius: 0 0.5rem 0.5rem 0;
}

.info-bubble__text {
  margin: 0;
  font-size: 0.88rem;
  font-weight: 500;
  line-height: 1.6;
  color: rgba(241, 245, 249, 0.92);
}

.info-bubble__tools {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.info-bubble__section-title {
  margin: 0;
  font-size: 0.72rem;
  font-weight: 650;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(148, 163, 184, 0.8);
}

.info-bubble__items {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin: 0;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  width: 100%;
  padding: 0.55rem 0.65rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 0.6rem;
  cursor: pointer;
  color: inherit;
  font: inherit;
  text-align: left;
  transition:
    background 0.25s ease,
    border-color 0.25s ease;
}

.info-item:hover {
  background: rgba(0, 245, 212, 0.08);
  border-color: rgba(0, 245, 212, 0.25);
}

.info-item__icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.info-item__text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.15rem;
  flex: 1;
}

.info-item__title {
  display: block;
  font-size: 0.88rem;
  font-weight: 650;
  line-height: 1.3;
  color: #f1f5f9;
}

.info-item__desc {
  display: block;
  margin-top: 0.12rem;
  font-size: 0.78rem;
  line-height: 1.4;
  color: rgba(148, 163, 184, 0.78);
}

.info-item__arrow {
  flex-shrink: 0;
  font-size: 1.1rem;
  line-height: 1;
  color: var(--plex-accent);
  opacity: 0.65;
}

.info-bubble__footer {
  margin: 0;
  padding-top: 0.65rem;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 0.82rem;
  line-height: 1.5;
  color: rgba(148, 163, 184, 0.65);
  text-align: center;
}

.status {
  grid-area: footer;
  position: relative;
  z-index: 2;
  margin: 0.65rem 0 var(--plex-page-gutter-bottom);
  padding: 1.25rem 1.6rem;
  border-radius: 1.2rem;
  display: grid;
  grid-template-columns: 430px minmax(0, 1fr);
  gap: 1.6rem;
  align-items: center;
  min-height: 150px;
  border: 1px solid rgba(90, 208, 255, 0.13);
  background: rgba(5, 17, 29, 0.78);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.035),
    0 -16px 60px rgba(0, 0, 0, 0.18);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.status__user {
  display: flex;
  align-items: center;
  gap: 1.45rem;
  border-right: 1px solid rgba(220, 236, 248, 0.08);
  padding-right: 1.45rem;
}

.level-ring {
  --ring-deg: calc(var(--level-progress) * 360deg);
  display: grid;
  width: 98px;
  aspect-ratio: 1;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, #071625 57%, transparent 58%),
    conic-gradient(#7bf8ff var(--ring-deg), rgba(75, 128, 160, 0.24) 0);
  color: #ffffff;
  box-shadow: 0 0 22px rgba(46, 255, 241, 0.12);
}

.level-ring span {
  font-size: 1.28rem;
  font-weight: 720;
}

.status-profile__copy {
  min-width: 0;
}

.status-profile__copy strong {
  display: block;
  color: #37fff1;
  font-size: 1.26rem;
  font-weight: 660;
}

.xp-ring {
  position: relative;
  width: 98px;
  height: 98px;
  flex-shrink: 0;
}

.xp-ring__svg {
  width: 100%;
  height: 100%;
}

.xp-ring__lv {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.28rem;
  font-weight: 720;
  color: #ffffff;
}

.status__meta {
  min-width: 0;
}

.status__explorer {
  font-size: 1.26rem;
  font-weight: 660;
  color: #37fff1;
}

.status__xpbar-wrap {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.9rem;
}

.status__xpbar {
  flex: 1;
  height: 8px;
  border-radius: 99px;
  background: rgba(207, 228, 242, 0.1);
  overflow: hidden;
  min-width: 146px;
}

.status__xpbar-fill {
  height: 100%;
  border-radius: 99px;
  background: linear-gradient(90deg, #19f0c9, #54f9ef);
  box-shadow: 0 0 14px rgba(46, 255, 241, 0.32);
}

.status__xpnums {
  font-size: 0.82rem;
  font-style: normal;
  color: rgba(225, 238, 247, 0.72);
  white-space: nowrap;
}

.status__reward {
  margin: 0.8rem 0 0;
  font-size: 0.82rem;
  color: rgba(225, 238, 247, 0.72);
}

.status__reward span,
.status__star {
  color: #55f9ff;
}

.status__res {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 1rem;
  min-width: 0;
}

.status__res-title {
  align-self: start;
  margin: 0;
  font-size: 0.94rem;
  font-weight: 740;
  color: #31ffef;
  white-space: nowrap;
}

.status__res-list {
  display: grid;
  grid-template-columns: repeat(6, minmax(72px, 1fr));
  gap: 0.85rem;
  min-width: 0;
}

.res-item {
  display: grid;
  min-width: 0;
  justify-items: center;
  gap: 0.35rem;
  text-align: center;
  white-space: nowrap;
}

.res-item__dot {
  display: grid;
  width: 62px;
  aspect-ratio: 1;
  place-items: center;
  clip-path: polygon(50% 0, 92% 25%, 92% 75%, 50% 100%, 8% 75%, 8% 25%);
  background:
    radial-gradient(circle, color-mix(in srgb, var(--res-color, #2efff1) 40%, transparent), transparent 68%),
    rgba(10, 31, 46, 0.8);
  box-shadow: 0 0 24px color-mix(in srgb, var(--res-color, #2efff1) 18%, transparent);
}

.res-item__dot::after {
  content: '';
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--res-color, #2efff1);
  box-shadow: 0 0 12px var(--res-color, #2efff1);
}

.res-item__label {
  font-size: 0.78rem;
  color: rgba(225, 238, 247, 0.68);
}

.res-item__val {
  font-size: 1.2rem;
  font-weight: 610;
  color: #ffffff;
}

.status__more {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.88rem;
  color: rgba(163, 191, 208, 0.72);
  text-decoration: none;
  white-space: nowrap;
}

.status__more:hover {
  text-decoration: underline;
}

@media (max-width: 1100px) {
  .main {
    grid-template-areas:
      'topbar'
      'arena'
      'footer';
    grid-template-columns: minmax(0, 1fr);
  }

  .info-panel {
    display: none;
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

  .shell--collapsed .sidebar {
    width: 100% !important;
  }

  .sidebar__nav {
    flex-direction: row;
    flex-wrap: wrap;
    flex: 1;
  }

  .sidebar__collapse {
    display: none;
  }

  .topbar__search {
    order: 3;
    flex: 1 1 100%;
    max-width: none;
  }

  .status__res {
    justify-content: flex-start;
  }
}
</style>
