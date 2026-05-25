<script setup lang="ts">
import { computed, ref } from 'vue'
import { NIcon, NInput } from 'naive-ui'
import { useAuthStore } from '../stores/auth'
import {
  AnalyticsOutline,
  BarbellOutline,
  GitNetworkOutline,
  NavigateOutline,
  PaperPlaneOutline,
  PulseOutline,
  SparklesOutline,
  TelescopeOutline,
  TrendingUpOutline,
} from '@vicons/ionicons5'
import PlexSidebar from '../components/layout/PlexSidebar.vue'
import PlexTopbar from '../components/layout/PlexTopbar.vue'

const auth = useAuthStore()
const sidebarCollapsed = ref(false)
const prompt = ref('')

const displayName = computed(() => auth.profile?.real_name || auth.profile?.username || '张子轩')


const suggestions = [
  { title: '学习分析', desc: '你在「动态规划」停留时间较长，建议优先修复「边界条件碎片」。', icon: AnalyticsOutline },
  { title: '知识修复路线', desc: '已为你生成修复路线', icon: PulseOutline },
  { title: '今日建议', desc: '适当休息有助于提升效率，明天再继续挑战吧。', icon: SparklesOutline },
] as const

const actions = [
  { label: '分析我的薄弱点', icon: TelescopeOutline },
  { label: '推荐下一试炼', icon: BarbellOutline },
  { label: '生成修复路线', icon: GitNetworkOutline },
  { label: '查看最近成长', icon: TrendingUpOutline },
] as const

</script>

<template>
  <div class="messenger-shell" :class="{ 'messenger-shell--collapsed': sidebarCollapsed }">
    <PlexSidebar v-model:collapsed="sidebarCollapsed" active-key="messenger" />

    <main class="messenger-main">
      <PlexTopbar title="驿站使者" subtitle="你的专属驿站，知识与成长的陪伴者" />

      <section class="messenger-stage" aria-label="驿站使者">
        <div class="station-bg" aria-hidden="true">
          <span class="station-bg__planet" />
          <span class="station-bg__ring station-bg__ring--top" />
          <span class="station-bg__ring station-bg__ring--floor" />
          <span class="station-bg__light station-bg__light--one" />
          <span class="station-bg__light station-bg__light--two" />
          <span class="station-bg__crystal station-bg__crystal--one" />
          <span class="station-bg__crystal station-bg__crystal--two" />
        </div>

        <section class="hero-zone">
          <article class="float-card float-card--greeting">
            <h2>晚上好，<span>{{ displayName }}</span></h2>
            <p>今天也在不断探索与成长呢</p>
            <div class="wave-bars" aria-hidden="true"><span /><span /><span /><span /><span /></div>
          </article>

          <article class="float-card float-card--fragment">
            <p>待修复知识碎</p>
            <strong>2 <span></span></strong>
            <a href="#" @click.prevent>去修复 <n-icon :component="NavigateOutline" /></a>
            <n-icon :component="GitNetworkOutline" class="float-card__watermark" />
          </article>

          <div class="assistant-bot" aria-hidden="true">
            <span class="assistant-bot__crest" />
            <span class="assistant-bot__head" />
            <span class="assistant-bot__ear assistant-bot__ear--left" />
            <span class="assistant-bot__ear assistant-bot__ear--right" />
            <span class="assistant-bot__face" />
            <span class="assistant-bot__body"><em></em></span>
            <span class="assistant-bot__arm assistant-bot__arm--left" />
            <span class="assistant-bot__arm assistant-bot__arm--right" />
            <span class="assistant-bot__cape" />
          </div>

          <article class="float-card float-card--trial">
            <h2>推荐下一试炼</h2>
            <strong>路径优化 · 进阶</strong>
            <p>匹配度 92%</p>
            <a href="#" @click.prevent>开始试炼 <n-icon :component="NavigateOutline" /></a>
            <span class="radar" aria-hidden="true" />
          </article>

          <article class="float-card float-card--growth">
            <h2>最近成长</h2>
            <p>连续探索 <strong>5 </strong></p>
            <p>击败了 <span>80%</span> 的 Explorer</p>
            <svg viewBox="0 0 100 44" class="growth-line" aria-hidden="true">
              <polyline points="4,36 20,28 32,32 45,18 57,22 70,10 82,17 96,4" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </article>
        </section>

        <aside class="analysis-panel" aria-label="学习分析建议">
          <header>
            <h2>小E 正在为你分析 <span aria-hidden="true">▮▮</span></h2>
          </header>
          <div class="analysis-list">
            <article v-for="item in suggestions" :key="item.title" class="analysis-card">
              <span class="analysis-card__icon">
                <n-icon :component="item.icon" />
              </span>
              <div>
                <strong>{{ item.title }}</strong>
                <p>{{ item.desc }}</p>
              </div>
            </article>
          </div>
          <button type="button" class="all-advice">
            查看全部建议
            <n-icon :component="NavigateOutline" />
          </button>
        </aside>

        <section class="prompt-dock" aria-label="向小E提问">
          <div class="prompt-line">
            <n-input
              v-model:value="prompt"
              placeholder="向小E提问，或让小E帮你分析学习情况..."
              class="prompt-input"
              :bordered="false"
            />
            <button type="button" aria-label="发送">
              <n-icon :component="PaperPlaneOutline" />
            </button>
          </div>
          <div class="prompt-actions">
            <button v-for="item in actions" :key="item.label" type="button">
              <n-icon :component="item.icon" />
              {{ item.label }}
            </button>
          </div>
        </section>
      </section>
    </main>
  </div>
