<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NIcon } from 'naive-ui'
import { useAuthStore } from '../stores/auth'
import {
  ChevronForwardOutline,
  DiamondOutline,
  ExtensionPuzzleOutline,
  KeyOutline,
  SparklesOutline,
  TrophyOutline,
} from '@vicons/ionicons5'
import StarFieldMap from '../components/discovery/StarFieldMap.vue'
import PlexSidebar from '../components/layout/PlexSidebar.vue'
import PlexTopbar from '../components/layout/PlexTopbar.vue'
import { fetchCurrentStudent, type CurrentStudent } from '../api/studentOverview'

const auth = useAuthStore()
const sidebarCollapsed = ref(false)
const profile = ref<CurrentStudent | null>(null)

const displayName = computed(
  () => profile.value?.real_name || auth.profile?.real_name || auth.profile?.username || 'Explorer',
)
const userLevel = computed(() => profile.value?.level ?? auth.profile?.level ?? 1)
const xpCurrent = computed(() => profile.value?.total_points ?? auth.profile?.total_points ?? 0)
const streakDays = computed(() => profile.value?.consecutive_days ?? 0)
const xpTarget = 5000
const xpRatio = computed(() => Math.min(1, xpCurrent.value / xpTarget))


const resources = computed(() => [
  { key: 'xp', label: '能量', value: String(xpCurrent.value), icon: 'XP', color: '#2efff1' },
  { key: 'dust', label: '星尘', value: String(Math.floor(xpCurrent.value * 0.4)), icon: SparklesOutline, color: '#61f7ff' },
  { key: 'key', label: '星钥', value: String(Math.max(1, Math.floor(userLevel.value / 2))), icon: KeyOutline, color: '#58d7ff' },
  { key: 'fragment', label: '修复碎片', value: String(Math.max(1, streakDays.value % 5)), icon: ExtensionPuzzleOutline, color: '#ffc86b' },
  { key: 'core', label: '修复核心', value: String(Math.max(1, Math.floor(userLevel.value / 5))), icon: DiamondOutline, color: '#ffd47a' },
  { key: 'crystal', label: '试炼结晶', value: String(Math.floor(xpCurrent.value / 90) + 12), icon: TrophyOutline, color: '#c765ff' },
])

async function loadProfile() {
  try {
    profile.value = await fetchCurrentStudent()
    auth.syncProfile({
      id: profile.value.id,
      username: profile.value.username,
      email: profile.value.email,
      real_name: profile.value.real_name ?? profile.value.username,
      role: profile.value.role ?? 'student',
      level: profile.value.level,
      total_points: profile.value.total_points,
    })
  } catch {
    profile.value = null
  }
}

onMounted(loadProfile)

</script>

