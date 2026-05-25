<script setup lang="ts">
import { ref } from 'vue'
import { NIcon } from 'naive-ui'
import {
  AddOutline,
  ChevronDownOutline,
  ChevronForwardOutline,
  CodeSlashOutline,
  LockClosedOutline,
  MapOutline,
  RemoveOutline,
  ServerOutline,
  SettingsOutline,
} from '@vicons/ionicons5'
import PlexSidebar from '../components/layout/PlexSidebar.vue'
import PlexTopbar from '../components/layout/PlexTopbar.vue'

type Domain = {
  key: string
  title: string
  progress: number
  state: string
  active?: boolean
  locked?: boolean
}


const sidebarCollapsed = ref(false)

const tabs = ['全部星域', '算法基础', '数据结构', '前端开发', '后端开发', '数据库', '计算机基础']

const domains: Domain[] = [
  { key: 'algo', title: '算法基础', progress: 62, state: '进行中', active: true },
  { key: 'data', title: '数据结构', progress: 41, state: '进行中', locked: true },
  { key: 'front', title: '前端开发', progress: 28, state: '待解锁', locked: true },
  { key: 'back', title: '后端开发', progress: 15, state: '待解锁', locked: true },
  { key: 'db', title: '数据库', progress: 8, state: '待解锁', locked: true },
]
</script>

