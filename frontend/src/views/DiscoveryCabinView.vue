<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import {
  NInput,
  NIcon,
  NAvatar,
  NBadge,
  NButton,
} from 'naive-ui'
import {
  RocketOutline,
  GitNetworkOutline,
  BarbellOutline,
  MailOutline,
  CalendarOutline,
  ArchiveOutline,
  ChevronBackOutline,
  SearchOutline,
  NotificationsOutline,
  ChevronDownOutline,
} from '@vicons/ionicons5'
import StarFieldMap from '../components/discovery/StarFieldMap.vue'

const router = useRouter()
const sidebarCollapsed = ref(false)
const searchText = ref('')

const xpCurrent = 3260
const xpTarget = 5000
const xpRatio = computed(() => Math.min(1, xpCurrent / xpTarget))

const navItems = [
  { key: 'cabin', label: '探索舱', icon: RocketOutline, active: true, to: '/discovery' },
  { key: 'track', label: '星轨路径', icon: GitNetworkOutline, active: false, to: '/star-path' },
  { key: 'trial', label: '试炼关卡', icon: BarbellOutline, active: false, to: '#' },
  { key: 'messenger', label: '驿站使者', icon: MailOutline, active: false, to: '#' },
  { key: 'daily', label: '今日委托', icon: CalendarOutline, active: false, to: '#' },
  { key: 'archive', label: '探索档案', icon: ArchiveOutline, active: false, to: '#' },
] as const

const resources = [
  { key: 'xp', label: 'XP 能量', value: '3260', color: '#22d3ee' },
  { key: 'dust', label: '星尘', value: '1280', color: '#a78bfa' },
  { key: 'key', label: '星钥', value: '8', color: '#fbbf24' },
  { key: 'frag', label: '修复碎片', value: '2', color: '#fb923c' },
  { key: 'core', label: '修复核心', value: '1', color: '#f472b6' },
  { key: 'crystal', label: '试炼结晶', value: '36', color: '#34d399' },
]

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/login')
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}
</script>