<template>
  <div class="cabin-shell" :class="{ 'cabin-shell--collapsed': sidebarCollapsed }">
    <PlexSidebar v-model:collapsed="sidebarCollapsed" active-key="cabin" />

    <main class="cabin-main">
      <div class="cabin-space" aria-hidden="true">
        <span class="cabin-space__planet" />
        <span class="cabin-space__star cabin-space__star--one" />
        <span class="cabin-space__star cabin-space__star--two" />
        <span class="cabin-space__star cabin-space__star--three" />
      </div>

      <PlexTopbar title="探索舱" subtitle="你的探索起点，连接知识星域与成长路线" />

      <section class="cabin-map-wrap" aria-label="探索舱">
        <StarFieldMap />

        <aside class="messenger-card" aria-label="驿站使者提示">
          <div class="messenger-bot" aria-hidden="true">
            <div class="messenger-bot__antenna" />
            <div class="messenger-bot__head">
              <span class="messenger-bot__face"></span>
            </div>
            <div class="messenger-bot__body">
              <span>✦</span>
            </div>
            <div class="messenger-bot__cape" />
          </div>
          <div class="messenger-bubble">
            <h2>驿站使者 · 小E <span aria-hidden="true">▮▮</span></h2>
            <p>建议前往「边界条件补给站」<br />那里有你需要的学习资源和能量补给哦。</p>
            <button type="button">
              查看路线
              <n-icon :component="ChevronForwardOutline" />
            </button>
          </div>
        </aside>
      </section>

      <footer class="cabin-status" aria-label="探索者资源">
        <section class="status-profile">
          <div class="level-ring" :style="{ '--level-progress': xpRatio }">
            <span>Lv.{{ userLevel }}</span>
          </div>
          <div class="status-profile__copy">
            <strong>Explorer · {{ displayName }}</strong>
            <div class="xp-track">
              <span class="xp-track__bar">
                <span :style="{ width: `${xpRatio * 100}%` }" />
              </span>
              <em>{{ xpCurrent }} / {{ xpTarget }} XP</em>
            </div>
            <p>连续探索 {{ streakDays }} 天 · 下一等级奖励 <span>星钥</span> x1</p>
          </div>
        </section>

        <section class="resource-bank">
          <h2>| 我的资源</h2>
          <div class="resource-bank__list">
            <div v-for="item in resources" :key="item.key" class="resource-item" :style="{ '--resource-color': item.color }">
              <span class="resource-item__orb">
                <template v-if="typeof item.icon === 'string'">{{ item.icon }}</template>
                <n-icon v-else :component="item.icon" />
              </span>
              <span class="resource-item__label">{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
          <a href="#" class="resource-bank__more" @click.prevent>
            更多
            <n-icon :component="ChevronForwardOutline" />
          </a>
        </section>
      </footer>
    </main>
  </div>
</template>

<style scoped>
.cabin-shell {
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

.cabin-shell--collapsed .cabin-sidebar {
  width: 84px;
}

.cabin-sidebar {
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

.cabin-sidebar__brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0 2.3rem 3.1rem;
  color: #25f5ee;
}

.brand-mark {
  filter: drop-shadow(0 0 12px rgba(37, 245, 238, 0.65));
}

.cabin-sidebar__name {
  color: #ffffff;
  font-size: 1.65rem;
  font-weight: 760;
  letter-spacing: 0.06em;
}

.cabin-sidebar__nav {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 1.05rem;
  padding-right: 1.35rem;
}

.cabin-nav {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 80px;
  gap: 0.95rem;
  padding: 0.7rem 1rem 0.7rem 2.55rem;
  color: rgba(220, 230, 241, 0.78);
  text-decoration: none;
  transition:
    background 0.18s ease,
    color 0.18s ease;
}

.cabin-nav:hover {
  color: #ffffff;
  background: rgba(37, 245, 238, 0.045);
}

.cabin-nav--active {
  color: #4ffff2;
  background:
    linear-gradient(90deg, rgba(16, 240, 192, 0.3), rgba(16, 240, 192, 0.09) 76%, transparent),
    rgba(6, 182, 212, 0.035);
}

.cabin-nav__bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  opacity: 0;
  background: linear-gradient(180deg, #5ffff3, #12d8c8);
  box-shadow: 0 0 18px rgba(37, 245, 238, 0.76);
}

.cabin-nav--active .cabin-nav__bar {
  opacity: 1;
}

.cabin-nav__icon {
  flex: 0 0 auto;
  font-size: 1.85rem;
}

.cabin-nav__label {
  font-size: 1.05rem;
  font-weight: 680;
  white-space: nowrap;
}

.cabin-sidebar__collapse {
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

.cabin-main {
  position: relative;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  background:
    radial-gradient(circle at 48% 9%, rgba(52, 211, 153, 0.1), transparent 25%),
    radial-gradient(circle at 76% 30%, rgba(79, 70, 229, 0.13), transparent 30%),
    radial-gradient(circle at 55% 54%, rgba(16, 240, 192, 0.14), transparent 38%),
    linear-gradient(180deg, #06121f 0%, #020a12 60%, #01070e 100%);
}

.cabin-main::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.58;
  background-image:
    radial-gradient(1px 1px at 11% 21%, rgba(255, 255, 255, 0.35), transparent),
    radial-gradient(1px 1px at 38% 23%, rgba(93, 214, 255, 0.45), transparent),
    radial-gradient(1px 1px at 62% 47%, rgba(255, 255, 255, 0.2), transparent),
    radial-gradient(1px 1px at 86% 18%, rgba(166, 111, 255, 0.42), transparent);
  background-size: 340px 340px;
}

.cabin-space {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.cabin-space__planet {
  position: absolute;
  left: -7%;
  bottom: -30%;
  width: 38%;
  aspect-ratio: 1;
  border-radius: 50%;
  background:
    radial-gradient(circle at 34% 30%, rgba(203, 232, 255, 0.3), transparent 10%),
    radial-gradient(circle at 45% 24%, rgba(91, 188, 255, 0.24), transparent 24%),
    radial-gradient(circle at 58% 62%, rgba(7, 18, 31, 0.96), rgba(3, 12, 22, 0.99) 58%),
    #030a12;
  box-shadow:
    inset 40px 28px 90px rgba(129, 207, 255, 0.15),
    -8px -10px 44px rgba(148, 220, 255, 0.24);
}

.cabin-space__star {
  position: absolute;
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #86f9ff;
  box-shadow: 0 0 13px rgba(134, 249, 255, 0.9);
}

.cabin-space__star--one {
  left: 36%;
  top: 30%;
}

.cabin-space__star--two {
  left: 70%;
  top: 43%;
}

.cabin-space__star--three {
  left: 48%;
  top: 66%;
}

.cabin-topbar {
  position: relative;
  z-index: 3;
  display: grid;
  grid-template-columns: minmax(240px, 1fr) minmax(320px, 520px) minmax(280px, 1fr);
  align-items: center;
  gap: 1.4rem;
  min-height: 76px;
  margin: 1.35rem 2.75rem 0;
  padding: 0 1.55rem;
  border: 1px solid rgba(117, 207, 255, 0.13);
  border-radius: 1.3rem;
  background: rgba(4, 17, 29, 0.78);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.035),
    0 22px 60px rgba(0, 0, 0, 0.16);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.cabin-crumb {
  display: flex;
  align-items: center;
  gap: 1.1rem;
  min-width: 0;
}

.cabin-crumb__chev {
  color: rgba(181, 203, 219, 0.3);
  font-size: 1.35rem;
}

.cabin-crumb__divider,
.cabin-userbar__divider {
  width: 1px;
  height: 34px;
  background: rgba(219, 235, 249, 0.1);
}

.cabin-crumb strong {
  color: #ffffff;
  font-size: 1.42rem;
  font-weight: 720;
}

.cabin-crumb__dot {
  width: 8px;
  aspect-ratio: 1;
  border-radius: 50%;
  background: #2efff1;
  box-shadow: 0 0 12px rgba(46, 255, 241, 0.7);
}

.cabin-search {
  align-self: center;
}

.cabin-search__input :deep(.n-input) {
  --n-height: 54px !important;
  --n-color: rgba(6, 18, 31, 0.68) !important;
  --n-color-focus: rgba(8, 24, 39, 0.9) !important;
  --n-border: 1px solid rgba(130, 212, 255, 0.12) !important;
  --n-border-hover: 1px solid rgba(37, 245, 238, 0.32) !important;
  --n-border-focus: 1px solid rgba(37, 245, 238, 0.48) !important;
  --n-box-shadow-focus: 0 0 0 2px rgba(37, 245, 238, 0.08) !important;
  --n-text-color: #edf7ff !important;
  --n-placeholder-color: rgba(210, 225, 238, 0.56) !important;
  font-size: 0.95rem;
}

.cabin-search__icon {
  color: #e8f9ff;
  font-size: 1.35rem;
}

.cabin-userbar {
  justify-self: end;
  display: flex;
  align-items: center;
  gap: 1.2rem;
}

.cabin-icon-btn {
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

.cabin-icon-btn:hover {
  background: rgba(255, 255, 255, 0.06);
}

.cabin-user {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  border: 0;
  background: transparent;
  color: #ffffff;
  cursor: pointer;
}

.cabin-user__avatar {
  border: 1px solid rgba(160, 211, 244, 0.26);
  background:
    radial-gradient(circle, rgba(82, 157, 255, 0.22), transparent 62%),
    #061827 !important;
  box-shadow:
    0 0 0 5px rgba(87, 139, 191, 0.1),
    0 0 18px rgba(37, 245, 238, 0.22);
}

.avatar-bot {
  position: relative;
  display: grid;
  width: 31px;
  height: 24px;
  place-items: center;
}

.avatar-bot__head {
  width: 28px;
  height: 20px;
  border-radius: 9px;
  background: #e9f3fb;
  box-shadow: inset 0 -8px 0 #111926;
}

.avatar-bot__head::before,
.avatar-bot__head::after {
  content: '';
  position: absolute;
  top: 13px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #36fff1;
  box-shadow: 0 0 7px rgba(54, 255, 241, 0.9);
}

.avatar-bot__head::before {
  left: 9px;
}

.avatar-bot__head::after {
  right: 9px;
}

.cabin-user__name {
  color: #ffffff;
  font-size: 0.98rem;
  font-weight: 680;
}

.cabin-user__chev {
  color: rgba(230, 242, 250, 0.82);
}

.cabin-map-wrap {
  position: relative;
  z-index: 2;
  height: calc(100dvh - 282px);
  min-height: 440px;
  margin: 0 2.75rem;
}

.messenger-card {
  position: absolute;
  right: 0.2rem;
  bottom: -0.1rem;
  width: 520px;
  height: 290px;
  pointer-events: none;
}

.messenger-bot {
  position: absolute;
  right: 2.6rem;
  top: 0;
  width: 190px;
  height: 180px;
  filter: drop-shadow(0 16px 34px rgba(37, 245, 238, 0.22));
}

.messenger-bot__antenna {
  position: absolute;
  left: 50%;
  top: 0;
  width: 38px;
  height: 18px;
  border: 4px solid #eef7fb;
  border-bottom: 0;
  border-radius: 18px 18px 0 0;
  transform: translateX(-50%);
}

.messenger-bot__antenna::after {
  content: '';
  position: absolute;
  right: -7px;
  top: -6px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #2efff1;
  box-shadow: 0 0 12px rgba(46, 255, 241, 0.9);
}

.messenger-bot__head {
  position: absolute;
  left: 30px;
  top: 18px;
  width: 124px;
  height: 92px;
  border: 8px solid #eaf3f7;
  border-radius: 38px;
  background: #101824;
  box-shadow:
    inset 0 0 0 3px rgba(77, 255, 238, 0.08),
    0 0 0 7px rgba(141, 210, 230, 0.12);
}

.messenger-bot__head::before,
.messenger-bot__head::after {
  content: '';
  position: absolute;
  top: 32px;
  width: 22px;
  height: 12px;
  border-radius: 999px;
  background: #35fff1;
  box-shadow: 0 0 12px rgba(53, 255, 241, 0.9);
}

.messenger-bot__head::before {
  left: 26px;
  transform: rotate(32deg);
}

.messenger-bot__head::after {
  right: 26px;
  transform: rotate(-32deg);
}

.messenger-bot__face {
  display: none;
}

.messenger-bot__body {
  position: absolute;
  left: 55px;
  top: 102px;
  display: grid;
  width: 76px;
  height: 72px;
  place-items: center;
  border-radius: 28px 28px 22px 22px;
  background: #edf6f8;
  color: #2efff1;
  font-size: 1.6rem;
}

.messenger-bot__body::before,
.messenger-bot__body::after {
  content: '';
  position: absolute;
  top: 26px;
  width: 42px;
  height: 15px;
  border-radius: 999px;
  background: #edf6f8;
}

.messenger-bot__body::before {
  left: -32px;
  transform: rotate(-32deg);
}

.messenger-bot__body::after {
  right: -32px;
  transform: rotate(32deg);
}

.messenger-bot__cape {
  position: absolute;
  right: 5px;
  bottom: 4px;
  width: 145px;
  height: 78px;
  border-radius: 70% 12% 70% 15%;
  background: linear-gradient(135deg, rgba(37, 245, 238, 0.48), rgba(13, 64, 83, 0.12));
  transform: rotate(-8deg);
  z-index: -1;
}

.messenger-bubble {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 490px;
  min-height: 168px;
  padding: 1.5rem 1.55rem 1.35rem;
  border: 1px solid rgba(39, 255, 238, 0.48);
  border-radius: 1.25rem;
  background: rgba(5, 22, 34, 0.82);
  box-shadow:
    0 0 34px rgba(39, 255, 238, 0.14),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
  pointer-events: auto;
}

.messenger-bubble h2 {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  margin: 0;
  color: #27ffee;
  font-size: 1.08rem;
}

.messenger-bubble h2 span {
  color: rgba(39, 255, 238, 0.65);
  font-size: 0.9rem;
  letter-spacing: 0.08em;
}

.messenger-bubble p {
  margin: 1rem 0 0;
  color: rgba(225, 238, 247, 0.75);
  font-size: 0.95rem;
  line-height: 1.6;
}

.messenger-bubble button {
  position: absolute;
  right: 1.55rem;
  bottom: 1rem;
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  min-height: 44px;
  padding: 0 1.15rem;
  border: 1px solid rgba(39, 255, 238, 0.36);
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(16, 240, 192, 0.42), rgba(6, 182, 212, 0.22));
  color: #eaffff;
  cursor: pointer;
  font-size: 0.94rem;
  font-weight: 720;
  box-shadow: 0 0 20px rgba(39, 255, 238, 0.16);
}

.cabin-status {
  position: relative;
  z-index: 3;
  display: grid;
  grid-template-columns: 430px minmax(0, 1fr);
  gap: 1.6rem;
  min-height: 150px;
  margin: 0 2.75rem 1.45rem;
  padding: 1.25rem 1.6rem;
  border: 1px solid rgba(90, 208, 255, 0.13);
  border-radius: 1.2rem;
  background: rgba(5, 17, 29, 0.78);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.035),
    0 -16px 60px rgba(0, 0, 0, 0.18);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.status-profile {
  display: flex;
  align-items: center;
  gap: 1.45rem;
  border-right: 1px solid rgba(220, 236, 248, 0.08);
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

.xp-track {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.9rem;
}

.xp-track__bar {
  width: 146px;
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(207, 228, 242, 0.1);
}

.xp-track__bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #19f0c9, #54f9ef);
  box-shadow: 0 0 14px rgba(46, 255, 241, 0.32);
}

.xp-track em,
.status-profile__copy p {
  color: rgba(225, 238, 247, 0.72);
  font-size: 0.82rem;
  font-style: normal;
}

.status-profile__copy p {
  margin: 0.8rem 0 0;
}

.status-profile__copy p span {
  color: #55f9ff;
}

.resource-bank {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 1rem;
  min-width: 0;
}

.resource-bank h2 {
  align-self: start;
  margin: 0;
  color: #31ffef;
  font-size: 0.94rem;
  font-weight: 740;
}

.resource-bank__list {
  display: grid;
  grid-template-columns: repeat(6, minmax(72px, 1fr));
  gap: 0.85rem;
  min-width: 0;
}

.resource-item {
  --resource-color: #2efff1;
  display: grid;
  min-width: 0;
  justify-items: center;
  gap: 0.35rem;
  color: rgba(225, 238, 247, 0.68);
  text-align: center;
}

.resource-item__orb {
  display: grid;
  width: 62px;
  aspect-ratio: 1;
  place-items: center;
  clip-path: polygon(50% 0, 92% 25%, 92% 75%, 50% 100%, 8% 75%, 8% 25%);
  background:
    radial-gradient(circle, color-mix(in srgb, var(--resource-color) 40%, transparent), transparent 68%),
    rgba(10, 31, 46, 0.8);
  color: var(--resource-color);
  font-size: 1.55rem;
  font-weight: 780;
  box-shadow: 0 0 24px color-mix(in srgb, var(--resource-color) 18%, transparent);
}

.resource-item__orb .n-icon {
  font-size: 1.8rem;
}

.resource-item__label {
  font-size: 0.78rem;
  white-space: nowrap;
}

.resource-item strong {
  color: #ffffff;
  font-size: 1.2rem;
  font-weight: 610;
}

.resource-bank__more {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: rgba(163, 191, 208, 0.72);
  font-size: 0.88rem;
  text-decoration: none;
  white-space: nowrap;
}

@media (max-width: 1280px) {
  .cabin-topbar {
    grid-template-columns: 1fr;
    height: auto;
    padding-block: 1rem;
  }

  .cabin-userbar {
    justify-self: start;
  }

  .cabin-map-wrap {
    height: auto;
    min-height: 620px;
  }

  .messenger-card {
    right: 0;
    transform: scale(0.86);
    transform-origin: right bottom;
  }

  .cabin-status {
    grid-template-columns: 1fr;
  }

  .status-profile {
    border-right: 0;
    border-bottom: 1px solid rgba(220, 236, 248, 0.08);
    padding-bottom: 1rem;
  }
}

@media (max-width: 900px) {
  .cabin-shell {
    flex-direction: column;
    overflow: auto;
  }

  .cabin-sidebar,
  .cabin-shell--collapsed .cabin-sidebar {
    width: 100%;
    min-height: auto;
    padding: 0.75rem;
  }

  .cabin-sidebar__brand {
    padding: 0.25rem 0.65rem 0.75rem;
  }

  .cabin-sidebar__nav {
    flex-direction: row;
    overflow-x: auto;
    padding-right: 0;
    gap: 0.45rem;
  }

  .cabin-nav {
    min-width: 132px;
    min-height: 64px;
    padding: 0.6rem 0.85rem;
  }

  .cabin-sidebar__collapse {
    display: none;
  }

  .cabin-main {
    overflow: visible;
  }

  .cabin-topbar,
  .cabin-map-wrap,
  .cabin-status {
    margin-inline: 1rem;
  }

  .cabin-map-wrap {
    min-height: 900px;
  }

  .messenger-card {
    position: relative;
    right: auto;
    bottom: auto;
    width: 100%;
    height: 230px;
    margin-top: 1rem;
    transform: none;
  }

  .messenger-bot {
    right: 0;
    transform: scale(0.78);
    transform-origin: right top;
  }

  .messenger-bubble {
    left: 0;
    right: auto;
    bottom: 0;
    width: min(100%, 430px);
  }

  .cabin-status {
    padding: 1rem;
  }

  .status-profile {
    align-items: flex-start;
  }

  .resource-bank {
    grid-template-columns: 1fr;
  }

  .resource-bank__list {
    grid-template-columns: repeat(3, minmax(82px, 1fr));
  }
}
</style>