<template>
  <div class="starpath-shell">
    <PlexSidebar v-model:collapsed="sidebarCollapsed" active-key="track" />

    <main class="starpath-main">
      <PlexTopbar
        title="星轨路径"
        subtitle="探索编程知识宇宙，点亮你的能力星图"
        placeholder="搜索知识点 / 试炼 / 星域"
        keyboard-hint="⌘K"
      />

      <section class="starpath-tabs" aria-label="星域分类">
        <button
          v-for="tab in tabs"
          :key="tab"
          type="button"
          class="domain-tab"
          :class="{ 'domain-tab--active': tab === '算法基础' }"
        >
          {{ tab }}
        </button>
        <div class="view-actions">
          <button type="button" class="view-select">
            切换视图
            <n-icon :component="ChevronDownOutline" />
          </button>
          <button type="button" class="map-button" aria-label="地图视图">
            <n-icon :component="MapOutline" />
          </button>
        </div>
      </section>

      <section class="starpath-content" aria-label="算法基础星域">
        <div class="content-left">
          <section class="path-board">
            <div class="domain-copy">
              <div class="domain-copy__head">
                <h2>算法基础星域</h2>
                <span>进行</span>
              </div>
              <p>星域探索进度</p>
              <strong>62%</strong>
              <div class="progress-line"><span /></div>
              <p class="domain-copy__desc">
                掌握算法思维的核心原理，<br />
                为解决复杂问题打下坚实基础。
              </p>
              <button type="button">
                星域详情
                <n-icon :component="ChevronForwardOutline" />
              </button>
            </div>

            <div class="path-canvas" aria-label="星轨节点图">
              <div class="path-orbits" aria-hidden="true">
                <span class="orbit orbit--outer" />
                <span class="orbit orbit--middle" />
                <span class="orbit orbit--inner" />
              </div>
              <svg class="path-lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                <defs>
                  <filter id="trackGlow" x="-30%" y="-30%" width="160%" height="160%">
                    <feGaussianBlur stdDeviation="0.35" result="blur" />
                    <feMerge>
                      <feMergeNode in="blur" />
                      <feMergeNode in="SourceGraphic" />
                    </feMerge>
                  </filter>
                </defs>
                <g fill="none" filter="url(#trackGlow)">
                  <path class="path-line path-line--done" d="M36 58 C45 53 48 48 56 46" />
                  <path class="path-line path-line--active" d="M56 46 C68 44 72 34 82 32" />
                  <path class="path-line path-line--active" d="M56 46 C50 55 48 64 45 76" />
                  <path class="path-line path-line--active" d="M45 76 C60 83 73 72 82 63" />
                  <path class="path-line path-line--locked" d="M28 69 C34 62 33 58 36 58" />
                  <path class="path-line path-line--locked" d="M43 32 C49 27 55 25 61 23" />
                  <path class="path-line path-line--locked" d="M43 32 C48 38 53 42 56 46" />
                </g>
              </svg>

              <div class="track-node track-node--current">
                <span class="track-node__badge">当前所在</span>
                <span class="track-node__orb">
                  <n-icon :component="CodeSlashOutline" />
                </span>
                <strong>01</strong>
                <p>算法思维入门</p>
                <em>◆ ◆ ◆ ◆</em>
              </div>

              <div class="track-node track-node--done track-node--n2">
                <span class="track-node__orb">
                  <n-icon :component="CodeSlashOutline" />
                </span>
                <strong>02</strong>
                <p>时间复杂<br />分析</p>
                <em>◆ ◆ ◆ ◆</em>
              </div>

              <div class="track-node track-node--done track-node--n5">
                <span class="track-node__orb">
                  <n-icon :component="ServerOutline" />
                </span>
                <strong>05</strong>
                <p>贪心算法</p>
                <em>◆ ◆ ◆ ◇</em>
              </div>

              <div class="track-node track-node--locked track-node--n3">
                <span class="track-node__orb">
                  <n-icon :component="LockClosedOutline" />
                </span>
                <strong>03</strong>
                <p>递归与分治</p>
                <em>◆ ◆ ◆ ◇</em>
              </div>

              <div class="track-node track-node--locked track-node--n4">
                <span class="track-node__orb">
                  <n-icon :component="LockClosedOutline" />
                </span>
                <strong>04</strong>
                <p>动态规划基础</p>
                <em>◆ ◆ ◇ ◇</em>
              </div>

              <div class="track-node track-node--locked track-node--n6">
                <span class="track-node__orb">
                  <n-icon :component="LockClosedOutline" />
                </span>
                <strong>06</strong>
                <p>图论基础</p>
                <em>◇ ◇ ◇ ◇</em>
              </div>

              <div class="track-node track-node--locked track-node--n7">
                <span class="track-node__orb">
                  <n-icon :component="LockClosedOutline" />
                </span>
                <strong>07</strong>
                <p>高级数据结构</p>
                <em>◇ ◇ ◇ ◇</em>
              </div>

              <div class="track-node track-node--locked track-node--n8">
                <span class="track-node__orb">
                  <n-icon :component="LockClosedOutline" />
                </span>
                <strong>08</strong>
                <p>算法综合应用</p>
                <em>◇ ◇ ◇ ◇</em>
              </div>

              <div class="zoom-tools" aria-label="地图控制">
                <button type="button" aria-label="放大"><n-icon :component="AddOutline" /></button>
                <button type="button" aria-label="缩小"><n-icon :component="RemoveOutline" /></button>
                <button type="button" aria-label="定位"><n-icon :component="SettingsOutline" /></button>
              </div>

              <div class="legend">
                <span><i class="legend__dot legend__dot--done" /> 已完成</span>
                <span><i class="legend__dot legend__dot--active" /> 进行中</span>
                <span><i class="legend__dot legend__dot--locked" /> 未解锁</span>
              </div>
            </div>
          </section>

          <section class="domain-overview">
            <h2><span />星域概览</h2>
            <div class="overview-list">
              <article
                v-for="domain in domains"
                :key="domain.key"
                class="overview-card"
                :class="{ 'overview-card--active': domain.active }"
              >
                <div>
                  <strong>{{ domain.title }}</strong>
                  <p>{{ domain.progress }}%</p>
                  <em>{{ domain.state }}</em>
                </div>
                <span class="planet" :class="{ 'planet--locked': domain.locked }">
                  <n-icon v-if="domain.locked" :component="LockClosedOutline" />
                </span>
              </article>
            </div>
          </section>
        </div>

        <aside class="detail-panel" aria-label="当前节点详情">
          <div class="detail-panel__head">
            <h2>01 算法思维入门</h2>
            <span>当前所在</span>
          </div>

          <div class="tags">
            <strong>核心知识</strong>
            <div>
              <span>抽象</span>
              <span>建模</span>
              <span>算法流程</span>
              <span>伪代码</span>
            </div>
          </div>

          <div class="panel-bot" aria-hidden="true">
            <span class="panel-bot__head" />
            <span class="panel-bot__body" />
            <span class="panel-bot__card panel-bot__card--left" />
            <span class="panel-bot__card panel-bot__card--right" />
          </div>

          <div class="mastery">
            <div>
              <strong>掌握进度</strong>
              <span>85%</span>
            </div>
            <p><span /></p>
          </div>

          <div class="advice">
            <strong>驿站使者建议</strong>
            <p>
              你已掌握算法基本流程，建议继续学习时间复杂度分析，为后续学习打下基础。
            </p>
            <a href="#" @click.prevent>前往驿站使者 <n-icon :component="ChevronForwardOutline" /></a>
          </div>

          <div class="rewards">
            <strong>星点奖励</strong>
            <div class="reward-row">
              <span>XP <em>+80</em></span>
              <span>结晶 <em>+1</em></span>
              <span>星尘 <em>+10</em></span>
            </div>
          </div>

          <button type="button" class="continue-btn">继续探索</button>
        </aside>
      </section>
    </main>
  </div>
