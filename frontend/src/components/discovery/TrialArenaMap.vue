<script setup lang="ts">
import { computed, watch } from 'vue'
import { NIcon } from 'naive-ui'
import { LockClosedOutline } from '@vicons/ionicons5'
import {
  TRIAL_MODES,
  filterTrials,
  isTrialUnlocked,
  type TrialMode,
  type TrialPosition,
  type TrialTheme,
} from '../../data/trialArena'

const props = withDefaults(
  defineProps<{
    searchQuery?: string
    userLevel?: number
    modelValue?: string | null
  }>(),
  {
    searchQuery: '',
    userLevel: 1,
    modelValue: null,
  },
)

const emit = defineEmits<{
  'update:modelValue': [key: string | null]
  select: [trial: TrialMode]
  enter: [trial: TrialMode]
}>()

const visibleTrials = computed(() => filterTrials(props.searchQuery))

const selectedKey = computed({
  get: () => props.modelValue,
  set: (key) => emit('update:modelValue', key),
})

const selectedTrial = computed(() =>
  TRIAL_MODES.find((t) => t.key === selectedKey.value) ?? null,
)

const positionClass: Record<TrialPosition, string> = {
  tl: 'trial__card--pos-tl',
  tr: 'trial__card--pos-tr',
  bl: 'trial__card--pos-bl',
  br: 'trial__card--pos-br',
}

const themeClass: Record<TrialTheme, string> = {
  teal: 'trial__card--teal',
  purple: 'trial__card--purple',
  orange: 'trial__card--orange',
  pink: 'trial__card--pink',
}

function trialUnlocked(trial: TrialMode) {
  return isTrialUnlocked(trial, props.userLevel)
}

function selectTrial(trial: TrialMode) {
  if (!trialUnlocked(trial)) return
  selectedKey.value = trial.key
  emit('select', trial)
}

function onCardClick(trial: TrialMode) {
  if (!trialUnlocked(trial)) return
  if (selectedKey.value === trial.key) {
    emit('enter', trial)
    return
  }
  selectTrial(trial)
}

function onCardDblClick(trial: TrialMode) {
  if (trialUnlocked(trial)) emit('enter', trial)
}

function cardVisible(trial: TrialMode) {
  if (!props.searchQuery.trim()) return true
  return visibleTrials.value.some((t) => t.key === trial.key)
}

