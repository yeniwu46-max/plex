<script setup lang="ts">
import { NIcon } from 'naive-ui'
import {
  FlaskOutline,
  ExtensionPuzzleOutline,
  TrophyOutline,
  HardwareChipOutline,
  LockClosedOutline,
} from '@vicons/ionicons5'
</script>

<template>
  <div class="map">
    <svg class="map__lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id="lnTeal" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="rgba(0,245,212,0.15)" />
          <stop offset="50%" stop-color="rgba(0,245,212,0.55)" />
          <stop offset="100%" stop-color="rgba(0,245,212,0.15)" />
        </linearGradient>
        <filter id="lineGlow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="0.35" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <!-- 中心到各节点 -->
      <g filter="url(#lineGlow)">
        <line x1="50" y1="50" x2="50" y2="14" stroke="url(#lnTeal)" stroke-width="0.35" />
        <line x1="50" y1="50" x2="22" y2="28" stroke="url(#lnTeal)" stroke-width="0.3" />
        <line x1="50" y1="50" x2="78" y2="28" stroke="url(#lnTeal)" stroke-width="0.3" />
        <line x1="50" y1="50" x2="24" y2="76" stroke="url(#lnTeal)" stroke-width="0.28" />
        <line x1="50" y1="50" x2="50" y2="88" stroke="rgba(148,163,184,0.25)" stroke-width="0.25" />
        <line x1="50" y1="50" x2="76" y2="80" stroke="rgba(148,163,184,0.22)" stroke-width="0.25" />
      </g>
    </svg>

    <div class="map__nodes">
      <!-- 顶部：补给站 -->
      <button type="button" class="node node--teal node--pos-top">
        <span class="node__tag">推荐</span>
        <span class="node__ring" />
        <span class="node__icon-wrap">
          <n-icon :component="FlaskOutline" class="node__icon" />
        </span>
        <span class="node__label">边界条件补给站</span>
      </button>

      <!-- 左上：碎片 -->
      <button type="button" class="node node--orange node--pos-tl">
        <span class="node__ring" />
        <span class="node__icon-wrap">
          <n-icon :component="ExtensionPuzzleOutline" class="node__icon" />
        </span>
        <span class="node__label">待修复碎片 x2</span>
      </button>

      <!-- 右上：试炼 -->
      <button type="button" class="node node--purple node--pos-tr">
        <span class="node__ring" />
        <span class="node__icon-wrap">
          <n-icon :component="TrophyOutline" class="node__icon" />
        </span>
        <span class="node__label">路径优化试炼</span>
      </button>

      <!-- 左下：AI -->
      <button type="button" class="node node--blue node--pos-bl">
        <span class="node__ring" />
        <span class="node__icon-wrap">
          <n-icon :component="HardwareChipOutline" class="node__icon" />
        </span>
        <span class="node__label">AI驿站</span>
      </button>

      <!-- 中下、右下：锁定 -->
      <div class="node node--locked node--pos-b">
        <span class="node__ring" />
        <span class="node__icon-wrap node__icon-wrap--muted">
          <n-icon :component="LockClosedOutline" class="node__icon" />
        </span>
        <span class="node__label">未解锁</span>
      </div>

      <div class="node node--locked node--pos-br">
        <span class="node__ring" />
        <span class="node__icon-wrap node__icon-wrap--muted">
          <n-icon :component="LockClosedOutline" class="node__icon" />
        </span>
        <span class="node__label">未解锁</span>
      </div>

      <!-- 中心当前位置 -->
      <div class="hub">
        <div class="hub__glow" />
        <div class="hub__star-wrap">
          <svg class="hub__star" viewBox="0 0 64 64" width="56" height="56">
            <defs>
              <filter id="hubStarGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="2.5" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            <path
              fill="#00f5d4"
              filter="url(#hubStarGlow)"
              d="M32 8l5.5 15.5L54 32l-16.5 8.5L32 56l-5.5-15.5L10 32l16.5-8.5L32 8z"
            />
          </svg>
        </div>
        <p class="hub__cap">当前位置</p>
        <p class="hub__title">算法星域 · 第二阶段</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.map {
  position: relative;
  flex: 1;
  min-height: 380px;
  min-width: 0;
  border-radius: 1rem;
  background:
    radial-gradient(ellipse 70% 55% at 50% 45%, rgba(0, 245, 212, 0.06), transparent 60%),
    radial-gradient(circle at 30% 70%, rgba(139, 92, 246, 0.05), transparent 45%),
    rgba(15, 23, 42, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.06);
  overflow: hidden;
}

