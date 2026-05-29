<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NIcon } from 'naive-ui'
import {
  ExtensionPuzzleOutline,
  HardwareChipOutline,
  LockClosedOutline,
  SparklesOutline,
  StorefrontOutline,
  TrophyOutline,
} from '@vicons/ionicons5'
import EmergencyMissionModal from './EmergencyMissionModal.vue'

const props = withDefaults(
  defineProps<{
    pendingFragmentCount?: number
    emergencyDoneToday?: boolean
  }>(),
  {
    pendingFragmentCount: 0,
    emergencyDoneToday: false,
  },
)

const emit = defineEmits<{
  emergencyCompleted: []
}>()

const fragmentLabel = computed(() => {
  const count = props.pendingFragmentCount
  if (count <= 0) return '待修复碎片'
  return `待修复碎片 x${count}`
})

const router = useRouter()
const emergencyOpen = ref(false)

function openEmergencyMission() {
  if (props.emergencyDoneToday) return
  emergencyOpen.value = true
}

function onEmergencyCompleted() {
  emit('emergencyCompleted')
}

function openMessenger() {
  void router.push('/student/messenger')
}

function openDailyQuest() {
  void router.push('/student/daily')
}

function openTrials() {
  void router.push('/student/trials')
}

function openStarPath() {
  void router.push('/student/star-path')
}
</script>

<template>
  <div class="star-map" aria-label="探索舱星图">
    <div class="orbit-field" aria-hidden="true">
      <span class="orbit orbit--outer" />
      <span class="orbit orbit--middle" />
      <span class="orbit orbit--inner" />
      <span class="orbit orbit--core" />
    </div>

    <svg class="star-map__lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <filter id="mapLineGlow" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="0.45" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <linearGradient id="lineTeal" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="rgba(39,255,238,0.2)" />
          <stop offset="52%" stop-color="rgba(39,255,238,0.86)" />
          <stop offset="100%" stop-color="rgba(39,255,238,0.2)" />
        </linearGradient>
        <linearGradient id="lineAmber" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="rgba(255,199,104,0.78)" />
          <stop offset="100%" stop-color="rgba(39,255,238,0.42)" />
        </linearGradient>
        <linearGradient id="linePurple" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="rgba(39,255,238,0.48)" />
          <stop offset="100%" stop-color="rgba(199,83,255,0.8)" />
        </linearGradient>
      </defs>
      <g filter="url(#mapLineGlow)">
        <line x1="50" y1="51" x2="50" y2="21" stroke="url(#lineTeal)" stroke-width="0.35" />
        <line x1="50" y1="51" x2="22" y2="37" stroke="url(#lineAmber)" stroke-width="0.28" />
        <line x1="50" y1="51" x2="80" y2="38" stroke="url(#linePurple)" stroke-width="0.28" />
        <line x1="50" y1="51" x2="23" y2="65" stroke="url(#lineTeal)" stroke-width="0.28" />
        <line x1="50" y1="51" x2="50" y2="82" stroke="rgba(177,206,222,0.34)" stroke-width="0.25" />
        <line x1="50" y1="51" x2="79" y2="64" stroke="rgba(177,206,222,0.3)" stroke-width="0.25" />
      </g>
      <g fill="#e9fbff">
        <circle cx="50" cy="38" r="0.55" />
        <circle cx="37" cy="47" r="0.45" />
        <circle cx="63" cy="48" r="0.45" />
        <circle cx="25" cy="65" r="0.55" />
        <circle cx="78" cy="64" r="0.52" />
        <circle cx="50" cy="82" r="0.55" />
      </g>
    </svg>

    <button
      type="button"
      class="map-node map-node--teal map-node--top"
      :class="{ 'map-node--done': emergencyDoneToday }"
      :aria-label="emergencyDoneToday ? '今日紧急任务已完成' : '边界条件补给站，开启紧急任务'"
      :disabled="emergencyDoneToday"
      @click="openEmergencyMission"
    >
      <span class="map-node__tag">{{ emergencyDoneToday ? '今日已完成' : '推荐' }}</span>
      <span class="map-node__orb">
        <n-icon :component="StorefrontOutline" />
      </span>
      <span class="map-node__label">边界条件补给站</span>
    </button>

    <EmergencyMissionModal v-model:show="emergencyOpen" @completed="onEmergencyCompleted" />

    <button
      type="button"
      class="map-node map-node--amber map-node--left"
      aria-label="待修复碎片，前往今日委托"
      @click="openDailyQuest"
    >
      <span class="map-node__orb">
        <n-icon :component="ExtensionPuzzleOutline" />
      </span>
      <span class="map-node__label">{{ fragmentLabel }}</span>
    </button>

    <button
      type="button"
      class="map-node map-node--purple map-node--right"
      aria-label="路径优化试炼，前往星轨路径"
      @click="openStarPath"
    >
      <span class="map-node__orb">
        <n-icon :component="TrophyOutline" />
      </span>
      <span class="map-node__label">路径优化试炼</span>
    </button>

    <button
      type="button"
      class="map-node map-node--blue map-node--bottom-left"
      aria-label="AI驿站，前往驿站使者"
      @click="openMessenger"
    >
      <span class="map-node__orb">
        <n-icon :component="HardwareChipOutline" />
      </span>
      <span class="map-node__label">AI驿站</span>
    </button>

    <div class="map-node map-node--locked map-node--bottom">
      <span class="map-node__orb">
        <n-icon :component="LockClosedOutline" />
      </span>
      <span class="map-node__label">未解锁</span>
    </div>

    <div class="map-node map-node--locked map-node--bottom-right">
      <span class="map-node__orb">
        <n-icon :component="LockClosedOutline" />
      </span>
      <span class="map-node__label">未解锁</span>
    </div>

    <button
      type="button"
      class="map-hub"
      aria-label="当前位置，前往试炼关卡"
      @click="openTrials"
    >
      <span class="map-hub__halo" aria-hidden="true" />
      <span class="map-hub__core">
        <n-icon :component="SparklesOutline" />
      </span>
      <strong>当前位置</strong>
      <span>算法星域 · 第二阶段</span>
    </button>
  </div>