</template>

<style scoped>
.messenger-shell {
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

.messenger-shell--collapsed .messenger-sidebar {
  width: 84px;
}

.messenger-sidebar {
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
  transition: width 0.2s ease;
}

.messenger-sidebar__brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0 2.55rem 2.85rem;
  color: #25f5ee;
}

.brand-mark {
  filter: drop-shadow(0 0 12px rgba(37, 245, 238, 0.65));
}

.messenger-sidebar__name {
  color: #ffffff;
  font-size: 1.75rem;
  font-weight: 760;
  letter-spacing: 0.08em;
}

.messenger-sidebar__nav {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 0.55rem;
}

.messenger-nav {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 76px;
  gap: 0.95rem;
  padding: 0.7rem 1.35rem 0.7rem 2.55rem;
  color: rgba(220, 230, 241, 0.74);
  text-decoration: none;
  transition: background 0.18s ease, color 0.18s ease;
}

.messenger-nav:hover {
  color: #ffffff;
  background: rgba(37, 245, 238, 0.045);
}

.messenger-nav--active {
  color: #ffffff;
  background:
    linear-gradient(90deg, rgba(16, 240, 192, 0.25), rgba(16, 240, 192, 0.07) 72%, transparent),
    rgba(6, 182, 212, 0.04);
}

.messenger-nav__bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  opacity: 0;
  background: linear-gradient(180deg, #5ffff3, #12d8c8);
  box-shadow: 0 0 18px rgba(37, 245, 238, 0.76);
}

.messenger-nav--active .messenger-nav__bar {
  opacity: 1;
}

.messenger-nav__icon {
  flex: 0 0 auto;
  font-size: 1.95rem;
}

.messenger-nav__copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.25rem;
  line-height: 1.1;
}

.messenger-nav__label {
  font-size: 1rem;
  font-weight: 670;
  white-space: nowrap;
}

