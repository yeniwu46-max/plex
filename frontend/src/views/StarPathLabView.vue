<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NIcon } from 'naive-ui'
import { fetchLearningPath, type LearningDomain } from '../api/studentProgress'
import { getPythonTrialQuestion } from '../data/pythonTrialQuestions'
import {
  STAR_PATH_ALGO_NODES,
  formatStarPathGems,
  getStarPathNode,
  isStarPathNodeUnlocked,
  starPathNodeTrackClass,
  getPrimaryQuestionId,
  type StarPathNode,
} from '../data/starPathTrail'
import {
  ChevronDownOutline,
  ChevronForwardOutline,
  CodeSlashOutline,
  LockClosedOutline,
  MapOutline,
  ServerOutline,
} from '@vicons/ionicons5'
import PlexSidebar from '../components/layout/PlexSidebar.vue'
import PlexTopbar from '../components/layout/PlexTopbar.vue'

const router = useRouter()

type Domain = {
  key: string
  title: string
  progress: number
  state: string
  active?: boolean
  locked?: boolean
}


const sidebarCollapsed = ref(false)
const loading = ref(true)
const errorMessage = ref('')
const domains = ref<Domain[]>([])
const activeDomainKey = ref('algo')

const tabs = ['全部星域', '算法基础', '数据结构', '前端开发', '后端开发', '数据库', '计算机基础']

const activeDomain = computed(() => domains.value.find((item) => item.key === activeDomainKey.value) ?? domains.value[0])

const starPathNodes = STAR_PATH_ALGO_NODES
const selectedNodeId = ref('01')

const selectedNode = computed(() => getStarPathNode(selectedNodeId.value) ?? starPathNodes[0])
const selectedQuestion = computed(() => getPythonTrialQuestion(getPrimaryQuestionId(selectedNode.value)))

function nodeIcon(node: StarPathNode) {
  if (node.status === 'locked') return LockClosedOutline
  if (node.icon === 'server') return ServerOutline
  return CodeSlashOutline
}

function nodePositionClasses(node: StarPathNode) {
  return [
    `track-node--${starPathNodeTrackClass(node)}`,
    node.position !== 'center' ? `track-node--${node.position}` : '',
    node.anchor ? `track-node--anchor-${node.anchor}` : '',
    { 'track-node--selected': selectedNodeId.value === node.id },
  ]
}

function onNodeClick(node: StarPathNode) {
  selectedNodeId.value = node.id
  if (isStarPathNodeUnlocked(node)) {
    void router.push(`/student/trials/practice/${getPrimaryQuestionId(node)}`)
  }
}

function continueExplore() {
  const node = selectedNode.value
  if (!isStarPathNodeUnlocked(node)) return
  void router.push(`/student/trials/practice/${getPrimaryQuestionId(node)}`)
}

function goToMessenger() {
  void router.push('/student/messenger')
}

function mapDomain(item: LearningDomain): Domain {
  return {
    key: item.key,
    title: item.title,
    progress: item.progress,
    state: item.state,
    active: item.active,
    locked: item.locked,
  }
}

