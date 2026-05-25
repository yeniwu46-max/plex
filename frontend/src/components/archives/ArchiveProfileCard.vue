<script setup lang="ts">
import type { ArchiveProfile } from '../../data/archivesMock'

defineProps<{
  profile: ArchiveProfile
}>()
</script>

<template>
  <section class="card profile" aria-label="探索者档案">
    <div class="profile__badge" aria-hidden="true">
      <svg viewBox="0 0 120 120" width="88" height="88">
        <defs>
          <linearGradient id="badgeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="var(--plex-accent)" />
            <stop offset="100%" stop-color="var(--plex-node-blue)" />
          </linearGradient>
        </defs>
        <circle cx="60" cy="60" r="52" fill="none" stroke="url(#badgeGrad)" stroke-width="2" opacity="0.5" />
        <path
          fill="url(#badgeGrad)"
          d="M60 18l8 24h26l-21 15 8 24-21-16-21 16 8-24-21-15h26z"
        />
      </svg>
    </div>
    <div class="profile__body">
      <p class="profile__role">Explorer · {{ profile.displayName }}</p>
      <p class="profile__id">{{ profile.explorerId }}</p>
      <div class="profile__stats">
        <div class="stat">
          <span class="stat__label">当前等级</span>
          <span class="stat__value">Lv.{{ profile.level }}</span>
        </div>
        <div class="stat">
          <span class="stat__label">称号</span>
          <span class="stat__value stat__value--sm">{{ profile.rankTitle }}</span>
        </div>
        <div class="stat">
          <span class="stat__label">连续探索</span>
          <span class="stat__value">{{ profile.streakDays }} 天</span>
        </div>
      </div>
    </div>
    <div class="profile__bg" aria-hidden="true" />
  </section>
</template>

<style scoped>
.card {
  border-radius: 1rem;
  border: 1px solid var(--plex-border);
  background: rgba(11, 22, 40, 0.72);
  backdrop-filter: blur(12px);
}

.profile {
  position: relative;
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 1.35rem 1.5rem;
  overflow: hidden;
  min-height: 160px;
}

.profile__bg {
  position: absolute;
  right: -10%;
  bottom: -40%;
  width: 55%;
  height: 120%;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, rgba(16, 240, 192, 0.12), transparent 65%);
  pointer-events: none;
}

.profile__badge {
  flex-shrink: 0;
  filter: drop-shadow(0 0 20px rgba(16, 240, 192, 0.35));
}

.profile__role {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 600;
}

.profile__id {
  margin: 0.35rem 0 1rem;
  font-size: 0.78rem;
  color: var(--plex-muted);
  letter-spacing: 0.08em;
}

.profile__stats {
  display: flex;
  flex-wrap: wrap;
  gap: 1.25rem 2rem;
}

.stat__label {
  display: block;
  font-size: 0.68rem;
  color: var(--plex-muted);
  margin-bottom: 0.2rem;
}

.stat__value {
  font-size: 1rem;
  font-weight: 700;
  color: var(--plex-accent);
}

.stat__value--sm {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--plex-text);
}
</style>