.messenger-nav__sub {
  color: rgba(221, 230, 239, 0.55);
  font-size: 0.72rem;
  font-weight: 680;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.messenger-nav--active .messenger-nav__label,
.messenger-nav--active .messenger-nav__sub {
  color: #52fff1;
  text-shadow: 0 0 14px rgba(37, 245, 238, 0.5);
}

.messenger-sidebar__collapse {
  width: 56px;
  height: 56px;
  align-self: center;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 50%;
  background: rgba(12, 27, 40, 0.68);
  color: #d9f4ff;
  cursor: pointer;
  font-size: 1.5rem;
}

.messenger-main {
  position: relative;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 38%, rgba(52, 211, 153, 0.08), transparent 30%),
    radial-gradient(circle at 76% 55%, rgba(22, 78, 99, 0.2), transparent 34%),
    linear-gradient(180deg, #06121f 0%, #020a12 61%, #01070e 100%);
}

.messenger-topbar {
  position: relative;
  z-index: 3;
  display: grid;
  grid-template-columns: minmax(260px, 1fr) minmax(320px, 540px) minmax(260px, 1fr);
  align-items: start;
  gap: 1.5rem;
  padding: 2.15rem 2.8rem 1.15rem 3.7rem;
}

.messenger-heading h1 {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  margin: 0;
  color: #ffffff;
  font-size: clamp(1.7rem, 2.2vw, 2.25rem);
  font-weight: 740;
  line-height: 1.1;
}

.messenger-heading h1 span {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #2efff1;
  box-shadow: 0 0 12px rgba(46, 255, 241, 0.85);
}

.messenger-heading p {
  margin: 0.7rem 0 0;
  color: rgba(221, 230, 239, 0.72);
  font-size: 0.98rem;
}

.messenger-search__input :deep(.n-input) {
  --n-height: 58px !important;
  --n-color: rgba(6, 18, 31, 0.66) !important;
  --n-color-focus: rgba(8, 24, 39, 0.86) !important;
  --n-border: 1px solid rgba(130, 212, 255, 0.12) !important;
  --n-border-hover: 1px solid rgba(37, 245, 238, 0.32) !important;
  --n-text-color: #edf7ff !important;
  --n-placeholder-color: rgba(210, 225, 238, 0.55) !important;
  font-size: 0.96rem;
}

.messenger-search__icon {
  color: #e8f9ff;
  font-size: 1.35rem;
}

.messenger-userbar {
  justify-self: end;
  display: flex;
  align-items: center;
  gap: 1.3rem;
}

.messenger-userbar__divider {
  width: 1px;
  height: 40px;
  background: rgba(219, 235, 249, 0.1);
}

.messenger-icon-btn {
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

.messenger-user {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  border: 0;
  background: transparent;
  color: #ffffff;
  cursor: pointer;
}

.messenger-user__avatar {
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

.messenger-user__copy {
  display: grid;
  gap: 0.2rem;
  text-align: left;
}

.messenger-user__copy strong {
  font-size: 0.96rem;
}

.messenger-user__copy em {
  width: fit-content;
  padding: 0.04rem 0.34rem;
  border-radius: 0.35rem;
  background: rgba(37, 245, 238, 0.18);
  color: #57fff2;
  font-size: 0.76rem;
  font-style: normal;
}

.messenger-stage {
  position: relative;
  z-index: 2;
  height: calc(100dvh - 124px);
  min-height: 0;
  overflow: hidden;
  padding: 0 2.8rem 2rem 3.7rem;
}

.station-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.station-bg::before {
  content: '';
  position: absolute;
  inset: 0;
  opacity: 0.48;
  background-image:
    radial-gradient(1px 1px at 12% 24%, rgba(255, 255, 255, 0.36), transparent),
    radial-gradient(1px 1px at 43% 18%, rgba(93, 214, 255, 0.45), transparent),
    radial-gradient(1px 1px at 63% 40%, rgba(255, 255, 255, 0.2), transparent),
    radial-gradient(1px 1px at 87% 22%, rgba(93, 214, 255, 0.24), transparent);
  background-size: 330px 330px;
}

.station-bg__planet {
  position: absolute;
  left: -12%;
  bottom: 12%;
  width: 31%;
  aspect-ratio: 1;
  border-radius: 50%;
  background:
    radial-gradient(circle at 35% 30%, rgba(203, 232, 255, 0.24), transparent 12%),
    radial-gradient(circle at 55% 58%, rgba(7, 18, 31, 0.96), rgba(3, 12, 22, 0.99) 58%);
  box-shadow:
    inset 36px 24px 84px rgba(129, 207, 255, 0.12),
    -8px -10px 44px rgba(148, 220, 255, 0.18);
}

.station-bg__ring {
  position: absolute;
  left: 50%;
  border: 1px solid rgba(211, 229, 240, 0.09);
  border-radius: 50%;
  transform: translateX(-50%);
}

.station-bg__ring--top {
  top: -190px;
  width: 80%;
  height: 340px;
  border-bottom-color: rgba(230, 241, 249, 0.28);
  box-shadow: inset 0 -10px 40px rgba(198, 218, 230, 0.05);
}

.station-bg__ring--floor {
  bottom: 7%;
  width: 38%;
  height: 120px;
  border-color: rgba(37, 245, 238, 0.2);
  box-shadow: 0 0 42px rgba(37, 245, 238, 0.14);
}

.station-bg__light {
  position: absolute;
  height: 4px;
  border-radius: 99px;
  background: linear-gradient(90deg, transparent, rgba(238, 248, 255, 0.86), transparent);
}

.station-bg__light--one {
  left: 35%;
  top: 7.5%;
  width: 18%;
}

.station-bg__light--two {
  right: -2%;
  top: 8%;
  width: 22%;
  opacity: 0.6;
}

.station-bg__crystal {
  position: absolute;
  width: 20px;
  height: 34px;
  clip-path: polygon(50% 0, 100% 50%, 50% 100%, 0 50%);
  background: linear-gradient(180deg, rgba(97, 247, 255, 0.45), rgba(12, 67, 86, 0.12));
  border: 1px solid rgba(97, 247, 255, 0.18);
}

.station-bg__crystal--one {
  left: 31%;
  top: 38%;
}

.station-bg__crystal--two {
  left: 36%;
  top: 56%;
  transform: scale(0.72);
}

.hero-zone {
  position: absolute;
  left: 7%;
  right: 25%;
  top: 9%;
  bottom: 18%;
}

.float-card {
  position: absolute;
  border: 1px solid rgba(105, 219, 255, 0.2);
  border-radius: 0.9rem;
  background:
    linear-gradient(180deg, rgba(13, 31, 49, 0.72), rgba(7, 21, 35, 0.68)),
    rgba(6, 18, 31, 0.7);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.035),
    0 16px 40px rgba(0, 0, 0, 0.16);
  backdrop-filter: blur(14px);
}

.float-card h2,
.float-card p {
  margin: 0;
}

.float-card--greeting {
  left: 3%;
  top: 12%;
  width: 310px;
  min-height: 154px;
  padding: 1.55rem 1.7rem;
}

.float-card--greeting h2 {
  color: #ffffff;
  font-size: 1.18rem;
}

.float-card--greeting h2 span {
  color: #29fff0;
}

.float-card--greeting p {
  margin-top: 0.7rem;
  color: rgba(230, 240, 247, 0.82);
}

.wave-bars {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 1.55rem;
  color: #31fff2;
}

.wave-bars span {
  width: 2px;
  height: 11px;
  border-radius: 99px;
  background: currentColor;
  box-shadow: 0 0 8px rgba(49, 255, 242, 0.7);
}

.wave-bars span:nth-child(2),
.wave-bars span:nth-child(4) {
  height: 18px;
}

.float-card--fragment {
  left: 7%;
  bottom: 11%;
  width: 258px;
  min-height: 150px;
  padding: 1.45rem 1.6rem;
}

.float-card--fragment p {
  color: #ffffff;
  font-size: 1rem;
}

.float-card--fragment strong {
  display: block;
  margin-top: 1rem;
  color: #ffffff;
  font-size: 2rem;
  font-weight: 650;
}

.float-card--fragment strong span {
  font-size: 1rem;
}

.float-card a {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  margin-top: 1rem;
  color: #25f5ee;
  font-size: 0.92rem;
  font-weight: 650;
  text-decoration: none;
}

.float-card__watermark {
  position: absolute;
  right: 1.4rem;
  bottom: 1.4rem;
  color: rgba(37, 245, 238, 0.24);
  font-size: 3.5rem;
}

.float-card--trial {
  right: 8%;
  top: 13%;
  width: 330px;
  min-height: 162px;
  padding: 1.5rem 1.6rem;
}

.float-card--trial h2,
.float-card--growth h2 {
  color: #ffffff;
  font-size: 1.08rem;
  font-weight: 650;
}

.float-card--trial strong {
  display: block;
  margin-top: 1rem;
  color: #ffffff;
  font-size: 1rem;
}

.float-card--trial p {
  margin-top: 0.5rem;
  color: rgba(230, 240, 247, 0.78);
}

.radar {
  position: absolute;
  right: 1.35rem;
  top: 3.4rem;
  display: block;
  width: 70px;
  aspect-ratio: 1;
  border: 1px solid rgba(37, 245, 238, 0.36);
  border-radius: 50%;
  background:
    radial-gradient(circle, rgba(37, 245, 238, 0.3), transparent 12%),
    conic-gradient(from 180deg, rgba(37, 245, 238, 0.22), transparent 35%);
  box-shadow: 0 0 22px rgba(37, 245, 238, 0.12);
}

.radar::before,
.radar::after {
  content: '';
  position: absolute;
  inset: 16px;
  border: 1px solid rgba(37, 245, 238, 0.28);
  border-radius: inherit;
}

.radar::after {
  inset: 31px;
}

.float-card--growth {
  right: 10%;
  bottom: 9%;
  width: 305px;
  min-height: 160px;
  padding: 1.45rem 1.6rem;
}

.float-card--growth p {
  margin-top: 0.9rem;
  color: rgba(230, 240, 247, 0.8);
}

.float-card--growth strong,
.float-card--growth span {
  color: #25f5ee;
}

.growth-line {
  position: absolute;
  right: 1.3rem;
  bottom: 1.5rem;
  width: 92px;
  color: #29dff3;
  filter: drop-shadow(0 0 8px rgba(41, 223, 243, 0.5));
}

.assistant-bot {
  position: absolute;
  left: 50%;
  top: 44%;
  width: 270px;
  height: 290px;
  transform: translate(-50%, -50%);
  filter: drop-shadow(0 24px 34px rgba(37, 245, 238, 0.16));
}

.assistant-bot__crest {
  position: absolute;
  left: 123px;
  top: 0;
  width: 42px;
  height: 66px;
  border-radius: 80% 20% 80% 20%;
  background: linear-gradient(135deg, #4afff2, #14918e);
  transform: rotate(48deg);
}

.assistant-bot__head {
  position: absolute;
  left: 52px;
  top: 38px;
  width: 168px;
  height: 122px;
  border: 13px solid #edf6f8;
  border-radius: 48px;
  background: #101824;
  box-shadow: 0 0 0 8px rgba(141, 210, 230, 0.08);
}

.assistant-bot__head::before,
.assistant-bot__head::after {
  content: '';
  position: absolute;
  top: 47px;
  width: 30px;
  height: 14px;
  border-radius: 999px;
  background: #35fff1;
  box-shadow: 0 0 14px rgba(53, 255, 241, 0.9);
}

.assistant-bot__head::before {
  left: 34px;
  transform: rotate(34deg);
}

.assistant-bot__head::after {
  right: 34px;
  transform: rotate(-34deg);
}

.assistant-bot__ear {
  position: absolute;
  top: 76px;
  width: 44px;
  height: 66px;
  border: 10px solid #dce9ef;
  border-radius: 50%;
  background: #172635;
}

.assistant-bot__ear::after {
  content: '';
  position: absolute;
  inset: 10px;
  border: 4px solid #2edfdc;
  border-radius: inherit;
}

.assistant-bot__ear--left {
  left: 24px;
}

.assistant-bot__ear--right {
  right: 24px;
}

.assistant-bot__body {
  position: absolute;
  left: 88px;
  top: 151px;
  display: grid;
  width: 94px;
  height: 108px;
  place-items: center;
  border-radius: 36px 36px 28px 28px;
  background: #edf6f8;
  color: #27dcd7;
  font-size: 2rem;
}

.assistant-bot__body em {
  font-style: normal;
}

.assistant-bot__arm {
  position: absolute;
  top: 169px;
  width: 74px;
  height: 26px;
  border-radius: 999px;
  background: #edf6f8;
}

.assistant-bot__arm--left {
  left: 36px;
  transform: rotate(-32deg);
}

.assistant-bot__arm--right {
  right: 36px;
  transform: rotate(20deg);
}

.assistant-bot__cape {
  position: absolute;
  right: 24px;
  bottom: 62px;
  width: 150px;
  height: 82px;
  border-radius: 70% 12% 70% 15%;
  background: linear-gradient(135deg, rgba(37, 245, 238, 0.48), rgba(13, 64, 83, 0.12));
  transform: rotate(-6deg);
  z-index: -1;
}

.analysis-panel {
  position: absolute;
  right: 2.8rem;
  top: 8.2%;
  width: 360px;
  min-height: 640px;
  padding: 1.65rem 1.35rem 1.35rem;
  border: 1px solid rgba(90, 208, 255, 0.14);
  border-radius: 1.2rem;
  background:
    linear-gradient(180deg, rgba(8, 25, 39, 0.76), rgba(4, 15, 26, 0.68)),
    rgba(4, 14, 24, 0.68);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.035);
  backdrop-filter: blur(16px);
}

.analysis-panel header h2 {
  margin: 0;
  color: rgba(235, 247, 255, 0.9);
  font-size: 1rem;
  font-weight: 650;
}

.analysis-panel header h2 span {
  color: #26ffee;
  letter-spacing: 0.15em;
}

.analysis-list {
  display: grid;
  gap: 1.25rem;
  margin-top: 1.55rem;
}

.analysis-card {
  display: grid;
  grid-template-columns: 44px 1fr;
  gap: 1rem;
  padding: 1.25rem;
  border: 1px solid rgba(130, 212, 255, 0.1);
  border-radius: 0.9rem;
  background: rgba(6, 18, 31, 0.48);
}

.analysis-card__icon {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 0.55rem;
  background: rgba(37, 245, 238, 0.08);
  color: #25f5ee;
  font-size: 1.4rem;
}

.analysis-card strong {
  color: #ffffff;
  font-size: 0.96rem;
}

.analysis-card p {
  margin: 0.65rem 0 0;
  color: rgba(221, 232, 241, 0.68);
  font-size: 0.86rem;
  line-height: 1.55;
}

.all-advice {
  display: flex;
  width: 100%;
  min-height: 58px;
  align-items: center;
  justify-content: center;
  gap: 1.2rem;
  margin-top: 1.35rem;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 0.8rem;
  background: linear-gradient(90deg, rgba(224, 237, 247, 0.08), rgba(224, 237, 247, 0.04));
  color: #ffffff;
  cursor: pointer;
  font-weight: 680;
}

.all-advice .n-icon {
  color: #25f5ee;
  font-size: 1.4rem;
}

.prompt-dock {
  position: absolute;
  left: 16%;
  bottom: 3.8%;
  width: min(940px, 58vw);
  padding: 1.05rem 1.35rem 1.35rem;
  border: 1px solid rgba(37, 245, 238, 0.28);
  border-radius: 1.1rem;
  background:
    linear-gradient(180deg, rgba(8, 25, 39, 0.78), rgba(4, 15, 26, 0.72)),
    rgba(4, 14, 24, 0.72);
  backdrop-filter: blur(16px);
}

.prompt-line {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding-bottom: 0.8rem;
  border-bottom: 1px solid rgba(224, 237, 247, 0.09);
}

.prompt-input :deep(.n-input) {
  --n-color: transparent !important;
  --n-text-color: #edf7ff !important;
  --n-placeholder-color: rgba(210, 225, 238, 0.55) !important;
  font-size: 1rem;
}

.prompt-line button {
  display: grid;
  width: 48px;
  height: 48px;
  flex: 0 0 auto;
  place-items: center;
  border: 0;
  background: transparent;
  color: #2efff1;
  cursor: pointer;
  font-size: 1.6rem;
}

.prompt-actions {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.prompt-actions button {
  display: inline-flex;
  min-height: 58px;
  align-items: center;
  justify-content: center;
  gap: 0.65rem;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 0.7rem;
  background: rgba(6, 18, 31, 0.55);
  color: rgba(237, 247, 255, 0.86);
  cursor: pointer;
  font-size: 0.92rem;
  font-weight: 650;
}

.prompt-actions .n-icon {
  color: #25f5ee;
  font-size: 1.25rem;
}

@media (max-width: 1280px) {
  .messenger-topbar {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .messenger-userbar {
    justify-self: start;
  }

  .messenger-stage {
    height: auto;
    min-height: 1120px;
    overflow-y: auto;
  }

  .hero-zone {
    right: 0;
  }

  .analysis-panel {
    top: auto;
    right: 2.8rem;
    bottom: 15rem;
    min-height: 520px;
  }

  .prompt-dock {
    left: 3.7rem;
    width: calc(100% - 7.4rem);
  }
}

@media (max-width: 900px) {
  .messenger-shell {
    flex-direction: column;
    overflow: auto;
  }

  .messenger-sidebar,
  .messenger-shell--collapsed .messenger-sidebar {
    width: 100%;
    min-height: auto;
    padding: 0.75rem;
  }

  .messenger-sidebar__brand {
    padding: 0.25rem 0.65rem 0.75rem;
  }

  .messenger-sidebar__nav {
    flex-direction: row;
    overflow-x: auto;
    padding-bottom: 0.25rem;
  }

  .messenger-nav {
    min-width: 132px;
    min-height: 64px;
    padding: 0.6rem 0.85rem;
  }

  .messenger-sidebar__collapse {
    display: none;
  }

  .messenger-main {
    overflow: visible;
  }

  .messenger-topbar,
  .messenger-stage {
    padding-inline: 1rem;
  }

  .messenger-stage {
    min-height: 1580px;
  }

  .hero-zone {
    position: relative;
    left: auto;
    right: auto;
    top: auto;
    bottom: auto;
    height: 840px;
  }

  .float-card--greeting,
  .float-card--fragment,
  .float-card--trial,
  .float-card--growth {
    position: relative;
    left: auto;
    right: auto;
    top: auto;
    bottom: auto;
    width: 100%;
    margin-bottom: 1rem;
  }

  .assistant-bot {
    top: 390px;
    transform: translate(-50%, -50%) scale(0.76);
  }

  .analysis-panel {
    position: relative;
    right: auto;
    bottom: auto;
    width: 100%;
    min-height: auto;
    margin-top: 1rem;
  }

  .prompt-dock {
    position: relative;
    left: auto;
    bottom: auto;
    width: 100%;
    margin-top: 1rem;
  }

  .prompt-actions {
    grid-template-columns: 1fr;
  }
}
</style>