async function loadPath() {
  loading.value = true
  errorMessage.value = ''
  try {
    const data = await fetchLearningPath()
    domains.value = data.domains.map(mapDomain)
    activeDomainKey.value = data.active_domain_key
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '星轨数据加载失败'
    domains.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadPath()
})
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

      <div v-if="loading" class="starpath-state">正在同步星轨路径…</div>
      <div v-else-if="errorMessage" class="starpath-state starpath-state--error">
        <span>{{ errorMessage }}</span>
        <n-button secondary size="small" @click="loadPath()">重试</n-button>
      </div>

      <section v-else class="starpath-content" :aria-label="`${activeDomain?.title ?? '星域'}星轨`">
        <div class="content-left">
          <section class="path-board">
            <div class="domain-copy">
              <div class="domain-copy__head">
                <h2>{{ activeDomain?.title ?? '星域' }}星域</h2>
                <span>{{ activeDomain?.state ?? '探索中' }}</span>
              </div>
              <p>星域探索进度</p>
              <strong>{{ activeDomain?.progress ?? 0 }}%</strong>
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
              <div class="path-track">
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
                <!-- 路径起止点在节点圆环边缘，控制点绕开圆心，避免线条穿过圆形组件 -->
                <g fill="none" filter="url(#trackGlow)">
                  <path class="path-line path-line--locked" d="M8.5 75.2 C9.5 66 12 56 17.5 48.5" />
                  <path class="path-line path-line--done" d="M19.5 46.2 C28 41 38 38 50.5 35.5" />
                  <path class="path-line path-line--active" d="M56.2 34.5 C66 27 78 18 89.5 12.2" />
                  <path class="path-line path-line--active" d="M50.2 40.2 C42 54 34 70 30.2 82.8" />
                  <path class="path-line path-line--active" d="M32.2 84.4 C52 78 72 68 90.8 58.2" />
                  <path class="path-line path-line--locked" d="M7.2 12.5 C16 17 32 26 49.2 35.2" />
                </g>
              </svg>

              <div
                v-for="node in starPathNodes"
                :key="node.id"
                class="track-node"
                :class="nodePositionClasses(node)"
                role="button"
                :tabindex="isStarPathNodeUnlocked(node) ? 0 : -1"
                :aria-label="`${node.id} ${node.title}${node.status === 'locked' ? '，未解锁' : ''}`"
                @click="onNodeClick(node)"
                @keydown.enter.prevent="onNodeClick(node)"
                @keydown.space.prevent="onNodeClick(node)"
              >
                <span v-if="node.status === 'current'" class="track-node__badge">当前所在</span>
                <span class="track-node__orb">
                  <n-icon :component="nodeIcon(node)" />
                </span>
                <strong>{{ node.id }}</strong>
                <p>
                  {{ node.title }}<template v-if="node.titleLine2"><br />{{ node.titleLine2 }}</template>
                </p>
                <em>{{ formatStarPathGems(node.gems) }}</em>
              </div>
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
          <div class="detail-panel__body">
            <div class="detail-panel__head">
              <h2>{{ selectedNode.id }} {{ selectedNode.title }}</h2>
              <span v-if="selectedNode.status === 'current'">当前所在</span>
              <span v-else-if="selectedNode.status === 'done'">已完成</span>
              <span v-else-if="selectedNode.status === 'progress'">进行中</span>
              <span v-else>未解锁</span>
            </div>

            <p v-if="selectedQuestion" class="detail-panel__trial">
              对应试炼：<strong>{{ selectedQuestion.title }}</strong>
              <small>{{ selectedQuestion.topic }}</small>
            </p>

          <div class="tags">
            <strong>核心知识</strong>
            <div>
              <span v-for="tag in selectedNode.knowledgeTags" :key="tag">{{ tag }}</span>
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
              <span>{{ selectedNode.mastery }}%</span>
            </div>
            <p><span :style="{ width: `${selectedNode.mastery}%` }" /></p>
          </div>

          <div class="advice">
            <strong>驿站使者建议</strong>
            <p>{{ selectedNode.advice }}</p>
            <a href="#" @click.prevent="goToMessenger">前往驿站使者 <n-icon :component="ChevronForwardOutline" /></a>
          </div>

            <div class="rewards">
              <strong>星点奖励</strong>
              <div class="reward-row">
                <span v-if="selectedQuestion">XP <em>+{{ selectedQuestion.rewardXp }}</em></span>
                <span>结晶 <em>+{{ selectedNode.rewardCrystal }}</em></span>
                <span>星尘 <em>+{{ selectedNode.rewardStardust }}</em></span>
              </div>
            </div>
          </div>

          <button
            type="button"
            class="continue-btn"
            :disabled="!isStarPathNodeUnlocked(selectedNode)"
            @click="continueExplore"
          >
            {{ isStarPathNodeUnlocked(selectedNode) ? '进入试炼' : '节点未解锁' }}
          </button>
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
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
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
  padding: 0.6rem var(--plex-page-gutter-x) 1.05rem;
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
  grid-template-rows: minmax(0, 1fr);
  align-items: stretch;
  gap: 1rem;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0 var(--plex-page-gutter-x) var(--plex-page-gutter-bottom);
}

.content-left {
  display: grid;
  grid-template-rows: minmax(360px, 1fr) auto;
  gap: 0.85rem;
  min-width: 0;
  min-height: 0;
  align-content: start;
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
  min-height: 460px;
  height: 100%;
  overflow: hidden;
}

.path-track {
  position: absolute;
  inset: 1.75rem 0.35rem 3rem 0.15rem;
  transform: none;
  transform-origin: center center;
}

.path-orbits {
  position: absolute;
  z-index: 0;
  inset: 0;
  pointer-events: none;
}

.orbit {
  position: absolute;
  left: 50%;
  top: 44%;
  border: 1px solid rgba(40, 238, 219, 0.12);
  border-radius: 50%;
  transform: translate(-50%, -50%) rotate(-14deg);
}

.orbit--outer {
  width: min(100%, 920px);
  height: 460px;
  border-color: rgba(143, 190, 221, 0.08);
}

.orbit--middle {
  width: min(82%, 700px);
  height: 340px;
  border-style: dashed;
}

.orbit--inner {
  width: min(56%, 440px);
  height: 220px;
}

.path-lines {
  position: absolute;
  z-index: 0;
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
  --node-orb: 52px;
  position: absolute;
  display: grid;
  width: max-content;
  max-width: 92px;
  justify-items: center;
  align-items: center;
  text-align: center;
  color: #ffffff;
  transform: translate(-50%, -50%);
}

.track-node__orb {
  position: relative;
  z-index: 1;
  display: grid;
  width: var(--node-orb);
  aspect-ratio: 1;
  place-items: center;
  border: 1px solid color-mix(in srgb, var(--node-color) 62%, transparent);
  border-radius: 50%;
  background:
    radial-gradient(circle, color-mix(in srgb, var(--node-color) 28%, transparent), transparent 66%),
    rgba(5, 17, 29, 0.96);
  color: #eaffff;
  box-shadow:
    0 0 0 5px color-mix(in srgb, var(--node-color) 9%, transparent),
    0 0 20px color-mix(in srgb, var(--node-color) 24%, transparent);
}