<template>
  <div class="shell" :class="{ 'shell--collapsed': sidebarCollapsed }">
    <aside class="sidebar" aria-label="主导航">
      <div class="sidebar__brand">
        <svg class="sidebar__logo" viewBox="0 0 48 48" width="28" height="28" aria-hidden="true">
          <path fill="currentColor" d="M24 4l5.2 14.8L44 24l-14.8 5.2L24 44l-5.2-14.8L4 24l14.8-5.2L24 4z" />
        </svg>
        <span v-if="!sidebarCollapsed" class="sidebar__name">PLEX</span>
      </div>

      <nav class="sidebar__nav">
        <component
          :is="item.to.startsWith('/') ? RouterLink : 'a'"
          v-for="item in navItems"
          :key="item.key"
          :to="item.to.startsWith('/') ? item.to : undefined"
          :href="item.to.startsWith('/') ? undefined : item.to"
          class="nav-item"
          :class="{ 'nav-item--active': item.active }"
          @click="(e: MouseEvent) => item.to === '#' && e.preventDefault()"
        >
          <span class="nav-item__accent" aria-hidden="true" />
          <n-icon :component="item.icon" class="nav-item__icon" />
          <span v-if="!sidebarCollapsed" class="nav-item__label">{{ item.label }}</span>
        </component>
      </nav>

      <n-button quaternary circle class="sidebar__collapse" @click="toggleSidebar">
        <span class="sidebar__chev" aria-hidden="true">«</span>
      </n-button>
    </aside>

    <div class="main">
      <header class="topbar">
        <div class="topbar__left">
          <button type="button" class="icon-btn" aria-label="返回" @click="goBack">
            <n-icon :component="ChevronBackOutline" :size="22" />
          </button>
          <h1 class="topbar__title">探索舱</h1>
        </div>

        <div class="topbar__search">
          <n-input
            v-model:value="searchText"
            round
            placeholder="搜索知识点、试炼或星域"
            clearable
            class="topbar__input"
          >
            <template #prefix>
              <n-icon :component="SearchOutline" class="topbar__search-icon" />
            </template>
          </n-input>
        </div>

        <div class="topbar__right">
          <n-badge dot type="success" :offset="[-2, 4]">
            <button type="button" class="icon-btn" aria-label="通知">
              <n-icon :component="NotificationsOutline" :size="22" />
            </button>
          </n-badge>

          <button type="button" class="user-chip">
            <n-avatar round :size="36" class="user-chip__avatar">★</n-avatar>
            <div class="user-chip__text">
              <span class="user-chip__name">张子轩</span>
              <span class="user-chip__lv">Lv.18</span>
            </div>
            <n-icon :component="ChevronDownOutline" :size="18" class="user-chip__arrow" />
          </button>
        </div>
      </header>

      <div class="content">
        <star-field-map />

        <aside class="mascot-panel" aria-label="驿站使者提示">
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
          <div class="bubble glass">
            <p class="bubble__who">驿站使者 · 小E · 小小</p>
            <p class="bubble__text">
              建议前往「边界条件补给站」，那里有你需要的学习资源和能量补给哦！
            </p>
            <a href="#" class="bubble__link" @click.prevent>查看路线 &gt;</a>
          </div>
        </aside>
      </div>

      <footer class="status glass">
        <div class="status__user">
          <div class="xp-ring" aria-hidden="true">
            <svg viewBox="0 0 64 64" class="xp-ring__svg">
              <circle cx="32" cy="32" r="26" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="5" />
              <circle
                cx="32"
                cy="32"
                r="26"
                fill="none"
                stroke="url(#xpGrad)"
                stroke-width="5"
                stroke-linecap="round"
                :stroke-dasharray="`${xpRatio * 163.36} 163.36`"
                transform="rotate(-90 32 32)"
              />
              <defs>
                <linearGradient id="xpGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stop-color="#00f5d4" />
                  <stop offset="100%" stop-color="#06b6d4" />
                </linearGradient>
              </defs>
            </svg>
            <span class="xp-ring__lv">Lv.18</span>
          </div>
          <div class="status__meta">
            <div class="status__row">
              <span class="status__explorer">Explorer · 张子轩</span>
            </div>
            <div class="status__xpbar-wrap">
              <div class="status__xpbar">
                <div class="status__xpbar-fill" :style="{ width: `${xpRatio * 100}%` }" />
              </div>
              <span class="status__xpnums">{{ xpCurrent }} / {{ xpTarget }} XP</span>
            </div>
            <p class="status__reward">下一等级奖励 <span class="status__star">★</span> x1</p>
          </div>
        </div>

        <div class="status__res">
          <span class="status__res-title">| 我的资源</span>
          <div class="status__res-list">
            <div v-for="r in resources" :key="r.key" class="res-item">
              <span class="res-item__dot" :style="{ background: r.color, boxShadow: `0 0 12px ${r.color}66` }" />
              <span class="res-item__label">{{ r.label }}</span>
              <span class="res-item__val">{{ r.value }}</span>
            </div>
          </div>
          <a href="#" class="status__more" @click.prevent>更多 &gt;</a>
        </div>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  min-height: 100%;
  background: #020617;
  color: #e2e8f0;
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
  color: #00f5d4;
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
  color: #00f5d4;
  background: rgba(0, 245, 212, 0.08);
  box-shadow: inset 0 0 24px rgba(0, 245, 212, 0.06);
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
  background: linear-gradient(180deg, #00f5d4, #0891b2);
  box-shadow: 0 0 12px rgba(0, 245, 212, 0.6);
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
  display: flex;
  flex-direction: column;
  position: relative;
  background:
    radial-gradient(ellipse 80% 50% at 50% -10%, rgba(0, 245, 212, 0.07), transparent),
    radial-gradient(ellipse 60% 40% at 90% 60%, rgba(139, 92, 246, 0.06), transparent),
    linear-gradient(180deg, #030712 0%, #020617 50%, #020617 100%);
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

.topbar__title {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 600;
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
  color: #00f5d4;
  font-weight: 600;
}

.user-chip__arrow {
  color: rgba(148, 163, 184, 0.8);
  margin-left: 0.15rem;
}

.content {
  position: relative;
  z-index: 1;
  flex: 1;
  min-height: 0;
  padding: 0.5rem 1rem 1rem;
  display: flex;
  align-items: stretch;
  justify-content: center;
  gap: 0.5rem;
}

.mascot-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: min(280px, 28vw);
  flex-shrink: 0;
  padding-top: 2rem;
  gap: 0.75rem;
}

.mascot {
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

.bubble {
  padding: 1rem 1.1rem;
  border-radius: 1rem;
  max-width: 100%;
}

.bubble__who {
  margin: 0 0 0.5rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: #94a3b8;
}

.bubble__text {
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.55;
  color: rgba(241, 245, 249, 0.9);
}

.bubble__link {
  display: inline-block;
  margin-top: 0.65rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: #00f5d4;
  text-decoration: none;
}

.bubble__link:hover {
  text-decoration: underline;
}

.status {
  position: relative;
  z-index: 2;
  margin: 0 1rem 1rem;
  padding: 0.85rem 1.25rem;
  border-radius: 1rem;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1.25rem 2rem;
  justify-content: space-between;
}

.status__user {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.xp-ring {
  position: relative;
  width: 56px;
  height: 56px;
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
  font-size: 0.65rem;
  font-weight: 700;
  color: #00f5d4;
}

.status__meta {
  min-width: 200px;
}

.status__explorer {
  font-size: 0.85rem;
  font-weight: 600;
  color: #f1f5f9;
}

.status__xpbar-wrap {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin-top: 0.35rem;
}

.status__xpbar {
  flex: 1;
  height: 6px;
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
  min-width: 120px;
}

.status__xpbar-fill {
  height: 100%;
  border-radius: 99px;
  background: linear-gradient(90deg, #00f5d4, #06b6d4);
  box-shadow: 0 0 12px rgba(0, 245, 212, 0.4);
}

.status__xpnums {
  font-size: 0.72rem;
  color: rgba(148, 163, 184, 0.95);
  white-space: nowrap;
}

.status__reward {
  margin: 0.35rem 0 0;
  font-size: 0.72rem;
  color: rgba(148, 163, 184, 0.85);
}

.status__star {
  color: #fbbf24;
}

.status__res {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
  min-width: 0;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.status__res-title {
  font-size: 0.78rem;
  color: rgba(148, 163, 184, 0.75);
  white-space: nowrap;
}

.status__res-list {
  display: flex;
  align-items: center;
  gap: 0.85rem 1.1rem;
  flex-wrap: wrap;
  overflow-x: auto;
  padding-bottom: 0.15rem;
}

.res-item {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.75rem;
  white-space: nowrap;
}

.res-item__dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.res-item__label {
  color: rgba(148, 163, 184, 0.9);
}

.res-item__val {
  font-weight: 600;
  color: #f1f5f9;
}

.status__more {
  font-size: 0.78rem;
  color: #00f5d4;
  text-decoration: none;
  white-space: nowrap;
}

.status__more:hover {
  text-decoration: underline;
}

@media (max-width: 1100px) {
  .mascot-panel {
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