</template>

<style scoped>
.starpath-shell {
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

.starpath-sidebar {
  position: relative;
  z-index: 4;
  width: 180px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 1.9rem 0 1.35rem;
  background:
    radial-gradient(circle at 22% 8%, rgba(20, 241, 226, 0.08), transparent 26%),
    linear-gradient(180deg, rgba(3, 15, 25, 0.98), rgba(1, 8, 15, 0.99));
  border-right: 1px solid rgba(110, 228, 255, 0.11);
}

.starpath-brand {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0 1.95rem 2.25rem;
  color: #25f5ee;
}

.brand-mark {
  filter: drop-shadow(0 0 12px rgba(37, 245, 238, 0.65));
}

.starpath-brand span {
  color: #ffffff;
  font-size: 1.55rem;
  font-weight: 780;
  letter-spacing: 0.06em;
}

.starpath-nav {
  display: grid;
  gap: 0.45rem;
  flex: 1;
  padding-top: 1rem;
}

.starpath-nav__item {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 78px;
  gap: 0.9rem;
  padding: 0.65rem 0.9rem 0.65rem 2.35rem;
  color: rgba(220, 230, 241, 0.68);
  text-decoration: none;
  transition: color 0.18s ease, background 0.18s ease;
}

.starpath-nav__item:hover {
  color: #ffffff;
  background: rgba(37, 245, 238, 0.045);
}

.starpath-nav__item--active {
  color: #4ffff2;
  background:
    linear-gradient(90deg, rgba(16, 240, 192, 0.27), rgba(16, 240, 192, 0.08) 72%, transparent),
    rgba(6, 182, 212, 0.035);
}

.starpath-nav__bar {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  opacity: 0;
  background: linear-gradient(180deg, #5ffff3, #12d8c8);
  box-shadow: 0 0 18px rgba(37, 245, 238, 0.76);
}

.starpath-nav__item--active .starpath-nav__bar {
  opacity: 1;
}

.starpath-nav__item .n-icon {
  font-size: 1.7rem;
}

.starpath-nav__item span:last-child {
  font-size: 1rem;
  font-weight: 680;
  white-space: nowrap;
}

.starpath-main {
  position: relative;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  background:
    radial-gradient(circle at 54% 48%, rgba(16, 240, 192, 0.09), transparent 34%),
    radial-gradient(circle at 78% 25%, rgba(79, 70, 229, 0.09), transparent 28%),
    linear-gradient(180deg, #06121f 0%, #020a12 60%, #01070e 100%);
}

.starpath-main::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.45;
  background-image:
    radial-gradient(1px 1px at 11% 21%, rgba(255, 255, 255, 0.3), transparent),
    radial-gradient(1px 1px at 38% 23%, rgba(93, 214, 255, 0.38), transparent),
    radial-gradient(1px 1px at 62% 47%, rgba(255, 255, 255, 0.18), transparent),
    radial-gradient(1px 1px at 86% 18%, rgba(166, 111, 255, 0.36), transparent);
  background-size: 340px 340px;
}

.starpath-top {
  position: relative;
  z-index: 3;
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(320px, 500px) minmax(260px, 1fr);
  align-items: center;
  gap: 1.4rem;
  padding: 1.45rem 2.25rem 1rem;
}

.starpath-title {
  position: relative;
  padding-left: 1.45rem;
}

.starpath-title::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.2rem;
  bottom: 0.2rem;
  width: 1px;
  background: rgba(39, 255, 238, 0.48);
}

.starpath-title h1 {
  margin: 0;
  color: #ffffff;
  font-size: 1.85rem;
  font-weight: 780;
  line-height: 1.08;
}

.starpath-title p {
  margin: 0.5rem 0 0;
  color: rgba(224, 237, 247, 0.72);
  font-size: 0.95rem;
}

.starpath-search__input :deep(.n-input) {
  --n-height: 48px !important;
  --n-color: rgba(6, 18, 31, 0.7) !important;
  --n-border: 1px solid rgba(130, 212, 255, 0.12) !important;
  --n-border-hover: 1px solid rgba(37, 245, 238, 0.32) !important;
  --n-text-color: #edf7ff !important;
  --n-placeholder-color: rgba(210, 225, 238, 0.58) !important;
  font-size: 0.9rem;
}

.search-kbd {
  padding: 0.12rem 0.42rem;
  border: 1px solid rgba(210, 225, 238, 0.13);
  border-radius: 0.35rem;
  color: rgba(220, 232, 242, 0.64);
  font-size: 0.75rem;
}

.starpath-userbar {
  justify-self: end;
  display: flex;
  align-items: center;
  gap: 1.35rem;
}

.icon-button {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #edf7ff;
  cursor: pointer;
}

.user-pill {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  border: 0;
  background: transparent;
  color: #ffffff;
  cursor: pointer;
}

.bot-avatar {
  border: 1px solid rgba(37, 245, 238, 0.28);
  background:
    radial-gradient(circle, rgba(37, 245, 238, 0.18), transparent 62%),
    #061827 !important;
  box-shadow:
    0 0 0 6px rgba(61, 163, 255, 0.1),
    0 0 22px rgba(37, 245, 238, 0.28);
}

.bot-avatar__face {
  position: relative;
  display: block;
  width: 32px;
  height: 22px;
  border-radius: 9px;
  background: #111926;
  box-shadow: inset 0 8px 0 #edf6f8;
}

.bot-avatar__face::before,
.bot-avatar__face::after {
  content: '';
  position: absolute;
  top: 12px;
  width: 8px;
  height: 3px;
  border-radius: 99px;
  background: #35fff1;
}

.bot-avatar__face::before {
  left: 7px;
  transform: rotate(28deg);
}

.bot-avatar__face::after {
  right: 7px;
  transform: rotate(-28deg);
}

.user-pill__copy {
  display: grid;
  gap: 0.2rem;
  text-align: left;
}

.user-pill__copy strong {
  font-size: 0.95rem;
}

.user-pill__copy em {
  width: fit-content;
  padding: 0.04rem 0.32rem;
  border-radius: 0.35rem;
  background: rgba(37, 245, 238, 0.18);
  color: #57fff2;
  font-size: 0.75rem;
  font-style: normal;
}

.starpath-tabs {
  position: relative;
  z-index: 3;
  display: flex;
  align-items: center;
  gap: 2rem;
  padding: 0.6rem 2.25rem 1.05rem;
  border-bottom: 1px solid rgba(126, 188, 220, 0.08);
}

.domain-tab {
  position: relative;
  flex: 0 0 auto;
  min-height: 42px;
  border: 0;
  background: transparent;
  color: rgba(224, 237, 247, 0.7);
  cursor: pointer;
  font-size: 0.96rem;
  font-weight: 620;
  white-space: nowrap;
}

.domain-tab--active {
  color: #eaffff;
}

.domain-tab--active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -0.55rem;
  height: 2px;
  border-radius: 99px;
  background: #23ffde;
  box-shadow: 0 0 14px rgba(35, 255, 222, 0.6);
}