</template>

<style scoped>
.star-map {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.orbit-field {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.orbit {
  position: absolute;
  left: 50%;
  top: 53%;
  border: 1px solid rgba(40, 238, 219, 0.14);
  border-radius: 50%;
  transform: translate(-50%, -50%) rotate(-8deg);
  box-shadow: 0 0 22px rgba(39, 255, 238, 0.035);
}

.orbit--outer {
  width: min(88vw, 1040px);
  height: min(38vw, 450px);
  border-color: rgba(143, 190, 221, 0.08);
}

.orbit--middle {
  width: min(68vw, 790px);
  height: min(29vw, 340px);
  border-style: dashed;
}

.orbit--inner {
  width: min(48vw, 560px);
  height: min(21vw, 245px);
}

.orbit--core {
  width: min(24vw, 280px);
  height: min(10vw, 118px);
  border-color: rgba(39, 255, 238, 0.46);
  box-shadow:
    0 0 26px rgba(39, 255, 238, 0.16),
    inset 0 0 28px rgba(39, 255, 238, 0.08);
}

.star-map__lines {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.map-node {
  --node-color: #27ffee;
  position: absolute;
  display: flex;
  width: 156px;
  margin-left: -78px;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font: inherit;
  text-align: center;
}

.map-node:not(.map-node--locked):hover .map-node__orb {
  transform: translateY(-2px) scale(1.04);
}

.map-node__orb {
  position: relative;
  display: grid;
  width: 92px;
  aspect-ratio: 1;
  place-items: center;
  border: 1px solid color-mix(in srgb, var(--node-color) 65%, transparent);
  border-radius: 50%;
  background:
    radial-gradient(circle, color-mix(in srgb, var(--node-color) 26%, transparent) 0 40%, transparent 62%),
    rgba(5, 17, 29, 0.88);
  box-shadow:
    0 0 0 8px color-mix(in srgb, var(--node-color) 9%, transparent),
    0 0 28px color-mix(in srgb, var(--node-color) 32%, transparent),
    inset 0 0 20px rgba(255, 255, 255, 0.035);
  color: #ffffff;
  transition: transform 0.18s ease;
}

.map-node__orb::before {
  content: '';
  position: absolute;
  inset: 9px;
  border: 1px solid color-mix(in srgb, var(--node-color) 52%, transparent);
  border-radius: inherit;
}

.map-node__orb .n-icon {
  font-size: 2.25rem;
  color: currentColor;
  filter: drop-shadow(0 0 12px color-mix(in srgb, var(--node-color) 80%, transparent));
}

.map-node__label {
  color: rgba(237, 247, 255, 0.82);
  font-size: 0.96rem;
  line-height: 1.3;
  text-shadow: 0 0 14px rgba(0, 0, 0, 0.65);
}

.map-node__tag {
  position: absolute;
  left: calc(50% + 38px);
  top: 4px;
  z-index: 2;
  padding: 0.2rem 0.42rem;
  border-radius: 0.35rem;
  background: rgba(16, 240, 192, 0.52);
  color: #eaffff;
  font-size: 0.76rem;
  font-weight: 720;
  white-space: nowrap;
}

.map-node--teal {
  --node-color: #27ffee;
}

.map-node--done,
.map-node:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  filter: grayscale(0.5);
}

.map-node--amber {
  --node-color: #ffc86b;
}

.map-node--purple {
  --node-color: #c95fff;
}

.map-node--blue {
  --node-color: #38bdf8;
}

.map-node--locked {
  --node-color: #c4d4de;
  cursor: default;
  pointer-events: none;
}

.map-node--locked .map-node__orb {
  opacity: 0.65;
  background: rgba(12, 23, 35, 0.76);
  box-shadow:
    0 0 0 8px rgba(177, 206, 222, 0.04),
    0 0 20px rgba(177, 206, 222, 0.1);
}

.map-node--locked .map-node__label {
  color: rgba(219, 230, 240, 0.48);
}

.map-node--top {
  left: 50%;
  top: 11%;
}

.map-node--left {
  left: 22%;
  top: 31%;
}

.map-node--right {
  left: 78%;
  top: 32%;
}

.map-node--bottom-left {
  left: 21%;
  top: 62%;
}

.map-node--bottom {
  left: 50%;
  top: 77%;
}

.map-node--bottom-right {
  left: 76%;
  top: 63%;
}

.map-hub {
  position: absolute;
  left: 50%;
  top: 53%;
  display: grid;
  justify-items: center;
  transform: translate(-50%, -50%);
  border: 0;
  background: transparent;
  color: #27ffee;
  text-align: center;
  cursor: pointer;
  font: inherit;
}

.map-hub:hover .map-hub__core {
  transform: scale(1.04);
}

.map-hub__halo {
  position: absolute;
  top: -82px;
  width: 310px;
  aspect-ratio: 1;
  border-radius: 50%;
  background:
    radial-gradient(circle, rgba(16, 240, 192, 0.5) 0 8%, rgba(16, 240, 192, 0.22) 18%, transparent 62%);
  filter: blur(3px);
  opacity: 0.88;
  pointer-events: none;
}

.map-hub__core {
  position: relative;
  display: grid;
  width: 116px;
  aspect-ratio: 1;
  place-items: center;
  border: 1px solid rgba(39, 255, 238, 0.68);
  border-radius: 50%;
  background:
    radial-gradient(circle, rgba(39, 255, 238, 0.32), transparent 64%),
    rgba(4, 23, 29, 0.82);
  box-shadow:
    0 0 0 11px rgba(16, 240, 192, 0.1),
    0 0 38px rgba(16, 240, 192, 0.56);
  color: #eaffff;
  transition: transform 0.18s ease;
}

.map-hub__core::before {
  content: '';
  position: absolute;
  inset: 11px;
  border: 1px solid rgba(39, 255, 238, 0.54);
  border-radius: inherit;
}

.map-hub__core .n-icon {
  font-size: 3.1rem;
  filter: drop-shadow(0 0 16px rgba(39, 255, 238, 0.95));
}

.map-hub strong {
  position: relative;
  margin-top: 1.15rem;
  color: #32ffef;
  font-size: 1.22rem;
  line-height: 1.2;
}

.map-hub span:last-child {
  position: relative;
  margin-top: 0.28rem;
  color: #23ffde;
  font-size: 1rem;
  font-weight: 620;
}

@media (max-width: 1100px) {
  .map-node--right,
  .map-node--bottom-right {
    left: 82%;
  }
}

@media (max-width: 760px) {
  .star-map {
    height: 620px;
    min-height: 620px;
  }

  .orbit--outer {
    width: 940px;
    height: 420px;
  }

  .orbit--middle {
    width: 720px;
    height: 320px;
  }

  .orbit--inner {
    width: 520px;
    height: 230px;
  }

  .map-node {
    width: 128px;
    margin-left: -64px;
  }

  .map-node__orb {
    width: 72px;
  }

  .map-node__label {
    font-size: 0.82rem;
  }

  .map-hub__core {
    width: 92px;
  }
}
</style>