watch(
  visibleTrials,
  (list) => {
    if (selectedKey.value && !list.some((t) => t.key === selectedKey.value)) {
      selectedKey.value = list[0]?.key ?? null
    }
    if (!selectedKey.value && list.length > 0) {
      const firstUnlocked = list.find((t) => trialUnlocked(t))
      if (firstUnlocked) selectedKey.value = firstUnlocked.key
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="arena" aria-label="试炼场地图">
    <div class="arena__orbits" aria-hidden="true">
      <span class="arena__orbit arena__orbit--1" />
      <span class="arena__orbit arena__orbit--2" />
      <span class="arena__orbit arena__orbit--3" />
    </div>

    <svg class="arena__lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id="arenaGradTeal" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="rgba(0,245,212,0.35)" />
          <stop offset="50%" stop-color="rgba(0,245,212,0.18)" />
          <stop offset="100%" stop-color="rgba(0,245,212,0.06)" />
        </linearGradient>
        <filter id="arenaLineGlow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="0.5" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <g filter="url(#arenaLineGlow)">
        <line
          v-for="trial in TRIAL_MODES"
          :key="`line-${trial.key}`"
          x1="50"
          y1="50"
          :x2="trial.position === 'tl' ? 22 : trial.position === 'tr' ? 78 : trial.position === 'bl' ? 22 : 78"
          :y2="trial.position === 'tl' || trial.position === 'tr' ? 22 : 78"
          stroke="url(#arenaGradTeal)"
          :stroke-width="selectedKey === trial.key ? 0.55 : 0.35"
          :opacity="cardVisible(trial) ? 1 : 0.15"
        />
      </g>
    </svg>

    <div class="trials">
      <button
        v-for="trial in TRIAL_MODES"
        :key="trial.key"
        type="button"
        class="trial__card"
        :class="[
          positionClass[trial.position],
          themeClass[trial.theme],
          {
            'trial__card--selected': selectedKey === trial.key,
            'trial__card--locked': !trialUnlocked(trial),
            'trial__card--dimmed': !cardVisible(trial),
          },
        ]"
        :aria-pressed="selectedKey === trial.key"
        :aria-disabled="!trialUnlocked(trial)"
        :tabindex="cardVisible(trial) ? 0 : -1"
        @click="onCardClick(trial)"
        @dblclick="onCardDblClick(trial)"
      >
        <span v-if="trial.tags?.[0] && trialUnlocked(trial)" class="trial__tag">{{ trial.tags[0] }}</span>
        <span class="trial__number">{{ trial.number }}</span>
        <span class="trial__ring" aria-hidden="true" />

        <span class="trial__icon-wrap">
          <n-icon v-if="trialUnlocked(trial)" :component="trial.icon" class="trial__icon" />
          <n-icon v-else :component="LockClosedOutline" class="trial__icon trial__icon--lock" />
        </span>

        <span class="trial__title">{{ trial.title }}</span>
        <span class="trial__subtitle">{{ trial.titleEn }}</span>
        <span class="trial__desc">{{ trial.description }}</span>

        <span v-if="!trialUnlocked(trial)" class="trial__lock-hint">Lv.{{ trial.requiredLevel }} 解锁</span>
        <span v-else-if="selectedKey === trial.key" class="trial__cta">再次点击进入</span>
        <span v-else class="trial__arrow" aria-hidden="true">→</span>
      </button>

      <div class="diamond-hub" :class="{ 'diamond-hub--active': !!selectedTrial }">
        <div class="diamond-hub__glow" />
        <svg class="diamond-hub__diamond" viewBox="0 0 100 100" width="80" height="80" aria-hidden="true">
          <defs>
            <filter id="diamondGlow" x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation="2" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <linearGradient id="diamondGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#00f5d4" stop-opacity="0.8" />
              <stop offset="50%" stop-color="#06b6d4" stop-opacity="0.6" />
              <stop offset="100%" stop-color="#0369a1" stop-opacity="0.4" />
            </linearGradient>
          </defs>
          <g filter="url(#diamondGlow)">
            <polygon points="50,20 75,50 50,50" fill="url(#diamondGrad)" opacity="0.9" />
            <polygon points="25,50 50,20 50,50" fill="url(#diamondGrad)" opacity="0.7" />
            <polygon points="50,50 75,50 50,80" fill="url(#diamondGrad)" opacity="0.5" />
            <polygon points="25,50 50,50 50,80" fill="url(#diamondGrad)" opacity="0.6" />
          </g>
          <polygon
            points="50,20 75,50 50,80 25,50"
            fill="none"
            stroke="#00f5d4"
            stroke-width="1.5"
            opacity="0.4"
            filter="url(#diamondGlow)"
          />
        </svg>
        <p v-if="selectedTrial" class="diamond-hub__label">{{ selectedTrial.title }}</p>
        <p v-else class="diamond-hub__label diamond-hub__label--muted">选择试炼模式</p>
      </div>
    </div>

    <p v-if="searchQuery.trim() && visibleTrials.length === 0" class="arena__empty">
      未找到匹配的试炼，请换个关键词
    </p>
  </div>
</template>

<style scoped>
.arena {
  position: relative;
  flex: 1;
  width: 100%;
  height: 100%;
  min-height: 320px;
  min-width: 0;
  border-radius: 1rem;
  background:
    radial-gradient(ellipse 85% 70% at 50% 50%, rgba(16, 240, 192, 0.06), transparent 60%),
    radial-gradient(circle at 25% 25%, rgba(139, 92, 246, 0.05), transparent 40%),
    radial-gradient(circle at 75% 75%, rgba(244, 114, 182, 0.05), transparent 40%),
    linear-gradient(180deg, rgba(7, 17, 31, 0.4) 0%, rgba(11, 22, 40, 0.85) 100%);
  border: 1px solid var(--plex-border);
  overflow: hidden;
}

.arena__orbits {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 0;
}

.arena__orbit {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(16, 240, 192, 0.1);
}

.arena__orbit--1 {
  width: min(50%, 340px);
  aspect-ratio: 1;
}

.arena__orbit--2 {
  width: min(75%, 510px);
  aspect-ratio: 1;
  border-color: rgba(16, 240, 192, 0.06);
}

.arena__orbit--3 {
  width: min(92%, 620px);
  aspect-ratio: 1;
  border-color: rgba(16, 240, 192, 0.04);
  animation: orbitSpin 80s linear infinite;
}

@keyframes orbitSpin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.arena__lines {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  opacity: 0.65;
  z-index: 0;
}

.trials {
  position: absolute;
  inset: 0;
  z-index: 1;
}

.arena__empty {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, 80px);
  margin: 0;
  font-size: 0.85rem;
  color: rgba(148, 163, 184, 0.85);
  z-index: 4;
  text-align: center;
  pointer-events: none;
}

.diamond-hub {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  z-index: 2;
  pointer-events: none;
}

.diamond-hub--active .diamond-hub__glow {
  opacity: 1;
  animation-duration: 2.5s;
}

.diamond-hub__glow {
  position: absolute;
  left: 50%;
  top: 42%;
  transform: translate(-50%, -50%);
  width: 140px;
  height: 140px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(0, 245, 212, 0.22) 0%, transparent 70%);
  animation: hubPulse 4s ease-in-out infinite;
  opacity: 0.55;
}

@keyframes hubPulse {
  0%,
  100% {
    opacity: 0.45;
    transform: translate(-50%, -50%) scale(1);
  }
  50% {
    opacity: 0.85;
    transform: translate(-50%, -50%) scale(1.12);
  }
}

.diamond-hub__diamond {
  position: relative;
  animation: diamondFloat 5s ease-in-out infinite;
  filter: drop-shadow(0 0 16px rgba(0, 245, 212, 0.4));
}

@keyframes diamondFloat {
  0%,
  100% {
    transform: translateY(0) rotateZ(0deg);
  }
  25% {
    transform: translateY(-4px) rotateZ(2deg);
  }
  75% {
    transform: translateY(4px) rotateZ(-2deg);
  }
}

.diamond-hub__label {
  margin: 0;
  font-size: 0.78rem;
  font-weight: 600;
  color: #f1f5f9;
  max-width: 120px;
  text-align: center;
  line-height: 1.25;
}

.diamond-hub__label--muted {
  color: rgba(148, 163, 184, 0.75);
  font-weight: 500;
}

.trial__card {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  width: 140px;
  margin-left: -70px;
  background: rgba(15, 23, 42, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.85rem;
  padding: 0.95rem 0.8rem 0.85rem;
  cursor: pointer;
  color: inherit;
  font: inherit;
  z-index: 3;
  transition:
    transform 0.25s ease,
    background 0.25s ease,
    border-color 0.25s ease,
    box-shadow 0.25s ease,
    opacity 0.25s ease;
  backdrop-filter: blur(12px);
}

.trial__card:focus-visible {
  outline: 2px solid var(--plex-accent);
  outline-offset: 3px;
}

.trial__card:hover:not(.trial__card--locked):not(.trial__card--dimmed) {
  transform: scale(1.06) translateY(-3px);
  background: rgba(15, 23, 42, 0.88);
  border-color: rgba(255, 255, 255, 0.18);
}

.trial__card--selected {
  transform: scale(1.08) translateY(-4px);
  border-color: rgba(255, 255, 255, 0.22);
  box-shadow: 0 0 28px rgba(0, 245, 212, 0.2);
}

.trial__card--locked {
  cursor: not-allowed;
  opacity: 0.72;
}

.trial__card--dimmed {
  opacity: 0.25;
  pointer-events: none;
}

.trial__card--teal {
  color: #00f5d4;
}

.trial__card--teal.trial__card--selected,
.trial__card--teal:hover:not(.trial__card--locked) {
  box-shadow: 0 0 32px rgba(0, 245, 212, 0.35), 0 8px 24px rgba(0, 245, 212, 0.12);
}

.trial__card--purple {
  color: #c084fc;
}

.trial__card--purple.trial__card--selected,
.trial__card--purple:hover:not(.trial__card--locked) {
  box-shadow: 0 0 32px rgba(192, 132, 252, 0.35), 0 8px 24px rgba(192, 132, 252, 0.12);
}

.trial__card--orange {
  color: #fbbf24;
}

.trial__card--orange.trial__card--selected,
.trial__card--orange:hover:not(.trial__card--locked) {
  box-shadow: 0 0 32px rgba(251, 191, 36, 0.35), 0 8px 24px rgba(251, 191, 36, 0.12);
}

.trial__card--pink {
  color: #f472b6;
}

.trial__card--pink.trial__card--selected,
.trial__card--pink:hover:not(.trial__card--locked) {
  box-shadow: 0 0 32px rgba(244, 114, 182, 0.35), 0 8px 24px rgba(244, 114, 182, 0.12);
}

.trial__tag {
  position: absolute;
  top: -0.45rem;
  right: 0.5rem;
  padding: 0.12rem 0.45rem;
  font-size: 0.6rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  border-radius: 99px;
  background: rgba(0, 245, 212, 0.2);
  color: #99f6e4;
  border: 1px solid rgba(0, 245, 212, 0.35);
}

.trial__number {
  font-size: 0.95rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  opacity: 0.85;
}

.trial__ring {
  position: absolute;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  border: 1.5px solid currentColor;
  opacity: 0.28;
  top: -2px;
  pointer-events: none;
}

.trial__icon-wrap {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  z-index: 1;
  margin-top: 0.15rem;
}

.trial__card--teal .trial__icon-wrap {
  box-shadow: inset 0 0 12px rgba(0, 245, 212, 0.15), 0 0 16px rgba(0, 245, 212, 0.22);
}

.trial__card--purple .trial__icon-wrap {
  box-shadow: inset 0 0 12px rgba(192, 132, 252, 0.15), 0 0 16px rgba(192, 132, 252, 0.22);
}

.trial__card--orange .trial__icon-wrap {
  box-shadow: inset 0 0 12px rgba(251, 191, 36, 0.15), 0 0 16px rgba(251, 191, 36, 0.22);
}

.trial__card--pink .trial__icon-wrap {
  box-shadow: inset 0 0 12px rgba(244, 114, 182, 0.15), 0 0 16px rgba(244, 114, 182, 0.22);
}

.trial__icon {
  font-size: 1.5rem;
  color: currentColor;
}

.trial__icon--lock {
  opacity: 0.85;
}

.trial__title {
  font-size: 0.88rem;
  font-weight: 600;
  text-align: center;
  color: #f1f5f9;
}

.trial__subtitle {
  font-size: 0.62rem;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(148, 163, 184, 0.75);
}

.trial__desc {
  font-size: 0.65rem;
  line-height: 1.35;
  text-align: center;
  color: rgba(226, 232, 240, 0.72);
  margin: 0.1rem 0 0;
}

.trial__lock-hint {
  font-size: 0.62rem;
  font-weight: 600;
  color: rgba(248, 113, 113, 0.9);
  margin-top: 0.15rem;
}

.trial__cta {
  font-size: 0.62rem;
  color: var(--plex-accent);
  font-weight: 600;
  margin-top: 0.1rem;
}

.trial__arrow {
  font-size: 0.8rem;
  opacity: 0.5;
  margin-top: 0.05rem;
}

.trial__card--pos-tl {
  left: 20%;
  top: 16%;
}

.trial__card--pos-tr {
  left: 80%;
  top: 16%;
}

.trial__card--pos-bl {
  left: 20%;
  bottom: 16%;
  top: auto;
}

.trial__card--pos-br {
  left: 80%;
  bottom: 16%;
  top: auto;
}

@media (max-width: 900px) {
  .trial__card {
    width: 120px;
    margin-left: -60px;
    padding: 0.8rem 0.65rem;
  }

  .trial__desc,
  .trial__cta {
    display: none;
  }
}

@media (max-width: 640px) {
  .trial__card {
    width: 108px;
    margin-left: -54px;
  }

  .trial__title {
    font-size: 0.75rem;
  }

  .trial__card--pos-tl {
    left: 14%;
    top: 14%;
  }

  .trial__card--pos-tr {
    left: 86%;
    top: 14%;
  }

  .trial__card--pos-bl {
    left: 14%;
    bottom: 14%;
  }

  .trial__card--pos-br {
    left: 86%;
    bottom: 14%;
  }
}
</style>