.view-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 0.65rem;
  margin-left: auto;
}

.view-select,
.map-button {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  min-height: 48px;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 0.55rem;
  background: rgba(6, 18, 31, 0.68);
  color: #edf7ff;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 650;
}

.view-select {
  padding: 0 1.05rem;
}

.map-button {
  width: 52px;
  justify-content: center;
  color: #2efff1;
}

.starpath-content {
  position: relative;
  z-index: 2;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: 1rem;
  height: calc(100dvh - 178px);
  min-height: 0;
  padding: 0 2.25rem 1.25rem;
}

.content-left {
  display: grid;
  grid-template-rows: minmax(0, 1fr) 172px;
  gap: 1rem;
  min-width: 0;
  min-height: 0;
}

.path-board,
.domain-overview,
.detail-panel {
  border: 1px solid rgba(90, 208, 255, 0.13);
  border-radius: 0.7rem;
  background:
    linear-gradient(180deg, rgba(8, 25, 39, 0.62), rgba(4, 15, 26, 0.54)),
    rgba(4, 14, 24, 0.56);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

.path-board {
  position: relative;
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  min-height: 0;
  overflow: hidden;
}

.domain-copy {
  position: relative;
  z-index: 2;
  padding: 1.65rem 0 1.2rem 1.75rem;
}

.domain-copy__head {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}

.domain-copy h2 {
  margin: 0;
  color: #ffffff;
  font-size: 1.45rem;
}

.domain-copy__head span {
  padding: 0.25rem 0.5rem;
  border-radius: 0.35rem;
  background: rgba(16, 240, 192, 0.16);
  color: #22ffde;
  font-size: 0.78rem;
  font-weight: 720;
}

.domain-copy p {
  margin: 1.35rem 0 0;
  color: rgba(224, 237, 247, 0.68);
  font-size: 0.88rem;
}

.domain-copy strong {
  display: block;
  margin-top: 0.5rem;
  color: #ffffff;
  font-size: 1.9rem;
  line-height: 1;
}

.progress-line {
  width: 155px;
  height: 6px;
  margin-top: 0.9rem;
  overflow: hidden;
  border-radius: 99px;
  background: rgba(197, 219, 236, 0.12);
}

.progress-line span {
  display: block;
  width: 62%;
  height: 100%;
  border-radius: inherit;
  background: #19f0c9;
  box-shadow: 0 0 14px rgba(25, 240, 201, 0.38);
}

.domain-copy__desc {
  line-height: 1.65;
}

.domain-copy button {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  min-height: 46px;
  margin-top: 1.8rem;
  padding: 0 1rem;
  border: 1px solid rgba(130, 212, 255, 0.1);
  border-radius: 0.5rem;
  background: rgba(6, 18, 31, 0.72);
  color: #edf7ff;
  cursor: pointer;
  font-weight: 650;
}

.path-canvas {
  position: relative;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.path-orbits {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.orbit {
  position: absolute;
  left: 52%;
  top: 52%;
  border: 1px solid rgba(40, 238, 219, 0.12);
  border-radius: 50%;
  transform: translate(-50%, -50%) rotate(-14deg);
}

.orbit--outer {
  width: 780px;
  height: 420px;
  border-color: rgba(143, 190, 221, 0.08);
}

.orbit--middle {
  width: 600px;
  height: 320px;
  border-style: dashed;
}

.orbit--inner {
  width: 385px;
  height: 205px;
}

.path-lines {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.path-line {
  stroke-width: 0.34;
  stroke-dasharray: 2.4 2.4;
}

.path-line--done {
  stroke: rgba(35, 255, 222, 0.72);
}

.path-line--active {
  stroke: rgba(35, 255, 222, 0.86);
}

.path-line--locked {
  stroke: rgba(224, 237, 247, 0.58);
}

.track-node {
  --node-color: #26ffee;
  position: absolute;
  display: grid;
  width: 142px;
  justify-items: start;
  color: #ffffff;
}

.track-node__orb {
  display: grid;
  width: 66px;
  aspect-ratio: 1;
  place-items: center;
  border: 1px solid color-mix(in srgb, var(--node-color) 62%, transparent);
  border-radius: 50%;
  background:
    radial-gradient(circle, color-mix(in srgb, var(--node-color) 28%, transparent), transparent 66%),
    rgba(5, 17, 29, 0.9);
  color: #eaffff;
  box-shadow:
    0 0 0 8px color-mix(in srgb, var(--node-color) 9%, transparent),
    0 0 28px color-mix(in srgb, var(--node-color) 28%, transparent);
}

.track-node__orb .n-icon {
  font-size: 1.75rem;
}

.track-node strong {
  margin-top: 0.55rem;
  color: rgba(255, 255, 255, 0.88);
  font-size: 0.92rem;
}

.track-node p {
  margin: 0.1rem 0 0;
  color: rgba(240, 247, 255, 0.88);
  font-size: 0.9rem;
  line-height: 1.35;
}

.track-node em {
  margin-top: 0.25rem;
  color: #23ffde;
  font-size: 0.68rem;
  font-style: normal;
  letter-spacing: 0.12em;
}

.track-node--current {
  --node-color: #23ffde;
  left: 47%;
  top: 37%;
  align-items: center;
  justify-items: center;
  text-align: center;
  transform: translate(-50%, -50%);
}

.track-node--current .track-node__orb {
  width: 96px;
  box-shadow:
    0 0 0 12px rgba(35, 255, 222, 0.12),
    0 0 40px rgba(35, 255, 222, 0.52);
}

.track-node__badge {
  margin-bottom: 0.45rem;
  padding: 0.25rem 0.5rem;
  border-radius: 0.35rem;
  background: rgba(16, 240, 192, 0.16);
  color: #22ffde;
  font-size: 0.78rem;
  font-weight: 720;
}

.track-node--done {
  --node-color: #23ffde;
}

.track-node--locked {
  --node-color: #d7e6ef;
}

.track-node--locked .track-node__orb {
  opacity: 0.72;
}

.track-node--locked em {
  color: rgba(230, 240, 247, 0.58);
}

.track-node--n2 {
  left: 21%;
  top: 53%;
}

.track-node--n3 {
  left: 39%;
  top: 75%;
}

.track-node--n4 {
  left: 75%;
  top: 61%;
}

.track-node--n5 {
  left: 78%;
  top: 26%;
}

.track-node--n6 {
  left: 36%;
  top: 18%;
}

.track-node--n7 {
  left: 58%;
  top: 8%;
}

.track-node--n8 {
  left: 5%;
  top: 63%;
}

.zoom-tools {
  position: absolute;
  left: 1.75rem;
  bottom: 1.5rem;
  display: grid;
  overflow: hidden;
  border: 1px solid rgba(130, 212, 255, 0.12);
  border-radius: 0.45rem;
}

.zoom-tools button {
  display: grid;
  width: 44px;
  height: 42px;
  place-items: center;
  border: 0;
  border-bottom: 1px solid rgba(130, 212, 255, 0.12);
  background: rgba(6, 18, 31, 0.72);
  color: #e8f9ff;
  cursor: pointer;
}

.zoom-tools button:last-child {
  border-bottom: 0;
}

.legend {
  position: absolute;
  right: 1.45rem;
  bottom: 1.25rem;
  display: flex;
  gap: 1.3rem;
  color: rgba(224, 237, 247, 0.68);
  font-size: 0.78rem;
}

.legend span {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}

.legend__dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  transform: rotate(45deg);
}

.legend__dot--done {
  background: #23ffde;
}

.legend__dot--active {
  background: #38bdf8;
}

.legend__dot--locked {
  background: #7d8791;
}

.domain-overview {
  padding: 0.95rem 1.2rem;
  overflow: hidden;
}

.domain-overview h2 {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: 0 0 0.85rem;
  color: #ffffff;
  font-size: 1.1rem;
}

.domain-overview h2 span {
  width: 3px;
  height: 22px;
  background: #23ffde;
  box-shadow: 0 0 12px rgba(35, 255, 222, 0.65);
}

.overview-list {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 1rem;
}

.overview-card {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 82px;
  align-items: center;
  min-height: 112px;
  overflow: hidden;
  border: 1px solid rgba(130, 212, 255, 0.11);
  border-radius: 0.55rem;
  background: rgba(7, 22, 36, 0.72);
  padding: 1rem;
}

.overview-card--active {
  border-color: rgba(35, 255, 222, 0.62);
  box-shadow: inset 0 0 18px rgba(35, 255, 222, 0.05);
}

.overview-card strong {
  color: #ffffff;
  font-size: 1rem;
}

.overview-card p {
  margin: 0.42rem 0 0;
  color: #ffffff;
  font-size: 1.25rem;
}

.overview-card em {
  display: block;
  margin-top: 0.4rem;
  color: #23ffde;
  font-style: normal;
  font-size: 0.82rem;
}

.planet {
  position: relative;
  display: block;
  width: 78px;
  aspect-ratio: 1;
  border-radius: 50%;
  background:
    radial-gradient(circle at 35% 30%, rgba(102, 255, 220, 0.62), transparent 22%),
    radial-gradient(circle at 60% 70%, rgba(3, 86, 88, 0.9), rgba(8, 38, 56, 0.95));
  box-shadow: 0 0 24px rgba(35, 255, 222, 0.2);
}

.planet--locked {
  filter: grayscale(0.9);
  opacity: 0.55;
}

.planet--locked .n-icon {
  position: absolute;
  right: 0;
  bottom: 6px;
  color: #edf7ff;
  font-size: 1.15rem;
}

.detail-panel {
  position: relative;
  overflow: hidden;
  padding: 1.65rem 1.55rem 1.25rem;
}

.detail-panel__head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.detail-panel h2 {
  margin: 0;
  color: #ffffff;
  font-size: 1.22rem;
}

.detail-panel__head span {
  align-self: start;
  padding: 0.25rem 0.5rem;
  border-radius: 0.35rem;
  background: rgba(16, 240, 192, 0.16);
  color: #22ffde;
  font-size: 0.76rem;
  font-weight: 720;
  white-space: nowrap;
}

.tags {
  margin-top: 1.55rem;
}

.tags strong,
.mastery strong,
.advice strong,
.rewards strong {
  color: #ffffff;
  font-size: 0.9rem;
}

.tags div {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-top: 0.75rem;
}

.tags span {
  padding: 0.4rem 0.62rem;
  border-radius: 0.35rem;
  background: rgba(224, 237, 247, 0.08);
  color: rgba(240, 247, 255, 0.9);
  font-size: 0.78rem;
  font-weight: 650;
}

.panel-bot {
  position: relative;
  height: 190px;
  margin: 0.7rem 0 0;
}

.panel-bot__head {
  position: absolute;
  left: 50%;
  top: 28px;
  width: 118px;
  height: 86px;
  border: 8px solid #edf6f8;
  border-radius: 34px;
  background: #101824;
  transform: translateX(-50%);
  box-shadow: 0 0 0 7px rgba(37, 245, 238, 0.12);
}

.panel-bot__head::before,
.panel-bot__head::after {
  content: '';
  position: absolute;
  top: 31px;
  width: 21px;
  height: 11px;
  border-radius: 999px;
  background: #35fff1;
  box-shadow: 0 0 12px rgba(53, 255, 241, 0.9);
}

.panel-bot__head::before {
  left: 25px;
  transform: rotate(32deg);
}

.panel-bot__head::after {
  right: 25px;
  transform: rotate(-32deg);
}

.panel-bot__body {
  position: absolute;
  left: 50%;
  top: 108px;
  width: 82px;
  height: 66px;
  border-radius: 28px 28px 22px 22px;
  background: #edf6f8;
  transform: translateX(-50%);
}

.panel-bot__card {
  position: absolute;
  top: 48px;
  width: 48px;
  height: 70px;
  border: 1px solid rgba(35, 255, 222, 0.36);
  border-radius: 0.35rem;
  background: rgba(16, 240, 192, 0.08);
  box-shadow: 0 0 16px rgba(35, 255, 222, 0.13);
}

.panel-bot__card--left {
  left: 46px;
  transform: rotate(12deg);
}

.panel-bot__card--right {
  right: 46px;
  transform: rotate(-12deg);
}

.mastery {
  margin-top: 0.4rem;
}

.mastery div {
  display: flex;
  justify-content: space-between;
  color: #ffffff;
}

.mastery div span {
  font-weight: 720;
}

.mastery p {
  height: 7px;
  margin: 0.65rem 0 0;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(224, 237, 247, 0.12);
}

.mastery p span {
  display: block;
  width: 85%;
  height: 100%;
  background: #23ffde;
  box-shadow: 0 0 14px rgba(35, 255, 222, 0.38);
}

.advice {
  margin-top: 1.45rem;
  padding-top: 1.35rem;
  border-top: 1px solid rgba(224, 237, 247, 0.08);
}

.advice p {
  margin: 0.75rem 0 0;
  color: rgba(224, 237, 247, 0.72);
  font-size: 0.9rem;
  line-height: 1.6;
}

.advice a {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  margin-top: 0.9rem;
  color: #23ffde;
  font-size: 0.9rem;
  font-weight: 720;
  text-decoration: none;
}

.rewards {
  margin-top: 1.2rem;
  padding-top: 1.1rem;
  border-top: 1px solid rgba(224, 237, 247, 0.08);
}

.reward-row {
  display: flex;
  justify-content: space-between;
  gap: 0.8rem;
  margin-top: 0.9rem;
}

.reward-row span {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: #dff8ff;
  font-weight: 680;
}

.reward-row em {
  font-style: normal;
}

.continue-btn {
  width: 100%;
  min-height: 48px;
  margin-top: 1rem;
  border: 0;
  border-radius: 0.38rem;
  background: linear-gradient(90deg, rgba(16, 240, 192, 0.8), rgba(18, 150, 130, 0.88));
  color: #eaffff;
  cursor: pointer;
  font-size: 0.96rem;
  font-weight: 760;
}

@media (max-width: 1280px) {
  .starpath-top {
    grid-template-columns: 1fr;
  }

  .starpath-userbar {
    justify-self: start;
  }

  .starpath-content {
    grid-template-columns: 1fr;
    height: auto;
    overflow-y: auto;
  }

  .content-left {
    grid-template-rows: 620px auto;
  }

  .detail-panel {
    min-height: 760px;
  }
}

@media (max-width: 900px) {
  .starpath-shell {
    flex-direction: column;
    overflow: auto;
  }

  .starpath-sidebar {
    width: 100%;
    min-height: auto;
    padding: 0.75rem;
  }

  .starpath-brand {
    padding: 0.25rem 0.65rem 0.75rem;
  }

  .starpath-nav {
    display: flex;
    overflow-x: auto;
    gap: 0.45rem;
    padding-top: 0;
  }

  .starpath-nav__item {
    min-width: 132px;
    min-height: 64px;
    padding: 0.6rem 0.85rem;
  }

  .starpath-top,
  .starpath-tabs,
  .starpath-content {
    padding-inline: 1rem;
  }

  .starpath-tabs {
    overflow-x: auto;
    gap: 1.65rem;
    padding-bottom: 1rem;
  }

  .view-actions {
    margin-left: 0;
  }

  .path-board {
    grid-template-columns: 1fr;
  }

  .domain-copy {
    padding: 1.2rem 1rem 0;
  }

  .content-left {
    grid-template-rows: 880px auto;
  }

  .path-canvas {
    min-height: 650px;
  }

  .overview-list {
    grid-template-columns: 1fr;
  }

  .legend {
    left: 1rem;
    right: auto;
    flex-wrap: wrap;
  }
}
</style>