.track-node__orb .n-icon {
  font-size: 1.35rem;
}

.track-node strong {
  margin-top: 0.4rem;
  color: rgba(255, 255, 255, 0.88);
  font-size: 0.82rem;
}

.track-node p {
  margin: 0.06rem 0 0;
  color: rgba(240, 247, 255, 0.88);
  font-size: 0.78rem;
  line-height: 1.3;
}

.track-node em {
  margin-top: 0.18rem;
  color: #23ffde;
  font-size: 0.62rem;
  font-style: normal;
  letter-spacing: 0.1em;
}

.track-node--anchor-left {
  max-width: 88px;
  transform: translate(0, -50%);
  justify-items: start;
  text-align: left;
}

.track-node--anchor-right {
  max-width: 88px;
  transform: translate(-100%, -50%);
  justify-items: end;
  text-align: right;
}

.track-node--current {
  --node-color: #23ffde;
  --node-orb: 68px;
  left: 52%;
  top: 36%;
  z-index: 3;
  max-width: 96px;
}

.track-node--current .track-node__orb {
  box-shadow:
    0 0 0 8px rgba(35, 255, 222, 0.12),
    0 0 32px rgba(35, 255, 222, 0.48);
}

.track-node--current .track-node__orb .n-icon {
  font-size: 1.55rem;
}

.track-node__badge {
  position: absolute;
  bottom: calc(100% + 0.35rem);
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
  margin-bottom: 0;
  padding: 0.25rem 0.5rem;
  border-radius: 0.35rem;
  background: rgba(16, 240, 192, 0.16);
  color: #22ffde;
  font-size: 0.78rem;
  font-weight: 720;
}

.track-node {
  cursor: pointer;
}

.track-node--done {
  --node-color: #23ffde;
}

.track-node--progress {
  --node-color: #23ffde;
}

.track-node--selected {
  filter: drop-shadow(0 0 14px rgba(37, 245, 238, 0.45));
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

/* 圆心对齐 path-lines；左侧三节点阶梯错落，避免挤成一条竖线 */
.track-node--n2 {
  left: 19%;
  top: 47%;
  z-index: 2;
}

.track-node--n3 {
  left: 30%;
  top: 86%;
  z-index: 1;
}

.track-node--n4 {
  left: 92%;
  top: 60%;
  z-index: 1;
}

.track-node--n5 {
  left: 92%;
  top: 11%;
  z-index: 2;
}

.track-node--n6 {
  left: 5%;
  top: 10%;
  z-index: 1;
}

.track-node--n7 {
  left: 3%;
  top: 77%;
  z-index: 1;
}

.legend {
  position: absolute;
  z-index: 5;
  right: 1.45rem;
  bottom: 1.25rem;
  display: flex;
  gap: 1.3rem;
  padding: 0.35rem 0.5rem;
  border-radius: 0.4rem;
  background: rgba(4, 14, 24, 0.72);
  color: rgba(224, 237, 247, 0.68);
  font-size: 0.78rem;
  pointer-events: none;
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
  flex-shrink: 0;
  padding: 0.85rem 1.2rem 1rem;
  overflow: visible;
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
  grid-template-columns: repeat(5, minmax(108px, 1fr));
  gap: 0.75rem;
}

.overview-card {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 82px;
  align-items: center;
  min-height: 100px;
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
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  overflow: hidden;
  padding: 1.65rem 1.55rem 1rem;
}

.detail-panel__body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
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

.detail-panel__trial {
  margin: 0.85rem 0 0;
  color: rgba(221, 230, 239, 0.72);
  font-size: 0.84rem;
  line-height: 1.5;
}

.detail-panel__trial strong {
  color: #5fffe8;
  font-weight: 700;
}

.detail-panel__trial small {
  display: block;
  margin-top: 0.2rem;
  color: rgba(221, 230, 239, 0.52);
  font-size: 0.78rem;
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
  height: 165px;
  margin: 0.55rem 0 0;
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
  margin-top: 1.1rem;
  padding-top: 1.1rem;
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
  margin-top: 0.9rem;
  padding-top: 0.9rem;
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
  flex-shrink: 0;
  width: 100%;
  min-height: 48px;
  margin-top: 0.75rem;
  border: 0;
  border-radius: 0.38rem;
  background: linear-gradient(90deg, rgba(16, 240, 192, 0.8), rgba(18, 150, 130, 0.88));
  color: #eaffff;
  cursor: pointer;
  font-size: 0.96rem;
  font-weight: 760;
}

.continue-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
  background: rgba(80, 100, 110, 0.5);
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
  }

  .content-left {
    grid-template-rows: minmax(480px, 1fr) auto;
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
    padding-inline: var(--plex-page-gutter-x);
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
    grid-template-rows: minmax(520px, 1fr) auto;
  }

  .path-canvas {
    min-height: 520px;
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