.map__lines {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.map__nodes {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 400px;
}

.hub {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  z-index: 2;
  pointer-events: none;
}

.hub__glow {
  position: absolute;
  left: 50%;
  top: 42%;
  transform: translate(-50%, -50%);
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(0, 245, 212, 0.25) 0%, transparent 70%);
  animation: pulse 3.5s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 0.7;
    transform: translate(-50%, -50%) scale(1);
  }
  50% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1.08);
  }
}

.hub__star-wrap {
  position: relative;
  display: flex;
  justify-content: center;
  filter: drop-shadow(0 0 20px rgba(0, 245, 212, 0.55));
}

.hub__star {
  animation: breathe 2.8s ease-in-out infinite;
}

@keyframes breathe {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.04);
  }
}

.hub__cap {
  margin: 0.5rem 0 0.15rem;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  color: rgba(148, 163, 184, 0.85);
  text-transform: none;
}

.hub__title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: #f1f5f9;
  white-space: nowrap;
}

.node {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  width: 112px;
  margin-left: -56px;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  color: inherit;
  font: inherit;
  z-index: 3;
  transition: transform 0.2s ease;
}

.node:not(.node--locked):hover {
  transform: scale(1.04);
}

.node--locked {
  cursor: default;
  pointer-events: none;
}

.node__tag {
  position: absolute;
  top: -1.35rem;
  left: 50%;
  transform: translateX(-50%);
  font-size: 0.62rem;
  padding: 0.12rem 0.4rem;
  border-radius: 999px;
  background: rgba(0, 245, 212, 0.2);
  color: #00f5d4;
  border: 1px solid rgba(0, 245, 212, 0.35);
  white-space: nowrap;
}

.node__ring {
  position: absolute;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  border: 1px solid currentColor;
  opacity: 0.35;
  top: 0.35rem;
  pointer-events: none;
}

.node--teal {
  color: #00f5d4;
}

.node--orange {
  color: #fb923c;
}

.node--purple {
  color: #c084fc;
}

.node--blue {
  color: #38bdf8;
}

.node--locked {
  color: rgba(148, 163, 184, 0.5);
}

.node__icon-wrap {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.node--teal .node__icon-wrap {
  box-shadow: 0 0 20px rgba(0, 245, 212, 0.35);
}

.node--orange .node__icon-wrap {
  box-shadow: 0 0 18px rgba(251, 146, 60, 0.35);
}

.node--purple .node__icon-wrap {
  box-shadow: 0 0 18px rgba(192, 132, 252, 0.35);
}

.node--blue .node__icon-wrap {
  box-shadow: 0 0 18px rgba(56, 189, 248, 0.35);
}

.node__icon-wrap--muted {
  box-shadow: none;
  opacity: 0.65;
}

.node__icon {
  font-size: 1.35rem;
  color: currentColor;
}

.node__label {
  font-size: 0.68rem;
  line-height: 1.25;
  text-align: center;
  color: rgba(226, 232, 240, 0.88);
  max-width: 7.5rem;
}

.node--locked .node__label {
  color: rgba(148, 163, 184, 0.65);
}

.node--pos-top {
  left: 50%;
  top: 8%;
}

.node--pos-tl {
  left: 18%;
  top: 18%;
}

.node--pos-tr {
  left: 82%;
  top: 20%;
}

.node--pos-bl {
  left: 20%;
  bottom: 14%;
  top: auto;
}

.node--pos-b {
  left: 50%;
  bottom: 6%;
  top: auto;
}

.node--pos-br {
  left: 80%;
  bottom: 12%;
  top: auto;
}

@media (max-width: 640px) {
  .map__nodes {
    min-height: 340px;
  }

  .node {
    width: 96px;
    margin-left: -48px;
  }

  .node__label {
    font-size: 0.62rem;
  }

  .hub__title {
    font-size: 0.82rem;
  }
}
</style>
